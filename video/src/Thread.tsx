import React from 'react';
import {AbsoluteFill, useCurrentFrame} from 'remotion';
import {C, F, STRIP, W} from './theme';
import {Mark, prog} from './primitives';
import {BOUNDARIES} from './timing';

/**
 * The one bold device in the video: a course that runs along the bottom of
 * every scene. Start triangle, six controls, finish. Each scene is a control,
 * and the leg into it inks as the scene arrives, so the video is visibly a race
 * from start to finish. The domain sits beside it the whole way through.
 */
export const Thread: React.FC = () => {
  const f = useCurrentFrame();
  const n = BOUNDARIES.length - 1;      // nodes = scenes
  const x0 = 1040;
  const x1 = W - 120;
  const y = STRIP / 2;
  const xs = Array.from({length: n}, (_, k) => x0 + ((x1 - x0) * k) / (n - 1));
  const r = 13;

  return (
    <AbsoluteFill style={{top: 'auto', height: STRIP, background: C.paper,
      borderTop: `2px solid ${C.ink}`}}>
      <div style={{position: 'absolute', left: 120, top: 0, height: STRIP,
        display: 'flex', alignItems: 'center', gap: 18}}>
        <Mark size={34} />
        <span style={{fontFamily: F.m, fontSize: 26, color: C.ink, letterSpacing: '0.01em'}}>
          Proof of Hunt / Studionet
        </span>
      </div>

      <svg width={W} height={STRIP} style={{position: 'absolute', left: 0, top: 0}}>
        {xs.slice(0, -1).map((x, k) => {
          const xa = x + r + 4;
          const xb = xs[k + 1] - r - 4;
          // the leg into scene k+1 draws over the last 20 frames before it
          const p = prog(f, BOUNDARIES[k + 1] - 20, 20);
          return (
            <g key={k}>
              <line x1={xa} y1={y} x2={xb} y2={y} stroke={C.purple} strokeWidth={2.5}
                strokeDasharray="7 6" strokeOpacity={0.4} />
              <line x1={xa} y1={y} x2={xa + (xb - xa) * p} y2={y} stroke={C.purple}
                strokeWidth={3} strokeLinecap="round" />
            </g>
          );
        })}
        {xs.map((x, k) => {
          const reached = f >= BOUNDARIES[k];
          const here = reached && f < BOUNDARIES[k + 1];
          const common = {
            fill: 'none',
            stroke: C.purple,
            strokeWidth: here ? 3.4 : 2.5,
            strokeOpacity: reached ? 1 : 0.4,
            strokeDasharray: reached ? undefined : '4 4',
          };
          if (k === 0) {
            const t = 16;
            return (
              <polygon key={k} {...common} strokeLinejoin="round"
                points={`${x + t},${y} ${x - t * 0.62},${y - t * 0.78} ${x - t * 0.62},${y + t * 0.78}`} />
            );
          }
          if (k === n - 1) {
            return (
              <g key={k}>
                <circle cx={x} cy={y} r={r - 4} {...common} />
                <circle cx={x} cy={y} r={r + 3} {...common} />
              </g>
            );
          }
          return <circle key={k} cx={x} cy={y} r={here ? r + 2 : r} {...common} />;
        })}
      </svg>
    </AbsoluteFill>
  );
};
