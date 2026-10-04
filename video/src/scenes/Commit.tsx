import React from 'react';
import {AbsoluteFill} from 'remotion';
import {C, F} from '../theme';
import {Cut, Headline, Mono, Sentence, Stamp, Typed} from '../primitives';
import type {SceneProps} from '../Video';
import {beatAfter, onBeat} from '../beat';


const FIELDS: [string, string][] = [
  ['answer', 'stout'],
  ['salt', 'f2b59a66…f47d2'],
  ['your address', '0x08a3…5b23'],
  ['first clue', 'index 0'],
];

/**
 * Commit before reveal. The answer is hashed with a salt, the player's address
 * and the clue, so a watcher can neither read it nor replay it. The id the
 * chain gives that commit is the player's place in the race.
 */
export const Commit: React.FC<SceneProps> = ({start}) => (
  <AbsoluteFill style={{padding: '84px 120px'}}>
    <Cut at={0}><Headline size={150}>Commit first.</Headline></Cut>
    <Cut at={10} style={{marginTop: 22, width: 1400}}>
      <Sentence size={42}>
        A salted hash hides your answer until reveal and binds the commit to your address.
      </Sentence>
    </Cut>

    <div style={{marginTop: 54, display: 'flex', gap: 22}}>
      {FIELDS.map(([k, v], i) => (
        <Cut key={k} at={34 + i * 10} style={{flex: 1, border: `2px solid ${C.ink}`, padding: '18px 24px'}}>
          <div style={{fontFamily: F.b, fontSize: 24, color: C.muted}}>{k}</div>
          <Mono size={32} style={{display: 'block', marginTop: 8}}>
            <Typed text={v} at={36 + i * 10} cps={50} />
          </Mono>
        </Cut>
      ))}
    </div>

    <Cut at={82} style={{marginTop: 30, display: 'flex', alignItems: 'center', gap: 28}}>
      <Mono size={26} color={C.muted}>sha256 of all four</Mono>
      <div style={{border: `3px solid ${C.purple}`, background: C.purpleWash, padding: '18px 30px'}}>
        <Mono size={38} color={C.purpleDeep}>
          <Typed text="ad8006124f7fecf5…d150939717bc2b4" at={88} cps={44} />
        </Mono>
      </div>
    </Cut>

    <div style={{marginTop: 56, display: 'flex', alignItems: 'center', gap: 56}}>
      <Stamp at={onBeat(start, 140)}>
        <Headline size={132} color={C.purple}>First commit</Headline>
      </Stamp>
      <Cut at={160} style={{width: 760}}>
        <Sentence size={40}>
          Real Studionet prototype: reveal stout, then judge. CORRECT; first clue cleared.
        </Sentence>
      </Cut>
    </div>
  </AbsoluteFill>
);
