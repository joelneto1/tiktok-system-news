import React from 'react';
import {
  AbsoluteFill,
  Video,
  useCurrentFrame,
  interpolate,
  spring,
  staticFile,
} from 'remotion';

interface BreakingNewsBannerProps {
  bannerText: string;
  topicText?: string;
  urgentKeywords: string[];
  fps: number;
  bannerTemplateUrl?: string;
}

/**
 * Layer 2: BREAKING NEWS banner using cropped video template.
 *
 * Uses staticFile (local, no HTTP) and NO Loop (template is 85s, longer than video).
 * Topic text overlaid on the white bar area with Bebas Neue font.
 */
export const BreakingNewsBanner: React.FC<BreakingNewsBannerProps> = ({
  bannerText,
  topicText,
  fps,
}) => {
  const frame = useCurrentFrame();

  // Entry slide animation
  const slideIn = spring({
    frame,
    fps,
    config: { damping: 15, stiffness: 120, mass: 0.8 },
  });
  const translateY = interpolate(slideIn, [0, 1], [-500, 0]);

  const headlineText = topicText || bannerText || 'BREAKING NEWS';

  // Headline delayed spring
  const headlineSlide = spring({
    frame: frame - 10,
    fps,
    config: { damping: 18, stiffness: 100, mass: 0.6 },
  });
  const headlineY = interpolate(headlineSlide, [0, 1], [-100, 0]);

  return (
    <AbsoluteFill style={{ justifyContent: 'flex-start', pointerEvents: 'none' }}>
      <div
        style={{
          transform: `translateY(${translateY}px)`,
          width: '100%',
        }}
      >
        {/* Video template banner (cropped 460px, served locally via staticFile) */}
        <div
          style={{
            width: '100%',
            height: 460,
            overflow: 'hidden',
            position: 'relative',
          }}
        >
          <Video
            src={staticFile('banner-cropped.mp4')}
            muted
            style={{
              width: '100%',
              height: '100%',
              objectFit: 'cover',
            }}
          />

          {/* Topic text on the white bar */}
          {topicText && (
            <div
              style={{
                position: 'absolute',
                bottom: 40,
                left: 0,
                width: '100%',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                padding: '0 40px',
              }}
            >
              <span
                style={{
                  color: '#111111',
                  fontSize: 38,
                  fontWeight: 700,
                  fontFamily: "'Bebas Neue', Impact, 'Arial Narrow', sans-serif",
                  textAlign: 'center',
                  lineHeight: 1.2,
                  textTransform: 'uppercase',
                  letterSpacing: 2,
                  textShadow: '1px 1px 3px rgba(0,0,0,0.15)',
                }}
              >
                {topicText}
              </span>
            </div>
          )}
        </div>
      </div>
    </AbsoluteFill>
  );
};
