/** Compare deployed bytes with the reviewed source; never loads signing keys. */
import fs from 'node:fs';
import crypto from 'node:crypto';
import {createClient} from 'genlayer-js';
import {studionet, localnet} from 'genlayer-js/chains';
const network = process.argv[2] ?? 'studionet';
if (!['local','studionet'].includes(network)) throw Error('Expected local or studionet');
const prefix = process.argv[3] ?? 'beta-';
const root = new URL('../', import.meta.url);
const client = createClient({chain: network === 'local' ? localnet : studionet});
const hash = bytes => crypto.createHash('sha256').update(bytes).digest('hex');
const expected = hash(fs.readFileSync(new URL('contracts/proof_of_hunt.py',root)));
const contracts = [];
for (const name of ['prototype','source','full','release']) {
  const file = new URL(`verification/${network}-${prefix}${name}.json`,root);
  if (!fs.existsSync(file)) continue;
  const {address} = JSON.parse(fs.readFileSync(file));
  if (!address) continue;
  const code = await client.getContractCode(address);
  const bytes = Buffer.from(code,'utf8');
  const actual = hash(bytes);
  contracts.push({name,address,actual,matches:actual===expected});
}
fs.writeFileSync(new URL(`verification/${network}-${prefix}code-parity.json`,root),JSON.stringify({expected,contracts},null,2)+'\n');
console.log(contracts);
if (contracts.some(c => !c.matches)) process.exitCode=1;
