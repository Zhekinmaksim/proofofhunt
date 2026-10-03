// Bundle once, then render stills for review or the full video.
//
//   node render.mjs stills 165 380 655        review frames
//   node render.mjs video                     out/proof-of-hunt.mp4
//
// Set REMOTION_CHROME to a Chromium binary if Remotion cannot download its
// own (for example behind a restrictive proxy). Otherwise leave it unset.
import {bundle} from '@remotion/bundler';
import {renderMedia, renderStill, selectComposition} from '@remotion/renderer';
import path from 'node:path';
import fs from 'node:fs';
import {execFileSync} from 'node:child_process';

const [mode, ...rest] = process.argv.slice(2);
const browserExecutable = process.env.REMOTION_CHROME || null;
fs.mkdirSync('out', {recursive: true});

const t0 = Date.now();
const serveUrl = await bundle({entryPoint: path.resolve('src/index.ts')});
console.log(`bundled in ${((Date.now() - t0) / 1000).toFixed(0)}s`);
const composition = await selectComposition({serveUrl, id: 'ProofOfHunt', browserExecutable});

if (mode === 'stills') {
  for (const frame of rest.map(Number)) {
    await renderStill({composition, serveUrl, frame, browserExecutable,
      output: `out/still-${String(frame).padStart(4, '0')}.png`});
    console.log(`still ${frame}`);
  }
} else {
  let last = -1;
  await renderMedia({
    composition, serveUrl, browserExecutable,
    codec: 'h264',
    crf: 18,
    outputLocation: 'out/proof-of-hunt.mp4',
    concurrency: Number(process.env.CONCURRENCY || 1),
    onProgress: ({progress}) => {
      const pct = Math.floor(progress * 100);
      if (pct !== last && pct % 5 === 0) { last = pct; console.log(`render ${pct}%`); }
    },
  });
  // Remotion's JPEG frames come out as full-range yuvj420p even with
  // pixelFormat set; that option was tried and did not stick. X and several
  // players reject or mis-render yuvj420p, so the file is re-encoded to
  // yuv420p here, audio copied untouched, moov atom moved to the front.
  const raw = 'out/proof-of-hunt.mp4';
  const tmp = 'out/proof-of-hunt.yuv420p.mp4';
  execFileSync('ffmpeg', ['-v', 'error', '-y', '-i', raw, '-c:v', 'libx264',
    '-preset', 'medium', '-crf', '18', '-vf', 'scale=out_range=tv', '-color_range', 'tv', '-pix_fmt', 'yuv420p', '-c:a', 'copy',
    '-movflags', '+faststart', tmp], {stdio: 'inherit'});
  fs.renameSync(tmp, raw);
  console.log(`done in ${((Date.now() - t0) / 60000).toFixed(1)} min`);
}
