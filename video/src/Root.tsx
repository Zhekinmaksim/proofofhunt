import React from 'react';
import {Composition} from 'remotion';
import './fonts';
import {Video} from './Video';
import {FPS, H, W} from './theme';
import {TOTAL} from './timing';

export const Root: React.FC = () => (
  <Composition
    id="ProofOfHunt"
    component={Video}
    durationInFrames={TOTAL}
    fps={FPS}
    width={W}
    height={H}
  />
);
