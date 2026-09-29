#!/usr/bin/env python3
"""
TikTok Video Compressor CLI
Compresses videos specifically tailored for TikTok's ingestion algorithms.
Prevents TikTok from ruining video quality, eliminates color washing, and preserves razor-sharp details.
"""

import argparse
import glob
import os
import sys
import time

# Ensure UTF-8 output on Windows terminal
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except AttributeError:
        pass

from rich.console import Console
from rich.panel import Panel
from rich.progress import BarColumn, Progress, SpinnerColumn, TextColumn, TimeRemainingColumn
from rich.prompt import Confirm, Prompt
from rich.table import Table

import compressor

console = Console(force_terminal=True)


def display_banner():
    banner = (
        "[bold magenta]🎵 TikTok Video Compressor[/bold magenta]\n"
        "[dim]Pre-compress videos to bypass TikTok's destructive compression & keep 100% sharpness[/dim]"
    )
    console.print(Panel(banner, border_style="magenta", expand=False))


def format_duration(seconds: float) -> str:
    seconds = max(0, int(seconds))
    m, s = divmod(seconds, 60)
    h, m = divmod(m, 60)
    if h > 0:
        return f"{h:d}h {m:02d}m {s:02d}s"
    return f"{m:02d}m {s:02d}s"


def run_compression(
    input_file: str,
    output_file: str,
    codec: str,
    mode: str,
    target_size_mb: float = None,
    verify_quality: bool = False,
    crf: int = None,
    preset: str = None,
    sharpen: bool = True,
    scale_to_1080p: bool = True,
):
    if not output_file:
        base, _ = os.path.splitext(input_file)
        output_file = f"{base}_tiktok.mp4"
    elif output_file.lower().endswith(".mov") and codec.lower() in ("av1", "libsvtav1"):
        output_file = os.path.splitext(output_file)[0] + ".mp4"

    try:
        info = compressor.probe_video(input_file)
    except Exception as e:
        console.print(f"[bold red]❌ Error probing file {input_file}:[/bold red] {e}")
        return

    # Print input specs table
    table = Table(title=f"Source: {info.filename}", show_header=True, header_style="bold magenta")
    table.add_column("Property", style="cyan")
    table.add_column("Value", style="green")

    table.add_row("Resolution", info.resolution_str + (" (Vertical 9:16)" if info.is_vertical_9_16 else " (Landscape/Custom)"))
    table.add_row("Framerate", info.fps_str)
    table.add_row("Duration", format_duration(info.duration_seconds))
    table.add_row("Original Size", compressor.format_bytes(info.size_bytes))
    table.add_row("Color Profile", "HDR (Auto-Tonemapped to BT.709)" if info.is_hdr else "SDR BT.709 Standard")
    table.add_row("TikTok Preset", mode.replace("_", " ").title())
    table.add_row("Micro-Sharpening", "Enabled (Counteracts TikTok recompression blur)" if sharpen else "Disabled")
    table.add_row("Target Codec", codec.upper())
    console.print(table)

    comp = compressor.VideoCompressor(
        codec=codec,
        mode=mode,
        custom_crf=crf,
        preset=preset,
        sharpen=sharpen,
        scale_to_1080p=scale_to_1080p,
    )

    with Progress(
        SpinnerColumn(),
        TextColumn("[bold magenta]{task.description}"),
        BarColumn(bar_width=40),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        TextColumn("[dim]• {task.fields[speed]} • {task.fields[bitrate]} • ETA:"),
        TimeRemainingColumn(),
        console=console,
    ) as progress:
        task = progress.add_task(
            "Optimizing for TikTok...",
            total=100,
            speed="1.0x",
            bitrate="--",
        )

        def on_progress(p: compressor.ProgressUpdate):
            progress.update(
                task,
                completed=p.percent,
                speed=p.speed,
                bitrate=p.bitrate,
            )

        try:
            result = comp.compress(
                input_path=input_file,
                output_path=output_file,
                target_size_mb=target_size_mb,
                progress_callback=on_progress,
                verify_quality=verify_quality,
            )
            progress.update(task, completed=100)
        except Exception as e:
            console.print(f"\n[bold red]❌ Compression failed:[/bold red] {e}")
            return

    # Summary Panel
    color = "green" if result.space_saved_percent > 0 else "yellow"
    summary_text = (
        f"[bold]TikTok Ready File:[/bold] {result.output_path}\n"
        f"[bold]Original Size:[/bold] {result.original_size_str}\n"
        f"[bold]Compressed Size:[/bold] {result.compressed_size_str}\n"
        f"[bold]Space Saved:[/bold] [{color}]{result.space_saved_str} ({result.space_saved_percent:.2f}% reduction)[/{color}]\n"
        f"[bold]Encoding Time:[/bold] {result.elapsed_time_seconds:.1f}s (Speed: {result.average_speed})\n\n"
        f"[bold green]✔ Fully Optimized for TikTok Ingestion[/bold green]\n"
        f"• VBV Bitrate ceiling applied (Bypasses TikTok server recompression)\n"
        f"• Rec.709 Color tags embedded (Prevents washed-out mobile display)\n"
        f"• FastStart moov atom added for instant TikTok playback"
    )

    if result.quality_score:
        score = result.quality_score
        ssim_str = f"{score.ssim:.4f}" if score.ssim else "N/A"
        psnr_str = f"{score.psnr_avg_db:.2f} dB" if score.psnr_avg_db else "N/A"
        badge = "[bold green]✔ ZERO PERCEPTIBLE QUALITY LOSS[/bold green]" if score.is_visually_lossless else "[yellow]Lossy[/yellow]"
        summary_text += (
            f"\n\n[bold]Scientific Quality Verification:[/bold] {badge}\n"
            f"• SSIM Score: {ssim_str} (>= 0.95 is visually identical to source)\n"
            f"• PSNR Score: {psnr_str} (>= 40 dB is broadcast-grade master quality)"
        )

    console.print(Panel(summary_text, title="TikTok Optimization Complete", border_style="magenta", expand=False))


def interactive_mode():
    display_banner()
    console.print("\n[bold]Interactive TikTok Setup Wizard[/bold]\n")

    input_file = Prompt.ask("Enter path to your video file").strip('"\'')
    while not os.path.exists(input_file):
        console.print("[red]File not found. Please try again.[/red]")
        input_file = Prompt.ask("Enter path to your video file").strip('"\'')

    mode_options = [
        ("tiktok_best", "TikTok Best Quality (Recommended: 1080p, Lanczos scale, Rec.709 color, crisp micro-details)"),
        ("tiktok_60fps", "TikTok 60fps Smooth (For gaming, dance, and fast action clips)"),
        ("target_size", "Target File Size (Fit under exact MB, e.g. 50MB)"),
        ("visually_lossless", "Standard Visually Lossless (Zero quality loss, universal playback)"),
    ]
    console.print("\nSelect Optimization Mode:")
    for idx, (_, desc) in enumerate(mode_options, 1):
        console.print(f"  [{idx}] {desc}")

    m_choice = Prompt.ask("Select mode", choices=["1", "2", "3", "4"], default="1")
    chosen_mode = mode_options[int(m_choice) - 1][0]

    codecs = compressor.get_available_encoders()
    codec_options = []
    if codecs.get("libx264"):
        codec_options.append("h264 (TikTok Gold Standard - Most compatible with TikTok servers)")
    if codecs.get("h264_nvenc"):
        codec_options.append("nvenc_h264 (NVIDIA GPU Hardware Accelerated - Ultra fast)")
    if codecs.get("libx265"):
        codec_options.append("hevc (H.265 - Maximum compression efficiency)")
    if codecs.get("libsvtav1"):
        codec_options.append("av1 (SVT-AV1 - Next-generation compression)")

    console.print("\nSelect Video Encoder:")
    for idx, opt in enumerate(codec_options, 1):
        console.print(f"  [{idx}] {opt}")

    c_choice = Prompt.ask("Select encoder", choices=[str(i) for i in range(1, len(codec_options) + 1)], default="1")
    chosen_codec = codec_options[int(c_choice) - 1].split()[0]

    target_mb = None
    if chosen_mode == "target_size":
        target_mb = float(Prompt.ask("Enter target size in Megabytes (e.g. 25, 50, 75)", default="50"))

    verify = Confirm.ask("Compute SSIM/PSNR mathematical quality check after encoding?", default=True)

    base, _ = os.path.splitext(input_file)
    default_out = f"{base}_tiktok.mp4"
    output_file = Prompt.ask("Output file path", default=default_out).strip('"\'')

    console.print("\n")
    run_compression(
        input_file=input_file,
        output_file=output_file,
        codec=chosen_codec,
        mode=chosen_mode,
        target_size_mb=target_mb,
        verify_quality=verify,
        sharpen=True,
        scale_to_1080p=True,
    )


def main():
    parser = argparse.ArgumentParser(
        description="TikTok Video Compressor — Pre-compress and optimize videos for TikTok to prevent quality destruction."
    )
    parser.add_argument("input", nargs="?", help="Input video file or directory path")
    parser.add_argument("-o", "--output", help="Output file path (default: <input>_tiktok.mp4)")
    parser.add_argument(
        "-c", "--codec",
        choices=["h264", "hevc", "av1", "nvenc_h264", "nvenc_hevc"],
        default="h264",
        help="Compression codec (default: h264 for optimal TikTok server ingest)",
    )
    parser.add_argument(
        "-m", "--mode",
        choices=["tiktok_best", "tiktok_60fps", "visually_lossless", "high_compression", "lossless", "target_size"],
        default="tiktok_best",
        help="Optimization mode (default: tiktok_best)",
    )
    parser.add_argument(
        "--60fps",
        dest="sixty_fps",
        action="store_true",
        help="Force 60fps constant frame rate for smooth TikTok playback",
    )
    parser.add_argument(
        "--target-size-mb",
        type=float,
        help="Target output size in Megabytes",
    )
    parser.add_argument(
        "--gpu",
        action="store_true",
        help="Use NVIDIA NVENC hardware acceleration for ultra-fast compression",
    )
    parser.add_argument(
        "--no-sharpen",
        action="store_true",
        help="Disable adaptive micro-detail sharpening",
    )
    parser.add_argument(
        "--no-scale",
        action="store_true",
        help="Disable automatic 4K to 1080p Lanczos scaling",
    )
    parser.add_argument(
        "--verify-quality",
        action="store_true",
        help="Calculate SSIM and PSNR to mathematically verify zero quality loss",
    )
    parser.add_argument(
        "--crf",
        type=int,
        help="Custom CRF rate control factor",
    )
    parser.add_argument(
        "--preset",
        help="Custom encoder preset (e.g. slow, medium, p6)",
    )
    parser.add_argument(
        "--batch",
        action="store_true",
        help="Batch optimize all videos in the input directory for TikTok",
    )
    parser.add_argument(
        "-i", "--interactive",
        action="store_true",
        help="Launch interactive TikTok creator wizard",
    )

    args = parser.parse_args()

    if args.interactive or not args.input:
        interactive_mode()
        return

    display_banner()

    codec = args.codec
    if args.gpu:
        codec = "nvenc_h264"

    mode = args.mode
    if args.sixty_fps:
        mode = "tiktok_60fps"
    elif args.target_size_mb:
        mode = "target_size"

    input_path = os.path.abspath(args.input)

    # Batch directory compression
    if args.batch or os.path.isdir(input_path):
        if not os.path.isdir(input_path):
            console.print(f"[bold red]❌ Input path is not a directory:[/bold red] {input_path}")
            return

        extensions = ["*.mp4", "*.mkv", "*.mov", "*.avi", "*.flv", "*.webm", "*.ts"]
        files = []
        for ext in extensions:
            files.extend(glob.glob(os.path.join(input_path, ext)))
            files.extend(glob.glob(os.path.join(input_path, ext.upper())))

        files = [f for f in sorted(list(set(files))) if not f.endswith("_tiktok.mp4") and "_tiktok" not in f]

        if not files:
            console.print(f"[yellow]No video files found in {input_path}[/yellow]")
            return

        console.print(f"[bold magenta]Found {len(files)} videos to optimize for TikTok.[/bold magenta]\n")
        out_dir = args.output or os.path.join(input_path, "tiktok_ready")
        os.makedirs(out_dir, exist_ok=True)

        total_orig = 0
        total_comp = 0
        for idx, f in enumerate(files, 1):
            console.print(f"\n[bold magenta]Processing [{idx}/{len(files)}]:[/bold magenta] {os.path.basename(f)}")
            base = os.path.splitext(os.path.basename(f))[0]
            out_file = os.path.join(out_dir, f"{base}_tiktok.mp4")
            run_compression(
                input_file=f,
                output_file=out_file,
                codec=codec,
                mode=mode,
                target_size_mb=args.target_size_mb,
                verify_quality=args.verify_quality,
                crf=args.crf,
                preset=args.preset,
                sharpen=not args.no_sharpen,
                scale_to_1080p=not args.no_scale,
            )
            if os.path.exists(f) and os.path.exists(out_file):
                total_orig += os.path.getsize(f)
                total_comp += os.path.getsize(out_file)

        saved = max(0, total_orig - total_comp)
        pct = (saved / total_orig * 100.0) if total_orig else 0.0
        console.print(Panel(
            f"[bold]Batch TikTok Optimization Complete![/bold]\n"
            f"Original Total: {compressor.format_bytes(total_orig)}\n"
            f"TikTok Ready Total: {compressor.format_bytes(total_comp)}\n"
            f"[bold green]Total Space Saved: {compressor.format_bytes(saved)} ({pct:.2f}% reduction)[/bold green]",
            border_style="magenta",
        ))

    # Single file compression
    else:
        run_compression(
            input_file=input_path,
            output_file=args.output,
            codec=codec,
            mode=mode,
            target_size_mb=args.target_size_mb,
            verify_quality=args.verify_quality,
            crf=args.crf,
            preset=args.preset,
            sharpen=not args.no_sharpen,
            scale_to_1080p=not args.no_scale,
        )


if __name__ == "__main__":
    main()
