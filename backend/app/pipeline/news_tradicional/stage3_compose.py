import json
import os
import shutil
import subprocess
import tempfile

from app.processing.asset_manager import asset_manager
from app.utils.logger import logger


async def compose_and_render(
    job_id: str,
    script: str,
    tts_audio_minio_path: str,
    avatar_data: dict,  # From stage2_track_a: {avatar_minio_path, duration}
    broll_data: dict,   # From stage2_track_b: {word_timestamps, scenes, broll_paths, urgent_keywords, total_duration}
    music_path: str | None = None,  # MinIO path to background music
    sfx_paths: dict | None = None,  # {sfx_type: MinIO path}
) -> str:
    """Stage 3: Build Remotion composition props and render final video.

    1. Convert all MinIO paths to presigned URLs
    2. Build CompositionProps JSON matching remotion/src/types.ts
    3. Write JSON to temp file
    4. Call Remotion render via subprocess (npx tsx remotion/src/render.ts)
    5. Upload rendered .mp4 to MinIO
    6. Return MinIO path
    """
    logger.info("[Stage 3] Starting composition for job {jid}", jid=job_id)

    # ── Presigned URLs for all assets ────────────────────────────────
    tts_audio_url = asset_manager.get_asset_url(tts_audio_minio_path)

    avatar_video_url = ""
    if avatar_data.get("avatar_minio_path"):
        avatar_video_url = asset_manager.get_asset_url(
            avatar_data["avatar_minio_path"]
        )

    # ── B-Roll items with presigned URLs ─────────────────────────────
    fps = 30
    broll_duration = 6  # seconds per B-Roll clip (full Grok take)
    brolls: list[dict] = []
    for idx in sorted(broll_data.get("broll_paths", {}).keys()):
        path = broll_data["broll_paths"][idx]
        url = asset_manager.get_asset_url(path)
        start_frame = idx * broll_duration * fps
        end_frame = start_frame + (broll_duration * fps)
        brolls.append(
            {
                "url": url,
                "startFrame": start_frame,
                "endFrame": end_frame,
            }
        )

    # ── Caption words from word timestamps ───────────────────────────
    captions: list[dict] = []
    for wt in broll_data.get("word_timestamps", []):
        captions.append(
            {
                "word": wt["word"],
                "startTime": wt["start"],
                "endTime": wt["end"],
            }
        )

    # ── Scenes ───────────────────────────────────────────────────────
    scenes: list[dict] = []
    for scene in broll_data.get("scenes", []):
        scenes.append(
            {
                "startTime": scene.get("start_time", 0),
                "endTime": scene.get("end_time", 3),
                "description": scene.get("description", ""),
                "keyword": scene.get("broll_prompt", "")[:50],
            }
        )

    # ── SFX items ────────────────────────────────────────────────────
    sfx: list[dict] = []
    for scene in broll_data.get("scenes", []):
        sfx_type = scene.get("sfx")
        if sfx_type and sfx_paths and sfx_type in sfx_paths:
            sfx_url = asset_manager.get_asset_url(sfx_paths[sfx_type])
            start_frame = int(scene.get("start_time", 0) * fps)
            sfx.append(
                {
                    "url": sfx_url,
                    "startFrame": start_frame,
                    "volume": 0.35,
                }
            )

    # ── Music URL ────────────────────────────────────────────────────
    music_url = ""
    if music_path:
        music_url = asset_manager.get_asset_url(music_path)

    # ── Calculate duration ───────────────────────────────────────────
    total_duration = broll_data.get(
        "total_duration", avatar_data.get("duration", 60)
    )
    duration_in_frames = int(total_duration * fps)

    # ── Build composition props ──────────────────────────────────────
    composition_props = {
        "jobId": job_id,
        "model": "news_tradicional",
        "fps": fps,
        "width": 1080,
        "height": 1920,
        "durationInFrames": duration_in_frames,
        "ttsAudioUrl": tts_audio_url,
        "avatarVideoUrl": avatar_video_url,
        "brolls": brolls,
        "captions": captions,
        "scenes": scenes,
        "sfx": sfx,
        "musicUrl": music_url,
        "bannerText": "BREAKING NEWS",
        "topicText": script.split('\n')[0][:120] if script else "",
        "urgentKeywords": broll_data.get("urgent_keywords", []),
    }

    # Save props JSON to MinIO for debugging / traceability
    props_json = json.dumps(composition_props, indent=2, ensure_ascii=False)
    asset_manager.save_asset(
        job_id,
        "stage3_render",
        "composition_props.json",
        props_json.encode("utf-8"),
        "application/json",
    )

    # ── Write props to temp file for Remotion ────────────────────────
    tmp_dir = tempfile.mkdtemp(prefix=f"render_{job_id}_")
    props_file = os.path.join(tmp_dir, "props.json")
    output_file = os.path.join(tmp_dir, "output.mp4")

    with open(props_file, "w", encoding="utf-8") as f:
        f.write(props_json)

    # ── Resolve Remotion directory ───────────────────────────────────
    # Try several common locations relative to the backend working dir
    candidates = [
        os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "remotion")
        ),
        os.path.join(os.getcwd(), "..", "remotion"),
        os.path.join(os.getcwd(), "remotion"),
    ]
    remotion_dir: str | None = None
    for candidate in candidates:
        normalised = os.path.normpath(candidate)
        if os.path.isdir(normalised):
            remotion_dir = normalised
            break

    if remotion_dir is None:
        # Fallback -- use first candidate and let subprocess fail with a
        # clear error rather than a confusing NoneType error.
        remotion_dir = os.path.normpath(candidates[0])
        logger.warning(
            "[Stage 3] Remotion directory not found at any candidate; "
            "using {d}",
            d=remotion_dir,
        )

    # ── Call Remotion render ─────────────────────────────────────────
    logger.info(
        "[Stage 3] Rendering video ({frames} frames, {dur:.1f}s)...",
        frames=duration_in_frames,
        dur=total_duration,
    )

    render_cmd = [
        "npx",
        "tsx",
        os.path.join(remotion_dir, "src", "render.ts"),
        "--input",
        props_file,
        "--output",
        output_file,
    ]

    proc = subprocess.run(
        render_cmd,
        capture_output=True,
        text=True,
        timeout=600,  # 10 min max
        cwd=remotion_dir,
    )

    if proc.returncode != 0:
        error_tail = proc.stderr[-500:] if proc.stderr else "(no stderr)"
        logger.error("[Stage 3] Remotion render failed: {err}", err=error_tail)
        raise RuntimeError(f"Remotion render failed: {error_tail}")

    if not os.path.exists(output_file):
        raise RuntimeError(
            "[Stage 3] Render completed but output file not found"
        )

    # ── Upload rendered video to MinIO ───────────────────────────────
    output_minio_path = asset_manager.save_asset_from_file(
        job_id, "output", "final.mp4", output_file, "video/mp4"
    )

    logger.success(
        "[Stage 3] Video rendered and uploaded: {path}", path=output_minio_path
    )

    # ── Cleanup ──────────────────────────────────────────────────────
    shutil.rmtree(tmp_dir, ignore_errors=True)

    return output_minio_path
