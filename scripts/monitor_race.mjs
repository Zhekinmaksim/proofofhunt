/** Bounded, unsigned reads. Exit 0 healthy, 1 actionable, 2 incomplete/RPC/config failure. */
import fs from 'node:fs';
import {pathToFileURL} from 'node:url';
import {createClient} from 'genlayer-js';
import {localnet, studionet} from 'genlayer-js/chains';

export function options(argv) {
  const out={};
  for(let i=0;i<argv.length;i+=2) {
    if(!argv[i].startsWith('--') || argv[i+1]===undefined) throw Error('Options require --name value');
    out[argv[i].slice(2)]=argv[i+1];
  }
  return out;
}
export function integer(value, fallback, min, max, name) {
  const n=Number(value??fallback);
  if(!Number.isInteger(n)||n<min||n>max) throw Error(`${name} must be an integer in ${min}..${max}`);
  return n;
}
export async function connect(opts) {
  const network=opts.network??'local';
  if(!['local','studionet'].includes(network)) throw Error('network must be local or studionet');
  const preset=network==='local'?localnet:studionet;
  const endpoint=opts.endpoint??(network==='local'?'http://localhost:4000/api':preset.rpcUrls.default.http[0]);
  if(!/^https?:\/\//.test(endpoint)) throw Error('endpoint requires HTTP(S)');
  if(!/^0x[0-9a-fA-F]{40}$/.test(opts.address??'')) throw Error('address requires a 20-byte contract address');
  const timeout=integer(opts['timeout-ms'],15000,1000,60000,'timeout-ms');
  const originalFetch=globalThis.fetch;
  // The pinned SDK does not expose a fetch timeout; abort its HTTP requests.
  globalThis.fetch=(url,init={})=>originalFetch(url,{...init,signal:AbortSignal.timeout(timeout)});
  const probe=createClient({chain:{...preset,rpcUrls:{...preset.rpcUrls,default:{...preset.rpcUrls.default,http:[endpoint]}}},endpoint});
  const chainId=Number(BigInt(await probe.request({method:'eth_chainId'})));
  const client=createClient({chain:{...preset,id:chainId},endpoint});
  return {network,endpoint,chainId,read:(functionName,kwargs={})=>client.readContract({address:opts.address,functionName,kwargs})};
}
export function assess(race, commits, now, complete=true) {
  const findings=[];
  const add=(code,details={})=>findings.push({code,...details});
  if(Number(race.protocol_version??1)<2) add('LEGACY_PROTOCOL_UNBOUNDED_DEADLINES');
  if([1,2].includes(Number(race.state)) && Number(race.closes_at??0)>0 && now>=Number(race.closes_at)) add('RACE_DEADLINE_EXPIRED',{action:'Review cancel_expired_race eligibility; do not resubmit pending writes blindly.'});
  for(const c of commits) {
    if([3,4].includes(Number(race.state))) continue;
    if(![0,3].includes(Number(c.verdict))) continue;
    if(Number(c.pin_status)===1) add('SOURCE_DRIFTED',{cid:c.cid,clue_idx:c.clue_idx});
    if(Number(c.pin_status)===2) add('SOURCE_UNREACHABLE',{cid:c.cid,clue_idx:c.clue_idx});
    if(Number(c.verdict)===3&&Number(c.pin_status)===0) add('JUDGE_UNDETERMINED',{cid:c.cid,clue_idx:c.clue_idx});
    const deadline=Number(c.revealed?c.judge_deadline:c.reveal_deadline);
    if(Number.isFinite(deadline)&&deadline>0&&now>=deadline) add('COMMIT_DEADLINE_EXPIRED',{cid:c.cid,deadline,action:'Review expire(cid) eligibility.'});
  }
  if(Number(race.state)===2) {
    const blockers=commits.filter(c=>Number(c.cid)<Number(race.winner_cid)&&Number(c.clue_idx)===Number(race.clue_count)-1&&[0,3].includes(Number(c.verdict)));
    add('PROVISIONAL_WINNER',{winner_cid:race.winner_cid,knownBlockerCids:blockers.map(c=>c.cid),note:'WON is provisional, not automatically a fault. Resolve or expire earlier final-clue claims.'});
    if(complete&&!blockers.length) add('FINALIZATION_REQUIRES_REVIEW');
  }
  if(!complete) add('INCOMPLETE_COMMIT_SCAN');
  return {healthy:findings.length===0,findings,exitCode:!complete?2:findings.length?1:0};
}
export function output(value, filename) {
  const text=JSON.stringify(value,(_,v)=>typeof v==='bigint'?v.toString():v,2)+'\n';
  if(filename) fs.writeFileSync(filename,text);
  process.stdout.write(text);
}
export async function main(opts) {
  const max=integer(opts['max-commits'],200,1,10000,'max-commits');
  const interval=integer(opts['interval-ms'],2500,250,60000,'interval-ms');
  const rpc=await connect(opts);
  const race=await rpc.read('race');
  const count=Number(race.commit_count);
  if(!Number.isSafeInteger(count)||count<0) throw Error('Invalid commit_count');
  const start=integer(opts['start-cid'],0,0,count,'start-cid');
  const commits=[];
  for(let cid=start;cid<Math.min(count,start+max);cid++) {
    await new Promise(r=>setTimeout(r,interval));
    const c=await rpc.read('commit_at',{cid});
    // Exclude revealed answers, commitments, handles and account data from operational output.
    commits.push({cid:Number(c.cid),clue_idx:Number(c.clue_idx),verdict:Number(c.verdict),pin_status:Number(c.pin_status),revealed:c.revealed,reveal_deadline:c.reveal_deadline,judge_deadline:c.judge_deadline});
  }
  const after=await rpc.read('race');
  const complete=start===0&&commits.length===count&&Number(after.commit_count)===count&&Number(after.state)===Number(race.state);
  const result={checkedAt:new Date().toISOString(),network:rpc.network,endpoint:rpc.endpoint,chainId:rpc.chainId,address:opts.address,race:after,scan:{start,count:commits.length,total:Number(after.commit_count),complete},commits,...assess(after,commits,Math.floor(Date.now()/1000),complete),sourceStatusScope:'Last recorded pending judge outcomes only; no live source fetch or write is performed.'};
  output(result,opts.output);process.exitCode=result.exitCode;
}
if(process.argv[1]&&import.meta.url===pathToFileURL(process.argv[1]).href) {
  let opts;
  try {opts=options(process.argv.slice(2));await main(opts);}
  catch(e) {output({checkedAt:new Date().toISOString(),healthy:false,exitCode:2,error:e.shortMessage??e.message},opts?.output);process.exitCode=2;}
}
