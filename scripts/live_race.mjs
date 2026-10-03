/** Real consensus verification. Requires npm --prefix scripts ci. */
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import {fileURLToPath} from 'node:url';
import {createClient, createAccount, generatePrivateKey, abi} from 'genlayer-js';
import {localnet, studionet} from 'genlayer-js/chains';
import {CalldataAddress} from 'genlayer-js/types';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const flags = Object.fromEntries(process.argv.slice(2).reduce((a, v, i, xs) => {
  if (v.startsWith('--')) a.push([v.slice(2), xs[i + 1]]);
  return a;
}, []));
const network = flags.network ?? 'local';
if (!['local', 'studionet'].includes(network)) throw Error('Use --network local|studionet');
const name = flags.name ?? 'prototype';
if (!/^[a-z0-9-]+$/.test(name)) throw Error('Invalid verification name');
const endpoint = network === 'local' ? 'http://localhost:4000/api' : studionet.rpcUrls.default.http[0];
const evidence = path.join(root, 'verification', `${network}-${name}.json`);
const existing = fs.existsSync(evidence) ? JSON.parse(fs.readFileSync(evidence)) : null;
const accountKeyName = flags['account-name'] ?? existing?.accountKeyName ?? '';
if(accountKeyName && !/^[a-z0-9-]+$/.test(accountKeyName)) throw Error('Invalid test account name');
const privateDir = path.join(root, 'verification/private');
fs.mkdirSync(privateDir, {recursive:true, mode:0o700});
const keyFile = path.join(privateDir, `${network}${accountKeyName ? '-'+accountKeyName : ''}-account.json`);
if (!fs.existsSync(keyFile)) fs.writeFileSync(keyFile, JSON.stringify({privateKey:generatePrivateKey()}), {mode:0o600});
const account = createAccount(JSON.parse(fs.readFileSync(keyFile)).privateKey);
const chain = {...(network === 'local' ? localnet : studionet)};
const probe = createClient({chain, endpoint});
const chainId = Number(BigInt(await probe.request({method:'eth_chainId'})));
chain.id = chainId;
const client = createClient({chain, endpoint, account});
const log = existing ?? {
  network, endpoint, chainId, accountKeyName, account:account.address, calls:[], plays:[], createdAt:new Date().toISOString()
};
if (log.account !== account.address || log.endpoint !== endpoint) throw Error('Checkpoint belongs to another account/network');
if (flags.address) log.address = flags.address;
const sourceSha256=crypto.createHash('sha256').update(fs.readFileSync(path.join(root,'contracts/proof_of_hunt.py'))).digest('hex');
if(log.client?.contractSha256 && log.client.contractSha256!==sourceSha256) throw Error('Source changed since this deployment; use a fresh race checkpoint');
log.client ??= {sdk:'genlayer-js@1.1.8',node:process.version,contractSha256:sourceSha256};
const save = () => fs.writeFileSync(evidence, JSON.stringify(log, (_, v) => typeof v === 'bigint' ? v.toString() : v, 2) + '\n');
const sleep = ms => new Promise(r=>setTimeout(r, ms));
const pollMs = network === 'studionet' ? 6000 : 2000;
async function retryRead(action) {
  for(let attempt=0;;attempt++) {
    try {return await action();} catch(error) {
      if(attempt>=4) throw error;
      console.log('Read-only RPC retry',attempt+1,error.shortMessage??error.message);
      await sleep(2000*(attempt+1));
    }
  }
}
const read = async (functionName, kwargs={}) => retryRead(()=>client.readContract({address:log.address,functionName,
  kwargs:functionName==='player' ? {addr:new CalldataAddress(Uint8Array.from(Buffer.from(kwargs.addr.slice(2),'hex')))} : kwargs}));

async function settle(row, requireFinal=flags.pipeline!=='true') {
  const deadline = Date.now() + 30 * 60_000;
  let seen;
  while (Date.now() < deadline) {
    const tx = await retryRead(()=>client.request({method:'eth_getTransactionByHash',params:[row.hash]}));
    if (!tx) {await sleep(pollMs); continue;}
    const status = tx.statusName ?? tx.status;
    if (status !== seen) {console.log(row.label, status); seen=status;}
    if (status === 'ACCEPTED' && !row.acceptedSeconds) {row.acceptedSeconds=(Date.now()-Date.parse(row.submittedAt))/1000;save();}
    if (['FINALIZED','CANCELED','UNDETERMINED'].includes(status) || (status==='ACCEPTED' && !requireFinal)) {
      const receipts = tx.consensus_data?.leader_receipt ?? [];
      const lead = Array.isArray(receipts) ? receipts[0] : receipts;
      row.status=status;
      if(status==='FINALIZED') row.finalizedSeconds=(Date.now()-Date.parse(row.submittedAt))/1000;
      row.address=tx.to_address ?? tx.to;
      row.execution=lead?.execution_result;
      row.stderr=lead?.genvm_result?.stderr ?? '';
      row.validators=[lead,...Object.values(tx.consensus_data?.validators ?? {})].filter(Boolean).map(v=>({
        address:v.node_config?.address,provider:v.node_config?.primary_model?.provider,
        model:v.node_config?.primary_model?.model,vote:v.vote,execution:v.execution_result,
        usage:v.execution_stats?.llm?.tokens
      }));
      row.votes=tx.consensus_data?.votes;
      row.consensusRounds=(tx.consensus_history?.consensus_results ?? []).map(r=>({round:r.consensus_round,statusChanges:r.status_changes}));
      row.outputs={};
      for(const [key,value] of Object.entries(lead?.eq_outputs ?? {})) {
        try {
          const bytes=Uint8Array.from(Buffer.from(value,'base64'));
          const decoded=abi.calldata.decode(bytes.subarray(1));
          try {row.outputs[key]=JSON.parse(decoded);} catch {row.outputs[key]=decoded;}
        } catch {row.outputs[key]={encoded:value};}
      }
      const receipt=await retryRead(()=>client.request({method:'eth_getTransactionReceipt',params:[row.hash]}));
      row.fee={gasUsed:receipt?.gasUsed,effectiveGasPrice:receipt?.effectiveGasPrice,actualNetworkFeeKnown:false,
        note:network==='local'?'Simulator receipt; local inference has no provider invoice.':'Studio simulator receipt; not a measured production inference invoice.'};
      save();
      const lastRound=row.consensusRounds.at(-1);
      const consensusFailed=lastRound && !(lastRound.statusChanges??[]).includes('ACCEPTED');
      if((status!=='FINALIZED' && !(status==='ACCEPTED' && !requireFinal))||row.execution!=='SUCCESS'||consensusFailed) throw Error(`${row.label}: ${status}/${row.execution}: ${row.stderr}`);
      return row;
    }
    await sleep(pollMs);
  }
  throw Error(`${row.label} timed out; hash checkpoint saved, do not resubmit blindly`);
}
async function transact(label, functionName, kwargs={}, deploy=false) {
  let row=log.calls.find(c=>c.label===label);
  if(row && JSON.stringify(row.kwargs)!==JSON.stringify(kwargs)) throw Error(`Checkpoint arguments changed for ${label}; preserve the old call and use a new label`);
  if(row) {if(row.status==='FINALIZED' && row.execution==='SUCCESS' && (!row.consensusRounds?.length || row.consensusRounds.at(-1).statusChanges?.includes('ACCEPTED'))) return row; return settle(row);}
  const submittedAt=new Date().toISOString();
  const hash=deploy ? await client.deployContract({code:fs.readFileSync(path.join(root,'contracts/proof_of_hunt.py'),'utf8'),kwargs})
    : await client.writeContract({address:log.address,functionName,kwargs});
  row={label,functionName,kwargs,hash,submittedAt};
  const runtimePath=path.join(root,`verification/runtime-${network}.json`);
  if(fs.existsSync(runtimePath)) row.runtime=JSON.parse(fs.readFileSync(runtimePath));
  log.calls.push(row);save();console.log(label,hash);
  return settle(row);
}
async function drain() {
  for(const row of log.calls.filter(c=>c.status==='ACCEPTED' && c.execution==='SUCCESS')) await settle(row,true);
}
async function author() {
  if(!flags.clues) throw Error('author requires --clues clues/file.json');
  const fixture=JSON.parse(fs.readFileSync(path.resolve(root,flags.clues)));
  if(!log.address) {const tx=await transact('deploy','__init__',{title:fixture.race_title},true);log.address=tx.address;save();}
  const info=await read('race');
  if(info.owner.toLowerCase()!==account.address.toLowerCase()) throw Error('Authoring account does not own this contract');
  for(const [i, clue] of fixture.clues.entries()) {
    const {expected, ...args}=clue;
    await transact(`add_clue[${i}]`,'add_clue',args);
  }
  for(const i of fixture.clues.keys()) {
    const label=flags['retry-pin']===String(i) ? `pin_clue[${i}]-${flags['retry-label']??'retry-1'}` : `pin_clue[${i}]`;
    await transact(label,'pin_clue',{idx:i});
  }
  await drain();
  for(const idx of fixture.clues.keys()) {
    if(!(await read('clue',{idx})).pinned) throw Error(`Clue ${idx} is not pinned after finalization`);
  }
  await transact(flags['retry-open']==='true' ? `open_race-${flags['retry-label']??'retry-1'}` : 'open_race','open_race');
  await drain();
  log.race=await read('race');save();console.log('Authored',log.address,log.race);
}
async function play() {
  if(!log.address || !flags.clues) throw Error('play requires contract checkpoint/address and --clues');
  const fixture=JSON.parse(fs.readFileSync(path.resolve(root,flags.clues)));
  await transact('join','join',{handle:`verification-${network}`});
  const limit=Number(flags.limit ?? fixture.clues.length);
  for(let idx=0;idx<limit;idx++) {
    let turn=log.plays.find(x=>x.idx===idx);
    // A manual judge phase may have completed after prepare; inspect its actual state.
    if(turn && !turn.result && log.calls.some(c=>c.functionName==='judge' && c.kwargs.cid===turn.cid && c.status==='FINALIZED' && c.execution==='SUCCESS')) {
      const observed=await read('commit_at',{cid:turn.cid});
      if(observed.verdict===1 || observed.verdict===2) {
        turn.result=observed;turn.player=await read('player',{addr:account.address});save();
      }
    }
    let priorAttempts;
    if(flags['new-attempt']===String(idx) && turn?.result?.verdict===2) {
      const current=await read('player',{addr:account.address});
      if(current.position!==idx) throw Error('New attempt requires this current clue');
      const {priorAttempts:previous=[], ...old}=turn;
      priorAttempts=[...previous,old];
      log.plays.splice(log.plays.indexOf(turn),1);turn=null;
    }
    if(!turn) {
      const answer=fixture.clues[idx].expected;
      const salt=idx===0 && flags.salt ? flags.salt : crypto.randomBytes(24).toString('hex');
      const commitment=crypto.createHash('sha256').update([answer.trim().toLowerCase().replace(/\s+/g,' '),salt,account.address.toLowerCase(),String(idx)].join('|')).digest('hex');
      if(idx===0 && flags.commitment && commitment!==flags.commitment) throw Error('Browser commitment does not match this player/answer/salt');
      turn={idx,answer,salt,commitment,attempt:(priorAttempts?.length??0)+1,...(priorAttempts?{priorAttempts}:{})};log.plays.push(turn);save();
    }
    if(turn.result?.verdict===1) {
      const current=await read('player',{addr:account.address});
      if(current.position>=idx+1) {console.log('Already cleared',idx);continue;}
    }
    const suffix=turn.attempt>1 ? `-attempt-${turn.attempt}` : '';
    await transact(`commit[${idx}]${suffix}`,'commit',{clue_idx:idx,commitment:turn.commitment});
    // Other players may commit between our read and transaction execution.
    // Resolve the id from accepted contract state, never predict it from count.
    const ownPlayer=await read('player',{addr:account.address});
    let resolved;
    const matches=c=>c.player.toLowerCase()===account.address.toLowerCase() && c.clue_idx===idx && c.commitment===turn.commitment;
    if(Number.isSafeInteger(ownPlayer.pending_cid) && ownPlayer.pending_cid>=0) {
      const pending=await read('commit_at',{cid:ownPlayer.pending_cid});
      if(matches(pending)) resolved=pending.cid;
    }
    if(resolved===undefined && Number.isSafeInteger(turn.cid)) {
      const previous=await read('commit_at',{cid:turn.cid});
      if(matches(previous)) resolved=previous.cid;
    }
    // Legacy v1 contracts do not expose pending_cid. This also allows resuming
    // after a reveal already settled, without submitting another commitment.
    if(resolved===undefined) {
      const race=await read('race');
      for(let cid=race.commit_count-1;cid>=0;cid--) {
        if(matches(await read('commit_at',{cid}))) {resolved=cid;break;}
      }
    }
    if(resolved===undefined) throw Error('Accepted commitment not found for this player, clue and digest; refusing reveal');
    if(turn.cid!==undefined && turn.cid!==resolved) {
      turn.cidCorrections??=[];
      turn.cidCorrections.push({previous:turn.cid,actual:resolved,reason:'Concurrent player committed before this transaction',observedAt:new Date().toISOString()});
    }
    turn.cid=resolved;save();
    const revealBase=`reveal[${idx}]${suffix}`;
    const priorReveal=log.calls.find(c=>c.label===revealBase);
    const revealLabel=priorReveal && priorReveal.kwargs.cid!==turn.cid ? `${revealBase}-resolved-cid-${turn.cid}` : revealBase;
    await transact(revealLabel,'reveal',{cid:turn.cid,answer:turn.answer,salt:turn.salt});
    if(flags.phase==='prepare') {
      await drain();
      log.failureBaseline=await read('player',{addr:account.address});
      save();console.log('Prepared',turn.cid,log.failureBaseline);return;
    }
    const judgeLabel=flags['retry-judge']===String(idx) ? `judge[${idx}]${suffix}-${flags['retry-label'] ?? 'retry-1'}` : `judge[${idx}]${suffix}`;
    await transact(judgeLabel,'judge',{cid:turn.cid});
    turn.result=await read('commit_at',{cid:turn.cid});
    turn.player=await read('player',{addr:account.address});save();console.log('Verdict',idx,turn.result,turn.player);
    if(turn.result.verdict!==1||turn.player.position!==idx+1) throw Error(`Clue ${idx}: expected CORRECT and position ${idx+1}`);
  }
  await drain();
  for(const turn of log.plays.filter(p=>p.idx<limit)) {
    turn.finalResult=await read('commit_at',{cid:turn.cid});
    if(turn.finalResult.verdict!==1) throw Error('Finalized verdict differs from accepted verdict');
  }
  log.race=await read('race');log.leaderboard=await read('leaderboard');save();
}
if(flags.phase==='author') await author();
else if(['play','prepare'].includes(flags.phase)) await play();
else if(flags.phase==='judge') {
  const row=await transact(flags.label ?? `judge-${flags.cid}`,'judge',{cid:Number(flags.cid)});
  await drain();
  log.lastCommit=await read('commit_at',{cid:Number(flags.cid)});
  log.lastPlayer=await read('player',{addr:account.address});
  row.snapshot={commit:log.lastCommit,player:log.lastPlayer};save();console.log(log.lastCommit,log.lastPlayer);
  if(flags['expect-verdict'] && log.lastCommit.verdict!==Number(flags['expect-verdict'])) throw Error('Unexpected verdict');
  if(flags['expect-pin'] && log.lastCommit.pin_status!==Number(flags['expect-pin'])) throw Error('Unexpected pin status');
  if(flags['expect-position'] && log.lastPlayer.position!==Number(flags['expect-position'])) throw Error('Unexpected player position');
  if(flags['assert-free']==='true') {
    if(!log.failureBaseline) throw Error('Missing baseline; run prepare first');
    for(const key of ['attempts_used','total_attempts','position','cleared']) {
      if(log.lastPlayer[key]!==log.failureBaseline[key]) throw Error(`UNDETERMINED changed ${key}`);
    }
    console.log('PASS: attempts and position unchanged');
  }
} else if(flags.phase==='read') {log.race=await read('race');log.leaderboard=await read('leaderboard');save();console.log(log.race,log.leaderboard);}
else throw Error('Use --phase author|play|prepare|judge|read');
