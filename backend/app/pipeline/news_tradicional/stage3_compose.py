import json
import os
import shutil
import subprocess
import tempfile

from app.processing.asset_manager import asset_manager
from app.services.minio_client import minio_client
from app.utils.logger import logger


def _log_to_db(video_id: str, stage: str, message: str, level: str = "INFO"):
    """Save a log entry to the database synchronously (for render progress)."""
    import asyncio
    from app.database import async_session_factory
    from app.models.log_entry import LogEntry

    async def _save():
        async with async_session_factory() as session:
            entry = LogEntry(
                video_id=video_id,
                stage=stage,
                level=level,
                message=message,
            )
            session.add(entry)
            await session.commit()

    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            asyncio.ensure_future(_save())
        else:
            asyncio.run(_save())
    except Exception:
        pass  # Non-critical


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

    # Helper to log to both terminal and database
    def log(msg, level="INFO"):
        print(f"[Render] {msg}", flush=True)
        _log_to_db(job_id, "stage3_render", f"[Render] {msg}", level)

    log("=== Iniciando Stage 3: Composicao e Renderizacao ===")
    log("Baixando assets do MinIO para pasta local...")

    # ── Download TTS audio ──────────────────────────────────────
    log("Baixando audio TTS...")
    tts_filename = _download_to_public(tts_audio_minio_path, assets_dir, "tts_audio.mp3")
    log("Audio TTS baixado!")

    # ── Download avatar ─────────────────────────────────────────
    avatar_filename = ""
    if avatar_data.get("avatar_minio_path"):
        log("Baixando avatar (WebM com alpha)...")
        ext = "webm" if "webm" in avatar_data["avatar_minio_path"] else "mp4"
        avatar_filename = _download_to_public(
            avatar_data["avatar_minio_path"], assets_dir, f"avatar.{ext}"
        )
        log(f"Avatar baixado: avatar.{ext}")
    else:
        log("AVISO: Sem avatar neste job", "WARNING")

    # ── Download B-Rolls ────────────────────────────────────────
    brolls: list[dict] = []
    sorted_indices = sorted(broll_data.get("broll_paths", {}).keys())
    total_brolls = len(sorted_indices)
    log(f"Baixando {total_brolls} B-Rolls...")
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
        log(f"B-Roll {i+1}/{total_brolls} baixado")
    log(f"Todos {total_brolls} B-Rolls baixados!")

    # ── Caption words ───────────────────────────────────────────
    log(f"Gerando legendas ({len(broll_data.get('word_timestamps', []))} palavras)...")
    captions: list[dict] = []
    for wt in broll_data.get("word_timestamps", []):
        captions.append({
            "word": wt.get("word", ""),
            "start": wt.get("start", 0),
            "end": wt.get("end", 0),
        })
    log(f"Legendas: {len(captions)} palavras sincronizadas")

    # ── Scenes ──────────────────────────────────────────────────
    log(f"Montando {len(broll_data.get('scenes', []))} cenas...")
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

    log(f"Cenas montadas: {len(scenes)} blocos")

    # ── SFX ─────────────────────────────────────────────────────
    log("Configurando efeitos sonoros (SFX)...")
    sfx: list[dict] = []

    # Always start with a Ding at frame 0
    if sfx_paths and "ding" in sfx_paths:
        log("Baixando SFX Ding (inicio do video)...")
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
    log(f"SFX configurados: {len(sfx)} efeitos sonoros")
    for item in sfx:
        item.pop("_type", None)

    # ── Download music ──────────────────────────────────────────
    music_url = ""
    if music_path:
        log("Baixando musica de fundo...")
        music_filename = _download_to_public(music_path, assets_dir, "music.mp3")
        music_url = f"assets/{music_filename}"
        log("Musica de fundo baixada!")
    else:
        log("Sem musica de fundo neste job")

    # ── Calculate duration ──────────────────────────────────────
    total_duration = broll_data.get(
        "total_duration", avatar_data.get("duration", 60)
    )
    duration_in_frames = int(total_duration * fps)
    log(f"Duracao total: {total_duration:.1f}s ({duration_in_frames} frames a {fps}fps)")

    # ── Build composition props ─────────────────────────────────
    log("Montando props da composicao Remotion...")
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
    log("Salvando props JSON...")
    tmp_dir = tempfile.mkdtemp(prefix=f"render_{job_id}_")
    props_file = os.path.join(tmp_dir, "props.json")
    output_file = os.path.join(tmp_dir, "output.mp4")

    with open(props_file, "w", encoding="utf-8") as f:
        f.write(props_json)
    log(f"Props salvo: {len(props_json)} bytes")

    # ── Render with retry logic ─────────────────────────────────
    log("=== Iniciando renderizacao Remotion ===")
    log(f"Resolucao: 1080x1920 @ {fps}fps")
    log(f"Duracao: {duration_in_frames} frames ({total_duration:.1f}s)")
    log(f"Assets: {total_brolls} B-Rolls, {len(captions)} palavras, {len(sfx)} SFX")

    render_cmd = [
        "npx", "tsx",
        os.path.join(remotion_dir, "src", "render.ts"),
        "--input", props_file,
        "--output", output_file,
    ]

    last_pct = -1  # Track last logged percentage

    max_retries = 3
    for attempt in range(1, max_retries + 1):
        log(f"Tentativa {attempt}/{max_retries}...")
        log("Bundling Remotion project...")

        proc = subprocess.Popen(
            render_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True, cwd=remotion_dir,
        )

        stderr_lines = []
        try:
            for line in proc.stderr:
                line = line.rstrip()
                stderr_lines.append(line)
                if "[render] Progress:" in line:
                    # Log every 5% to frontend
                    try:
                        pct = float(line.split("Progress:")[1].strip().replace("%", ""))
                        pct_int = int(pct)
                        if pct_int >= last_pct + 5:
                            last_pct = pct_int
                            log(f"Renderizando... {pct_int}%")
                    except Exception:
                        pass
                    print(f"[Render] {line}", flush=True)
                elif "[render]" in line:
                    log(line)
                    print(f"[Render] {line}", flush=True)
            proc.wait(timeout=900)
        except subprocess.TimeoutExpired:
            proc.kill()
            log(f"TIMEOUT: Render excedeu 15 minutos (tentativa {attempt})", "ERROR")
            if attempt < max_retries:
                import time
                time.sleep(5)
                continue
            raise RuntimeError("[Stage 3] Remotion render timed out after all retries")

        if proc.returncode == 0 and os.path.exists(output_file):
            file_size = os.path.getsize(output_file) / (1024 * 1024)
            log(f"=== RENDER CONCLUIDO COM SUCESSO! === ({file_size:.1f}MB)", "SUCCESS")
            break  # Success

        stderr_full = "\n".join(stderr_lines)
        log(f"ERRO na tentativa {attempt}: {stderr_full[-300:]}", "ERROR")

        if attempt < max_retries:
            log("Aguardando 5s antes de tentar novamente...")
            import time
            time.sleep(5)
        else:
            raise RuntimeError(f"Remotion render failed after {max_retries} attempts: {stderr_full[-1000:]}")

    if not os.path.exists(output_file):
        raise RuntimeError("[Render] Render concluido mas arquivo nao encontrado")

    # ── Upload rendered video to MinIO ──────────────────────────
    log("Fazendo upload do video final para MinIO...")
    import re, unicodedata
    topic_ascii = unicodedata.normalize('NFKD', topic[:60]).encode('ascii', 'ignore').decode()
    topic_slug = re.sub(r'[^a-zA-Z0-9\s-]', '', topic_ascii).strip().replace(' ', '_').lower()
    output_filename = f"news_{topic_slug}.mp4" if topic_slug else "final.mp4"
    output_minio_path = asset_manager.save_asset_from_file(
        job_id, "output", output_filename, output_file, "video/mp4"
    )
    log(f"Video salvo no MinIO: {output_minio_path}", "SUCCESS")
    log("=== PIPELINE FINALIZADO COM SUCESSO! ===", "SUCCESS")

    # ── Cleanup ─────────────────────────────────────────────────
    log("Limpando arquivos temporarios...")
    shutil.rmtree(tmp_dir, ignore_errors=True)
    # Clean assets from public/
    for f in os.listdir(assets_dir):
        try:
            os.remove(os.path.join(assets_dir, f))
        except Exception:
            pass

    return output_minio_path
