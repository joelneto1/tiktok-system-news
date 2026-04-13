import React from 'react';
import { AbsoluteFill, Video, staticFile } from 'remotion';

interface AvatarOverlayProps {
  avatarVideoUrl: string;
  durationInFrames: number;
}

/**
 * Layer 1: Avatar overlay — large, centered in lower portion.
 * Uses Video (not OffthreadVideo) for native WebM alpha channel support.
 * Assets loaded via staticFile (local, no HTTP).
 */
export const AvatarOverlay: React.FC<AvatarOverlayProps> = ({
  avatarVideoUrl,
}) => {
  if (!avatarVideoUrl) {
    return null;
  }

  const src = avatarVideoUrl.startsWith('http') ? avatarVideoUrl : staticFile(avatarVideoUrl);

  return (
    <AbsoluteFill
      style={{
        justifyContent: 'flex-end',
        alignItems: 'center',
      }}
    >
      <Video
        src={src}
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
