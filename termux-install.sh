#!/data/data/com.termux/files/usr/bin/bash
# 🎵 TikTok Video Compressor — Termux One-Click Auto-Installer
# Sets up Python, FFmpeg, storage permissions, and creates a global shortcut.

set -e

echo ""
echo "=========================================================="
echo "  🎵 TikTok Video Compressor — Termux Mobile Installer    "
echo "=========================================================="
echo ""

# 1. Request Phone Storage Permission
echo "[1/4] Requesting phone storage permissions..."
termux-setup-storage
sleep 2

# 2. Update Packages & Install Dependencies
echo "[2/4] Installing Python, Git, and FFmpeg..."
pkg update -y
pkg install -y python git ffmpeg

# 3. Install Python Dependencies
echo "[3/4] Installing Python packages (rich)..."
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"
pip install -r requirements.txt

# 4. Set up Global Terminal Shortcut
echo "[4/4] Creating terminal shortcut 'tiktok-compress'..."
BASHRC="$HOME/.bashrc"
ALIAS_CMD="alias tiktok-compress='python $SCRIPT_DIR/compress.py'"

if ! grep -q "tiktok-compress" "$BASHRC" 2>/dev/null; then
    echo "" >> "$BASHRC"
    echo "# TikTok Video Compressor Shortcut" >> "$BASHRC"
    echo "$ALIAS_CMD" >> "$BASHRC"
fi

echo ""
echo "=========================================================="
echo "  ✨ Installation Complete!                               "
echo "=========================================================="
echo ""
echo "You can now compress videos directly from your camera roll:"
echo "  tiktok-compress ~/storage/dcim/Camera/VID_example.mp4"
echo ""
echo "Or start the interactive creator wizard:"
echo "  tiktok-compress -i"
echo ""
