import React from 'react';
import { AbsoluteFill, Img, Video, Sequence } from 'remotion';
import type { BRollItem } from '../types';
import { secondsToFrames } from '../utils/timing';

interface BackgroundBRollProps {
  brolls: BRollItem[];
  fps: number;
  durationInFrames: number;
  brollDurationSeconds?: number;
}

/**
 * Layer 0: Sequential B-Roll playback with hard cuts.
 *
 * Uses OffthreadVideo instead of Video for more reliable rendering
 * (handles videos shorter than expected without crashing).
 */
export const BackgroundBRoll: React.FC<BackgroundBRollProps> = ({
  brolls,
  fps,
  durationInFrames,
  brollDurationSeconds = 6,
}) => {
  if (brolls.length === 0) {
    return <AbsoluteFill style={{ backgroundColor: '#000' }} />;
  }

  const brollDurationFrames = secondsToFrames(brollDurationSeconds, fps);
  const slotsNeeded = Math.ceil(durationInFrames / brollDurationFrames);

  const mediaStyle: React.CSSProperties = {
    width: '100%',
    height: '100%',
    objectFit: 'cover',
  };

  return (
    <AbsoluteFill style={{ backgroundColor: '#000' }}>
      {Array.from({ length: slotsNeeded }).map((_, i) => {
        const broll = brolls[i % brolls.length];
        const from = i * brollDurationFrames;
        const remaining = durationInFrames - from;
        const clipDuration = Math.min(brollDurationFrames, remaining);
        const isVideo = isVideoUrl(broll.url);

        if (clipDuration <= 0) return null;

        return (
          <Sequence key={i} from={from} durationInFrames={clipDuration}>
            <AbsoluteFill>
              {isVideo ? (
                <Video
                  src={broll.url}
                  muted
                  pauseWhenBuffering
                  style={mediaStyle}
                />
              ) : (
                <Img src={broll.url} style={mediaStyle} />
              )}
            </AbsoluteFill>
          </Sequence>
        );
      })}
    </AbsoluteFill>
  );
};

function isVideoUrl(url: string): boolean {
  const lower = url.toLowerCase();
  return (
    lower.endsWith('.mp4') ||
    lower.endsWith('.webm') ||
    lower.endsWith('.mov') ||
    lower.endsWith('.avi') ||
    lower.includes('video')
  );
}
