# Powermonger hot paths, second pass (PMPerf2): what holds it back NOW, and what was built

Setup: 1 MB STE, TOS 1.62, Hatari 2.6.1, the CURRENT default patch set (tick_*, snd_*, p4_ptr_a/b, p4_spr, pm_noprot*, pm_tooltip, p3b_interp, p3b_delta) applied live on
`work/snapshots/{map_idle,get_men,battle_320}.sav` at the next loop top, 60 VBL warm-up, then 300 VBL profiled (`tools/pmprof2.py run SNAP MHZ [--add p6_slope p6_tri]`;
Hatari `profile save` = per-address instruction counts and cycles; tag `b2` = baseline, `n2` = with the new patches, `*s` = with the CycleCounter stage trace; files `work/prof2/*.txt|*.stages.json`).
Tables: `tools/pmtop10.py` (named routines), `tools/pmrep2.py` (clusters of executed addresses). A "pass" in the top-10 tables = one entry of the window copy (render-only R passes of p3b_interp included).
Evidence = raw tool output; `[INFERENCE]` = not run. Every cycle figure is Hatari's.

## 0. Result

| | before (current defaults) | after p6_slope + p6_tri | after + p6_cpy |
|---|---|---|---|
| map_idle 8 MHz | 2.769 fps, 2 766 862 cycles/pass | 3.214 fps (+16.0 %), -13.73 % cycles | 3.394 fps (+22.6 % total), a further -5.04 % |
| get_men 8 MHz | 4.519 fps, 1 689 415 | 5.185 fps (+14.8 %), -13.22 % | 5.399 fps (+19.5 % total), a further -3.95 % |
| battle_320 8 MHz | 4.552 fps, 1 679 215 | 5.213 fps (+14.5 %), -13.34 % | 5.490 fps (+20.6 % total), a further -3.97 % |
| map_idle 16 MHz | 7.205 fps | 8.261 fps (+14.7 %), -13.97 % | 8.406 fps (+16.7 % total), a further -3.62 % |
| get_men 16 MHz | 9.334 fps | 10.174 fps (+9.0 %), -12.68 % | 10.492 fps (+12.4 % total), a further -2.85 % |
| battle_320 16 MHz | 9.913 fps | 11.354 fps (+14.5 %), -13.83 % | 11.443 fps (+15.4 % total), a further -2.74 % |

All rows pixel-identical by `tools/pmab.py` (raw lines in section 6). Cold boots of one floppy with the whole default set + p6_slope + p6_tri + p6_cpy
(`build/p6/floppy/powermonger.st`): STE 1 MB / TOS 1.62 and ST 1 MB / TOS 1.04 both reach the 3D view (`BOOT OK ... MARKER=b'PMPO'`; STE FLAGS 0x3 with `$bdc04 = b17e0001` = blitter chosen,
ST FLAGS 0x6 with `b17e0002` = pre-shifted sprite cache), blobs at `$d9012` / `$da000` present; screenshots `work/shots/perf2/cold_ste/`, `cold_st/`. `build --hd` with the new patches assembles (HD boot not run).

## 1. Frame split by stage (8 MHz and 16 MHz; CycleCounter at the main-loop call sites, interrupts count in the stage they hit)

Per loop pass, share of the cycles in the window (T, S and R passes mixed; the "rest" column also holds the tick glue and the cost of S passes, so it is noisy):

| scene | landscape + objects `$f898` | window copy `$12ce0` | VBL wait `$1870` | rest (logic, HUD, UI, men sim, tooltip, tick glue) |
|---|---:|---:|---:|---:|
| map_idle 8 MHz, before | 67.6 % | 7.7 % | 3.5 % | 21.1 % |
| get_men 8 MHz, before | 61.0 % | 9.2 % | 5.4 % | 24.5 % |
| battle_320 8 MHz, before | 62.6 % | 12.1 % | 4.8 % | 20.5 % |
| get_men 16 MHz, before | 64.2 % | 10.4 % | 7.2 % | 18.2 % |
| get_men 8 MHz, after p6_slope + p6_tri | 61.1 % (983 923 cycles per rendered pass instead of 1 156 913) | 10.4 % | 5.7 % | 22.7 % |

The landscape share stays near 61-64 % because everything else gets a bigger share of a shorter pass; its absolute cost fell by 15 %.
The function-level profile (next section) is the better view: terrain setup + fill = 50-56 % of all cycles before, 46-51 % after.

## 2. Top 10 functions by exclusive cycles, BEFORE (current defaults, `*_b2.txt`)

get_men 8 MHz:
work/prof2/get_men_8_b2: 43248364 cycles, 25 rendered passes, 1729935 cycles/pass
| # | function | share % | cycles/pass | calls/pass | cycles/call | role |
|---|---|---:|---:|---:|---:|---|
| 1 | terrain span fill (orig) | 40.6 | 702456 | 127.4 | 5514 | masked 4-plane span fill of one triangle |
| 2 | triangle setup (orig) | 10.0 | 173615 | 127.4 | 1363 | clip tests, sort, 3-7 divu, record for the fill |
| 3 | window copy | 9.4 | 162976 | 1.0 | 162976 | 32000 B picture -> back buffer |
| 4 | sprite blit (p4_spr) | 7.3 | 126499 | 18.0 | 7012 | masked sprite, blitter / pre-shifted cache |
| 5 | VBL wait | 6.9 | 119947 | 2936.8 | 41 | idle spin until the VBL flag |
| 6 | small sprites (8 px) | 4.1 | 70772 | 17.5 | 4049 | SPRITE8 objects, rol/ror per row |
| 7 | cell loop | 2.7 | 46247 | 1.0 | 46247 | per cell: 2 triangles, objects |
| 8 | sound (snd_ DMA resampler) | 2.4 | 41139 | 10.8 | 3823 | STE DMA sound producer |
| 9 | army/people lists | 2.3 | 40602 | 39.5 | 1027 | move person between cell chains |
| 10 | men interp (p3b) | 2.1 | 36306 | 0.0 | 907652 | predict-ahead men positions |
| | rest (HUD, UI, logic, interrupts, ...) | 3.6 | 61565 | | | |

battle_320 8 MHz:
work/prof2/battle_320_8_b2: 43406048 cycles, 25 rendered passes, 1736242 cycles/pass
| # | function | share % | cycles/pass | calls/pass | cycles/call | role |
|---|---|---:|---:|---:|---:|---|
| 1 | terrain span fill (orig) | 40.7 | 706473 | 128.0 | 5519 | masked 4-plane span fill of one triangle |
| 2 | triangle setup (orig) | 10.0 | 174437 | 128.0 | 1363 | clip tests, sort, 3-7 divu, record for the fill |
| 3 | window copy | 9.4 | 162967 | 1.0 | 162967 | 32000 B picture -> back buffer |
| 4 | sprite blit (p4_spr) | 7.3 | 127188 | 18.2 | 7004 | masked sprite, blitter / pre-shifted cache |
| 5 | VBL wait | 6.3 | 110234 | 2586.7 | 43 | idle spin until the VBL flag |
| 6 | small sprites (8 px) | 6.3 | 109087 | 26.0 | 4196 | SPRITE8 objects, rol/ror per row |
| 7 | cell loop | 2.7 | 46146 | 1.0 | 46146 | per cell: 2 triangles, objects |
| 8 | army/people lists | 2.3 | 39175 | 23.8 | 1649 | move person between cell chains |
| 9 | sound (snd_ DMA resampler) | 2.2 | 38248 | 10.8 | 3542 | STE DMA sound producer |
| 10 | men interp (p3b) | 1.9 | 33785 | 0.0 | 844628 | predict-ahead men positions |
| | rest (HUD, UI, logic, interrupts, ...) | 3.4 | 59174 | | | |

map_idle 8 MHz:
work/prof2/map_idle_8_b2: 43300936 cycles, 21 rendered passes, 2061949 cycles/pass
| # | function | share % | cycles/pass | calls/pass | cycles/call | role |
|---|---|---:|---:|---:|---:|---|
| 1 | terrain span fill (orig) | 47.6 | 981769 | 126.1 | 7783 | masked 4-plane span fill of one triangle |
| 2 | triangle setup (orig) | 8.1 | 167015 | 126.1 | 1324 | clip tests, sort, 3-7 divu, record for the fill |
| 3 | window copy | 7.7 | 157740 | 1.0 | 157740 | 32000 B picture -> back buffer |
| 4 | sprite blit (p4_spr) | 6.3 | 130476 | 17.9 | 7307 | masked sprite, blitter / pre-shifted cache |
| 5 | small sprites (8 px) | 6.3 | 130062 | 30.0 | 4342 | SPRITE8 objects, rol/ror per row |
| 6 | sound (snd_ DMA resampler) | 5.0 | 102169 | 12.9 | 7946 | STE DMA sound producer |
| 7 | VBL wait | 4.9 | 100996 | 2010.8 | 50 | idle spin until the VBL flag |
| 8 | cell loop | 2.2 | 45381 | 1.0 | 47650 | per cell: 2 triangles, objects |
| 9 | army/people lists | 2.0 | 41398 | 23.9 | 1732 | move person between cell chains |
| 10 | pointer (VBL, p4_ptr) | 1.7 | 35407 | 12.9 | 2754 | mouse pointer skip test |
| | rest (HUD, UI, logic, interrupts, ...) | 3.3 | 67572 | | | |

get_men 16 MHz:
work/prof2/get_men_16_b2: 86664120 cycles, 54 rendered passes, 1604891 cycles/pass
| # | function | share % | cycles/pass | calls/pass | cycles/call | role |
|---|---|---:|---:|---:|---:|---|
| 1 | terrain span fill (orig) | 44.0 | 706105 | 128.2 | 5508 | masked 4-plane span fill of one triangle |
| 2 | triangle setup (orig) | 10.9 | 174180 | 128.2 | 1358 | clip tests, sort, 3-7 divu, record for the fill |
| 3 | window copy | 10.1 | 162608 | 1.0 | 162608 | 32000 B picture -> back buffer |
| 4 | sprite blit (p4_spr) | 7.9 | 127004 | 18.1 | 7020 | masked sprite, blitter / pre-shifted cache |
| 5 | VBL wait | 6.1 | 98256 | 2883.2 | 34 | idle spin until the VBL flag |
| 6 | small sprites (8 px) | 4.5 | 72064 | 18.2 | 3963 | SPRITE8 objects, rol/ror per row |
| 7 | cell loop | 2.9 | 46445 | 1.0 | 46445 | per cell: 2 triangles, objects |
| 8 | army/people lists | 2.3 | 36114 | 18.6 | 1944 | move person between cell chains |
| 9 | object project/sort | 1.6 | 25816 | 33.2 | 777 | per cell object list, screen position |
| 10 | sprite blit (orig) | 1.5 | 23846 | 19.1 | 1249 | masked sprite (zoom variants) |
| | rest (HUD, UI, logic, interrupts, ...) | 2.1 | 33857 | | | |

("VBL wait" calls = spin iterations; "men interp (p3b)" has no meaningful call count, it is wrapper code that runs inside several stages.)

### 2.1 AFTER p6_slope + p6_tri (`*_n2.txt`)
get_men 8 MHz:
work/prof2/get_men_8_n2: 43428180 cycles, 30 rendered passes, 1447606 cycles/pass
| # | function | share % | cycles/pass | calls/pass | cycles/call | role |
|---|---|---:|---:|---:|---:|---|
| 1 | p6_tri setup+fill | 47.4 | 685968 | 127.3 | 5390 | new setup + chunked span fill |
| 2 | window copy | 11.3 | 162987 | 1.0 | 162987 | 32000 B picture -> back buffer |
| 3 | sprite blit (p4_spr) | 8.7 | 125745 | 17.9 | 7025 | masked sprite, blitter / pre-shifted cache |
| 4 | small sprites (8 px) | 4.9 | 70851 | 17.5 | 4049 | SPRITE8 objects, rol/ror per row |
| 5 | VBL wait | 4.4 | 63248 | 1139.6 | 55 | idle spin until the VBL flag |
| 6 | cell loop | 3.2 | 46202 | 1.0 | 46202 | per cell: 2 triangles, objects |
| 7 | army/people lists | 2.7 | 38786 | 32.4 | 1198 | move person between cell chains |
| 8 | sound (snd_ DMA resampler) | 2.4 | 34657 | 9.0 | 3851 | STE DMA sound producer |
| 9 | men interp (p3b) | 2.1 | 30590 | 0.0 | 917700 | predict-ahead men positions |
| 10 | object project/sort | 1.7 | 24843 | 32.3 | 768 | per cell object list, screen position |
| | rest (HUD, UI, logic, interrupts, ...) | 3.6 | 52144 | | | |

map_idle 8 MHz:
work/prof2/map_idle_8_n2: 43311464 cycles, 23 rendered passes, 1883107 cycles/pass
| # | function | share % | cycles/pass | calls/pass | cycles/call | role |
|---|---|---:|---:|---:|---:|---|
| 1 | p6_tri setup+fill | 50.7 | 953870 | 132.8 | 7181 | new setup + chunked span fill |
| 2 | window copy | 8.8 | 166046 | 1.0 | 166046 | 32000 B picture -> back buffer |
| 3 | sprite blit (p4_spr) | 7.3 | 137926 | 18.9 | 7309 | masked sprite, blitter / pre-shifted cache |
| 4 | small sprites (8 px) | 7.2 | 136202 | 31.3 | 4357 | SPRITE8 objects, rol/ror per row |
| 5 | sound (snd_ DMA resampler) | 5.0 | 93274 | 11.7 | 7946 | STE DMA sound producer |
| 6 | VBL wait | 4.5 | 84366 | 1557.5 | 54 | idle spin until the VBL flag |
| 7 | cell loop | 2.5 | 47844 | 1.0 | 45851 | per cell: 2 triangles, objects |
| 8 | army/people lists | 2.1 | 38962 | 20.8 | 1875 | move person between cell chains |
| 9 | men interp (p3b) | 1.8 | 33238 | 0.0 | 764464 | predict-ahead men positions |
| 10 | pointer (VBL, p4_ptr) | 1.7 | 32302 | 11.7 | 2752 | mouse pointer skip test |
| | rest (HUD, UI, logic, interrupts, ...) | 3.2 | 60752 | | | |

### 2.2 Disassembly excerpts with cycles (Hatari per-instruction averages, get_men 8 MHz)

**#1 terrain span fill `$e3e6-$e5aa` (original code; 36 494 scanlines in 27 passes = 1352/pass, 127 triangles/pass).** Cost per entry, measured:
head+rts 221 cycles per triangle; prelude (`$e420-$e46e`) 200.5 per scanline; one-group body 217 (47.6 % of scanlines); two adjacent groups 342 (47.5 %); three+ groups 394 + 24 + 181 (4.9 %); total 516 cycles per scanline, 5 502 per triangle, 49.7 cycles per pixel written.
```
00e420 lsr.w #1,d4            8   ; undo the doubling of the previous scanline's index
00e422 lsr.w #1,d5            8
00e424 swap d4                4   ; x_left DDA: swap / add.l slope / swap = 16 cycles per edge
00e426 add.l a3,d4            8
00e428 swap d4                4
00e42a subq.w #1,d7           4   ; left run counter (reload code at $e42e)
00e42c bne.b $e436           12
00e436 swap d7                4   ; right edge: the same again (swap d5 / add.l a4,d5 / swap d5) + counter
 ...
00e44a move.l a5,d6 / add.l d6,d6 / addq.b #8,d6 / lsr.l #1,d6 / movea.l d6,a5      4+8+4+10+6 = 32   ; pattern pointer step
00e456 add.w d4,d4 / add.w d5,d5                                                      8
00e45a move.w (a6,d5.w),d6    16  ; byte offset of the right 16-px group (table at $ece2)
00e45e move.w (a6,d4.w),d0    16  ; and of the left one
00e462 lea.l (a1,d0.w),a2     16
00e466 sub.w d0,d6 / bge / bne                                                       4+12+10
 -- one group (00e470..00e4a2, 217): masks = -$80(a6,..) & -$40(a6,..) (70), then per long: and.l (a2),d1 14 / and.l (a5)+,d0 16 / or.l 10 / move.l d0,(a2)+ 12 (x2) + lea + bra.w 20
 -- two groups (00e55a..00e5a6, 342): the same body twice with one mask each
```
The tail of every scanline is `lea $a0(a1),a1 ; bra.w $e420` (8+12).

**#2 triangle setup `$ef62-$f240` (1363 cycles per call, 127 calls/pass):** 296 cycles of range tests (`tst.w/bmi.w` x3, `cmp.w #199/blt.w` x3, `cmp.l #0/bgt.w` x3, `cmp.l #$ff0000/blt.w` x3), the sort by `exg`, 7 `divu.w` of 120-131 cycles each at `$f010 $f01c $f046 $f052 $f0b4 $f0c0 $f0fe $f10a` (3 per call on the usual path: 2 edges + the third run), each wrapped in 60-80 cycles of `swap/ext/neg/lsl/andi`, and 14 stores of the record the filler reads back (`move.l d4,$a(a0)` ...).
Each of the 24 call sites in the cell loop adds `movem.l d0-d3/d5-d7/a0-a2,-(a7)` (88) + `bsr.w` (18) + `movem.l (a7)+,...` (92) and the colour byte logic (`move.b -$2041(a1),d3 ; cmpi.w #$c,d3 ; bge ; add.w d5,d3`).

**#3 window copy `$12ce0` (163 k cycles, once per pass):** `movem.l (a0)+,d2-d7/a2-a3 ; movem.l d2-d7/a2-a3,(a1) ; adda.w d1,a1` twice per `dbra`, 500 times = 32 000 B at 5.1 cycles/byte (the bus-bound minimum for movem is ~4.0).

**#4 sprite blit (p4_spr, `$bd500`):** 18 calls x 7 000 cycles; the STE blitter does 8 HOG passes (per plane AND the mask, OR the plane) over 24 rows x 3 words = 72 words x 12 bus cycles x 8 = 6 900 cycles: bus-bound, nothing left on the CPU side.

**#5 VBL wait `$1870`:** `tst.w $2df8c.l` 16 + `beq.b` 12 = 28 cycles x 2 937 spins/pass. The game flips (`$187a` writes `$ff8201/03`, clears `$2df8c`) and the VBL handler (`$14d2`) sets the flag; the next pass may not touch the buffer it just stopped showing until then, so each pass is padded to the next VBL: on average half a VBL (80 k cycles) is idle.

**#6 small sprites `$11f12-$120e8` (the SPRITE8.DAT objects, 17-31 per pass, 4.0-4.3 k cycles each):** per row `moveq #-1,d2 ; move.b (a1)+,d2 ; rol.w d0,d2 ; move.w (a0),d3 ; and.w d2,d3 ; clr.w d4 ; move.b (a1)+,d4 ; rol.w d0,d4 ; or.w d4,d3 ; move.w d3,(a0)+` x4 planes (the `rol/ror.w d0,dn` by the pixel shift is 34 cycles at 6+2n, ~1 150 cycles/pass per instruction line); `muls.w d6/d7` x6 (`$11f36-$11f62`) for the object's screen position (700-760 cycles/pass per line); `mulu.w #$37,d2` at `$11f88`.

**#7 cell loop `$fccc-$fde8` (46 k, one call/pass):** 128 cells, `bsr.w $ef62` x2-4 with the movem pairs above, `jsr $115e0` per cell with objects.
**#8 DMA sound producer `$d0000`** (31.7 cycles per resampled output sample, 12 517 Hz while a chunk plays: 2.2-5 %). **#9 people lists `$163ea`** (move a person between cell chains, 1.0-2.2 k per call). **#10 p3b_interp/delta** (1.3-2.1 %).

## 3. Deep dive: the terrain triangle fill and setup

Corrections to hotpaths.md: the fill is NOT texture mapped (no u/v, no per-pixel interpolation). It is a **flat-shaded, dithered triangle fill**.

* **What a triangle is** (`$ef62` -> record at `$f1e2` -> `$e3e6`): colour byte (terrain type from the cell tables, +water phase `$4bb3e & 3` for colours < 12), y0, x0 for both edges, and runs `(count, slope)` for the left and the right edge; the shorter edge gets a third run for the rest. Slopes are 16.16 numbers `(|dx|<<16)/dy` (dy > |dx|) or `((|dx|<<8)/dy)<<8`.
* **Per scanline** the filler adds the slope to the two edge x values, finds the left and right 16-pixel groups (word table at `$ece2`, 8 bytes per group) and masks them (two long tables); the interior groups are plain `move.l d0/d1,(a2)+` stores of the pattern.
* **Pattern ("texture")**: a 128-byte ring per colour (`[$ffa2] / 2 + colour * 128`; 4-plane, two longs per scanline). The ring pointer for the triangle starts at `((colour<<8) + $ffa2 + y0*16)/2` (byte add: the low byte wraps without carry) and the filler adds 4 in the `(a5)+` read and 4 more per scanline, wrapping its low 7 bits; the `(a5)+` carry into bit 7 is NOT wrapped (every 16 scanlines the pointer moves into the next colour's ring when `(a5 & 7) >= 4`). The same two longs are used for every group of the scanline: the texture is read per scanline, not per pixel and not per group. Colour mapping: byte 0 of the record = colour, or `$1c` when the long edge is the right edge (`s2 > s1`).
* **Span length distribution** (groups touched minus one, from a unicorn trace of `$f898` on `work/dumps`): get_men/battle_320: 652 one-group, 650 two-group, 67 three-group scanlines of 1 369 (47.6 / 47.5 / 4.9 %); map_idle: 1 049 / 787 / 134 of 1 970 (53.2 / 39.9 / 6.8 %). Triangles are tiny: 10.7 scanlines and ~10 pixels per scanline; the per-scanline overhead is the cost, not the pixels (50 cycles per pixel).
* **Overdraw (trace of every span of one frame, unicorn on the RAM of the pass start):** pixels written 14 037 vs unique 12 481 (x1.12) in get_men/battle_320, 19 012 vs 14 440 (x1.32) in map_idle. Terrain rows 90..181, x 96..253. So at most 11-24 % of the fill work paints a pixel that a later triangle paints again; an exact cull would need per-pixel coverage of later triangles = as expensive as the fill.
* **Behind the HUD / off screen?** Against the real final frame (Hatari capture of RAM at `$130aa` and at the flip of the same pass, `/tmp`-only; unicorn `$f898` result vs the final back buffer): R1 differs from the final buffer in 92 bytes, 0 of them terrain pixels: no terrain pixel is overpainted by the HUD in this view. Triangles with a vertex outside x 0..255 / y 0..199 go to the polygon clipper `$f202` (0 per pass in the three scenes, ~10 % in random off-centre views); nothing off screen is filled otherwise.
* **Can the triangle setup avoid the divides?** The 3 edges per triangle are all different (dx, dy) pairs, the slope is a truncated quotient with no recurrence, so no incremental scheme exists; but the domain is tiny: dx and dy < 64 in 99.9 % of 21 410 divides over random views (dy 50th/95th/99th percentile 6/16/23; |dx| 15/31/39). `p6_slope` holds the 64 x 64 table of the original quotients (16 384 B, exact by construction: `(mag<<16)/dy` or `((mag<<8)/dy)<<8`, no overflow possible for mag <= 255); other operands run the original `divu` code. (A reciprocal multiply needs two `mulu`, 110-140 cycles = no gain over `divu`.)
* **Other things found:** (a) at headings 0, 64, 128, 192 (cells aligned with the screen) 40-68 % of the triangles are flat-topped (two vertices on one row); the original takes a special path (`$f13e`) there; `p6_tri` handles flat top and flat bottom natively. (b) the pattern ring wraps every 16 scanlines; half of the triangles of a typical view cross a wrap (`fast_W` 64 of 122).

## 4. What was built (all `; default: no`, new files, nothing existing edited except the shared tool bits listed in section 9)

### 4.1 `p6_slope` + `p6_tri` (setup + fill, sites `$ef62`; data `$d5000-$d8fff`, code `$d9000-$d976d`)
Replaces `$ef62` (6 bytes -> `jmp $d9012`) and with it the filler for every ordinary triangle; the original code stays as the fallback (`ofb` re-runs the original `$ef62` with the inputs untouched).
Per triangle (measured, get_men 8 MHz, `work/prof2/get_men_8_t2`): setup + head 1 170 cycles instead of ~1 670 (1 363 + 258 + the run reloads); per scanline 390 instead of 480-516. Total per pass `$ef62 + $e3e6`: 876 k -> 686 k (get_men 8 MHz, b2 vs n2 profiles), 1 149 k -> 954 k (map_idle).
What changed, all exact:
1. one `cmp.l #$ff0000` + `cmp.w #199` unsigned pair per vertex instead of 12 signed tests;
2. the divides come from `p6_slope` (misses run the original divu branches);
3. no record in `$f1e2`: the plan (chunks) is built in registers + static lists (`TL/TR`, `tend`, `tw`) and the filler runs directly;
4. the filler is organised in chunks (scanlines between two events: end of the short edge's run = slope change, pattern-ring wrap): inside a chunk the DDA is `add.l a3,d4 / add.l a4,d5`, no counters, no pattern step (`(a5)+` does the +8), `S ^ ((S ^ P) & m)` for the masked store, `dbra`;
5. generic chunk list (`tallb`) for triangles with more than one ring wrap; flat top / flat bottom native; everything else (clipper, ...) = original.
Exactness (all by `tools/pmfill_test.py`, unicorn 68000, whole 1 MB compared, scratch `$f1e2..$f211` and the stack below the frame excluded):
```
$ python3 tools/pmfill_test.py --patch p6_slope p6_tri --views 300 --seed 11     (3 dumps x 300 random cameras: scroll, heading, tilt, scale, zoom, water phase)
900 views (64 skipped: the original faults too), 1370462 scanlines (original), 8067 non-setup streams: IDENTICAL (whole RAM)
$ python3 tools/pmfill_test.py --patch p6_slope p6_tri --fuzz 4000 --seed 21     (direct calls of $ef62: random vertices incl. outside, flat, crossing, big dx/dy, random ring base)
fuzz: 4000 triangles (0 where the original faults too): IDENTICAL (whole RAM)
```
Final code (flat top/bottom, `tallb`): `--fuzz 3000 --seed 77`: 3000 triangles IDENTICAL; `--views 250 --seed 99`: 750 views (48 skipped), 1 124 788 scanlines, 6 466 clipper streams, IDENTICAL (whole RAM). (The two runs quoted above were made before flat-top support was added.) Negative control: a table with `+1` in one branch -> 13 of 30 views MISMATCH.
Not covered by any test: the abort path (`done:`, right group left of the left group: never hit in 6 000 triangles and 2 M scanlines; it is the same `rts` as the original); odd ring pointers (impossible on a 68000: the original would take an address error); x > 319.
Assumptions (stated in the patch): `$f1e3` (record byte 1) is 0 and written by nobody; x stays in 0..255 inside this path (vertex range test).
Fallbacks: out-of-range vertex -> original (clipper); with `p6_tri` a flat triangle is native. Rate of `ofb` in the profiled scenes: 0-3 triangles per pass (2.7 in map_idle before flat support was added; none at the four compass headings tested afterwards).

### 4.2 `p6_cpy` (window copy on the STE blitter; site `$12ce0`, code `$da000`)
50 chunks of 4 rows (HOG, 2 560 cycles each = 0.32 ms). **Originally 20 chunks of 10 rows (6 400 cycles = 0.8 ms), on the argument that a 7812-baud keyboard byte takes 1.28 ms so the ACIA could not overrun: WRONG in Hatari, where an interrupt raised during a chunk can wait for TWO chunks; the IKBD reply (9 bytes per VBL) then overran, the mouse packet desynced and the VBL pointer code took a bus error (`work/notes/buserr.md`).** Interrupts are taken between chunks. Uses p4_spr's blitter decision word (`$bdc04 == $b17e0001`); otherwise (ST, TT, Falcon, no p4_spr) the original routine runs. Registers as the original leaves them.
Hatari charges the blitter 8 cycles per word, so the gain is -35 k cycles per pass by the arithmetic and -58 k measured in `pmab` (-3.95 %); [INFERENCE] a real STE blitter at 8 MHz moves a word in 8 cycles too, so expect about -35 k = -2.4 % there, not -4 %.

## 5. The window copy `$12ce0`: writers, and why it was not made smaller

Asked: prove the list of writers so only dirty rows need the HUD restore, or find another exact scheme. Result: **no exact restore-only-what-was-drawn scheme was found; the list of writers cannot be proven complete.**
Evidence collected: in the real final frame of get_men (pass 109) 6 521 bytes differ from the picture `$78000`: 5 741 inside the window box (cols 5-19, rows 13-165), 780 outside (rows 0-5: the tooltip patch's strip, 46-56: the army status icon, 166-189: terrain below row 165 and the status bar). Writers seen: terrain fill and sprites (known), `$178ae` (tooltip), `$165b2`/`$17878` HUD, the `$6a3a/$7a56/$d23a/$7202` UI, the pointer (in the displayed buffer), `$3f14` icon blits. Unknown to the analysis: every dialog, message and requester drawn over the 3D view by the UI code, and anything reached through the jump tables of the HUD code. A dirty-span log for fill + sprites would cost ~55 k cycles (per scanline min/max update + per-row restore) instead of 163 k, but it is exact only if every other writer also logs, which cannot be shown.
Exact alternatives measured instead: blitter in 10-row chunks (`p6_cpy`: -4.0 % of a pass); a 13-register `movem` loop on the CPU (4.73 vs 5.07 cycles/byte, -0.8 % of a pass, plain ST only) [INFERENCE, not built]. The copy cannot be removed by flipping buffers (the renderer only draws over the picture). p4_chase (copy behind the beam) is not exact (pointer at x = 304, y >= 184).

## 6. Gates (raw `pmab` output; base = tick_* + test_walk* + p4_ptr_a/b + p4_spr (+ p3b_interp/delta with `--base-poke b8a80:0001 --poke b8a80:0001 --tonly` once those became default); 700 VBL, `--walk`)

p6_slope + p6_tri on the tick + p4 base (before p3b became default):
```
map_idle @8 MHz: IDENTICAL (back frames matched 28, shown+pointer matched 11, flips captured 43/37) | work/pass 2766086 -> 2385558 (-380528, -13.76 %) | flips 37 -> 43 fps 2.769 -> 3.214 (+16.0 %)
get_men @8 MHz: IDENTICAL (back frames matched 58, shown+pointer matched 40, flips captured 72/62) | work/pass 1659326 -> 1435788 (-223538, -13.47 %) | flips 62 -> 72 fps 4.613 -> 5.325 (+15.4 %)
battle_320 @8 MHz: IDENTICAL (back frames matched 56, shown+pointer matched 34, flips captured 73/62) | work/pass 1648269 -> 1425155 (-223113, -13.54 %) | flips 62 -> 73 fps 4.606 -> 5.391 (+17.0 %)
```
With the new defaults (p3b_interp + p3b_delta in both runs, predict-ahead forced off in both, only tick-pass frames are hard comparisons, `--mhz 8 16`):
```
map_idle @8 MHz: IDENTICAL (back 31, shown+pointer 18) | work/pass 2766862 -> 2387033 (-13.73 %) | fps 2.769 -> 3.214 (+16.0 %)
map_idle @16 MHz: IDENTICAL (back 55) | 2147611 -> 1847638 (-13.97 %) | fps 7.205 -> 8.261 (+14.7 %)
get_men @8 MHz: IDENTICAL (back 53, shown+pointer 31, R frames differing (allowed) 1) | 1689415 -> 1466005 (-13.22 %) | fps 4.519 -> 5.185 (+14.8 %)
get_men @16 MHz: IDENTICAL (back 56, R frames differing (allowed) 34) | 1581005 -> 1380531 (-12.68 %) | fps 9.334 -> 10.174 (+9.0 %)
battle_320 @8 MHz: IDENTICAL (back 55, shown+pointer 36) | 1679215 -> 1455158 (-13.34 %) | fps 4.552 -> 5.213 (+14.5 %)
```
battle_320 @16 MHz: IDENTICAL (back 55) | 1499598 -> 1292260 (-13.83 %) | fps 9.913 -> 11.354 (+14.5 %)
p6_cpy on top of p6_slope + p6_tri (`--only p6_cpy`):
```
map_idle @8 MHz: IDENTICAL | 2387106 -> 2266806 (-5.04 %) | fps 3.214 -> 3.394 (+5.6 %)          map_idle @16: IDENTICAL | 1847466 -> 1780497 (-3.62 %) | 8.261 -> 8.406 (+1.8 %)
get_men @8 MHz: IDENTICAL | 1466011 -> 1408060 (-3.95 %) | fps 5.185 -> 5.399 (+4.1 %)          get_men @16: IDENTICAL | 1380533 -> 1341203 (-2.85 %) | 10.174 -> 10.492 (+3.1 %)
battle_320 @8 MHz: IDENTICAL | 1455163 -> 1397411 (-3.97 %) | fps 5.213 -> 5.490 (+5.3 %)       battle_320 @16: IDENTICAL | 1292374 -> 1256962 (-2.74 %) | 11.354 -> 11.443 (+0.8 %)
get_men @8 MHz, --st (FLAGS 6, plain-ST path of the patched run): IDENTICAL (back 54, shown+pointer 29); cycles +3.13 % only because the ST run also uses the sprite CACHE path instead of the blitter (the copy path is the original there)
```
`--st` for p6_tri is not meaningful (it has no ST/STE split); the plain ST is covered by the cold boot.

## 7. Ranked list of what remains (all exact unless marked; estimates are [INFERENCE] from the profiles above, effort S/M/L, risk L/M/H)

| # | idea | est. gain (8 MHz) | effort | risk | notes |
|---|---|---:|---|---|---|
| 1 | **Triple buffering = no VBL wait** | +4.4-6.6 % of cycles idle now (get_men 8: 63 k/pass, 16 MHz: 93 k) -> +5-7 % fps, more on faster machines | M | M | The wait exists only because the buffer just flipped away is still scanned. A third 32 000 B buffer (256-aligned; `$70000-$77cff` reads 100 % zero in all three dumps and the resource table has no destination there: NOT proven free, needs the pattern test of loading.md section 5) removes it: (a) `$1898 move.w #0,$2df8c` -> stamp the VBL count after the base write, (b) the main-loop flip call `$1386c` -> rotate (R,D,F) = (F,R,D) instead of swapping, (c) `$13090 jsr $1870` -> wait until `$6f304` differs from the count stamped at the PREVIOUS flip (a plain `$187a` flip stamps both, so menus keep the old rule). Touches `tick_pass`/p3b R passes and the pointer code only through `$2df78/$2df7c`, which keep their meaning. pmab needs a third capture region. Not built: no free-RAM proof, and p3b_interp/TickHz were changing the pass logic in parallel. |
| 2 | Small sprites `$11f82` on the blitter / pre-shifted cache (as p4_spr) | -1.5-3 % (4-7 % of cycles, 4.0-4.3 k per sprite) | M | M | same exactness proof method as p4_spr (`test_blit`) |
| 3 | p6_tri trims: fold the per-vertex range test into the view-table build `$fec6` (per vertex, not per triangle), cheaper slope macro (the `lsl.w #8` 22 + two checks 24), single combined ring-phase table | -1-1.5 % (1 170 -> ~900 cycles per triangle) | M | L | fuzz harness exists |
| 4 | Cell-loop wrapper: 24 call sites save/restore 10 registers (180 cycles) + colour logic per triangle; a new loop over the same data | -1.5-2.5 % | L | M | the four rotation variants `$f996-$fde8` are near copies |
| 5 | 13-register movem copy for plain ST | -0.8 % (ST only) | S | L | 4.73 vs 5.07 cycles/byte |
| 6 | p4_spr blitter: the 8 HOG passes are bus-bound (6.9 k of 7.0 k); fewer passes would need the mask in the halftone RAM | <= -1 % | M | M | |
| 7 | DMA sound resampler `$d0000` (2.2-5 %): `DEFMODE 1` plays the chunk at the DMA rate with zero CPU | -2.2-5 % while a sample plays | S | audio changes (pitch/duration), not video | belongs to the sound tradeoffs, not exact |
| 8 | people lists `$163ea` (2.3-2.7 %), logic stages | <= -1 % | M | L | list manipulation, no arithmetic to remove |
| 9 | static terrain-layer cache (reuse the previous frame's terrain when camera and tick are unchanged) | rejected: sprites interleave with terrain cells; re-painting the later triangles that overlap each sprite repaints about as many triangles as the frame has (20 objects x 6-12 triangles vs 128) | | | |
| 10 | terrain overdraw culling | rejected: overdraw is x1.12-1.32 and exact coverage costs as much as the fill | | | |

### Honest ceiling
Exact ideas 1-6 together are worth about 12-16 % of the current cycles; get_men at 8 MHz would go from 5.4 to roughly 6.2-6.5 fps and map_idle from 3.4 to ~4. What remains after that is the span fill itself (~390 cycles per scanline, ~1 360 scanlines per pass = 0.5 M cycles, 33 % of the pass), the sprite blits (9 %) and the window copy (8 % even on the blitter): each is near the bus-bound limit of its method, so a 2x speed-up is not available without changing what is drawn (section 8) or the machine (the 16 MHz rows above).

## 8. Visual tradeoffs (NOT built; need your decision; mock-ups render `$f898` of the get_men snapshot with the triangle setup told to skip triangles, same code and palette, no HUD pass/pointer; `work/shots/perf2/`)

| id | what | before/after | effect |
|---|---|---|---|
| V1 | narrower 3D window: do not draw terrain whose centroid is outside x 45..200 of 256 | `vt_before.png` / `vt_narrow_window.png` (13 of 128 triangles, 1 243 of 1 369 scanlines kept) | -9 % scanlines in this view: about -5 % of a pass; corners of the island vanish |
| V2 | no far terrain: drop triangles with centroid y < 120 | `vt_before.png` / `vt_no_far_rows.png` (72 of 128 triangles skipped, 822 of 1 369 scanlines) | -40 % scanlines = about -20 % of a pass; the whole upper half of the island and the village disappear (shown to bound the idea, not a proposal) |
| V3 | half-resolution terrain (merge 2 x 2 cells into one bigger triangle pair) | not rendered | halves the triangles: about -20 % of a pass; the heightfield gets coarser, edges at cell borders jump |
| V4 | lower quality sound (DEFMODE 1, section 7 row 7) | none | -2.2-5 % while a sample plays |
Reference screenshot from Hatari: `vt_ref_hatari_get_men.png`.

## 9. Files, tools, RAM

New: `patches/p6_slope.s`, `p6_tri.s`, `p6_cpy.s`; `tools/pmfill_test.py` (unicorn differential test and fuzz; `pip install unicorn`), `tools/pmprof2.py`, `tools/pmrep2.py`, `tools/pmtop10.py`; profiles in `work/prof2/` (the `.bin` dumps were removed, they are reproducible); build `build/p6/` (floppy with everything).
Shared files touched: `tools/pmpatch.py` (`PREFIX_RANGES["p6_"] = $D5000-$DCFFF`; a `p5_` range at `$CE000` was tried and removed because `pmab`'s `test_walk*` live there), `tools/pmab.py` (`--base-poke`: a poke applied to the base run too, needed to run the gate with p3b_interp in both runs).
RAM used: `$D5000-$D8FFF` slope table (16 384 B), `$D9000-$D976D` p6_tri (1 902 B incl. static chunk lists, which are written at run time), `$DA000-$DA087` p6_cpy; all inside the snd_ range's unused tail and the HD overlay window. Floppy payload +18 KB of records (the build reports the free space).
'''
