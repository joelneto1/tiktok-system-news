import React from 'react';
import {
  AbsoluteFill,
  useCurrentFrame,
  interpolate,
  spring,
  useVideoConfig,
} from 'remotion';
import { secondsToFrames } from '../utils/timing';

interface BreakingNewsBannerProps {
  /** Primary banner text, e.g. "BREAKING NEWS" */
  bannerText: string;
  /** Topic headline shown below the red banner */
  topicText?: string;
  /** Keywords to cycle after the static period */
  urgentKeywords: string[];
  fps: number;
}

/**
 * Layer 2: Animated BREAKING NEWS banner.
 *
 * - Slides in from top with spring animation on entry.
 * - Red gradient banner with pulsing glow effect.
 * - "BREAKING" in red box, "NEWS" in yellow box (TV news style).
 * - Scrolling ticker line underneath.
 * - White headline bar below with topic text.
 * - After 15s, cycles urgent keywords in the headline.
 */
export const BreakingNewsBanner: React.FC<BreakingNewsBannerProps> = ({
  bannerText,
  topicText,
  urgentKeywords,
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
  const translateY = interpolate(slideIn, [0, 1], [-200, 0]);

  // ── Pulsing glow on the red banner ──
  const glowOpacity = interpolate(
    Math.sin(frame * 0.15),
    [-1, 1],
    [0.6, 1],
  );

  // ── Scrolling ticker line ──
  const tickerOffset = interpolate(
    frame,
    [0, 9999],
    [width, -width * 4],
    { extrapolateRight: 'extend' },
  );

  // ── Headline text cycling ──
  const staticEndFrame = secondsToFrames(15, fps);
  let headlineText = topicText || bannerText || 'BREAKING NEWS';

  if (frame > staticEndFrame && urgentKeywords.length > 0) {
    const cycleFrames = secondsToFrames(4, fps);
    const allTexts = [headlineText, ...urgentKeywords];
    const cycleIndex =
      Math.floor((frame - staticEndFrame) / cycleFrames) % allTexts.length;
    headlineText = allTexts[cycleIndex];

    // Fade transition between texts
    const cycleProgress = ((frame - staticEndFrame) % cycleFrames) / cycleFrames;
    // eslint-disable-next-line @typescript-eslint/no-unused-vars
    const _fadeIn = cycleProgress < 0.1 ? cycleProgress / 0.1 : 1;
  }

  // ── Headline entry (delayed spring) ──
  const headlineSlide = spring({
    frame: frame - 8,
    fps,
    config: { damping: 18, stiffness: 100, mass: 0.6 },
  });
  const headlineY = interpolate(headlineSlide, [0, 1], [-60, 0]);

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
            height: 90,
            background: 'linear-gradient(180deg, #DC2626 0%, #991B1B 100%)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            gap: 12,
            position: 'relative',
            overflow: 'hidden',
            opacity: glowOpacity,
            boxShadow: '0 4px 20px rgba(220, 38, 38, 0.6)',
          }}
        >
          {/* Animated background pattern (subtle moving lines) */}
          <div
            style={{
              position: 'absolute',
              inset: 0,
              background:
                'repeating-linear-gradient(90deg, transparent, transparent 40px, rgba(255,255,255,0.03) 40px, rgba(255,255,255,0.03) 42px)',
              transform: `translateX(${(frame * 0.5) % 42}px)`,
            }}
          />

          {/* BREAKING text in red box */}
          <div
            style={{
              backgroundColor: '#B91C1C',
              border: '3px solid #FCD34D',
              borderRadius: 4,
              padding: '6px 18px',
              zIndex: 1,
            }}
          >
            <span
              style={{
                color: '#FFFFFF',
                fontSize: 38,
                fontWeight: 900,
                fontFamily: 'Inter, Arial Black, sans-serif',
                letterSpacing: 4,
                textTransform: 'uppercase',
              }}
            >
              BREAKING
            </span>
          </div>

          {/* NEWS text in yellow box */}
          <div
            style={{
              backgroundColor: '#FCD34D',
              borderRadius: 4,
              padding: '6px 18px',
              zIndex: 1,
            }}
          >
            <span
              style={{
                color: '#000000',
                fontSize: 38,
                fontWeight: 900,
                fontFamily: 'Inter, Arial Black, sans-serif',
                letterSpacing: 4,
                textTransform: 'uppercase',
              }}
            >
              NEWS
            </span>
          </div>
        </div>

        {/* ── Ticker line (thin red bar with scrolling text) ── */}
        <div
          style={{
            width: '100%',
            height: 28,
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
              fontSize: 14,
              fontWeight: 700,
              fontFamily: 'Inter, Arial, sans-serif',
              letterSpacing: 2,
              textTransform: 'uppercase',
            }}
          >
            {'★ BREAKING NEWS ★ LATEST UPDATE ★ BREAKING NEWS ★ LATEST UPDATE ★ BREAKING NEWS ★ LATEST UPDATE ★ BREAKING NEWS ★ LATEST UPDATE ★ '}
          </div>
        </div>

        {/* ── White headline bar with topic ── */}
        <div
          style={{
            width: '100%',
            minHeight: 70,
            backgroundColor: '#FFFFFF',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            padding: '10px 30px',
            transform: `translateY(${headlineY}px)`,
            boxShadow: '0 4px 12px rgba(0,0,0,0.3)',
          }}
        >
          <span
            style={{
              color: '#111111',
              fontSize: 30,
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
