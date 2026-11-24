# Flood — Atari STE Enhanced (v1.0)

**Original game:** Bullfrog Productions / Electronic Arts (1990)  
**Status:** v1.0 built, verified across ST / STE / Mega STE / TT / Falcon + auto-booting 720 KB floppy.

## What's Implemented

1. **STE Blitter Acceleration & Smooth 1-Pixel Horizontal Scrolling (`patches/flood_patch.s`):**
   - **Smooth 1-pixel horizontal camera & tilemap (`$013606` & `$0136e6`):** Replaces the original ST's jerky 128-pixel chunk jumps with continuous 1-pixel camera tracking centered on Quiffy. Renders a 21-tile-wide (336×192, stride 168 B) cached background buffer (`bg_cache`) only when `coarse_x`/`scroll_y`/tiles change, then copies to the backbuffer via STE Blitter hardware `FXSR` barrel-shifting (`SKEW = $80 | (16 - fine_x)`), or a dedicated 32 MHz CPU `lsl.l` shift path on Atari TT (no Blitter).
   - **1-pixel smooth water overlay (`$013988`):** Shifts native ST `W_BLOCKS.BLK` water tiles by `fine_x` with left/right clipping so waterfalls and puddles stay pixel-locked to the scrolling cavern.
   - **32×32 masked sprites (`$01e248`):** STE Blitter hardware `SKEW` + `NFSR` + `ENDMASK` run-length blitting (4.3× faster than CPU `ror.l` shifting: 12.8% → 3.0% CPU).
   - Automatic runtime Blitter probe (`$ffff8a3c.w`) with clean CPU fallback on plain ST and TT.
2. **Fixed 25.0 Hz VBL Frame Pacing (`$01328e`):**
   - Paces the main loop via Flood's VBL counter (`$01e92c`) to exact 2-VBL intervals (25.0 fps).
   - Eliminates 8 MHz slowdowns (17.5–20.0 → 24.6–25.0 fps) and prevents 16 MHz Mega STE / 32 MHz TT / Falcon from running at 2.5×–2.9× speed.
3. **Full Amiga 4-Channel Stereo Audio on STE DMA (`$ff8900`, 12,517 Hz):**
   - Relocated the exact 3,932-byte Amiga 68000 music/SFX sequencer from `alt/amiga/Flood (Bullfrog + Electronic Arts).adf` (`RUN_PROG` `$00d0a8–$00e004`), redirecting Paula `$dff0a0/$dff096` writes to 4 Virtual Paula channels mixed into an atomic cursor-tracked 2,000-byte (8 × 250 B = 80 ms) circular STE DMA ring buffer at 12,517 Hz stereo (works cleanly at 50 Hz, 60 Hz, and 71 Hz with zero dropouts or tempo drift).
   - **Title / High-Score / Ending:** Full Amiga music (`TRACK.DA` + `INSTR.DA` → `AM_MUS.BIN`, 129,920 B).
   - **Gameplay:** Full Amiga 4-channel stereo SFX (`FLDFX.DU` + `FLDFX.IN` → `AM_SFX.BIN`, 99,460 B) with SFX ID bounds guard (`1..61`), replacing ST Timer A YM2149 digi-SFX (cutting audio CPU cost from 12.7% → 8.0%).
   - Automatic runtime STE DMA probe (`$ffff8901.w`) with clean fallback to ST YM audio on plain ST — plus Falcon-safe YM mirror fix (`$01acd4`, **0 `crit`** in `tools/hwscan.py`).
4. **Polish & Compatibility Fixes:**
   - Restored Amiga 12-bit STE palettes for tilesets **B** (`pal 1`) and **C** (`pal 2`) — ST originally duplicated tileset A's palette across all 3 slots.
   - Disables IKBD mouse reporting (`$12`) on startup and re-enables (`$08`) on exit so mouse movement cannot inject spurious joystick/keyboard packets into Flood's IKBD handler.
   - Switches TT / Medium-res video modes cleanly to ST Low (`Setscreen(-1,-1,0)`) and restores on exit.
   - Added subtle `"enhanced by dad_prg v1.0"` banner at top-left of the title/password screen.

## Verification Results

| Machine | Media | FPS (Live Lv1) | Audio | Status |
|---|---|---:|---|---|
| **1 MB 8 MHz STE** (TOS 1.62) | HD (`FLO.PRG`) | **24.6–25.0 fps** (up from 17.5) | 12.5 kHz Stereo Amiga DMA (Title WAV RMS L=2739/R=1932, SFX WAV RMS L=741/R=767) | Pass |
| **1 MB 8 MHz STE** (TOS 1.62) | **720 KB Floppy** (`Flood_v1.0.st`) | **Auto-boots** from `\AUTO\FLO.PRG` | 12.5 kHz Stereo Amiga DMA | Pass |
| **1 MB 8 MHz ST** (TOS 1.04) | HD (`FLO.PRG`) | **25.0 fps** (CPU fallback) | ST YM fallback, 0 errors | Pass |
| **2 MB 16 MHz Mega STE** (TOS 2.06) | HD (`FLO.PRG`) | **Paced (no 2.5× speedup)** | 12.5 kHz Stereo Amiga DMA, 0 errors | Pass |
| **4 MB 32 MHz TT** (TOS 3.06) | HD (`FLO.PRG`) | **25.0 fps** (down from 50.0) | 12.5 kHz Stereo Amiga DMA, 0 errors | Pass |
| **4 MB 16 MHz Falcon** (TOS 4.04) | HD (`FLO.PRG`) | **25.0 fps** | 12.5 kHz Stereo Amiga DMA, 0 errors | Pass |

## Build & Package

```bash
python3 games/done/flood/tools/build_flood.py
python3 games/done/flood/tools/package_flood.py --version v1.0
```

Outputs (gitignored):
- `dist/Flood_hd_v1.0.zip` (491 KB) — ready-to-run HD `FLOOD/` folder
- `dist/Flood_floppy_v1.0.zip` (485 KB) — auto-booting 720 KB Atari ST/STE floppy image (`Flood_v1.0.st`)

## Files

- [patches/flood_patch.s](patches/flood_patch.s) — 68000 patch source (STE Blitter, 25 Hz pacer, 4-frame water, Virtual Paula + 12.5 kHz stereo STE DMA mixer)
- [tools/build_flood.py](tools/build_flood.py) — Unpacks `FLO.FIC`, extracts Amiga assets from ADF, relocates Amiga sequencer blob, links `FLO.PRG`
- [tools/package_flood.py](tools/package_flood.py) — Builds HD and 720 KB auto-booting floppy `.zip` releases
- [work/notes/baseline.md](work/notes/baseline.md) — Baseline profile, RAM map, hardware scan, and Amiga ADF audit
