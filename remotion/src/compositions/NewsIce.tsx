import React from 'react';
import { AbsoluteFill } from 'remotion';
import type { CompositionProps } from '../types';

export const NewsIce: React.FC<CompositionProps> = () => {
  return (
    <AbsoluteFill
      style={{
        backgroundColor: '#16213e',
        justifyContent: 'center',
        alignItems: 'center',
        fontFamily: 'sans-serif',
      }}
    >
      <div style={{ color: '#00b4d8', fontSize: 48, fontWeight: 'bold' }}>
        News Ice
      </div>
      <div style={{ color: '#ffffff', fontSize: 28, marginTop: 16, opacity: 0.6 }}>
        Coming Soon
      </div>
    </AbsoluteFill>
  );
};
