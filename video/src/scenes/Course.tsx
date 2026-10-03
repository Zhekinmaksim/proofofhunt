import React from 'react';
import {CLUE_TITLES} from '../verified';
import {AbsoluteFill, interpolate, useCurrentFrame} from 'remotion';
import {CourseMap} from '../CourseMap';
import {C, F} from '../theme';
import {Cut, Headline} from '../primitives';
import type {SceneProps} from '../Video';
import {beatAfter, onBeat} from '../beat';


const TITLES = CLUE_TITLES;

/**
 * The memorable moment: the whole course inks in, leg by leg, while the clue
 * list beside it advances in step. The list and the map are visibly the same
 * chain, which is the game in one picture.
 */
export const Course: React.FC<SceneProps> = ({start}) => {
  const f = useCurrentFrame();
  // one leg per beat: each control lights exactly on the music
  let inked = 0;
  for (let k = 0; k < 12; k++) {
    const s = beatAfter(start, 2 + k);
    const e = beatAfter(start, 3 + k);
    inked += interpolate(f, [s, e], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
  }
  const finish = beatAfter(start, 16);
  const at = Math.floor(inked);

  return (
    <AbsoluteFill>
      <div style={{position: 'absolute', left: 700, top: 62, width: 1100, height: 804,
        border: `2px solid ${C.ink}`, overflow: 'hidden'}}>
        <CourseMap inked={inked} width={1100} height={804} />
      </div>

      <div style={{position: 'absolute', left: 120, top: 62, width: 520}}>
        <div style={{position: 'relative', height: 300}}>
          <Cut at={0} until={finish - 4} style={{position: 'absolute', inset: 0}}>
            <Headline size={104}>Each clue</Headline>
            <Headline size={104}>unlocks</Headline>
            <Headline size={104}>the next.</Headline>
          </Cut>
          <Cut at={finish} style={{position: 'absolute', inset: 0}}>
            <Headline size={104}>First to</Headline>
            <Headline size={104}>the finish</Headline>
            <Headline size={104}>wins.</Headline>
          </Cut>
        </div>

        <div style={{marginTop: 34, display: 'flex', flexDirection: 'column', gap: 6}}>
          {TITLES.map((t, i) => {
            const done = i < at;
            const now = i === at && inked < 12;
            const color = now ? C.purple : done ? C.ink : C.line2;
            return (
              <div key={t} style={{display: 'flex', alignItems: 'baseline', gap: 16, height: 40}}>
                <span style={{fontFamily: F.m, fontSize: 18, color, width: 34}}>
                  {String(i + 1).padStart(2, '0')}
                </span>
                <span style={{fontFamily: F.d, fontWeight: 800, fontSize: 34,
                  textTransform: 'uppercase', color, letterSpacing: '0.004em'}}>
                  {t}
                </span>
              </div>
            );
          })}
        </div>
      </div>
    </AbsoluteFill>
  );
};
