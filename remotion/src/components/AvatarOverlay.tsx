import React from 'react';
import { AbsoluteFill, Video } from 'remotion';

interface AvatarOverlayProps {
  /** URL to the avatar video (WebM VP9 with alpha channel preferred) */
  avatarVideoUrl: string;
  durationInFrames: number;
}

/**
 * Layer 1: Avatar with transparent background in the lower-third center.
 *
 * - Video should have alpha channel (WebM VP9 with yuva420p).
 * - Positioned at bottom center, taking ~45% of screen height.
 * - Plays for the entire duration synced with TTS audio.
 */
export const AvatarOverlay: React.FC<AvatarOverlayProps> = ({
  avatarVideoUrl,
}) => {
  // Don't render if no avatar URL is provided
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
        style={{
          width: '100%',
          height: '45%',
          objectFit: 'contain',
          objectPosition: 'bottom center',
        }}
      />
    </AbsoluteFill>
  );
};
