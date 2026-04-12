import React from 'react';
import { AbsoluteFill, Video } from 'remotion';

interface AvatarOverlayProps {
  avatarVideoUrl: string;
  durationInFrames: number;
}

/**
 * Layer 1: Avatar overlay — large, centered in lower portion.
 * 70% height, cover with top-center focus.
 * Uses Video component for native WebM alpha support.
 * Dark gradient behind avatar to prevent body semi-transparency.
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
      {/* Solid gradient behind avatar to prevent semi-transparent body */}
      <div
        style={{
          position: 'absolute',
          bottom: 0,
          left: 0,
          width: '100%',
          height: '50%',
          background: 'linear-gradient(to bottom, transparent 0%, rgba(0,0,0,0.85) 30%, rgba(0,0,0,1) 100%)',
        }}
      />
      <Video
        src={avatarVideoUrl}
        muted
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
