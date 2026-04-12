import React from 'react';
import { AbsoluteFill, useVideoConfig } from 'remotion';
import { BackgroundBRoll } from '../components/BackgroundBRoll';
import { AvatarOverlay } from '../components/AvatarOverlay';
import { BreakingNewsBanner } from '../components/BreakingNewsBanner';
import { Captions } from '../components/Captions';
import { SoundDesign } from '../components/SoundDesign';
import type { CompositionProps } from '../types';

/**
 * News Tradicional - Main composition assembling all 5 layers.
 */
export const NewsTradicional: React.FC<CompositionProps> = (props) => {
  const { fps, durationInFrames } = useVideoConfig();

  return (
    <AbsoluteFill style={{ backgroundColor: '#000' }}>
      <BackgroundBRoll
        brolls={props.brolls}
        fps={fps}
        durationInFrames={durationInFrames}
        brollDurationSeconds={6}
      />

      <AvatarOverlay
        avatarVideoUrl={props.avatarVideoUrl}
        durationInFrames={durationInFrames}
      />

      <BreakingNewsBanner
        bannerText={props.bannerText || 'BREAKING NEWS'}
        topicText={props.topicText}
        urgentKeywords={props.urgentKeywords || []}
        bannerTemplateUrl={props.bannerTemplateUrl}
        fps={fps}
      />

      <Captions captions={props.captions} fps={fps} />

      <SoundDesign
        ttsAudioUrl={props.ttsAudioUrl}
        musicUrl={props.musicUrl}
        sfx={props.sfx}
        fps={fps}
        durationInFrames={durationInFrames}
      />
    </AbsoluteFill>
  );
};
