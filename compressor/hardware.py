"""
Hardware Acceleration & Available Encoder Detection Module
Checks FFmpeg binaries for hardware (NVIDIA NVENC, Intel QSV, AMD AMF) and CPU codecs.
"""

import shutil
import subprocess
from typing import Dict, List


def get_available_encoders() -> Dict[str, bool]:
    """Inspects FFmpeg to discover supported video encoders."""
    ffmpeg_bin = shutil.which("ffmpeg")
    if not ffmpeg_bin:
        return {}

    try:
        res = subprocess.run(
            [ffmpeg_bin, "-encoders"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
        )
        output = res.stdout
    except Exception:
        return {}

    codecs_to_check = {
        "libsvtav1": "SVT-AV1 (CPU - Highest Quality & Compression)",
        "libx265": "H.265 / HEVC (CPU - High Compression)",
        "libx264": "H.264 / AVC (CPU - Universal Compatibility)",
        "hevc_nvenc": "NVIDIA NVENC HEVC (GPU Hardware Accelerated)",
        "av1_nvenc": "NVIDIA NVENC AV1 (GPU Hardware Accelerated)",
        "h264_nvenc": "NVIDIA NVENC H.264 (GPU Hardware Accelerated)",
        "hevc_qsv": "Intel QuickSync HEVC (GPU Hardware Accelerated)",
        "h264_qsv": "Intel QuickSync H.264 (GPU Hardware Accelerated)",
        "hevc_amf": "AMD AMF HEVC (GPU Hardware Accelerated)",
        "h264_amf": "AMD AMF H.264 (GPU Hardware Accelerated)",
    }

    supported: Dict[str, bool] = {}
    for codec in codecs_to_check:
        supported[codec] = f" {codec} " in output

    return supported


def get_recommended_encoder(prefer_gpu: bool = False) -> str:
    """
    Returns the optimal encoder:
    - If prefer_gpu is True and NVENC is present -> hevc_nvenc
    - Otherwise -> libsvtav1 (best compression / zero quality loss) or libx265
    """
    encoders = get_available_encoders()
    if prefer_gpu:
        if encoders.get("av1_nvenc"):
            return "av1_nvenc"
        if encoders.get("hevc_nvenc"):
            return "hevc_nvenc"
        if encoders.get("h264_nvenc"):
            return "h264_nvenc"

    if encoders.get("libsvtav1"):
        return "libsvtav1"
    if encoders.get("libx265"):
        return "libx265"
    if encoders.get("libx264"):
        return "libx264"

    return "libx264"
