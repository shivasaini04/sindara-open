import React from 'react';
import {AbsoluteFill} from 'remotion';

export const ink = {paper: '#F3ECD9', black: '#172B2B', red: '#D74732', mint: '#B9D8B0', gold: '#E5B34B'};

// Seeded geometry, never Math.random(): frames can render in any order.
export const Paper: React.FC<{t: number; dark?: boolean}> = ({t, dark = false}) => {
  const tick = Math.floor(t * 8);
  return <g opacity={dark ? 0.13 : 0.18} pointerEvents="none">
    {Array.from({length: 650}, (_, i) => {
      const x = (i * 127 + tick * 23) % 1080;
      const y = (i * 347 + tick * 41) % 1920;
      return <path key={i} d={`M${x} ${y}h${1 + i % 6}`} stroke={dark ? ink.paper : ink.black} strokeWidth={1 + i % 2} />;
    })}
  </g>;
};

export const Stage: React.FC<{t: number; dark?: boolean; label: string; children: React.ReactNode}> = ({t, dark = false, label, children}) => <AbsoluteFill style={{background: dark ? ink.black : ink.paper}}>
  <svg viewBox="0 0 1080 1920" width="100%" height="100%" style={{fontFamily: 'Arial, Helvetica, sans-serif'}}>
    <rect width="1080" height="1920" fill={dark ? ink.black : ink.paper} />
    <g opacity="0.15" stroke={dark ? ink.paper : ink.black} strokeWidth="1">
      {Array.from({length: 12}, (_, i) => <path key={i} d={`M${i * 100} 0v1920`} />)}
      {Array.from({length: 20}, (_, i) => <path key={i} d={`M0 ${i * 100}h1080`} />)}
    </g>
    {children}
    <Paper t={t} dark={dark} />
    <path d="M60 140h960M60 1570h960" stroke={dark ? ink.paper : ink.black} strokeWidth="3" />
    <text x="65" y="112" fontSize="22" letterSpacing="5" fill={dark ? ink.paper : ink.black}>SINDARA / {label}</text>
    <text x="65" y="1620" fontSize="20" letterSpacing="3" fill={dark ? ink.paper : ink.black}>DRAWN IN CODE. MOVED BY TIME.</text>
    <text x="1015" y="1620" textAnchor="end" fontSize="20" fill={dark ? ink.paper : ink.black}>{t.toFixed(2)}s</text>
  </svg>
</AbsoluteFill>;

export const Label: React.FC<{x?: number; y: number; children: React.ReactNode; fill?: string; size?: number; anchor?: 'start' | 'middle' | 'end'}> = ({x = 90, y, children, fill = ink.black, size = 32, anchor = 'start'}) => <text x={x} y={y} fill={fill} fontSize={size} textAnchor={anchor} letterSpacing="2">{children}</text>;
