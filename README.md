# Proof of Hunt

A twelve-clue onchain race on GenLayer: commit an answer, reveal it, and ask
validators to judge it against the live web. The earliest correct final-clue
commit wins, subject to the published reveal and judging deadlines.

**Protocol v2 public beta on Studionet. No prizes.** V2 fixes the duplicate
advancement and finalization blockers found in the original prototype. It has
not received an independent security audit. Existing v1 deployments are obsolete
and unsafe for competition; their successful traces are historical evidence only.

Start with [RUN.md](RUN.md) for the rules, setup, verification and deployment
procedure. The active address and endpoint are configured in
[`web/config.js`](web/config.js); an empty address means a verified deployment
has not yet been selected. Never substitute a historical v1 address.

```sh
python3 scripts/test_race.py
python3 scripts/test_race_v2.py
python3 scripts/test_canon_parity.py
python3 scripts/test_commitment_parity.py
python3 scripts/test_dryrun.py
npm --prefix scripts ci
node scripts/test_monitor.mjs
npm --prefix web ci
npm --prefix web test
npm --prefix web run build
python3 -m http.server 8000 --directory web/dist
```

Open `http://localhost:8000/` rather than loading browser modules with `file://`.
The client supports wallet transactions, live race state and leaderboard, and
backup export/import. End-to-end signing and deployed-site checks are recorded
separately in RUN.md. Player secrets need a separate backup; clearing browser storage can lose a salt
and prevent reveal. See the client workflow in RUN.md.

Current v2 evidence includes **81 passing contract checks**, **14 client tests**,
and completed two-clue prototypes on local Studio and Studionet. An isolated
signer also completed join/commit/reveal/judge through the actual SDK EIP-1193
provider path; browser extension approval UI remains a separate check.

One v2 Studionet `judge` reached ACCEPTED in **20.485 s** and FINALIZED in
**53.602 s**. Its reported token usage is estimated at **$0.012422**, excluding
unreported inference and infrastructure costs; this is not an invoice. See
[`verification/judge-cost-beta.json`](verification/judge-cost-beta.json) and the
current submission notes in RUN.md. Pending full-course, source-recovery and
public deployment checks are not implied by the prototype results.

V2 permits one pending commitment per player, a 24-hour reveal period, a
seven-day judging period from commitment, and a 30-day race. Limits are 128
players and 8,192 commitments. Recovery is deterministic; the owner cannot
selectively discard claims or replace sealed sources.

[Operations and recovery procedures](verification/production-ops.md) include
read-only monitoring and a bounded RPC latency smoke. Both local Studio and Studionet passed 12/12 correct answers and the controlled
DRIFTED → UNREACHABLE → restored-source path. See
[`verification/report-beta.json`](verification/report-beta.json). New verification
uses `beta-*` checkpoint names so v1 results are not counted as v2 results.

Configured source repository: [Zhekinmaksim/proofofhunt](https://github.com/Zhekinmaksim/proofofhunt).
Live beta: [proofofhunt-rouge.vercel.app](https://proofofhunt-rouge.vercel.app).
Vercel serves the wallet client over HTTPS. `proofofhunt.quest` is the intended
custom domain; its DNS setup is handled by the owner.

The Remotion explainer is `video/out/proof-of-hunt.mp4`. Soundtrack usage rights
were confirmed by the owner. The execution video and older transaction records
must retain their protocol/version labels.
