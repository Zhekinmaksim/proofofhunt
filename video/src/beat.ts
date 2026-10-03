import {BEATS} from './music';

/**
 * Beat helpers. Scenes are written in scene-local frames; these convert
 * through the global beat grid so a verdict or an inked leg lands on the
 * music wherever the scene happens to sit in the edit.
 */

/** The beat nearest a scene-local frame, returned scene-local. */
export const onBeat = (start: number, local: number): number => {
  const g = start + local;
  let best = BEATS[0];
  for (const b of BEATS) if (Math.abs(b - g) < Math.abs(best - g)) best = b;
  return Math.round(best - start);
};

/** The n-th beat at or after the start of the scene, scene-local. */
export const beatAfter = (start: number, n: number): number => {
  const i = BEATS.findIndex((b) => b >= start);
  return BEATS[Math.min(i + n, BEATS.length - 1)] - start;
};
