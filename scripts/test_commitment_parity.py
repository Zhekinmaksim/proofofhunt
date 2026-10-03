"""
The client and the contract must compute the same commitment. Always.

If web/commitment.js normalises an answer even slightly differently from
contracts/proof_of_hunt.py, then reveal() rejects the answer the player
actually meant. The commit is spent, the attempt is gone, and from the player's
side nothing explains why: they typed the right answer and the chain said no.

The rule is duplicated because an Intelligent Contract is a single file and
cannot export a module for the frontend to import. This test is what keeps the
duplicate honest, so the duplication is a known cost rather than a latent bug.

    python3 scripts/test_commitment_parity.py

Needs node. If node is missing the test says so and exits non-zero rather than
passing quietly, because a parity test that skips itself is worse than none.
"""

import json
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

sys.path.insert(0, os.path.join(ROOT, "scripts"))
sys.path.insert(0, os.path.join(ROOT, "contracts"))

import fake_genlayer  # noqa: F401  installs the stand-in genlayer module
import proof_of_hunt as poh


# Deliberately awkward: leading and trailing space, internal runs, tabs and
# newlines, mixed case, a checksummed address, unicode, an empty answer, and a
# clue index that is not a single digit.
CASES = [
    ("lo", "cafebabe", "0x1111111111111111111111111111111111111111", 0),
    ("  LO  ", "cafebabe", "0x1111111111111111111111111111111111111111", 0),
    ("Short\tand   Stout", "s", "0xAbCdEf0123456789aBcDeF0123456789AbCdEf01", 3),
    ("multi\nline\nanswer", "0", "0x0000000000000000000000000000000000000001", 11),
    ("2047", "deadbeef00", "0xffffffffffffffffffffffffffffffffffffffff", 10),
    ("utf-8", "salt", "0x2222222222222222222222222222222222222222", 6),
    ("", "salt", "0x3333333333333333333333333333333333333333", 1),
    ("Grüße aus Frankfurt", "ümlaut", "0x4444444444444444444444444444444444444444", 7),
    ("   ", "spaces", "0x5555555555555555555555555555555555555555", 2),
    ("a" * 200, "long", "0x6666666666666666666666666666666666666666", 9),
]

JS_HARNESS = r"""
import { commitmentOf, normaliseAnswer } from "%s";
const cases = %s;
const out = [];
for (const [answer, salt, player, idx] of cases) {
  out.push({
    norm: normaliseAnswer(answer),
    commitment: await commitmentOf(answer, salt, player, idx),
  });
}
process.stdout.write(JSON.stringify(out));
"""


def main():
    js_path = os.path.join(ROOT, "web", "commitment.js")
    if not os.path.exists(js_path):
        print("FAIL web/commitment.js is missing")
        return 1

    try:
        subprocess.run(["node", "--version"], capture_output=True, check=True)
    except (FileNotFoundError, subprocess.CalledProcessError):
        print("FAIL node is not available, so parity could not be checked.")
        print("     Install node and re-run. This test does not skip.")
        return 1

    src = JS_HARNESS % (js_path.replace("\\", "/"), json.dumps(CASES))
    with tempfile.NamedTemporaryFile("w", suffix=".mjs", delete=False) as f:
        f.write(src)
        harness = f.name

    try:
        r = subprocess.run(["node", harness], capture_output=True, text=True)
        if r.returncode != 0:
            print("FAIL node could not run the client module:")
            print(r.stderr.strip()[:600])
            return 1
        js = json.loads(r.stdout)
    finally:
        os.unlink(harness)

    fails = []
    for (answer, salt, player, idx), got in zip(CASES, js):
        want_norm = poh.normalise_answer(answer)
        want_commit = poh.commitment_of(answer, salt, player, idx)
        label = repr(answer[:28]) + ("..." if len(answer) > 28 else "")

        if got["norm"] != want_norm:
            print(f"  FAIL normalise {label}: js {got['norm']!r} != py {want_norm!r}")
            fails.append(label)
        elif got["commitment"] != want_commit:
            print(f"  FAIL commitment {label}: js {got['commitment'][:16]}... "
                  f"!= py {want_commit[:16]}...")
            fails.append(label)
        else:
            print(f"  ok   {label} -> {want_commit[:16]}...")

    print()
    if fails:
        print(f"{len(fails)} case(s) diverge. The client would lose player commits.")
        return 1
    print(f"client and contract agree on all {len(CASES)} cases")
    return 0


if __name__ == "__main__":
    sys.exit(main())
