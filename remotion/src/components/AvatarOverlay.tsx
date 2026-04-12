import React from 'react';
import { AbsoluteFill, Video } from 'remotion';

interface AvatarOverlayProps {
  /** URL to the avatar video (WebM VP9 with alpha channel preferred) */
  avatarVideoUrl: string;
  durationInFrames: number;
}

/**
 * Layer 1: Avatar overlay — large, centered in lower portion.
 *
 * - Fixed size: 70% of frame height, centered horizontally.
 * - Positioned so the avatar occupies the bottom 70% of the screen.
 * - objectFit: cover with top center focus (shows face/bust).
 * - Independent of the reference video's original size.
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
