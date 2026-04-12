import React from 'react';
import {
  AbsoluteFill,
  useCurrentFrame,
  interpolate,
  spring,
  useVideoConfig,
} from 'remotion';

interface BreakingNewsBannerProps {
  /** Primary banner text, e.g. "BREAKING NEWS" */
  bannerText: string;
  /** Topic headline shown below the red banner — stays FIXED */
  topicText?: string;
  /** Keywords (unused — topic stays static) */
  urgentKeywords: string[];
  fps: number;
}

/**
 * Layer 2: Animated BREAKING NEWS banner.
 *
 * - Slides in from top with spring animation.
 * - Large red gradient banner with pulsing glow.
 * - "BREAKING" in red box, "NEWS" in yellow box.
 * - Scrolling ticker underneath.
 * - White headline bar with FIXED topic text (no cycling).
 */
export const BreakingNewsBanner: React.FC<BreakingNewsBannerProps> = ({
  bannerText,
  topicText,
  fps,
}) => {
  const frame = useCurrentFrame();
  const { width } = useVideoConfig();

  // ── Entry animation: slide down from top ──
  const slideIn = spring({
    frame,
    fps,
    config: { damping: 15, stiffness: 120, mass: 0.8 },
  });
  const translateY = interpolate(slideIn, [0, 1], [-250, 0]);

  // ── Pulsing glow ──
  const glowOpacity = interpolate(
    Math.sin(frame * 0.15),
    [-1, 1],
    [0.7, 1],
  );

  // ── Scrolling ticker ──
  const tickerOffset = interpolate(
    frame,
    [0, 9999],
    [width, -width * 4],
    { extrapolateRight: 'extend' },
  );

  // ── Headline: FIXED topic text ──
  const headlineText = topicText || bannerText || 'BREAKING NEWS';

  // ── Headline entry (delayed spring) ──
  const headlineSlide = spring({
    frame: frame - 8,
    fps,
    config: { damping: 18, stiffness: 100, mass: 0.6 },
  });
  const headlineY = interpolate(headlineSlide, [0, 1], [-80, 0]);

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
            height: 120,
            background: 'linear-gradient(180deg, #DC2626 0%, #991B1B 100%)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            gap: 16,
            position: 'relative',
            overflow: 'hidden',
            opacity: glowOpacity,
            boxShadow: '0 6px 24px rgba(220, 38, 38, 0.7)',
          }}
        >
          {/* Animated background pattern */}
          <div
            style={{
              position: 'absolute',
              inset: 0,
              background:
                'repeating-linear-gradient(90deg, transparent, transparent 40px, rgba(255,255,255,0.03) 40px, rgba(255,255,255,0.03) 42px)',
              transform: `translateX(${(frame * 0.5) % 42}px)`,
            }}
          />

          {/* BREAKING */}
          <div
            style={{
              backgroundColor: '#B91C1C',
              border: '3px solid #FCD34D',
              borderRadius: 4,
              padding: '8px 24px',
              zIndex: 1,
            }}
          >
            <span
              style={{
                color: '#FFFFFF',
                fontSize: 48,
                fontWeight: 900,
                fontFamily: 'Inter, Arial Black, sans-serif',
                letterSpacing: 5,
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
              borderRadius: 4,
              padding: '8px 24px',
              zIndex: 1,
            }}
          >
            <span
              style={{
                color: '#000000',
                fontSize: 48,
                fontWeight: 900,
                fontFamily: 'Inter, Arial Black, sans-serif',
                letterSpacing: 5,
                textTransform: 'uppercase',
              }}
            >
              NEWS
            </span>
          </div>
        </div>

        {/* ── Ticker line ── */}
        <div
          style={{
            width: '100%',
            height: 32,
            backgroundColor: '#7F1D1D',
            overflow: 'hidden',
            display: 'flex',
            alignItems: 'center',
          }}
        >
          <div
            style={{
              whiteSpace: 'nowrap',
              transform: `translateX(${tickerOffset}px)`,
              color: '#FCD34D',
              fontSize: 16,
              fontWeight: 700,
              fontFamily: 'Inter, Arial, sans-serif',
              letterSpacing: 2,
              textTransform: 'uppercase',
            }}
          >
            {'★ BREAKING NEWS ★ LATEST UPDATE ★ BREAKING NEWS ★ LATEST UPDATE ★ BREAKING NEWS ★ LATEST UPDATE ★ BREAKING NEWS ★ LATEST UPDATE ★ '}
          </div>
        </div>

        {/* ── White headline bar — FIXED topic ── */}
        <div
          style={{
            width: '100%',
            minHeight: 90,
            backgroundColor: '#FFFFFF',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            padding: '12px 36px',
            transform: `translateY(${headlineY}px)`,
            boxShadow: '0 4px 16px rgba(0,0,0,0.35)',
          }}
        >
          <span
            style={{
              color: '#111111',
              fontSize: 36,
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
