"""
TikTok Video Compression Profiles and Parameter Factory
Specifically calibrated to bypass TikTok's server-side quality degradation,
prevent color-washing (HDR->BT.709 tonemapping), and maintain maximum sharpness.
"""

import os
from typing import List, Optional
from .probe import VideoInfo


def _get_codec_args(
    codec: str,
    mode: str,
    custom_crf: Optional[int],
    preset: Optional[str],
    fps_val: int,
) -> List[str]:
    """Returns codec-specific FFmpeg encoding arguments."""
    is_tiktok_mode = mode in ("tiktok_best", "tiktok_60fps")
    is_visually_lossless = mode == "visually_lossless"
    max_rate = "14M" if fps_val == 60 else "9M"
    buf_size = "28M" if fps_val == 60 else "18M"

    c = codec.lower()

    if c in ("nvenc_h264", "h264_nvenc"):
        cq = custom_crf if custom_crf is not None else (18 if (is_visually_lossless or is_tiktok_mode) else 23)
        args = [
            "-c:v", "h264_nvenc",
            "-cq", str(cq),
            "-preset", preset or "p6",
            "-tune", "hq",
            "-profile:v", "high",
            "-pix_fmt", "yuv420p",
        ]
        if is_tiktok_mode:
            args.extend(["-b:v", "0", "-maxrate", max_rate, "-bufsize", buf_size])
        return args

    elif c in ("nvenc_hevc", "hevc_nvenc"):
        cq = custom_crf if custom_crf is not None else (19 if (is_visually_lossless or is_tiktok_mode) else 24)
        args = [
            "-c:v", "hevc_nvenc",
            "-cq", str(cq),
            "-preset", preset or "p6",
            "-tune", "hq",
            "-pix_fmt", "yuv420p",
        ]
        if is_tiktok_mode:
            args.extend(["-b:v", "0", "-maxrate", max_rate, "-bufsize", buf_size])
        return args

    elif c in ("hevc", "libx265"):
        crf = custom_crf if custom_crf is not None else (20 if (is_visually_lossless or is_tiktok_mode) else 24)
        args = [
            "-c:v", "libx265",
            "-crf", str(crf),
            "-preset", preset or "medium",
            "-pix_fmt", "yuv420p",
        ]
        if is_tiktok_mode:
            args.extend(["-maxrate", max_rate, "-bufsize", buf_size])
        return args

    elif c in ("av1", "libsvtav1"):
        crf = custom_crf if custom_crf is not None else (24 if (is_visually_lossless or is_tiktok_mode) else 28)
        args = [
            "-c:v", "libsvtav1",
            "-crf", str(crf),
            "-preset", preset or "6",
            "-pix_fmt", "yuv420p",
            "-svtav1-params", "tune=0",
        ]
        if is_tiktok_mode:
            args.extend(["-maxrate", max_rate, "-bufsize", buf_size])
        return args

    else:
        # Default TikTok Standard: H.264 High Profile (Most compatible with TikTok server ingest)
        crf = custom_crf if custom_crf is not None else (18 if (is_visually_lossless or is_tiktok_mode) else 23)
        args = [
            "-c:v", "libx264",
            "-crf", str(crf),
            "-preset", preset or ("slow" if (is_visually_lossless or is_tiktok_mode) else "medium"),
            "-profile:v", "high",
            "-level", "4.2",
            "-pix_fmt", "yuv420p",
        ]
        if is_tiktok_mode:
            args.extend(["-maxrate", max_rate, "-bufsize", buf_size])
        return args


def build_ffmpeg_args(
    input_file: str,
    output_file: str,
    info: VideoInfo,
    codec: str = "h264",  # 'h264', 'hevc', 'av1', 'nvenc_h264', 'nvenc_hevc'
    mode: str = "tiktok_best",  # 'tiktok_best', 'tiktok_60fps', 'visually_lossless', 'high_compression', 'lossless', 'target_size'
    target_size_mb: Optional[float] = None,
    audio_mode: str = "aac",  # 'aac', 'copy', 'opus'
    custom_crf: Optional[int] = None,
    preset: Optional[str] = None,
    sharpen: bool = True,
    scale_to_1080p: bool = True,
) -> List[str]:
    """
    Constructs optimized FFmpeg command arguments tailored for TikTok uploads.
    """
    # -ignore_unknown prevents failing on unmapped proprietary data streams (e.g. iPhone mebx metadata)
    args = ["ffmpeg", "-y", "-hide_banner", "-ignore_unknown", "-i", input_file]

    # Map primary video and primary audio stream only.
    # Note: Using 0:a:0? avoids mapping proprietary secondary audio streams
    # (such as apple_apac spatial audio on iPhone 16 Pro) which lack FFmpeg decoders.
    args.extend(["-map", "0:v:0", "-map", "0:a:0?"])

    video_filters = []

    # 1. HDR to SDR Tonemapping (Fixes washed-out / gray iPhone HDR uploads on TikTok)
    if info.is_hdr:
        video_filters.append("zscale=t=linear:npl=100,format=gbrpf32le,zscale=p=bt709,tonemap=tonemap=hable:desat=0,zscale=t=bt709:m=bt709:r=tv,format=yuv420p")

    # 2. Dynamic Lanczos Scaling to TikTok 1080p standard
    # Uploading 4K directly to TikTok causes TikTok's poor server-side downscaler to blur the video.
    # Pre-scaling with Lanczos algorithm maintains razor-sharp edges.
    # The filter expression automatically handles vertical (portrait) vs landscape:
    # Portrait (ih > iw): scales to 1080:1920 (width 1080, height -2 preserves exact AR)
    # Landscape (iw >= ih): scales to 1920:1080 (height 1080, width -2 preserves exact AR)
    if scale_to_1080p and info.is_4k_or_higher:
        video_filters.append("scale='if(gt(ih,iw),1080,-2)':'if(gt(ih,iw),-2,1080)':flags=lanczos")
    else:
        # Ensure dimensions are divisible by 2 for H.264 / H.265 / AV1 encoders
        video_filters.append("scale=trunc(iw/2)*2:trunc(ih/2)*2")

    # 3. Micro-detail Sharpening
    # Adding subtle edge contrast counteracts TikTok's lossy recompression algorithms
    if sharpen and mode in ("tiktok_best", "tiktok_60fps", "visually_lossless"):
        video_filters.append("unsharp=5:5:0.5:5:5:0.0")

    # Apply video filters if any exist
    if video_filters:
        args.extend(["-vf", ",".join(video_filters)])

    # 4. TikTok Framerate Handling (Constant Frame Rate prevents audio de-sync on TikTok)
    fps_val = 30
    if mode == "tiktok_60fps":
        fps_val = 60
        args.extend(["-r", "60"])
    elif mode == "tiktok_best":
        fps_val = 60 if (info.video_stream and info.video_stream.fps and info.video_stream.fps >= 50) else 30
        args.extend(["-r", str(fps_val)])
    elif info.video_stream and info.video_stream.fps and info.video_stream.fps >= 50:
        fps_val = 60

    # 5. Codec & Rate Control
    if mode == "target_size" and target_size_mb and info.duration_seconds > 0:
        total_target_bits = target_size_mb * 8 * 1024 * 1024
        audio_bitrate_kbps = 192
        total_seconds = info.duration_seconds
        available_video_bits = total_target_bits - (audio_bitrate_kbps * 1000 * total_seconds)
        if available_video_bits < 100000:
            available_video_bits = total_target_bits * 0.85
        video_bitrate_kbps = max(50, int((available_video_bits / total_seconds) / 1000))

        c = codec.lower()
        if c in ("nvenc_h264", "h264_nvenc"):
            args.extend(["-c:v", "h264_nvenc", "-b:v", f"{video_bitrate_kbps}k", "-preset", preset or "p5", "-pix_fmt", "yuv420p"])
        elif c in ("hevc", "libx265"):
            args.extend(["-c:v", "libx265", "-b:v", f"{video_bitrate_kbps}k", "-preset", preset or "medium", "-pix_fmt", "yuv420p"])
        elif c in ("av1", "libsvtav1"):
            args.extend(["-c:v", "libsvtav1", "-b:v", f"{video_bitrate_kbps}k", "-preset", preset or "6", "-pix_fmt", "yuv420p", "-svtav1-params", "tune=0"])
        else:
            args.extend(["-c:v", "libx264", "-b:v", f"{video_bitrate_kbps}k", "-preset", preset or "medium", "-profile:v", "high", "-pix_fmt", "yuv420p"])

    else:
        args.extend(_get_codec_args(codec=codec, mode=mode, custom_crf=custom_crf, preset=preset, fps_val=fps_val))

    # 6. Standard TikTok BT.709 Color Matrix Tags
    # Ensures colors look vibrant and accurate on all iPhone and Android displays
    args.extend([
        "-color_primaries", "bt709",
        "-color_trc", "bt709",
        "-colorspace", "bt709",
    ])

    # 7. TikTok Audio Specifications: AAC-LC, 192kbps, 48kHz stereo
    if audio_mode == "copy" and mode not in ("tiktok_best", "tiktok_60fps"):
        args.extend(["-c:a", "copy"])
    else:
        args.extend([
            "-c:a", "aac",
            "-b:a", "192k",
            "-ar", "48000",
            "-ac", "2",
        ])

    # 8. Web FastStart (Moov atom at beginning for instant TikTok uploading and processing)
    args.extend(["-movflags", "+faststart"])

    args.append(output_file)
    return args
