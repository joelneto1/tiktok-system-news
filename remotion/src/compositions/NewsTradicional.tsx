import React from 'react';
import { AbsoluteFill, useVideoConfig } from 'remotion';
import { BackgroundBRoll } from '../components/BackgroundBRoll';
import { AvatarOverlay } from '../components/AvatarOverlay';
import { BreakingNewsBannerVideo } from '../components/BreakingNewsBannerVideo';
import { Captions } from '../components/Captions';
import { SoundDesign } from '../components/SoundDesign';
import type { CompositionProps } from '../types';

/**
 * News Tradicional - Main composition assembling all 5 layers.
 *
 * Layer 0: Background B-Rolls (6s each, muted)
 * Layer 1: Avatar with transparent background
 * Layer 2: BREAKING NEWS banner (video template + topic text)
 * Layer 3: Word-synced captions
 * Layer 4: Sound design (TTS + music + SFX)
 */
export const NewsTradicional: React.FC<CompositionProps> = (props) => {
  const { fps, durationInFrames } = useVideoConfig();

  return (
    <AbsoluteFill style={{ backgroundColor: '#000' }}>
      {/* Layer 0: Background B-Rolls (6s each, muted) */}
      <BackgroundBRoll
        brolls={props.brolls}
        fps={fps}
        durationInFrames={durationInFrames}
        brollDurationSeconds={6}
      />

      {/* Layer 1: Avatar with transparent background */}
      <AvatarOverlay
        avatarVideoUrl={props.avatarVideoUrl}
        durationInFrames={durationInFrames}
      />

      {/* Layer 2: Breaking News banner (video template + topic) */}
      <BreakingNewsBannerVideo
        bannerTemplateUrl={(props as any).bannerTemplateUrl}
        topicText={props.topicText}
        fps={fps}
        durationInFrames={durationInFrames}
      />

      {/* Layer 3: Word-synced captions */}
      <Captions captions={props.captions} fps={fps} />

      {/* Layer 4: Sound design (TTS + music + SFX) */}
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
