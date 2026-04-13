import json
import os
import shutil
import subprocess
import tempfile

from app.processing.asset_manager import asset_manager
from app.services.minio_client import minio_client
from app.utils.logger import logger


async def compose_and_render(
    job_id: str,
    script: str,
    tts_audio_minio_path: str,
    avatar_data: dict,
    broll_data: dict,
    music_path: str | None = None,
    sfx_paths: dict | None = None,
    topic: str = "",
) -> str:
    """Stage 3: Build Remotion composition props and render final video."""
    logger.info("[Stage 3] Starting composition for job {jid}", jid=job_id)

    fps = 30
    broll_duration = 6

    # ── Presigned URLs for all assets ────────────────────────────────
    tts_audio_url = asset_manager.get_asset_url(tts_audio_minio_path)

    avatar_video_url = ""
    if avatar_data.get("avatar_minio_path"):
        avatar_video_url = asset_manager.get_asset_url(
            avatar_data["avatar_minio_path"]
        )

    # ── B-Roll items (BRollItemSchema) ──────────────────────────────
    brolls: list[dict] = []
    sorted_indices = sorted(broll_data.get("broll_paths", {}).keys())
    for i, idx in enumerate(sorted_indices):
        path = broll_data["broll_paths"][idx]
        url = asset_manager.get_asset_url(path)
        start_frame = i * broll_duration * fps
        duration_frames = broll_duration * fps
        scenes_list = broll_data.get("scenes", [])
        alt = scenes_list[i].get("description", "")[:80] if i < len(scenes_list) else ""
        brolls.append({
            "url": url,
            "startFrame": start_frame,
            "durationInFrames": duration_frames,
            "alt": alt,
        })

    # ── Caption words (CaptionWordSchema) ───────────────────────────
    captions: list[dict] = []
    for wt in broll_data.get("word_timestamps", []):
        captions.append({
            "word": wt.get("word", ""),
            "start": wt.get("start", 0),
            "end": wt.get("end", 0),
        })

    # ── Scenes (SceneBlockSchema) ───────────────────────────────────
    scenes: list[dict] = []
    raw_scenes = broll_data.get("scenes", [])
    for i, scene in enumerate(raw_scenes):
        start_time = scene.get("start_time", i * broll_duration)
        end_time = scene.get("end_time", start_time + broll_duration)
        start_frame = int(start_time * fps)
        duration_frames = int((end_time - start_time) * fps)
        if duration_frames < 1:
            duration_frames = broll_duration * fps
        scenes.append({
            "id": f"scene_{i:02d}",
            "type": "broll",
            "startFrame": start_frame,
            "durationInFrames": duration_frames,
            "text": scene.get("description", ""),
            "brollIndex": i if i < len(brolls) else 0,
        })

    # ── SFX items (SfxItemSchema) ───────────────────────────────────
    sfx: list[dict] = []

    # Always start with a Ding at frame 0
    if sfx_paths and "ding" in sfx_paths:
        sfx.append({
            "url": asset_manager.get_asset_url(sfx_paths["ding"]),
            "startFrame": 0,
            "volume": 0.25,
            "_type": "ding",
        })

    for scene in raw_scenes:
        sfx_type = scene.get("sfx")
        if sfx_type == "news_flash":
            continue  # Never use news_flash
        if sfx_type and sfx_paths and sfx_type in sfx_paths:
            sfx_url = asset_manager.get_asset_url(sfx_paths[sfx_type])
            start_frame = int(scene.get("start_time", 0) * fps)
            # Impact: very soft, max 1 per video (skip if already have one)
            if sfx_type == "impact":
                has_impact = any(s.get("_type") == "impact" for s in sfx)
                if has_impact:
                    continue  # Only 1 impact per video
                volume = 0.08
            else:
                volume = 0.20
            sfx.append({
                "url": sfx_url,
                "startFrame": start_frame,
                "volume": volume,
                "_type": sfx_type,  # internal tracking, stripped before render
            })

    # ── Music URL ────────────────────────────────────────────────────
    music_url = ""
    if music_path:
        music_url = asset_manager.get_asset_url(music_path)

    # Strip internal _type field from SFX items
    for item in sfx:
        item.pop("_type", None)

    # ── Calculate duration ───────────────────────────────────────────
    total_duration = broll_data.get(
        "total_duration", avatar_data.get("duration", 60)
    )
    duration_in_frames = int(total_duration * fps)

    # ── Banner template URL (pre-cropped, lightweight) ────────────────
    banner_template_url = ""
    banner_template_path = "templates/banner-cropped.mp4"
    if not minio_client.object_exists(banner_template_path):
        import os as _os
        template_local = _os.path.normpath(
            _os.path.join(_os.path.dirname(__file__), "..", "..", "..", "..", "remotion", "public", "banner-cropped.mp4")
        )
        if _os.path.isfile(template_local):
            minio_client.upload_from_file(banner_template_path, template_local, "video/mp4")
            logger.info("[Stage 3] Uploaded cropped banner template to MinIO")
    if minio_client.object_exists(banner_template_path):
        banner_template_url = asset_manager.get_asset_url(banner_template_path)

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
        "bannerTemplateUrl": banner_template_url,
        "topicText": topic[:120] if topic else (script.split('\n')[0][:120] if script else ""),
        "urgentKeywords": broll_data.get("urgent_keywords", []),
    }

    # Save props JSON to MinIO for debugging
    props_json = json.dumps(composition_props, indent=2, ensure_ascii=False)
    asset_manager.save_asset(
        job_id, "stage3_render", "composition_props.json",
        props_json.encode("utf-8"), "application/json",
    )

    # ── Write props to temp file for Remotion ────────────────────────
    tmp_dir = tempfile.mkdtemp(prefix=f"render_{job_id}_")
    props_file = os.path.join(tmp_dir, "props.json")
    output_file = os.path.join(tmp_dir, "output.mp4")

    with open(props_file, "w", encoding="utf-8") as f:
        f.write(props_json)

    # ── Resolve Remotion directory ───────────────────────────────────
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
        remotion_dir = os.path.normpath(candidates[0])
        logger.warning("[Stage 3] Remotion directory not found; using {d}", d=remotion_dir)

    # ── Call Remotion render ─────────────────────────────────────────
    logger.info(
        "[Stage 3] Rendering video ({frames} frames, {dur:.1f}s)...",
        frames=duration_in_frames, dur=total_duration,
    )

    render_cmd = [
        "npx", "tsx",
        os.path.join(remotion_dir, "src", "render.ts"),
        "--input", props_file,
        "--output", output_file,
    ]

    proc = subprocess.Popen(
        render_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        text=True, cwd=remotion_dir,
    )

    # Stream stderr for progress logging
    stderr_lines = []
    try:
        for line in proc.stderr:
            line = line.rstrip()
            stderr_lines.append(line)
            if "[render]" in line:
                logger.info("{line}", line=line)
        proc.wait(timeout=600)
    except subprocess.TimeoutExpired:
        proc.kill()
        raise RuntimeError("[Stage 3] Remotion render timed out (600s)")

    stdout_full = proc.stdout.read() if proc.stdout else ""
    stderr_full = "\n".join(stderr_lines)

    if proc.returncode != 0:
        logger.error("[Stage 3] Remotion STDERR: {err}", err=stderr_full[-2000:])
        logger.error("[Stage 3] Remotion exit code: {code}", code=proc.returncode)
        raise RuntimeError(f"Remotion render failed: {stderr_full[-1000:]}")

    if not os.path.exists(output_file):
        raise RuntimeError("[Stage 3] Render completed but output file not found")

    # ── Upload rendered video to MinIO ───────────────────────────────
    output_minio_path = asset_manager.save_asset_from_file(
        job_id, "output", "final.mp4", output_file, "video/mp4"
    )

    logger.success("[Stage 3] Video rendered and uploaded: {path}", path=output_minio_path)

    # ── Cleanup ──────────────────────────────────────────────────────
    shutil.rmtree(tmp_dir, ignore_errors=True)

    return output_minio_path
