"""Diagnostic reproduction of known prototype bugs; not a release pass test.

Uses the deterministic fake SDK only. It asserts the current vulnerable
behaviour so a future fix should replace these assertions with regressions.
"""
import contextlib
import io
import importlib.util
import sys
from pathlib import Path

with contextlib.redirect_stdout(io.StringIO()):
    import test_race as t

spec = importlib.util.spec_from_file_location("proof_of_hunt_v1", Path(__file__).resolve().parents[1] / "verification/proof_of_hunt-v1.py")
poh = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = poh
spec.loader.exec_module(poh)
t.poh = poh
fx = t.fx
c = t.build_race(2)
fx.set_sender(t.ALICE)
c.join("alice")
first = t.play(c, t.ALICE, 0, "1974", "a")
second = t.play(c, t.ALICE, 0, "1974", "b")
for cid in (first, second):
    fx.set_verdicts(fx.verdict("correct"))
    c.judge(cid)
player = c.player(fx.Address(t.ALICE))
print("Duplicate clue-0 commits:", {"position": player["position"],
      "finished": player["finished"], "race_state": c.race()["state"]})
assert player["position"] == 2 and player["finished"]

c = t.build_race(2)
for who in (t.ALICE, t.BOB):
    fx.set_sender(who)
    c.join(who[-4:])
    cid = t.play(c, who, 0, "1974")
    fx.set_verdicts(fx.verdict("correct"))
    c.judge(cid)
fx.set_sender(t.ALICE)
c.commit(1, poh.commitment_of("1974", "withheld", t.ALICE, 1))
cid = t.play(c, t.BOB, 1, "1974")
fx.set_verdicts(fx.verdict("correct"))
c.judge(cid)
print("Earlier unrevealed final commit:", {"race_state": c.race()["state"],
      "winner": c.race()["winner"], "state_won": poh.STATE_WON,
      "state_final": poh.STATE_FINAL})
assert c.race()["state"] == poh.STATE_WON
fx.set_sender(t.ALICE)
c.reveal(2, "1974", "withheld")
fx.set_verdicts(fx.verdict("incorrect"))
c.judge(2)
print("Earlier claim now INCORRECT but race still provisional:",
      {"verdict": c.commits[2].verdict, "race_state": c.race()["state"]})
assert c.commits[2].verdict == poh.V_INCORRECT
assert c.race()["state"] == poh.STATE_WON
print("Advancement and both finalization blockers reproduced locally. No hosted transactions sent.")
