import asyncio
import json
import os

from app.utils.logger import logger


class FFmpegProcessor:
    """Wrapper for FFmpeg operations (chromakey, audio extraction, thumbnails)."""

    @staticmethod
    async def chromakey(
        input_path: str,
        output_path: str,
        color: str = "00FF00",
        similarity: float = 0.3,
        blend: float = 0.1,
    ) -> str:
        """Remove green screen background and add alpha channel.

        Args:
            input_path: Path to input video with green screen.
            output_path: Path for output video with transparency.
            color: Hex color to remove (default green).
            similarity: Color similarity threshold (0-1).
            blend: Edge blending (0-1).

        Returns:
            Output path.
        """
        # Chromakey + alpha threshold: pixels with >30% opacity become fully opaque
        # This prevents the body from being semi-transparent while keeping background transparent
        vf_filter = (
            f"chromakey=0x{color}:{similarity}:{blend},"
            f"geq=r='r(X,Y)':g='g(X,Y)':b='b(X,Y)':a='if(gt(alpha(X,Y),77),255,0)'"
        )
        cmd = [
            "ffmpeg",
            "-y",
            "-i",
            input_path,
            "-vf",
            vf_filter,
            "-c:v",
            "png",
            "-pix_fmt",
            "rgba",
            output_path,
        ]

        logger.info(f"Running chromakey: {input_path} -> {output_path}")
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()

        if proc.returncode != 0:
            raise RuntimeError(
                f"FFmpeg chromakey failed: {stderr.decode()[-500:]}"
            )

        logger.success(f"Chromakey complete: {output_path}")
        return output_path

    @staticmethod
    async def extract_audio(
        video_path: str,
        output_path: str | None = None,
        format: str = "mp3",
    ) -> str:
        """Extract audio track from video file."""
        if output_path is None:
            base = os.path.splitext(video_path)[0]
            output_path = f"{base}.{format}"

        codec = "libmp3lame" if format == "mp3" else "aac"
        cmd = [
            "ffmpeg",
            "-y",
            "-i",
            video_path,
            "-vn",  # No video
            "-acodec",
            codec,
            "-q:a",
            "2",
            output_path,
        ]

        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()

        if proc.returncode != 0:
            raise RuntimeError(
                f"FFmpeg audio extraction failed: {stderr.decode()[-500:]}"
            )

        logger.info(f"Audio extracted: {output_path}")
        return output_path

    @staticmethod
    async def extract_thumbnail(
        video_path: str,
        output_path: str | None = None,
        time_offset: float = 0.0,
    ) -> str:
        """Extract a single frame from video as JPEG thumbnail."""
        if output_path is None:
            base = os.path.splitext(video_path)[0]
            output_path = f"{base}_thumb.jpg"

        cmd = [
            "ffmpeg",
            "-y",
            "-ss",
            str(time_offset),
            "-i",
            video_path,
            "-vframes",
            "1",
            "-q:v",
            "2",
            output_path,
        ]

        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()

        if proc.returncode != 0:
            raise RuntimeError(
                f"FFmpeg thumbnail extraction failed: {stderr.decode()[-500:]}"
            )

        return output_path

    @staticmethod
    async def get_duration(file_path: str) -> float:
        """Get media file duration in seconds using ffprobe."""
        cmd = [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "json",
            file_path,
        ]

        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()

        if proc.returncode != 0:
            raise RuntimeError(f"ffprobe failed: {stderr.decode()[-500:]}")

        data = json.loads(stdout.decode())
        return float(data["format"]["duration"])

    @staticmethod
    async def get_video_info(file_path: str) -> dict:
        """Get detailed video info (width, height, fps, duration, codec)."""
        cmd = [
            "ffprobe",
            "-v",
            "error",
            "-select_streams",
            "v:0",
            "-show_entries",
            "stream=width,height,r_frame_rate,codec_name,duration",
            "-show_entries",
            "format=duration,size",
            "-of",
            "json",
            file_path,
        ]

        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()

        if proc.returncode != 0:
            raise RuntimeError(f"ffprobe failed: {stderr.decode()[-500:]}")

        data = json.loads(stdout.decode())
        stream = data.get("streams", [{}])[0]
        fmt = data.get("format", {})

        # Parse frame rate (e.g., "30/1" -> 30.0)
        fps_str = stream.get("r_frame_rate", "30/1")
        if "/" in fps_str:
            num, den = fps_str.split("/")
            fps = float(num) / float(den) if float(den) != 0 else 30.0
        else:
            fps = float(fps_str)

        return {
            "width": int(stream.get("width", 0)),
            "height": int(stream.get("height", 0)),
            "fps": fps,
            "codec": stream.get("codec_name", ""),
            "duration": float(fmt.get("duration", stream.get("duration", 0))),
            "size": int(fmt.get("size", 0)),
        }

    @staticmethod
    async def convert_to_webm_alpha(
        input_path: str,
        output_path: str,
    ) -> str:
        """Convert video with alpha channel to WebM VP9 (for Remotion transparency)."""
        cmd = [
            "ffmpeg",
            "-y",
            "-i",
            input_path,
            "-c:v",
            "libvpx-vp9",
            "-pix_fmt",
            "yuva420p",
            "-auto-alt-ref",
            "0",
            "-b:v",
            "2M",
            output_path,
        ]

        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()

        if proc.returncode != 0:
            raise RuntimeError(
                f"FFmpeg WebM conversion failed: {stderr.decode()[-500:]}"
            )

        logger.info(f"Converted to WebM with alpha: {output_path}")
        return output_path


# Singleton
ffmpeg_processor = FFmpegProcessor()
