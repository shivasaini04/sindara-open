import React from 'react';
import {Composition} from 'remotion';
import {Launch} from './productions/launch';
import {Explainer} from './productions/explainer';
import {DataPulse} from './productions/data-pulse';

export const Root: React.FC = () => <>
  <Composition id="Launch" component={Launch} durationInFrames={360} fps={30} width={1080} height={1920} defaultProps={{title: 'MAKE IT MOVE.'}} />
  <Composition id="Explainer" component={Explainer} durationInFrames={360} fps={30} width={1080} height={1920} />
  <Composition id="DataPulse" component={DataPulse} durationInFrames={360} fps={30} width={1080} height={1920} />
</>;
