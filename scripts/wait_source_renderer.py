"""Wait for Studio's renderer to observe a fixture update, including its cache."""
import argparse
import json
import subprocess
import time
from pathlib import Path
from urllib.parse import urlencode
from dryrun_clues import canonicalise

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('state', choices=['original','drifted','missing'])
args = parser.parse_args()
root = Path(__file__).resolve().parents[1]
clue = json.loads((root / 'clues/source-failure-02.json').read_text())['clues'][0]
expected = None if args.state=='missing' else canonicalise((root / f'verification/source-fixture/{args.state}.txt').read_text())
url = 'http://webdriver:4444/render?' + urlencode(dict(url=clue['source_url'],mode='text',waitAfterLoaded='0.0'))
deadline = time.monotonic()+900
previous = None
while time.monotonic()<deadline:
    result = subprocess.run(['docker','exec','genlayer-consensus-worker-1','curl','--max-time','60','-fsS','-D','-',url],capture_output=True,text=True)
    headers, _, body = result.stdout.partition('\n\n')
    status = next((l.split(':',1)[1].strip() for l in headers.splitlines() if l.lower().startswith('resulting-status:')), 'unknown')
    ready = result.returncode==0 and (status=='404' if expected is None else status=='200' and canonicalise(body)==expected)
    state = (status,ready)
    if state!=previous:
        print(json.dumps(dict(fixture=args.state,renderer_status=status,ready=ready,observedAt=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()))),flush=True)
        previous=state
    if ready:
        (root / f'verification/renderer-source-{args.state}.txt').write_text(result.stdout)
        break
    time.sleep(10)
else:
    raise RuntimeError('Renderer still has stale content; do not submit the next judge yet')
