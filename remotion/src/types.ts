export interface BRollItem {
  /** URL to the b-roll video or image */
  url: string;
  /** Start frame for this b-roll clip */
  startFrame: number;
  /** Duration in frames */
  durationInFrames: number;
  /** Optional alt text / description */
  alt?: string;
}

export interface CaptionWord {
  /** The word text */
  word: string;
  /** Start time in seconds */
  start: number;
  /** End time in seconds */
  end: number;
  /** Confidence score 0-1 */
  confidence?: number;
}

export interface SceneBlock {
  /** Unique scene identifier */
  id: string;
  /** Scene type: avatar talking, b-roll overlay, text card, etc. */
  type: 'avatar' | 'broll' | 'text_card' | 'transition';
  /** Start frame */
  startFrame: number;
  /** Duration in frames */
  durationInFrames: number;
  /** Optional text content for text_card scenes */
  text?: string;
  /** Index into brolls array if type is 'broll' */
  brollIndex?: number;
}

export interface SfxItem {
  /** URL to the sound effect audio file */
  url: string;
  /** Frame at which to play this SFX */
  startFrame: number;
  /** Volume 0-1 */
  volume?: number;
}

export interface CompositionProps extends Record<string, unknown> {
  /** Unique job identifier */
  jobId: string;
  /** Video model/template to use */
  model: 'news_tradicional' | 'news_jornalistico' | 'news_ice';
  /** Frames per second */
  fps: number;
  /** Video width in pixels */
  width: number;
  /** Video height in pixels */
  height: number;
  /** Total duration in frames */
  durationInFrames: number;
  /** URL to the TTS audio file */
  ttsAudioUrl: string;
  /** URL to the avatar video file */
  avatarVideoUrl: string;
  /** B-roll clips to overlay */
  brolls: BRollItem[];
  /** Word-level captions for subtitles */
  captions: CaptionWord[];
  /** Scene layout blocks */
  scenes: SceneBlock[];
  /** Sound effects */
  sfx: SfxItem[];
  /** URL to background music track */
  musicUrl: string;
  /** Text for the news banner/ticker */
  bannerText: string;
  /** Topic headline shown in white bar below the banner */
  topicText?: string;
  /** Keywords to highlight as urgent */
  urgentKeywords: string[];
}
