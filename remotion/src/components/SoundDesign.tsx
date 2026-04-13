import React from 'react';
import { Audio, Sequence, staticFile } from 'remotion';
import type { SfxItem } from '../types';

interface SoundDesignProps {
  ttsAudioUrl: string;
  musicUrl: string;
  sfx: SfxItem[];
  fps: number;
  durationInFrames: number;
}

const SFX_DURATION_SECONDS = 2;

/** Resolve URL: use staticFile for local paths, pass through for HTTP URLs */
function resolveUrl(url: string): string {
  if (!url) return '';
  return url.startsWith('http') ? url : staticFile(url);
}

/**
 * Layer 4: Audio mixing layer.
 * Uses staticFile for local audio files.
 */
export const SoundDesign: React.FC<SoundDesignProps> = ({
  ttsAudioUrl,
  musicUrl,
  sfx,
  fps,
}) => {
  const sfxDurationFrames = Math.round(SFX_DURATION_SECONDS * fps);

  return (
    <>
      {ttsAudioUrl && <Audio src={resolveUrl(ttsAudioUrl)} volume={1.0} />}

      {musicUrl && (
        <Audio src={resolveUrl(musicUrl)} volume={0.08} loop />
      )}

      {sfx.map((sfxItem, i) => {
        if (!sfxItem.url) return null;
        const volume = sfxItem.volume ?? 0.35;
        return (
          <Sequence
            key={i}
            from={sfxItem.startFrame}
            durationInFrames={sfxDurationFrames}
          >
            <Audio src={resolveUrl(sfxItem.url)} volume={volume} />
          </Sequence>
        );
      })}
    </>
  );
};
