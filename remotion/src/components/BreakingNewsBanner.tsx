import React from 'react';
import {
  AbsoluteFill,
  Video,
  Loop,
  useCurrentFrame,
  interpolate,
  spring,
} from 'remotion';

interface BreakingNewsBannerProps {
  bannerText: string;
  topicText?: string;
  urgentKeywords: string[];
  fps: number;
}

/**
 * Layer 2: Breaking News banner.
 *
 * - Uses pre-cropped video template from MinIO (bannerTemplateUrl)
 * - Falls back to topicText overlay in white bar
 * - Topic text is FIXED (no cycling)
 */
export const BreakingNewsBanner: React.FC<BreakingNewsBannerProps & { bannerTemplateUrl?: string }> = ({
  bannerText,
  topicText,
  bannerTemplateUrl,
  fps,
}) => {
  const frame = useCurrentFrame();

  // Entry slide animation
  const slideIn = spring({
    frame,
    fps,
    config: { damping: 15, stiffness: 120, mass: 0.8 },
  });
  const translateY = interpolate(slideIn, [0, 1], [-400, 0]);

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
        {/* Video template banner (cropped to 460px, includes white bar, no black) */}
        {bannerTemplateUrl ? (
          <div
            style={{
              width: '100%',
              height: 460,
              overflow: 'hidden',
              position: 'relative',
            }}
          >
            <Loop durationInFrames={Math.round(85 * fps)}>
              <Video
                src={bannerTemplateUrl}
                muted
                style={{
                  width: '100%',
                  height: '100%',
                  objectFit: 'cover',
                }}
              />
            </Loop>
            {/* Topic text overlaid on the white bar area */}
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
                    fontSize: 36,
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
        ) : (
          /* Fallback CSS banner */
          <div
            style={{
              width: '100%',
              height: 160,
              background: 'linear-gradient(180deg, #DC2626 0%, #991B1B 100%)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: 20,
            }}
          >
            <div style={{ backgroundColor: '#B91C1C', border: '4px solid #FCD34D', borderRadius: 6, padding: '10px 30px' }}>
              <span style={{ color: '#FFF', fontSize: 64, fontWeight: 900, fontFamily: 'Inter, Arial Black, sans-serif', letterSpacing: 6 }}>BREAKING</span>
            </div>
            <div style={{ backgroundColor: '#FCD34D', borderRadius: 6, padding: '10px 30px' }}>
              <span style={{ color: '#000', fontSize: 64, fontWeight: 900, fontFamily: 'Inter, Arial Black, sans-serif', letterSpacing: 6 }}>NEWS</span>
            </div>
          </div>
        )}

        {/* White headline bar — only when NO video template (fallback) */}
        {!bannerTemplateUrl && (
        <div
          style={{
            width: '100%',
            minHeight: 110,
            backgroundColor: '#FFFFFF',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            padding: '16px 40px',
            transform: `translateY(${headlineY}px)`,
            boxShadow: '0 6px 20px rgba(0,0,0,0.35)',
          }}
        >
          <span
            style={{
              color: '#111111',
              fontSize: 40,
              fontWeight: 800,
              fontFamily: 'Inter, Arial, sans-serif',
              textAlign: 'center',
              lineHeight: 1.2,
              textTransform: 'uppercase',
            }}
          >
            {headlineText}
          </span>
        </div>
        )}
      </div>
    </AbsoluteFill>
  );
};
