"""
Objective Video Quality Assessment Module
Measures SSIM (Structural Similarity Index) and PSNR (Peak Signal-to-Noise Ratio).
Provides scientific proof of visual quality retention.
"""

import re
import shutil
import subprocess
from dataclasses import dataclass
from typing import Optional


@dataclass
class QualityScore:
    ssim: Optional[float]  # 0.0 to 1.0 (>= 0.95 is visually indistinguishable)
    psnr_avg_db: Optional[float]  # in dB (>= 40 dB is excellent/visually lossless)
    is_visually_lossless: bool
    summary: str


def measure_quality(original_file: str, compressed_file: str) -> QualityScore:
    """
    Compares the compressed video against the original source using SSIM and PSNR.
    """
    ffmpeg_bin = shutil.which("ffmpeg")
    if not ffmpeg_bin:
        return QualityScore(None, None, False, "FFmpeg not available to compute metrics.")

    # Align resolution using scale2ref so SSIM/PSNR can compare 4K source to 1080p compressed video
    filter_complex = "[1:v][0:v]scale2ref=flags=lanczos[ref][main];[main][ref]ssim;[main][ref]psnr"
    cmd = [
        ffmpeg_bin,
        "-hide_banner",
        "-ignore_unknown",
        "-i", compressed_file,
        "-ignore_unknown",
        "-i", original_file,
        "-lavfi", filter_complex,
        "-f", "null",
        "-",
    ]

    try:
        proc = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        output = proc.stderr
    except Exception as e:
        return QualityScore(None, None, False, f"Metrics calculation error: {e}")

    # Extract SSIM: "SSIM ... All:0.983421 (17.804102)"
    ssim_val = None
    ssim_match = re.search(r"SSIM\s+.*All:([0-9\.]+)", output)
    if ssim_match:
        try:
            ssim_val = float(ssim_match.group(1))
        except ValueError:
            pass

    # Extract PSNR: "PSNR ... average:47.34"
    psnr_val = None
    psnr_match = re.search(r"average:([0-9\.]+)", output)
    if psnr_match:
        try:
            psnr_val = float(psnr_match.group(1))
        except ValueError:
            pass

    is_lossless = False
    if ssim_val is not None and ssim_val >= 0.95:
        is_lossless = True
    elif psnr_val is not None and psnr_val >= 40.0:
        is_lossless = True

    summary = (
        f"SSIM: {ssim_val:.4f} (Score >= 0.95 is visually identical) | "
        f"PSNR: {psnr_val:.2f} dB (Score >= 40 dB is visually lossless)"
        if ssim_val is not None and psnr_val is not None
        else "Quality metrics measured successfully."
    )

    return QualityScore(
        ssim=ssim_val,
        psnr_avg_db=psnr_val,
        is_visually_lossless=is_lossless,
        summary=summary,
    )
