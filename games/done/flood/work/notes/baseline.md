# Flood — Baseline Analysis & Hardware / Amiga Audit

## 1. Executable & Memory Map (1 MB STE, TOS 1.62)

Unpacked `FLO.FIC` (`FLO.PRG`, 51,842 B; TEXT `$bf40`, DATA `$3f0`, BSS `$480d8`) loads at TEXT base **`$012576`** under TOS 1.62 (relocatable).

| Range | Size | Usage |
|---|---:|---|
| `$000000–$012575` | ~73 KB | TOS system vars, vectors, GEMDOS |
| `$012576–$06697e` | ~337 KB | `FLO.PRG` (TEXT + DATA + BSS, incl. `B_FLOOD.ECH`, tiles, sprites, maps) |
| **`$068000–$0f7fff`** | **576 KB** | **Completely unused (0% non-zero in `ram_game.bin`)** |
| `$0f8000–$0fffff` | 32 KB | Screen RAM (double-buffered; flip at `$01273e`: `move.l d0, $ffff8200.l`) |

Vectors installed by `FLO.PRG`:
- VBL (`$70`): `$012656` (increments VBL counter `$01e92c`, sets VBL flag `$026962`, calls music tick `$01b4fa`)
- IKBD (`$118`): `$0127f0` (reads `$fffffc00/$fffffc02`, Joystick 1 interrogation `$16` → `$144f2` rel)
- MFP Timer A (`$134`): `$01acae` (YM2149 digi-SFX playback IRQ)

## 2. Baseline FPS & CPU Speed Scaling (Level 1)

Measured via `tools/stharness.py` (`flip_reg='($ff8201).b'`, 50 Hz RGB, sound enabled):

| Scenario | CPU Clock | FPS | VBLs / frame | Relative Speed |
|---|---:|---:|---:|---:|
| Level 1 (intro banner / standing) | 8 MHz STE | **25.0 fps** | 2.00 | 1.00× |
| Level 1 (live gameplay, SFX active) | 8 MHz STE | **17.5–20.0 fps** | 2.50–2.86 | 0.70–0.80× |
| Level 1 (live gameplay) | 16 MHz STE/MSTE | **43.0 fps** | 1.16 | **2.46×** |
| Level 1 (live gameplay) | 32 MHz | **50.0 fps** | 1.00 | **2.86×** |

**Why fast machines zip along at 2–3× speed:**
The main loop runs **1 simulation tick per rendered frame** and then waits for a **single** VBL (`sub_0126dc`: `tst.w $26962.l; beq.b $126dc`, cleared by `sub_012702` right after flipping `$ffff8200.l`). There is no fixed-rate frame pacer or VBL-delta accumulator:
- At 8 MHz, a frame takes ~1.85–2.6 VBLs → **17.5–25 fps** (slowdowns whenever SFX or water/enemies get busy).
- At 16 MHz, a frame fits in ~1.16 VBLs → **43 fps** (2.5× game speed!).
- At 32 MHz, a frame fits in 1.00 VBL → **50 fps** (2.9× game speed!).

## 3. Where the Frame Budget Goes (8 MHz STE Cycle Profile)

Profiled with Hatari (`h.profile(vbls=200..250)`), 8 MHz STE, Level 1:

| Routine (RAM addr) | Standing (25 fps) | Live w/ SFX (20 fps) | What it does |
|---|---:|---:|---|
| **`$0136b0–$013986`** | **51.8%** (~150k cyc/f) | **43.6%** (~149k cyc/f) | **Full-screen 20×12 tilemap redraw** from scratch every frame via CPU `move.l (a0)+,(a5)+` (30,720 B/frame, 16px coarse-X, 1px fine-Y) |
| **`$01e248–$01e32a`** | **11.4%** (~33k cyc/f) | **12.8%** (~44k cyc/f) | **32×32 masked sprite renderer** using CPU `ror.l d0, d3..d7` shift-on-the-fly + `and`/`or`/`movem.w` |
| **`$01acae–$01ad00`** | **5.2%** (~15k cyc/f) | **12.7%** (~43k cyc/f) | **MFP Timer A YM2149 digi-SFX IRQ** (`movep.l d1, -$720f(a0)` — also hits Falcon-illegal YM mirror `$ff8804/06`!) |
| **`$0126dc–$0126e4`** | **6.3%** (~18k cyc/f) | **10.7%** (~37k cyc/f) | **Idle VBL wait loop** (wasted waiting for VBL #2 or #3 after missing the prior VBL) |
| **`$01c1a0–$01c624`** | **6.1%** (~18k cyc/f) | **5.1%** (~17k cyc/f) | 128-slot entity update loop (`$654ca`) & jump table |
| **`$013988–$013be4`** | **3.3%** (~10k cyc/f) | **2.7%** (~9k cyc/f) | **Water overlay renderer** (ORs 1-bitplane `W_BLOCKS` into planes 2–3; grows much heavier when heavily flooded) |
| **`$01d6ae–$01dad6`** | **3.7%** (~11k cyc/f) | **2.2%** (~8k cyc/f) | Tile bounding-box collision checks |
| **`$013cce–$013d88`** | **3.4%** (~10k cyc/f) | **2.8%** (~10k cyc/f) | Water/flood simulation |
| **`$012656–$0126ae`** | **0.3%** (~1k cyc/f) | **0.3%** (~1k cyc/f) | VBL IRQ + music tick (`$01b4fa`: 0.04%) |
| Everything else | ~8.5% | ~7.1% | HUD, 16×16 sprites, misc logic |

**Root cause of slowdowns:**
Even with a nearly empty Level 1 screen, active CPU work is ~280,000 cycles/frame (1.75 VBLs). The moment Timer A YM digi-SFX fires (~43,000 cycles/frame = 12.7% CPU), active work crosses **320,512 cycles (2.0 VBLs)** and drops straight to **3 VBLs (16.7–20.0 fps)**.

## 4. Hardware Scan (`tools/hwscan.py` on `FLO.PRG`)

- **Blitter (`$ff8a00`):** **Not used at all (0 accesses).**
- **STE fine scroll (`$ff820d/$ff820f/$ff8265`):** **Not used at all (0 accesses).**
- **STE DMA audio (`$ff8900`):** **Not used at all (0 accesses).**
- **Critical finding:** `$01acd4` (`$1875e` in PRG): `movep.l d1, -$720f(a0)` writes YM mirror `$ff8804/06` — **bus error on Falcon** (must be fixed or replaced with STE DMA audio + safe YM fallback).
- **IKBD ACIA (`$fffffc00`):** Shared with custom IRQ at `$0127f0` — any STE blitter bursts must be kept short (non-HOG or small tile/sprite chunks) so IKBD bytes are never dropped.

## 5. STE Hardware Speedup & Timing Opportunities

1. **STE Blitter for Tilemap Redraw (`$0136b0–$013986`):**
   - Straight blitter drop-in for 240 tiles (16×16×4bpp) drops tilemap cost from ~150k cyc → ~75k cyc (**saves ~75k cyc/frame**).
   - Even better: **virtual-height / ring-buffer scrolling with STE `VBASE` + dirty-tile / save-restore** or **STE hardware fine X-scroll (`$ff8265`)** can eliminate full-screen redraws entirely, cutting tilemap cost to **~15–30k cyc/frame** (and optionally adding smooth 1-pixel horizontal scrolling!).
2. **STE Blitter for 32×32 Masked Sprites (`$01e248–$01e32a`):**
   - Replaces CPU `ror.l` barrel-shifting with STE Blitter hardware `SKEW` + `HOP/OP` mask/OR: ~44k cyc → ~12k cyc (**saves ~32k cyc/frame**).
3. **STE DMA Audio (`$ff8900`) for SFX (and optionally Amiga music):**
   - Replaces Timer A YM2149 digi-SFX IRQ (`$01acae`): **saves ~43k cyc/frame (12.7% CPU)** during SFX, eliminates Falcon YM-mirror crash, and dramatically improves audio quality.
4. **STE Blitter for Water Overlay (`$013988–$013be4`):**
   - Hardware OR of 1-plane water masks into planes 2–3 (**saves ~6–20k cyc/frame** under heavy flooding).
5. **Fixed-Speed Frame Pacing (8 MHz STE, 16 MHz Mega STE, 32 MHz TT/Falcon):**
   - Target a **rock-solid 25.0 fps (2 VBLs/frame)** (matching intended gameplay speed on 8 MHz ST/Amiga) — OR **50.0 fps rendering with 25 Hz fixed-timestep physics** (Wait: since total optimized frame work drops to ~110–145k cyc/frame < 160,256 cyc/VBL, **true 50 fps rendering** is achievable on an 8 MHz STE if we interpolate/decouple physics at 25 Hz, OR rock-solid locked 25 fps with 100% consistent speed across 8/16/32 MHz!).

## 6. Amiga ADF Audit (`alt/amiga/Flood (Bullfrog + Electronic Arts).adf`)

Custom Bullfrog trackloader directory at offset `$1600` (track 1; 1 track = 11 sectors = `$1600` = 5,632 B). Uses the **exact same Bullfrog word-tag LZ77 compression** as ST `FLOODGX`.

### Artwork Comparison

| Asset | Atari ST | Amiga ADF | Opportunity for 1 MB STE |
|---|---|---|---|
| `BLOCKA/B/C` tiles | 256 × 16×16×4bpp + 256 B attr (`$8100`) | 256 × 16×16×4bpp + 256 B attr (`$8100`) | **100% pixel-identical** (deinterleaved). |
| **Level Palettes** | **12-bit STE palettes already in `FLO.PRG` (`$012750`)**, BUT slots `pal 0/1/2` are all identical (`BLOCKA` palette only!) | 3 distinct 12-bit palettes in `RUN_PROG` (`+0xe9fc`, `+0xea3c`, `+0xea7c`) | **Easy 64-byte win:** restore Amiga's distinct `BLOCKB` and `BLOCKC` 12-bit STE palettes into `pal 1` and `pal 2`! |
| `W_BLOCKS` (water) | 2,656 B (2 anim frames × 42 tiles) | 5,376 B (**4 anim frames** × 42 tiles) | **Easy win:** 2× smoother water animation (only +2.7 KB RAM). |
| `SPR_16` | 12,800 B (80 sprites × 160 B) | 12,800 B (80 sprites × 160 B) | Same sprite count & 4bpp+mask format. |
| `SPR_32` | 65,476 B (offset table + packed rows) | 96,000 B (150 × 640 B raw 4bpp+mask) | Same 4bpp sprites (ST trims empty rows). |
| `TITLE.SC` | 320×200×4bpp (16 colours, 32,000 B) | 320×264×**5bpp (32 colours**, 52,800 B) | 5bpp exceeds ST/STE 4bpp hardware (would need 16-colour remap/raster split). |
| `BIG_PIC.` / `END_SCRE` | Not in ST `FLOODGX` (`INTRO.TOS` is 4.5 KB) | `BIG_PIC.` (100,000 B) + `END_SCRE` (124,160 B) | Amiga-only richer intro/ending artwork (check bitplane depth before porting). |

### Audio Comparison

| Component | Atari ST (`B_FLOOD.ECH`, 103 KB) | Amiga ADF (226 KB total) | Opportunity for 1 MB STE |
|---|---|---|---|
| **SFX** | 8-bit PCM played via **Timer A YM2149** (4-bit nonlinear volume, steals **12.7% CPU**) | `FLDFX.IN` (**97 KB**, 25 clean 8-bit PCM SFX) + `FLDFX.DU` (2.1 KB) | **Huge win:** play on **STE DMA Audio (`$ff8900`)** at 0% CPU! |
| **Music** | Minimal YM2149 chip music (`$01b4fa`, 0.04% CPU) | `TRACK.DA` (9.3 KB song) + `INSTR.DA` (**120 KB**, 18 PCM instruments) | **Fits in 1 MB STE RAM** (218 KB total PCM vs **576 KB free RAM**!). Needs a lightweight 4-channel software mixer to STE DMA buffer (e.g. 12.5 kHz stereo/mono, ~15–20% CPU — easily affordable once blitter frees ~50%+ CPU!). |
