import { bundle } from '@remotion/bundler';
import { renderMedia, selectComposition } from '@remotion/renderer';
import path from 'node:path';
import fs from 'node:fs';
import { z } from 'zod';
import type { CompositionProps } from './types';

// ---------------------------------------------------------------------------
// Zod schema for input validation
// ---------------------------------------------------------------------------

const BRollItemSchema = z.object({
  url: z.string().min(1),
  startFrame: z.number().int().min(0),
  durationInFrames: z.number().int().min(1),
  alt: z.string().optional(),
});

const CaptionWordSchema = z.object({
  word: z.string(),
  start: z.number().min(0),
  end: z.number().min(0),
  confidence: z.number().min(0).max(1).optional(),
});

const SceneBlockSchema = z.object({
  id: z.string(),
  type: z.enum(['avatar', 'broll', 'text_card', 'transition']),
  startFrame: z.number().int().min(0),
  durationInFrames: z.number().int().min(1),
  text: z.string().optional(),
  brollIndex: z.number().int().min(0).optional(),
});

const SfxItemSchema = z.object({
  url: z.string().min(1),
  startFrame: z.number().int().min(0),
  volume: z.number().min(0).max(1).optional(),
});

const CompositionPropsSchema = z.object({
  jobId: z.string().min(1),
  model: z.enum(['news_tradicional', 'news_jornalistico', 'news_ice']),
  fps: z.number().int().min(1).default(30),
  width: z.number().int().min(1).default(1080),
  height: z.number().int().min(1).default(1920),
  durationInFrames: z.number().int().min(1),
  ttsAudioUrl: z.string().default(''),
  avatarVideoUrl: z.string().default(''),
  brolls: z.array(BRollItemSchema).default([]),
  captions: z.array(CaptionWordSchema).default([]),
  scenes: z.array(SceneBlockSchema).default([]),
  sfx: z.array(SfxItemSchema).default([]),
  musicUrl: z.string().default(''),
  bannerText: z.string().default('BREAKING NEWS'),
  topicText: z.string().optional(),
  urgentKeywords: z.array(z.string()).default([]),
  bannerTemplateUrl: z.string().optional(),
});

// ---------------------------------------------------------------------------
// Composition ID mapping
// ---------------------------------------------------------------------------

const COMPOSITION_ID_MAP: Record<CompositionProps['model'], string> = {
  news_tradicional: 'NewsTradicional',
  news_jornalistico: 'NewsJornalistico',
  news_ice: 'NewsIce',
};

// ---------------------------------------------------------------------------
// CLI argument parsing
// ---------------------------------------------------------------------------

function parseArgs(argv: string[]) {
  let inputPath: string | undefined;
  let outputPath = 'out/video.mp4';

  for (let i = 0; i < argv.length; i++) {
    if (argv[i] === '--input' && argv[i + 1]) {
      inputPath = argv[i + 1];
      i++;
    } else if (argv[i] === '--output' && argv[i + 1]) {
      outputPath = argv[i + 1];
      i++;
    }
  }

  return { inputPath, outputPath };
}

// ---------------------------------------------------------------------------
// Main
// ---------------------------------------------------------------------------

async function main() {
  const args = process.argv.slice(2);
  const { inputPath, outputPath } = parseArgs(args);

  // ---- Read raw JSON from file or stdin ----
  let rawJson: string;

  if (inputPath) {
    if (!fs.existsSync(inputPath)) {
      console.error(`[render] Error: input file not found: ${inputPath}`);
      process.exit(1);
    }
    rawJson = fs.readFileSync(inputPath, 'utf-8');
    console.error(`[render] Reading props from file: ${inputPath}`);
  } else {
    console.error('[render] Reading props from stdin...');
    const chunks: Buffer[] = [];
    for await (const chunk of process.stdin) {
      chunks.push(chunk);
    }
    rawJson = Buffer.concat(chunks).toString('utf-8');
  }

  // ---- Parse & validate with Zod ----
  let parsed: unknown;
  try {
    parsed = JSON.parse(rawJson);
  } catch {
    console.error('[render] Error: invalid JSON input');
    process.exit(1);
  }

  const validation = CompositionPropsSchema.safeParse(parsed);
  if (!validation.success) {
    console.error('[render] Validation errors:');
    for (const issue of validation.error.issues) {
      console.error(`  - ${issue.path.join('.')}: ${issue.message}`);
    }
    process.exit(1);
  }

  const props = validation.data as CompositionProps;
  const compositionId = COMPOSITION_ID_MAP[props.model];

  console.error(`[render] Job: ${props.jobId}`);
  console.error(`[render] Model: ${props.model} -> ${compositionId}`);
  console.error(
    `[render] Duration: ${props.durationInFrames} frames (${(props.durationInFrames / props.fps).toFixed(1)}s)`,
  );

  // ---- Bundle the Remotion project ----
  console.error('[render] Bundling...');
  const entryPoint = path.resolve(__dirname, './index.ts');
  const bundleLocation = await bundle({
    entryPoint,
    webpackOverride: (config) => config,
  });
  console.error('[render] Bundle ready.');

  // ---- Select the composition ----
  const composition = await selectComposition({
    serveUrl: bundleLocation,
    id: compositionId,
    inputProps: props as unknown as Record<string, unknown>,
    timeoutInMilliseconds: 120000,
  });

  // ---- Ensure output directory exists ----
  const outputDir = path.dirname(path.resolve(outputPath));
  if (!fs.existsSync(outputDir)) {
    fs.mkdirSync(outputDir, { recursive: true });
  }

  // ---- Render ----
  const resolvedOutput = path.resolve(outputPath);
  console.error(`[render] Rendering ${compositionId} -> ${resolvedOutput}`);
  console.error(
    `[render] Resolution: ${props.width}x${props.height} @ ${props.fps}fps`,
  );

  const dynamicTimeout = Math.max(120000, Math.round(props.durationInFrames / 3) * 1000);
  console.error(`[render] Timeout: ${dynamicTimeout}ms, Concurrency: 50%`);

  await renderMedia({
    composition: {
      ...composition,
      durationInFrames: props.durationInFrames,
      fps: props.fps,
      width: props.width,
      height: props.height,
    },
    serveUrl: bundleLocation,
    codec: 'h264',
    outputLocation: resolvedOutput,
    inputProps: props as unknown as Record<string, unknown>,
    timeoutInMilliseconds: dynamicTimeout,
    concurrency: '50%',
    onProgress: ({ progress }) => {
      const pct = (progress * 100).toFixed(1);
      process.stderr.write(`\r[render] Progress: ${pct}%`);
    },
  });

  console.error('\n[render] Done!');

  // Output final path to stdout (for piping to next process)
  console.log(JSON.stringify({ output: resolvedOutput }));
}

main().catch((err) => {
  console.error('[render] Fatal error:', err);
  process.exit(1);
});
