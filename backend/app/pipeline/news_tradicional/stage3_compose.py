import json
import os
import shutil
import subprocess
import tempfile

from app.processing.asset_manager import asset_manager
from app.services.minio_client import minio_client
from app.utils.logger import logger


def _download_to_public(minio_path: str, public_dir: str, filename: str) -> str:
    """Download a MinIO file to the Remotion public/ folder for staticFile() access."""
    local_path = os.path.join(public_dir, filename)
    data = minio_client.download_file(minio_path)
    with open(local_path, "wb") as f:
        f.write(data)
    logger.debug("[Stage 3] Downloaded {f} ({s:.1f}MB)", f=filename, s=len(data) / 1048576)
    return filename  # Return just the filename for staticFile()


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
    """Stage 3: Build Remotion composition props and render final video.

    Downloads all assets to remotion/public/ for staticFile() access (no HTTP URLs).
    Uses the same approach as the working yt-automation project.
    """
    logger.info("[Stage 3] Starting composition for job {jid}", jid=job_id)

    fps = 30
    broll_duration = 6

    # ── Resolve Remotion directory ───────────────────────────────
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

    # ── Prepare public/ folder for staticFile() assets ──────────
    public_dir = os.path.join(remotion_dir, "public")
    assets_dir = os.path.join(public_dir, "assets")
    os.makedirs(assets_dir, exist_ok=True)

    # Clean previous job assets
    for f in os.listdir(assets_dir):
        try:
            os.remove(os.path.join(assets_dir, f))
        except Exception:
            pass

    logger.info("[Stage 3] Downloading assets to public/ for staticFile()...")

    # ── Download TTS audio ──────────────────────────────────────
    tts_filename = _download_to_public(tts_audio_minio_path, assets_dir, "tts_audio.mp3")

    # ── Download avatar ─────────────────────────────────────────
    avatar_filename = ""
    if avatar_data.get("avatar_minio_path"):
        ext = "webm" if "webm" in avatar_data["avatar_minio_path"] else "mp4"
        avatar_filename = _download_to_public(
            avatar_data["avatar_minio_path"], assets_dir, f"avatar.{ext}"
        )

    # ── Download B-Rolls ────────────────────────────────────────
    brolls: list[dict] = []
    sorted_indices = sorted(broll_data.get("broll_paths", {}).keys())
    for i, idx in enumerate(sorted_indices):
        minio_path = broll_data["broll_paths"][idx]
        broll_filename = _download_to_public(minio_path, assets_dir, f"broll_{i:02d}.mp4")
        start_frame = i * broll_duration * fps
        duration_frames = broll_duration * fps
        scenes_list = broll_data.get("scenes", [])
        alt = scenes_list[i].get("description", "")[:80] if i < len(scenes_list) else ""
        brolls.append({
            "url": f"assets/{broll_filename}",
            "startFrame": start_frame,
            "durationInFrames": duration_frames,
            "alt": alt,
        })
    logger.info("[Stage 3] Downloaded {n} B-Rolls to public/", n=len(brolls))

    # ── Caption words ───────────────────────────────────────────
    captions: list[dict] = []
    for wt in broll_data.get("word_timestamps", []):
        captions.append({
            "word": wt.get("word", ""),
            "start": wt.get("start", 0),
            "end": wt.get("end", 0),
        })

    # ── Scenes ──────────────────────────────────────────────────
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

    # ── SFX ─────────────────────────────────────────────────────
    sfx: list[dict] = []

    # Always start with a Ding at frame 0
    if sfx_paths and "ding" in sfx_paths:
        ding_filename = _download_to_public(sfx_paths["ding"], assets_dir, "sfx_ding.mp3")
        sfx.append({
            "url": f"assets/{ding_filename}",
            "startFrame": 0,
            "volume": 0.25,
            "_type": "ding",
        })

    for scene in raw_scenes:
        sfx_type = scene.get("sfx")
        if sfx_type == "news_flash":
            continue
        if sfx_type and sfx_paths and sfx_type in sfx_paths:
            sfx_filename = f"sfx_{sfx_type}.mp3"
            sfx_path = os.path.join(assets_dir, sfx_filename)
            if not os.path.exists(sfx_path):
                _download_to_public(sfx_paths[sfx_type], assets_dir, sfx_filename)
            start_frame = int(scene.get("start_time", 0) * fps)
            if sfx_type == "impact":
                has_impact = any(s.get("_type") == "impact" for s in sfx)
                if has_impact:
                    continue
                volume = 0.08
            else:
                volume = 0.20
            sfx.append({
                "url": f"assets/{sfx_filename}",
                "startFrame": start_frame,
                "volume": volume,
                "_type": sfx_type,
            })

    # Strip internal _type field
    for item in sfx:
        item.pop("_type", None)

    # ── Download music ──────────────────────────────────────────
    music_url = ""
    if music_path:
        music_filename = _download_to_public(music_path, assets_dir, "music.mp3")
        music_url = f"assets/{music_filename}"

    # ── Calculate duration ──────────────────────────────────────
    total_duration = broll_data.get(
        "total_duration", avatar_data.get("duration", 60)
    )
    duration_in_frames = int(total_duration * fps)

    # ── Build composition props ─────────────────────────────────
    composition_props = {
        "jobId": job_id,
        "model": "news_tradicional",
        "fps": fps,
        "width": 1080,
        "height": 1920,
        "durationInFrames": duration_in_frames,
        "ttsAudioUrl": f"assets/{tts_filename}",
        "avatarVideoUrl": f"assets/{avatar_filename}" if avatar_filename else "",
        "brolls": brolls,
        "captions": captions,
        "scenes": scenes,
        "sfx": sfx,
        "musicUrl": music_url,
        "bannerText": "BREAKING NEWS",
        "topicText": topic[:120] if topic else (script.split('\n')[0][:120] if script else ""),
        "urgentKeywords": broll_data.get("urgent_keywords", []),
    }

    # Save props JSON to MinIO for debugging
    props_json = json.dumps(composition_props, indent=2, ensure_ascii=False)
    asset_manager.save_asset(
        job_id, "stage3_render", "composition_props.json",
        props_json.encode("utf-8"), "application/json",
    )

    # ── Write props to temp file ────────────────────────────────
    tmp_dir = tempfile.mkdtemp(prefix=f"render_{job_id}_")
    props_file = os.path.join(tmp_dir, "props.json")
    output_file = os.path.join(tmp_dir, "output.mp4")

    with open(props_file, "w", encoding="utf-8") as f:
        f.write(props_json)

    # ── Render with retry logic ─────────────────────────────────
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

    max_retries = 3
    for attempt in range(1, max_retries + 1):
        logger.info("[Stage 3] Render attempt {a}/{m}", a=attempt, m=max_retries)

        proc = subprocess.Popen(
            render_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True, cwd=remotion_dir,
        )

        stderr_lines = []
        try:
            for line in proc.stderr:
                line = line.rstrip()
                stderr_lines.append(line)
                if "[render]" in line:
                    logger.info("{line}", line=line)
            proc.wait(timeout=900)
        except subprocess.TimeoutExpired:
            proc.kill()
            logger.error("[Stage 3] Render timed out (attempt {a})", a=attempt)
            if attempt < max_retries:
                import time
                time.sleep(5)
                continue
            raise RuntimeError("[Stage 3] Remotion render timed out after all retries")

        if proc.returncode == 0 and os.path.exists(output_file):
            break  # Success

        stderr_full = "\n".join(stderr_lines)
        logger.error("[Stage 3] Render failed (attempt {a}): {err}", a=attempt, err=stderr_full[-1000:])

        if attempt < max_retries:
            import time
            time.sleep(5)
        else:
            raise RuntimeError(f"Remotion render failed after {max_retries} attempts: {stderr_full[-1000:]}")

    if not os.path.exists(output_file):
        raise RuntimeError("[Stage 3] Render completed but output file not found")

    # ── Upload rendered video to MinIO ──────────────────────────
    output_minio_path = asset_manager.save_asset_from_file(
        job_id, "output", "final.mp4", output_file, "video/mp4"
    )

    logger.success("[Stage 3] Video rendered and uploaded: {path}", path=output_minio_path)

    # ── Cleanup ─────────────────────────────────────────────────
    shutil.rmtree(tmp_dir, ignore_errors=True)
    # Clean assets from public/
    for f in os.listdir(assets_dir):
        try:
            os.remove(os.path.join(assets_dir, f))
        except Exception:
            pass

    return output_minio_path
