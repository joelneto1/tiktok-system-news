import React from 'react';
import { AbsoluteFill, OffthreadVideo, staticFile } from 'remotion';

interface AvatarOverlayProps {
  avatarVideoUrl: string;
  durationInFrames: number;
}

/**
 * Layer 1: Avatar overlay — large, centered in lower portion.
 * Uses OffthreadVideo with staticFile for reliable local loading.
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
      <OffthreadVideo
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
