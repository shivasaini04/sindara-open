import React from 'react';
import {useCurrentFrame, useVideoConfig} from 'remotion';
import {Stage, ink, Label} from '../lib/Stage';
import {easeOut, progress} from '../lib/time.js';

export const Launch: React.FC<{title?: string}> = ({title = 'MAKE IT MOVE.'}) => {
  const {fps} = useVideoConfig();
  const t = useCurrentFrame() / fps;
  const shot = Math.min(2, Math.floor(t / 4));
  const local = t - shot * 4;
  const enter = easeOut(progress(local, 0, 0.6));
  return <Stage t={t} label="KINETIC LAUNCH" dark={shot === 1}>
    {shot === 0 ? <>
      <circle cx={810 + Math.sin(t) * 22} cy="620" r="440" fill={ink.red} />
      <circle cx="810" cy="620" r={210 + Math.sin(t * 2) * 14} fill="none" stroke={ink.paper} strokeWidth="35" />
      <Label y={300}>01 / A SMALL IDEA</Label>
      <g transform={`translate(${(1 - enter) * -50} 0)`} fill={ink.black} fontWeight="900" fontSize="180" letterSpacing="-9">
        <text x="70" y="890">SMALL</text><text x="70" y="1070">IDEA.</text>
      </g>
      <Label y={1360}>Give it a rhythm.</Label>
      <path d={`M90 1440h${240 + 640 * progress(t, 0, 4)}`} stroke={ink.black} strokeWidth="18" />
    </> : shot === 1 ? <>
      <Label y={300} fill={ink.mint}>02 / A SHARED TIMELINE</Label>
      <g transform={`translate(0 ${(1 - enter) * 100})`} fontWeight="900" fontSize="154" fill={ink.paper} letterSpacing="-7">
        <text x="75" y="580">WORDS.</text><text x="75" y="750">SHAPES.</text><text x="75" y="920" fill={ink.mint}>RHYTHM.</text>
      </g>
      {Array.from({length: 14}, (_, i) => <rect key={i} x={90 + i * 64} y={1300 - 200 * Math.abs(Math.sin(local * 2 + i * 0.7))} width="38" height={30 + 200 * Math.abs(Math.sin(local * 2 + i * 0.7))} rx="5" fill={i % 3 === 0 ? ink.red : ink.mint} />)}
      <Label y={1450} fill={ink.paper}>One clock. Every layer.</Label>
    </> : <>
      <Label y={300}>03 / YOUR NEXT SHORT</Label>
      <g transform={`translate(540 760) rotate(${-9 + Math.sin(local) * 2}) scale(${0.85 + enter * 0.15})`}>
        <rect x="-570" y="-160" width="1140" height="320" fill={ink.red} />
        <text textAnchor="middle" y="48" fill={ink.paper} fontWeight="900" fontSize={title.length > 14 ? 74 : 105} letterSpacing="-4">{title}</text>
      </g>
      <Label y={1180} size={72}>Your source.</Label><Label y={1280} size={72}>Your timing.</Label><Label y={1420}>Build with Sindara Studio.</Label>
    </>}
  </Stage>;
};
