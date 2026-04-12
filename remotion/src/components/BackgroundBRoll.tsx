import React from 'react';
import { AbsoluteFill, Img, Sequence, Video } from 'remotion';
import type { BRollItem } from '../types';
import { secondsToFrames } from '../utils/timing';

interface BackgroundBRollProps {
  brolls: BRollItem[];
  fps: number;
  durationInFrames: number;
  /** Duration each B-Roll clip plays before cutting to the next. Default: 6 seconds (full Grok take). Last B-Roll may be cut short to fit video duration. */
  brollDurationSeconds?: number;
}

/**
 * Layer 0: Sequential B-Roll playback with hard cuts.
 *
 * - Each B-Roll plays for `brollDurationSeconds` (6s default, full Grok take) then cuts to the next.
 * - The last B-Roll may be cut short to match the total video duration.
 * - All B-Rolls are muted.
 * - Fills the entire 1080x1920 frame with object-fit: cover.
 * - If fewer B-Rolls than needed, the sequence loops.
 */
export const BackgroundBRoll: React.FC<BackgroundBRollProps> = ({
  brolls,
  fps,
  durationInFrames,
  brollDurationSeconds = 6,
}) => {
  // Nothing to render if no B-Rolls provided
  if (brolls.length === 0) {
    return (
      <AbsoluteFill style={{ backgroundColor: '#000' }} />
    );
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
        // Last slot: clamp to remaining frames to prevent stutter/overrun
        const remaining = durationInFrames - from;
        const clipDuration = Math.min(brollDurationFrames, remaining);
        const isVideo = isVideoUrl(broll.url);

        if (clipDuration <= 0) return null;

        return (
          <Sequence
            key={i}
            from={from}
            durationInFrames={clipDuration}
          >
            <AbsoluteFill>
              {isVideo ? (
                <Video
                  src={broll.url}
                  muted
                  style={mediaStyle}
                />
              ) : (
                <Img
                  src={broll.url}
                  style={mediaStyle}
                />
              )}
            </AbsoluteFill>
          </Sequence>
        );
      })}
    </AbsoluteFill>
  );
};

/** Check if a URL likely points to a video file. */
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
