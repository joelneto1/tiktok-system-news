import React from 'react';
import { AbsoluteFill, Video } from 'remotion';

interface AvatarOverlayProps {
  avatarVideoUrl: string;
  durationInFrames: number;
}

/**
 * Layer 1: Avatar overlay — large, centered in lower portion.
 * 70% height, cover with top-center focus.
 * Uses Video for native WebM alpha channel support.
 */
export const AvatarOverlay: React.FC<AvatarOverlayProps> = ({
  avatarVideoUrl,
}) => {
  if (!avatarVideoUrl) {
    return null;
  }

  return (
    <AbsoluteFill
      style={{
        justifyContent: 'flex-end',
        alignItems: 'center',
      }}
    >
      <Video
        src={avatarVideoUrl}
        muted
        pauseWhenBuffering
        style={{
          width: '100%',
          height: '70%',
          objectFit: 'cover',
          objectPosition: 'top center',
        }}
      />
    </AbsoluteFill>
  );
};
