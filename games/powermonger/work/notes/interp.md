# Powermonger men interpolation (PMInterp): predict-ahead on render-only passes

Patches (both `; default: no`, need the `tick_*` set): `patches/p3b_interp.s` (site `$130aa`, `jsr $f898` the landscape + objects renderer) and `patches/p3b_delta.s` (site `$130c8`, `jsr $6a3a`).
Blob and data: prefix `p3b_` = `$B8800-$BAFFF`; code `$B8AA0-$B8BBD` and `$B8BC0-$B8C79`, data `PD $B8A80` (32 B), `OLD $B8D00` (2048 B), `LST $B9500` (5120 B, ends `$BA8FF`).
Gate tool: `tools/pminterp.py` (`state`, `strip`, `cost`, `rate`, `edge`, `ui`, `boot`); `tools/pmab.py --tonly` (new flag), `tools/pmtick.py` (masks, below). Frames and screenshots in `work/shots/interp_*` (git-ignored).
Everything: 1 MB STE, TOS 1.62, Hatari 2.6.1, snapshots in `work/snapshots/`, 16 MHz via `set_cpuclock` unless said otherwise. Evidence = raw tool output or disassembly (`tools/m68dis.py` on `work/dumps/get_men.bin`); `[INFERENCE]` = not run.

## 0. Result

| item | status |
|---|---|
| World ticks 4 per second, world state untouched | `state`: RAM `$0-$60000` at every loop top equal to the tick-only build in 7 runs (5 scenes at 16 MHz, 2 at 8 MHz) with a negative control each (section 4a) |
| Men (and projectiles) drawn part-way into their next step on render-only passes | yes; steady walker: tick-only `102 102 105 105 105 107 107 110 110 113 ...` (pairs), interp `103 105 106 107 109 110 111 113 114 116 117 118 ...` (section 4c) |
| Tick passes pixel-identical to the tick-only build | yes with `TOFF = 1` (T frames 55/55, 55/55, 56/56, 55/55 byte-identical at 16 MHz). **By default tick passes are drawn with offset 1.0 on purpose, see section 2.3: the literal "frac = 0 on tick passes" makes every man jump back one step at every tick pass** |
| Cost | render pass +8.2 k cycles (get_men, 12-17 movers) to +14.5 k (battle_260, 12-24 movers), delta scan 24-39 k per tick; mean +20 k per pass = +1.1 % at 16 MHz; fps 8.200 = 8.200 (get_men), 8.033 -> 7.867 (battle_260); **8 MHz: fps identical** (section 4d) |
| Edge cases | stop (overshoot 3-5 px for at most one tick, then snap back), death, building, teleport, pause, query window: section 5 |
| Cold boot, default floppy set + this patch | STE 1 MB TOS 1.62 and Mega STE 4 MB TOS 2.06: `PMPO`, both sites patched, 16 MHz set (320 005 / 266 675 cycles per VBL = 2 x the 8 MHz figure), offsets drawn only at 16 MHz (section 4f) |
| Not done / limits | animals and angels are not extrapolated (about 1 px per tick); a man crossing a cell edge holds for the rest of the tick (section 6) |

## 1. What moves per tick (people table `$51b66`, 512 x `$32` B)

Method: `log_passes` (RAM `$0-$60000` at every loop top, 16 MHz, 700 VBL, the first loop top of each tick) on get_men, battle_320, battle_260, map_idle, then per record the change of the words `+8` (x) and `+10` (z) between consecutive ticks (`/tmp/pmi/ana*.py`, not kept; the numbers below are from those runs).
* Live records: byte `+5` > 0 (1 or 2; 47 live records in every snapshot, highest index 47). `+6` = draw handler (jump table `$1162e`), `+7` = sprite/state.
* **Men** (`+5` = 2, `+6` = 0): per tick (-32,0) (31,0) (32,0) (0,8) (0,7) (-32,32) (0,-32) (32,21) (26,17) (22,22) (38,0) (33,33), 0 when standing (get_men, 1100 record-ticks: 295 standing). Nothing above 38 per axis.
* **Projectiles** (`+5` = 1, `+6` = 0, `+7` = `$40`, battle_320 / battle_260): (52, 8..24) per tick for 3-10 ticks, then one landing step of 53-102 (73, 70, 102, 74, 82, 86, 72, 62, 53...; those above 56 get no list entry) and they stand. They ride the same table and draw path as the men.
* Static records `+5` = 1, `+6` = 14 (1430 record-ticks, houses or objects [INFERENCE]): never move. Angels (`+5` = `$fe`, `+6` = 12, battle_320, 550 record-ticks): x/z constant, the word `+18` (height) falls by exactly 1 per tick (`(-1, 550)`): 1 px per tick, **not extrapolated** (a rise of 1 px per 12.5 VBL cannot be seen between ticks).
* Animals (table `$4ccd6`, stride `$14`, 40 records; `+8/+10` change by (-1,4) (1,7) (-3,-3) (-4,0) per tick): at most 7 units = about 1 px per tick, **not extrapolated**.
* Captains (`$51538`, 6 x `$13c`) and groups (`$4e514`) are not drawn from their own position: their sprite is a man record. Carts, boats and birds: **none found** in the 7 snapshots (no record of another kind moved); [INFERENCE] if they live in the people table they are covered by the same code as long as a tick moves them by at most 56 units per axis.

## 2. Design

### 2.1 How the renderer reads a record (disassembly)
```
0130aa  jsr $f898.l                      the only call of the landscape renderer (m68dis --callers f898)
00fdb2  move.w $0(a2),d4 ; beq ; jsr $115e0.l      per cell: terrain triangles, then the chain of the cell ($47970 grid, word = head)
0115e0  lea.l $51b66.l,a3 ; adda.w d4,a3 ; ... jsr $1162e(pc,d4.w)    handler by byte +6;  move.w $0(a3),d4 ; bne $115e0  (chain link at +0)
011c8a  (men)  ... 011ca6: bsr.w $11f12
011f12  move.w $8(a3),d6 ; move.w $a(a3),d7
011f1a  andi.w #$ff,d6 ; andi.w #$ff,d7 ; bilinear blend of the cell's 4 projected corners (a0), 4(a0), $40(a0), $44(a0) -> d0/d1 screen x/y
```
So a man's screen position is the LOW BYTES of x/z (the position inside the cell he is chained in); the high bytes select the cell, and the chain is rebuilt by the men update at the tick. A render-only pass can therefore draw him part-way into the next step by changing the low bytes for the duration of `$f898` and writing the words back. Height comes from the same bilinear blend (the terrain), so it follows.

### 2.2 Hooks
* `p3b_delta` (`$130c8`, the pass's `jsr $6a3a`, right after the men update `jsr $14b62` at `$130c2`): `jsr dlt`; `dlt` ends with `jmp $6a3a`. On every pass that ran a world tick (tick_head `RON` D+6 = 0) it compares the x/z longs of the 512 records with `OLD` (positions after the previous scan), writes `OLD := new` and builds `LST`: `{record byte offset, dx, dz, -, -}` (10 B) for every record whose change is at most `STEP` = 56 units per axis (men <= 38, projectiles in flight 52; teleport, spawn into a slot and the landing step of a projectile are larger: no entry = no extrapolation). `NMOV` (PD+2) = entries. ~52 cycles per record, 24-39 k per tick (section 4d).
* `p3b_interp` (`$130aa`): `jsr ap`. `ap` computes `FQ`, for every entry saves x/z, writes `low(x) + (dx*FQ)>>8` and the same for z clamped to 0..255 (high byte untouched), calls `jsr $f898` untouched, then writes the saved words back (registers and the stack are restored around both halves).
* `FQ` = time since the tick the records describe, in 1/256 of a tick (tick = 12.5 VBL = 25 half-VBL = tick_head's TK): `ACC * 256/25` on a render-only pass (`ACC` = tick_head's half-VBL accumulator, < 25 there), `(ACC + 25) * 256/25` on a tick pass (see 2.3), at most 384. No list, `NMOV` 0, `FQ` 0 or the game paused (`$57ff2`): `ap` calls `$f898` as it was.
* Scan gate: `p3b_delta` scans only while a render-only pass was seen in the last 8 ticks (`D+12` RPASS against `PD+16`, countdown `PD+24`). A machine that never has render-only passes (8 MHz: every pass is a tick pass) pays the 28-cycle check and the frames are the tick-only frames. When render-only passes start the first interval has no list and the second has one built against stale `OLD` (changes above 56 are dropped); smoothing is complete from the third tick.
* `PD+0` `TOFF` != 0 forces `FQ` = 0 on tick passes (the gate, `--poke b8a80:0001`).

### 2.3 Deviation from the brief: frac on tick passes
The brief said frac = VBLs since the last tick / 12.5 and 0 on tick passes. The pass order is: logic, **render**, ..., men update (`$14b62`). The render of tick pass k therefore shows the people as tick k-1 left them (that is what the tick-only build shows too, and why its R frames after the tick show the new positions). With frac = 0 on the tick pass the sequence at 16 MHz (T, R, T, R) is `Q(k-1)+0, Q(k)+0.5d, Q(k)+0, Q(k+1)+0.5d`: a step back every tick pass. Measured (`strip`, same window, `TOFF` = default tick-only vs 0 vs 1), progress of every moving record along its net displacement, consecutive frame pairs:
```
get_men    16 MHz tick-only: 214 pairs backwards  4 unchanged 154 forwards  56 | interp: 222 pairs backwards 10 unchanged 110 forwards 102 | TOFF: 220 pairs backwards  53 unchanged  92 forwards  75
battle_260 16 MHz tick-only: 816 pairs backwards 15 unchanged 531 forwards 270 | interp: 790 pairs backwards 41 unchanged 357 forwards 392 | TOFF: 790 pairs backwards 167 unchanged 346 forwards 277
battle_290 16 MHz tick-only: 832 pairs backwards 27 unchanged 516 forwards 289 | interp: 780 pairs backwards 42 unchanged 259 forwards 479 | TOFF: 780 pairs backwards 261 unchanged 218 forwards 301
```
Same record over 26 frames (get_men record 9, `R/T tick/ACC:x,y` of the sprite blit, from `--dump`):
```
tick-only: 102,124 102,124 105,122 105,122 105,122 107,121 107,121 110,119 110,119 113,119 113,119 116,117 ...   (pairs, 3 px per tick)
interp:    103,123 105,122 106,122 107,121 109,120 110,119 111,120 113,119 114,118 116,117 117,117 118,116 121,116 122,115 123,115 123,115 123,116 128,115 130,115 131,115 133,115 134,115 135,115 137,115 138,115 140,115
TOFF:      103,123 102,124 106,122 107,121 105,122 107,121 112,119 110,119 115,118 113,119 117,116 116,117 121,116 119,117 123,115 123,115 122,115 128,115 126,114 ...   (a step back at every T frame)
```
So tick passes are drawn at the end of the straight line the render-only passes before them were running: `FQ = (ACC + 25)*256/25` (the same line, `ACC` is what is left after tick_head took the tick off), capped at 1.5 steps. Pixel-identical tick passes are available as `TOFF`; with it the gate (b) passes (section 4b) and nothing else changes. [Decision for the lead: default stays "continuous"; `TOFF` is not for play.]

### 2.4 Velocity and clamps
* Velocity = the last tick's delta (position after this tick minus after the previous scan), per axis, from `OLD`. A record that stops keeps its last delta for the render-only passes of the tick in which it stopped: at most one step of overshoot (3-5 px for a man) for at most one tick, then the scan sees delta 0 and the record is drawn where it is (section 5).
* Low byte clamped to 0..255 on purpose: the sprite is drawn when the renderer reaches the cell the record is CHAINED in (the chain changes in the men update at the tick, not here), terrain of cells drawn later would paint over a sprite that stands past the edge, and the screen blend overflows 16 bits when `d6` leaves 0..255 (`muls.w d6,d1; asr.w #8,d1`). A man crossing a cell edge (x moves 32 of 256 per tick: 1 tick in 8 per axis) holds at the edge for the rest of that tick and jumps when the tick moves him into the next cell: in the strip above `123,115 123,115 123,116 128,115` (record 9, x low byte $f0 -> $10 at tick 157).
* Walk animation frames: left as the game has them, once per tick (`$57fec` bit 0 toggles in `$1abaa`, which tick_wx runs on tick passes only); the facing byte `+$11` is read live by the renderer.
* Camera scroll / rotate / zoom already change per pass: no change.

## 3. Files touched besides the two patches
* `tools/pminterp.py` (new), `tools/pmab.py` (`--tonly`: only tick-pass frames are hard comparisons, differing render-only frames are counted), `tools/pmtick.py` MASKS: `$1c480-$1c550` (pointer + its save area; was `-$1c4e0`), `$2dea4-$2dea6` (key table, Alt), `$2df9e-$2dfa0` (right-button latch, IKBD handler `$12d6-$136c`), SITE_MASKS `$130aa` and `$130c8`.
* Those masks are input/pointer state that differs by timing. Observed with the tool before they were masked (one loop top each, 700 VBL): `$2dea4` (`iter 173 tick 173 tick-only 00ff interp 0000`, `iter 196 ... tick-only 0000 interp 00ff`) in 2 of 2 get_men runs of tick-only against tick-only (`--selfcmp`), and in 1 get_men and 1 battle_260 tick-only against interp run; `$2df9e` in 2 of 3 battle_260 tick-only against interp runs (iters 308-310, 335) but 0 of 3 tick-only against tick-only and 0 of 4 interp against interp (`--selfcmp --selfip`); `$1c4e0-$1c546` (pointer save) and `$57fd4` (command highlight) in 1 get_men tick-only against interp run (iters 157, 156); in one map_idle run (all against the first top of a tick) 15 render-scratch ranges (`$3f366-$3f584` vertex tables, `$f1e2`, `$f890`, ...) at one loop top. `state` now pairs the j-th loop top of a tick with the j-th loop top of the same tick in the other run (T top first, then the render-only tops) instead of every top against the first one, and with that and the masks 3 map_idle and 3 get_men runs were IDENTICAL. [INFERENCE] about the cause (the build with offsets is slightly slower, so a top compares a different instant of those latches); the masked ranges are input and screen-scratch state, not world state. The key table and RMB latch masks hide an input byte each; the world tables, the people table, the grid and the RNG are not masked.

## 4. Gates

### 4a. World state (`pminterp.py state SNAP MHZ 700`)
Both runs apply their live image at the first flip (`pmpatch.py live`: `build/live/tk` = tick set, `build/live/ip` = tick set + p3b_interp + p3b_delta), then every loop top (`b pc=$12fd8`, `savebin $0 $60000`) is compared word by word, per world tick, tick-only vs interp (masks above; `$B8xxx` is outside the dump). Negative control: tick k of one run against tick k+1 of the other.
```
get_men    16 MHz: 108 loop tops over 55 ticks IDENTICAL, negative control 111/111     battle_260 16 MHz:  91 over 56 IDENTICAL, neg 97/97
battle_320 16 MHz: 110 over 56 IDENTICAL, neg 112/112                                  battle_290 16 MHz: 103 over 56 IDENTICAL, neg 106/106
map_idle   16 MHz:  76 over 56 IDENTICAL, neg 85/85
get_men     8 MHz:  53 over 53 IDENTICAL, neg 52/52                                    battle_320  8 MHz:  54 over 54 IDENTICAL, neg 51/51
```
(All final code. battle_260 8 MHz was also run before the last edit of the scan gate (`ACTIVE`): 39 over 39 IDENTICAL.) The tops include render-only passes with offsets applied (`NPASS` PD+8 grows), so the people table is restored exactly after every `$f898`, and `$f898` writes no record. RNG `$2df84` is inside the compared range.

### 4b. Tick-pass frames (`pmab.py --only p3b_interp p3b_delta --poke b8a80:0001 --tonly --snapshot ... --mhz 16 --vbls 700`)
```
get_men    @16 MHz: IDENTICAL (back frames matched 55, shown+pointer matched 3, R frames differing (allowed) 55, flips captured 113/113)
battle_260 @16 MHz: IDENTICAL (back frames matched 55, ... R frames differing (allowed) 2)
battle_290 @16 MHz: IDENTICAL (back frames matched 56, ... R frames differing (allowed) 0)
map_idle   @16 MHz: IDENTICAL (back frames matched 55, shown+pointer matched 8, R frames differing (allowed) 0)
```
(the base run carries tick_* and test_walk*; frames matched by (world tick, pass kind), byte for byte.) In battle_260/290 and map_idle nothing that moves is on screen in the 700-VBL window starting at pmab's absolute VBL (the battle is over by then), hence the few differing R frames; the strips (4c) start at the snapshot's own apply flip.
8 MHz, default (no `TOFF`): battle_260 45 of 45 identical, map_idle 30 of 30 identical (no list is ever built), get_men: identical up to tick 166, then `BACK DIFFER key (tick 167, T) ... 142 B differ, rows 98-125, 16-px columns 9-10` (the men), because a render-only pass early in the run (VBL phase) made the gate scan for 8 ticks. [INFERENCE] the early R pass; `rate` below shows `R 0` over 1500 VBL.

### 4c. Frames at 16 MHz (`pminterp.py strip SNAP 16 260 [--tk] [--toff] --png DIR --sheet`)
At every `$11f82` blit with `a3` in the people table the harness logs the sprite's screen (x, y) and at every flip the tick, `RON`, `ACC`, the buffer; camera `$4bb3a/c/$ff9a` is constant in the windows (`camera ... distinct over the window: [(22, 45, 240)]`). Strip images: `work/shots/interp_strip_get_men_16_tk.png` and `..._ip.png` (12 frames each, crop of the village). Position series: section 2.3 (record 9, steady walker: monotonic 103 -> 140 over 26 frames, per tick x moves +3..+5 px split over 2 frames) and, from `--dump`, record 1 / 4 / 6 (stoppers): `T154/2:200,107 R154/14:202,107 T155/1:203,108 R155/13:200,107 T156/0:200,107` (get_men, code before the `ACTIVE` edit; overshoot 3 px for the render-only passes of the tick in which the man stopped, then the true position).

### 4d. Cost and fps
Cycles (`pminterp.py cost`, CycleCounter between breakpoints, pairs split by a VBL interrupt dropped; get_men and battle_260 snapshots, 16 MHz):
```
get_men    ap apply  (entry -> jsr $f898):  R mean 6618 (min 5560 max 7912), T mean 6736;   ap restore: R 1576, T 1628;   NMOV 12..17
get_men    dl scan   (tick passes):          mean 33336 (32268-37796);  R-pass early-out 28 cycles
battle_260 ap apply:  R 11818 (5784-16836), T 11617;   restore R 2688, T 2568;   dl scan mean 38607 (32996-42652);  NMOV 12..24
```
Per mover about 450 cycles to apply + 100 to restore, 52 per record scanned. Whole render stage, `pmab.py` (S1 `$13096` -> flip entry, mean over all passes of the run, tick + render-only, 16 MHz): get_men +20 478 (+1.12 %), battle_260 +19 892 (+1.11 %), battle_290 +18 108 (+1.03 %), map_idle +27 257 (+1.11 %); tick passes only (paired): +1.93 %, +1.93 %, +1.77 %, +1.52 %.
fps over 1500 VBL (`pminterp.py rate`, flips per VBL window, run side by side):
```
get_men    16 MHz: interp 246 flips (8.200)   tick-only 246 (8.200)      8 MHz: 113 (3.767) = 113 (3.767)
battle_260 16 MHz: interp 236 flips (7.867)   tick-only 241 (8.033)      8 MHz: 104 (3.467) = 104 (3.467)
```
World ticks 4.00/s in all of them (`3.999 / 4.028 / 4.001 / 4.028` per 50 VBL). 8 MHz is unchanged (no list is built); at 16 MHz the loss is 0 to 2 % of fps (`battle_260` 5 flips of 241), as large as the ~20 movers there make it.

### 4e. Edge cases (`pminterp.py edge SNAP 16 VBLS KIND --rec 9 --at 5`, a poke when the world tick reaches +AT; `pminterp.py ui`)
* **Man stops** (natural, get_men): the last delta is kept for one tick, the render-only passes draw him up to 3-5 px past where he stops, the next tick's scan drops him from the list and the following frames are the true position (4c, record 1: 202 -> 203 -> 200). Accepted overshoot.
* **Death, angel** (poke `+5 = $fe`, `+6 = $0c`, `+7 = 4`, `+18 = $7e` at tick 154): `T154:116,117 R154:113,119 T155:113,119 R155:113,119 T156:113,119`; after the run `NMOV 15`, record not in the list (the position did not change in the tick of the death, delta 0), record bytes `fe 20 04`, x `$1290`. The angel stands where it was, no drift; its overshoot was the single T154 frame (116 instead of 113).
* **Entering a building / record freed** (poke `+5 = 0`): record not in the list afterwards (`record 9 ... in the mover list: NO`), drawn at a constant `116,117` (the poke leaves it in its cell chain; the real game unlinks it, which removes it from the draw).
* **Teleport** (poke x high byte := `$3f`, a jump of 40 cells): `T154:113,119 R154:117,117 T155:118,116 R155:116,117 R155:116,117 T156:116,117`, record not in the list (|delta| > 56), x `$3fb0` at the end. Same path as a captain teleport, a spawn into a slot and a projectile's landing step.
* **Pause** (`$57ff2` = 1): `ap` calls `$f898` as is and the scan clears the list after 8 passes (`NMOV 0`); [obs] the renderer draws no people while paused (0 records blitted in 80 flips).
* **Query window open** (`pminterp.py ui get_men 16 250 --at 178,103`: Query icon (76,191), then a click that opens the house window "House Name: Barn ... Togbroa & Bllion", `work/shots/interp_query_0.png`/`_2.png`: window up, men moving behind it): `29 loop tops, render passes with offsets 49, scans 33, NMOV 14`, `world ticks with >1 loop top: 9; of those with a people table that differs between the tops: 0`. A person's own window was not opened (the click picked the house; the window code is the same for any object [INFERENCE]).

### 4f. Cold boot (`pmpatch.py build --floppy --out build/interp --only <default set> p3b_interp p3b_delta`, default set = p4_ptr_a p4_ptr_b p4_spr pm_noprot pm_noprot_box pm_tooltip snd_core snd_setup snd_start snd_stop tick_*; `pminterp.py boot`)
```
ste TOS 1.62 1024K: in game after 147 s, MARKER b'PMPO', FLAGS 0x3
  sites: $130aa 4eb9000b8aa0 $130c8 4eb9000b8bc0
  8 MHz set: 170013 cycles/VBL; 936 VBL, fps 3.86, ticks 75 (4.006/s), T 75 R 0 S 3; interp: NMOV 0, render passes with offsets 0, scans 0
  16 MHz set: 320005 cycles/VBL; 936 VBL, fps 8.36, ticks 75 (4.006/s), T 75 R 81 S 0; interp: NMOV 13, render passes with offsets 156, scans 75
megaste TOS 2.06 4096K: in game after 145 s, MARKER b'PMPO', FLAGS 0x3
  sites: $130aa 4eb9000b8aa0 $130c8 4eb9000b8bc0
  8 MHz set: 133339 cycles/VBL; 974 VBL, fps 3.07, ticks 79 (4.055/s), T 77 R 0 S 16; interp: NMOV 0, render passes with offsets 0, scans 0
  16 MHz set: 266675 cycles/VBL; 973 VBL, fps 6.57, ticks 78 (4.008/s), T 77 R 53 S 0; interp: NMOV 10, render passes with offsets 130, scans 78
```
16 MHz is set in both (the cycles per VBL double; the Hatari status bar of `work/shots/interp_cold_megaste4m.png` reads `16MHz(CE)/- 4MB MegaSTE, TOS 2.06`). The Mega STE's cycles per VBL are 133 333 / 266 667 = 8 or 16 MHz / 60: its VBL runs at 60 Hz ("RGB 60 Hz" in the status bar), so the world tick there is 4.8 per second as timing.md section 10 says (the printed `ticks/s` columns divide by 50). Screenshots: `work/shots/interp_cold_ste1m.png`, `interp_cold_megaste4m.png`. Not run: HD build, ST/TT/Falcon.

## 5. Limits / open
* A man crossing a cell edge holds for the rest of the tick and then jumps (<= 7 px, 1 tick in 8 per axis; 2.4). Fix, if wanted: a patch of `sub_011f1a` (`andi.w #$ff` twice) so `d6/d7` may leave 0..255 by up to about 24 units; risks: terrain drawn after the cell paints over the sprite, 16-bit overflow of the blend at the closest zoom. Not built, not tested.
* Stops overshoot by one step for one tick (accepted by the lead); a turn mid-walk draws the old direction for one tick.
* Not extrapolated: angels (1 px/tick), animals (<= 7 units/tick), anything that moves more than 56 units per axis per tick.
* After the last render-only pass the scan keeps running for 8 more ticks (8 x ~33 k cycles, once).
* Tick passes are drawn up to 1.5 steps ahead (cap 384/256); at 8 MHz with a render-only pass early in a scene (get_men) the T frames carry the offset for 8 ticks.
* `pmpatch.py boot` was not extended; the cold boot above is `pminterp.py boot` on `build/interp/floppy/powermonger.st`.
