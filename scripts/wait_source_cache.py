"""Wait out the observed 300-second public-source cache before a hosted judge."""
import argparse
import json
import time
from datetime import datetime, timezone
from pathlib import Path

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('state', choices=['original','drifted','missing'])
parser.add_argument('--seconds', type=int, default=330)
args = parser.parse_args()
path = Path(__file__).resolve().parents[1] / 'verification/source-fixture/mutation-history.json'
record = json.loads(path.read_text())[-1]
if record['state'] != args.state:
    raise SystemExit('Fixture is not in the expected state')
ready_at = datetime.fromisoformat(record['observedAt']).timestamp() + args.seconds
print(f'Waiting for {args.state} cache expiry at {datetime.fromtimestamp(ready_at, timezone.utc).isoformat()}', flush=True)
while time.time() < ready_at:
    if json.loads(path.read_text())[-1] != record:
        raise SystemExit('Fixture changed during the cache wait')
    time.sleep(min(10, max(0, ready_at-time.time())))
print('Cache wait complete; actual contract result must still be checked.', flush=True)
