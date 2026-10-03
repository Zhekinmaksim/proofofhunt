import React from 'react';
import {AbsoluteFill} from 'remotion';
import {CourseMap} from '../CourseMap';
import {C} from '../theme';
import {Cut, Headline, Mark, Mono, Sentence, Stamp} from '../primitives';
import {JUDGE_ACCEPTED, JUDGE_FINALIZED, REVIEWER_CONTRACT} from '../verified';
import type {SceneProps} from '../Video';

/** Verified prototype results, not a claim of production readiness. */
export const End: React.FC<SceneProps> = () => (
  <AbsoluteFill style={{padding: '74px 120px'}}>
    <div style={{position: 'absolute', left: 1120, top: 74, border: `2px solid ${C.ink}`}}>
      <CourseMap inked={12} width={680} height={400} />
    </div>
    <Stamp at={0}><Mark size={90} /></Stamp>
    <Cut at={0} style={{marginTop: 24}}>
      <Headline size={180}>Proof of</Headline>
      <Headline size={180}>Hunt</Headline>
    </Cut>
    <Cut at={8} style={{marginTop: 30}}>
      <Headline size={82} color={C.purple}>12 / 12 correct</Headline>
      <Sentence size={36}>Local Studio + diverse Studionet validators.</Sentence>
    </Cut>
    <Cut at={12} style={{position: 'absolute', left: 1120, top: 516, width: 680}}>
      <Mono size={26}>One Studionet judge</Mono>
      <Headline size={68}>{JUDGE_ACCEPTED}s accepted / {JUDGE_FINALIZED}s final</Headline>
      <Sentence size={30}>~$0.0124 model-cost estimate</Sentence>
      <Sentence size={24} color={C.muted}>Measured prototype run; not an invoice.</Sentence>
    </Cut>
    <Cut at={16} style={{position: 'absolute', left: 120, bottom: 60}}>
      <Sentence size={34}>Free Studionet beta · connect your wallet · no prizes</Sentence>
      <Mono size={25} color={C.purpleDeep}>{REVIEWER_CONTRACT}</Mono>
      <Sentence size={24} color={C.muted} style={{marginTop: 12}}>Verified 03 Oct 2026 · source, receipts and execution demo in the project.</Sentence>
    </Cut>
  </AbsoluteFill>
);
