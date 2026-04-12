import React from 'react';
import {
  AbsoluteFill,
  useCurrentFrame,
  interpolate,
  spring,
  useVideoConfig,
} from 'remotion';

interface BreakingNewsBannerProps {
  bannerText: string;
  topicText?: string;
  urgentKeywords: string[];
  fps: number;
}

/**
 * Layer 2: Large BREAKING NEWS banner (matches reference video size).
 *
 * - Red gradient banner ~160px with large BREAKING/NEWS text
 * - Blue "LIVE STREAMING" ticker bar ~40px
 * - White headline bar ~110px with FIXED topic text
 * - Total height: ~310px
 */
export const BreakingNewsBanner: React.FC<BreakingNewsBannerProps> = ({
  bannerText,
  topicText,
  fps,
}) => {
  const frame = useCurrentFrame();
  const { width } = useVideoConfig();

  // ── Entry animation ──
  const slideIn = spring({
    frame,
    fps,
    config: { damping: 15, stiffness: 120, mass: 0.8 },
  });
  const translateY = interpolate(slideIn, [0, 1], [-350, 0]);

  // ── Pulsing glow ──
  const glowOpacity = interpolate(
    Math.sin(frame * 0.15),
    [-1, 1],
    [0.75, 1],
  );

  // ── Scrolling ticker ──
  const tickerOffset = interpolate(
    frame,
    [0, 9999],
    [width, -width * 4],
    { extrapolateRight: 'extend' },
  );

  // ── Headline: FIXED topic ──
  const headlineText = topicText || bannerText || 'BREAKING NEWS';

  // ── Headline delayed spring ──
  const headlineSlide = spring({
    frame: frame - 10,
    fps,
    config: { damping: 18, stiffness: 100, mass: 0.6 },
  });
  const headlineY = interpolate(headlineSlide, [0, 1], [-100, 0]);

  return (
    <AbsoluteFill style={{ justifyContent: 'flex-start' }}>
      <div
        style={{
          transform: `translateY(${translateY}px)`,
          width: '100%',
        }}
      >
        {/* ── Red banner with BREAKING / NEWS ── */}
        <div
          style={{
            width: '100%',
            height: 160,
            background: 'linear-gradient(180deg, #DC2626 0%, #991B1B 100%)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            gap: 20,
            position: 'relative',
            overflow: 'hidden',
            opacity: glowOpacity,
            boxShadow: '0 6px 30px rgba(220, 38, 38, 0.7)',
          }}
        >
          {/* Animated pattern */}
          <div
            style={{
              position: 'absolute',
              inset: 0,
              background:
                'repeating-linear-gradient(90deg, transparent, transparent 40px, rgba(255,255,255,0.03) 40px, rgba(255,255,255,0.03) 42px)',
              transform: `translateX(${(frame * 0.5) % 42}px)`,
            }}
          />

          {/* World map dots pattern overlay */}
          <div
            style={{
              position: 'absolute',
              inset: 0,
              background: 'radial-gradient(circle 2px, rgba(255,255,255,0.15) 1px, transparent 1px)',
              backgroundSize: '20px 20px',
              opacity: 0.5,
            }}
          />

          {/* BREAKING */}
          <div
            style={{
              backgroundColor: '#B91C1C',
              border: '4px solid #FCD34D',
              borderRadius: 6,
              padding: '10px 30px',
              zIndex: 1,
            }}
          >
            <span
              style={{
                color: '#FFFFFF',
                fontSize: 64,
                fontWeight: 900,
                fontFamily: 'Inter, Arial Black, sans-serif',
                letterSpacing: 6,
                textTransform: 'uppercase',
              }}
            >
              BREAKING
            </span>
          </div>

          {/* NEWS */}
          <div
            style={{
              backgroundColor: '#FCD34D',
              borderRadius: 6,
              padding: '10px 30px',
              zIndex: 1,
            }}
          >
            <span
              style={{
                color: '#000000',
                fontSize: 64,
                fontWeight: 900,
                fontFamily: 'Inter, Arial Black, sans-serif',
                letterSpacing: 6,
                textTransform: 'uppercase',
              }}
            >
              NEWS
            </span>
          </div>
        </div>

        {/* ── Blue ticker line (LIVE STREAMING) ── */}
        <div
          style={{
            width: '100%',
            height: 40,
            background: 'linear-gradient(180deg, #1E3A5F 0%, #0F2340 100%)',
            overflow: 'hidden',
            display: 'flex',
            alignItems: 'center',
            position: 'relative',
          }}
        >
          <div
            style={{
              whiteSpace: 'nowrap',
              transform: `translateX(${tickerOffset}px)`,
              color: '#FFFFFF',
              fontSize: 16,
              fontWeight: 700,
              fontFamily: 'Inter, Arial, sans-serif',
              letterSpacing: 3,
              textTransform: 'uppercase',
            }}
          >
            {'★ LIVE STREAMING ★ BREAKING NEWS ★ LATEST UPDATE ★ LIVE STREAMING ★ BREAKING NEWS ★ LATEST UPDATE ★ LIVE STREAMING ★ BREAKING NEWS ★ '}
          </div>
          {/* LIVE badge */}
          <div
            style={{
              position: 'absolute',
              right: 20,
              backgroundColor: '#DC2626',
              borderRadius: 4,
              padding: '4px 12px',
              display: 'flex',
              alignItems: 'center',
              gap: 6,
            }}
          >
            <div
              style={{
                width: 8,
                height: 8,
                borderRadius: '50%',
                backgroundColor: '#FFFFFF',
                opacity: interpolate(Math.sin(frame * 0.2), [-1, 1], [0.3, 1]),
              }}
            />
            <span
              style={{
                color: '#FFFFFF',
                fontSize: 14,
                fontWeight: 800,
                letterSpacing: 1,
              }}
            >
              LIVE
            </span>
          </div>
        </div>

        {/* ── White headline bar — FIXED topic ── */}
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
              fontSize: 42,
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
      </div>
    </AbsoluteFill>
  );
};
