import React from 'react';
import { AbsoluteFill, useCurrentFrame } from 'remotion';
import type { CaptionWord } from '../types';
import { CAPTION_STYLE, COLORS, FONTS, TEXT_STROKE_SHADOW } from '../utils/styles';

interface CaptionsProps {
  captions: CaptionWord[];
  fps: number;
}

/**
 * Layer 3: Word-by-word synchronized captions.
 *
 * - Positioned above the avatar's head (center, ~48% from bottom).
 * - Current word: yellow (#FFD700) with black stroke, slightly scaled up.
 * - Previous words in the same group: white with black stroke.
 * - Upcoming words in the same group: dimmed white.
 * - Shows a window of words grouped into lines of 4 words, 2 lines visible.
 * - Each word appears in sync with Whisper timestamps.
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

  // If before any words, don't show captions
  if (currentWordIndex === -1) {
    return null;
  }

  const { wordsPerLine, linesVisible } = CAPTION_STYLE;
  const windowSize = wordsPerLine * linesVisible;

  // Calculate which group of words to show
  const groupStart = Math.floor(currentWordIndex / windowSize) * windowSize;
  const visibleWords = captions.slice(groupStart, groupStart + windowSize);

  // Split into lines
  const lines: CaptionWord[][] = [];
  for (let i = 0; i < visibleWords.length; i += wordsPerLine) {
    lines.push(visibleWords.slice(i, i + wordsPerLine));
  }

  return (
    <AbsoluteFill
      style={{
        justifyContent: 'flex-start',
        alignItems: 'center',
        paddingTop: '38%',
      }}
    >
      <div
        style={{
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          gap: 8,
          maxWidth: CAPTION_STYLE.maxWidth,
          padding: '0 40px',
        }}
      >
        {lines.map((line, lineIdx) => (
          <div
            key={lineIdx}
            style={{
              display: 'flex',
              gap: 24,
              justifyContent: 'center',
              flexWrap: 'wrap',
            }}
          >
            {line.map((word, wordIdx) => {
              const globalIdx =
                groupStart + lineIdx * wordsPerLine + wordIdx;
              const isCurrent = globalIdx === currentWordIndex;
              const isPast = globalIdx < currentWordIndex;

              return (
                <span
                  key={globalIdx}
                  style={{
                    fontSize: CAPTION_STYLE.fontSize,
                    fontWeight: CAPTION_STYLE.fontWeight,
                    fontFamily: FONTS.caption,
                    lineHeight: CAPTION_STYLE.lineHeight,
                    color: isCurrent
                      ? COLORS.captionYellow
                      : isPast
                        ? COLORS.captionWhite
                        : COLORS.captionDimmed,
                    textShadow: TEXT_STROKE_SHADOW,
                    transform: isCurrent ? 'scale(1.1)' : 'scale(1)',
                    textTransform: 'uppercase',
                    display: 'inline-block',
                    marginRight: 20,
                    paddingLeft: 4,
                    paddingRight: 4,
                  }}
                >
                  {word.word}{' '}
                </span>
              );
            })}
          </div>
        ))}
      </div>
    </AbsoluteFill>
  );
};
