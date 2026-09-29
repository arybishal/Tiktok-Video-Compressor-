# TikTok Video Compressor — Full Setup & Creator Guide

A complete guide for creators and developers to install, configure, and use **TikTok Video Compressor** to pre-compress and optimize videos before uploading to TikTok.

---

## Table of Contents
1. [Why Pre-Compressing for TikTok is Essential](#1-why-pre-compressing-for-tiktok-is-essential)
2. [TikTok Optimal Video Specifications](#2-tiktok-optimal-video-specifications)
3. [Prerequisites & System Requirements](#3-prerequisites--system-requirements)
4. [Installation & Setup](#4-installation--setup)
   - [Windows Installation](#windows-installation)
   - [macOS Installation](#macos-installation)
   - [Linux (Ubuntu/Debian) Installation](#linux-ubuntudebian-installation)
   - [Android (Termux) Installation](#android-termux-installation)
5. [Command Line (CLI) Creator Guide](#5-command-line-cli-creator-guide)
6. [Python Library Integration](#6-python-library-integration)
7. [Hardware Acceleration (NVIDIA NVENC)](#7-hardware-acceleration-nvidia-nvenc)
8. [Creator Best Practices for 100% Crisp TikToks](#8-creator-best-practices-for-100-crisp-tiktoks)

---

## 1. Why Pre-Compressing for TikTok is Essential

When you record in 4K or at high bitrates (30–80 Mbps on iPhone, mirrorless cameras, or OBS), uploading the raw file directly causes TikTok's servers to aggressively degrade your video:

1. **Blurry Downscaling**: TikTok uses a fast, low-quality server downscaling algorithm that blurs sharp textures.
2. **Brutal Bitrate Destruction**: TikTok's automated compressor crushes bitrates down to ~2,000–5,000 kbps, causing blocky artifacts in movement.
3. **Washed-Out Colors**: iPhone HDR (Dolby Vision / HLG) loses its metadata during TikTok's recompression, causing footage to look gray, faded, and desaturated.

**The Solution:**
By pre-optimizing your video with **TikTok Video Compressor**, the file is encoded to match TikTok's exact ingestion profile. TikTok's ingestion bot recognizes the video as already optimized, passing it through without destructive server-side recompression.

---

## 2. TikTok Optimal Video Specifications

| Parameter | Recommended Setting | What This Tool Applies |
| :--- | :--- | :--- |
| **Aspect Ratio** | 9:16 Vertical | Automatically detected or preserved |
| **Resolution** | 1080 x 1920 | High-quality **Lanczos algorithm** downscales 4K footage |
| **Framerate** | 30 fps or 60 fps | Constant Frame Rate (CFR) avoids audio de-sync |
| **Video Codec** | H.264 High Profile Level 4.2 | Gold standard for TikTok server compatibility |
| **Color Matrix** | Rec.709 Standard (SDR) | Auto-tonemaps iPhone HDR to prevent washed-out colors |
| **Bitrate Control** | VBV Capped (8M – 14M) | Avoids triggering TikTok’s server-side downscaler |
| **Audio** | AAC-LC, 192 kbps, 48 kHz stereo | Maximum audio clarity without distortion |
| **Container** | MP4 with FastStart | Moov atom at file start for instant upload processing |

---

## 3. Prerequisites & System Requirements

* **Python 3.9+** (Compatible with Python 3.9, 3.10, 3.11, 3.12, 3.13, and 3.14).
* **FFmpeg** and **ffprobe** installed and added to your system PATH.

---

## 4. Installation & Setup

### Windows Installation
1. Install **FFmpeg** (using PowerShell):
   ```powershell
   winget install Gyan.FFmpeg
   ```
2. Open PowerShell in the project directory:
   ```powershell
   cd C:\path\to\CompressorBot
   ```
3. Set up and activate a virtual environment:
   ```powershell
   python -m venv venv
   .\venv\Scripts\Activate.ps1
   ```
4. Install dependencies:
   ```powershell
   pip install -r requirements.txt
   ```

### macOS Installation
1. Install FFmpeg using Homebrew:
   ```bash
   brew install ffmpeg
   ```
2. Navigate to directory and set up environment:
   ```bash
   cd CompressorBot
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

### Linux (Ubuntu/Debian) Installation
```bash
sudo apt update && sudo apt install -y ffmpeg python3 python3-pip python3-venv
cd CompressorBot
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Android (Termux) Installation
You can run **TikTok Video Compressor** directly on Android phones using [Termux](https://termux.dev/) to pre-compress recordings before posting:

1. **Install Termux** (Download from [F-Droid](https://f-droid.org/en/packages/com.termux/) or GitHub Releases — avoid the outdated Google Play Store build).
2. **Grant Storage Access** (allows reading videos from DCIM, Movies, and Downloads):
   ```bash
   termux-setup-storage
   ```
3. **Install Python, Git, and FFmpeg**:
   ```bash
   pkg update && pkg upgrade -y
   pkg install -y python git ffmpeg
   ```
4. **Clone Repository & Install Dependencies**:
   ```bash
   git clone https://github.com/arybishal/Tiktok-Video-Compressor-.git
   cd Tiktok-Video-Compressor-
   pip install -r requirements.txt
   ```
5. **Optimize Videos Directly from Phone Storage**:
   ```bash
   python compress.py ~/storage/dcim/Camera/VID_example.mp4
   ```
   *(Or launch the interactive setup wizard with `python compress.py -i`)*

> [!TIP]
> **Mobile Performance Tip**: On Android devices, select **Encoder [1] `h264`** (with preset `fast` or `medium`). Modern mobile ARM processors encode H.264 very quickly with NEON hardware-level instruction sets.

---

## 5. Command Line (CLI) Creator Guide

### 1. Default Best Quality TikTok Optimization
```bash
python compress.py my_video.mp4
```
*Performs 1080p Lanczos scaling, Rec.709 color calibration, micro-sharpening, and VBV bitrate capping. Outputs to `my_video_tiktok.mp4`.*

### 2. Smooth 60fps Mode (For Gaming & Fast Motion)
```bash
python compress.py gameplay.mp4 --60fps
```
*Forces constant 60fps pacing and adjusts the VBV bitrate limit to 14 Mbps for fluid motion.*

### 3. Ultra-Fast Compression with NVIDIA GPU
```bash
python compress.py raw_clip.mp4 --gpu
```
*Uses hardware NVENC encoding on your NVIDIA graphics card (encodes at 5x–10x real-time speed).*

### 4. Mathematical Quality Verification (SSIM / PSNR)
```bash
python compress.py clip.mp4 --verify-quality
```
*Calculates and displays the exact SSIM (Structural Similarity) and PSNR scores proving zero perceptible quality loss.*

### 5. Batch Process an Entire Directory of Videos
```bash
python compress.py C:\Users\User\Videos\TikTokDrafts\ --batch
```
*Automatically finds all video files in the folder and saves TikTok-ready versions in a `tiktok_ready/` subfolder.*

### 6. Interactive Creator Wizard
```bash
python compress.py --interactive
```
*Launches an interactive prompt guiding you step-by-step through codec selection, resolution, and quality presets.*

---

## 6. Python Library Integration

Import and use the compression engine directly in your own Python editing and rendering pipelines:

```python
from compressor import compress_video, VideoCompressor, probe_video

# 1. Quick TikTok compression
result = compress_video(
    input_file="input.mp4",
    output_file="output_tiktok.mp4",
    mode="tiktok_best",
    verify_quality=True,
)

print(f"Original:   {result.original_size_str}")
print(f"Compressed: {result.compressed_size_str} ({result.space_saved_percent:.1f}% space saved)")

# 2. Advanced customization
compressor = VideoCompressor(
    codec="h264",         # TikTok gold standard
    mode="tiktok_60fps",  # Constant 60fps
    sharpen=True,         # Retain micro-details
    scale_to_1080p=True,  # Downscale 4K to 1080p
)

result = compressor.compress(
    input_path="raw_video.mp4",
    output_path="tiktok_ready.mp4",
)
```

---

## 7. Hardware Acceleration (NVIDIA NVENC)

If you have an NVIDIA GPU (e.g. GTX 1650, RTX 20/30/40 series):
* The tool automatically detects your GPU and supports `--gpu` mode.
* NVENC offloads video processing from your CPU, allowing full 1080p 60fps renders in seconds.

---

## 8. Creator Best Practices for 100% Crisp TikToks

1. **Always Pre-Downscale 4K**: Never upload raw 4K directly. Pre-downscaling to 1080x1920 using Lanczos gives vastly sharper results than TikTok's mobile app.
2. **Turn on "Allow High-Quality Uploads" in the TikTok App**:
   - In TikTok: Go to **Profile** > **Settings and Privacy** > **Data Saver** > Turn **Data Saver OFF**.
   - When posting: On the final upload screen, tap **More options** > Toggle **Allow high-quality uploads ON**.
3. **Use Constant Frame Rate (CFR)**: Phone recordings with variable frame rates cause micro-stutter and audio drift; this tool locks frames to constant 30fps or 60fps.
