/** Live EIP-1193 SDK path test. Isolated Node signer, never browser key injection.
 * This verifies provider routing/signing against Studio, not an extension's UI.
 */
import fs from 'node:fs';
import crypto from 'node:crypto';
import assert from 'node:assert/strict';
import {createClient,createAccount,generatePrivateKey,abi} from 'genlayer-js';
import {localnet} from 'genlayer-js/chains';
import {CalldataAddress} from 'genlayer-js/types';
import {verifyWalletIdentity,singleSendProvider} from '../web/wallet.js';
const endpoint='http://localhost:4000/api';
const file=new URL('../verification/wallet-provider-live.json',import.meta.url);
const keyFile=new URL('../verification/private/wallet-provider-account.json',import.meta.url);
if(!fs.existsSync(keyFile))fs.writeFileSync(keyFile,JSON.stringify({privateKey:generatePrivateKey()}),{mode:0o600});
const signer=createAccount(JSON.parse(fs.readFileSync(keyFile)).privateKey);
const checkpoint=JSON.parse(fs.readFileSync(new URL('../verification/local-beta-full.json',import.meta.url)));
const address=checkpoint.address;
const chain={...localnet,id:61999,rpcUrls:{default:{http:[endpoint]}}};
const rpc=createClient({chain,endpoint});
const log=fs.existsSync(file)?JSON.parse(fs.readFileSync(file)):{address,account:signer.address,endpoint,calls:[],providerMethods:[],createdAt:new Date().toISOString(),scope:'Actual SDK EIP-1193 provider path with isolated Node signer; no browser extension UI tested'};
assert.equal(log.account,signer.address);assert.equal(log.address,address);
const save=()=>fs.writeFileSync(file,JSON.stringify(log,null,2)+'\n');
const provider={request:async({method,params})=>{
  log.providerMethods.push(method);
  if(method==='eth_accounts'||method==='eth_requestAccounts')return[signer.address];
  if(method!=='eth_sendTransaction')return rpc.request({method,params});
  const tx=params[0];assert.equal(tx.from.toLowerCase(),signer.address.toLowerCase());
  const signed=await signer.signTransaction({to:tx.to,data:tx.data,type:'legacy',value:BigInt(tx.value??0),gas:BigInt(tx.gas),gasPrice:BigInt(tx.gasPrice),nonce:Number(BigInt(tx.nonce)),chainId:Number(BigInt(tx.chainId))});
  return rpc.request({method:'eth_sendRawTransaction',params:[signed]});
}};
const identityParams=[{type:'read',to:address,from:signer.address,data:abi.transactions.serialize([abi.calldata.encode(abi.calldata.makeCalldataObject('race',[],{})),false]),transaction_hash_variant:'latest-final'}];
const verify=()=>verifyWalletIdentity(provider,rpc,{account:signer.address,chainId:61999,endpoint,params:identityParams});
const read=(functionName,kwargs={})=>rpc.readContract({address,functionName,kwargs,transactionHashVariant:'latest-final'});
async function send(method,kwargs){
 let row=log.calls.find(c=>c.method===method);
 if(!row){await verify();const sdk=createClient({chain,endpoint,account:signer.address,provider:singleSendProvider(provider,verify)});const hash=await sdk.writeContract({address,functionName:method,kwargs});row={method,hash,kwargs,submittedAt:new Date().toISOString()};log.calls.push(row);save();console.log(method,hash);}
 if(row.status==='FINALIZED')return;
 for(let i=0;i<900;i++){
  const tx=await rpc.request({method:'eth_getTransactionByHash',params:[row.hash]});
  if((tx?.statusName??tx?.status)==='FINALIZED'){
   row.status='FINALIZED';row.execution=tx.consensus_data?.leader_receipt?.[0]?.execution_result;
   row.rounds=tx.consensus_history?.consensus_results?.map(r=>r.status_changes);save();
   assert.equal(row.execution,'SUCCESS');assert.ok(row.rounds?.at(-1)?.includes('ACCEPTED'));console.log(method,'FINALIZED');return;
  }
  if(['CANCELED','UNDETERMINED'].includes(tx?.statusName??tx?.status))throw Error(method+' '+tx.statusName);
  await new Promise(r=>setTimeout(r,2000));
 }
 throw Error('Timed out; transaction checkpoint retained');
}
await send('join',{handle:'wallet-provider-check'});
const playerArgs={addr:new CalldataAddress(Uint8Array.from(Buffer.from(signer.address.slice(2),'hex')))};
log.salt??=crypto.randomBytes(16).toString('hex');save();
const commitment=crypto.createHash('sha256').update(['stout',log.salt,signer.address.toLowerCase(),'0'].join('|')).digest('hex');
await send('commit',{clue_idx:0,commitment});
log.cid??=Number((await read('player',playerArgs)).pending_cid);save();assert.ok(log.cid>=0);
await send('reveal',{cid:log.cid,answer:'stout',salt:log.salt});
await send('judge',{cid:log.cid});
log.player=await read('player',playerArgs);log.result=await read('commit_at',{cid:log.cid});
assert.equal(log.result.verdict,1);assert.equal(log.player.position,1);
assert.equal(log.providerMethods.filter(m=>m==='eth_sendTransaction').length,4);
log.passed=true;log.completedAt=new Date().toISOString();save();console.log('PASS provider path: join, commit, reveal, judge FINALIZED; CORRECT position 1');
