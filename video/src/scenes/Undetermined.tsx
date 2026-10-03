import React from 'react';
import {AbsoluteFill} from 'remotion';
import {C} from '../theme';
import {Cut, Headline, Mono, Sentence, Stamp, Typed} from '../primitives';
import type {SceneProps} from '../Video';
import {beatAfter, onBeat} from '../beat';


const KEPT = ['No attempt lost.', 'Position unchanged.', 'Retry within the judging deadline.'];

/**
 * The design decision most likely to be questioned, shown rather than argued:
 * when the source cannot be read, the verdict is UNDETERMINED, and it costs the
 * player no attempt. The fixed judging deadline still applies.
 */
export const Undetermined: React.FC<SceneProps> = ({start}) => (
  <AbsoluteFill style={{padding: '84px 120px'}}>
    <Cut at={0}><Headline size={150}>Changed or unreachable.</Headline></Cut>

    <div style={{marginTop: 40, borderLeft: `4px solid ${C.ink}`, paddingLeft: 28}}>
      <Mono size={34}><Typed text="Studionet source test: changed text, then HTTP 404" at={6} cps={90} /></Mono>
      <div style={{marginTop: 12}}>
        <Mono size={34} color={C.muted}><Typed text="DRIFTED / UNREACHABLE" at={30} cps={34} /></Mono>
      </div>
    </div>

    <div style={{marginTop: 50, display: 'flex', alignItems: 'center', gap: 60}}>
      <Stamp at={onBeat(start, 46)}>
        <div style={{border: `4px solid ${C.ink}`, padding: '8px 28px 2px'}}>
          <Headline size={120}>Undetermined</Headline>
        </div>
      </Stamp>
      <div style={{display: 'flex', flexDirection: 'column', gap: 14}}>
        {KEPT.map((k, i) => (
          <Cut key={k} at={68 + i * 12} style={{display: 'flex', alignItems: 'center', gap: 18}}>
            <svg width={26} height={26} viewBox="0 0 26 26">
              <circle cx={13} cy={13} r={9} fill="none" stroke={C.purple} strokeWidth={3} />
            </svg>
            <Sentence size={42} color={C.ink}>{k}</Sentence>
          </Cut>
        ))}
      </div>
    </div>

    <Cut at={110} style={{marginTop: 54}}>
      <Sentence size={40}>Restore and retry before the deadline: up to 7 days from commit.</Sentence>
    </Cut>
  </AbsoluteFill>
);
