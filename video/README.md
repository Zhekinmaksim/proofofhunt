# Proof of Hunt, the one-minute video

A Remotion project. 60 seconds, 1920x1080, 30 fps, eight scenes, with a
soundtrack the edit is cut to.

```
npm install
npm run studio        # preview and scrub in the browser
npm run render        # out/proof-of-hunt.mp4
```

`node render.mjs stills 165 560 1245` renders review frames without encoding
the whole video. `node render.mjs video` is the same as `npm run render` but
reuses one bundle and prints progress.

If Remotion cannot download its own browser (behind a restrictive proxy, for
example), point it at an existing `chrome-headless-shell` binary:

```
REMOTION_CHROME=/path/to/headless_shell node render.mjs video
```

A full Chrome binary will not work: it no longer supports the old headless
mode Remotion uses. It has to be the headless shell.

## The script

| Scene | Seconds | What it shows | On the music |
|---|---|---|---|
| Open | 0-5.9 | A detail of the map with the title block on it. The first leg inks. | quiet rise |
| Gate | 5.9-13.7 | An ordinary onchain puzzle checks a stored hash, which is a password. No answer key is stored; revealed answers are. | cut on the drums coming back |
| Course | 13.7-23.4 | The course inks while the clue list advances. Earliest correct final-clue commit wins. | one leg per beat |
| Commit | 23.4-31.2 | The answer is hashed; the commit id is the player's place in the race. | id lands on a beat |
| Tribunal | 31.2-42.9 | Check the source pin; illustrative validator votes; the card is punched. | each verdict on a beat |
| Order | 42.9-50.7 | Verdicts come back in reverse; the earliest correct commit wins anyway. | full groove |
| Undetermined | 50.7-56.3 | Source drift/removal returns UNDETERMINED without spending an attempt. | the music drops out |
| End | 56.3-60 | Public beta, verified results, measured judge, active contract. | the final hit, then the song ends |

Every scene cut lands on a downbeat. Scene lengths and the beat grid are
generated into `src/music.ts`; scenes use `onBeat` and `beatAfter` from
`src/beat.ts` so their events stay on the music wherever they sit in the edit.

## Soundtrack

`public/music.m4a` is the minute from 132.0 s to 192.0 s of the track, at
123 BPM, normalised to -14 LUFS. That window was chosen because the end of the
track has the video's shape: the drums return at 137.9 s, the music drops at
182.7 s, the strongest hit lands at 188.3 s, and the tail has decayed to silence
by 192 s. The scene where a source goes offline plays over the drop, so the
outage is something you hear. To make that work, "Order" now comes before
"Undetermined".

```
python3 ../scripts/fit_music.py path/to/track.mp3
```

re-cuts the audio and regenerates `src/music.ts`. The anchors in that script
were measured with librosa (onset strength, loudness fall, beat tracking), not
picked by ear; re-measure them if the track changes. In the rendered file the
audio sits 0 ms from the source window, and the two pinned cuts are within one
frame of their hits.

The project owner confirmed public usage rights for this soundtrack.

## Design

The same system as the site: the ISOM map palette, Sofia Sans Extra Condensed
in capitals for headings and figures, Sofia Sans for sentences, Martian Mono
only for machine values. Purple is the course overprint and marks only what
belongs to the race.
The folded-map waypoint mark imports `web/brand/mark.geometry.json`, the same source
used by the site headers and favicons.

One bold device runs the whole minute: a course along the bottom of the frame,
a start, six controls and a finish, one per scene. The leg into each scene inks
as the scene arrives, so the video is visibly a race from start to finish. The
domain sits beside it throughout.

Motion is reserved for things that change state in the game: a leg inks, a
digest is pinned, a verdict lands, a card is punched, the lead changes hands.
Text cuts in on the beat instead of fading and sliding up, because the stock
fade-and-rise on every block is what makes an explainer look generated.

## The course

`src/course.ts` is generated, not written. It comes from `scripts/course.py`,
the same module that draws the map on the landing page and the social card, via

```
python3 ../scripts/export_course_ts.py
```

Change the course there and re-export; the video, the site and the card stay
the same map.

## Encoding

`node render.mjs video` renders with Remotion and then re-encodes with ffmpeg
to yuv420p with faststart, copying the audio. Remotion's JPEG frames come out
as full-range yuvj420p even with its pixelFormat option set, and X and several
players reject that. The output is ready to upload as it is.


## Contract execution demo

`out/proof-of-hunt-execution.mp4` is separate from the Remotion explainer.
It assembles real Studio/Studionet UI captures of the verification run,
with captions and consensus waits omitted. It is labelled as captured
snapshots rather than continuous footage. The original frames and captions
are in `verification/demo-frames/manifest.json`; transaction evidence is
in `verification/*-prototype.json`, `*-source.json`, and `*-full.json`.

Rebuild with `python3 scripts/render_demo.py` from the project root, using
Python with Pillow installed and ffmpeg on PATH. The script reads the
captured frames; it does not re-run transactions or fabricate results.

## October 2026 update

The updated Remotion explainer preserves the 60-second soundtrack and design.
It uses the current CERN source, clue titles and real prototype commitment,
shows DRIFTED/UNREACHABLE recovery, and reports 12/12 sequential correct answers
and 19 s / 52 s observed judge timing. The ~$0.0194 model-cost figure estimates
reported token usage; it is not an invoice. The ending identifies the OPEN
reviewer contract and manual Studio calls.

Vote wording and reversed verdict order are labelled illustrations. No fixed
validator count or production-readiness claim is made. See RUN.md's production
review for the duplicate-commit advancement bug and unrevealed-commit finalization
blocker. `src/verified.ts` holds the evidence-backed titles, address and timings.
