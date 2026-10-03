"""Change only the disposable Gist created for this project's source test.

Usage: python3 scripts/source_fixture.py original|drifted|missing
The Gist remains in place so the same source URL can be restored after a 404.
Requires an authenticated GitHub CLI. No contract transactions are sent.
"""

import argparse
import json
import re
import subprocess
import time
import urllib.error
import urllib.request
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "verification" / "source-fixture"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("state", choices=["original", "drifted", "missing"])
    args = parser.parse_args()
    gist = json.loads((FIXTURE / "gist.json").read_text())
    gist_id = gist["id"]
    if not re.fullmatch(r"[0-9a-f]{32}", gist_id):
        raise ValueError("invalid fixture gist id")
    if gist["description"] != "Proof of Hunt disposable source-drift verification fixture":
        raise ValueError("this is not the disposable source fixture")
    spec = json.loads((ROOT / "clues" / "source-failure-02.json").read_text())
    url = spec["clues"][0]["source_url"]
    if f"/{gist_id}/raw/source.txt" not in url:
        raise ValueError("source URL does not refer to this fixture")

    expected = None if args.state == "missing" else (FIXTURE / f"{args.state}.txt").read_text()
    entry = None if expected is None else {"content": expected}
    result = subprocess.run(
        ["gh", "api", "--method", "PATCH", f"/gists/{gist_id}", "--input", "-"],
        input=json.dumps({"files": {"source.txt": entry}}),
        text=True, capture_output=True, check=True,
    )
    updated = json.loads(result.stdout)
    print(f"Updated disposable fixture to {args.state}; waiting for its live URL.", flush=True)
    deadline = time.monotonic() + 600
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=30) as response:
                observed = response.read().decode()
            ready = expected is not None and observed == expected
        except urllib.error.HTTPError as error:
            if error.code != 404:
                raise
            ready = expected is None
        if ready:
            record = {"state": args.state, "url": url,
                      "revision": updated["history"][0]["version"],
                      "observedAt": datetime.now(timezone.utc).isoformat()}
            history_path = FIXTURE / "mutation-history.json"
            history = json.loads(history_path.read_text()) if history_path.exists() else []
            history.append(record)
            history_path.write_text(json.dumps(history, indent=2) + "\n")
            print(json.dumps(record))
            return
        time.sleep(10)
    raise RuntimeError("raw source has not changed yet; do not judge against stale CDN content")


if __name__ == "__main__":
    main()
