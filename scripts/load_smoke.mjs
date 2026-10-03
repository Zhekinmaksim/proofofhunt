/** Low-rate read latency smoke. Never signs or submits transactions. */
import {performance} from 'node:perf_hooks';
import {connect,options,integer,output} from './monitor_race.mjs';
let opts;
try {
  opts=options(process.argv.slice(2));
  const samples=integer(opts.samples,10,1,100,'samples');
  const interval=integer(opts['interval-ms'],1000,500,60000,'interval-ms');
  const rpc=await connect(opts),latencies=[],failures=[];
  for(let i=0;i<samples;i++) {
    if(i) await new Promise(r=>setTimeout(r,interval));
    const began=performance.now();
    try {const race=await rpc.read('race');if(!Number.isSafeInteger(Number(race.commit_count))) throw Error('Invalid race response');latencies.push(performance.now()-began);}
    catch(e) {failures.push({sample:i,error:e.shortMessage??e.message});}
  }
  latencies.sort((a,b)=>a-b);
  const percentile=p=>latencies.length?Number(latencies[Math.max(0,Math.ceil(p*latencies.length)-1)].toFixed(1)):null;
  const result={checkedAt:new Date().toISOString(),network:rpc.network,endpoint:rpc.endpoint,address:opts.address,requested:samples,succeeded:latencies.length,failed:failures.length,intervalMs:interval,latencyMs:{p50:percentile(.5),p95:percentile(.95),max:percentile(1)},failures,scope:'Serial race() reads. Not a consensus, throughput, write-load, or provider-cost benchmark.'};
  output(result,opts.output);process.exitCode=failures.length?2:0;
} catch(e) {output({checkedAt:new Date().toISOString(),exitCode:2,error:e.shortMessage??e.message},opts?.output);process.exitCode=2;}
