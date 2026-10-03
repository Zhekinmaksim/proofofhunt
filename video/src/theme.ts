// The palette is quoted from ISOM, the IOF printing standard for orienteering
// maps, exactly as on the landing page. Purple is the course overprint and
// marks only what belongs to the race; yellow is open ground.
export const C = {
  paper: '#ffffff',
  sheet: '#f6f6f2',
  ink: '#14140f',
  ink2: '#3f4038',
  muted: '#6e7065',
  faint: '#9a9c91',
  line: '#dcdcd4',
  line2: '#c2c3b9',
  yellow: '#ffc42e',
  yellowSoft: '#ffe08f',
  purple: '#d5006d',
  purpleDeep: '#a80057',
  purpleWash: '#fbe3ee',
} as const;

// Condensed capitals for headings and figures, the normal width for sentences,
// mono only for machine values: hashes, ids, verdicts, URLs.
export const F = {
  d: '"Sofia Sans Extra Condensed", "Arial Narrow", sans-serif',
  b: '"Sofia Sans", system-ui, sans-serif',
  m: '"Martian Mono", ui-monospace, monospace',
} as const;

export const W = 1920;
export const H = 1080;
export const STRIP = 96;            // the course strip along the bottom
export const STAGE = H - STRIP;     // the area each scene draws into
export const FPS = 30;
