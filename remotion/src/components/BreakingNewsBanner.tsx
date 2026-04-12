import React from 'react';
import {
  AbsoluteFill,
  Video,
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
 * - No entry animation (fixed from frame 0)
 * - staticFile for local serving
 * - Topic text large, 2 lines, prominent on white bar
 */
export const BreakingNewsBanner: React.FC<BreakingNewsBannerProps> = ({
  bannerText,
  topicText,
}) => {
  const headlineText = topicText || bannerText || 'BREAKING NEWS';

  return (
    <AbsoluteFill style={{ justifyContent: 'flex-start', pointerEvents: 'none' }}>
      <div style={{ width: '100%' }}>
        {/* Video template banner — fixed, no animation */}
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

          {/* Topic text — large, 2 lines, prominent */}
          {topicText && (
            <div
              style={{
                position: 'absolute',
                bottom: 10,
                left: 0,
                width: '100%',
                height: 140,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                padding: '0 30px',
              }}
            >
              <span
                style={{
                  color: '#111111',
                  fontSize: 46,
                  fontWeight: 700,
                  fontFamily: "'Bebas Neue', Impact, 'Arial Narrow', sans-serif",
                  textAlign: 'center',
                  lineHeight: 1.15,
                  textTransform: 'uppercase',
                  letterSpacing: 3,
                  textShadow: '1px 1px 4px rgba(0,0,0,0.2)',
                }}
              >
                {headlineText}
              </span>
            </div>
          )}
        </div>
      </div>
    </AbsoluteFill>
  );
};
