# 🍁 MapleEXP Tracker

[![GitHub Pages](https://img.shields.io/badge/GitHub%20Pages-Live%20Web%20App-brightgreen?style=for-the-badge&logo=github)](https://observnad.github.io/MapleExp-Tracker/)
[![Download MapleEXPTracker.exe](https://img.shields.io/badge/Download-MapleEXPTracker.exe-blue?style=for-the-badge&logo=windows)](https://github.com/observnad/MapleExp-Tracker/releases/latest/download/MapleEXPTracker.exe)
[![GitHub Release](https://img.shields.io/github/v/release/observnad/MapleExp-Tracker?style=for-the-badge&color=orange)](https://github.com/observnad/MapleExp-Tracker/releases/latest)

> 🌐 **Live Web Edition (Zero Install)**: Open **[MapleEXP Tracker Web App](https://observnad.github.io/MapleExp-Tracker/)** in Chrome or Edge to track directly in your browser using Window Capture!  
> 📥 **Desktop Executable**: Click **[MapleEXPTracker.exe](https://github.com/observnad/MapleExp-Tracker/releases/latest/download/MapleEXPTracker.exe)** for the standalone Windows desktop overlay.

---

A high-performance, real-time battle analysis & experience tracker for MapleStory that continuously monitors your EXP, rolling rates (**1m, 5m, 10m, 30m, 1h**), and 3x4 quickslot item quantities with configurable **Low-Item Full-App Red Alert Warnings**.

Now available as a **GitHub Pages Web Application** (Chrome Screen Capture & Recording) and a **Standalone Desktop Application**!

---

## 🌟 Web Application Features (GitHub Pages & Chrome)

- **🎥 Chrome "Record App Window" / Screen Capture**:
  - Click **"📹 Select MapleStory Window"** to choose your MapleStory game window using Chrome's native Screen Capture API (`navigator.mediaDevices.getDisplayMedia`).
  - No Python, no drivers, and no installation required—works on any desktop Chromium browser (Chrome, Edge, Brave, Opera).
- **🔴 Built-in Window Recording & Download**:
  - Record your gameplay grinding sessions with **`MediaRecorder`**.
  - One-click **"Start Recording"** with live timer badge, followed by instant `.webm` video download.
- **📌 Picture-in-Picture (PiP) Floating Always-on-Top Overlay**:
  - Click **"📌 Float (PiP)"** to pop out a compact, floating statistics overlay that stays **Always-on-Top** over MapleStory while you play!
  - Displays current EXP, yellow progress bar, hourly rates, and monitored item counts.
- **⚡ 1-Click Instant Demo & Image Drag-and-Drop**:
  - Test the web app immediately without launching the game using the **"⚡ 1-Click Demo Screen"** button or by dragging and dropping any screenshot or recording.
- **🔔 Audio Alerts via Web Audio API**:
  - Audible two-tone chime when your monitored potion or item count drops below threshold. Toggleable with the Sound button.
- **💾 Session Log Export**:
  - Download complete CSV logs of your battle analysis session with timestamps and EXP deltas.

---

## 🎒 Hotbar Item Monitor & Low Quantity Red Alert

- **Live 3x4 Hotbar Grid**:
  - Screencaps all MapleStory quickslots (`1..4`, `Shift..Pup`, `Ctrl..Pdn`) in real time.
  - Interactive cell selector: click any slot to set custom thresholds and alerts.
- **Configurable Minimum Thresholds**:
  - Quick presets (`10`, `20`, `50`, `100`), custom numbers, and stepper buttons.
- **🚨 Full-App Red Alert Warning**:
  - When monitored item quantity drops below threshold, the entire application switches to a bold warning red theme with an alert banner and sound chime so you never run out of potions during grinds.

---

## 📈 Rolling Time Windows & Battle Analysis

- **Rolling Intervals**:
  - **1 Minute**: Rapid feedback on current grinding spot efficiency.
  - **5 Minutes**: Short-term burst rate.
  - **10 Minutes**: Standard battle analysis window.
  - **30 Minutes**: Long grind pacing.
  - **1 Hour**: Full hourly projection (`EXP/hr` and `% / hr`).
- **Interactive 128-Slice Sparkline Graph**:
  - Rolling EXP rate graph with interactive hover tooltips displaying EXP gained per slice.
- **Level Up Projection (ETA)**:
  - Real-time calculator projecting hours and minutes until 100% based on rolling rates.
- **Anti-Glitch & Portal Transition Immunity**:
  - Multi-frame dropout immunity buffers dark screen map transitions (portal transitions) without triggering false level-ups or wild rate spikes.
  - 2-pass retroactive history sanitization filters transient OCR digit anomalies.

---

## 🚀 How to Run

### Option 1: Live Web App (GitHub Pages)
Visit the live site directly:
```
https://observnad.github.io/MapleExp-Tracker/
```
1. Click **"📹 Select MapleStory Window"**.
2. In the Chrome popup, select the **"Window"** tab and click your MapleStory window.
3. (Optional) Click **"📌 Float (PiP)"** to keep a mini overlay floating over your game!

To run the web app locally:
```powershell
# Using Python
python -m http.server 8080

# Or using Node
npx serve .
```
Then navigate to `http://localhost:8080` in Chrome or Edge.

---

### Option 2: Standalone Desktop Executable (`.exe`)
Download or run the pre-compiled Windows executable:
```
dist\MapleEXPTracker.exe
```
No installation or Python environment required!

---

### Option 3: Running Desktop App from Source
```powershell
# Activate virtual environment
.\.venv\Scripts\activate

# Run desktop application
python -m src.app
```

---

## 🧪 Testing

### Running JavaScript Unit & Browser E2E Tests:
```powershell
# Core EXP tracker unit tests
node test_js/test_tracker.js

# Computer vision & OCR unit tests
node test_js/test_detector.js

# Full Headless Chrome End-to-End integration test
node test_js/test_browser_e2e.js
```

### Running Python Unit Tests:
```powershell
.\.venv\Scripts\python test_exp_tracker.py
```

---

## 📐 Detection Architecture

1. **Window Capture**:
   - Web: Chrome Screen Capture API (`navigator.mediaDevices.getDisplayMedia`).
   - Desktop: Win32 GDI `BitBlt` capturing the bottom ROI at 1 Hz.
2. **Anchor Matching**:
   - Normalized cross-correlation (NCC / `TM_CCOEFF_NORMED`) matching the embedded `EXP.` logo across scales `0.6x` to `2.5x`.
3. **Adaptive Pixel-Font OCR**:
   - Normalized to 1.0x scale, binarized (`gray > 125`), segmented by vertical projection, and matched against exact pixel bitmaps (`0-9`, `,`, `.`, `[`, `]`, `%`).
4. **Yellow Bar Cross-Validation**:
   - Evaluates progress bar yellow pixels (`R > 150, G > 180, B < 80`) vs gray fill to verify OCR percentage against graphical progress.
5. **Hotbar Quantity OCR**:
   - Matches 9px tall MapleStory font bitmaps in cell bottom-left corners with greedy non-overlapping selection.
