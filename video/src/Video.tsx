import React from 'react';
import {AbsoluteFill, Audio, Sequence, staticFile, useCurrentFrame} from 'remotion';
import {C, STAGE} from './theme';
import {BOUNDARIES, DURATIONS} from './timing';
import {SCENE_ORDER} from './music';
import {Thread} from './Thread';
import {prog} from './primitives';
import {Open} from './scenes/Open';
import {Gate} from './scenes/Gate';
import {Course} from './scenes/Course';
import {Commit} from './scenes/Commit';
import {Tribunal} from './scenes/Tribunal';
import {Undetermined} from './scenes/Undetermined';
import {Order} from './scenes/Order';
import {End} from './scenes/End';

export type SceneProps = {start: number};

const BY_NAME: Record<string, React.FC<SceneProps>> = {
  open: Open, gate: Gate, course: Course, commit: Commit,
  tribunal: Tribunal, order: Order, undetermined: Undetermined, end: End,
};

/** Each scene gets a short dissolve at both ends, nothing more. */
const Dissolve: React.FC<{dur: number; children: React.ReactNode; first: boolean; last: boolean}> = ({
  dur, children, first, last,
}) => {
  const f = useCurrentFrame();
  const a = first ? 1 : prog(f, 0, 4);
  const b = last ? 1 : 1 - prog(f, dur - 4, 4);
  return <AbsoluteFill style={{height: STAGE, opacity: Math.min(a, b)}}>{children}</AbsoluteFill>;
};

export const Video: React.FC = () => (
  <AbsoluteFill style={{background: C.paper}}>
    {/* The minute 132 s to 192 s of the track, cut and normalised by
        scripts/fit_music.py. The video ends as the song does. */}
    <Audio src={staticFile('music.m4a')} />
    {SCENE_ORDER.map((name, i) => {
      const Scene = BY_NAME[name];
      return (
        <Sequence key={name} from={BOUNDARIES[i]} durationInFrames={DURATIONS[i]} name={name}>
          <Dissolve dur={DURATIONS[i]} first={i === 0} last={i === SCENE_ORDER.length - 1}>
            <Scene start={BOUNDARIES[i]} />
          </Dissolve>
        </Sequence>
      );
    })}
    <Thread />
  </AbsoluteFill>
);
