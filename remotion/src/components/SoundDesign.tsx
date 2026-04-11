import React from 'react';
import { Audio, Sequence } from 'remotion';
import type { SfxItem } from '../types';

interface SoundDesignProps {
  /** URL to the TTS narration audio */
  ttsAudioUrl: string;
  /** URL to the background music track (looped) */
  musicUrl: string;
  /** Sound effects to play at specific frames */
  sfx: SfxItem[];
  fps: number;
  durationInFrames: number;
}

/** Default duration for each SFX clip in frames (2 seconds at 30fps = 60 frames) */
const SFX_DURATION_SECONDS = 2;

/**
 * Layer 4: Audio mixing layer.
 *
 * - Main TTS voice at full volume.
 * - Suspense music loop at ~12% volume (static ducking).
 * - SFX (whoosh, ding) at transition points from scene director data.
 */
export const SoundDesign: React.FC<SoundDesignProps> = ({
  ttsAudioUrl,
  musicUrl,
  sfx,
  fps,
  durationInFrames,
}) => {
  const sfxDurationFrames = Math.round(SFX_DURATION_SECONDS * fps);

  return (
    <>
      {/* Main TTS narration voice */}
      {ttsAudioUrl && <Audio src={ttsAudioUrl} volume={1.0} />}

      {/* Background suspense music - looped, low enough to not compete with narrator */}
      {musicUrl && (
        <Audio
          src={musicUrl}
          volume={0.08}
          loop
        />
      )}

      {/* SFX at specific frame positions - slightly louder for impact but not overpowering */}
      {sfx.map((sfxItem, i) => {
        if (!sfxItem.url) return null;
        const volume = sfxItem.volume ?? 0.35;
        return (
          <Sequence
            key={i}
            from={sfxItem.startFrame}
            durationInFrames={sfxDurationFrames}
          >
            <Audio src={sfxItem.url} volume={volume} />
          </Sequence>
        );
      })}
    </>
  );
};
