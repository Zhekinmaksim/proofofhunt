import React from 'react';
import {AbsoluteFill, interpolate, useCurrentFrame} from 'remotion';
import {C, F} from '../theme';
import {Cut, Headline, Mono, prog, Sentence, Stamp, Typed} from '../primitives';
import type {SceneProps} from '../Video';
import {beatAfter, onBeat} from '../beat';


const BARS = [92, 86, 95, 70, 88, 93, 60, 90, 78];
const SAYS = [
  'The document calls the body short and stout.',
  'Matches the line the clue points to.',
  'Stout completes the phrase in the source.',
];

const Step: React.FC<{n: number; title: string}> = ({n, title}) => (
  <div style={{display: 'flex', alignItems: 'baseline', gap: 16, marginBottom: 26}}>
    <span style={{fontFamily: F.m, fontSize: 30, color: C.purple}}>{n}</span>
    <Headline size={54}>{title}</Headline>
  </div>
);

/**
 * The three stages, in the order the contract runs them. The point the scene
 * has to land is in the middle column: three validators write three different
 * sentences and return one identical verdict, and consensus compares only the
 * verdict and the source. The prose dims; the verdicts stay.
 */
export const Tribunal: React.FC<SceneProps> = ({start}) => {
  const f = useCurrentFrame();
  const punch = onBeat(start, 296);
  const sweep = prog(f, 40, 38);
  const pinned = f >= 84;
  const dim = interpolate(f, [228, 240], [1, 0.3], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
  const BAR_STEP = 28;

  return (
    <AbsoluteFill style={{padding: '70px 120px'}}>
      <Cut at={0}>
        <Headline size={116}>Then the tribunal reads</Headline>
        <Headline size={116}>the same page.</Headline>
      </Cut>

      {/* Stage A: pin the source */}
      <Cut at={22} style={{position: 'absolute', left: 120, top: 330, width: 500}}>
        <Step n={1} title="Check the source pin" />
        <div style={{position: 'relative', border: `2px solid ${C.ink}`, padding: '24px 26px',
          height: BARS.length * BAR_STEP + 36}}>
          {BARS.map((w, i) => (
            <div key={i} style={{height: 10, width: `${w}%`, background: C.line,
              marginTop: i === 0 ? 0 : BAR_STEP - 10}} />
          ))}
          <div style={{position: 'absolute', left: 14, right: 14,
            top: 14 + interpolate(sweep, [0, 1], [0, 3 * BAR_STEP]),
            height: 4 * BAR_STEP - 4,
            border: `3px ${pinned ? 'solid' : 'dashed'} ${C.purple}`,
            background: pinned ? 'rgba(213,0,109,0.08)' : 'transparent'}} />
        </div>
        <div style={{marginTop: 20, display: 'flex', alignItems: 'center', gap: 16}}>
          <Mono size={26} color={C.purpleDeep}><Typed text="source digest" at={84} cps={40} /></Mono>
          <Stamp at={onBeat(start, 112)}><Mono size={22} color={C.purple}>pinned</Mono></Stamp>
        </div>
        <Cut at={120} style={{marginTop: 14}}>
          <Sentence size={28}>Pin before opening the race. Re-read and check the window at judge time.</Sentence>
        </Cut>
      </Cut>

      {/* Stage B: three validators judge */}
      <Cut at={132} style={{position: 'absolute', left: 690, top: 330, width: 660}}>
        <Step n={2} title="Validators judge" />
        {SAYS.map((s, i) => (
          <Cut key={i} at={146 + i * 26} style={{display: 'grid',
            gridTemplateColumns: '58px 1fr auto', alignItems: 'baseline', gap: 16,
            padding: '16px 0', borderBottom: i < 2 ? `2px solid ${C.line}` : 'none'}}>
            <Mono size={22} color={C.faint}>V{i + 1}</Mono>
            <Sentence size={30} style={{opacity: dim}}>{s}</Sentence>
            <Stamp at={onBeat(start, 156 + i * 26)}><Mono size={24} color={C.purple}>correct</Mono></Stamp>
          </Cut>
        ))}
        <Cut at={240} style={{marginTop: 26}}>
          <Sentence size={30} color={C.ink}>
            Illustrative votes. Equivalence compares verdict and source digest, not reasoning.
          </Sentence>
        </Cut>
      </Cut>

      {/* Stage C: apply */}
      <Cut at={280} style={{position: 'absolute', left: 1410, top: 330, width: 400}}>
        <Step n={3} title="Apply" />
        <div style={{display: 'grid', gridTemplateColumns: 'repeat(6, 1fr)', gap: 10, width: 380}}>
          {Array.from({length: 12}, (_, i) => (
            <div key={i} style={{height: 56, border: `2px solid ${i === 0 && f >= punch ? C.purple : C.line2}`,
              display: 'flex', alignItems: 'center', justifyContent: 'center'}}>
              {i === 0 ? (
                <Stamp at={punch}>
                  <svg width={34} height={34} viewBox="0 0 26 26">
                    {[[6, 6], [20, 6], [13, 13], [6, 20], [13, 20]].map(([x, y]) => (
                      <circle key={`${x}${y}`} cx={x} cy={y} r={2.6} fill={C.purple} />
                    ))}
                  </svg>
                </Stamp>
              ) : null}
            </div>
          ))}
        </div>
        <Cut at={312} style={{marginTop: 26}}>
          <Sentence size={30}>Card punched.<br />Clue 02 opens.</Sentence>
        </Cut>
      </Cut>
    </AbsoluteFill>
  );
};
