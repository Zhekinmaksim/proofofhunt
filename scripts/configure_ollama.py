"""Configure existing local Ollama validators; never modifies hosted networks."""
import argparse
import json
from pathlib import Path
import urllib.request

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--native', action='store_true', help='Use Mac Ollama on loopback via Lima host forwarding')
parser.add_argument('--model', default='qwen2.5:7b')
parser.add_argument('--temperature', type=float, default=0.1)
args = parser.parse_args()
if not 0 <= args.temperature <= 1:
    raise ValueError('temperature must be between 0 and 1')
root = Path(__file__).resolve().parents[1]

def rpc(method, params):
    req = urllib.request.Request('http://localhost:4000/api',
        data=json.dumps(dict(jsonrpc='2.0', id=1, method=method, params=params)).encode(),
        headers={'Content-Type':'application/json'})
    with urllib.request.urlopen(req, timeout=60) as response:
        result = json.load(response)
    if 'error' in result:
        raise RuntimeError(result['error'])
    return result['result']

validators = rpc('sim_getAllValidators', [])
for validator in validators:
    if validator['provider'] != 'ollama':
        continue
    config = dict(validator['config'])
    # CLI 0.39.1's provider schema caps these settings and requires the typo.
    # The correctly spelled key is also needed by Ollama itself.
    config.update(num_ctx=4096, num_predict=512, temperature=args.temperature, temprature=args.temperature,
                  num_gpu=16 if args.native else 0)
    plugin_config = dict(validator['plugin_config'])
    plugin_config['api_url'] = 'http://host.lima.internal:11435' if args.native else 'http://ollama:11434'
    rpc('sim_updateValidator', [validator['address'], validator['stake'], 'ollama',
                               args.model, config, 'ollama', plugin_config])
updated = rpc('sim_getAllValidators', [])
for validator in updated:
    validator.pop('private_key', None)
target = root / 'verification' / ('local-validators-metal.json' if args.native else 'local-validators-cpu.json')
target.write_text(json.dumps(updated, indent=2) + '\n')
runtime = dict(provider='ollama', model=args.model, backend='Metal' if args.native else 'Docker CPU',
               options=dict(num_ctx=4096, num_predict=512, temperature=args.temperature,
                            num_gpu=16 if args.native else 0), validators=len(updated))
(root / 'verification/runtime-local.json').write_text(json.dumps(runtime, indent=2) + '\n')
print(f"Configured {len(updated)} local validators: {runtime['backend']}")
