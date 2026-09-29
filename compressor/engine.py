"""
Core Video Compression Execution Engine
Executes FFmpeg with real-time progress monitoring, error trapping, and performance metrics.
"""

import os
import re
import shutil
import subprocess
import time
from dataclasses import dataclass
from typing import Callable, Optional

from .hardware import get_available_encoders
from .metrics import QualityScore, measure_quality
from .probe import VideoInfo, format_bytes, probe_video
from .profiles import build_ffmpeg_args


@dataclass
class ProgressUpdate:
    percent: float
    fps: float
    current_time_seconds: float
    total_time_seconds: float
    speed: str
    bitrate: str
    eta_seconds: float


@dataclass
class CompressionResult:
    input_path: str
    output_path: str
    original_size_bytes: int
    compressed_size_bytes: int
    space_saved_bytes: int
    space_saved_percent: float
    duration_seconds: float
    elapsed_time_seconds: float
    average_speed: str
    quality_score: Optional[QualityScore] = None

    @property
    def original_size_str(self) -> str:
        return format_bytes(self.original_size_bytes)

    @property
    def compressed_size_str(self) -> str:
        return format_bytes(self.compressed_size_bytes)

    @property
    def space_saved_str(self) -> str:
        return format_bytes(self.space_saved_bytes)


class VideoCompressor:
    """
    High-performance video compressor designed to maximize size reduction without visible quality loss.
    """

    def __init__(
        self,
        codec: str = "h264",  # 'h264', 'hevc', 'av1', 'nvenc_h264', 'nvenc_hevc'
        mode: str = "tiktok_best",  # 'tiktok_best', 'tiktok_60fps', 'visually_lossless', 'high_compression', 'lossless', 'target_size'
        audio_mode: str = "aac",  # 'aac', 'copy', 'opus'
        custom_crf: Optional[int] = None,
        preset: Optional[str] = None,
        sharpen: bool = True,
        scale_to_1080p: bool = True,
    ):
        self.codec = codec.lower()
        self.mode = mode.lower()
        self.audio_mode = audio_mode.lower()
        self.custom_crf = custom_crf
        self.preset = preset
        self.sharpen = sharpen
        self.scale_to_1080p = scale_to_1080p

        # Verify ffmpeg availability
        self.ffmpeg_bin = shutil.which("ffmpeg")
        if not self.ffmpeg_bin:
            raise RuntimeError("ffmpeg executable not found in system PATH.")

    def compress(
        self,
        input_path: str,
        output_path: Optional[str] = None,
        target_size_mb: Optional[float] = None,
        progress_callback: Optional[Callable[[ProgressUpdate], None]] = None,
        verify_quality: bool = False,
    ) -> CompressionResult:
        """
        Compresses input_path and saves to output_path.
        """
        if not os.path.exists(input_path):
            raise FileNotFoundError(f"Input file does not exist: {input_path}")

        info = probe_video(input_path)

        if not output_path:
            base, ext = os.path.splitext(input_path)
            output_path = f"{base}_tiktok_optimized{ext or '.mp4'}"

        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

        args = build_ffmpeg_args(
            input_file=input_path,
            output_file=output_path,
            info=info,
            codec=self.codec,
            mode=self.mode,
            target_size_mb=target_size_mb,
            audio_mode=self.audio_mode,
            custom_crf=self.custom_crf,
            preset=self.preset,
            sharpen=self.sharpen,
            scale_to_1080p=self.scale_to_1080p,
        )

        total_duration = info.duration_seconds
        start_time = time.time()
        last_speed = "1.0x"

        # Launch FFmpeg process with stderr pipe
        process = subprocess.Popen(
            args,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            universal_newlines=True,
            encoding="utf-8",
            errors="replace",
        )

        time_pattern = re.compile(r"time=(\d+):(\d+):(\d+\.?\d*)")
        fps_pattern = re.compile(r"fps=\s*([\d\.]+)")
        speed_pattern = re.compile(r"speed=\s*([\d\.]+)x")
        bitrate_pattern = re.compile(r"bitrate=\s*([\d\.]+k?bits/s)")

        error_lines = []

        try:
            for line in process.stderr:
                error_lines.append(line)
                if len(error_lines) > 50:
                    error_lines.pop(0)

                t_match = time_pattern.search(line)
                if t_match and total_duration > 0:
                    hours, mins, secs = t_match.groups()
                    current_secs = (int(hours) * 3600) + (int(mins) * 60) + float(secs)
                    percent = min(100.0, max(0.0, (current_secs / total_duration) * 100.0))

                    fps_val = 0.0
                    fps_match = fps_pattern.search(line)
                    if fps_match:
                        try:
                            fps_val = float(fps_match.group(1))
                        except ValueError:
                            pass

                    speed_val = "1.0x"
                    speed_match = speed_pattern.search(line)
                    if speed_match:
                        speed_val = f"{speed_match.group(1)}x"
                        last_speed = speed_val

                    bitrate_val = "N/A"
                    bitrate_match = bitrate_pattern.search(line)
                    if bitrate_match:
                        bitrate_val = bitrate_match.group(1)

                    elapsed = time.time() - start_time
                    eta = 0.0
                    if percent > 0:
                        eta = (elapsed / (percent / 100.0)) - elapsed

                    if progress_callback:
                        update = ProgressUpdate(
                            percent=percent,
                            fps=fps_val,
                            current_time_seconds=current_secs,
                            total_time_seconds=total_duration,
                            speed=speed_val,
                            bitrate=bitrate_val,
                            eta_seconds=max(0.0, eta),
                        )
                        progress_callback(update)

            process.wait()

        except Exception as e:
            process.kill()
            if os.path.exists(output_path):
                try:
                    os.remove(output_path)
                except OSError:
                    pass
            raise RuntimeError(f"Compression interrupted: {e}")

        if process.returncode != 0:
            if os.path.exists(output_path):
                try:
                    os.remove(output_path)
                except OSError:
                    pass
            err_text = "".join(error_lines)
            raise RuntimeError(f"FFmpeg encoding failed (Exit code {process.returncode}):\n{err_text}")

        elapsed_total = time.time() - start_time
        orig_size = os.path.getsize(input_path)
        comp_size = os.path.getsize(output_path)
        saved_bytes = max(0, orig_size - comp_size)
        saved_pct = (saved_bytes / orig_size * 100.0) if orig_size else 0.0

        quality: Optional[QualityScore] = None
        if verify_quality:
            quality = measure_quality(input_path, output_path)

        return CompressionResult(
            input_path=input_path,
            output_path=output_path,
            original_size_bytes=orig_size,
            compressed_size_bytes=comp_size,
            space_saved_bytes=saved_bytes,
            space_saved_percent=saved_pct,
            duration_seconds=total_duration,
            elapsed_time_seconds=elapsed_total,
            average_speed=last_speed,
            quality_score=quality,
        )


def compress_video(
    input_file: str,
    output_file: Optional[str] = None,
    codec: str = "h264",
    mode: str = "tiktok_best",
    target_size_mb: Optional[float] = None,
    verify_quality: bool = False,
    sharpen: bool = True,
    scale_to_1080p: bool = True,
) -> CompressionResult:
    """Convenience helper for quick one-line TikTok compression."""
    compressor = VideoCompressor(
        codec=codec,
        mode=mode,
        sharpen=sharpen,
        scale_to_1080p=scale_to_1080p,
    )
    return compressor.compress(
        input_path=input_file,
        output_path=output_file,
        target_size_mb=target_size_mb,
        verify_quality=verify_quality,
    )
