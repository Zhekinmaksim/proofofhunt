import markGeometry from "../../web/brand/mark.geometry.json";
import React from 'react';
import {Easing, interpolate, spring, useCurrentFrame, useVideoConfig} from 'remotion';
import {C, F} from './theme';

export const EASE = Easing.bezier(0.25, 0.1, 0, 1);

/** 0..1 over [from, from + dur], clamped and eased. */
export const prog = (frame: number, from: number, dur: number) =>
  interpolate(frame, [from, from + dur], [0, 1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
    easing: EASE,
  });

/**
 * Text cuts in rather than sliding up. Fade-and-rise on every block is the
 * stock explainer move and reads as a template; here the mechanics move and
 * the words simply appear on the beat. Layout is reserved from frame zero so
 * nothing reflows as lines arrive.
 */
export const Cut: React.FC<{
  at: number;
  until?: number;
  children: React.ReactNode;
  style?: React.CSSProperties;
}> = ({at, until, children, style}) => {
  const f = useCurrentFrame();
  const a = prog(f, at, 4);
  const b = until === undefined ? 1 : 1 - prog(f, until, 4);
  return <div style={{opacity: Math.min(a, b), ...style}}>{children}</div>;
};

/** Machine values type on, because that is literally how they arrive. */
export const Typed: React.FC<{
  text: string;
  at: number;
  cps?: number;
  style?: React.CSSProperties;
}> = ({text, at, cps = 34, style}) => {
  const f = useCurrentFrame();
  const {fps} = useVideoConfig();
  const n = Math.max(0, Math.min(text.length, Math.floor(((f - at) * cps) / fps)));
  return (
    <span style={style}>
      {text.slice(0, n)}
      <span style={{opacity: 0}}>{text.slice(n)}</span>
    </span>
  );
};

export const Headline: React.FC<{
  size?: number;
  color?: string;
  children: React.ReactNode;
  style?: React.CSSProperties;
}> = ({size = 128, color = C.ink, children, style}) => (
  <div
    style={{
      fontFamily: F.d,
      fontWeight: 800,
      fontSize: size,
      lineHeight: 0.9,
      letterSpacing: '-0.004em',
      textTransform: 'uppercase',
      color,
      ...style,
    }}
  >
    {children}
  </div>
);

export const Sentence: React.FC<{
  size?: number;
  color?: string;
  children: React.ReactNode;
  style?: React.CSSProperties;
}> = ({size = 40, color = C.ink2, children, style}) => (
  <div style={{fontFamily: F.b, fontSize: size, lineHeight: 1.3, color, ...style}}>
    {children}
  </div>
);

export const Mono: React.FC<{
  size?: number;
  color?: string;
  children: React.ReactNode;
  style?: React.CSSProperties;
}> = ({size = 28, color = C.ink, children, style}) => (
  <span style={{fontFamily: F.m, fontSize: size, color, letterSpacing: '0.01em', ...style}}>
    {children}
  </span>
);

/** A verdict lands like a punch: overshoots slightly and settles. */
export const Stamp: React.FC<{
  at: number;
  children: React.ReactNode;
  style?: React.CSSProperties;
}> = ({at, children, style}) => {
  const f = useCurrentFrame();
  const {fps} = useVideoConfig();
  const s = spring({frame: f - at, fps, config: {damping: 13, stiffness: 240, mass: 0.6}});
  const scale = interpolate(s, [0, 1], [1.4, 1]);
  const opacity = f < at ? 0 : interpolate(s, [0, 0.35], [0, 1], {extrapolateRight: 'clamp'});
  return (
    <span
      style={{
        display: 'inline-block',
        transform: `scale(${scale})`,
        transformOrigin: 'left center',
        opacity,
        ...style,
      }}
    >
      {children}
    </span>
  );
};

/** The route/check H; shared with every site and brand export. */
export const Mark: React.FC<{size: number; color?: string}> = ({
  size,
  color = C.purple,
}) => (
  <svg width={size} height={size} viewBox={markGeometry.viewBox} aria-hidden="true">
    <path fill={color} d={markGeometry.path} />
  </svg>
);

/** A white sheet with an ink edge, the frame used for every panel. */
export const Sheet: React.FC<{
  children: React.ReactNode;
  style?: React.CSSProperties;
}> = ({children, style}) => (
  <div
    style={{
      background: C.paper,
      border: `2px solid ${C.ink}`,
      boxShadow: '12px 12px 0 rgba(20,20,15,0.10)',
      ...style,
    }}
  >
    {children}
  </div>
);
