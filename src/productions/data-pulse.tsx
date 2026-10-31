import React from 'react';
import {useCurrentFrame, useVideoConfig} from 'remotion';
import {Stage, Label, ink} from '../lib/Stage';
import {easeOut, progress} from '../lib/time.js';
import data from './data.json';

export const DataPulse: React.FC = () => {
  const {fps} = useVideoConfig();
  const t = useCurrentFrame() / fps;
  const total = data.values.reduce((sum, d) => sum + d.value, 0);
  return <Stage t={t} label="DATA FILM" dark>
    <Label y={300} fill={ink.mint}>A COMMUNITY, IN MOTION.</Label>
    <text x="75" y="595" fontSize="240" letterSpacing="-10" fontWeight="900" fill={ink.paper}>{Math.round(total * easeOut(progress(t, 0, 7)))}</text>
    <Label y={675} fill={ink.mint}>PROJECTS / ONE FICTIONAL WEEK</Label>
    <path d="M90 1300h900" stroke={ink.paper} strokeWidth="3" />
    {data.values.map((d, i) => {
      const height = d.value / 84 * 450 * easeOut(progress(t, 0.5 + i * 0.7, 1.0));
      return <g key={d.label}>
        <rect x={100 + i * 128} y={1300 - height} width="88" height={height} fill={i === 6 ? ink.red : ink.mint} />
        <text x={144 + i * 128} y={1270 - height} textAnchor="middle" fontSize="32" fill={ink.paper}>{d.value}</text>
        <text x={144 + i * 128} y="1350" textAnchor="middle" fontSize="24" fill={ink.paper}>{d.label}</text>
      </g>;
    })}
    <Label y={1460} size={24} fill={ink.mint}>SYNTHETIC DATA / REPLACE WITH YOUR OWN</Label>
  </Stage>;
};
