import React from 'react';
import {useCurrentFrame, useVideoConfig} from 'remotion';
import {Stage, Label, ink} from '../lib/Stage';
import {easeOut, progress} from '../lib/time.js';

// Event markers are also consumed by scripts/demo_audio.py.
import timing from './timing.json';
export const Explainer: React.FC = () => {
  const {fps} = useVideoConfig();
  const t = useCurrentFrame() / fps;
  const step = t >= timing.events[2].t ? 2 : t >= timing.events[1].t ? 1 : 0;
  const words = ['WRITE', 'MEASURE', 'ANIMATE'];
  return <Stage t={t} label="EXPLAINER">
    <Label y={300}>HOW DOES A FILM BECOME CODE?</Label>
    <text x="75" y="530" fontSize="148" fontWeight="900" fill={ink.black} letterSpacing="-7">{words[step]}.</text>
    {words.map((word, i) => {
      const k = easeOut(progress(t, timing.events[i].t, 0.55));
      const y = 660 + i * 230;
      return <g key={word} transform={`translate(${(1 - k) * 120} 0)`} opacity={k}>
        <rect x="90" y={y} width="900" height="170" rx="12" fill={i === step ? ink.black : ink.mint} />
        <circle cx="170" cy={y + 85} r="43" fill={ink.red} />
        <text x="170" y={y + 99} textAnchor="middle" fontSize="40" fontWeight="700" fill={ink.paper}>{i + 1}</text>
        <text x="250" y={y + 100} fontSize="56" fill={i === step ? ink.paper : ink.black} fontWeight="700">{word}</text>
        {i < 2 && <path d={`M170 ${y + 182}v32m-10-10 10 10 10-10`} stroke={ink.black} strokeWidth="5" fill="none" />}
      </g>;
    })}
    <Label y={1460}>{['Choose one idea per shot.', 'Put events on a real timeline.', 'Every frame is a function of time.'][step]}</Label>
  </Stage>;
};
