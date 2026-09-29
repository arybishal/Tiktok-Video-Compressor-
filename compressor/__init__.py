"""
TikTok Video Compressor — Pre-compress and optimize videos for TikTok to prevent quality degradation.
"""

from .engine import CompressionResult, ProgressUpdate, VideoCompressor, compress_video
from .hardware import get_available_encoders, get_recommended_encoder
from .metrics import QualityScore, measure_quality
from .probe import VideoInfo, format_bytes, probe_video

__version__ = "1.0.0"

__all__ = [
    "VideoCompressor",
    "compress_video",
    "probe_video",
    "measure_quality",
    "get_available_encoders",
    "get_recommended_encoder",
    "VideoInfo",
    "CompressionResult",
    "ProgressUpdate",
    "QualityScore",
    "format_bytes",
]
