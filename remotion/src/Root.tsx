import React from 'react';
import { Composition } from 'remotion';
import { NewsTradicional } from './compositions/NewsTradicional';
import { NewsJornalistico } from './compositions/NewsJornalistico';
import { NewsIce } from './compositions/NewsIce';
import type { CompositionProps } from './types';

const defaultProps: CompositionProps = {
  jobId: 'preview',
  model: 'news_tradicional',
  fps: 30,
  width: 1080,
  height: 1920,
  durationInFrames: 30 * 60, // 60 seconds at 30fps
  ttsAudioUrl: '',
  avatarVideoUrl: '',
  brolls: [],
  captions: [
    { word: 'BREAKING', start: 0, end: 0.5 },
    { word: 'NEWS', start: 0.5, end: 1.0 },
    { word: 'A', start: 1.0, end: 1.2 },
    { word: 'MAJOR', start: 1.2, end: 1.6 },
    { word: 'EVENT', start: 1.6, end: 2.0 },
    { word: 'HAS', start: 2.0, end: 2.3 },
    { word: 'OCCURRED', start: 2.3, end: 2.8 },
    { word: 'TODAY', start: 2.8, end: 3.2 },
    { word: 'IN', start: 3.2, end: 3.4 },
    { word: 'THE', start: 3.4, end: 3.6 },
    { word: 'CITY', start: 3.6, end: 4.0 },
    { word: 'CENTER', start: 4.0, end: 4.5 },
  ],
  scenes: [],
  sfx: [],
  musicUrl: '',
  bannerText: 'BREAKING NEWS',
  urgentKeywords: ['URGENT', 'DEVELOPING STORY', 'LIVE UPDATE'],
};

export const RemotionRoot: React.FC = () => {
  return (
    <>
      <Composition
        id="NewsTradicional"
        component={NewsTradicional}
        durationInFrames={30 * 60}
        fps={30}
        width={1080}
        height={1920}
        defaultProps={defaultProps}
      />
      <Composition
        id="NewsJornalistico"
        component={NewsJornalistico}
        durationInFrames={30 * 60}
        fps={30}
        width={1080}
        height={1920}
        defaultProps={{ ...defaultProps, model: 'news_jornalistico' as const }}
      />
      <Composition
        id="NewsIce"
        component={NewsIce}
        durationInFrames={30 * 60}
        fps={30}
        width={1080}
        height={1920}
        defaultProps={{ ...defaultProps, model: 'news_ice' as const }}
      />
    </>
  );
};
