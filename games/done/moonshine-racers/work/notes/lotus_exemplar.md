# Lotus Esprit Turbo Challenge STE 1.0 (exemplar): what it is, how fast it is, what transfers to Moonshine

Owner: LotusStudy. Machine for every number: Hatari 2.6.1, STE, TOS 1.62, 1 MB, 8.02 MHz (160,256 cycles per VBL), 50 Hz, floppy A: read-only
(`work/lotus/lotus.py`: the harness' Hatari with a wrapper `hatari_flop.sh` that drops `--harddrive/--auto` and adds `--disk-a <exemplar> --protect-floppy on`).
Evidence: disassembly lines come from `tools/m68dis.py` on RAM dumps taken in the race (`work/lotus/dump/*.bin`, git-ignored); cycles from Hatari `profile save`
(`work/lotus/prof/drive8.txt`, 77 frames, 8 MHz), from breakpoint timestamps (`lstages.py`), and from `info blitter` snapshots at the sprite blit entry. Anything not proven is **[INFERENCE]**.
Hatari's blitter model charges the blit's bus time to the instruction that starts it (the `move.b dX,$ff8a3c`-type store), so profile cycles per instruction include blitter time.

## 0. Verdict in one page

1. **It is Gremlin's 1990 Lotus Esprit Turbo Challenge (Shaun Southern, Andrew Morris) with an STE-only re-engineering by Jonathan Thomas** (hi-score table "1st JONATHAN THOMAS"; the loader holds the acrostic "Lots Of The Untapped Software Enhancing STE Potential Restricted Immensely This Therefore Underpowered Racer But Our Code Has Amiga Lovers Looking Ever Nonplussed" = LOTUS ESPRIT TURBO CHALLENGE, loader packed with UPX). The original ST version is **not available locally**: nothing below says what the upgrade changed, only what the upgraded code does. STE/Mega-ST-only parts in the code: **the blitter does all background drawing and the sprites** (about 1,090 blit starts per frame = 35 % of the frame's cycles) and **STE DMA sound** (`$ff8900`, hwscan `crit` lines `$ec15a-$ec274`).
2. **It is fast only because it draws a small view.** One player: the 3D view is **96 of 200 lines** (320 x 96, the other half is a static garage picture); one frame costs **354,125 cycles = 2.21 VBL at 8 MHz** (22-23 fps; 87 % of flips come 2 VBL after the previous one, 12 % after 3, 2 % after 4); at 16 MHz it sits exactly on its **25 fps cap (2.00 VBL)**. Two players (two 96-line views): **674,344 cycles = 4.21 VBL = 12 fps at 8 MHz**. Per displayed 3D line that is 3.7 k (1P, 96 lines) / 3.5 k (2P, 192 lines) cycles against Moonshine's current driving pass of **491 k for ~200 lines = 2.5 k per line** (`hud_build.md` 4b). **Moonshine (default patches) is already cheaper per displayed line than the exemplar**, with the caveat that the contents differ (Lotus: 20 cars on the grid, sampled engine sound, player-car overlay; Moonshine's 200 lines include HUD rows and 24-27 active objects).
3. **No hardware trick makes it cheaper than Moonshine's patched road.** Road = pre-rendered row strips copied per scanline by the blitter with hardware skew (1,078 cycles per road row incl. CPU, geometry extra) against Moonshine `rd_draw` 1,190 cycles per row (+ 710 geometry); horizon = blitter panorama copy, 868 cycles per row against Moonshine's 700 (CPU, four pre-shifted copies). It uses **no STE hardware scroll** (`$ff820d`, `$ff8264/65`: no hits), no STE palette bits, no line doubling; palette splits by Timer B (2.2 per VBL).
4. **The one technique worth measuring is its blitter sprite engine** (separate mask plane, 4 AND + 3-4 OR passes, 8-word HOG blits issued from an unrolled `move.w d1,(a2) / move.b d6,(a6)` chain with persistent registers). I rebuilt it as a microbenchmark and measured it at 8 MHz against Moonshine's stock kernel cost fits: **-33..-40 k cycles per pass on the type-0 kernels if every sprite used it (ideal)**, expected **-17..-30 k (3.5-6 % of 491 k, 0.10-0.19 VBL)** after edge/clip fallbacks. That confirms, and only improves by about 10 k, the earlier blitter study (`sprites.md` section 6: -22..-29 k). It does not by itself reach the 2.7 VBL target (needs -58 k).
5. What would: fewer rows (the Lotus lesson, visible, section 7 item 2: -30..-40 k for ~16 road + 14 horizon rows) plus the exact items the Tight agents are already doing. Nothing in this disk is a free lunch.

## 1. What the file is (verified)

- 819,200 B, 80 tracks x 10 sectors x 2 sides, FAT12 (`work/lotus/fatx.py` lists/extracts; extracted data in git-ignored `alt/lotus/disk/`). Boot sector is executable (checksum $1234) but only blanks the palette and returns (`$1e: moveq #$0,d0 / lea.l $8240.w,a0 / move.l d0,(a0)+ ...`). Files: `AUTO\LOADER.PRG` 19,124 B, `0X80000.LZ4` 147,784 B (-> 446,562 B), `CARS.LZ4` 32,132 B (-> 61,800), `SAMPLES.LZ4` 31,908 B (-> 51,609), 57 `FILExx.SCR` screens (intro/menus pictures). `lz4 -d` unpacks the three LZ4 files.
- The game runs from **$70000-$7E000 (main program) and $80000-$ED0E2 (the depacked `0X80000` image: code, road strips, panorama, sprites)**; screens $10100, $17E00, $1FB00. It fills a 1 MB machine; 512 KB is impossible (code at $80000+).
- Boots on **STE, TOS 1.62, 1 MB** (the harness default) with no special options. Intro: car art with animated headlights, "Dimensions"/"Specification" blueprints, title "LOTUS ESPRIT TURBO CHALLENGE", hi-score tables (Easy/Hard), "Game Information" (controls), "Game Options" (difficulty Easy 7 races, **number of players ONE/TWO**, gears, control method), "Select a track", then the race. Navigation recipe: after VBL ~10,000 (use `hatari-option --fast-forward true` for the first 7 s, then off) joystick-1-by-keys: `Control_R` = fire, `Down`/`Right` moved the highlight and set "TWO" players (`shots/m_u.png`). Screenshots: `work/lotus/shots/` (`title.png`, `m_b` hi-scores, `m_c` game information, `m_d` options/track select, `m_u` two-player option, `m_w`/`m_e` race entry, `race_1p_grid/driving.png`, `race_2p_grid/driving.png`, `sheet_overview.png`).
- hwscan of the race RAM (`work/lotus/hwscan_race1.txt`, range $400-$100000): VBL/Timer B/IKBD vectors, FDC (own disk routines `$708fa-$70918`), YM2149, **STE DMA sound crit lines**, blitter reached through `lea.l $8a38.w,aN` style pointers (not listed by hwscan; found by byte search: `$7948a`, `$794ba`, `$80200-$80240`, `$c6f2e-$c6f3a`, `$ece08`). No `$ff820d/$ff8264/$ff8265`, no `$ff9200`, no STE palette LSBs (`m $ff8240`: values 0-7 per nibble only).

## 2. Screen mode, layout, raster

- ST low res 320x200, 4 planes, 16 colours. **Split screen**: rows 0-95 view 1, rows 96-103 black gap, rows 104-199 view 2 (`shots/race_2p_grid.png`). In one-player mode view 2 is a static garage picture with an animated pit crew (costs 23 k per frame, section 4). HUD (GEAR/MPH/RPM/FUEL/POS) is drawn into the right side of each view.
- **Triple buffer**: `m $7d40a` = `00010100 00017e00 0001fb00`; the flip is in the VBL handler: `$755f6: move.b d0,$8201.w / $755fe: move.b d0,$8203.w`, buffer index `$7c540` cycles 0,1,2 (`$7566c`). The palette load and the first Timer B arm are in the same handler chain (`$70586`, `$7059a`).
- **Raster**: the VBL routine loads a palette (`$70586: lea.l $8240.w,a1` + 8 x `move.l (a0)+,(a1)+`), arms Timer B with `move.b #$c8,$fa21.w` (first split) and every Timer B routine (`$70684`, `$70790`, `$706c0`, `$70754`, `$708ce`, `$c7722`) rewrites a few colours (`$70692: lea.l $8258.w,a1` + 2 `move.l`) and re-arms the next split (`move.b #$39,$fa21.w`). Profile: **170 Timer B entries in 77 frames = 2.2 per VBL**, ISR code (VBL + IKBD + Timer B) 4.4 k cycles per frame. Banding of sky/ground is palette, not pixels.

## 3. Frame rate and pacing (measured)

Flip = execution of `$755f6` (`b pc = $755f6 :trace`, count over a VBL window; joystick up forced by `w $70569 $01`; script `work/lotus/flipint.py`, raw `work/lotus/prof/flipint_*.txt`):

| scene | clock | flips / VBL | VBL per flip | fps | intervals (VBL: count) |
|---|---|---:|---:|---:|---|
| 1 player, driving | 8 MHz | 234 flips (about 10 s) | **2.15** | 23.3 | 2: 202, 3: 27, 4: 4 |
| 1 player, driving, count windows | 8 MHz | 113 and 118 in 250 VBL | 2.12-2.21 | 22.6-23.6 | |
| 1 player, standing grid | 8 MHz | 82 in 200 VBL | 2.44 | 20.5 | |
| 1 player | **16 MHz** | 125 in 250 VBL; 250 flips | **2.00** | 25.0 | 2: 249 |
| 2 players (both driving) | 8 MHz | 63 in 250 VBL; 119 flips | **3.97-4.19** | 12.0-12.6 | 2: 1, 3: 5, 4: 86, 5: 23, 6: 3 |
| 2 players | 16 MHz | 248 flips | 2.02 | 24.8 | 2: 243, 3: 4 |

- **2-VBL floor**: `sub_07631c: move.w $7c542.l,d0 / sub.w $7c544.l,d0 / cmp.w #$2,d0 / bpl` (wait until at least 2 VBLs since the last frame start, `$7c542` = VBL counter incremented in `$7554e`/`$755aa: addq.w #$1,$7c542.l`). Maximum 25 fps. At 8 MHz one player the game sits on that floor (frame period min 308 k, mean 346 k cycles incl. the slips) and slips to 3 or 4 VBL on 14 % of frames.
- **World speed does not depend on frame rate**: position `$7c596` advances 420 / 425 units per VBL at 8 / 16 MHz (`work/lotus` session, same start state, +Up: (123 -> 463 VBL) 8503453 -> 8646253 vs 8551053 -> 8695553). The stamp ring `$7d3bc` (8 words) and the elapsed-VBL delta (`$7631c`..`$763fa`) feed the time step **[INFERENCE: code read, not every use traced]**.
- Moonshine comparison: stock 6.0 VBL (8.3 fps) driving; now 3.06 VBL per pass. Lotus 1P at 2.2 VBL draws less than half the lines; Lotus 2P at 4.2 VBL is slower than Moonshine's pass for the same number of lines.

## 4. Where the cycles go (8 MHz, one player, driving; `lprof.py`, `lstages.py`)

Stage times between breakpoints on the return addresses of the frame body `$76440-$765fa` (`work/lotus/prof/stages_drive8.txt` 1P, `stages_drive2p.txt` 2P; interrupts included in the stage they hit, as `msrstages.py`):

| stage (call in the frame body) | what it does | 1P cycles | 2P view 1 / view 2 |
|---|---|---:|---:|
| `78a60` (+copies, `$76378..$76576`) | road geometry: second-order integration over 96 slices | 31,818 | 33,359 / 33,007 |
| `78f3a` | slices -> per-scanline records (hill interpolation) | 19,587 | 20,481 / 19,542 |
| `765fe` | **road: per scanline blits** (57 lines) | 75,001 | 80,937 / 79,119 |
| `79170` (view 2: `79180`) | **sky fill + mountain panorama blits** (8 + 31 rows) + HUD word copies | 38,460 | 33,608 / 34,258 |
| `796fa` (view 2: `79ab2`) | opponents' logic, sort of 4 lists, **sprites** | 100,739 | 124,303 / 112,510 |
| `790e6` (view 2: `790f6`) | **player car / overlay masked blits** (`jmp $ece08`) | 46,474 | 44,986 / 48,748 |
| `7a64c`, `78a04`, `7902e`, `78a2a` | small | 4,874 | 4,711 / 4,468 |
| `79180` in 1P | garage picture animation (pit crew words) | 23,064 | (view 2 is a real view) |
| idle wait `$7631c` | spin until 2 VBLs | 6,344 | 222 |
| **period** | | **346,389 (2.16 VBL)** | **674,344 (4.21 VBL)** |

Instruction-level profile (`profile save`, 77 frames, 27,267,592 cycles = 354,125 per frame; regions by disassembly, `work/lotus/prof/drive8.txt`):

| region | cycles/frame | share |
|---|---:|---:|
| road per-line blits + table lookups (`$76640-$76754`; `muls.w d3,d1` at `$7668a` runs 4,389 times = 57.0 lines per frame) | 61,461 | 17.4 % |
| sprite blit chains + per-sprite setup (`$c6f28-$c70dc`, `$c7300-$c7402`, `$c747a`; 806 sprite draws = 10.5 per frame) | 59,757 | 16.9 % |
| player car / overlay blits (`$ece08-$ed0ff`, 226 blit starts per frame) | 36,584 | 10.3 % |
| object sorting, projection, sprite preparation (`$796fa-$7a64c`) | 31,190 | 8.8 % |
| horizon panorama blits + sky fill (`$793e6-$795ef`; 124 blit starts = 31 rows x 4) | 26,895 | 7.6 % |
| road geometry, slice integration (`$78a98-$78f3a`) | 25,185 | 7.1 % |
| engine-sound resampler for DMA sound (`$ec14a-$ece08`, 2.2 calls per frame = once per VBL) | 22,537 | 6.4 % |
| frame control, physics, flip, state copies (`$75500-$76640`) | 22,393 | 6.3 % |
| opponent cars (19) position/AI (`$795f2-$796fa`) | 22,482 | 6.3 % |
| road geometry, slices to lines (`$78f3a-$7910e`) | 16,804 | 4.7 % |
| HUD / garage word copies (`$79280-$79340`) | 15,999 | 4.5 % |
| VBL + Timer B + IKBD ISR | 4,407 | 1.2 % |
| rest | 8,432 | 2.4 % |

- **Blit starts per frame** (profile counts of the start stores): road 228 (57 lines x 4), horizon 124, sprites 512 (chain), car/overlay 226: **~1,090 per frame, 123 k cycles = 35 % of the frame** (road 36.4 k, horizon 19.8 k, sprites 38.0 k, car 28.9 k).
- Bytes: the whole view is rewritten every frame, 96 rows x 160 B = 15,360 B (sky 8 + horizon 31 + road 57 rows), plus about 4,100 blitted words per frame for the sprites (512 chain blits of ~8 words).
- Fully idle time is only 4.6-6.3 k (1.3-1.8 %): the game is CPU-bound at 8 MHz even with the blitter.

## 5. How each part is drawn (evidence)

### 5.1 Road: pre-rendered row strips + one 4-blit copy per scanline, hardware skew
```
076672:  361c        move.w (a4)+,d3        ; per-line records from $78f3a (curve offset, y, ...)
07667a:  0642058f    addi.w #$58f,d2
076686:  0643fcb0    addi.w #$fcb0,d3 / 07668a: c3c3 muls.w d3,d1 / 07668c: swap d1   ; one muls per line
076694:  c63c000f    and.b #$f,d3           ; low nibble of the horizontal offset = blitter skew
0766ca:  2c300000    move.l (a0,d0.w),d6    ; pointer to the pre-rendered strip for this line / lateral position
0766d4:  2686        move.l d6,(a3)  / 0766d6: 21c98a32 move.l a1,$8a32.w  ; src, dst
0766da:  3a85 move.w d5,(a5)  (ycount = 1)   / 0766dc: 3c83 move.w d3,(a6) ; control: $c080|skew = start + HOG + NFSR
0766de:  34bc000f    move.w #$f,(a2)        ; HOP 0 / LOP $f = fill with ones (plane 1)
0766e6:  34bc0203    move.w #$203,(a2)      ; HOP 2 (source) / LOP 3 (copy) for the other planes
```
- `$80200` (called once per frame at `$7666c`) programs the constant registers: src xinc 8, yinc `$ff62`, dest xinc 8, yinc `$ff6a`, xcount `$14` = 20 words, endmasks `$ffff`: **one blit = one bitplane of one 320-pixel scanline**; 4 blits per scanline (3 copies from the strip + 1 fill with ones; a variant swaps which plane is filled). Profile: copy 181 cycles (20 words, 9.0 per word), fill 97.
- **Data**: table `$8024c` has 400 long pointers into `$8124c-$9b06c` (106,016 B); steps 192 B rising to 376 B per entry (`work/lotus` analysis): each entry is a **pre-rendered 24-47 group strip (384-750 px) of one road scanline** (grass `8`, road `d`, kerbs `6`, lane dashes), wider than the screen so the curve offset is a whole-word pointer shift plus the 0-15 px blitter skew. 20 depth classes x ~20 variants (stripe phase, lateral position) **[INFERENCE for the exact index meaning; the pointer table, strip pixels and `d0 = (pos >> 2) & $3fc` index are read from the dump]**.
- Cost per road line: 1,078 cycles (61,461 / 57), of which blit 640, CPU 438; geometry is separate: 25.2 k + 16.8 k + copies for 96 slices (`$78a98`: 8 adds + one `muls.w d3,d6` + two table reads per slice, unrolled x 96) = about 530 cycles per slice.
- **Why Moonshine cannot copy it**: the strip is chosen from (line depth, stripe phase, lateral offset) because the road width per line is fixed by perspective. Moonshine's width comes from per-position profile tables (`road.md` section 2: 445 distinct (w0, A-B) pairs in 240 frames), so there is no finite set of strips.

### 5.2 Horizon: a 3-plane panorama copied with the blitter skew
```
07948e:  3afc0006    move.w #$6,(a5)+        ; src xinc 6 = 3 planes per 16 px
0794ca:  21c98a24    move.l a1,$8a24.w       ; src = panorama row; 0794c8: 2488 move.l a0,(a2)  dst = screen row
0794d0:  1a85 move.b d5,(a5) ... 4 start stores per row (copy, copy, fill with ones, copy), HOP/LOP switched between them
0794e6:  43e901e0    lea.l $1e0(a1),a1       ; next panorama row (pitch 480 B; screen pitch 160 B)
```
31 mountain rows (`$7c546+$5e = 31` in the dump) x 4 blits (124 per frame) + 8 sky rows by `movem.l d0-d5/a0-a3,-(a4)` fills (`$795da`). Source = `$27800`, 480 B per row = 80 groups x 6 B = 1280 px of 3-plane data (rendered `work/lotus/shots/pano3.png`: the mountain picture repeats roughly every 320 px, 83 % of the bytes equal at a 120 B offset); the 4th plane is the fill pass. The word offset comes from the source pointer, 0-15 px from the skew, so **1-pixel scroll resolution without STE hardware scroll**. Cost 868 cycles per row (26.9 k / 31) against Moonshine's 700 per row (38.7 k driving / 55 rows, CPU `movem` from four pre-shifted copies, 4-pixel steps).

### 5.3 Sprites: mask + planes, blitter, chained 8-word HOG blits
`info blitter` at `$c70a0` (the entry of every sprite draw; 209 draws logged, `work/lotus/prof/blit_sprite_trace.txt`):
```
x count 2 | src X-inc 10, Y-inc 10 | dst X-inc 8, Y-inc 152 | HOP 02 LOP 01 | endmask1 07ff, 2 ffff, 3 f800 | skew 45 | control 0f
```
- Source = interleaved **[mask, plane0, plane1, plane2(, plane3)]** per word (xinc 8 for 3 planes, 10 for 4: `cmp.w #$a,d5` decides the 4th OR pass); destination xinc 8 (next 16 pixels of one plane), yinc = 160 - 8 (n-1). Pass list (`$c70a0-$c70d4`): **4 AND passes** (`move.w #$201,$8a3a.w`, same mask source for the four dest planes: `bsr $c70d8` with `addq.l #$2,a1` between) then **3-4 OR passes** (`move.w #$207,$8a3a.w`, `addq.l #$2,a0 / a1`). 7.4 passes per sprite on average (5,960 `$c70d8` entries / 806 draws).
- Distribution of the 209 logged draws (1 s of race): xcount 2 (a 16-px column plus the shift spill word) **146**, 5: 24, 3: 19, 1: 12, 4: 7, 6: 1; 4-plane (`d5 = 10`) 158, 3-plane (`d5 = 8`) 51. Sprites are drawn at any x with `skew` (shift) + endmasks from tables (`$c7404`/`$c7424`); they are pre-scaled bitmaps chosen from tables (`$7a0d8: lea.l $7024c.l,a1 / movea.l (a1,d6.w),a1`), not pre-shifted (the shift is the blitter's), like Moonshine whose sprites are pre-scaled but shifted at draw time.
- **Burst policy**: `move.b #$c0,d6` = start + **HOG**, no non-HOG, no BUSY polling. The blit size is held near **8 words** whatever the width: `d1` (ycount per blit) = 8 / 4 / 2 / 1 for xcount 1 / 2 / 3 / 4+ (`$c6ffa..$c708a: moveq #$8,d1 / #$4 / #$2 / #$1`), so a sprite is a chain of tiny ~65-cycle blits (`$c7400: move.b d6,(a6)` averages 64.8 cycles). **The registers persist: each chain element is `move.w d1,(a2)` (ycount) + `move.b d6,(a6)` (start) = 16 CPU cycles per blit**; source/dest addresses and endmasks are programmed once per pass **[INFERENCE: the chain relies on the blitter's address registers advancing to the next rows after each blit; the code never reloads them between chain elements]**. The entry point into the unrolled chain (`$c7300-$c7402`, one pair = 4 bytes) is computed from the height (`move.w d1,$c70de.l`, self-modified). Timer B / VBL interrupts can be taken between blits (SR `$2300` at the sprite entry): the worst blit is a 20-word line blit of the background (181 cycles), not a whole sprite.
- Per sprite: 5.7 k cycles (59.8 k / 10.5) of which CPU setup 1.1 k (`$c6f28-$c70d6`), chain pairs 0.78 k, blitter 3.8 k; plus 3.0 k sorting/projection/prep per sprite (31.2 k / 10.5 of `$796fa-$7a64c`, which also serves the 19 opponents). 100.7 k for the 1P object stage vs Moonshine's 211-227 k with 15-17 type-0 calls and 6-8 composites.
- The **player car / overlay** (stage `790e6`, `jmp $ece08`, 46 k = 13 % of the frame) is the same AND/OR blit scheme with xcount 1 column strips (`$ece66`: 5 pairs x 4 AND passes + OR passes, 226 blit starts). Moonshine's player car + second layer cost 35 k + 22 k = 57 k (`sprites.md` T1).

### 5.4 Sound and the rest
- **Sampled engine sound on STE DMA** (`$ec14a`, 22.5 k cycles per frame = 6.4 %): once per VBL a **CPU resampler** fills the DMA buffer by pitch stepping an engine sample (`$ec2ac: move.b (a0,d0.w),(a2)+ / addx.l d1,d0`, step from RPM `$7cc3c`); `SAMPLES.LZ4` 51,609 B. Moonshine uses the YM2149 (cheap): this is an anti-transfer.
- Opponents (`$795f2-$796fa`, 19 opponents: `move.w $7cc72.l,d7` loop count, `$7cc72` = 19 in the 1P dump and 18 in the 2P dump, i.e. 20 cars with the player(s); `$7c6b2` records): 22.5 k per frame; the hottest single instruction of the whole profile is `$79662: divu.w $7ca9a.l,d0` (41 executions per frame, 469,604 cycles over 77 frames = 6.1 k per frame).
- Input via IKBD ACIA (`$7044c`), FDC reads by own routines (`$708fa`).

## 6. Microbenchmark of the Lotus sprite formulation (my own code, 8 MHz, `work/lotus/bench/`)

`lbs.s` (first cut) and `lbs2.s` (table-driven setup, no `mulu/divu`) implement the formulation of 5.3 and run in a plain TOS desktop Hatari (STE, 1 MB, 8.02 MHz, interrupts masked, `run_lbs.py`, markers `m_case`/`m_end` timestamped with `e CycleCounter`, 8 calls per case, raw `bench/res_*.txt`, `bench/last_log.txt`). Source: random words (timing is data independent); 3 planes (nibble 7) unless noted; 4 AND + 3 OR passes; HOG; blit size about 8 words; unrolled pair chain.

Cycles per call (lbs2):

| columns | rows | Lotus-form shifted (x&15 = 4 or 7) | Lotus-form aligned (x&15 = 0) | Moonshine stock kernel, shifted / aligned (harness values `res_stock_matrix.txt` where marked h; else the fit `a + b*rows` of `sprites.md` T4) |
|---|---:|---:|---:|---|
| 1 | 10 | 3,745 | 2,993 | 3,760 / 1,692 (h) |
| 1 | 16 | 4,781 | 3,525 | 5,841 / 2,629 (fit) |
| 1 | 30 | 7,385 | 5,009 | 10,517 / 4,561 (fit) |
| 2 | 10 | 4,941 | 4,001 | 5,969 / 2,997 (fit) |
| 2 | 16 | 6,789 | 5,205 | 9,204 / 4,472 (h) |
| 2 | 30 | 11,101 | 8,201 | 16,449 / 7,697 (fit) |
| 3 | 16 | 9,477 | 7,213 | 12,792 / 6,508 (h) |
| 4 | 16 | 10,821 | 9,901 | 16,572 / 8,368 (h) |
| 4 | 30 | 18,661 | 16,957 | 29,263 (fit) / n.a. |
| 2 (4 planes, nibble 15) | 16 | 7,629 | | 10,932 / 5,428 (h) |

- Marginal cost = 12 cycles per word per pass as the blitter model (`sprites.md` section 6: 11.4 per word) plus the chain pair: 173-182 / 308 / 476 / 560 cycles per row for 1 / 2 / 3 / 4 columns (words per row n = 2, 3, 4, 5; one blit per row for n >= 4). **Fixed cost per sprite about 2.0-2.1 k cycles in my implementation (1x1 call = 2,149)**, comparable with the exemplar's measured 1.1 k setup + 0.8 k chain pairs per sprite + per-blit start latency. This fixed cost is why small and aligned sprites do not gain (break-even about 10-12 rows for one column; **aligned sprites are slower than the stock kernel: 1.18 x at 4 columns, 1.16 x at 2 columns, 1.77 x at 1 column 10 rows**).
- First-cut `lbs.s` (with `mulu`/`divu`) had 2.3 k fixed cost: the table-driven setup saves only 0.2 k, the pass loop (7 x ~150 cycles) is the floor.
- **Estimate for Moonshine** (per pass, type-0 kernels only): Moonshine's trace tables T2 (`sprites.md`, per scene calls per frame x mean rows x mean cycles per call) against this table (linear interpolation in rows, aligned/shifted separately, Lotus-form = blit every sprite, hybrid = cheaper of the two per class):

| scene | stock type-0 kernels | Lotus-form all | hybrid | saving all / hybrid |
|---|---:|---:|---:|---:|
| race_grid | 155.8 k | 122.6 k | 119.5 k | 33.2 k / 36.3 k |
| race_start | 154.8 k | 115.0 k | 114.3 k | 39.9 k / 40.5 k |
| race_up | 159.2 k | 122.3 k | 121.7 k | 36.9 k / 37.4 k |
| race_drive | 139.2 k | 106.3 k | 105.9 k | 32.8 k / 33.2 k |

  = **-33..-40 k per pass (7-8 % of a 491 k pass, 0.21-0.25 VBL) ideal**. Realisation factor from the earlier blitter study (their microbench ratio 0.73 for 2 columns, real frames -12.9 % of type-0 draws, because of interior-only fallback to the stock kernel, composite types 1/3 not covered, aligned sprites) 50-75 % -> **-17..-30 k (0.10-0.19 VBL)**. Not counted: composites (type 1/3, 45-53 k). The player's two layers are the 4-column rows of T2 (35 k + 22 k stock at 34-36 and 21 rows -> about 21.5 k + 13.6 k Lotus-form by the 4-column marginal of 560 per row), i.e. about -22 k of the saving, so the estimate depends on those two sprites more than on the rest.
- Costs and risks of the format: the Lotus data needs a precomputed mask word per source word (+33 % for 3-plane data, +25 % for 4-plane) and Lotus also stores the shift-spill word (xinc 10 and xcount 2 for a 1-column sprite; my `lbs2.s` avoids it with a zero source yinc): **Moonshine's 154 KB of bitmap banks would grow to about 205 KB with masks only and up to about 300 KB with spill words**, against 215 KB free at 1 MB of which `rd_geom/rd_draw` already use 96 KB (`$D0000-$E7FFF`, `road.md` 6.1/6.2), i.e. about 119 KB left (`rendering.md` section 3). So at 1 MB only a run-time mask build (3 extra cheap passes, which the earlier prototype pays) or a per-level subset of the banks fits; at 4 MB there is no space problem.
- Limits of the measurement: Hatari's blitter model (4 cycles per bus access, no video-DMA contention modelled), interrupts masked in my harness, no clipping, no composite types, no real frames. The microbench ratio at 2 columns (0.73) agrees with the earlier prototype (`sprites.md` table: 0.73), which is the only cross-check.

## 7. Transferable techniques for Moonshine, ranked (STE 8 MHz, cycles per 491 k pass)

| # | technique | evidence it exists in the exemplar | Moonshine today | STE-only? | est. gain per pass (basis) | risk | verdict |
|---|---|---|---|---|---|---|---|
| 1 | **Blitter sprites, Lotus-form**: mask plane stored with the planes, 4 AND + 3-4 OR passes, HOG blits of ~8 words from an unrolled `move.w d1,(a2)/move.b d6,(a6)` chain, persistent registers | `$c6f2c-$c7402`, `info blitter` (5.3); 10.5 sprites per frame at 5.7 k each | CPU kernels `$12000-$16000`, 153-159 k for type-0 per pass | **yes** (blitter: STE, Mega ST; not ST/TT/Falcon; Mega STE 16 MHz: CPU path is faster, probe needed) | **-33..-40 k ideal, -17..-30 k expected** (section 6, 4 scenes) | **high**: new data format or run-time mask, clip fallback, composites, HOG vs IKBD (the exemplar keeps bursts <= 181 cycles), plain ST path remains | only identified sprite lever; it matches `sprites.md` option (e); worth doing only if the user wants the extra 0.1-0.2 VBL on the STE |
| 2 | **Fewer rows drawn** (the exemplar's real speed secret: 96 view rows of 200, road 57 rows, horizon 31) | 1P frame 354 k for 96 rows | road 80 rows x (1.19 k draw + 0.71 k geometry), horizon 55 rows x 0.7 k | no | each removed road row about -1.9 k, each horizon row -0.7 k: **16 road + 14 horizon rows = -40 k** (`road.md` 6.1/6.2 costs per row) | low technically; **visible change, needs user approval** | the only lever of the size needed; not a Lotus technique but the Lotus lesson |
| 3 | Blitter horizon scroll with 1-pixel steps (3-plane panorama 1280 px wide + skew) | 5.2: 31 rows x 4 blits | 4-px steps, CPU `movem` from 4 pre-shifted copies, 700 c/row | yes | **+5..+10 k (slower)** (868 vs 700 c/row) | medium | reject for speed; only for smoothness |
| 4 | Pre-rendered road strips + blitter skew (template rows) | `$8024c`, 400 strips, 106 KB | `rd_draw` compiled spans + edge windows | yes | **about 0** (1,078 vs 1,190 c/row; geometry unchanged) | very high: needs fixed road width | reject (road.md section 2 premise confirmed false for Moonshine) |
| 5 | Incremental 2nd-order road geometry (8 adds + 1 `muls` per slice, unrolled) | `$78a98-$78b3c` | `rd_geom` 710 c/slice | no | **about 0** (Lotus 530 c/slice incl. slice->line pass) | high (different road model) | reject |
| 6 | Few raster splits (2.2 Timer B per VBL) | 170 entries / 77 frames = 2.2 per VBL; VBL + Timer B + IKBD ISR 4.4 k per frame = 2.0 k per VBL | about 8 per VBL (41-47 per 5-6 VBL frame), Timer B ISR 12-14 k per 5-6 VBL = 2.4 k per VBL (`rendering.md` section 5) | no | **none**: per VBL the two ISR bills are equal (2.0 vs 2.4 k) | | reject |
| 7 | Triple buffering with VBL-ISR flip, time-stamped schedule, time-based world | `$755f6`, `$7d3bc`, 3-buffer index `$7c540` | double buffer + `mt/mx` pacing (fixed tick) | no | 0 cycles (pacing only) | | already covered by the tick/extra-frame design (same 2-VBL granularity idea) |
| 8 | CPU-resampled DMA engine sound | `$ec14a`, 22.5 k per frame = 10.2 k per VBL | YM2149 player 18.8-21.8 k per 5-6 VBL = 3.6 k per VBL (`rendering.md` section 5) | yes | **cost, not gain: about +6.6 k per VBL, +20 k per 3-VBL pass** | | do not adopt |
| 9 | Short HOG blits as raster/IKBD policy (<= 8 words sprites, 20 words per line) | 5.3, SR `$2300` in the sprite entry | prototype BUDGET 1,800 cycles per blit (`msb.s`) | yes | 0, but needed for #1 (Timer B jitter <= 181 cycles instead of 1,800) | | take as a design rule for #1 |

Visual compromises seen in the exemplar: 96-line views (the whole point), road made of pre-rendered strips (fixed width, no per-position width changes), pre-scaled sprites with up to 9 size steps per object kind (clamp `cmp.w #$8,d6 / moveq #$8,d6` at `$7a258`, **[INFERENCE]** that d6 is the scale step) drawn with 3-4 colour planes, palette banding by Timer B for sky/ground (9-bit ST colours only, 16 colours), 4-VBL frames in two-player mode (12 fps), sampled sound at a 6 % CPU price.

## 8. Unproven / caveats

- No stock (original ST) build is available: "what the STE upgrade changed" is `[INFERENCE]`; I did not test the disk on an ST or Mega ST (hwscan crit lines say DMA sound would bus-error; the blitter registers would bus-error on a plain ST).
- Hatari only (8.02 MHz model; the blitter model does not include video DMA contention); no real-hardware frame rate. The 16 MHz run uses Hatari's `--cpuclock 16`, which keeps bus-bound work at 8 MHz cost (`road.md` section 4), so 25.0 fps there is the cap, not a measure of speed.
- The road strip index and the stamp ring semantics are read from code and dumps, not fully traced. Sprite size/frame choice (`$7a0d8`) was read only far enough to confirm table-driven pre-scaled bitmaps (`lea $7024c / movea.l (a1,d6.w),a1`).
- The microbench uses random source data and no clipping; per-frame cycles for Moonshine are projections from its trace tables, not a patched run. Realisation factors are taken from the earlier study, not measured here.
- 2P figures use a standing start grid with 20 cars; Moonshine figures are the default-patch driving pass (`hud_build.md` 4b).

## 9. Files (`work/lotus/`)

`lotus.py` (harness), `hatari_flop.sh`, `fatx.py` (FAT12 lister/extractor), `lprof.py` (call tree/bucket from a Hatari profile), `lstages.py` / `run2p.py` (per-stage cycles), `flipint.py` (flip intervals), `mont.py`, `hwscan_race1.txt`, `prof/` (`drive8.txt` profile, `stages_*.txt` + `.rawlog`, `flipint_*.txt`, `blit_sprite_trace.txt`), `bench/` (`lbs.s`, `lbs2.s`, `run_lbs.py`, `res_*.txt`), `shots/`, `race1.sav`/`race2p.sav` (1 MB STE snapshots at race start, 1P and 2P; git-ignored), `dump/*.bin` (git-ignored). Extracted disk data: `alt/lotus/disk/` (git-ignored).
