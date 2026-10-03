import React from 'react';
import {AbsoluteFill, useCurrentFrame} from 'remotion';
import {C} from '../theme';
import {Cut, Headline, Mono, prog, Sentence, Typed} from '../primitives';
import type {SceneProps} from '../Video';
import {beatAfter, onBeat} from '../beat';


const SOURCES = [
  'rfc-editor.org/rfc/rfc2324.txt',
  'rfc-editor.org/rfc/rfc1149.txt',
  'info.cern.ch/hypertext/WWW/TheProject.html',
  'info.cern.ch/hypertext/WWW/Proposal.html',
  'eips.ethereum.org/EIPS/eip-20',
];

/**
 * The objection the whole design answers. An ordinary onchain puzzle compares
 * your answer to a stored hash, which is a password. The stored value is
 * struck out, and what replaces it is the live web.
 */
export const Gate: React.FC<SceneProps> = ({start}) => {
  const f = useCurrentFrame();
  const hit = onBeat(start, 92);
  const swap = beatAfter(start, 8);
  const strike = prog(f, hit, 8);

  return (
    <AbsoluteFill style={{padding: '96px 120px'}}>
      {/* the password gate */}
      <Cut at={0} until={swap - 4} style={{position: 'absolute', left: 120, top: 200, width: 1680}}>
        <Headline size={124}>Most onchain puzzles</Headline>
        <Headline size={124}>check a stored answer.</Headline>

        <Cut at={20} style={{marginTop: 64}}>
          <div style={{display: 'inline-block', background: C.sheet, border: `2px solid ${C.ink}`,
            padding: '30px 40px'}}>
            <Mono size={40}>
              <Typed text="require(keccak256(answer) == " at={22} cps={60} />
            </Mono>
            <span style={{position: 'relative', display: 'inline-block'}}>
              <Mono size={40} color={C.purpleDeep}>
                <Typed text="0x9f2c4e1b…a71d" at={52} cps={40} />
              </Mono>
              <span style={{position: 'absolute', left: 0, top: '52%', height: 5,
                width: `${strike * 100}%`, background: C.ink}} />
            </span>
            <Mono size={40}><Typed text=");" at={64} cps={30} /></Mono>
          </div>
        </Cut>

        <Cut at={66} style={{marginTop: 46}}>
          <Sentence size={44}>That is a password. Somebody had to write it down first.</Sentence>
        </Cut>
      </Cut>

      {/* the web as the answer key */}
      <Cut at={swap} style={{position: 'absolute', left: 120, top: 120, width: 1680}}>
        <Headline size={124}>Proof of Hunt</Headline>
        <Headline size={124}>reads the live web.</Headline>

        <div style={{marginTop: 56, display: 'flex', flexDirection: 'column', gap: 16}}>
          {SOURCES.map((s, i) => (
            <Cut key={s} at={swap + 14 + i * 9} style={{display: 'flex', alignItems: 'center', gap: 22}}>
              <svg width={30} height={30} viewBox="0 0 30 30">
                <circle cx={15} cy={15} r={11} fill="none" stroke={C.purple} strokeWidth={3} />
              </svg>
              <Mono size={34} color={C.ink2}><Typed text={s} at={swap + 14 + i * 9} cps={70} /></Mono>
            </Cut>
          ))}
        </div>

        <Cut at={swap + 66} style={{marginTop: 46}}>
          <Sentence size={44}>No stored answer key. Sources are pinned; revealed answers are stored.</Sentence>
        </Cut>
      </Cut>
    </AbsoluteFill>
  );
};
