# Moonshine Racers: rendering, frame time and speed-up study (read-only, nothing patched)

Game: Moonshine Racers (Millennium 1991), PP's HAGA HD conversion (`RUNME.TOS` + `HAGA` + `FILES/MS1 MS2 MSR_S1.FIC`).
Machine for all numbers unless stated: Hatari 2.6.1, STE, TOS 1.62, 1 MB, 8.02 MHz, 50 Hz (`tools/stharness.py`, game copied to scratch drive C:).
Every claim cites a disassembly line (address + text, from `tools/m68dis.py` on a RAM dump in `work/dumps/`) or a raw output kept in `work/notes/`.
Anything not proven is marked **[INFERENCE]**.

## 0. Findings in one page

1. **CPU-bound and sync-capped.** The race runs at 8.3 fps driving (6.00 VBL/frame) and 9.9 fps standing (5.06 VBL/frame) at 8 MHz. At 16 MHz **and** 32 MHz both scenes give exactly 16.67 fps (3.00 VBL/frame): the frame sync has a hard 3-VBL floor (`cmpi.b #$2,$611a` then a wait for one more VBL after the flip), so a faster CPU (or any CPU optimisation) can never beat 16.7 fps until the sync is changed. Mega STE (HAGA sets 16 MHz + cache) already sits at 14.4 fps standing.
2. **Game speed is frame-coupled.** World position `$5ff8` advances by the speed word once per loop (`add.w d0,$5ff8.w`): 82.4 units/s at 8 MHz, 167.0 at 16 MHz, 166.7 at 32 MHz. A pure speed-up makes the game faster, not smoother, unless timing is decoupled (user decision, Q2).
3. **Flat profile, nothing dominates.** Per frame (8 MHz, grid / driving): object sprites 27 % / 24 %, road span draw 22 % / 20 %, road geometry 12 % / 10 %, 12 cloud sprites 10 % / 8 %, HUD gauges + minimap 14 % / 16 %, horizon strip copy 5.5 % / 4 %, idle wait for VBL 5 % / 12 %, interrupts + YM sound ~5 %.
4. **The game redraws almost everything almost unchanged.** Between two presented frames only ~90 bytes of 32,000 change while standing (0.3 %) and ~2.2 KB while driving (7 %), yet every frame repaints the whole road (rows 120-199) and the horizon strip, and walks 12 clouds and the minimap (`work/notes/frame_diff.txt`).
5. **No STE hardware is used and the blitter will not help.** No blitter, DMA sound, STE palette bits, hardware scroll or enhanced joystick access anywhere in the executed code. The kernels are 68000 `movem`/and/or loops; blitter bus cost per word equals the 68000's (`midwinter2/work/notes/blitter.md`: 4.40 vs 4.33 cycles/word), so no gain at 8 MHz. Hardware fine scroll could replace the horizon copy (optional, visible, STE-only).

## 1. Boot and navigation (harness: `tools/msr.py`)

```python
import sys; sys.path.insert(0, '<gamebench>/tools'); sys.path.insert(0, '<game>/tools')
from msr import Moonshine
h = Moonshine()                 # cold boot, STE TOS 1.62, 1 MB, autoruns C:\RUNME.TOS (drive = originals/MOONSHR copy)
h.boot_to_race()                # -> True when $1021 == 2 and $100e > 40 (race loop running); ~VBL 5900, ~2 min wall
h.drive(True)                   # w $6105 $01 = joystick port 1 'up' (accelerate); h.drive(False) releases
h.savemem('work/snapshots/x.sav'); h.close()
h = Moonshine(snapshot='work/snapshots/x.sav')       # restore (retargets the scratch path inside the memstate)
```
CLI tests: `python3 tools/msr_boot_test.py --machine megaste --mem 4096 [--snap f.sav] [--shots prefix]`.

Recipe (VBL counts at 8 MHz; `work/notes/boot_*.log`):
- VBL 300-900: PP's HW-detect screen ("Machine: STE / TOS ver / Exit to Desktop: * on NumPad / Save gamestate: / on NumPad").
- VBL ~1000-2500: cover picture (`LMR273.HST`/`FMR273.HST`, STE hi-colour slideshow, times out by itself).
- VBL ~2700-5000: sunrise intro animation.
- then each **SPACE** (scancode 57) advances one screen: "Welcome partners... PRESS A KEY" -> title + "Hi, I'm Ike. Watchin..." -> map "Cactus Creek!" -> **the first race**, a standing start (HUD timer running, car does not move until the joystick is pushed).
- `boot_to_race()` presses SPACE every 4 s after VBL 5000 and polls `$1021` (mode byte, 2 in the race) and `$100e` (loop counter).

```
STE TOS 1.62 1 MB:      t=116s vbl=5800 $1021/$100e=(2, 62)   RESULT in_race = True vbl 5905
Mega STE TOS 2.06 4 MB: t=102s vbl=5928 $1021/$100e=(2, 84)   RESULT in_race = True vbl 6049   (work/notes/boot_megaste_4096.log)
Mega STE TOS 2.06 1 MB: RESULT in_race = True vbl 6047                                        (work/notes/boot_megaste_1024.log)
STE TOS 1.62 4 MB:      t=114s vbl=5709 $1021/$100e=(2, 62)   RESULT in_race = True vbl 5809  (work/notes/boot_ste_4096.log)
```
Screenshots: `work/shots/boot_{ste,megaste}_{1024,4096}.png`, `race_grid.png`, `race_start.png`, `race_drive.png`, `work/shots/film_sheet.png`.

**Input.** The IKBD handler `$cfb4` stores joystick packets at `$6104` (port 0, packet `$fe`) and `$6105` (port 1, packet `$ff`):
```
00cfd6:  0c0000f7  cmpi.b #$f7, d0      00cfdc: cmpi.b #$fe, d0 / beq $d028 (-> move.b d0,$6102)
00d030:  13c000006103  move.b d0, $6103.l   00d046: move.b d0, $6105.l ; clr.b $6103.l
```
Bits: 0 up, 1 down, 2 left, 3 right, 7 fire (observed: `m $6104` after holding Up+Right-Ctrl = `00 81`). A debugger write `w $6105 $01` is a deterministic, replayable input (snapshots keep it). Host keys work with `extra=['--joy1','keys']` (`hatari-option --joy1 keys` at run time) via `h._xdo('keydown','--window',h.win,'Up')`. The game also sets the IKBD to **absolute mouse mode, 320x200** (`$d148` sends `moveq #$9,d0` ... `move.w #$140,d1 / #$c8,d2` at `$6ff0`) and reports joystick events (`$d140` sends `$14`).
Key scancode `$39` (space) is stored by the same handler into `$60ff/$6100` (PP's keypad `*` and `/` are handled by the stub at `$264`: `cmpi.b #$e5` / `#$e6`).

**Snapshots** (all 1 MB STE unless named; `work/snapshots/`):
| file | state |
|---|---|
| `ste1m_race_grid.sav` | standing on the grid, no input (`$5ff8=0`, 4 cars + signs in view); the benchmark "standing" scene |
| `ste1m_race_start.sav` | fresh race (frame counter `$100e`=48, timer at start) with `$6105=$01` set: drives straight. The benchmark "driving" scene; a clean 33 s race window |
| `ste1m_race_idle.sav` | earlier standing state (timer already 37: it times out and restarts the race within ~500 VBL, so do not benchmark world rates on it) |
| `ste1m_race_drive.sav`, `ste1m_race_up.sav` | mid-race states; near the 39 s limit: **their world-rate runs were invalidated by the race restart** (`work/notes/bench_ste_race_drive.INVALID_*.jsonl`, `bench_ste_race_up.INVALID_*.jsonl` also ignored `--cpuclock`) |
| `ste4m_race_start.sav`, `megaste4m_race_start.sav` | 4 MB STE / 4 MB Mega STE at the race start |

## 2. Baseline numbers

Method: `tools/msrbench.py SNAP --clocks 8 16 32 --vbls N` restores the snapshot, `hatari-option --cpuclock N` (the memstate carries its own clock, `--cpuclock` on the command line is ignored), 100 VBL settle, then counts executions of the flip routine `$d1ca` with a trace breakpoint (`b pc = $d1ca :trace`) over N VBLs, and reads the world words with `m`. (`stharness.fps()` is not usable: the flip writes `$ff8200` as a long and the `($ff8201).b` change breakpoint reported 0 flips.) Raw: `work/notes/bench_ste_race_{grid,start}.jsonl`.

| scene | clock | flips / VBLs | fps | VBL per frame | frame counter `$100e` per s | world `$5ff8` per s |
|---|---:|---:|---:|---:|---:|---:|
| grid (standing) | 8 MHz | 79 / 400 | **9.88** | 5.06 | 9.83 | 0 |
| grid | 16 MHz | 133 / 400 | 16.63 | 3.01 | 16.64 | 0 |
| grid | 32 MHz | 134 / 400 | 16.75 | 2.99 | 16.72 | 0 |
| driving (`race_start` + up) | 8 MHz | 50 / 300 | **8.33** | 6.00 | 8.33 | **82.42** |
| driving | 16 MHz | 100 / 300 | 16.67 | 3.00 | 16.70 | **166.97** |
| driving | 32 MHz | 100 / 300 | 16.67 | 3.00 | 16.67 | **166.67** |
| Mega STE 4 MB grid (clock left as HAGA sets it, `$ff8e21=$ff`) | HAGA | 87 / 300 | 14.5 | 3.45 | 15.0 | (standing) |
Earlier 500-VBL driving runs on the not-yet-clean `race_up` snapshot: 83 flips / 500 VBL = 8.3 fps (and 42 / 250 = 8.4).

- **CPU or blitter/disk bound?** The race runs entirely from RAM (no `Fread`/FDC; no blitter) and fps scales with the CPU clock exactly until the 3-VBL floor, so it is CPU-bound (cycle count). The profile total at 8 MHz is 827 k cycles/frame (grid) and 943 k (driving) against 160,256 per VBL (`work/notes/profile_buckets.txt`).
- **Frame-rate dependent game speed: YES.** 82.4 -> 167.0 units/s when fps doubles (x2.03). The HUD timer is not yet identified (`work/notes/clock_scan_{8,16}.txt` are noisy): **[INFERENCE]** it is VBL-time-driven since the game's only VBL-time sources are `$611a/$611b` (`addq.b #$1,$611a.l` / `$611b.l` in the VBL handler `$d122/$d128`) and `$611b` is never read by the main loop; unproven (Q3).
- **Why exactly 3.00 VBL at 16/32 MHz** (frame sync, evidence):
```
00d1e4:  0c3900020000611a   cmpi.b #$2, $611a.l       ; wait until >= 2 VBLs since the last clear
00d1ec:  65f6               bcs.b  $d1e4
00d1ee:  6100ffda           bsr.w  $d1ca               ; flip: swap $1004/$1008, write $ff8200
00d1f2:  61000012           bsr.w  $d206               ; wait for the NEXT VBL
00d1f6:  42390000611a       clr.b  $611a.l
00d206:  3f00  move.w d0,-(a7) / 1038611a  move.b $611a.w,d0 / b038611a cmp.b $611a.w,d0 / 67fa beq.b $d20c
```
  The counter is cleared right after a VBL, so the next flip is at VBL +2 at the earliest and the post-flip wait ends at +3. Period = max(3, ceil(render time in VBL)). At 8 MHz grid: render 766 k cycles = 4.78 VBL -> 5 VBL (measured 5.06); driving 846 k = 5.28 VBL -> 6 VBL (measured 6.00).
- **Page flip:** double buffered, `$1004`/`$1008` = `$70000`/`$78000` (`m $1000` after boot: `00 07 00 00 00 07 80 00`), flip `$d1ca`:
```
00d1ca:  20381008  move.l $1008.w,d0 / 22381004 move.l $1004.w,d1 / 21c01004 move.l d0,$1004.w / 21c11008 move.l d1,$1008.w
00d1da:  2400 move.l d0,d2 / e05a ror.w #8,d2 / 21c28200  move.l d2,$8200.w
```
  (`$d1a8` is the other form: waits `$ff8209`==8 then writes `$ff8203/$ff8201`; used for the first screen.)

## 3. Hardware survey

Method: `tools/hwscan.py` on the RAM dump (`--range 200-70000`, which covers every executed instruction: Hatari's `profile stats` reports the active RAM range as `0x00796a-0x018f32` for the race and "ROM TOS: no activity"), on the unpacked RUNME (`python3 tools/pp_depack.py RUNME.TOS` -> `work/dumps/RUNME_unpacked.tos`: text $4430, data 22, bss 111206), on the HAGA file and on PP's resident HAGA code. Raw: `work/notes/hwscan_race0_raw.txt`, `hwscan_runme_haga.txt`, `hwscan_haga_resident.txt`.

| item | finding (game main program, executed in the race) | evidence | machine risk |
|---|---|---|---|
| video mode | ST low-res, 320x200, 4 planes, 16 colours; `clr.b $8260.w` | `00d1c4: clr.b $8260.w`; screen 32,000 bytes = 160 B/row | none |
| palette | ST 9-bit only (`$0222,$0333,$0500,$0630...`), no STE LSB bits | `m $ff8240 32`: `00 00 00 00 02 22 03 33 05 00 06 30 04 21 05 41 01 31 02 10 05 52 04 44 02 23 06 66 05 32 04 57` | none |
| raster | **Timer B in event-count mode (TBCR=8), vector `$120`->`$d616`**, one interrupt every 4 scanlines from a table at `$3cc0`: rewrites colours 1-14 (`move.l (a1)+,$8242.w`...) + 15 (`move.w (a1)+,$825e.w`). Sky gradient / HUD vs road palettes. 41-47 interrupts per frame, 12-14 k cycles (1.5 %) | `006fd4: move.l #$d616,$120.w`; `00d5f6: move.b #$8,$fa1b.w`; `00d62c..00d6d8` palette writes; profile counts below | per-line palette changes: Hatari TT/Falcon draws one palette per frame (cosmetic, per skill) |
| MFP | game clears every MFP enable at start, then enables only **Timer B** (IERA bit0) and **ACIA** (IERB bit6); **TOS's 200 Hz timer C is off**; Timer A/C/D untouched | `006f72..006f8e clr.b $fa07..$fa15`; `006f92 move.b #$1,d0 -> $fa07,$fa13`; `006fa4 move.b #$40,d0 -> $fa09,$fa15` | HAGA's `$114` timer-C vector is replaced during load by RUNME (`010b50..010bd0`) |
| vectors | VBL `$70`->`$d11e`, HBL/timerB `$120`->`$d616`, IKBD `$118`->`$cfb4`; exception/trap vectors `$100-$13f` -> `rte` stub `$7004`; SSP `$78000` | `006fcc/006fd4/006fdc`, `006fc2 move.l #$7004,(a0)+` x16, `006f68 lea.l $78000.l,a7` | writes vectors: restore on exit (PP's `*` exit) |
| VBL handler | `$d11e`: `movem.l d0-d7/a0-a6,-(a7)`, `addq.b #1,$611a`, `$611b`, `bsr $d486`: sound `$8bf2`, palette/raster setup, 3.4 k cycles per VBL | `00d11e..00d136`, `00d486`; profile `$d486` 3,435 cycles/call | none |
| screen buffers | two, `$70000` and `$78000` (32,000 B each, 768 B gap), flip by `move.l d2,$8200.w` (`$ff8201`/`$ff8203` only, low byte `$ff820d` stays 0) | `00d1ca..00d1de` | none (ST-compatible) |
| blitter | **not used** (no `$ff8a00-$ff8a3f` access in the executed range; hwscan reports 0 blitter lines) | `hwscan_race0_raw.txt`: 38 lines, 0 crit | a plain ST/TT have none, so a patch must probe |
| DMA sound | **not used**; sound = YM2149 through `$ff8800/$ff8802` only, via `lea.l $ff8800.l,a1 / lea.l $2(a1),a2` and `move.b (a0)+,(a2)` | `008e30..008e82` | **Falcon YM mirrors `$ff8804/$ff8806`: not touched** (no `movep`, no `$ff8804`) |
| STE hardware scroll `$ff8264/65`, `$ff820d`, `$ff820f` | not used | no hits | free to use on STE (probe `_MCH`/bus error) |
| STE/Falcon joystick `$ff9200+` | not used | no hits | |
| IKBD | joystick events + absolute mouse; handler `$cfb4`; command send `$d19a` busy-waits `btst #1,$fc00` (`00d19a`). Handler starts with `move.w #$2500,sr` | `00cfb4: move.w #$2500,sr`, `00cfbe: move.b $fc02.w,d0` | **blitter HOG bursts would starve it**: keep bursts short |
| 50/60 Hz | `$ff820a` reads `$fe` in the race (50 Hz); the game has no sync-mode write of its own; PP's RUNME writes `$fe` (`010b8a move.b #$fe,$820a.w`, low-confidence) | `m $ff820a` = `fe`; timing is VBL-count based, so 60 Hz would run 20 % faster **[INFERENCE, not tested; no US TOS 2.06 image here]** | test needed |
| Mega STE | RUNME/HAGA write `$ff8e21` (`010b24 move.b #$fc,$8e21.w`; HAGA `$2860`): Mega STE runs at 16 MHz + cache in the game (`m $ff8e21` = `ff`) | `hwscan_runme_haga.txt`, `hwscan_haga_resident.txt` | game already gets 16 MHz there |
| TT/Falcon | PP's `$14346 lea.l $9800.w,a4` Falcon palette pointer in RUNME; the game itself is plain ST | RUNME scan | not tested here |
| HAGA resident | 53 MFP, 45 vector writes, 6 `$8e21` (PP's loader, not the game) | `hwscan_runme_haga.txt` | |

Memory map at the race (1 MB; zero runs from `work/dumps/ram_race_start.bin`): game code `$7000-$19000`, data to `$B2700`, **free `$B2700-$E8400` (215 KB)**, also `$4E700-$50000`, `$54000-$56000`; PP's resident HAGA at `$F3000-$FB700`; HAGA chunk cache `$81000-$B1D40` (loads only). **Not the same at 4 MB** (`work/notes/freeram_ste4m.txt`, `freeram_megaste4m.txt`): the zero runs start at `$C7900` (STE and Mega STE 4 MB), so `$B2700-$C7900` holds data there. **[INFERENCE]** that data is the whole MS1 image (286,507 bytes = `$81000-$C6F2B`) in PP's >=4 MB whole-image cache mode (pp-haga-conversions: `HAGA+$321c` test, `$81000-$135000`), and MS2 (772,096 bytes) would be cached over `$C7900-$140000` when it is read; not verified in this study. A payload at `$B2700-$C7900` therefore needs the HAGA `pp_bigram_cache` patch (keeps chunk mode) to survive at 4 MB.

## 4. Renderer architecture

### 4.1 Frame loop (`$796a`..`$7bac`, one loop = one presented frame)
```
00796a:  jsr $838a            input/keys
007988..007a88:               state machine, timers, "$91f0" scroll value
007a88:  movea.l $1008.w,a5   a5 = back buffer; then the call list below
007b74:  jsr $d1e4            wait + flip (+ wait one more VBL)   [bytes shown at 7b72 are a mis-decode; real insn at 7b74]
007b7a:  move.w $1304.w,$1300.w / move.w $1302.w,$12fe.w          raster table setup for timer B
007b86:  addq.w #$1,$100e.w                                       frame counter
007b90:  add.w d0,$5ff8.w   (d0 = $130c = speed)                  WORLD POSITION: once per frame
007ba6:  lsr.w #3,d0 / add.w d0,$11c2.w                           distance/score
007bac:  bra.w $796a
```
The call list in the render part (return addresses are the stage points of `tools/msrstages.py`):
`f9fa fb96 fc2a fc80 fce4 fd64 fa2c 10ca6 1125c 113d4 1147a 11792 112c4 11342 11230 11396 fe50 ff76 1003c` (input/physics/AI, ~21 k cycles total), then
`17c24` (clear `$4ff8` span buffer), **`100b4`** road geometry, **`17c42`** road span draw, `10a5e 10a98 e218 e2e8 1182e 11a3c e316 dd50`, **`18318`** horizon strip, **`e406`** depth-sorted object draw, **`ef7a`** clouds + HUD, `18888 18c86 18f0e`, `d1e4`.

### 4.2 What each stage does (and what it paints)
Evidence for "what it paints": `work/shots/film_sheet.png` and the bounding boxes of the pixels each call changed. Reproduce with `python3 tools/msrfilm.py work/snapshots/ste1m_race_start.sav work/film` (chained `b pc = <return address of each call> :trace :once :file` breakpoints; each stage file saves both buffers and arms the next, so the film is one single frame; raw output `work/notes/film_bbox.txt`; which buffer is the back buffer alternates, the tool picks the one that changes). Label `NN_pc` = state when the CPU reaches `pc`, i.e. **after** the call that returns there:
```
21_7b10 (after 17c42, road span draw)  rows 120-199, x 0-319   4153 bytes differ vs the previous distinct stage
30_7b46 (after 18318, horizon strip)   rows 65-119,  x 0-319   4580
31_7b4c (after e406, objects)          rows 104-189, x 16-287  2617
32_ef84 (after de1c, cloud pass 1)     rows 1-64,    x 0-319    533
35_ef90 (after f214, thermometer)      rows 53-63,   x 32-63     45
38_efa0 (after f53c, digits)           rows 16-46,   x 80-95     83
41_efae (after f620, bottom-left item) rows 172-199, x 0-31     292
42_efb2 (after f76a, bottom-right)     rows 180-194, x 272-303  102
43_efb6 (after f7f0, speedometer)      rows 151-174, x 256-319  493
44_efbc (after de6c, cloud pass 2)     rows 0-69,    x 0-319    539
45_efc0 (after f22c, minimap box)      rows 16-64,   x 16-95    182
```
Between these, the back buffer is **unchanged from the start of the render part through `jsr $100b4`** (stage 00 `7a92` through stage 20 `7b0a` have the same hash; the first change is `21_7b10`). The names of the HUD parts (thermometer, speedometer, minimap) come from where the pixels land in the screenshots (`work/shots/race_start.png`), not from tracing the callers.

**Background is persistent, not rebuilt.** Sky, clouds area, HUD frame, mountains live in the two buffers; per frame the game repaints rows 120-199 completely (road, grass, bands; this also erases last frame's cars and signs), recopies the horizon strip rows 65-119, then draws sprites over it. There are no dirty rectangles for the road.

- **`$100b4` road geometry (97 k cycles/frame)**: builds per-scanline tables for 112 lines (`moveq #$6f,d7`) from the position/curve data: `$4564` curve offsets, `$1bbc` sine table (`and.w #$7fe`), `$4804/$49c4/$4aa4` outputs, segment stream at `$4b84`. The hot loop `$10216..$102b0` does two `mulu.w d0,d3` per line (`01025e / 01026e`) plus table lookups (`move.b (a5,d5.w),d3`, `andi.w #$3ff`). Output is a list of `movem.w d0-d2/d6,-(a6)` segment records per scanline.
- **`$17c42` road span draw (116 k excl.; 194 k / 176 k with `$1058a` and IRQs)**: walks backwards from the end of the screen (`lea $7d00(a0),a0`) writing scanlines with **precompiled unrolled `movem.l d2/d4-d6,-(a0)` spans** (jump table at `$17cba`, 4 longs = 16 bytes per instruction, `00017d0e..017d32`), edge groups through `jsr (a4)` = `$1058a`:
```
017d98:  4e94  jsr (a4)            a4 = $1058a   ; 106 calls/frame, ~560 cycles each (~60 k/frame)
01058a:  movem.l d1/d3,-(a7) ... 0105a0: tst.w (a5) / beq / move.l d1,d0 ... or.l d5,d0 ... (12 conditional tst/or per call)
```
  `$1058a` expands up to three colours (table `a5=$135a`, 16 `tst.w` + conditional `or.l`) into four plane words per 16-pixel group. It is called ~106 times per frame.
- **`$18318` horizon strip (35-45 k)**: copies a 55-row strip from one of **four pre-shifted copies** (`$60800 $62600 $64400 $66200`: `movea.l $1838e(pc,d6.w),a1`, d6 = `d2 & $c`) with `movem.l` blocks selected by a 20-entry jump table at `$1839e` (16-pixel column offset `d2 & $f0`). So the scroll has 4-pixel resolution. The bottom of the strip is then filled with `movem.l d0-d6/a3-a5,-(a0)` of `$ffffffff` (`018378`).
- **`$e406` objects (219-231 k, the largest stage)**: sorts the 37 object slots (table `$29c8`, stride `$38`) by depth with a 5-element exchange network (`00e440..00e474`, `cmp.w/exg.l`), builds an order list at `$36e8`, then calls `$e598` once per slot (37 calls/frame, 8.2 k cycles total for the loop itself, `profile` `$e598` 35-38 calls/frame, 128-240 cycles). `$e598` fetches the object type (`move.w $c(a2),d0`: 0..3) and goes through scale/frame lookups (`$1b076` table, stride 14 bytes: pointer, width, height...) into **masked sprite blitters**: `$12c1a`, `$12b06`, `$15a4e`, `$12c40`-style variants (see below) which `jsr (a6)` into self-modified kernels (`move.l (a2)+,(a4)` writes into code at `012c4c`).
- **Sprite kernels** (`$12000-$16000`, 43-45 % of all cycles in the bucket profile; spread over ~60 variants, hot blocks `$15100`, `$12b40`, `$14100-$141bf`, `$14540`, `$126c0`): 3-word sprite rows `movem.w (a1)+,d1-d3`, mask = OR of the three words, `and.w d0,(a3)` / `or.w dN,(a3)+` per plane word, `lea $98(a3),a3` per row (160 B stride), shifted variants use `ror.l d6,dN` and long `and.l (a3),d2 / or.l`:
```
012c1a:  5347 subq.w #1,d7 / 4c99000e movem.w (a1)+,d1-d3 / 3001 move.w d1,d0 / 8042 or.w d2,d0 / 8043 or.w d3,d0 / 4640 not.w d0
012c28:  c153 and.w d0,(a3) / 835b or.w d1,(a3)+ / c15b and.w d0,(a3)+ / c153 and.w d0,(a3) / 855b or.w d2,(a3)+ / c153 and.w d0,(a3) / 875b or.w d3,(a3)+
012c36:  47eb0098 lea.l $98(a3),a3 / 51cfffe0 dbra d7,$12c1c
```
  ~142 cycles per row of one 16-pixel chunk (4 dest words): about 35 cycles per destination word. Sprites are pre-scaled bitmaps (no run-time scaling). **Not preshifted**: the shift is done at draw time with `ror.l`.
- **`$ef7a` HUD + clouds (195-233 k)** call order and measured cost (stage rows, mean cycles, grid / driving): `de1c` 29 k / 31 k, `f1c0`, `efc6`, `f214` 8.5 k / 9.5 k, `f3b6` 0 / **34 k** (score digits, redrawn whenever `$11c2` changes = every frame while driving), `f430`, `f53c` - / 10 k, `11ef0`, `f90c` 8 k / 4 k, `f620` 10 k, `f76a` 12.7 k / 11.3 k, `f7f0` 21 k / 19 k (speedometer), `de6c` **51 k / 49 k**, `f22c` **50 k / 54 k** (minimap), `f134`.
  - `de1c`/`de6c`: loop over the 12 slots `$29c8+$38*n` (`moveq #$b,d7`, `lea $29c8.w,a6`, `lea $38(a6)`), calling the 1-plane routines `$122e4` (`not.w d0; or.w d0,(a3)` x5 words per row: 80-pixel-wide rows) and `$15052`. They change pixels only in rows 0-69 across the full width (539 / 533 bytes): **[INFERENCE] these are the 12 cloud sprites** (the white dithered patches in the sky that drift in the screenshots), erase + draw in plane 0. Cost per frame ~80 k cycles (8-10 %) for ~540 changed bytes.
  - `f22c`: calls `$12788`, `$127fa` x4 (rectangle/line parts, `moveq #$1f,d0 / #$f,d1 / #$50,d2 / #$f,d3`) and `$12690` (30 k): changes rows 16-64, x 16-95 = the minimap box with the track outline and position dot.
  - Most HUD parts are guarded by "value changed" flags that redraw twice, for the two buffers (e.g. `f3b6`: `cmp.w $11c4.w,d2 / bne.. / tst.b $11c7.w / clr.b $11c7.w`), so the gauges cost little when nothing changes but the score and minimap cost every frame.
- **Sound**: `$8bf2 -> $8c38` YM player runs from the VBL handler (3.6 k cycles per VBL, ~19-22 k per frame at 5-6 VBL/frame, 2.3 %): cost scales with VBL count, not frames. No DMA.

### 4.3 Bytes processed per frame
Road: rows 120-199 x 160 B = 12,800 B written by `movem` spans + edge groups. Horizon: rows 65-119 = 8,800 B copied (+ fill). Sprites: variable; object stage 219-231 k cycles. Pixels that actually differ between two presented frames: **grid 90 B (77 sky + 7 mountain + 5 road), driving 2,193 B (176 + 318 + 1,699)** of 32,000; changed rows per frame while driving: 61 of 80 road rows, 14 of 55 strip rows, 17 of 65 top rows (`work/notes/frame_diff.txt`, `frame_diff_rows.txt`; method `tools/msrframes.py` + `msrdiff.py`: 12 consecutive flips, each finished buffer compared to the next / the one after).

## 5. Profile

Per-call cycles of the frame loop (`tools/msrstages.py`: a chain of `:once :file` breakpoints on the return address of every call, each logging `e VBL` / `e FrameCycles`; the VBL counter and FrameCycles wrap at different instants, so the script fits the wrap offset `c0` (4880) until the event times are monotonic: 0 violations). Interrupt time (timer B, VBL, sound) is **included** in the stage it interrupts. 55 frames each. Raw: `work/notes/stages_race_{grid,start}.txt`; tables: `python3 tools/msrstages_md.py race_start`.

| stage (call) | what | grid cycles | grid % | driving cycles | driving % |
|---|---|---:|---:|---:|---:|
| `$e406` | depth-sorted objects (cars, signs, trees; 37 slots) | 219,369 | 27.1 | 230,617 | 24.1 |
| `$17c42` | road span draw (+ `$1058a` edges + IRQs) | 176,261 | 21.8 | 194,044 | 20.2 |
| `$100b4` | road geometry | 97,034 | 12.0 | 97,112 | 10.1 |
| `$de6c` + `$de1c` | 12 cloud sprites (draw + erase passes) | 80,359 | 9.9 | 80,205 | 8.4 |
| `$f22c` | minimap | 49,621 | 6.1 | 54,181 | 5.7 |
| `$18318` | horizon strip copy | 44,876 | 5.5 | 38,731 | 4.0 |
| `$d1e4` (stage `07b7a`) | **idle wait**: flip + wait for VBL | 43,255 | 5.3 | 112,652 | 11.7 |
| `$f3b6 $f53c $f620 $f76a $f7f0 $f214 $f90c $11ef0` | HUD digits, gauges, thermometer | 65,000 | 8.0 | 99,000 | 10.3 |
| `$e316` | (36 x `$e338`, small per-object loop) | 11,923 | 1.5 | 15,370 | 1.6 |
| everything else (input, AI, physics, `$18888..`) | | ~21,000 | 2.6 | ~37,000 | 3.9 |
| **mean frame period** | sum of stages | **809,390 = 5.05 VBL** | | **958,756 = 5.98 VBL** | |

Interrupt cost inside those numbers (profile, `profile save`): timer B ISR 41 / 47 executions per frame, 12.3 k / 14.0 k cycles (`$d616-$d6f8`); VBL handler `$d11e` + `$d486` 7.1 k / 8.1 k; YM sound `$8bf2-$9000` 18.8 k / 21.8 k: ~38-44 k cycles/frame (4.6 %), constant per VBL, not per frame.

Instruction-level bucket profile (Hatari `profile save`, exclusive cycles per jsr-target bucket, `tools/msrprof.py`, `work/notes/profile_buckets.txt`): `$12c1a` 21.0 % / 16.3 % ("calls 0": a bucket of dynamically dispatched sprite kernels), `$100b4` 18.9 % / 16.9 % (this bucket also swallows `$1058a`, the edge routine called from the road draw), `$17c42` 13.0 % / 12.2 %, `$d206` 4.1 % / 9.4 %... **The bucket table mis-assigns dynamically called code (`jsr (aN)`); the stage table is the one to trust.** Totals: 826,817 cycles/frame (grid, 33 frames) and 942,607 (driving, 29 frames).

**Distribution: flat.** No single routine is above 27 %; the top three (objects, road draw, geometry) are 61 % (grid) / 54 % (driving); sprites in the broad sense (objects + clouds + HUD + minimap) 51 % / 48 %.

## 6. Ranked plan (8 MHz STE; gains are cycles of the measured routine, not guaranteed frame-rate)

Frame period now: 5.05 VBL (grid) / 5.98 VBL (driving). Gain column = estimated change of the period; basis cited. All "pixel-identical" items can be gated by the A/B capture at the flip `$d1ca` (buffers `$70000/$78000`, 32,000 visible bytes each) with a negative control.

| # | item | what / candidate fix | est. gain (basis) | risk | pixels | machines |
|---|---|---|---|---|---|---|
| 1 | **Frame sync** | Remove `cmpi.b #$2,$611a / bcs` floor (`$d1e4`); move the post-flip VBL wait (`bsr $d206` at `$d1f2`) to just before the first back-buffer write (`jsr $17c42`, `$7b0a`): the geometry `$100b4` (97 k) and logic (21 k) run during the wait. | idle wait 43 k / 113 k cycles now; period = ceil(render): grid 4.78 -> 5 VBL, driving 5.28 -> 6 VBL; expect **+4 % grid, +10 % driving** (period 5.05 -> ~4.85, 5.98 -> ~5.4); removes the 16.7 fps cap on faster machines (the 16 MHz/32 MHz/Mega STE results). **[INFERENCE]** (needs a prototype); evidence the back buffer is untouched until `17c42`: film hashes. | low-medium: `$611a` is also read by `$df20` (animation phase), `$16a2e`; frame-coupled speed changes (item 2) | identical | all |
| 2 | **Game speed vs fps** | fixed timestep: per-frame increments (`add.w $130c,$5ff8`, `$11c2`, AI/object steps, `$100e`) scaled by elapsed VBLs with remainder accumulators (MW2 method), or tick the world at a fixed rate and let render skip | not a speed-up; **required for any fps gain not to speed the game up** (world 2.03x at 16 MHz). Basis: pos/s 82.4 -> 167.0. Per-frame counters are many (`$100e` users: `007492 007a0a 007a34 00db98 00f9fa 00fa92 ...`) | **high**: integer speeds are 7-10 per frame (low resolution), AI/collision per frame | n/a | all |
| 3 | **Minimap skip** `$f22c` | redraw only when its inputs changed for 2 frames (both buffers); or draw the track outline once and only move the dot | 50-54 k = **-6 %** standing (inputs static), driving: the dot moves each frame -> redraw only the dot area (rows 16-64 x 16-95, 182 B changed): est. -35 k (-3.5 %) | low-medium | identical if both buffers are kept in sync | all |
| 4 | **Clouds** `$de1c/$de6c` | cloud strips are 1-plane, 80 px wide rows (`or.w`/`and.w` per word, 5 words per row via `$122e4`/`$15052`): move to long `movem`/`or.l` kernels, or skip erase+draw for clouds whose position did not change for 2 frames | 80 k cycles for ~540 changed bytes. Kernel rewrite 30-40 % = **-25..-32 k (-3..-4 %)**; position-skip: clouds move every frame (77 sky bytes change per frame even standing), so little. **[INFERENCE]** | low | identical | all |
| 5 | **Edge routine** `$1058a` | table-driven colour->plane expansion (precompute the 16 combinations per frame / per scanline set instead of 12 `tst.w/or.l` per call) | 106 calls x ~560 cycles = ~60 k; to ~150 cycles = **-40 k (-4..-5 %)**. Exactness testable on all inputs offline | low | identical | all |
| 6 | **Road geometry** `$100b4` | replace the 2 `mulu.w` per line (`$1025e/$1026e`, 112 lines) with a 16x? table, strength-reduce the loop; or reuse the previous frame's table while standing | 97 k; mulu alone ~13 k; careful rewrite **-25..-35 k (-3 to -4 %)**; standing frames identical input -> skip whole stage (-12 % but only on the grid: the cars also animate, so the road part can only be skipped with item 7) | medium (exact table compare per frame is easy) | identical | all |
| 7 | **Road repaint avoidance** `$17c42` | the road is repainted fully each frame (12,800 B) while 7 % of bytes change: keep per-row/segment records of what each buffer holds and repaint only changed spans/rows; sprites erase through the repaint, so it needs a per-row "sprite touched" mask | upper bound: 176-194 k -> ~60-80 k (**-100 k, -11..-13 %**) **[INFERENCE]**: driving changes 61 of 80 rows per frame (13 % of bytes), so row-level skipping gains little; span-level is needed. Standing: nearly all redundant (0.8 of 80 rows change) | **high** | identical | all |
| 8 | **Score digits** `$f3b6` | redraw only the changed digit(s) | 34 k while driving = **-3.5 %**, est. -25 k (-2.5 %) | low | identical | all |
| 9 | **Horizon strip** `$18318` | skip the 8,800-byte copy when the scroll offset (`$12f8`) is unchanged for 2 frames (straights); or STE hardware fine scroll in the timer-B table | 35-45 k (4-5.5 %), not every frame; hardware scroll = whole saving but **1-pixel steps instead of the 4-pixel preshift steps (visible), STE-only**, needs line-width/`$ff8265` handling per band | skip: low; hw scroll: high | skip: identical; hw: visible | skip all; hw STE only |
| 10 | **Object dispatch** `$e598`/kernels | 37 slots/frame go through `$e598`: early-out for inactive/off-screen, specialise the common types; sprite kernels `ror.l` -> pre-shifted data (RAM ok: 215 KB free) | e406 is 219-231 k; the visible share per type is unknown (needs per-type profile). A plausible 10-20 % of it = **-20..-45 k** **[INFERENCE]** | medium | identical | all |
| 11 | **Blitter** | masked sprite via 2 blitter passes (`dst &= ~mask`, `dst |= src`) needs a separate mask in memory; ~24 cycles/word (2 passes x 12) vs CPU ~35 cycles/dest word, but setup ~200+ cycles per pass kills small/distant sprites (most are small); span fills: 4.4 vs 4.33 cycles/word = parity (measured in MW2, `blitter.md`); copy 8.8 vs 8.3 | **no gain expected** (bus-bound; HOG starves IKBD, `st-game-speedup`). **[INFERENCE, not measured here]** | high | identical | STE/Mega ST only (probe `$ff8a3c`, Mega STE `$ff8e21` readable = 16 MHz: CPU wins) |
| 12 | **Triple buffer** | alternative to item 1 | needs the HUD "redraw twice" flags generalised to three buffers: rejected, item 1 gives most of it without a third buffer | high | | |

Rough sum if items 1, 3, 4, 5, 6, 8, 9(skip) are done: cycle items 3-6, 8, 9 remove about 168 k (grid: 50+28+40+30+0+20) / 178 k (driving: 35+28+40+30+25+20) of the 766 k / 846 k render cycles (22 % / 21 %) and item 1 cuts the idle part: **~5.05 -> ~3.9 VBL grid (12.8 fps) and ~5.98 -> ~4.3 VBL driving (11.6 fps)**, i.e. about +30 % / +40 % fps. **[INFERENCE: arithmetic on the measured routine costs plus my per-item savings, not measured end to end.]** Items 7 and 10 are the only large further levers and are risky or visible. 16.7 fps (the sync floor) at 8 MHz is not reachable with these items alone; on a 16 MHz machine item 1 is what lifts the cap.

Pixel-identity story: items 1, 3-8, 10 are pixel-identical by construction and by the A/B gate; item 9 (skip) is identical, item 9 (hardware scroll) and any cloud/sprite reduction are visible and need approval.
Equality gate design: `capture_frames(out, flip_addr=0xd1ca, at_vbl, nth_flip, buffers={'b70000':(0x70000,0x7d00),'b78000':(0x78000,0x7d00)})`, input as a pure function of the loop counter (`$6105` fixed), stock game at 8 vs 16 MHz must come out identical **before** timing patches (self-test), and a negative control (e.g. a nopped cloud pass) must fail.

## 7. What patch delivery needs

- **Loader chain (measured, cold boot with `--trace gemdos`, `tools/msrentry.py`, raw `work/notes/entry_ste_1024.txt`, RAM at the instant the game starts: `work/dumps/ram_entry_1024.bin`):** `Pexec(0,"C:\RUNME.TOS")` -> `Fopen("HAGA")`, `Fread(64,14000,0x137dc)`, `Super`; HAGA probes `GSAU.TOS`, `FILES\D15H5.FIC`, `C:\GAMEX\D15H5.FIC` (other games' files, not found: harmless) and reads `$ff8e21` (bus error on an STE: `WARN : Bus Error reading at address $ffff8e21, PC=$1398a`, PP's own guarded probe); cover `FMR273.HST` -> `$137dc`; `Dsetpath("FILES")`; `Fread("MSR_S1.FIC",17103) -> $81000` (stage 1: header `C3 00 00 42af ... "MSR_S1"`); then `Fread("MS1",200000) -> $81000` twice (the second after `Fseek(86507)`): the 1 MB chunk cache; no further GEMDOS file activity before the game starts. `MS2` is not opened before the first race. After that the game is in RAM at `$7000-$19000` (profile range `0x00796a-0x018f32`).
  **Game start:** code `move.l #$6f5a,$88.w` / `trap #2` at `$6f50` (`21fc 00006f5a 0088 4e42`; the same bytes again at `$7150`); the trap handler `$6f5a`: `move.w #$2700,sr`, `lea.l $70000.l,a0`, `bsr.w $d1a8`, `lea.l $78000.l,a7`, clears the MFP (`$6f6e..$6f8e`), installs `$70/$118/$120`, `move.w #$2300,sr`, `bra.w $718c`. At the breakpoint `pc = $6f64`: `SSP=$7FFEA` (frame `SR=$2300`, `PC=$6f5a`), `USP=$B1F40` (PP's), `SR=$2700`. The game never returns to PP's code. So a **one-shot installer can hook `$6f5e`** (the 6-byte `lea.l $70000.l,a0`: `jmp installer.l` after replaying it): supervisor mode, IPL 7, before the MFP is touched, every patch site in `$7000-$19000` already loaded. **Not done:** how to get a RAM patch applied at that instant from outside (MW2: replace PP's patcher tail `jmp <entry>`; here PP's patcher block was not located: `$4bc-$59c` holds TOS vector data at the entry instant, not code). Open item for P1; leads: RUNME's stack phase (`work/dumps/RUNME_unpacked.tos`) and a hook on the return of HAGA's second `MS1` chunk read (`PC=$F9120`, the `Fclose` after it).
- **Payload placement**: 1 MB: `$B2700-$E8400` free (215 KB; MW2 used `$B3000-$BAFFF` staged by RUNME's data segment). 4 MB: free only from `$C7900` (and MS2's whole-image cache may later cover `$C7900-$140000`); safest is the HAGA `pp_bigram_cache` file patch (keeps chunk mode, as in MW2) so one address works at both sizes, or use `$E0000-$E8400` (32 KB) only if MS2 is never cached over it (unverified). The code needed for items 1, 3-9 is small (< 8 KB); table data (items 5, 6) a few KB.
- **Machine probing**: no cookie jar (PP's jar), use the 68020 index-scale test and bus-error-guarded probes as in MW2/Populous. The patches in this plan need no blitter and no STE register, so they work on ST/Mega ST/TT/Falcon unchanged; only item 9 (hardware scroll) needs a probe.
- **Patch sites** (from this study; all inside the one `$7000-$19000` image, which does not move with TOS, so no relocation needed): flip `$d1e4-$d206`, call `$7b0a` (insert wait), HUD callees `$f22c`, `$f3b6`, cloud `$de1c/$de6c`, `$1058a`, `$100b4`, `$18318`.
- **Credit line**: the user picks the screen (the intro "Welcome partners" text screen or the title).
- **Saves**: PP's statesave is a HAGA feature (`/` on the keypad); the game has no own save to flush (unverified: only the HAGA README mentions "savestates").

## 8. Open questions for the user

Q1. Is there a floppy version to ship? PP's release is HAGA HD only (floppy images are STX conversions inside `MS1`/`MS2`); the standing rule says floppy + HD. Do you want a floppy build, or HD only?
Q2. **Game speed**: at 16 MHz the unpatched game already runs the world 2.03x faster per second than at 8 MHz (and any speed-up does the same on 8 MHz). Should the patched game (a) keep today's 8 MHz world speed per second (needs the fixed-timestep rewrite, high risk, item 2), or (b) accept that the game runs faster when fps rises (then the playable speed rises up to 2x on the same level design)?
Q3. Does the HUD stopwatch (race time limit, ~39 s) have to stay in real seconds? (not yet identified in code; see Q2).
Q4. Visible trade-offs: OK to drop to fewer clouds, or to update the sky every other frame, if pixel-identical items are not enough? OK to use STE hardware scroll for the horizon (smoother, STE-only)?
Q5. Target speed: 8 MHz STE is the baseline; is "about 12-13 fps" (the estimate above) an acceptable result, or is 16.7 fps (the sync floor) the goal at 8 MHz? The latter needs sprite-work reduction (visible) or a redesign of the repaint (item 7).
Q6. 60 Hz machines: should the patch force 50 Hz sync (`$ff820a = $fe`) at start? (the game is VBL-timed, 60 Hz would run it 20 % fast).
Q7. Mega STE: HAGA already runs it at 16 MHz + cache; do you want the patch to leave that as is? (the sync fix then helps it: 14.4 fps standing today, expected 16.7+).
Q8. Credit line placement and version string (`v1.0 enhanced by dad_prg`?).

## 9. Unproven / caveats

- Per-routine semantics of the sprite kernels (which objects use which variant) and of `$de1c/$de6c` (clouds) are inferred from pixel bounding boxes, not from tracing each caller.
- Sprite-routine and road-draw gains (items 4, 7, 10) are estimates; only the stage costs are measured. Nothing has been prototyped.
- Hatari-only measurements (8.02 MHz model, STE bus timing approximated). Real-hardware fps was not measured.
- 60 Hz, TT/Falcon, ST TOS 1.04, 2 MB boots and long play (multiple races, game over, the Mega STE/Falcon HAGA menus) were not tested. Boot tested: STE 1.62 1 MB and 4 MB, Mega STE 2.06 1 MB and 4 MB.
- The HUD clock variable, the number of simultaneously visible objects per frame, and the exact PP hand-over address are open.
- `work/notes/bench_ste_race_up.INVALID_*.jsonl` and `bench_ste_race_drive.INVALID_*.jsonl` are kept only as a record of two invalid runs.

## 10. Files

`tools/`: `msr.py` (Moonshine class, `boot_to_race`, `drive`, `flips_pc`, `prof`), `msr_boot_test.py`, `msrbench.py` (fps/world rate vs clock), `msrprofrun.py` (snapshot -> dump + profile), `msrprof.py` (bucket table), `msrtree.py` (inclusive call tree from the profile), `msrstages.py` + `msrstages_md.py` (per-call cycles of the frame loop), `msrframes.py` + `msrdiff.py` (consecutive presented frames and changed-byte statistics), `msrclock.py`, `msrdump.py`, `planar.py` (screen dump -> PNG).
`work/`: `dumps/ram_race_{0,up,grid,start}.bin` (1 MB each, HAGA/game RAM), `RUNME_unpacked.tos`; `prof/race_{grid,start}.txt`; `snapshots/*.sav`; `shots/`; `frames/{grid,drive}` (12 flips, both buffers); `notes/` (all raw numbers cited above).
