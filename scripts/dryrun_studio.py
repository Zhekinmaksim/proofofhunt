"""Check actual Studio renderer windows before authoring a full race.

python3 scripts/dryrun_studio.py clues/race-01.json
Requires the running Studio worker and web.render webdriver service.
This does not replace consensus pin_clue or a real judge transaction.
"""
import hashlib
import json
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlencode

from dryrun_clues import canonicalise, cut_window, MIN_WINDOW_CHARS


def main(spec_path):
    rows = []
    for idx, clue in enumerate(json.loads(Path(spec_path).read_text())["clues"]):
        url = "http://webdriver:4444/render?" + urlencode({
            "url": clue["source_url"], "mode": "text", "waitAfterLoaded": "0.0"
        })
        result = subprocess.run([
            "docker", "exec", "genlayer-consensus-worker-1", "curl",
            "--max-time", "120", "-fsS", "-D", "-", url,
        ], capture_output=True, text=True)
        headers, _, body = result.stdout.partition("\r\n\r\n")
        if not body:
            headers, _, body = result.stdout.partition("\n\n")
        status = next((x.split(":", 1)[1].strip() for x in headers.splitlines()
                       if x.lower().startswith("resulting-status:")), "unknown")
        canon = canonicalise(body)
        window = cut_window(canon, clue["anchor"], clue["window_chars"])
        answer = clue["expected"].strip().lower()
        good = (result.returncode == 0 and status in ("200", "304")
                and canon.count(clue["anchor"].lower()) == 1
                and len(window) >= MIN_WINDOW_CHARS and answer in window)
        row = dict(idx=idx, title=clue["title"], source_url=clue["source_url"],
                   status=status, passed=good, window=window,
                   digest=hashlib.sha256(window.encode()).hexdigest(),
                   anchor_count=canon.count(clue["anchor"].lower()),
                   stderr=result.stderr)
        rows.append(row)
        print(f"[{idx:02}] {'PASS' if good else 'FAIL'} {clue['title']}: status={status}, "
              f"anchors={row['anchor_count']}, chars={len(window)}, answer={answer in window}", flush=True)
    target = Path("verification") / (Path(spec_path).stem + "-renderer.json")
    target.write_text(json.dumps(rows, indent=2) + "\n")
    return 0 if all(r["passed"] for r in rows) else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
