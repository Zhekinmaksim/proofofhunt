# Public beta operations

The intended release is a **public beta on Studionet, without prizes**. Earlier v1 verification proves the ordinary 12-clue path, not the security of v2. Deploy and verify the corrected v2 contract separately; never advertise a v1 address as fixed. Existing contracts are immutable and cannot receive a source-code patch.

## One-shot monitor

Install the pinned SDK with `npm --prefix scripts ci`, then run:

```sh
node scripts/monitor_race.mjs --network studionet --address 0xYOUR_CONTRACT --output verification/monitor-latest.json
```

The command uses no account, wallet, private key, signature, or write method. It reads `race()` and at most 200 commits at 2,500 ms intervals, then reads race state again. HTTP requests abort after 15 seconds. Configure `--max-commits 500`, `--interval-ms 1000`, or `--timeout-ms 20000` when necessary. Bounds prevent accidental unbounded or rapid polling. The CLI itself does not remain in the background. The repository includes
`.github/workflows/monitor.yml`, scheduled hourly at minute 17 UTC with manual
dispatch, using `web/config.js` for the address, 2,500 ms intervals, at most 200
commits and a 15-minute job timeout. It becomes active after the workflow is
pushed to the default branch and GitHub Actions is enabled. No Codex automation
was created. Check Actions run status/artifacts for failures or incomplete scans.
`.github/workflows/check.yml` runs repository checks on pushes and pull requests.

Exit status: **0** means the scanned state has no identified alert; **1** means review a listed finding; **2** means an RPC/configuration failure or incomplete scan. A partial page (`--start-cid`) cannot declare the whole race healthy. Concurrent changes can make a scan incomplete; run again after pending transactions settle. RPC calls are independent snapshots, not an atomic audit.

Findings cover legacy protocol without deadline recovery, pending commit deadlines, past race closing time, recorded DRIFTED/UNREACHABLE results, and provisional winners. A provisional winner is expected until earlier final-clue claims are resolved; it is an attention item, not proof of a bug. A fully scanned provisional state with no visible blocker requires review of finalization.

**Source status is the last stored judge observation.** Read-only monitoring does not fetch each source through validators, refresh a pin, or prove that a currently unjudged page is reachable. Terminal resolved/expired attempts do not create stale source alarms. Race FINAL or CANCELLED is terminal, not an outage.

## Incident procedures

- **RPC failure:** preserve the JSON error and check the configured endpoint/chain. Inspect any previous transaction hash before retrying a write. Do not generate replacement commits solely because a browser timed out. Retrying reads is safe; repeated writes can create different race outcomes.
- **DRIFTED:** retain the stored pin digest, current judge receipt and affected cid. A source owner may restore the original page if authorized. Do not silently change a sealed clue, stored pin, or answer to make it pass. After CDN/renderer cache expiry, a player can retry the same eligible revealed commitment. Confirm that attempts were not charged.
- **UNREACHABLE:** check origin availability and caching separately from RPC health. Allow a bounded recovery period within the contract deadline. A transient fetch or model failure is not an incorrect player answer. Do not retry continuously.
- **Expired commitment:** verify current chain state and the appropriate `reveal_deadline` or `judge_deadline`; then submit `expire(cid)` through the application/wallet when eligible. Confirm terminal verdict 4 and reread race/player state. Monitor clock comparisons use host UTC seconds; the contract decides eligibility using its own execution time.
- **Provisional winner (state 2):** inspect all earlier final-clue cids listed as blockers. Complete legitimate reveals/judgments within deadlines or expire eligible claims. Confirm state 3 before presenting a final winner. Do not substitute verdict completion time for commit order.
- **Race past `closes_at`:** review current pending claims and `cancel_expired_race()` eligibility. Confirm CANCELLED (state 4) or the final winner after the transaction settles. The monitor never submits this action automatically.
- **Model disagreement or malformed output:** retain the consensus history, model identifiers, usage and original input. A weak model returning the wrong answer is not grounds to rewrite a valid clue. Read the latest finalized state: a FINALIZED transaction envelope alone does not prove the consensus accepted its state transition.

For any state-changing recovery: persist the transaction hash, wait for accepted/finalized consensus and successful execution, then reread affected views. Do not expose salts from unrevealed player attempts, keys, credentials or raw backend logs in tickets. Public verification artifacts should contain only intentionally public evidence.

## Read latency smoke

```sh
node scripts/load_smoke.mjs --network studionet --address 0xYOUR_CONTRACT --samples 10 --interval-ms 2500 --output verification/read-load-smoke.json
node scripts/test_monitor.mjs
```

The smoke performs sequential unsigned `race()` reads, maximum 100 samples and minimum 500 ms pause. It reports successful-read p50/p95/max and every failed sample, exiting 2 for any failure. It measures API read latency only. It does **not** establish concurrent-player capacity, write throughput, consensus reliability or resilience under a source outage. Do not run high-rate load tests on shared Studionet without operator authorization. Local adversarial contract tests and live two-player/recovery scenarios remain separate release gates.

## Costs, hosting and evidence

Studionet is a development environment. Simulator gas receipts are not production invoices; local Ollama has hardware/electricity costs even when provider billing is zero. The v2 recorded $0.012422 judge figure (`judge-cost-beta.json`) is an estimate of reported model token usage under stated public rates, excludes unreported/cancelled work and infrastructure, and is not a guaranteed future price. Provider/model changes can change latency, consensus behavior and cost. Capture actual network, model mix, receipt, timestamp and finalized state with every new deployment.

GitHub source and Vercel hosting do not make the shared Studionet a production SLA. Keep the public-beta/no-prizes disclosure visible. If RPC is unavailable, the UI must show unavailable data rather than a fake leaderboard or an optimistic verdict. Browser storage is not a backup: offer player salt export/import before irreversible clearing of site data.

The owner confirmed soundtrack usage rights for this project. The soundtrack
may remain in the public Remotion render. Preserve that authorization with the
release records; separately verify rights for any replacement audio introduced
later.
