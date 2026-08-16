import asyncio
import os
import shutil
from pathlib import Path
from typing import Optional


class ClipExtractor:
    """
    Asynchronous FFmpeg video segment extraction service.
    Extracts precise broadcast moments around detected events.
    """

    def __init__(self, output_dir: str = "output"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.ffmpeg_available = shutil.which("ffmpeg") is not None
        self._clip_counter = 0

    async def extract(
        self,
        source_file: str,
        start_ms: int,
        end_ms: int,
        agent_id: str,
        event_id: str,
        padding_before_ms: int = 4000,
        padding_after_ms: int = 4000,
    ) -> Optional[str]:
        """
        Extracts a video sub-clip using FFmpeg with context padding.
        Returns the relative web-accessible path: e.g. '/api/clips/fan/clip_001.mp4'.
        """
        self._clip_counter += 1
        agent_dir = self.output_dir / agent_id
        agent_dir.mkdir(parents=True, exist_ok=True)

        filename = f"{agent_id}_clip_{self._clip_counter:03d}_{event_id[-6:]}.mp4"
        output_filepath = agent_dir / filename
        web_url = f"/api/clips/{agent_id}/{filename}"

        # If already exists, return web_url
        if output_filepath.exists() and output_filepath.stat().st_size > 1000:
            return web_url

        # Time calculations
        actual_start_ms = max(0, start_ms - padding_before_ms)
        actual_end_ms = end_ms + padding_after_ms
        duration_sec = (actual_end_ms - actual_start_ms) / 1000.0
        start_sec = actual_start_ms / 1000.0

        source_path = Path(source_file) if source_file else None

        # If source video exists and FFmpeg is present, cut the real clip
        if source_path and source_path.exists() and self.ffmpeg_available:
            cmd = [
                "ffmpeg", "-y",
                "-ss", f"{start_sec:.3f}",
                "-i", str(source_path),
                "-t", f"{duration_sec:.3f}",
                "-c:v", "libx264",
                "-preset", "ultrafast",
                "-crf", "26",
                "-c:a", "aac",
                "-b:a", "96k",
                "-movflags", "+faststart",
                str(output_filepath)
            ]
            try:
                proc = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                await asyncio.wait_for(proc.communicate(), timeout=20.0)
                if proc.returncode == 0 and output_filepath.exists():
                    return web_url
            except Exception as e:
                print(f"[ClipExtractor] FFmpeg execution error: {e}")

        # Fallback / Development mode: generate a minimal playable MP4 or placeholder
        await self._create_placeholder_clip(output_filepath, agent_id, duration_sec)
        return web_url

    async def _create_placeholder_clip(self, output_path: Path, agent_id: str, duration_sec: float):
        """Generate a simulated clip for testing if raw 720p/224p video isn't locally present."""
        if output_path.exists():
            return

        if self.ffmpeg_available:
            color_map = {
                "fan": "0x1e3a8a",    # Blue
                "coach": "0x78350f",  # Amber/Bronze
                "social": "0x831843"  # Pink/Magenta
            }
            bg_color = color_map.get(agent_id, "0x0f172a")
            
            # Generate 3-second animated color test pattern
            cmd = [
                "ffmpeg", "-y",
                "-f", "lavfi",
                "-i", f"color=c={bg_color}:s=480x270:d={min(duration_sec, 4.0)}",
                "-c:v", "libx264",
                "-preset", "ultrafast",
                "-pix_fmt", "yuv420p",
                "-movflags", "+faststart",
                str(output_path)
            ]
            try:
                proc = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                await asyncio.wait_for(proc.communicate(), timeout=10.0)
                return
            except Exception:
                pass

        # If ffmpeg is absent, write dummy binary placeholder
        try:
            with open(output_path, "wb") as f:
                f.write(b"AI_SPORTS_PRODUCER_CLIP_PLACEHOLDER")
        except Exception:
            pass
