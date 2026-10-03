# Proof of Hunt

An onchain quest race on GenLayer. Twelve clues, no stored answer key, a tribunal
of validators judging free text against the live web, and the first to the end
wins.

**Current release: protocol v2 public beta on Studionet, without prizes.**
The three contract blockers found in v1 are fixed in the current source.
A successful v1 trace is not evidence that the new source has passed live checks.
All v1 contract addresses below are obsolete and unsafe for competition.
The active deployment is selected only in `web/config.js` after v2 verification;
an empty address deliberately disables play until that step is complete.

This file covers the rules, deployment and verification. The current release
limits and recovery policy are below. It is not an independent security audit.

---

## What is here

```
contracts/proof_of_hunt.py    the Intelligent Contract, the whole game
clues/race-01.json            the authored clue chain for race 01
scripts/
  course.py                   the map: relief model, terrain, course geometry
  dryrun_clues.py             check clue sources before they cost anything
  deploy_calls.py             turn the clue file into an ordered call list
  dryrun_studio.py            check windows through the actual Studio renderer
  live_race.mjs               send real calls, checkpoint hashes, verify state
  start_studio.sh             start the compatible local services without reset
  configure_ollama.py         configure existing local Ollama validators
  source_fixture.py           mutate only the disposable source-test Gist
  wait_source_renderer.py     wait until local web.render sees the mutation
  wait_source_cache.py        wait out the observed hosted-source cache
  sync_clues.py               update both static pages from race-01.json
  summarize_verification.py   summarize public transaction checkpoints
  check_deployed_code.mjs     compare deployed source bytes with this archive
  monitor_race.mjs            bounded unsigned state and deadline monitoring
  load_smoke.mjs              low-rate unsigned RPC latency measurement
  test_monitor.mjs            monitoring state/boundary regression checks
  render_demo.py              assemble real UI captures, with waits omitted
  package_project.py          archive source, evidence, and demos without keys
  make_brand.py               regenerate every brand asset
  inline_assets.py            embed fonts and the play map into the pages
  export_course_ts.py         export the course to the video as TypeScript
  fit_music.py                cut the soundtrack and fit the scene timing to it
  fake_genlayer.py            a stand-in genlayer module, for local tests
  test_race.py                deterministic game and security regression checks
  test_canon_parity.py        guards the duplicated canonicalisation rules
  test_commitment_parity.py   guards the duplicated commitment rule
video/                        the one-minute Remotion video, see video/README.md
  out/proof-of-hunt.mp4       rendered: 1920x1080, 30 fps, 60 s, yuv420p
web/
  index.html                  the landing page
  play.html                   the play view
  commitment.js               the commitment rule, shared and tested
  config.js                   active verified v2 address and network endpoints
  fonts/                      the three self-hosted families, OFL
  brand/                      mark, favicons, social card, course.svg
```

Build with `npm --prefix web ci && npm --prefix web run build`. Serve the
allowlisted output with `python3 -m http.server 8000 --directory web/dist`, then
open `http://localhost:8000/`. The wallet client uses JavaScript modules;
opening the HTML with `file://` is not the supported workflow.

---

## Prerequisites

- Python 3.11 or newer for the scripts
- Outbound network access for `dryrun_clues.py` (it fetches the clue sources)
- Node 20+, Docker, and GenLayer CLI for real Studio tests. Run
  `npm --prefix scripts ci` for the pinned integration SDK (`genlayer-js 1.1.8`).
- `pip install pillow cairosvg` only if you want to regenerate brand assets.
  Neither is needed to run the contract, the tests or the site.

---

## Run the tests

```
python3 scripts/test_race.py
python3 scripts/test_race_v2.py
python3 scripts/test_canon_parity.py
python3 scripts/test_commitment_parity.py     # needs node
python3 scripts/test_dryrun.py               # source-gate regression checks, offline
node scripts/test_monitor.mjs                # operational alert regressions
```

`test_race.py` exercises the deterministic half of the contract against a fake
`genlayer` module: commit ordering, reveal binding, attempt accounting,
advancement, the winner rule, finalisation. Consensus behaviour is deliberately
out of scope here - that gets tested on Studio - but everything tested here is
code where a bug produces a **wrong race result** rather than a failed
transaction, which is why it is worth testing off chain at all.

`test_commitment_parity.py` exists for the same reason in the other direction.
If `web/commitment.js` normalises an answer even slightly differently from the
contract, `reveal()` rejects the mismatched opening. The player must recover
the original answer and salt before the reveal deadline; an unrevealed expiry
consumes an attempt. It checks
ten awkward cases including unicode, tabs, newlines, empty input and a
checksummed address. It does not skip when node is missing, it fails, because a
parity test that skips itself is worse than none.

`test_canon_parity.py` exists because the canonicalisation rules are duplicated
between the contract and the dry-run tool. An Intelligent Contract is a single
file and cannot import a shared module, so duplication is unavoidable; silent
drift is not. If these two ever disagree, the dry run starts approving clues the
chain will reject, which is worse than having no dry run.

---

## Deploying a race

The order is fixed and the contract enforces it.

### 1. Dry run the clues

```
python3 scripts/dryrun_clues.py clues/race-01.json
```

For each clue this checks: the source is reachable, the anchor is on the page,
the anchor is unique, the window is long enough to judge against, **the answer
is actually inside the window**, the answer matches its own pattern, and the
anchor does not leak the answer.

This is not the authority on whether a clue works - `pin_clue` on chain is, and
only it can be, because the digest depends on what GenVM's renderer makes of a
page rather than on what an HTTP client on your laptop makes of it. What the dry
run catches is the cheap class of mistakes, for free.

Fetch errors must be diagnosed before changing a clue: proxy-wide `403` or DNS
failures may be local egress restrictions. A `403` on just one source may be a
source policy instead. Run this check with ordinary outbound HTTPS. Duplicate
anchors are failures, including when the first occurrence happens to contain
the answer.

It earns its keep. It caught the BIP-39 clue asking for the wordlist size, 2048,
which does not appear on the page at all - the page says each group of eleven
bits encodes a number from 0 to 2047. The tribunal would have returned
UNDETERMINED on the correct answer, forever, and the only way to find out would
have been a confused player.

### 2. Generate the call sequence

```
python3 scripts/deploy_calls.py clues/race-01.json
python3 scripts/deploy_calls.py clues/race-01.json --json
```

This prints payloads rather than sending them, so it cannot rot when the client
library changes. Paste into Studio, feed to genlayer-js, whatever you use.

### 3. Deploy, author, pin, open

```
deploy(title)          the contract
add_clue(...)          once per clue, in order, deterministic and cheap
pin_clue(i)            once per clue, NON-deterministic, may fail, retryable
open_race()            refuses while any clue is unpinned
```

**`pin_clue` is the important step and the one that can fail.** It runs Stage A
against the clue's source and records the digest the tribunal agreed on. The
author does not supply that digest and cannot: it depends on GenVM's renderer.
The chain derives it. Confirm accepted consensus, successful execution and the
stored pinned state; a finalized transaction envelope alone does not prove a
state change. Agreement during pinning does not guarantee future availability.

That turns the central technical risk of the project - web fetch diverging
between validators - from a checklist item into a gate. A clue that cannot be
pinned cannot enter a race. If `pin_clue` fails consensus, replace the source;
do not retry it forever.

### 4. Verify before announcing

Run the whole chain yourself with the known answers printed by
`deploy_calls.py`. Submit each as commit, reveal, judge. Confirm the verdict is
CORRECT and not UNDETERMINED. Diagnose any failure using the stored pin status,
rendered window, model output and consensus history. A missing answer in the
window is a clue bug; malformed model output or validator disagreement is not
fixed by rewriting an otherwise valid clue.

---

## Playing, in three transactions

```
commit(clue_idx, commitment)     deterministic. Assigns the commit id.
                                 THIS is the moment the race is judged by.
reveal(cid, answer, salt)        deterministic. Binds the answer to that commit.
judge(cid)                       non-deterministic. Slow, may fail, retryable.
                                 Anyone may call it, on anybody's commit.
```

Splitting these is not ceremony, it is the mechanism that makes unreliable web
fetch survivable. If `judge` fails because two validators fetched different
bytes, the transaction reverts and the commit from step one - with its id, its
ordering, its claim on the race - is untouched. A validator disagreement preserves the commitment, but a retry must finish
within the published judging deadline.

The commitment is `hash(normalised_answer | salt | player | clue_idx)`, bound to
the player and the clue so it cannot be lifted from the mempool and replayed.
Use the `commitment_preview` view rather than reimplementing the normalisation
rules and discovering the mismatch after committing.

---

## How the race is decided

**The winner is the earliest correct commit by commit id, not the first verdict
to come back.** Commit ids are positions in an append-only list, so they are
exactly the order the chain accepted commitments in.

Three consequences worth understanding before changing anything:

- A correct verdict arriving first does not win. The race stays at `WON`
  (provisional) while any lower-id commit on the final clue is still awaiting a
  verdict, and only reaches `FINAL` when none is. An earlier commit judged later
  takes the win back.
- **Ties are impossible by construction.** Two commits cannot share an id. No
  ad hoc tiebreak rule is needed, and adding one would only be extra surface.
- Judging is still allowed after `FINAL`. A player who was mid-race when
  somebody won is entitled to a verdict on the answer they already paid to
  commit, and it cannot change the outcome, because anything still unjudged is
  unable to displace the fixed winner. V2 still enforces the original judging
  deadline and rejects judging after cancellation.

`UNDETERMINED` is a first-class verdict and never counts as wrong: no attempt
consumed, no position moved, same revealed commit retryable before its judging
deadline. A long outage can exhaust that deadline; it cannot be retried forever.

### V2 deadlines, limits and cancellation

- One pending commitment per player prevents concurrent attempts from advancing
  the same clue twice. Reveal and judge also require the current clue position.
- Reveal within **24 hours from commit**. An unrevealed commitment can be
  expired by anyone after its deadline and consumes one attempt. This bounds
  withheld claims; expiry does not reveal a missing salt.
- Judge within **seven days from commit**, not seven days from reveal. Expiry
  of an already revealed unresolved commitment is free and releases the player
  to try again if the race remains open. UNDETERMINED itself is also free.
- A race closes **30 days after opening**. Both per-commit deadlines are capped
  by this time. Anyone may call `cancel_expired_race()` when eligible: it first
  resolves finalization and otherwise sets CANCELLED.
- The hard limits are **128 players and 8,192 commitments**. At most six
  chargeable failed attempts are allowed on a clue. These bounds limit work;
  they do not establish throughput or an SLA.

`expire(cid)` and cancellation follow contract rules. The owner cannot choose
which competitor to expire, extend individual deadlines, or replace a sealed
source. Terminal incorrect and expired resolutions recheck finalization.
A later CORRECT verdict is provisional while an earlier eligible final-clue
claim remains unresolved. FINAL is state 3; CANCELLED is state 4; EXPIRED is
verdict 4. Read the actual stored deadlines instead of guessing from local time.

---

## Authoring new clues

Four rules, each learned the hard way:

1. **The anchor must not contain the answer.** Anchors are public in the `clue`
   view. An anchor like "returns the number of decimals" is a giveaway.
2. **The anchor sits immediately before the material.** The window runs forward
   from the anchor. On the RFC 1 clue this bit: the author's name is above the
   line "Request for Comments: 1", not below it.
3. **Constrain the answer form.** The `answer_pattern` regex is checked on chain
   before any model is called. It is the cheap deterministic filter that keeps
   the answer space near binary and stops a player burning tribunal budget on an
   essay.
4. **Prefer sources that cannot change.** Standards frozen on publication,
   historical records, specification files nobody has touched in years. A page
   that drifts does not produce a wrong verdict - it produces UNDETERMINED and
   costs the player nothing - but it does waste consensus.

The source URL is public. It has to be, it is on chain, and claiming otherwise
would be exactly the gap between claimed behaviour and implementation that gets
submissions rejected. The race is about solving faster with the same
information, not about privileged information. Say so plainly in the submission.

---

## The practice clue

The "Try a clue" section on the landing page runs a working miniature of the
three stages, judged client-side. It exists because the page previously
explained the game without ever letting anyone play it, and because the
tribunal - the most unusual thing in the project - was described in prose and
never shown.

Two details in it are load-bearing and should survive any redesign:

- The three validators return **three differently worded sentences and one
  identical verdict.** That is the equivalence principle made visible: consensus
  compares the verdict enum and the source digest, and ignores the prose. A
  reader gets the whole argument in one glance.
- The "replay with the source unreachable" button demonstrates UNDETERMINED,
  including the line that no attempt is consumed. This is the design decision
  most likely to be questioned in review and the hardest to explain in words.

Clue zero itself is a properly formed clue by the four authoring rules, and its
source is real: Kleinrock's own page at `lk.cs.ucla.edu/internet_first_words.html`,
anchored at "the transmission itself was simply to", which sits immediately
before the material and does not leak the answer. If you ever want a
thirteenth clue, it is already written.

The judging is scripted, not onchain, and the copy on the page says so in the
first sentence. Keep that sentence.

---

## The landing page and the palette

The palette is not designed, it is quoted. **ISOM** is the IOF's printing
standard for orienteering maps, and it assigns every colour a fixed job: blue is
water, yellow is open land, green is vegetation, brown is landform, black is
paths and rock, and purple is the course, overprinted last on top of all of it.
The spec gives CMYK for offset printing; `scripts/course.py` documents each mix
and why the screen value differs from a naive conversion.

One rule follows and governs the whole page: **yellow is ground, purple is the
course.** Yellow fills surfaces the way open land fills a map. Purple marks only
what belongs to the race: the live flag, the button, the open clue, the leader.
Nothing else is ever purple. White is not empty either. On a real map white is
runnable forest, the default state of the ground, which is why a printed sheet
is mostly white and why this page is too.

An earlier draft ran acid lime on near black and justified it with a story about
night orienteering. The story did not change the fact that dark plus a neon
accent is the default every crypto landing page reaches for. It was replaced.

### The map

`scripts/course.py` draws a real ISOM sheet, not an abstraction of one. The
thing that separates the two is **density**. A printed sheet carries brown
contour lines across its entire surface, dozens of them, thin and nested, plus a
track network and small point symbols scattered everywhere. A map made of a few
large rounded shapes is a picture of a map, and it reads as a children's
illustration however accurate the colours are. That was the note that produced
this version.

- **The ground is modelled, not drawn.** A height field built from six smooth
  bumps and hollows is sampled on a grid and its iso-lines extracted by marching
  squares, then chained into polylines. Nesting, spacing, and the way lines
  crowd on steep ground come out on their own, because they are consequences of
  a surface rather than decisions about a drawing. Every fifth line is an index
  contour and prints heavier, exactly as on paper.
- **Point features carry the scale below the contours.** Boulders, knolls, pits
  and crags on a seeded lattice, culled wherever they would collide with a
  control circle. Their absence is most of what made earlier drafts look like a
  toy.
- **Vegetation and open land are many and small**, not few and large, and every
  outline is generated: a ring of points whose radius wobbles by a seeded amount,
  smoothed through Catmull-Rom. Hand-drawn polygons come out as regular hexagons
  and hand-drawn curves come out as ellipses; real ground is neither.
- **Every line was routed by search, not by eye.** The stream, the track and both
  minor branches were each scored on their closest approach to any control across
  hundreds of candidate seeds. All of them clear every control. A stream through
  a control circle is not a style problem, it is an unreadable map.
- **Legs stop at the edge of a control circle**, the course does not cross
  itself, and control numbers sit on the bisector of their two legs so a number
  never lands on a line. Verified in code.
- **Magnetic north lines** run the full height. Every orienteering map has them,
  the runner aligns a compass to them, and they give the sheet its texture.

Ink weights are deliberately light: contours at 0.55 and index at 0.95, tracks
at 1.1 and 0.8, water at 1.7. Only the course is heavy, at 2.1, because on a
printed map the overprint is meant to dominate everything under it. Heavy
strokes everywhere were the other half of why earlier drafts looked childish.

The module emits literal hexes rather than CSS variables. That is deliberate: an
earlier version referred to `var(--overprint)`, a page-level rename broke it, and
the entire course vanished while the terrain still rendered. A shared graphic
must not depend on its host defining the right names.

Generation takes about a second, which is why the map is baked into the page and
the card at build time rather than generated in the browser.

### Structure

Built against the taste-skill anti-slop rules (github.com/Leonxlnx/taste-skill),
with the ambition taken from awwwards and one of its habits deliberately left
behind. The Tie-break, a recent Site of the Day, scored 9.2 on animation and
6.6 on both accessibility and semantics. Award-winning sites win on interaction
and lose on the markup underneath. There is no reason to inherit the second
half along with the first, so everything that moves here is a progressive
enhancement and every one of them is switched off under
`prefers-reduced-motion`.

Two devices are borrowed, and both are quotations of the real artefact rather
than effects:

- **The hero is a title block printed on the sheet.** A competition map carries
  an overprinted box with the event, the course, its length and its climb. That
  is the hero: a detail of the map at full bleed with the block sitting on it,
  and the data line underneath carrying the numbers that actually decide the
  race. The hero shows a detail rather than the whole course, because at that
  size the whole map is a thumbnail of itself and the block would cover the
  start, which is the one thing a map must never hide.
- **Scrolling the clue list runs the course.** The map is sticky beside the
  list; each clue that arrives inks in its leg and lights its control, and the
  caption names where you are. The list and the map become visibly the same
  thing. This is not decoration: scrolling the chain is the only thing on the
  page that is literally what the game does.

The interaction is one `IntersectionObserver`, no scroll handler and no library.
The clue chain is an ordered list with every clue's text in the markup, in
order, so the section reads correctly with script disabled and to a screen
reader; the observer only changes opacity and inks the map. Legs carry
`pathLength="1"`, so a single CSS transition draws any leg whatever its real
length. Going back up does not un-ink anything, because a course you have run
stays run.

The constraints that shaped the rest, so a future edit does not quietly undo
them:

- **One eyebrow on the page.** The small mono-caps label above a headline is the
  most templated rhythm in AI-built sites. Budget is one per three sections; the
  page spends its single one on "Race 01 is open", which reports real state.
- **One status dot, one marquee, zero em-dashes.**
- **One superfamily at two widths, plus a mono.** Sofia Sans Extra Condensed,
  set in capitals, carries every heading and every figure. In capitals it reads
  like a race bib or a timing board, and on the title block it reads like the
  overprint on a competition map, which is the point. Sofia Sans, the same
  family at normal width, carries running text, so headings and body share one
  set of shapes. Martian Mono is reserved for machine values: digests, commit
  ids, verdicts, counts.

  It replaced Bricolage Grotesque, which by 2026 had become the default
  "distinctive" grotesque of AI-built landing pages. The pick was made by
  setting the actual title block in three candidates side by side (Sofia Sans,
  Hubot Sans, Overpass), not by name. The awwwards free-fonts collection was
  the starting point, but its most interesting entries (Faune, Galgo, Okta
  Neue) are only distributed through their own sites and could not be bundled
  and verified here.

  All three families are **embedded in the pages** under the SIL OFL, so they
  make no call to Google Fonts and need no `fonts/` folder beside them.
  `web/fonts/` is the source; `scripts/inline_assets.py` writes the woff2 files
  into each page as data URIs, and also inlines the course map into the play
  view. Re-run it after changing a font. Every page now works as a single file:
  opened from a download or an email it looks exactly as it does deployed.

  That is not a nicety. `index.html` was once opened on its own, without the
  `fonts/` folder; the browser fell back to a wider face, the headline set in
  four lines, and the title block overflowed the hero and had its top clipped
  off. Two fixes followed. The fonts were embedded, and the hero was rebuilt so
  the sheet grows around the block instead of fixing its own height and
  clipping whatever does not fit. The second fix is the one that matters: the
  block now cannot be clipped by anything, including a font that fails to
  load. Checked at nine viewports from 360x640 to 1920x1080, with the real
  fonts and with a deliberately wide fallback forced on. One trap: the `ch` unit is the
  width of a zero, which in an extra-condensed face is tiny, so any `max-width`
  written in `ch` for the old grotesque chokes this one into extra lines. The
  headline measure was rewritten for that reason.
- **The judging panel has a real empty state**, a skeleton of the result in the
  same positions rather than a paragraph describing it.

One trap worth remembering: `overflow-x: hidden` on `body` silently disables
`position: sticky` for every descendant, which killed the sticky map the first
time. `overflow-x: clip` clips the same way without creating a scroll container.

Two sections were deleted rather than restyled. "How a clue is cleared" was
three equal cards numbered 01, 02, 03, and it described the same three stages
that "Try a clue" demonstrates live one screen earlier. The demonstration wins.

The statement block is a solid purple field. There is an optional photograph
slot in it, marked TODO in the markup: a real map sheet and compass, 2400x900,
dropped in at low opacity. The block is finished without one.

---

## The play view

The v2 client uses `web/config.js` as its deployment source. It must refuse a
legacy protocol or an unconfigured address. The HTTP endpoint is part of network
identity: local Studio and hosted Studionet may report the same chain ID.

The commitment rule remains in `web/commitment.js` and is checked against the
contract by `scripts/test_commitment_parity.py`. The answer form is checked before
sending; deterministic contract checks remain authoritative. Wallet approval
signs a transaction, while accepted/finalized state determines its outcome.

Keep a player backup containing each answer and salt before relying on browser
storage. Backups contain private unrevealed answers: do not commit them to Git,
publish them in evidence, or share them with competitors. Losing a salt can make
reveal impossible; after the reveal deadline, expiry charges an attempt.

Implemented client actions are wallet-backed `join`, `commit`, `reveal`,
`judge`, `expire`, and `cancel_expired_race`, with a manual payload fallback.
The play view reads live race, player, clue and pending-commit state; the landing
leaderboard uses live reads. Storage is separated by endpoint, contract and
account. Backup export/import validates commitments against answer/salt data.
The client checks endpoint identity even when two networks share a chain ID,
does not automatically retry writes, and rejects a FINALIZED envelope whose
consensus did not accept the transition.

The client unit suite covers these safeguards (14 checks). A real Chrome
session verified local v2 reads, manual payload generation and recovery after
reload; the captured state is `web/client-verification.png`. The actual SDK
EIP-1193 provider path was also exercised against local Studio using an isolated
Node signer: all four join/commit/reveal/judge transactions finalized, and the
player advanced to position 1 (`verification/wallet-provider-live.json`). A real
browser extension approval UI has not been exercised. Wallets that
cannot forward the identity-checking `gen_call` fail closed to the manual Studio
fallback; matching chain IDs alone are insufficient. Build the allowlisted static output
under `web/dist` before hosting. Historical payload-only descriptions apply to
v1.

---

## Domain

The intended custom domain is **proofofhunt.quest**; its DNS connection is
handled by the owner. The configured source repository is
[Zhekinmaksim/proofofhunt](https://github.com/Zhekinmaksim/proofofhunt) and the
frontend targets Vercel. A successful source push is not proof that hosting or
the custom domain is live. The social-card meta tags use absolute
URLs on that domain (`https://proofofhunt.quest/brand/og.png`), because the
crawlers that build link previews do not resolve relative paths: a relative
`og:image` means no preview at all when the link is shared. Both pages carry a
canonical URL. Deploy the built `web/dist/` so that `brand/og.png` resolves at that address.

## The video

`video/` is a Remotion project that renders a one-minute explainer: the map,
the course, commit before reveal, the tribunal, UNDETERMINED, and why the
earliest correct commit wins however late its verdict arrives. It draws the same
course as the site, exported from `scripts/course.py`, in the same type and
palette. The rendered file is `video/out/proof-of-hunt.mp4`, already encoded
as yuv420p with faststart so it uploads cleanly to X. Script, timing, design
rules and render instructions are in `video/README.md`.

The soundtrack is the last minute of a 123 BPM track, cut so the video ends as
the song does. Every scene cut lands on a downbeat, each leg of the course inks
on a beat, and the scene where a source goes offline plays over the moment the
music drops out. `scripts/fit_music.py` cuts the audio and generates the timing;
the render's audio sits 0 ms from the source. The owner confirmed usage rights
for the soundtrack; it may remain in the published render.

## Brand assets

```
pip install pillow cairosvg
python3 scripts/make_brand.py
```

Needs the three TTFs in a `fonts/` directory beside `scripts/`, or set
`POH_FONTS` to wherever they live: Sofia Sans Extra Condensed, Sofia Sans and
Martian Mono, all from the google/fonts repository. The headline on the social
card is fitted to its column by measurement rather than set at a fixed size,
because the first render with the new face ran the full stop of "STORED."
across the divider and onto the map.

The mark's pins are ink. They were white for a while after the palette moved
from dark to paper, which on a white page left the mark as a bare ring with no
punch pattern, the one thing it is about. It went unnoticed at nav size and was
caught at 120px on the video's end card.

Regenerates the mark, `favicon.ico` (16/32/48, each drawn at its own size rather
than resampled), `favicon.svg`, `apple-touch-icon.png`, `icon-512.png`,
`logo-lockup.svg` and `og.png`. Fonts are resolved through fontconfig; install
Bricolage Grotesque, Familjen Grotesk and Martian Mono locally or the card falls
back to whatever is available.

The mark is a control point that has been punched. The ring is the map symbol
for a control; the dots are the pin pattern a control punch leaves in a runner's
card. One glyph, both halves of the name: the place an answer was hidden, and
the evidence you found it. Below about twenty pixels it drops to three pins and
loses its legs, because five pins at 16px are a smudge and two legs read as a
slash through the circle.

The design is a night orienteering course: near-black terrain, a lime overprint
that reads under a headlamp. One rule governs it - everything belonging to the
race is the overprint colour and nothing else is. The map on the page and the
map on the social card are the same SVG rendered twice, not two drawings that
resemble each other.

---

## GenLayer SDK version

The contract targets the **v0.2.x** surface: `from genlayer import *`,
`gl.Contract`, `@allow_storage`, `gl.public.write`, `gl.nondet.web.render`,
`gl.eq_principle.strict_eq`, `gl.eq_principle.prompt_comparative`.

v0.3.0-rc restructures the namespaces. If you move to it, the renames are:

| v0.2.x            | v0.3.x                  |
|-------------------|-------------------------|
| `gl.Contract`     | `gl.contract.Contract`  |
| `@allow_storage`  | `gl.storage.allow`      |

Check the current API before deploying. The web fetch surface is the fragile
part and moves most.

v0.2.16 events declare positional-only indexed fields followed by `**data`;
explicit keyword-only parameters are rejected during class generation. The SDK
binds indexed arguments in alphabetical field order. The contract declarations
and emission calls now use that order. All nine event classes passed the
official Event reflection check; see `verification/sdk-event-abi.txt`. This
checks the event ABI only, not a full GenVM deployment.

The real deployment also exposed a fake-SDK mismatch: `Address.ZERO` is not
available in the runtime. The constructor now builds the twenty-byte zero
address explicitly, and the test double no longer offers that extra member.

### Local environment and historical model observations

CLI 0.39.1's Compose file installs an older webdriver and omits the Redis
consensus worker required by the current Studio images. The project override
adds those services and uses webdriver 0.0.9, whose `/render` endpoint is needed
by GenVM v0.2.16. It also supplies the migration environment and a persistent
GenVM cache. The exact checked image digests are in `verification/studio-images.txt`.

```
bash scripts/start_studio.sh
docker exec genlayer-ollama ollama pull qwen2.5:7b
genlayer update ollama --model qwen2.5:7b
python3 scripts/configure_ollama.py
python3 scripts/dryrun_studio.py clues/race-01.json
npm --prefix scripts ci
node scripts/live_race.mjs --name beta-prototype --account-name beta-prototype --phase author --clues clues/prototype-02.json
node scripts/live_race.mjs --name beta-prototype --phase play --clues clues/prototype-02.json
```

On this Mac, Docker CPU inference worked but one judge took over five minutes.
Native Ollama 0.35.0 uses Metal and is reachable from Colima through
`host.lima.internal`, while listening only on `127.0.0.1:11435`. The same
qwen2.5:7b Q4_K_M weights were copied from the container into
`verification/private/ollama-models/`; that directory is excluded from delivery.
For the v2 beta, use a model that passes the unchanged full clue chain; the
historical Qwen failures below are not a reason to alter correct clue content.
Llama 3.1 8B completed the v1 TreeMap retry. Configure it with
`python3 scripts/configure_ollama.py --native --model llama3.1:8b --temperature 0`
when the model is installed in the native Ollama store.

For this optional acceleration, run `bash scripts/start_native_ollama.sh` in a
separate terminal, then `python3 scripts/configure_ollama.py --native --temperature 0` **between
transactions**. The older provider schema requires `temprature` as well as the
correct Ollama `temperature` key; the helper preserves both and uses a 4096
context with 512 output tokens. Restore Docker inference with the same helper
without `--native`. Temperature 0 removed a comparative-check disagreement
on CERN that occurred at 0.1 despite a correct leader ruling. The same
revealed commit passed without changing its clue; the failed transaction
is retained in the evidence.

The live runner saves every submitted hash before polling. Resume the same
command/checkpoint after interruption; do not submit duplicate commits blindly.
It checks the leader's execution result and the resulting contract state because
FINALIZED alone can include a failed contract call or a consensus round
marked Undetermined. The latter leaves the revealed commit unjudged; it
is distinct from the contract's verdict=3 source-failure path. Validator cancellation after
quorum is distinct from a leader error. Private test keys stay in the ignored
`verification/private/` folder; existing CLI accounts and network settings are
not used. Use distinct `--name` values for fresh races and `--account-name beta-full`
when an independent test account is needed. Completed clues are skipped
when resuming. To make an explicit, recorded retry of a failed consensus
judge without recreating the commit, pass `--retry-judge <index>` and
`--retry-label <unique-label>` after checking its live state. An already
recorded INCORRECT result is terminal for that commit; `--new-attempt <index>`
creates a fresh commitment, preserves the old result in `priorAttempts`, and
uses the next allowed attempt. It never disguises a charged failure as a
free retry. `--pipeline true` submits dependent calls after ACCEPTED, then
waits for every accepted transaction to finalize at the end of the phase.
The full-play phase rereads every verdict after that drain. For a precise
observed finality benchmark use the default, which waits through FINALIZED
for each call; bulk-drain finality observations can be later than finalization.

For source-failure runs, author `clues/source-failure-02.json`, then prepare
with `--phase prepare --limit 1`. Save the baseline before mutating the page.
After `source_fixture.py drifted|missing|original`, also run
`wait_source_renderer.py` with that state before judging. The first deletion
test found a real cache difference: the HTTP client already saw 404 while
web.render still served the previous text. For hosted tests the raw page
reported `Cache-Control: max-age=300`; `wait_source_cache.py` waits 330 seconds
from a confirmed mutation before judging. A wait does not itself prove cache
refresh: assert the actual contract status and preserve unexpected results.
Once the local renderer saw 404, the same
commit returned UNREACHABLE. No attempts were charged during either result.

The HTTP and renderer dry runs now pass all twelve sources. The W3C copy of the
1989 proposal returned 403 to Chrome, so clue 4 uses CERN's historical November
1990 proposal and a matching riddle. The EIP-55 reference answer is `keccak256`,
the spelling inside the rendered code example. IANA and RFC 793 windows and six
duplicate anchors were corrected. `sync_clues.py` also removed excess backslash
escaping in the static play page's numeric patterns; browser patterns and clue
data now agree with the JSON fixture (`verification/web-clue-parity.txt`).

---

## Historical v1 verification checklist — not a v2 release pass

**This completed checklist describes v1 only. Do not reuse its contract
addresses or checked boxes for the v2 release.** Keep this order when repeating
the checks for v2. HTTP dry runs and the fake SDK do not prove GenVM execution or
consensus. Record network, SDK/Studio version, provider/model, account, contract
address, transaction hashes, and observed state for each network run.

- [x] Run `test_race.py`, `test_canon_parity.py`, and
  `test_commitment_parity.py` (Node required). Passed on 2026-10-02.
- [x] Run `test_dryrun.py`. Its three offline source-gate checks passed.
- [x] Run `dryrun_clues.py clues/race-01.json` against all twelve live sources.
  Passed on 2026-10-02. Corrected IANA and RFC 793 windows and made six anchors
  unique. The IANA HTTP window ends before the mutable revision date; inspect
  the GenVM-rendered window too. Logs are in `verification/`.
- [x] Generate the 26 authoring calls with `deploy_calls.py`. Saved as
  `verification/race-01-calls.txt` and `.json`; expected answers are in the text
  log only, not in the deployment payloads.
- [x] Prepare `clues/prototype-02.json` with RFC 2324 and RFC 1149 only.
  Its six authoring calls are in `verification/prototype-02-calls.json`.
- [x] Start local Studio with Ollama. Docker and Node are installed; use
  `genlayer init --ollama`, then `genlayer up --ollama`. On this Colima host set
  `DOCKER_HOST=unix:///Users/zmaxx/.colima/default/docker.sock` for the CLI.
  Inspect existing GenLayer data before accepting `init`: it resets images,
  containers, volumes, provider keys, and the database. `up` does not perform
  that reset. Studio should be at `http://localhost:8080`.
- [x] Select and record the Ollama model with
  `genlayer update ollama --model <name>`. Check the actual validator configs;
  starting the Ollama container alone does not make validators use it.
- [x] Deploy `contracts/proof_of_hunt.py` from Studio Contracts with one string
  constructor argument, `title`. Resolve SDK incompatibilities only against
  the actual runtime and rerun deterministic tests after changing the contract.
- [x] Author and pin the two-clue prototype, then open and join. Commit,
  reveal, and judge `stout` for clue 0. Require `verdict=1` (CORRECT) and
  `player.position=1`. Then repeat with `256` for clue 1 and verify the finish.
  Use `web/play.html` or `commitment_preview` with the same player address.
- [x] Deploy a separate source-failure race with at least two clues. Pin a
  controlled HTTPS page with an anchor and at least 200 characters in the
  window. Join, commit, and reveal before changing the source. Change text
  **inside the pinned window**, then judge the same commit: require
  `verdict=3`, `pin_status=1` (DRIFTED), unchanged attempts and position.
  Remove the page, judge that commit again: require `verdict=3`,
  `pin_status=2` (UNREACHABLE), unchanged attempts and position. Restore the
  original page and verify the same commit can advance the player.
- [x] Run all twelve known answers in local Studio; require CORRECT at every
  step. Diagnose an UNDETERMINED by `pin_status`, the rendered excerpt, and
  validator/model output. A weak model's invalid JSON is not a clue bug.
- [x] Measure one successful `judge`: submission-to-verdict wall time, time
  to finality separately, receipt fee/currency, and any measured inference cost.
  State what a local or subsidised Studio run does not measure; do not treat
  an absent cost field as zero or extrapolate it to production pricing.
- [x] Repeat the prototype, source-failure race, and twelve-answer trace on
  Studionet with different validator providers. Use the stable `studionet`
  network, and check the RPC/chain ID before sending transactions.
- [x] Put the verified **full race** address from Studionet into `CONTRACT` in
  `web/play.html`. Keep prototype and source-failure addresses in the run log.
- [x] Record real commit/reveal/judge execution and the source-failure retry.
  `video/out/proof-of-hunt.mp4` is an explainer, not this execution recording.
- [x] Complete the submission notes below with addresses, transaction evidence,
  judge time/cost, demo link, and remaining limitations.

Local validators sharing one Ollama model test execution, not provider diversity.
They also fetch from the same machine: local success cannot establish that
independent Studionet renderers agree. In CLI 0.39.1 the validator creation
command is `genlayer localnet validators create`; check `--help` for provider
and model options rather than assuming `genlayer validators create` exists.

---

## Public beta scope and remaining assurance limits

The release target is Studionet, without prizes. Independent security review,
a production network SLA and a measured production invoice are outside the
claims established by this repository. The deterministic regressions, real
network tests and read latency smoke exercise different risks; none replaces
the others.

The execution demo uses actual captured Studio states with consensus waits
omitted. It is labelled as snapshots, not a continuous screen recording.
Historical v1 footage must not be presented as execution of the v2 contract.
Local inference has hardware/electricity costs; hosted simulator receipts are
not a production cost quote. No prize or eligibility rules should be inferred.

Operational commands and incident procedures are in
[`verification/production-ops.md`](verification/production-ops.md). Monitoring
runs once per invocation. The repository includes GitHub Actions checks on
push/PR and a read-only monitor scheduled hourly at minute 17 UTC, plus manual
dispatch. The schedule becomes effective after the workflow is pushed to the
default branch and Actions is enabled; no Codex automation was created.
Read-only checks do not refresh the live source through validators.

---

## Current v2 submission notes — 2026-10-03

1. **The race accommodates slow consensus.** Players commit before validators
   judge an answer. Judgments can finish asynchronously without changing the
   ordering of already included commitments.
2. **The winner is decided by commit order.** The earliest correct final-clue
   commit wins. Earlier eligible claims must resolve or expire under the same
   public deadlines before finalization. This does not promise equal transaction
   inclusion latency.
3. **Judging requires the live web.** The contract stores no answer key.
   Validators read the current source, compare its canonical window with the
   pinned digest, and judge the submitted answer against that window. Revealed
   player answers are public; this demonstration course has known answers.

This is a free Studionet public beta, without prizes or an independent security
review. Protocol v2 fixes repeated advancement and blocked finalization, limits
players to one pending commitment, and publishes 24-hour reveal, seven-day
judging and 30-day race deadlines. The judging deadline starts at commitment;
both commitment deadlines are capped by race closure.

**Verified current-source results:**

| Check | Observed result | Evidence |
| --- | --- | --- |
| Deterministic contract checks | 81 passing checks: 60 base checks and 21 v2 regressions | `verification/test-race-v2.txt`, `verification/test-race-v2-security.txt` |
| Browser-client safeguards | 14 passing tests covering recovery integrity, wallet identity, write retry protection and finality | `npm --prefix web test` |
| Local two-clue v2 prototype | `stout` and `256`: CORRECT; race FINAL, winner cid 1 | `verification/local-beta-prototype.json` |
| Studionet two-clue v2 prototype | `stout` and `256`: CORRECT; race FINAL, winner cid 1 | `verification/studionet-beta-prototype.json` |
| Actual EIP-1193 provider path | join → commit → reveal → judge finalized; `stout` CORRECT, position 1 | `verification/wallet-provider-live.json` |
| Browser recovery | Chrome read local v2 state and recovered the same saved answer, salt and hash after reload | `web/client-verification.png` |

Local prototype: `0x7C813e45431DFE405e0e5C43A7f4f22Fc1a5212e`.
Studionet prototype: `0x897F3ffcBDaeC00B3b90dbBf10ba438e5Daa1850`.
Both prototype checkpoints identify source SHA-256
`95f3bb804d2f831a63c7f29647d06bccebbc139b86179f598c53e8de3f0dd8d0`.
These finished prototypes are evidence, not the public race entry point.

The wallet-provider test used an isolated Node signer through the actual SDK
EIP-1193 transaction path on local Studio. It verifies provider integration and
real state transitions, not a browser extension's approval UI. Its judge hash is
`0x7fd797b583e5588cbca3824838ea4cb8b07485f614fbbb0a5532151200d25c4d`.

**Measured v2 judge:** Studionet transaction
`0x032ade8b021660e50b69ac33155ab564820a9c27d209d71921045d31cc2ecee0`
reached observed ACCEPTED in **20.485 seconds** and FINALIZED in **53.602
seconds**. Reported GPT-5.4 and Claude Sonnet 4.6 token usage totals an estimated
**$0.012422** at uncached public list prices. This assumes the GPT-5.4 routing
policy uses GPT-5.4 pricing, excludes unreported canceled inference, rendering,
machine costs and subsidies, and is not an operator invoice. The simulator's
zero gas price is not a production cost measurement. Full calculation and
receipts: `verification/judge-cost-beta.json`; pricing sources checked on
2026-10-03: [GPT-5.4](https://openrouter.ai/openai/gpt-5.4) and
[Claude Sonnet 4.6](https://openrouter.ai/anthropic/claude-sonnet-4.6/pricing).

The new twelve-clue trace, controlled-source failure/recovery, final public race
address and HTTPS deployment must be recorded separately when verified. The
prototype results above do not establish those pending checks. V1 evidence
below remains historical and must not be counted as a v2 release pass.

### Historical v1 local evidence — obsolete deployments

The UI deployment is `0x4F05EdFbc8a633E61B1E23354c7C47cE8dcA8021`
(transaction `0x4ea7a3f8b7933f38a65c7c8fc1ad4ee5f98f2feb0bbd5519d7d52e68cbbb9a5f`).
Its constructor and SDK schema were loaded by Studio. Independent signed
verification uses fresh test accounts, not the existing CLI wallet.

| Local check | Address | Observed result |
| --- | --- | --- |
| Two-clue prototype | `0x8CE8e3B9991Bc2FC47e8d6D933085F03d1724580` | stout CORRECT / position 1; 256 CORRECT; FINAL, winner_cid 1 |
| Source failure and recovery | `0x2cb7d37F5f517f32FCE35a2df8CCe738f6e8b914` | DRIFTED and UNREACHABLE spent no attempt; restored source cleared the same commit |

The source recovery used commit 0 throughout. The DRIFTED transaction is
`0x01c1871d4cd9f2d1e9025ba9e2fd9fc7aa7eaab2bfafedc05fb04ad61f059731`;
the confirmed UNREACHABLE retry is
`0x9ac49e92b052d9b7772b2ced71a3b993e97b90dbaead45bcb7ca6c2c1c80818a`;
restoration is
`0x6b501925b776007e98e0ad601aabec84e716ced307ae8693f13efaa7406c3fae`.
The first deletion judge still saw the cached changed page and returned DRIFTED;
that result is preserved rather than labelled UNREACHABLE.

The successful restoration judge on native Ollama Qwen 2.5 7B took **32.568 s**
from submission to observed ACCEPTED and **38.601 s** to observed FINALIZED.
The local receipt reports `gasUsed=8000000`, `effectiveGasPrice=0`: **0 GEN in
the simulator receipt**. Provider billing is **$0 for local inference**;
electricity and machine cost were not measured. This is not production pricing.
The earlier Docker CPU stout judge took 320.779 s / 330.890 s with a different
context configuration, so these are separate observations, not a controlled
benchmark. Polling is every two seconds.

The small model exposed two limitations in the full local trace: a comparative
JSON disagreement at temperature 0.1 on CERN, resolved by judging the same
commit at temperature 0, and an incorrect semantic ruling on TreeMap despite
the correct pinned excerpt. The latter charged one attempt. Its explanation
confused the requested container name with the separate requirement to
instantiate generic types. The clue and contract were kept unchanged while
Qwen 2.5 14B was downloaded and checked with the exact tribunal prompt. It
repeated the same semantic error off-chain, so it was not allowed to spend
another race attempt. Llama 3.1 8B passed the identical prompt and then the
real on-chain retry: transaction
`0x0a04bdeb786afd48cd4088e6a5ca486a6b605ff9cb8d93a058512741c440ef1d`.
The full local race at `0xc5B25B9643A37D1c0798Ed3Bc1d869BEBAe994d3`
finished with all **12/12 CORRECT**, position 12 and 13 total attempts,
including the preserved incorrect Qwen ruling. The successful last commit is
12. See `verification/local-full.json` and the model-specific
`verification/treemap-model-smoke-*.json` records. Local validators now run
Llama 3.1 8B at temperature 0; this local model agreement is not evidence of
heterogeneous consensus.


### Historical v1 Studionet prototype and measured judge

The prototype at `0xE2ab983C99Ab127fd3c79E66Ce83ec4c70C1b4ED` is FINAL:
`stout` and `256` both returned CORRECT, positions 1 and 2, winner_cid 1.
Its source schema was checked on the hosted SDK before deployment.

The first judge,
`0x7861327c95c2d66be0583efb7a1d84fd914afe57da58f8302424716aaeef3145`,
reached observed ACCEPTED in **18.992 s** and FINALIZED in **52.271 s**.
Successful participants include GPT-5.4 policies, OpenRouter GPT-5.4, and
OpenRouter Claude Sonnet 4.6. The receipt reports **0 GEN** in hosted Studio.

Reported token usage implies approximately **$0.0194** of model work at
uncached public list prices: GPT-5.4 $2.50/$15 per million input/output tokens
and Sonnet 4.6 $3/$15. This prices the named GPT-5.4 routing policies as GPT-5.4
and excludes unreported canceled work, web rendering and infrastructure.
It is an estimate, not the operator's invoice. The exact token counts,
assumptions and arithmetic are in `verification/judge-cost-estimate.json`.
Sources checked on 2026-10-03:
[GPT-5.4 pricing](https://openrouter.ai/openai/gpt-5.4) and
[Sonnet 4.6 pricing](https://openrouter.ai/anthropic/claude-sonnet-4.6/pricing).

### Run new v2 hosted verification with separate checkpoints

The live runner uses `https://studio.genlayer.com/api` for `--network studionet`.
It probes the chain ID and uses isolated keys in `verification/private/`, not
the CLI's existing wallet. Both this hosted simulator and the local instance
reported chain ID 61999; the endpoint is therefore part of the network identity.
Install the pinned client with `npm --prefix scripts ci`, then use a fresh
`--name` for a new race; an existing name resumes its checkpoint.

```bash
node scripts/live_race.mjs --network studionet --name beta-prototype --account-name beta-prototype --phase author --clues clues/prototype-02.json --pipeline true
node scripts/live_race.mjs --network studionet --name beta-prototype --phase play --clues clues/prototype-02.json
node scripts/live_race.mjs --network studionet --name beta-full --account-name beta-full --phase author --clues clues/race-01.json --pipeline true
node scripts/live_race.mjs --network studionet --name beta-full --phase play --clues clues/race-01.json --pipeline true
# Verify beta-* checkpoints and deployed source hashes explicitly.
# Historical report.json / code-parity files describe v1 unless regenerated
# with matching v2 contract addresses and the current source hash.
```

Pipeline mode progresses after ACCEPTED and drains successful transactions to
FINALIZED before declaring the phase complete. It verifies every pinned clue
and every final answer from contract state. Its finality timings can be late
observations; use the non-pipelined prototype judge for the timing measurement.
Checkpoint JSON files preserve submitted hashes so restarting cannot silently
send duplicate commits.

The hosted RPC also returned one temporary HTML response and later rejected
a judge submission with an explicit 30-requests/minute rate limit. Execution
resumed from saved hashes. Read-only requests have bounded retries; writes
are not automatically repeated. Hosted status polling is now every six
seconds (the earlier prototype timing used two-second polling).

A hosted RFC 8259 pin reached FINALIZED with a successful leader execution but
its consensus round timed out; the clue was not pinned. The subsequent open
correctly failed. The runner now requires an ACCEPTED consensus round and checks
stored pin state. A separately labelled retry pinned the same unchanged clue
and opened the race. Original failed transactions remain in
`verification/studionet-full.json` and its author logs.

The disposable raw source advertises `Cache-Control: max-age=300`. Hosted
mutation checks wait 330 seconds after observing changed content or HTTP 404;
the subsequent contract verdict, not the timer, proves DRIFTED/UNREACHABLE.
Mutation times and revisions are saved under `verification/source-fixture/`.
The original page is restored at the end. Its private administrative account
and test signing keys are excluded from the archive.

### Historical v1 hosted source failure and recovery

Contract `0x591DA9c2375e377fB6e7b488b50022dE69f5BDA7` used commit 0 throughout:

| Mutation | Final result | Transaction |
| --- | --- | --- |
| Changed text | UNDETERMINED / DRIFTED; total_attempts 0 | `0x26e8e81a837340785e915800dab1cbc06b065f9c29e582dd01b2713a0c2081eb` |
| Removed page | UNDETERMINED / UNREACHABLE; total_attempts 0 | `0xc9430c10eee80a8315208e1e5e2f784c6df153a4e3f1ab56896a942eb3c0d3e5` |
| Restored original | CORRECT / OK; position 1, total_attempts 1 | `0xfaa2dfd4c37e1ec908e6eaf725606f2f1439659b123916ba758ddc093becdb34` |

No second commit or reveal was sent. Both source failures preserved
`attempts_used`, `total_attempts`, `position`, and `cleared`; the final recovery
advanced exactly once. Snapshots are in `verification/studionet-source.json`.

### Obsolete v1 reviewer race — do not join

`0x1Bc40819aF0fAED6e789AECc909561FD4F9579CB` was the earlier OPEN v1 race.
It cannot be patched and remains vulnerable even though its authoring calls
were finalized. `verification/studionet-release.json` and the associated source
parity file are historical records, not the v2 entry point. Do not put this
address into the new client. The selected v2 address belongs in `web/config.js`.

### Historical v1 twelve-clue Studionet trace

Verification contract **`0xF71CC39fa2Bd35F35f997bCD51a631545A6B4b71`**
finished with **12/12 CORRECT**, position 12, total_attempts 12, state FINAL,
winner_cid 11. Every answer was read again from final contract state after
transaction finalization. The last judge is
`0xa94709ebc760ab2f73694a7d811bec78457003570355c2443ac6b0c45a05d8fc`.
This completed race is historical evidence only. Neither it nor the old OPEN
race above is a safe entry point for the new beta.

`verification/report.json` records successful prototype, source-failure/recovery,
and full-race checks for both local Studio and Studionet. Individual transaction
checkpoints retain exact hashes, validator models, votes, token counts,
rendered outputs, and preserved failed attempts. Cheap checks passed: 60 race
checks, 7 canonicalisation checks, 10 commitment checks, 3 dry-run regression
checks, and all 12 live sources through both HTTP and Studio's renderer.

Demo: `video/out/proof-of-hunt-execution.mp4` shows actual local and hosted UI
captures, including both source failures, recovery, and the twelve-clue finish.
Captions explicitly identify snapshots and omitted waits. The older
`video/out/proof-of-hunt.mp4` remains the mechanics explainer. The distributable
`proof-of-hunt-verified.zip` contains source, public evidence, and both videos,
with a SHA-256 file manifest; signing keys, dependency folders, and Ollama
weights are excluded.

## V2 public beta release — 2026-10-03

Three v1 blockers are fixed in the current source:

1. **Duplicate advancement:** each player has one pending commitment; reveal
   and judge check its clue against the current position. A correct resolution
   releases the pending slot and advances once.
2. **Withheld final reveals:** fixed reveal/judge deadlines and permissionless
   expiry prevent an earlier claim from blocking the winner forever. Unrevealed
   expiry charges an attempt; revealed unresolved expiry is free. There is no
   owner override.
3. **INCORRECT leaving state WON:** terminal incorrect and expired paths
   re-evaluate finalization so a resolved earlier claim cannot leave a winner
   needlessly provisional.

The original failing diagnostic output remains historical evidence in
`verification/production-review-repro.txt`; it is not a passing regression suite
for the corrected contract. Use the current deterministic tests. Preserve
failed model/consensus results in new evidence rather than relabelling them as
successful executions.

Use new checkpoint names beginning `beta-` for local Studio and Studionet.
Before selecting the release address, require a fresh two-clue prototype,
source drift/removal/recovery, all twelve answers, and adversarial multi-player
finalization checks against the same source hash. Actual new deployment
addresses and completed live checks must be added only when observed. The
configuration source is `web/config.js`; historical v1 addresses are not a
fallback if v2 deployment is unavailable.

The wallet actions, backup recovery, live leaderboard and pending/final state
handling are implemented. The live EIP-1193 provider test and browser backup recovery are recorded above.
A browser extension approval flow and HTTPS behavior against the selected public
deployment still require their own checks; provider tests do not prove those UI
steps. Vercel hosting and custom-domain DNS are separate checks;
the owner will connect `proofofhunt.quest`. Do not claim the custom domain is
live until it resolves and serves the intended deployment.

Run `node scripts/test_monitor.mjs` for alert logic and use the new address with:

```sh
node scripts/monitor_race.mjs --network studionet --address 0xVERIFIED_V2_ADDRESS --output verification/beta-monitor.json
node scripts/load_smoke.mjs --network studionet --address 0xVERIFIED_V2_ADDRESS --samples 10 --interval-ms 1000 --output verification/beta-read-smoke.json
```

These commands never sign transactions. The monitor returns 0 for no identified
alert, 1 for an actionable finding and 2 for failure/incomplete coverage. A
provisional winner is a review item, not automatically a bug. Consult
`verification/production-ops.md` for source, expiry, cancellation and RPC
recovery. A low-rate read smoke does not establish write-load capacity.

The owner confirmed soundtrack usage rights. Keep the music in the Remotion
render, update its claims to this public beta, and label any reused v1 execution
footage accurately. Neither the explainer nor test results claim an independent
security audit or readiness for prizes.
