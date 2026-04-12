import React from 'react';
import { AbsoluteFill, OffthreadVideo, staticFile, Loop } from 'remotion';

interface BreakingNewsBannerVideoProps {
  /** Topic text to show in the white bar below the banner */
  topicText?: string;
  fps: number;
  durationInFrames: number;
}

/**
 * Layer 2: Breaking News banner using pre-made video template.
 *
 * - Uses the "MODELO BREAKING NEWS TRADICIONAL.mp4" as overlay
 * - Positioned at top, cropped to show only the banner portion (~320px)
 * - Topic text overlaid on the white bar below the banner
 * - Loops for the entire video duration
 * - Rest of the video is transparent (not rendered)
 */
export const BreakingNewsBannerVideo: React.FC<BreakingNewsBannerVideoProps> = ({
  topicText,
  fps,
  durationInFrames,
}) => {
  // The template banner occupies approximately the top 320px of 1920px
  const bannerHeight = 320;

  return (
    <AbsoluteFill style={{ pointerEvents: 'none' }}>
      {/* Banner video — cropped to top portion only */}
      <div
        style={{
          position: 'absolute',
          top: 0,
          left: 0,
          width: '100%',
          height: bannerHeight,
          overflow: 'hidden',
        }}
      >
        <Loop durationInFrames={Math.round(85 * fps)}>
          <OffthreadVideo
            src={staticFile('breaking-news-template.mp4')}
            muted
            style={{
              width: '100%',
              height: 1920,
              objectFit: 'cover',
              objectPosition: 'top center',
            }}
          />
        </Loop>
      </div>

      {/* Topic text on the white bar area */}
      {topicText && (
        <div
          style={{
            position: 'absolute',
            top: 200,
            left: 0,
            width: '100%',
            minHeight: 100,
            backgroundColor: 'rgba(255, 255, 255, 0.95)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            padding: '14px 40px',
            boxShadow: '0 4px 16px rgba(0,0,0,0.3)',
          }}
        >
          <span
            style={{
              color: '#111111',
              fontSize: 38,
              fontWeight: 800,
              fontFamily: 'Inter, Arial, sans-serif',
              textAlign: 'center',
              lineHeight: 1.2,
              textTransform: 'uppercase',
            }}
          >
            {topicText}
          </span>
        </div>
      )}
    </AbsoluteFill>
  );
};
