# Player Manager (Atari ST) — Performance & Match Engine Reference

Measured on **Hatari 8 MHz 68000 STE, 1 MB RAM, TOS 1.62, RGB 50 Hz** (unless noted otherwise).

---

## 1. New Game Setup Performance (Task 0 & Task 1)

| Build | Teams / Players | Virtual Time (8 MHz STE) | Speedup |
|---|---:|---:|---:|
| Unpatched `originals/PLAYERME` | 44 teams / ~920 players | ~460 s (7m 40s) | 1.0× |
| Patched `micro_opt.s` (bit-exact + Option A) | 44 teams / ~920 players | ~109 s (1m 49s) | 4.2× |
| Patched `micro_opt.s` + `league92.s` | 92 teams / 1,918 players | ~253 s (4m 13s) | 1.8× faster than original despite 2.1× more clubs/players |

---

## 2. Match Engine Performance (Task 2 — Kick Off 2 Overlay)

### Root Cause of "Laggy" Feel (Fixed)
In `patches/ko2_bridge.s`, `-$34c4(a4)` was mistakenly set to `1` (assuming it was an Aftertouch toggle). In Kick Off 2, `-$34c4(a4)` is actually **Game Speed / extra VBL delay** (`$0134b4` computes `-$4ed6(a4) = (1 << speed) >> 1`, and the main loop at `$01b4bc` waits `-$4ed6(a4)` *additional* VBLs after every rendered frame).
- `-$34c4 = 0` (`-$4ed6 = 0`): **50.00 FPS** (standalone Kick Off 2 default; Aftertouch is always active in KO2's physics).
- `-$34c4 = 1` (`-$4ed6 = 1`): **25.00 FPS cap** (waits 2 VBLs per frame -> halves framerate and doubles input latency).

### Measured Match Engine Metrics (1 MB 8 MHz STE, 50 Hz PAL)

| Configuration | Speed Delay (`-$4ed6`) | Measured Active FPS | VBLs / Frame | VBL Idle Headroom (`$1b4b2..$1b4b6`) | Timer B Stripes (`$120.w`) |
|---|---:|---:|---:|---:|---|
| Standalone Kick Off 2 (`originals/KICKOFF2`) | `0` | 50.00 FPS (cap) | 1.00 | — | `$018e36` (`$0060`/`$0050`, 48 lines) |
| Patched PM + KO2 (before fix, `-$34c4 = 1`) | `1` | **24.90 FPS** (122 frames / 245 VBLs) | 2.01 | — | `$018e36` (`$0060`/`$0050`, 48 lines) |
| Patched PM + KO2 (after fix, `-$34c4 = 0`) | `0` | **50.00 FPS** (1,803 frames / 1,803 VBLs) | 1.00 | **~42.5% idle** (active play, ~57.5% CPU used) | `$018e36` (`$0060`/`$0050`, 48 lines) |

> **Headroom note for future Amiga tiled pitch port:** At 50 FPS on an 8 MHz 68000 STE, Kick Off 2 currently uses ~57.5% of a 20 ms VBL (~42.5% idle headroom, ~92,000 cycles/frame free during light play; ~18% idle when many players are simultaneously on screen). On STE, the hardware Blitter + horizontal fine-scroll registers can offload a tiled pitch background with minimal CPU cost if we keep sprite overdraw disciplined.

---

## 3. Horizontal Grass Stripes Verification (Timer B HBL Raster)

Both unpatched Player Manager (`$01b5c2..$01b63c`) and Kick Off 2 (`$018d06..$018e66`) use the exact same Atari ST Timer B raster technique:
- VBL queue (`$456.w`) calls `$018d06`, which reads vertical camera position `camY` (`$2739c.l`), computes `(camY + 200) % 96`, sets top stripe colour `$27186.l` to `$0060` (bright green) or `$0050` (medium green), and loads Timer B data register `$fffa21` with `tb_init = 48 - (phase % 48)` scanlines.
- Timer B ISR (`$120.w = $018e36`) toggles `$ff8240` via `eori.w #$30, $27186.l` (`$0060 <-> $0050`) every 48 scanlines.

Verified on 1 MB STE (`build/game`):
- `VBL queue`: `['0xdfb16', '0x18d06', ...]`
- `Timer B ($120.w)`: `0x018e36`
- Active vertical scroll check:
  - Frame 1 (`t2_scroll_1.png`): `camY = 596`, `tb_init = 20`
  - Frame 2 (`t2_scroll_2.png`): `camY = 580`, `tb_init = 36` (exact 16-scanline shift matching the 16 px vertical camera movement)
  - Top goal (`t2_stripe_A.png`): `camY = -17`, `tb_init = 9`

---

## 4. v1.1 Atari STE Amiga Visuals & Audio Performance (`KO2STE.BIN`)

Measured on **Hatari 8 MHz 68000 STE, 1 MB RAM, TOS 1.62, RGB 50 Hz PAL** (`build/game`, active Watch-mode match).

### Hardware Architecture (100% Inside 1 MB STE RAM)
- **Auto-Detection (`BR_IS_STE` at `$0b5978`):** Bus-Error-safe probe of `$ff8901` (STE DMA Sound) and `$ff8a3c` (STE Blitter). Plain 1 MB ST (`machine="st"`, TOS 1.04) detects `BR_IS_STE = 0` and runs 100% Classic ST mode (Timer B grass stripes + YM audio) with zero bus errors.
- **STE DMA Audio (`AMIGASND.BIN`, 22,376 B):** 17 Amiga 8-bit signed PCM samples extracted from Kick Off 2 Final Whistle (`sounds`) and resampled to exact 6,258 Hz mono STE DMA (`$ff8900..$ff8924`). Zero Timer-A CPU interrupt overhead!
- **STE Blitter Tiled Pitch (`AMIGAP0..3.BIN`, 32,288 B each):** All 4 Amiga pitches (`normal`, `wet`, `soggy`, `artificial`) converted to STE 12-bit RGB palettes (`$ff8240..$ff824e`, colours `0..7`), 0-based `80×96` tilemaps, and 256 ST-interleaved 3bpp `16×16` tiles. Rendered via STE Hardware Corkscrew scrolling (`$ff8201/$03/$0d`, `$ff820f`, `$ff8265`) into a 71.2 KB ring buffer (`$088f00..$09afff`, stride 168 bytes).
- **Dual-Playfield 16-Colour Split:** Pitch tiles use colours `0..7` (Plane 3 = `0`); sprites and HUD/Radar set Plane 3 = `1` to use KO2's own sprite palette (`8..15`), preserving non-clashing club kits with zero colour clashes.
- **Live View Toggle (`V` key):** Press `V` in-match on STE to swap instantaneously between Amiga STE and Classic ST views.

### Measured v1.1 Performance & Optimisation Progression (1 MB 8 MHz STE)

| Configuration | Active FPS | VBLs / Frame | Notes |
|---|---:|---:|---|
| v1.0 Classic ST (`V` toggle on STE) | **50.00 FPS** | **1.000** | 38.0% VBL idle headroom, Timer B stripes + YM audio |
| v1.1 Amiga STE (pitch + sprites + DMA, no HUD) | **50.00 FPS** | **1.000** | **56.0% VBL idle headroom** (+18% faster than Classic ST!) |
| v1.1 Amiga STE + 68000 sparse HUD/Radar (initial) | 26.68 FPS | 1.874 | Software 4-plane shifts (~420 cyc/word) exceeded 1 VBL |
| v1.1 Amiga STE + Blitter 88-line masked Radar + full HUD | 25.31 FPS | 1.975 | 11 Blitter passes on 88×4w Radar + 14×20w HUD (~80% VBL) |
| v1.1 Amiga STE + Opaque 88-line Radar + tight 3-box HUD | 30.67 FPS | 1.630 | Cut HUD to 3 tight boxes (Name/Score/Clock) + opaque Radar |
| v1.1 + Direct `NFSR` single-`TRAP #8` sprites | 42.77 FPS | 1.169 | Eliminated `P0/P1/P2` scratch copies; `XCOUNT=1` when `skew=0` |
| v1.1 + Batched tile rows/cols + 44-line Compact Mini-Radar + 1-call Plane-3 clear | **49.75–49.88 FPS** | **1.002–1.005** | **398–400 frames / 400–401 VBLs** — locked 50 Hz feel with full Radar, Name, Score, Clock & Event Banners! |

### 1 MB STE Live Match RAM Map (`$07fd00..$0b2ff8`)
- `$07fd00..$0800ff`: 1bpp Blitter HUD mask scratch (1 KB)
- `$080100..$080ec0`: Compact Mini-Radar save-under (3.5 KB)
- `$081000..$088e1f`: Active Amiga pitch (`AMIGAP0..3.BIN`: 32 B STE palette + 7,680 B map + 24,576 B 3bpp tiles)
- `$088f00..$09afff`: STE Corkscrew ring buffer (`424 × 168` = 71.2 KB + slack)
- `$09b000..$09cfff`: Blitter 4bpp sprite save-under slots (`32 × 256 B` = 8 KB)
- `$09d000..$0ae93f`: `KO2_FILES_CR` (72 KB)
- `$0ae940..$0affff`: `KO2STE.BIN` (5,786 B / 5,824 B slot)
- `$0b0000..$0b20ef`: KO2 `$010a2e` static buffer (8.4 KB)
- `$0b20f0..$0b2f5f`: Bottom HUD & Center Event Banner save-under (3.7 KB, cleanly below `PMOK` at `$0b2ff8`)

## v1.1 Atari STE 50 Hz Lossless AVI Verification (2026-11-26)
Verified via Hatari `--avirecord --avi-vcodec png --avi-fps 50` (120 consecutive 50 Hz frames per test, extracted via `ffmpeg` and audited frame-to-frame):
- **Key fixes in `KO2STE.BIN` (6,566 bytes <= 6,592 limit):**
  - Replaced 68000 Blitter Bottom HUD (~22k cycles/frame) with **0-cycle STE Hardware Split-Screen** (Timer B ISR at scanline 181 -> `$07f1c0`, second Timer B at +18 scanlines for jet-black bottom border).
  - Replaced 68000 per-pixel vector Radar (~90k cycles/frame) with **Batched STE Blitter `ENDMASK` Transparent Vector Radar** (`cmd 7` + batched `cmd 6`, pre-scaled line cache, `Y_STEP=4` vertical lines, `2×1` dots, skipping KO2's redundant `$01fae8` hidden radar drawer).
  - Added **KO2-style narrow STE hardware raster-beam avoidance** (`[-28 .. +18]` scanlines via `$ff8205/$07/$09`) to `ste_skip_beam_1`/`2`, eliminating player flicker & mid-blit tearing.
  - Moved 1bpp sprite mask generation into the STE Blitter inside `cmd 3`, precomputed 2D overlap bounds (`±20` vertical tolerance) in `ste_erase_spr_amiga`, expanded `STE_LIFT_PTRS` to 32 entries, and added Corkscrew Primary/Mirror wrap sprite transfer (`ste_cork_wrap_spr`).
- **Measured Results (1 MB 8 MHz Atari STE, TOS 1.62):**
  - Default Radar (`scale=16`): **47.22–49.81 FPS (`1.004–1.059 VBL/frame`)**, **0/119** radar drops, **0/119** player drops, **0/119** HUD drops.
  - Large Radar (`scale=8`): **49.80 FPS (`1.004 VBL/frame`)**, **0/119** radar drops (pixel-identical every frame), **0/119** player drops, **0/119** HUD drops.
  - Live `V`-key toggle: Classic ST **49.71 FPS** <-> Amiga STE **50.29 FPS**, `PMOK @ $b2ff8 = $504d4f4b` intact.

---

## 5. v1.1 Final 2 MB+ STE Triple-Buffered 50/60 Hz Engine & Lessons Learned (2026-11-28)

### Final Architecture (`KO2STE.BIN`, 7,572 B, 2 MB Minimum RAM)
Moving to a **2 MB minimum** unlocked a clean 616 KB STE match arena (`$0d0000..$169fff`, >250 KB below 2 MB `HDDRIVER`) with **zero flicker, zero tearing, zero judder**, and enough headroom to sneak beneath the **60 Hz NTSC (`133,604` cyc/VBL)** ceiling:
- **Triple-Buffered 448-Line Linear Rings (`DB_A`/`DB_B`/`DB_C`, `$0d0000..$1077ff`):** Lockstep `ste_vbl_end` VBlank latching (`STE_DISP_IDX` scanned out, `STE_PEND_IDX` queued in `$ff8201/$03/$0d` with `STE_PEND_HSCR` applied after VSync, `STE_SHOW_IDX` newest completed) eliminates single-buffer raster chasing and 1 MB ring-seam splits completely.
- **Single Supervisor Render Bracket (`ste_pu_sup` on isolated 4 KB stack `$10e000`):** One `TRAP #8` per frame with `IPL=0` preserved (VBL/Timer C/IKBD fire freely), eliminating all mid-frame exception round-trips.
- **$O(1)$ Sprite Slot Indexing + Inactive Fast-Skip:** `(a3)` stores `slot_idx + 1` (`1..32`); `ste_erase_spr` exits in 28 cycles on `tst.l (a3) == 0` before saving registers.
- **160 KB 640-Sprite Pre-Trimmed / Pre-Masked / X-Trimmed Cache (`$136800..$15e7ff`):** Precomputes `y_skip`, `trimmed_h`, plane-activity flags, and `max_1col_skew` (trailing zero bits of combined mask) so skewed sprites that fit in 16 pixels blit/save/restore as `4w` (`XCOUNT=1`) instead of `8w` (`XCOUNT=2`).
- **Direct Supervisor 1-Plane `NFSR` Transparent Bottom HUD (`$168000`/`$169000` 4 KB save pools):** Runs directly inside `ste_pu_sup`, `AND`s only 3 planes (`P0..P2`), and skips zero `P2_HOME`/`P1_AWAY` planes on `OR`.
- **160 KB 5-Scale Split Radar (`$10e800..$1367ff`) + `STE_DOT_XLUT` (`$166000`) + `ste_rad_div`:** Pass 1 draws solid `$ffff` horizontal radar words via 2-byte deltas (zero RMW); Pass 2 draws masked words; 23 dots plot with zero shifts via a 336×16 B LUT; scales 16/8 use `lsr.w #4`/`#3`; radar is cleanly hidden during walk-out (`STE_WALKOUT`) until centre-circle arrival.
- **44-Cycle Direct `Iorec(1)` Check (`ste_fast_cconis` at `$02024a`):** Checks `ibufhd == ibuftl` directly in User mode, bypassing `TRAP #1` $\to$ GEMDOS $\to$ BIOS on 99.9% of frames.
- **Auto-50 Hz PAL Match Switch + Live `H` 60 Hz Toggle:** Auto-switches colour systems to 50 Hz PAL on match entry, allows live `H` toggle between 50 Hz PAL and 60 Hz NTSC Turbo with HUD banner, and restores pre-match `$448.w`/`$ff820a.w` on match exit.

### Measured 200-VBL Hardware Cycle Profiles (Cold-Boot `.vhd`, 8 MHz 2 MB STE, TOS 1.62)

| Scenario | VBL Budget | Active (CPU + Blitter HOG) | Free Headroom | Measured FPS |
|---|---:|---:|---:|---:|
| 50 Hz PAL — Steady Open Play | `160,256` cyc/VBL | **`107,735` cyc/VBL** (`67.2%`) | **`+52,521`** (`32.8%`) | **`50.0 fps`** |
| 50 Hz PAL — Heavy 22-AI Fast-Break Scroll | `160,256` cyc/VBL | **`152,884` cyc/VBL** (`95.4%`) | **`+7,372`** (`4.6%`) | **`48.6–50.0 fps`** |
| 60 Hz Turbo (`H`) — Steady Open Play | `133,604` cyc/VBL | **`107,456` cyc/VBL** (`80.4%`) | **`+26,148`** (`19.6%`) | **`60.00 fps`** (`266/266` VBLs) |
| 60 Hz Turbo (`H`) — Heavy 22-AI Fast-Break Scroll | `133,604` cyc/VBL | **`128,873` cyc/VBL** (`96.5%`) | **`+4,731`** (`3.5%`) | **`49.6–55.7 fps`** |

### Key Engineering Lessons Learned
1. **Triple-buffering beats raster-chasing every time:** Single-buffer beam avoidance is inherently fragile under variable load and real hardware/MiSTerFPGA timing. Three linear rings with lockstep VBlank `VBASE` + `HSCROLL`/`LINEWID` latching eliminate flicker/tearing structurally.
2. **Isolate Supervisor render stacks from tight game stacks:** KO2's `USP` (`$028292`) and `ISP` (`$028250`) sit only 66 bytes apart. Running a whole frame render + nested VBL/Timer C IRQs on a dedicated 4 KB stack (`$10e000`) prevents silent stack corruption.
3. **Measure Blitter bus traffic, not just blit count:** Pre-interleaving the HUD into 4bpp (`3` blits) actually *increased* bus cycles (`24` RMW ops/col-row across all 4 planes) compared to direct 1-plane `NFSR` (`15` RMW ops/col-row skipping empty planes, where `NFSR` reads `N-1` source words per scanline — fewer than `SKEW=0`). Always profile after every optimisation.
4. **Never assume unused struct padding in a closed binary:** Writing a slot index to `4(a3)` clobbered KO2's live player struct (`$bc(a5)`). Encoding `slot_idx + 1` inside `(a3)` itself preserved KO2's `tst.l (a3)` contract with zero extra bytes.
5. **Fast-exit hooks that the engine calls unconditionally:** KO2 calls `$01a83e` (`ste_erase_spr`) on all ~35 entities every frame relying on its first `tst.l (a3); beq` to skip inactive ones. Checking `tst.l (a3)` *before* `movem.l` saved ~4,000 cycles/VBL in two instructions.
6. **Verify with real moving-camera gameplay, not stationary screens:** A single leftover human controller pointer (`$b4(a5)`) can stall a goal kick and produce misleadingly low cycle profiles. Always inspect screenshots alongside profiler output.
