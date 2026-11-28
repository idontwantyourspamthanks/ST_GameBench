# Gods (Atari ST) — Frame Budget & 1 MB STE Performance Analysis

**Target hardware analyzed:** 1 MB Atari STE, 8 MHz 68000, TOS 1.62, 50 Hz RGB, sound enabled (50066 Hz).  
**Source build:** `originals/GODS/` (PP's Gamex HD conversion, Jan 2011), cold-booted via bootable HDDRIVER ACSI image (`tools/gods.py`).  
**Measurement method:** Hatari 2.6.1 cycle-accurate CPU profiler (`profile cycles 20000`) and Shifter `$ff8203` flip counter over 200–250 VBLs in Level 1 (both standing still and active scrolling with 4 monsters on screen), cross-referenced against 68000 disassembly of the live 1 MB RAM dump (`work/ram_level1.bin`).

---

## 1. Executive Summary

- **Stock framerate:** **16.67 fps (3 VBLs/frame = 480,768 cycles/frame)**, both standing still (`16.6 fps`, 3.01 VBLs/frame) and scrolling with 4 enemies (`16.5 fps`, 3.03 VBLs/frame).
- **Why it is 16.67 fps:**
  1. **Software tilemap redraw dominates the frame:** Gods redraws the entire 320×192 playfield (`10 × 12 = 120` tiles of 32×16 px) in software **every single frame**, even when the camera is stationary. That alone burns **236,574–264,312 cycles/frame (1.48–1.65 VBLs)** — over half the entire 8 MHz CPU.
  2. **Software masked sprite blitting** computes 4-plane OR masks on-the-fly and rotates all 4 bitplanes with `rol.l` in software, taking another **72,406–94,716 cycles/frame (0.45–0.59 VBLs)**.
  3. **Total active CPU work is 2.45 VBLs (idle) to 2.69 VBLs (scrolling + 4 enemies)** — it cannot fit in 2 VBLs (25 fps = 320,512 cycles), so the game also sets a **3-VBL floor** (`$003056: move.w #$2, $35a.w`).
  4. **Zero STE hardware is used:** `hwscan.py` confirms no accesses to the STE Blitter (`$ff8a00`), STE Hardware Scrolling (`$ff820d`/`$ff820f`/`$ff8265`), or STE DMA Audio (`$ff8900`).
- **1 MB STE opportunity:**
  - **Game logic + AI + physics + audio + HUD + VBL/HBL** together cost only **~71,671 cycles/frame (0.45 VBLs)** during scrolling + combat (or ~98k with the optional PAL1 sky-gradient HBL active).
  - **Tier 1 (Blitter-only tilemap + pre-masked Blitter sprites):** Drops total work to **~230,000 cyc/fr (1.44 VBLs)** → **rock-solid 25 fps (2 VBLs)**, matching the Amiga version's framerate with minimal architectural change.
  - **Tier 2 (STE Hardware Scrolling + edge-tile Blitter + dirty-rect Blitter sprites):** Drops total work to **~117,000 cyc/fr (0.73 VBLs)** → **25 fps with >63% headroom**, or **50 fps (1 VBL = 160,256 cycles)** smooth scrolling (provided the Timer B sky-gradient HBL is kept lightweight).
  - **Memory headroom:** On a 1 MB STE, **`$084000–$0abfff` (~160 KB) is completely free**, and dropping pre-shifted tile copies under STE hardware scrolling frees another **~105–140 KB** inside lower 512 KB — **~265–300 KB total free RAM** for ring-buffer screens, pre-computed sprite masks, and optional STE DMA sound effects.

---

## 2. Measured Baseline Frame Budget (Stock 8 MHz STE)

Measured over **73 game frames** (~220–221 VBLs) in Hatari (`work/prof_idle.json` and `work/prof_scroll.json`).  
Reference budgets at 8.0128 MHz / 50 Hz PAL: **1 VBL = 160,256 cycles**, **2 VBLs = 320,512 cycles**, **3 VBLs = 480,768 cycles**.

| Subsystem | Address Range(s) | Idle (cyc/fr) | Idle (% 3-VBL) | Scroll + 4 Enemies (cyc/fr) | Scroll (% 3-VBL) | Scroll (% 1-VBL) |
|---|---|---:|---:|---:|---:|---:|
| **Tilemap / BG redraw** | `$17dda–$18cc6` | 236,574 | 48.91% | **264,312** | **54.48%** | **164.9%** |
| **Software sprite blitters** | `$17690–$17dd9`, `$19056–$198a7` | 72,406 | 14.97% | **94,716** | **19.52%** | **59.1%** |
| **Game logic, AI, physics, collision** | main loop (`$30f0–$33e4`, `$7338–$f9ff`, etc.) | 24,709 | 5.11% | **30,087** | **6.20%** | **18.8%** |
| **HUD / score / status / ticker** | `$3cc6–$3d70`, `$559c–$6130`, `$17280–$17500` | 14,181 | 2.93% | **22,998** | **4.74%** | **14.4%** |
| **Audio driver (YM2149)** | `$20000–$20fff` (called from VBL `$17272`) | 9,499 | 1.96% | **11,214** | **2.31%** | **7.0%** |
| **Timer B HBL raster** | `$5298–$559b` | 31,777 | 6.57% | **4,549** | **0.94%** | **2.8%** |
| **VBL ISR + palette reload** | `$1e8e2–$1e924`, `$171b4–$1727f` | 3,146 | 0.65% | **2,823** | **0.58%** | **1.8%** |
| **Total Active CPU Work** | | **392,292** | **81.11%** | **430,698** | **88.78%** | **268.8%** |
| **Wait-VBL spin + flip** | `$1e926–$1e946`, `$1ecaa–$1ece6` | 91,359 | 18.89% | 54,426 | 11.22% | 34.0% |
| **Total (3 VBLs/frame)** | | **483,651** | **100.0%** | **485,124** | **100.0%** | **302.7%** |

*(Note: Total cycles/frame slightly exceed 480,768 because ~1–2% of frames occasionally spill to 4 VBLs, giving 3.01–3.03 VBLs/frame.)*

---

## 3. Rendering & Sync Architecture (Disassembly Findings)

### 3.1 Frame Sync & Hard 3-VBL Cap (`$0033b0`, `$01ecaa`, `$01e8e2`)
- **Double buffers:** `$110e.w = $070200` (front) and `$110a.w = $078300` (back) — 32 KB each with vertical padding for clipping.
- **VBL ISR (`$01e8e2`):** Reloads palette if `$10b8.w != 0`, increments `$1e92e.l` (free-running VBL tick) and `$1e92c.l` (frame VBL counter), calls `$171b4` (sets up Timer B HBL, runs YM2149 audio driver `$2032c`, increments level timer `$f8c.w`).
- **Frame cap & flip (`$0033b0 → $01ecaa`):**
  ```m68k
  0033b0: move.w $35a.w, d0        ; $35a.w initialized to 2 at $003056
  0033b4: jsr    $1ecaa.l
  ...
  01ecaa: cmp.w  $1e92c(pc), d0    ; spin while vbl_count <= $35a.w
  01ecae: bge.b  $1ecaa
  ...                              ; swap $110a/$110e, write $ff8203/$ff8201
  01ecde: clr.w  $1e92c.l
  01ece6: bra.w  $1e930            ; wait for next VBL (sets $1e92c = 1)
  ```
- Because `$1e930` waits for 1 VBL after clearing `$1e92c`, `$35a.w = 2` enforces a **3-VBL (16.67 fps) floor** (`$35a.w = 1` → 2 VBLs / 25 fps; `$35a.w = 0` → 1 VBL / 50 fps).
- In our profile, `$1ecaa–$1ecae` spent only **1,460 cycles across 73 frames** (20 cycles/frame = **zero spins**): the CPU never finished early enough to hit the cap, and instead spun in `$1e930` waiting for VBL #3 to complete.
- **Debug raster bar left in shipping code:** `$00339a` writes `$35c.w` (0 = black) to `$ffff8240` before `$1ecaa` and clears it to 0 afterward — the Bitmap Brothers' own frame-time profiler!

### 3.2 Tilemap / Background Renderer (`$018036`, `$017f1a–$018cc6`)
- **Playfield:** `320 × 192` pixels (`$140 × $c0`); bottom 8 lines (`192–199`) are the green status/message ticker bar.
- **Map:** `$e30.w = $069b74`, 128 tiles wide × 64 tiles high (`8,192` bytes, 1 byte/tile; Level 1 uses 115 unique tile IDs, max ID 182).
- **Pre-shifted tiles (`$f1a.w = $045574`):** Tiles are `32 × 16` pixels (`16 bytes/row × 16 rows = 256 bytes` unshifted). For 2-pixel smooth horizontal scrolling on a plain ST, Gods stores **pre-shifted copies** at `1,408 bytes/tile` (`(id << 7) + (id << 8) + (id << 10)` at `$17fae` / `$18146`: 256 B aligned + 3×384 B shifted pairs).
- **Aligned path (`$017f1a`, when `(cam_x & $0c) == 0`):** Copies 16 bytes/row with `4× move.l (a3)+,(a2)+` + `adda.w a5,a2` + `dbra`. Even in this fast aligned path (Idle), redrawing 120 tiles takes **236,574 cycles/frame**.
- **Shifted path (`$01804c–$0189ba`):** Uses `or.l` for the overlapping left word + `move.l` for the right words, plus a clever run-length optimization (`$018478`) when adjacent horizontal tiles are identical (`cmp.b (a0), d0`). Still burns **264,312 cycles/frame** during scrolling.
- **Why it redraws every frame:** Redrawing the full tilemap doubles as sprite-background erasure on a plain ST.

### 3.3 Software Masked Sprite Blitters (`$0176d0`, `$017b7a`, `$019634`)
- **`$0176d0` (32 px wide sprites — hero, monsters):** ~1 call/frame idle, ~3 calls/frame with 4 enemies on screen. Reads 4 bitplanes (`movem.w (a0)+,d0-d3` + 4×`move.w`), shifts all 4 planes with `rol.l d7, d0..d3`, **computes the transparency mask on-the-fly** (`move.l d0,d4; or.l d1,d4; or.l d2,d4; or.l d3,d4`), splits it across 3 word columns with `and.w`/`not.w`, and writes `and.w` + `or.w` to the screen.
- **`$017b7a` (16 px wide sprites — pickups, projectiles, effects):** ~3–4 calls/frame.
- **`$019634` (hero/overlay blitter):** ~1 call/frame.
- Combined cost: **72,406 cyc/fr (idle)** to **94,716 cyc/fr (4 enemies)**, scaling linearly with on-screen enemies and projectiles.

### 3.4 Timer B HBL Raster (`$005298–$00559b`)
- Controlled by `$3da.w` (set/cleared by trigger actions `ACT[11]`/`ACT[12]` at `$1a094`/`$1a0a0`):
  - When `$3da.w != 0` (outdoor/sky-gradient areas, active at Level 1 start): fires Timer B repeatedly down the playfield to cycle `PAL1` (`$ffff8242`), then fires **every scanline for the bottom 8 lines** (`$538c–$54b2`) for the green ticker gradient → **31,777 cyc/fr (6.57%)**.
  - When `$3da.w == 0`: fires only at scanline 191 (`$bf`) for the 8-line ticker gradient → **4,549 cyc/fr (0.94%)**.

---

## 4. 1 MB STE Memory Map & Available RAM

From `work/ram_level1.bin` (1 MB STE, Level 1 active):

| Address Range | Size | Contents |
|---|---:|---|
| `$000000–$000fff` | 4 KB | Exception vectors, game globals (`$300–$fff`) |
| `$001000–$021000` | 128 KB | Gods 68000 executable, tables, YM2149 sound driver (`$20000`) |
| `$021000–$045573` | 145 KB | Level sprite graphics, palettes, audio/SFX data, buffers |
| `$045574–$06831b` | 140 KB | Pre-shifted tile set (`$f1a.w`) |
| `$06831c–$0701ff` | 32 KB | Sprite headers (`$685e4`), Level 1 map (`$69b74`), triggers (`$6e21c`), strings (`$6f99e`) |
| `$070200–$07ffff` | 64 KB | Double-buffered screen RAM (`$70200` and `$78300`) |
| **`$084000–$0abfff`** | **160 KB** | **COMPLETELY FREE (all zeros on 1 MB STE)** |
| `$0ac000–$0fffff` | 336 KB | PP Gamex loader, TOS state backup, disk/cache buffers |

**Total reclaimable RAM on 1 MB STE:**
- **160 KB immediately free** at `$084000–$0abfff`.
- **+105–140 KB reclaimable** inside `$045574–$06831b` if STE hardware scrolling eliminates the 3 pre-shifted tile copies (keeping only the 256-byte unshifted tiles: ~26–46 KB).

---

## 5. 1 MB STE Performance Opportunities

### Option A — Tier 1: STE Blitter Tilemap + Pre-Masked Blitter Sprites (**25 fps, Low Risk**)
Keep the existing double-buffered screen layout (`$70200`/`$78300`) and camera logic untouched, and accelerate the two biggest bottlenecks with the STE Blitter (`$ff8a00`):

1. **Blitter Tilemap Redraw:**
   - Copy 32×16 tiles using the Blitter with `SKEW` (for arbitrary 0–15 px horizontal scroll!) — eliminating pre-shifted tile copies entirely.
   - 320×192 × 4 planes = 30,720 bytes = 15,360 words. At ~8 cycles/word (Blitter read+write in HOG/burst mode) + ~120 tile setups (~150 cyc each): **~141,000 cycles/frame** (down from 264,312 — saving **~123,000 cyc/fr**).
   - *Even better:* When `cam_x`/`cam_y` haven't moved (or moved only a few pixels), only redraw tiles dirty under sprites? Even without dirty-rect, full Blitter redraw fits easily in 2 VBLs!
2. **Pre-Masked Blitter Sprites:**
   - Pre-compute 1-plane inverted masks for all level sprites at level-load time into the 160 KB free RAM (`$084000–$0abfff`, masks take only ~1/4 of sprite size ≈ 25–35 KB).
   - Replace `$176d0` / `$17b7a` / `$19634` with 2-pass Blitter (4-plane AND with 1-plane mask + 4-plane OR with sprite data, using hardware `SKEW` & `ENDMASK`).
   - Cuts sprite blitting from **94,716 cyc/fr** to **~28,000–35,000 cyc/fr** (saving **~60,000 cyc/fr**).
3. **Projected Tier 1 Total (Scroll + 4 Enemies):**
   - `141,000` (Blitter tiles) + `32,000` (Blitter sprites) + `71,671` (logic + AI + HUD + audio + VBL/HBL) = **~245,000 cyc/fr (1.53 VBLs)**.
   - Even with the 31.8k Timer B sky gradient active: **~272,000 cyc/fr (1.70 VBLs)**.
   - **Result:** Rock-solid **25 fps (2 VBLs = 320,512 cycles)** with ~50,000–75,000 cycles of combat headroom!

### Option B — Tier 2: STE Hardware Scrolling + Blitter Edge-Tiles & Dirty-Rect Sprites (**25 fps Effortless / 50 fps Achievable**)
Use the STE Shifter's hardware scrolling (`$ff8201/$ff8203/$ff820d` base address, `$ff820f` line width, `$ff8265` pixel fine scroll) with two slightly wider ring-buffer playfields (e.g., `352 × 224` ≈ 39.4 KB × 2 = 79 KB, fitting in `$084000–$0abfff`):

1. **Background updates drop by >95%:**
   - Standing still: **0 tiles** redrawn (**0 cycles**).
   - Scrolling horizontally/vertically: blit only the newly revealed **1 column (12 tiles)** or **1 row (10 tiles)** with the Blitter (~12 tiles × 128 words × 8 cyc ≈ **~12,000 cycles/frame**).
   - Down from **264,312 cyc/fr** → saving **~252,000 cycles/frame (1.57 VBLs)**!
2. **Sprite background save/restore + Blitter draw:**
   - Save background rectangles under active sprites to a scratch buffer before drawing, restore them next frame with Blitter (fast unmasked copy), then draw sprites with pre-masked Blitter.
   - Estimated cost for 8–10 sprites: **~35,000–45,000 cycles/frame** (down from 94,716).
3. **Projected Tier 2 Total (Scroll + 4 Enemies):**
   - `12,000` (edge tiles) + `40,000` (Blitter sprites + save/restore) + `71,671` (logic + AI + HUD + audio + VBL/HBL) = **~123,671 cyc/fr (0.77 VBLs)**.
   - **Result:**
     - At **25 fps (2 VBLs)**: Uses only **39%** of the CPU — huge headroom for heavy boss/combat scenes and **STE DMA Audio**.
     - At **50 fps (1 VBL = 160,256 cycles)**: Fits in **0.77 VBLs** when Timer B sky gradient is off (~36k cycles spare), and **0.94 VBLs** (~151k cycles) with the sky gradient on. Optimizing the Timer B handler (using `usp`/register-pinned pointer instead of pushing/popping `a0`/`d0` and absolute long memory ops on every scanline) would reclaim another ~10–15k cycles, making **50 fps** viable in most scenes.
   - *Note on bottom ticker bar:* The 8-line green status ticker at scanlines 192–199 does not scroll horizontally with the playfield. Under STE hardware scrolling, Timer B at scanline 191 (`$bf`) can reset `$ff8265 = 0` and `$ff820f = 0` (and optionally switch `$ff8205/$07/$09` video counter to a dedicated static ticker buffer) — a classic, rock-solid STE split-screen technique.

### Option C — Timestep & Audio Considerations on 1 MB STE
1. **Simulation speed vs. framerate:** Gods' main loop (`$0030f0–$0033e4`) steps physics, movement, animation, and AI **once per rendered frame**.
   - Changing `$35a.w` from `2` (3 VBLs = 16.67 fps) to `1` (2 VBLs = 25 fps) speeds up gameplay by **1.5×** — which is actually closer to the Amiga version's 25 fps feel, though some players may prefer preserving the ST's original 16.67 Hz timing (achievable via fixed-timestep / visual interpolation if targeting 50 fps).
2. **STE DMA Audio (`$ff8900`):** The stock YM2149 driver costs only ~11k cycles/frame. With 160–265 KB of free RAM on a 1 MB STE, adding 12.5 kHz STE DMA sampled SFX (weapons, impacts, voices from the Amiga version) is very feasible with near-zero CPU overhead.
3. **Important fix for the Gamex base build:** As documented in `ADAPTIVE_AI_ANALYSIS.md`, this Gamex build (`originals/GODS/`) has **4 unpatched Rob Northen Copylock traps (`$873b4953`)** still live in RAM (`$00fec8`, `$00d864`, `$010ffe`, `$00b4ee`), which break Power Potions, nerf weapon damage, give the Guardian boss ~121M HP, and overwrite all monster AI to max-speed pure-chase. Any STE enhancement patch should fix those 4 longwords first.

---

## 6. Measured Tier 2 Implementation Results (1 MB 8 MHz STE)

Implemented in `patches/stage2.s`, `patches/ste_sprites.s`, and `patches/ste_scroll.s` (built via `tools/godspatch.py` into `build/game/`):

- **4 Rob Northen Copylock traps neutralized** on all machines (`$00fec8 = 0`, `$00d864 = 0`, `$010ffe = 0`, `$00b4ee = $05dc`).
- **STE Tier 2 engine active on STE / Mega STE** (auto-detected via bus-error-safe `$ff8a3c`/`$ff8265` probe; plain ST falls back cleanly to stock rendering while keeping the Copylock fixes):
  - Double-buffered `352 × 224` (`176 B/line`) corkscrew hardware-scroll playfields at `$086000–$0999ff` (`$ff8201/$03/$0d` HI→MID→LO + `$ff820f` LINEWID + `$ff8265` HSCROLL).
  - Unified 143-tile diff against per-buffer `128 × 64` drawn-tile caches (`$09a000–$09dfff`) — 1 single 4-plane Blitter call per newly revealed or mutated tile.
  - Lazy 1-plane mask cache (`$0a4000–$0abfff`) + HOG per-plane Blitter sprites (`$176d0`, `$17b7a`, `$19634`) + LIFO dirty-rect background save/restore (`$09e000–$0a3fff`).
  - HUD corners (lives, 24 px energy potion jar, score box) copied with hardware `SKEW = fine_x`; Timer B scanline 191 (`$00538c`) switches the Shifter back to the static 8-line green ticker bar.

| Metric (1 MB 8 MHz STE, TOS 1.62, 50 Hz, sound ON) | Stock ST/STE | Tier 2 STE (25 fps cap) | Tier 2 STE (uncapped) |
|---|---:|---:|---:|
| **Idle FPS** | 16.6 fps (3.01 VBLs) | **25.0 fps (2.00 VBLs locked)** | 35.5 fps (1.41 VBLs) |
| **Scrolling + 4 Enemies FPS** | 16.5 fps (3.03 VBLs) | **25.0 fps (2.00 VBLs locked)** | **47.0 fps (1.06 VBLs)** |
| **Active CPU Work / Frame (Scroll + Combat)** | 430,698 cyc (2.69 VBLs) | **~173,216 cyc (1.08 VBLs)** | ~170,000 cyc (1.06 VBLs) |
| **Wait-VBL Headroom (Scroll + Combat)** | 11.2% (of 3 VBLs) | **45.9% (of 2 VBLs)** | 6% (of 1 VBL) |

*Note on 60 Hz:* Because active work is ~173k cycles/frame (well under 2 NTSC VBLs = 267k cycles), 2-VBL locked mode has ~94k cycles of headroom even at 60 Hz (30 fps), while 50 Hz PAL gives an authentic Amiga-matched **locked 25.0 fps** with 46% CPU spare.

