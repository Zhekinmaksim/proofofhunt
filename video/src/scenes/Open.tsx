import React from 'react';
import {AbsoluteFill, interpolate, useCurrentFrame} from 'remotion';
import {CourseMap} from '../CourseMap';
import {C, F, STAGE, W} from '../theme';
import {Cut, Headline, Sentence, Sheet} from '../primitives';
import type {SceneProps} from '../Video';
import {beatAfter, onBeat} from '../beat';


/**
 * A detail of the sheet with the title block printed on it, exactly as the
 * landing page opens. The first leg inks while the title arrives: the race has
 * started before anyone has said what it is.
 */
export const Open: React.FC<SceneProps> = ({start}) => {
  const f = useCurrentFrame();
  const inkEnd = onBeat(start, 172);
  // a slow drift across the sheet, so it reads as a map under a hand
  const vx = interpolate(f, [0, 176], [-196, -180]);
  const inked = interpolate(f, [inkEnd - 44, inkEnd], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});

  return (
    <AbsoluteFill>
      <CourseMap inked={inked} view={[vx, 88, 452, 232]} width={W} height={STAGE} />

      <Sheet style={{position: 'absolute', left: 120, bottom: 64, width: 800}}>
        <div style={{display: 'flex', justifyContent: 'space-between', padding: '20px 36px',
          borderBottom: `2px solid ${C.ink}`, fontFamily: F.m, fontSize: 22}}>
          <span style={{color: C.muted}}>Race 01, Paper Trail</span>
          <span style={{color: C.purple}}>Studionet prototype</span>
        </div>
        <div style={{padding: '38px 36px 42px'}}>
          <Cut at={10}><Headline size={150}>Twelve clues.</Headline></Cut>
          <Cut at={36}><Headline size={150}>No answer key</Headline></Cut>
          <Cut at={46}><Headline size={150}>is stored.</Headline></Cut>
          <Cut at={84} style={{marginTop: 30}}>
            <Sentence size={40}>An onchain quest race on GenLayer.</Sentence>
          </Cut>
        </div>
      </Sheet>
    </AbsoluteFill>
  );
};
