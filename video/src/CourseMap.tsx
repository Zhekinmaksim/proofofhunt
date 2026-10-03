import React from 'react';
import {C, F} from './theme';
import {
  CONTROLS,
  FINISH,
  FIELD,
  LABELS,
  LEGS,
  R_CTRL,
  R_FINISH,
  R_FINISH_IN,
  START_TRI,
  TERRAIN_SVG,
} from './course';

type Props = {
  /** How far along the course the ink has reached, 0..12, fractional. */
  inked: number;
  /** viewBox in map units, for cropping into a detail of the sheet. */
  view?: [number, number, number, number];
  width: number;
  height: number;
  /** Locked parts of the course are a dashed ghost at this opacity. */
  ghost?: number;
};

const legLength = ([x0, y0, x1, y1]: readonly number[]) => Math.hypot(x1 - x0, y1 - y0);

/**
 * The same sheet as the landing page and the social card, generated from
 * scripts/course.py. Every leg is drawn twice: a dashed ghost that is always
 * there, because a runner can see where the course goes before running it, and
 * a solid tracer that inks in as the race is run.
 */
export const CourseMap: React.FC<Props> = ({inked, view, width, height, ghost = 0.5}) => {
  const [fw, fh] = FIELD;
  const vb = view ?? [0, 0, fw, fh];

  return (
    <svg
      width={width}
      height={height}
      viewBox={vb.join(' ')}
      preserveAspectRatio="xMidYMid slice"
      style={{display: 'block'}}
    >
      {/* paper well beyond the sheet, so a crop past its edge is still paper */}
      <rect x={-2000} y={-2000} width={5000} height={5000} fill={C.paper} />
      <g dangerouslySetInnerHTML={{__html: TERRAIN_SVG}} />

      <g>
        {LEGS.map((l, i) => (
          <line
            key={`g${i}`}
            x1={l[0]}
            y1={l[1]}
            x2={l[2]}
            y2={l[3]}
            stroke={C.purple}
            strokeWidth={2.1}
            strokeDasharray="8 6"
            strokeLinecap="round"
            strokeOpacity={ghost}
          />
        ))}
      </g>

      <g>
        {LEGS.map((l, i) => {
          const p = Math.max(0, Math.min(1, inked - i));
          if (p <= 0) return null;
          const len = legLength(l);
          return (
            <line
              key={`t${i}`}
              x1={l[0]}
              y1={l[1]}
              x2={l[2]}
              y2={l[3]}
              stroke={C.purple}
              strokeWidth={2.4}
              strokeLinecap="round"
              strokeDasharray={len}
              strokeDashoffset={len * (1 - p)}
            />
          );
        })}
      </g>

      <polygon
        points={START_TRI.map((p) => p.join(',')).join(' ')}
        fill="none"
        stroke={C.purple}
        strokeWidth={2.2}
        strokeLinejoin="round"
      />

      {CONTROLS.map(([cx, cy], i) => {
        const on = inked >= i + 1 - 1e-6;
        const [lx, ly] = LABELS[i];
        return (
          <g key={`c${i}`}>
            <circle
              cx={cx}
              cy={cy}
              r={R_CTRL}
              fill="none"
              stroke={C.purple}
              strokeWidth={on ? 2.4 : 2.1}
              strokeDasharray={on ? undefined : '5 4'}
              strokeOpacity={on ? 1 : ghost}
            />
            <text
              x={lx}
              y={ly}
              textAnchor="middle"
              dominantBaseline="central"
              fill={C.purple}
              fillOpacity={on ? 1 : ghost}
              style={{fontFamily: F.m, fontSize: 11, fontWeight: 600}}
            >
              {i + 1}
            </text>
          </g>
        );
      })}

      {[R_FINISH_IN, R_FINISH].map((r) => {
        const on = inked >= LEGS.length - 1e-6;
        return (
          <circle
            key={`f${r}`}
            cx={FINISH[0]}
            cy={FINISH[1]}
            r={r}
            fill="none"
            stroke={C.purple}
            strokeWidth={on ? 2.4 : 2.1}
            strokeDasharray={on ? undefined : '5 4'}
            strokeOpacity={on ? 1 : ghost}
          />
        );
      })}
    </svg>
  );
};
