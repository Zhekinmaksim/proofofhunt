import React from 'react';
import {AbsoluteFill, useCurrentFrame} from 'remotion';
import {C, F} from '../theme';
import {Cut, Headline, Mono, Sentence, Stamp} from '../primitives';
import type {SceneProps} from '../Video';
import {beatAfter, onBeat} from '../beat';


// Three correct commits on the final clue, listed in commit order. Their
// verdicts come back in reverse, which is the case that matters.
const BASE = [
  {cid: 118, who: '0x7c4e…a19f', back: 124},
  {cid: 124, who: 'pigeon.eth', back: 84},
  {cid: 131, who: 'masinter', back: 44},
];
const ORD = ['1st', '2nd', '3rd'];

/**
 * The cleanest answer to "games do not belong on a slow chain". Verdicts can
 * land in any order; the winner is the earliest correct commit, so the
 * provisional leader changes hands until the oldest commit is judged, and then
 * the race is final.
 */
export const Order: React.FC<SceneProps> = ({start}) => {
  const f = useCurrentFrame();
  const ROWS = BASE.map((r) => ({...r, back: onBeat(start, r.back)}));
  const back = ROWS.filter((r) => f >= r.back);
  const leader = back.length ? Math.min(...back.map((r) => r.cid)) : null;
  const final = f >= ROWS[0].back;
  const arrival = [...ROWS].sort((a, b) => a.back - b.back).map((r) => r.cid);

  return (
    <AbsoluteFill style={{padding: '84px 120px'}}>
      <div style={{position: 'relative', height: 230}}>
        <Cut at={0} until={164} style={{position: 'absolute', inset: 0}}>
          <Headline size={120}>Verdicts can arrive</Headline>
          <Headline size={120}>in any order.</Headline>
        </Cut>
        <Cut at={168} style={{position: 'absolute', inset: 0}}>
          <Headline size={120}>The earliest correct</Headline>
          <Headline size={120}>final-clue commit wins.</Headline>
        </Cut>
      </div>

      <div style={{marginTop: 50, borderTop: `3px solid ${C.ink}`}}>
        {ROWS.map((r) => {
          const has = f >= r.back;
          const isLeader = leader === r.cid;
          return (
            <div key={r.cid} style={{display: 'grid', gridTemplateColumns: '300px 460px 520px 1fr',
              alignItems: 'center', height: 112, borderBottom: `2px solid ${C.line}`}}>
              <Headline size={76} color={isLeader ? C.purple : C.ink}>#{r.cid}</Headline>
              <Sentence size={40} color={C.ink}>{r.who}</Sentence>
              <div>
                {has ? (
                  <Stamp at={r.back}>
                    <Mono size={30} color={C.purple}>correct</Mono>
                    <span style={{fontFamily: F.b, fontSize: 24, color: C.muted, marginLeft: 18}}>
                      verdict back {ORD[arrival.indexOf(r.cid)]}
                    </span>
                  </Stamp>
                ) : (
                  <Mono size={26} color={C.faint}>judging…</Mono>
                )}
              </div>
              <div>
                {isLeader && !final ? <Mono size={28} color={C.purple}>leading</Mono> : null}
                {isLeader && final ? (
                  <Stamp at={ROWS[0].back}><Headline size={64} color={C.purple}>Winner</Headline></Stamp>
                ) : null}
              </div>
            </div>
          );
        })}
      </div>

      <Cut at={180} style={{marginTop: 44}}>
        <Sentence size={42}>Illustration: older final-clue claims must settle before the result is final.</Sentence>
      </Cut>
    </AbsoluteFill>
  );
};
