import React from 'react';
import { AbsoluteFill, useCurrentFrame } from 'remotion';
import type { CaptionWord } from '../types';
import { CAPTION_STYLE, COLORS, FONTS, TEXT_STROKE_SHADOW } from '../utils/styles';

interface CaptionsProps {
  captions: CaptionWord[];
  fps: number;
}

/**
 * Layer 3: Word-by-word synchronized captions (karaoke style).
 *
 * - 2 words visible at a time
 * - Current word: yellow, others: white
 * - Positioned above avatar head (~55% from top)
 */
export const Captions: React.FC<CaptionsProps> = ({ captions, fps }) => {
  const frame = useCurrentFrame();

  if (captions.length === 0) {
    return null;
  }

  const currentTime = frame / fps;

  // Find current word index
  let currentWordIndex = -1;
  for (let i = 0; i < captions.length; i++) {
    if (currentTime >= captions[i].start && currentTime <= captions[i].end) {
      currentWordIndex = i;
      break;
    }
  }

  // If between words, find the most recently ended word
  if (currentWordIndex === -1) {
    for (let i = captions.length - 1; i >= 0; i--) {
      if (currentTime > captions[i].end) {
        currentWordIndex = i;
        break;
      }
    }
  }

  if (currentWordIndex === -1) {
    return null;
  }

  const { wordsPerLine, linesVisible } = CAPTION_STYLE;
  const windowSize = wordsPerLine * linesVisible;

  // Calculate which group of words to show
  const groupStart = Math.floor(currentWordIndex / windowSize) * windowSize;
  const visibleWords = captions.slice(groupStart, groupStart + windowSize);

  return (
    <AbsoluteFill
      style={{
        justifyContent: 'flex-start',
        alignItems: 'center',
        paddingTop: '60%',
      }}
    >
      <div
        style={{
          textAlign: 'center',
          maxWidth: CAPTION_STYLE.maxWidth,
          padding: '0 40px',
        }}
      >
        {visibleWords.map((word, idx) => {
          const globalIdx = groupStart + idx;
          const isCurrent = globalIdx === currentWordIndex;
          const isPast = globalIdx < currentWordIndex;

          return (
            <span
              key={globalIdx}
              style={{
                fontSize: CAPTION_STYLE.fontSize,
                fontWeight: CAPTION_STYLE.fontWeight,
                fontFamily: FONTS.caption,
                lineHeight: 1.3,
                color: isCurrent
                  ? COLORS.captionYellow
                  : isPast
                    ? COLORS.captionWhite
                    : COLORS.captionDimmed,
                textShadow: TEXT_STROKE_SHADOW,
                transform: isCurrent ? 'scale(1.1)' : 'scale(1)',
                textTransform: 'uppercase',
                display: 'inline',
              }}
            >
              {word.word}{idx < visibleWords.length - 1 ? ' ' : ''}
            </span>
          );
        })}
      </div>
    </AbsoluteFill>
  );
};
