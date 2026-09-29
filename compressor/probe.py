"""
Video Probing & Metadata Extraction Module
Uses ffprobe to extract stream, codec, format, resolution, and color/HDR details.
"""

import json
import os
import shutil
import subprocess
from dataclasses import dataclass
from typing import List, Optional


@dataclass
class StreamInfo:
    index: int
    codec_type: str  # 'video', 'audio', 'subtitle'
    codec_name: str
    width: Optional[int] = None
    height: Optional[int] = None
    rotation: int = 0
    display_width: Optional[int] = None
    display_height: Optional[int] = None
    pix_fmt: Optional[str] = None
    fps: Optional[float] = None
    bitrate: Optional[int] = None
    channels: Optional[int] = None
    sample_rate: Optional[int] = None
    color_space: Optional[str] = None
    color_transfer: Optional[str] = None
    color_primaries: Optional[str] = None
    is_hdr: bool = False


@dataclass
class VideoInfo:
    path: str
    filename: str
    size_bytes: int
    duration_seconds: float
    bitrate: int
    format_name: str
    video_stream: Optional[StreamInfo]
    audio_streams: List[StreamInfo]
    subtitle_streams: List[StreamInfo]

    @property
    def resolution_str(self) -> str:
        if self.video_stream and self.video_stream.display_width and self.video_stream.display_height:
            rot_str = f" (Rotated {self.video_stream.rotation} deg)" if self.video_stream.rotation else ""
            return f"{self.video_stream.display_width}x{self.video_stream.display_height}{rot_str}"
        return "Unknown"

    @property
    def is_vertical_9_16(self) -> bool:
        if self.video_stream and self.video_stream.display_width and self.video_stream.display_height:
            return self.video_stream.display_height > self.video_stream.display_width
        return False

    @property
    def is_4k_or_higher(self) -> bool:
        if self.video_stream and self.video_stream.display_width and self.video_stream.display_height:
            return self.video_stream.display_width >= 2160 or self.video_stream.display_height >= 2160
        return False

    @property
    def is_hdr(self) -> bool:
        return self.video_stream.is_hdr if self.video_stream else False

    @property
    def video_codec(self) -> str:
        return self.video_stream.codec_name if self.video_stream else "None"

    @property
    def fps_str(self) -> str:
        if self.video_stream and self.video_stream.fps:
            return f"{self.video_stream.fps:.2f} fps"
        return "Unknown"


def format_bytes(size: int) -> str:
    if size <= 0:
        return "0 B"
    power = 1024
    n = 0
    units = ["B", "KB", "MB", "GB", "TB"]
    s = float(size)
    while s >= power and n < len(units) - 1:
        s /= power
        n += 1
    return f"{s:.2f} {units[n]}"


def probe_video(file_path: str) -> VideoInfo:
    """Probes video file using ffprobe and returns structured VideoInfo."""
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")

    ffprobe_bin = shutil.which("ffprobe")
    if not ffprobe_bin:
        raise RuntimeError("ffprobe is not installed or not found in system PATH.")

    cmd = [
        ffprobe_bin,
        "-v", "quiet",
        "-print_format", "json",
        "-show_format",
        "-show_streams",
        file_path,
    ]

    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding="utf-8")
    if result.returncode != 0:
        raise RuntimeError(f"ffprobe failed to inspect {file_path}: {result.stderr}")

    data = json.loads(result.stdout)
    fmt = data.get("format", {})
    streams = data.get("streams", [])

    duration = float(fmt.get("duration", 0.0))
    bitrate = int(fmt.get("bit_rate", 0))
    size_bytes = int(fmt.get("size", os.path.getsize(file_path)))
    format_name = fmt.get("format_name", "unknown")

    video_stream: Optional[StreamInfo] = None
    audio_streams: List[StreamInfo] = []
    subtitle_streams: List[StreamInfo] = []

    for s in streams:
        codec_type = s.get("codec_type")
        codec_name = s.get("codec_name", "unknown")
        idx = int(s.get("index", 0))

        if codec_type == "video" and not video_stream:
            # Parse fps
            fps = None
            r_fps = s.get("r_frame_rate", "")
            if "/" in r_fps:
                num, den = r_fps.split("/")
                if float(den) > 0:
                    fps = float(num) / float(den)
            elif r_fps:
                fps = float(r_fps)

            stream_bitrate = int(s.get("bit_rate", 0)) if s.get("bit_rate") else None
            pix_fmt = s.get("pix_fmt", "")
            color_space = s.get("color_space")
            color_transfer = s.get("color_transfer")
            color_primaries = s.get("color_primaries")

            is_hdr = False
            if color_transfer in ("smpte2084", "arib-std-b67", "linear") or "10" in pix_fmt:
                is_hdr = True

            # Parse rotation from side data (Display Matrix) or tags
            rotation = 0
            for sd in s.get("side_data_list", []):
                if "rotation" in sd:
                    try:
                        rotation = int(float(sd["rotation"]))
                        break
                    except (ValueError, TypeError):
                        pass
            if rotation == 0 and "rotate" in s.get("tags", {}):
                try:
                    rotation = int(float(s["tags"]["rotate"]))
                except (ValueError, TypeError):
                    pass

            raw_w = s.get("width")
            raw_h = s.get("height")
            if raw_w and raw_h and abs(rotation) in (90, 270):
                disp_w = raw_h
                disp_h = raw_w
            else:
                disp_w = raw_w
                disp_h = raw_h

            video_stream = StreamInfo(
                index=idx,
                codec_type="video",
                codec_name=codec_name,
                width=raw_w,
                height=raw_h,
                rotation=rotation,
                display_width=disp_w,
                display_height=disp_h,
                pix_fmt=pix_fmt,
                fps=fps,
                bitrate=stream_bitrate,
                color_space=color_space,
                color_transfer=color_transfer,
                color_primaries=color_primaries,
                is_hdr=is_hdr,
            )
        elif codec_type == "audio":
            audio_streams.append(
                StreamInfo(
                    index=idx,
                    codec_type="audio",
                    codec_name=codec_name,
                    channels=s.get("channels"),
                    sample_rate=int(s.get("sample_rate", 0)) if s.get("sample_rate") else None,
                    bitrate=int(s.get("bit_rate", 0)) if s.get("bit_rate") else None,
                )
            )
        elif codec_type == "subtitle":
            subtitle_streams.append(
                StreamInfo(
                    index=idx,
                    codec_type="subtitle",
                    codec_name=codec_name,
                )
            )

    return VideoInfo(
        path=os.path.abspath(file_path),
        filename=os.path.basename(file_path),
        size_bytes=size_bytes,
        duration_seconds=duration,
        bitrate=bitrate,
        format_name=format_name,
        video_stream=video_stream,
        audio_streams=audio_streams,
        subtitle_streams=subtitle_streams,
    )
