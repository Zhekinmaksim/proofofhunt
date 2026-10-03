// Scene lengths are fitted to the soundtrack by scripts/fit_music.py and live
// in the generated music.ts. They still sum to 1800 frames, one minute.
import {DURATIONS} from './music';

export {DURATIONS};

export const BOUNDARIES: number[] = DURATIONS.reduce<number[]>(
  (acc, d) => [...acc, acc[acc.length - 1] + d],
  [0],
);

export const TOTAL = BOUNDARIES[BOUNDARIES.length - 1];
