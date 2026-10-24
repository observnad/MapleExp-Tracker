# 🍁 MapleEXP Tracker

[![Download MapleEXPTracker.exe](https://img.shields.io/badge/Download-MapleEXPTracker.exe-brightgreen?style=for-the-badge&logo=windows)](https://github.com/observnad/MapleExp-Tracker/releases/latest/download/MapleEXPTracker.exe)
[![GitHub Release](https://img.shields.io/github/v/release/observnad/MapleExp-Tracker?style=for-the-badge&color=blue)](https://github.com/observnad/MapleExp-Tracker/releases/latest)

> 📥 **Direct Download for Friends**: Click **[MapleEXPTracker.exe](https://github.com/observnad/MapleExp-Tracker/releases/latest/download/MapleEXPTracker.exe)** to download the standalone executable. No Python or installation needed—just double-click to run!

---

A lightweight, high-performance, standalone desktop tracker for MapleStory that continuously monitors your experience points (EXP) and calculates rolling gains and rates across **1m, 5m, 10m, 30m, and 1h** intervals.

---

## 🌟 Key Features

- **Multi-Window & Multi-Scale Support**:
  - Automatically detects the game window and dynamic UI scaling factor without hardcoded coordinates.
  - Adapts instantly when the window is resized, moved, or when UI scaling changes.
- **Rolling Time Windows**:
  - **1 Minute**: Rapid feedback on current grinding spot efficiency.
  - **5 Minutes**: Short-term burst rate.
  - **10 Minutes**: Standard battle analysis window.
  - **30 Minutes**: Long grind pacing.
  - **1 Hour**: Full hourly projection (`EXP/hr` and `% / hr`).
- **Comprehensive Session Analytics**:
  - Current EXP number (with comma formatting) & exact percentage `[XX.XX%]`.
  - In-game style yellow progress bar fill with subpixel cross-verification.
  - Total Session EXP gained & session duration timer.
  - **Level Up ETA**: Real-time projection estimating time until next level up.
  - **Level-Up Handling**: Seamlessly detects when level resets to 0% and accurately accounts for cumulative gain.
- **Gamer-Centric Overlay UI**:
  - Modern dark theme with rounded cards.
  - **📌 Always on Top**: Keep the tracker visible over your game window while grinding.
  - **🔄 Reset Session**: Start a fresh battle analysis session with one click.
  - **⏸ Pause / Resume**: Temporarily halt tracking when taking breaks or chatting.
  - **👁 Live Preview**: Collapsible drawer showing the real-time crop of the EXP bar and character recognition.
- **Zero-Dependency Executable (`.exe`)**:
  - Self-contained single executable. Friends can double-click and run immediately without installing Python or any libraries.

---

## 🚀 How to Run

### Option 1: Standalone Executable (For You & Friends)
Simply send or run the pre-built `.exe`:
```
dist\MapleEXPTracker.exe
```
No installation or Python environment required!

### Option 2: Running from Source
If modifying the codebase:
```powershell
# Activate virtual environment
.\.venv\Scripts\activate

# Run application
python -m src.app
```

### Option 3: Rebuilding the Executable
To recompile the `.exe` after making changes:
```powershell
python build_exe.py
```
The compiled output will be generated in the `dist/` directory.

---

## 📐 How the Detection Works

1. **Window Capture**: Uses low-overhead Win32 GDI `BitBlt` to capture only the bottom region of the MapleStory window. CPU impact is imperceptible (< 0.5% at 1 Hz).
2. **Multi-Scale Anchor Matching**: Performs normalized cross-correlation matching using an embedded `EXP.` logo template across scale factors ranging from `0.6x` to `2.5x`.
3. **Adaptive Pixel-Font OCR**: Once the logo is locked, it extracts the subsequent text area, normalizes the scale grid, and segments characters by column projections. Each character (`0-9`, `,`, `.`, `[`, `]`, `%`) is matched against exact bitmap signatures.
4. **Yellow Bar Cross-Validation**: Simultaneously scans the progress bar fill row directly below the text to confirm the visual fill percentage against the text percentage.
