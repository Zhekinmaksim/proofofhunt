"""Summarize real transaction checkpoints without reading private test keys."""
import hashlib
import json
import statistics
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
prefix = sys.argv[1] if len(sys.argv) > 1 else "beta-"
report = {"observedAt": datetime.now(timezone.utc).isoformat(), "sourceSha256": hashlib.sha256((ROOT / "contracts/proof_of_hunt.py").read_bytes()).hexdigest(),
          "networks": {}}
for network in ("local", "studionet"):
    result = {}
    for name in ("prototype", "source", "full"):
        file = ROOT / "verification" / f"{network}-{prefix}{name}.json"
        if not file.exists():
            result[name] = {"complete": False, "note": "not run"}
            continue
        data = json.loads(file.read_text())
        item = {"address": data.get("address"), "account": data["account"], "endpoint": data["endpoint"],
                "chainId": data["chainId"], "race": data.get("race"), "complete": False}
        if name in ("prototype", "full"):
            expected = 2 if name == "prototype" else 12
            plays = data.get("plays", [])
            item["answers"] = [{"idx": p["idx"], "answer": p["answer"], "verdict": p.get("result", {}).get("verdict")} for p in plays]
            item["correctCount"] = sum(p.get("result", {}).get("verdict") == 1 for p in plays)
            item["complete"] = item["correctCount"] == expected and data.get("race", {}).get("state") == 3
        else:
            rows = {c["label"]: c for c in data["calls"]}
            baseline = data.get("failureBaseline", {})
            item["sourceChecks"] = {}
            for label, verdict, pin in (("drifted", 3, 1), ("unreachable-retry", 3, 2), ("restored", 1, 0)):
                row = rows.get(label, {})
                if label == "unreachable-retry" and not row:
                    row = rows.get("unreachable", {})
                snapshot = row.get("snapshot", {})
                commit, player = snapshot.get("commit", {}), snapshot.get("player", {})
                passed = commit.get("verdict") == verdict and commit.get("pin_status") == pin
                if verdict == 3:
                    passed = passed and all(player.get(k) == baseline.get(k) for k in ("attempts_used", "total_attempts", "position", "cleared"))
                else:
                    passed = passed and player.get("position") == 1 and player.get("total_attempts") == 1
                item["sourceChecks"][label] = {"passed": passed, "hash": row.get("hash"), "commit": commit, "player": player}
            item["complete"] = all(c["passed"] for c in item["sourceChecks"].values())
        item["sourceMatches"] = data.get("client", {}).get("contractSha256") == report["sourceSha256"]
        item["complete"] = item["complete"] and item["sourceMatches"]
        judges = [c for c in data["calls"] if c["functionName"] == "judge" and c.get("status") == "FINALIZED" and c.get("execution") == "SUCCESS" and (not c.get("consensusRounds") or "ACCEPTED" in c["consensusRounds"][-1].get("statusChanges", []))]
        item["judges"] = [{k: c.get(k) for k in ("label", "hash", "acceptedSeconds", "finalizedSeconds", "fee", "runtime", "validators", "votes")} for c in judges]
        accepted = [c["acceptedSeconds"] for c in judges if c.get("acceptedSeconds")]
        if accepted:
            item["medianObservedAcceptedSeconds"] = statistics.median(accepted)
        result[name] = item
    result["complete"] = all(result[n]["complete"] for n in ("prototype", "source", "full"))
    report["networks"][network] = result
out = ROOT / f"verification/report-{prefix.rstrip('-') or 'legacy'}.json"
out.write_text(json.dumps(report, indent=2) + "\n")
for network, result in report["networks"].items():
    print(network, {n: result[n]["complete"] for n in ("prototype", "source", "full")})
print(out)
