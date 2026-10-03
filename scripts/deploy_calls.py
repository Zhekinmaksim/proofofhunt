"""
Turn the clue file into the exact sequence of contract calls that opens a race.

This prints call payloads rather than sending them. That is deliberate: the
GenLayer client surface moves between releases, and a script that hardcodes it
rots quietly and then fails halfway through authoring, leaving a half-built
clue chain on chain. Payloads paste into Studio, into genlayer-js, or into
whatever the client looks like this month, and they cannot go stale.

    python3 scripts/deploy_calls.py clues/race-01.json          # human readable
    python3 scripts/deploy_calls.py clues/race-01.json --json   # machine readable

The order matters and the contract enforces it:

    1. deploy(title)
    2. add_clue(...)   once per clue, in order. Index is assignment order.
    3. pin_clue(i)     once per clue. Non-deterministic, may fail, retryable.
    4. open_race()     refuses while any clue is unpinned.

Step 3 is the one that costs consensus and the one that can fail. That is the
point of it: a clue whose source cannot be agreed on by independent validators
cannot enter a race, and you find that out here rather than from a player whose
correct answer came back UNDETERMINED.
"""

import json
import sys


def calls(spec):
    out = [{
        "step": "deploy",
        "method": "__init__",
        "args": {"title": spec["race_title"]},
        "note": "deploy the contract, then use its address for everything below",
    }]

    for i, c in enumerate(spec["clues"]):
        out.append({
            "step": f"add_clue[{i:02d}]",
            "method": "add_clue",
            "args": {
                "title": c["title"],
                "riddle": c["riddle"],
                "source_url": c["source_url"],
                "anchor": c["anchor"],
                "window_chars": int(c["window_chars"]),
                "answer_form": c["answer_form"],
                "answer_pattern": c["answer_pattern"],
                "hint": c["hint"],
            },
            "note": "deterministic and cheap, no web fetch",
        })

    for i, c in enumerate(spec["clues"]):
        out.append({
            "step": f"pin_clue[{i:02d}]",
            "method": "pin_clue",
            "args": {"idx": i},
            "note": (
                f"fetches {c['source_url']} and agrees on the window at "
                f"anchor {c['anchor']!r}. If this fails consensus the source is "
                f"unstable across validators - replace it, do not retry forever"
            ),
        })

    out.append({
        "step": "open_race",
        "method": "open_race",
        "args": {},
        "note": "one way door, the clue chain is sealed after this",
    })
    return out


def main(path, as_json=False):
    spec = json.load(open(path))
    seq = calls(spec)

    if as_json:
        json.dump(seq, sys.stdout, indent=2, ensure_ascii=False)
        print()
        return 0

    print(f"\n{spec['race_title']}")
    print(f"{len(spec['clues'])} clues, {len(seq)} calls\n")
    for c in seq:
        print(f"--- {c['step']}  ->  {c['method']}")
        if c["args"]:
            for k, v in c["args"].items():
                v = json.dumps(v, ensure_ascii=False)
                if len(v) > 110:
                    v = v[:107] + '..."'
                print(f"      {k} = {v}")
        print(f"      # {c['note']}")
        print()

    expected = [c.get("expected", "") for c in spec["clues"]]
    if all(expected):
        print("After open_race, verify the chain end to end with these answers:")
        print("  " + ", ".join(f"{i}:{a}" for i, a in enumerate(expected)))
        print("\nSubmit each as commit -> reveal -> judge and confirm the verdict")
        print("is CORRECT, not UNDETERMINED. An UNDETERMINED on a known-good")
        print("answer means the window does not contain the material, which is a")
        print("clue authoring bug, not a chain problem.\n")
    return 0


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("-")]
    sys.exit(main(args[0] if args else "clues/race-01.json", "--json" in sys.argv))
