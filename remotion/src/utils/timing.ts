import type { BRollItem, CaptionWord, SceneBlock } from '../types';

/**
 * Convert seconds to frames, rounding to the nearest integer.
 */
export const secondsToFrames = (seconds: number, fps: number): number =>
  Math.round(seconds * fps);

/**
 * Convert frames to seconds.
 */
export const framesToSeconds = (frames: number, fps: number): number =>
  frames / fps;

/**
 * Find the current word being spoken at a given frame.
 * Returns the current word, all previous words, and all upcoming words.
 */
export function getWordAtFrame(
  captions: CaptionWord[],
  frame: number,
  fps: number,
): {
  current: CaptionWord | null;
  currentIndex: number;
  previous: CaptionWord[];
  upcoming: CaptionWord[];
} {
  const currentTime = framesToSeconds(frame, fps);

  let currentIndex = -1;

  // Find the word whose time range contains the current time
  for (let i = 0; i < captions.length; i++) {
    if (currentTime >= captions[i].start && currentTime <= captions[i].end) {
      currentIndex = i;
      break;
    }
  }

  // If no exact match, find the most recent word that has ended
  if (currentIndex === -1) {
    for (let i = captions.length - 1; i >= 0; i--) {
      if (currentTime > captions[i].end) {
        currentIndex = i;
        break;
      }
    }
  }

  if (currentIndex === -1) {
    return {
      current: null,
      currentIndex: -1,
      previous: [],
      upcoming: captions,
    };
  }

  return {
    current: captions[currentIndex],
    currentIndex,
    previous: captions.slice(0, currentIndex),
    upcoming: captions.slice(currentIndex + 1),
  };
}

/**
 * Find which scene is active at a given frame.
 */
export function getSceneAtFrame(
  scenes: SceneBlock[],
  frame: number,
  _fps: number,
): SceneBlock | null {
  for (const scene of scenes) {
    if (
      frame >= scene.startFrame &&
      frame < scene.startFrame + scene.durationInFrames
    ) {
      return scene;
    }
  }
  return null;
}

/**
 * Find which B-Roll should be displayed at a given frame.
 */
export function getBRollAtFrame(
  brolls: BRollItem[],
  frame: number,
): BRollItem | null {
  for (const broll of brolls) {
    if (
      frame >= broll.startFrame &&
      frame < broll.startFrame + broll.durationInFrames
    ) {
      return broll;
    }
  }
  return null;
}
