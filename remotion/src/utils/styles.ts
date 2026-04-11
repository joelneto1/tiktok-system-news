/**
 * Shared style constants for the News Tradicional video template.
 */

export const COLORS = {
  breakingNewsRed: '#DC2626',
  breakingNewsBg: '#1a1a2e',
  captionYellow: '#FFD700',
  captionWhite: '#FFFFFF',
  captionStroke: '#000000',
  captionDimmed: 'rgba(255, 255, 255, 0.3)',
  bannerBg: 'rgba(220, 38, 38, 0.95)',
  bannerBorder: '#FCD34D',
  bannerText: '#FFFFFF',
  background: '#000000',
} as const;

export const FONTS = {
  caption: 'Inter, Arial, sans-serif',
  banner: 'Inter, Arial, sans-serif',
} as const;

export const CAPTION_STYLE = {
  fontSize: 52,
  fontWeight: 800 as const,
  strokeWidth: 3,
  lineHeight: 1.2,
  maxWidth: 900,
  wordsPerLine: 4,
  linesVisible: 2,
} as const;

export const BANNER_STYLE = {
  height: 60,
  fontSize: 26,
  fontWeight: 800 as const,
  letterSpacing: 3,
  borderWidth: 3,
} as const;

/**
 * CSS text-shadow that simulates a thick black stroke around text.
 */
export const TEXT_STROKE_SHADOW = `
  -3px -3px 0 ${COLORS.captionStroke},
   3px -3px 0 ${COLORS.captionStroke},
  -3px  3px 0 ${COLORS.captionStroke},
   3px  3px 0 ${COLORS.captionStroke},
  -3px  0   0 ${COLORS.captionStroke},
   3px  0   0 ${COLORS.captionStroke},
   0   -3px 0 ${COLORS.captionStroke},
   0    3px 0 ${COLORS.captionStroke}
`.trim();
