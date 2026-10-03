"""Reproduce the deployed tribunal prompt against local Ollama, without a transaction."""
import argparse
import ast
import json
import re
import time
import urllib.request
from pathlib import Path

root = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--model', default='qwen2.5:14b')
args = parser.parse_args()
clue = json.loads((root / 'clues/race-01.json').read_text())['clues'][11]
trace = json.loads((root / 'verification/local-full.json').read_text())
window = next(c['outputs']['0'] for c in trace['calls'] if c['label'] == 'judge[11]')
tree = ast.parse((root / 'contracts/proof_of_hunt.py').read_text())
expressions = [node.value for node in ast.walk(tree) if isinstance(node, ast.Assign)
               and any(isinstance(t, ast.Name) and t.id == 'prompt' for t in node.targets)]
if len(expressions) != 1:
    raise ValueError('Expected one tribunal prompt')
prompt = eval(compile(ast.Expression(expressions[0]), '<tribunal prompt>', 'eval'), {},
              dict(riddle=clue['riddle'], form=clue['answer_form'], window=window, answer=clue['expected']))
(root / 'verification/treemap-tribunal-prompt.txt').write_text(prompt + '\n')
request = dict(model=args.model, messages=[dict(role='user', content=prompt)], stream=False,
               format='json', options=dict(temperature=0, num_ctx=4096, num_predict=512, num_gpu=16))
started = time.monotonic()
req = urllib.request.Request('http://127.0.0.1:11435/api/chat',
                             data=json.dumps(request).encode(), headers={'Content-Type':'application/json'})
with urllib.request.urlopen(req, timeout=1200) as response:
    result = json.load(response)
content = result['message']['content']
out = dict(model=args.model, wallSeconds=time.monotonic()-started, result=json.loads(content),
           options=request['options'], evalCount=result.get('eval_count'), evalDuration=result.get('eval_duration'))
payload=json.dumps(out, indent=2)+'\n'
(root / 'verification/treemap-model-smoke.json').write_text(payload)
model_name=re.sub(r'[^a-zA-Z0-9_.-]', '-', args.model)
(root / 'verification' / f'treemap-model-smoke-{model_name}.json').write_text(payload)
print(json.dumps(out, indent=2))
if out['result'].get('verdict') != 'correct':
    raise SystemExit('Local model did not support the known answer; do not alter the clue to fit it')
