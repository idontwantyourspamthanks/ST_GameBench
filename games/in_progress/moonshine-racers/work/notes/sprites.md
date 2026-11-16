# Moonshine Racers: sprite work, measured (object stage `$e406`, clouds, options a-e)

Machine for every number: Hatari 2.6.1, STE, TOS 1.62, 1 MB, 8.02 MHz, 50 Hz; snapshots `work/snapshots/ste1m_race_{grid,start,up,drive}.sav` (stock game: no mr_/mt_/rd_ patch active in the traces).
Nothing here changes a shipped patch. **No `ms_*` patch is shipped** (section 9). Disassembly lines come from `tools/m68dis.py` on `work/dumps/ram_race_start.bin`.
Cycle numbers are Hatari `e CycleCounter` / `e FrameCycles` timestamps taken by breakpoint scripts. Tools and raw data: `work/sprite/` (`raw/*.log.gz` traces, `out/*` tables and raw outputs, `res_*.txt` raw harness outputs; `python3 work/sprite/report.py` regenerates the traced tables, `python3 work/sprite/gen_notes.py` regenerates this file). Unproven = `[INFERENCE]`.

## 0. Findings in one page

1. **The object stage is 211-227 k cycles per pass (`$e406`), 89 % of it inside the sprite kernels** (race_start: kernel calls ~200 k, dispatch + glue ~25 k). Against the pass lengths reported for the render patches (4.73 VBL with mr_*, 4.29 VBL driving with rd_* = 687 k cycles) the stage is 28 % / 32 % of the pass: the sprite work did not shrink while everything else did.
2. **Two sprites are 26 % of the stage**: the player car (slot 12, bank `$2156a`, 4 columns, 34-36 rows, constant x, `x & 15 = 2`) 33-36 k and its second layer (slot 49, 4 columns, 21 rows, `x & 15 = 4`) 21-22 k, every pass.
3. **96 % of all type-0 draws are shifted** (`x & 15 != 0`); a shifted row costs about twice an aligned row. Sprites are pre-scaled bitmaps (8 scale steps per object kind), **not pre-shifted**: the shift is `ror.l`/`lsr.l` at draw time.
4. **Options, real Hatari cycles, each differentially checked against the stock kernel on the real banks (identical screen checksums)**:
   (a) pre-masked: aligned -16 %, shifted -4 %..+1 %. (b) pre-shifted data: -37..-46 % per call, but **one shift variant of the sprite set is 413 KB (15 variants: 6.0 MB) against 215 KB free, and the banks are mutable at run time**. (c) generated kernel with immediate shift + zero-mask skip: 0.93-1.05 (no gain). (d) early-out of dead calls: 16-108 cycles per dead call, ~0.2 k per pass. (e) STE blitter (10-12 passes per sprite part, HOG): **-12.9 % of a real frame's type-0 draws with interrupts enabled (5,645,148 -> 4,916,668 cycles for 30 frames of 17 calls)**, predicted -22..-29 k per pass (3.2-4.2 % of a 687 k pass); break-even 10 rows (1 column) / 6 rows (2 columns) / 13 / 14 (3 / 4 columns).
5. **Clouds (`$de1c` + `$de6c`, 80 k per pass = 10 %) repeat the same (x, y, frame) in 100 % of the passes while standing and 51 % while driving, but skipping them is not pixel-identical**: gate `race_grid` DIFFER 86 bytes at flips 10 and 40 (section 7). Rejected; files kept in `work/sprite/rejected/`.
6. Recommendation (section 10): no sprite-kernel work (exact CPU headroom 1-2 % of the pass); the blitter is the only measured lever (3.5-4 %, STE / Mega ST with a blitter at 8 MHz only) and needs a decision on real-hardware raster/IKBD latency that Hatari cannot show; the cloud erase/draw is the only 6-12 % item and is not exact.

## 1. How it was measured

- `work/sprite/trace.py SNAP NAME` (parser `parse.py`, `analyze.py`): persistent breakpoints (`b pc = X :trace :file script`) on the stage entry `$e406` / exit `$e4fc`, the slot dispatch `$e598` / `$e568` (script logs `e a2` and `m a2 56` = the 56-byte slot), every kernel call site (`$ed6e jsr (a4)` type 0 with return `$ed70`, `$e710 jsr $15442` types 1/3 with return `$e716`, the `jsr/jmp (a0)` sites `$1551a $1554a $1556a $155ac $155cc $15604` inside `$15442`, `$e8c8 $e920 $e9f2 $eaba $eb0a $ec94` type 2) and the interrupt entries/exits (`$d11e/$d136`, `$d616/$d6ba/$d68e`); each script prints `e VBL`, `e FrameCycles` and `r`. Time = VBL x 160,256 + FrameCycles with the wrap offset fitted (0 violations); interrupt time is subtracted with an entry/rte depth counter. 142 / 120 / 120 / 78 complete frames (grid / start / up / drive), logs `raw/race_*.log.gz`.
- Breakpoints added from inside a breakpoint script crash Hatari (`too many new breakpoints added within single breakpoint hit`, then a silent exit): they are sent from outside, `$e406` last, so every reported frame has all of them armed. A Hatari run takes ~20 s per scene.
- Stage totals match rendering.md (219-231 k incl. interrupts): mean net 213,250 / 224,778 / 227,373 / 211,296 cycles with 8.5-9.6 k interrupt cycles per stage removed.
- Microbenchmarks (`kb.s` + `kb.py`, `kb2.py`, `mk.py`; `unit.py` runs a blob inside a snapshot): the blob is loaded at `$C0000`, entered from the game loop (`$7b74` redirected), SR `$2700`; it calls a kernel `reps` times on a scratch screen `$C8000` that is refilled with a fixed pattern before each case; markers `m_case` / `m_end` are timestamped; the harness overhead (an `rts` kernel, 164 cycles) is subtracted; **a checksum of the whole scratch screen after every case is compared with the stock kernel's**. Sprites are the real bitmaps of the four banks. `kb3.s` replays a call list repeatedly with interrupts enabled.

## 2. Sprite format, scaling, data (confirmed)

- **Slots** `$29c8 + n * $38` (56 bytes): 0-11 clouds, 12-16 car slots, 17-47 rolling scenery slots, 49-59 special slots drawn through `$e568` (slot 12 `$2c68` and slot 49 `$3480` are the player's car and its second layer). The stage sorts 37 slots by depth with an exchange network (`00e440-00e474`), builds the order list `$36e8`, then calls `$e598` once per slot. `$e598` dispatches on the type word `$c(a2)` (`00e5a4 move.w $c(a2),d0`): 0 = one bitmap (`$ec98 -> $ecc8 -> jsr (a4)` at `$ed6e`), 1 and 3 = **three stacked parts** (`$e5c6` / `$e620` -> `jsr $15442` at `$e710`; the parts use kernels from `$37c0/$37c4/$37c8`), 2 = car with shadow (`$e718`, `$124ac`; not seen in these scenes).
- **Table-driven pre-scaled bitmaps**: `$34(a2)` = table base, entry = (`$6(a2) + $8(a2)`) x 14 bytes `{ptr.l, width px.w, height.w, xoff.w, yoff.w, nibble.w}` (`00ecc8-00ecde: add.w d0,d0 / move.w d0,d1 / lsl.w #3,d0 / sub.w d1,d0 / adda.w d0,a0`; bitmap `00ecf0 movea.l (a0),a1`, rows `00ece0 move.w $6(a0),d7`).
- **Banks and sizes** (`out/preshift_budget.txt`, entries scanned from the tables in the dump; sprite sheets `out/sheet_A.png`, `sheet_B.png`, `sheet_cars.png`, `sheet_player.png`):

| bank | table | entries | bitmap data | content |
|---|---|---|---|---|
| scenery A | `$3d16e` | 280 | 65,802 B | road signs (stop, road block, speed limit, police), billboards ("VOTE", "DRINK"), barn/buildings, rocks, cacti, bushes; nibbles 11/13, a few 7 |
| scenery B | `$5a402` | 64 | 23,634 B | trees, cacti, tumbleweed, skulls, bushes (nibble 11) |
| opponent cars | `$306c4` | 96 | 50,536 B | 3 car bodies x 8 scale steps (nibble 15, 64x47 ... 17x13) + 24-96 nibble-7 frames (62x38 ... 16x10) |
| player cars | `$2156a` (also `$25244`, `$28f0c`, chosen by `$102c` at `$dfa8`) | 45 | 14,244 B | 3 sizes (62x37, 61x36, 62x34) x 5 steering frames + small wheel/dust parts (16 px wide, nibble 3) |

  **154 KB of bitmap data in total.** The cloud bank `$19d10` (10 entries, 912 B, nibble 2) is separate.
- **Scale steps: 8 per object kind**, e.g. scenery A `64x63 56x56 49x49 43x42 37x36 30x30 22x22 17x17`, scenery B `45x21 40x19 35x17 30x14 26x12 21x10 16x8 12x6`, cars `64x47 56x42 49x36 43x32 37x27 30x22 22x17 17x13`: width x ~0.87 per step. A 16-step small-scenery set exists in bank A. There is no run-time scaling.
- **Row format**: width rounded up to 16 px = `c` columns (1-4). The nibble `$c(entry)` = planes present in the data (bit n = plane n): **7 = planes 0,1,2; 11 = 0,1,3; 13 = 0,2,3; 15 = 0-3**; data words per column-row = number of planes. **The mask is the OR of the data planes, recomputed for every row; the absent plane is only cleared under the mask** (`and.w d0,(a3)+`):
```
012a04:  4c99000e  movem.w (a1)+,d1-d3
012a08:  3001 / 8042 / 8043 / 4640   move.w d1,d0 / or.w d2,d0 / or.w d3,d0 / not.w d0
012a10:  c153 and.w d0,(a3) / 835b or.w d1,(a3)+ / c153 / 855b or.w d2,(a3)+ / c153 / 875b or.w d3,(a3)+ / c15b and.w d0,(a3)+   ; 142 cycles per aligned column-row
```
  Row layout (found by a differential test of my blitter formulation against the stock kernel, then confirmed in the kernels): the first two columns are one **plane-major pair** (`013704 movem.w (a1)+,d1-d6`: d1 = p0c0, d2 = p0c1, d3 = p1c0 ...; mask `013710 or.w d3,d0 / 013712 or.w d5,d0` = d1|d3|d5), every further column is a **single with its planes interleaved** (`01373a movem.w (a1)+,d1-d3`). A 1-column sprite is one interleaved column; rows are contiguous, `c x 2 x planes` bytes per row.
- **Kernel family** (`$12000-$16000`): 16 full entries (4 nibbles x 1-4 columns; pointer tables `$399c $39b0 $39c4 $3a14`, entries `$12994 $12a98 $12bac $12ce0` (1 column), `$12f60 $130e2 $1327e $1345a` (2), `$13662 $1384c $13a5e $13cc8` (3), `$13f6e $141cc $1445c $1475a` (4)) = clip x (`012994 cmpi.w #$fff0,d0` ...), clip y (`0129a4 tst.w d1 ...`), `move.w d2,$100c.l` (`0129f4`, state `$100c` = y*160 + (x&$f0)/2), then jump into the aligned (`tst.w d6 / bne`) or shifted loop. The post-setup entries (`$129fc ...`, tables `$38ac-$3960`, selector table `$37ec`) are reached from the 3-part objects. All these pointer tables are static data (xref: only reads, identical to the game-entry dump). Edge columns are skipped by **self-modifying code** (`012a28 lea.l $12cc0(pc),a0 / lea.l $12a66(pc),a4 / move.l (a2)+,(a4)` ...: 4-5 compares + `move.l` into the loop per call, ~330 cycles for the 4-column shifted kernel; entry 232 + prologue 335 = 570 measured by the profile). The shifted loop does `lsr.l d6,d1` per plane word (`01410a`), swaps and a long `and.l (a3),d0` at the edges.
- **What each alignment costs** (T4 below: fits of 6,600 calls; harness numbers in section 5 agree): 1 column aligned 138 cycles/row, shifted 334; 2 columns 235 / 524; 4 columns aligned ~200 per column-row (poor fit: 145 calls, all big scenery), shifted 881 per row. Harness (n7, 16 rows): 1 column 1,692 (10 rows) aligned vs 3,520 shifted; 2 columns 4,472 vs 9,204; 3 columns 6,508 vs 12,408; 4 columns 8,368 vs 15,804 (`res_stock_matrix.txt`, all four nibbles).

## 3. Traced cost tables

## T1 cycles per frame by class (slot net time = dispatch + draw; ISR time excluded), mean over traced frames
| scene | frames | player (slot12) | player2 (slot49) | opponents 13-15 | scenery type 0 | scenery type 1/3 composites | inactive slots | stage total |
|---|---|---|---|---|---|---|---|---|
| race_grid | 142 | 36,149 | 22,017 | 15,644 | 91,326 | 41,254 | 6,858 | 213,250 |
| race_start | 120 | 35,160 | 21,713 | 38,532 | 70,155 | 52,964 | 6,254 | 224,778 |
| race_up | 120 | 35,415 | 21,326 | 15,973 | 101,833 | 46,689 | 6,137 | 227,373 |
| race_drive | 78 | 33,475 | 21,883 | 14,734 | 81,227 | 53,734 | 6,243 | 211,296 |

## T2 type-0 single-sprite calls per frame by size class (columns x aligned/shifted), visible rows, mean kernel cycles
| scene | cols | x&15 | calls/frame | mean visible rows | mean kernel cycles/call | kernel cycles/frame |
|---|---|---|---|---|---|---|
| race_grid | 1 | aligned | 0.17 | 10.0 | 1,834 | 310 |
| race_grid | 1 | shifted | 7.90 | 12.0 | 4,757 | 37,587 |
| race_grid | 2 | aligned | 0.04 | 18.0 | 5,016 | 177 |
| race_grid | 2 | shifted | 3.36 | 14.7 | 8,498 | 28,548 |
| race_grid | 3 | aligned | 0.01 | 30.0 | 11,860 | 84 |
| race_grid | 3 | shifted | 0.21 | 24.7 | 19,881 | 4,200 |
| race_grid | 4 | aligned | 1.01 | 48.9 | 24,789 | 24,963 |
| race_grid | 4 | shifted | 2.08 | 28.6 | 28,743 | 59,915 |
| race_start | 1 | aligned | 0.41 | 11.7 | 2,022 | 825 |
| race_start | 1 | shifted | 8.02 | 12.1 | 4,489 | 35,987 |
| race_start | 2 | aligned | 0.15 | 16.7 | 4,426 | 664 |
| race_start | 2 | shifted | 3.23 | 15.2 | 8,593 | 27,783 |
| race_start | 3 | aligned | 0.05 | 27.8 | 11,033 | 552 |
| race_start | 3 | shifted | 0.99 | 26.6 | 21,566 | 21,386 |
| race_start | 4 | aligned | 0.01 | 38.0 | 16,968 | 141 |
| race_start | 4 | shifted | 2.34 | 30.0 | 28,858 | 67,577 |
| race_up | 1 | shifted | 6.79 | 10.8 | 3,883 | 26,374 |
| race_up | 2 | aligned | 0.07 | 14.5 | 4,120 | 275 |
| race_up | 2 | shifted | 5.71 | 18.9 | 10,689 | 61,019 |
| race_up | 3 | aligned | 0.02 | 30.0 | 12,464 | 208 |
| race_up | 3 | shifted | 2.20 | 9.4 | 6,159 | 13,550 |
| race_up | 4 | aligned | 0.01 | 35.0 | 9,336 | 78 |
| race_up | 4 | shifted | 2.05 | 29.2 | 28,097 | 57,598 |
| race_drive | 1 | aligned | 0.26 | 11.7 | 2,013 | 516 |
| race_drive | 1 | shifted | 7.99 | 10.9 | 4,019 | 32,097 |
| race_drive | 2 | aligned | 0.13 | 14.2 | 4,128 | 529 |
| race_drive | 2 | shifted | 5.24 | 13.3 | 7,616 | 39,936 |
| race_drive | 3 | aligned | 0.04 | 22.0 | 9,179 | 353 |
| race_drive | 3 | shifted | 0.36 | 24.2 | 20,081 | 7,208 |
| race_drive | 4 | shifted | 2.12 | 28.1 | 27,590 | 58,363 |

## T3 type-0 call outcomes (calls per frame)
| scene | drawn | rows<=0 (nothing) | x off screen | y clipped to nothing | composite (type 1/3) objects | slots active (drawn) | slots in sort list not drawn |
|---|---|---|---|---|---|---|---|
| race_grid | 14.8 | 0.0 | 0.0 | 0.0 | 6.0 | 20.8 | 25.2 |
| race_start | 15.2 | 0.0 | 1.3 | 0.0 | 7.7 | 24.2 | 21.8 |
| race_up | 16.8 | 4.0 | 2.0 | 0.0 | 4.0 | 26.9 | 19.1 |
| race_drive | 16.1 | 1.2 | 1.1 | 0.0 | 6.8 | 25.2 | 20.8 |

## T4 stock kernel cost fit, cycles = a + b * visible rows (type-0 calls of all four scenes)
| cols | x&15 | calls | a | b (cycles/row) | b per column-row |
|---|---|---|---|---|---|
| 1 | aligned | 93 | 421 | 138 | 138 |
| 1 | shifted | 3522 | 497 | 334 | 334 |
| 2 | aligned | 41 | 647 | 235 | 118 |
| 2 | shifted | 1959 | 729 | 524 | 262 |
| 3 | aligned | 12 | -1384 | 456 | 152 |
| 3 | shifted | 441 | -1557 | 853 | 284 |
| 4 | aligned | 145 | -14697 | 807 | 202 |
| 4 | shifted | 988 | 2833 | 881 | 220 |

## T5 kernel variants (type 0 full entries) over all traced calls
| nibble | cols | entry | calls | cycles (M) |
|---|---|---|---|---|
| 7 | 4 | 0x13f6e | 1002 | 27.85 |
| 11 | 2 | 0x130e2 | 2002 | 12.75 |
| 11 | 1 | 0x12a98 | 2918 | 12.60 |
| 13 | 4 | 0x1445c | 155 | 3.74 |
| 7 | 3 | 0x13662 | 161 | 3.27 |
| 7 | 2 | 0x12f60 | 326 | 2.83 |
| 13 | 2 | 0x1327e | 255 | 2.49 |
| 13 | 1 | 0x12bac | 758 | 1.80 |
| 11 | 3 | 0x1384c | 294 | 1.63 |
| 7 | 1 | 0x12994 | 340 | 1.15 |
| 13 | 3 | 0x13a5e | 24 | 0.58 |
| 11 | 4 | 0x141cc | 27 | 0.06 |

Per slot (race_start means): player 35,160, player2 21,713, opponents 13/14/15 23,079 + 5,748 + 9,705 (slot 13 is large at that moment), scenery slots 17-47 1.1-9 k each when drawn (drawn fraction 0.40-0.86 per slot), inactive slots 164 cycles each (`00e598 btst.b #$0,$4(a2) / beq`), cloud slots outside this stage. Classes by size (T2): 1 column 49 % of the type-0 calls / 23 % of kernel cycles, 2 columns 27 % / 27 %, 3 columns 6 % / 8 %, 4 columns 15 % / 42 % (players, opponents, big scenery). Visible/offscreen/tiny (T3): 15-17 drawn type-0 calls per pass, 6-8 composite objects, 21-27 active slots of 48 in the sort list, 0-4 calls per pass with rows <= 0 and 0-2 off screen; the smallest bitmaps are 1-3 px (scenery A steps 0-15, 3-13 px, 1-2 rows) and cost the glue, not the kernel.

Where the stage's cycles go (race_start, per pass): `$e406` head (sort, order list) 3.3 k; inactive slots 2.9 k; type-0 glue before the kernel call 8.3 k (490 per call) and after 2.2 k; type 1/3: glue 7.1 k + 1.1 k, composite (`$15442` front end + 3 parts) 44.8 k; type-0 kernels 155 k. Kernel row loops are ~85 % of kernel time, per-call overhead ~14 %.

## 4. Stock kernel micro-matrix (raw `res_stock_matrix.txt`; x = 100 + s so the real shift is (100 + s) & 15: s 12 = aligned)

```
calibration (rts kernel) per rep: 164.0
calib                                        0 cyc/call   sum cff95192
n7 c1 s0 rows10 16x10                     3520 cyc/call   sum b6aea031
n7 c1 s1 rows10 16x10                     3640 cyc/call   sum 5b8add08
n7 c1 s4 rows10 16x10                     3760 cyc/call   sum f43fabc4
n7 c1 s8 rows10 16x10                     4000 cyc/call   sum 57aec9cd
n7 c1 s12 rows10 16x10                    1692 cyc/call   sum 3fa6614a
n7 c1 s15 rows10 16x10                    3520 cyc/call   sum f2765173
n7 c2 s0 rows16 32x18                     9204 cyc/call   sum 2bdf84af
n7 c2 s1 rows16 32x18                     9204 cyc/call   sum 86e1b9dd
n7 c2 s4 rows16 32x18                     9204 cyc/call   sum 6ca9ebae
n7 c2 s8 rows16 32x18                     9204 cyc/call   sum a91c18cc
n7 c2 s12 rows16 32x18                    4472 cyc/call   sum f5989081
n7 c2 s15 rows16 32x18                    9204 cyc/call   sum cffc3f82
n7 c3 s0 rows16 48x30                    12408 cyc/call   sum da3ac3b6
n7 c3 s1 rows16 48x30                    12600 cyc/call   sum c0ce5f10
n7 c3 s4 rows16 48x30                    12792 cyc/call   sum 14851b03
n7 c3 s8 rows16 48x30                    13176 cyc/call   sum b65eb8a1
n7 c3 s12 rows16 48x30                    6508 cyc/call   sum 186bf28e
n7 c3 s15 rows16 48x30                   12408 cyc/call   sum 0bbf94f9
n7 c4 s0 rows16 62x38                    15804 cyc/call   sum 6c75c5e8
n7 c4 s1 rows16 62x38                    16188 cyc/call   sum b117fb28
n7 c4 s4 rows16 62x38                    16572 cyc/call   sum 6673b012
n7 c4 s8 rows16 62x38                    17340 cyc/call   sum 50dc4375
n7 c4 s12 rows16 62x38                    8368 cyc/call   sum 7fd05d50
n7 c4 s15 rows16 62x38                   15804 cyc/call   sum 0f71d0f4
n11 c1 s0 rows16 15x30                    5288 cyc/call   sum 8a034e21
n11 c1 s1 rows16 15x30                    5480 cyc/call   sum b7aa5257
n11 c1 s4 rows16 15x30                    5672 cyc/call   sum 1e404e64
n11 c1 s8 rows16 15x30                    6056 cyc/call   sum a6e8fbd8
n11 c1 s12 rows16 15x30                   2556 cyc/call   sum fcd576c1
n11 c1 s15 rows16 15x30                   5288 cyc/call   sum 120bcf7c
n11 c2 s0 rows16 29x54                    9012 cyc/call   sum e70fc29e
n11 c2 s1 rows16 29x54                    9012 cyc/call   sum 4744780c
n11 c2 s4 rows16 29x54                    9012 cyc/call   sum e248e37b
n11 c2 s8 rows16 29x54                    9012 cyc/call   sum 36148d99
n11 c2 s12 rows16 29x54                   4472 cyc/call   sum cdd5ef0f
n11 c2 s15 rows16 29x54                   9012 cyc/call   sum 44679ffc
n11 c3 s0 rows16 43x74                   12152 cyc/call   sum eef2d490
n11 c3 s1 rows16 43x74                   12344 cyc/call   sum e7a19bc7
n11 c3 s4 rows16 43x74                   12536 cyc/call   sum acf1386c
n11 c3 s8 rows16 43x74                   12920 cyc/call   sum 78e51c77
n11 c3 s12 rows16 43x74                   6508 cyc/call   sum fb26be46
n11 c3 s15 rows16 43x74                  12152 cyc/call   sum bad7cdd7
n11 c4 s0 rows16 64x110                  15484 cyc/call   sum 6c7488d7
n11 c4 s1 rows16 64x110                  15868 cyc/call   sum 913321e2
n11 c4 s4 rows16 64x110                  16252 cyc/call   sum 1ebfa799
n11 c4 s8 rows16 64x110                  17020 cyc/call   sum 2f6f44d1
n11 c4 s12 rows16 64x110                  8368 cyc/call   sum 0191bc86
n11 c4 s15 rows16 64x110                 15484 cyc/call   sum 253a0443
n13 c1 s0 rows16 16x28                    5288 cyc/call   sum c4e90b87
n13 c1 s1 rows16 16x28                    5480 cyc/call   sum 3f771f6a
n13 c1 s4 rows16 16x28                    5672 cyc/call   sum 221e95c8
n13 c1 s8 rows16 16x28                    6056 cyc/call   sum e5fecd3a
n13 c1 s12 rows16 16x28                   2556 cyc/call   sum 15cd119a
n13 c1 s15 rows16 16x28                   5288 cyc/call   sum 56813cdf
n13 c2 s0 rows16 20x36                    9012 cyc/call   sum d4b31451
n13 c2 s1 rows16 20x36                    9012 cyc/call   sum 5e61b0fb
n13 c2 s4 rows16 20x36                    9012 cyc/call   sum b8e3b111
n13 c2 s8 rows16 20x36                    9012 cyc/call   sum 9f4bc09f
n13 c2 s12 rows16 20x36                   4472 cyc/call   sum 9e18fa3c
n13 c2 s15 rows16 20x36                   9012 cyc/call   sum 83a00490
n13 c3 s0 rows16 42x43                   12152 cyc/call   sum 877e6bcc
n13 c3 s1 rows16 42x43                   12344 cyc/call   sum 954f97c5
n13 c3 s4 rows16 42x43                   12536 cyc/call   sum d7119e65
n13 c3 s8 rows16 42x43                   12920 cyc/call   sum 48c24f6c
n13 c3 s12 rows16 42x43                   6508 cyc/call   sum 5d1a9a58
n13 c3 s15 rows16 42x43                  12152 cyc/call   sum 9ade4345
n13 c4 s0 rows16 63x64                   15864 cyc/call   sum a0255a6c
n13 c4 s1 rows16 63x64                   16440 cyc/call   sum f84659ec
n13 c4 s4 rows16 63x64                   17016 cyc/call   sum efd958cb
n13 c4 s8 rows16 63x64                   18168 cyc/call   sum dbfbd3d0
n13 c4 s12 rows16 63x64                   8368 cyc/call   sum e02320b5
n13 c4 s15 rows16 63x64                  15864 cyc/call   sum 20fe60d7
n15 c1 s0 rows13 15x13                    5144 cyc/call   sum a8ea4984
n15 c1 s1 rows13 15x13                    5352 cyc/call   sum 453e0cc1
n15 c1 s4 rows13 15x13                    5560 cyc/call   sum dc6586a4
n15 c1 s8 rows13 15x13                    5976 cyc/call   sum 48b7fed9
n15 c1 s12 rows13 15x13                   2332 cyc/call   sum 79eb09a8
n15 c1 s15 rows13 15x13                   5144 cyc/call   sum 873cf193
n15 c2 s0 rows16 30x22                   10932 cyc/call   sum 82efde1b
n15 c2 s1 rows16 30x22                   10932 cyc/call   sum 57f6d512
n15 c2 s4 rows16 30x22                   10932 cyc/call   sum c4baa86a
n15 c2 s8 rows16 30x22                   10932 cyc/call   sum 0deb58b8
n15 c2 s12 rows16 30x22                   5428 cyc/call   sum ed5d9d07
n15 c2 s15 rows16 30x22                  10932 cyc/call   sum 58ca5d4f
n15 c3 s0 rows16 45x36                   14904 cyc/call   sum 481f5345
n15 c3 s1 rows16 45x36                   15160 cyc/call   sum 63412285
n15 c3 s4 rows16 45x36                   15416 cyc/call   sum 0f711947
n15 c3 s8 rows16 45x36                   15928 cyc/call   sum da95907b
n15 c3 s12 rows16 45x36                   7724 cyc/call   sum 846fac65
n15 c3 s15 rows16 45x36                  14904 cyc/call   sum 02901eca
n15 c4 s0 rows16 64x47                   19004 cyc/call   sum dd178e09
n15 c4 s1 rows16 64x47                   19516 cyc/call   sum e491132a
n15 c4 s4 rows16 64x47                   20028 cyc/call   sum 1ef17eb7
n15 c4 s8 rows16 64x47                   21052 cyc/call   sum 2d6bf7e9
n15 c4 s12 rows16 64x47                  10032 cyc/call   sum 294c8f6a
n15 c4 s15 rows16 64x47                  19004 cyc/call   sum d1a252cb
```

## 5. Options (real Hatari cycles, all rows IDENTICAL to the stock kernel)

Raw `res_mk_clock8.txt` (`mk.py`; cycles per call; stock vs (a) pre-masked, (b) pre-shifted, (c) generated):
```
c1 s0 rows10           stock                        1692
c1 s0 rows10           (a) premasked aligned        1416  ratio  0.84  IDENTICAL
c2 s0 rows16           stock                        4472
c4 s0 rows16           stock                        8368
c1 s4 rows10           stock                        3520
c1 s4 rows10           (a) premasked shifted        3384  ratio  0.96  IDENTICAL
c1 s4 rows10           (c) generated+zeroskip       3496  ratio  0.99  IDENTICAL
c2 s4 rows16           stock                        9204
c2 s4 rows16           (b) preshifted               5796  ratio  0.63  IDENTICAL
c4 s4 rows16           stock                       15804
c4 s4 rows16           (b) preshifted               9376  ratio  0.59  IDENTICAL
c1 s8 rows10           stock                        3760
c1 s8 rows10           (a) premasked shifted        3704  ratio  0.99  IDENTICAL
c1 s8 rows10           (c) generated+zeroskip       3940  ratio  1.05  IDENTICAL
c2 s8 rows16           stock                        9204
c2 s8 rows16           (b) preshifted               5796  ratio  0.63  IDENTICAL
c4 s8 rows16           stock                       16572
c4 s8 rows16           (b) preshifted               9376  ratio  0.57  IDENTICAL
c1 s12 rows10          stock                        4000
c1 s12 rows10          (a) premasked shifted        4024  ratio  1.01  IDENTICAL
c1 s12 rows10          (c) generated+zeroskip       3700  ratio  0.93  IDENTICAL
c2 s12 rows16          stock                        9204
c2 s12 rows16          (b) preshifted               5796  ratio  0.63  IDENTICAL
c4 s12 rows16          stock                       17340
c4 s12 rows16          (b) preshifted               9376  ratio  0.54  IDENTICAL
```
- **(a) pre-masked data** (stored `~M`, the kernel skips move/or/or/not): aligned **0.84** (1,692 -> 1,416 for 10 rows); shifted **0.96-1.01**: the mask has to be shifted as well (one more `ror.l`), which eats what or/or/not saves. 96 % of draws are shifted. A persistent mask array (+1/3 of the bank) would also have the validity problem of (b).
- **(b) pre-shifted data**, long ops, dest column = `[mask long (M,M)][p0:p1 long][p2:0 long]`, 108 cycles per dest column: 2 columns 5,796 vs 9,204 (**0.63**), 4 columns 9,376 vs 15,804-17,340 (**0.54-0.59**). Memory (`out/preshift_budget.txt`):
```
A $3d16e       bitmaps 280  source data   65802 B   one pre-shifted variant (mask+planes, c+1 columns)  186000 B
B $5a402       bitmaps  64  source data   23634 B   one pre-shifted variant (mask+planes, c+1 columns)   65040 B
cars $306c4    bitmaps  96  source data   50536 B   one pre-shifted variant (mask+planes, c+1 columns)  121128 B
player $2156a  bitmaps  45  source data   14244 B   one pre-shifted variant (mask+planes, c+1 columns)   40524 B
total source 154216 B; ONE shift variant of every bitmap 412692 B; all 15 shifts 6190380 B (6045 KB) vs 215 KB free at 1 MB
shift variants of the whole set that fit in 215 KB: 0.53
```
  Only the player's own sprites (constant x, 3 bitmaps) would fit (and are 26 % of the stage), **but the banks are not immutable**: `ram_race_grid` vs `ram_race_start` differ by 217 bytes in 16 clusters of ~48 bytes inside the player bank (`$21a69-$24e20`), and `ram_entry_1024` vs `ram_race_start` by 36,989 bytes in `$19000-$62000` (pointer fix-ups at `$1b077`, scenery B, cars). A cache has to validate the source rows on every use (Populous 2 `pop2_spr` does one `cmpm.l` per long): 6 `cmpm.l` (20 cycles each) = 120 cycles per 4-column row cut the saving to ~16 k per pass (2.3 % of the pass) for a cache, a build routine and a flush rule. Not built.
- **(c) generated straight-line kernel**: the existing shifted loop is within ~3 % of the best sequence I could write (per plane `moveq / move.w / ror.l / swap` 117 + masks 24 + 7 read-modify-writes per dest column 84..168 + 18 = ~327 for a 1-column row vs the stock 334). The immediate-shift family with zero-mask skip (`pc_c1`, shifts 4 / 8 / 12) measures **0.99 / 1.05 / 0.93**. The zero-mask skip alone could save ~12 % of the row cycles (34 % / 40 % / 31 % / 13 % of the destination column-words of the 1 / 2 / 3 / 4-column shifted draws have an empty mask, computed from the real bitmaps and the logged x/rows) but the test costs 12 cycles per column and 32 loops (16 kernels x aligned/shifted) would have to be rewritten.
- **(d) early-out** (`early.py`): cycles per dead call in the kernel: rows = 0: 108; x off screen: 16-36; y >= 200: 80. 4 calls per pass in race_up have rows <= 0 and 2 are off screen: ~0.2 k. The glue before the call (490 cycles) is the cost and is the code that decides. Inactive slots: 164 cycles x 19-25 per pass = 3-4 k; an early-out in the `$e4dc` loop would save ~1.3 k. Not worth a patch.

## 6. (e) The STE blitter

Hatari blitter model, raw `out/blitter_micro.txt`:
```
Hatari 2.6.1 STE 8 MHz, harness blob (SR $2700), e CycleCounter at markers (raw timeline, deltas in cycles):
m_a0 -> m_a1  +25212   100 x register set-up sequence of one blit (14 instructions + dbra, no start)           = 252 per iteration (242 without dbra)
m_b0 -> m_b1  +60808   100 x HOG blit D &= ~S, xcount 3, ycount 16 (48 words), skew 5, + 3 register writes + start + dbra = 608
m_c0 -> m_c1  +188808  100 x same, xcount 5, ycount 32 (160 words)                                              = 1,888   -> (1888-608)/(160-48) = 11.4 cycles per word
m_d0 -> m_d1  +41608   100 x LOP 3 (S only), xcount 3, ycount 16 (48 words)                                      = 416     -> 7.4 per word
m_e0 -> m_e1  +26168   20 x non-HOG blit (48 words) + CPU polling BUSY (addq.l/btst/bne loop, 34 cycles per iteration): 1,308 per blit, 380 polling iterations in total (19 per blit = ~650 CPU cycles) -> the blit takes ~2.2x its HOG time, the CPU keeps ~50 %
m_f0 -> m_f1  +36008   1000 x the same polling loop without a blit = 36 per iteration (calibration)
probe: $ff8a28 written $5aa5 reads back $5aa5, $ff8a3c reads 0 (blitter present)
```
- Register set-up of one blit = 242 cycles; HOG blit D &= ~S = **11.4 cycles per word**; copy 7.4; non-HOG with the CPU polling BUSY: the blit takes ~2.2x as long (the CPU keeps ~50 % of the bus), i.e. non-HOG is slower than the CPU kernels; only HOG is usable.
- **Formulation** (`msb.s`; skew + NFSR + endmasks as in `pop2_spr`): endmask1 = `$ffff >> s`, endmask3 = `$ffff << (16 - s)`, SKEW = s | $40, xcount = columns + 1 (columns if s = 0), source xinc 2 / yinc `row bytes - 2 (cols - 1)` (a plane's words of one row are adjacent in the plane-major layout), dest xinc 8 / yinc `168 - 8 n`. Passes per sprite part: P mask-build passes (T = OR of the data planes, one word per column, LOP S then S|D), 4 mask passes (D &= ~T on all four dest planes, LOP 4), P data passes (D |= S, LOP 7): **10 passes (12 for the 4-plane nibble 15)**; one pass cannot do two planes because the skew mixes consecutive stream words. A stored-mask variant (7 passes) needs a persistent mask array (validity problem of (b)). Rows are split so that a pass is at most BUDGET (1,800) cycles.
- **3-4 column sprites need 2-3 groups** (the pair, then one single per further column); groups are drawn as independent shifted sprites (the word two groups share holds disjoint masks: `(D&~Ma|Sa)&~Mb|Sb = D&~(Ma|Mb)|Sa|Sb`).
- **Prototype** `work/sprite/msb.s` (harness differential test): 1-4 columns, nibbles 7/11/13/15, interior sprites only (x >= 0, y >= 0, all dest columns on screen: everything else jumps to the stock entry), writes `$100c` like the stock. Results (budget 1,800, 16 rows; `res_blit_matrix_b1800.txt` shows the pre-group-split run in which the 3-4 column rows DIFFER, `res_blit_c34.txt` is the final 3-4 column run):
```
n 7 c1 s 0 rows 10  stock     1692  blit     3188  ratio  1.88  IDENTICAL
n 7 c1 s 3 rows 10  stock     3520  blit     3792  ratio  1.08  IDENTICAL
n 7 c1 s 4 rows 10  stock     3520  blit     3796  ratio  1.08  IDENTICAL
n 7 c1 s 8 rows 10  stock     3760  blit     3796  ratio  1.01  IDENTICAL
n 7 c1 s15 rows 10  stock     4240  blit     3792  ratio  0.89  IDENTICAL
n 7 c2 s 0 rows 16  stock     4472  blit     5740  ratio  1.28  IDENTICAL
n 7 c2 s 3 rows 16  stock     9204  blit     6680  ratio  0.73  IDENTICAL
n 7 c2 s 4 rows 16  stock     9204  blit     6684  ratio  0.73  IDENTICAL
n 7 c2 s 8 rows 16  stock     9204  blit     6684  ratio  0.73  IDENTICAL
n 7 c2 s15 rows 16  stock     9204  blit     6680  ratio  0.73  IDENTICAL
n 7 c3 s 0 rows 16  stock     6508  blit     7600  ratio  1.17  DIFFER
n 7 c3 s 3 rows 16  stock    12408  blit     8540  ratio  0.69  DIFFER
n 7 c3 s 4 rows 16  stock    12408  blit     8544  ratio  0.69  DIFFER
n 7 c3 s 8 rows 16  stock    12792  blit     8544  ratio  0.67  DIFFER
n 7 c3 s15 rows 16  stock    13560  blit     8540  ratio  0.63  DIFFER
n 7 c4 s 0 rows 16  stock     8368  blit     9452  ratio  1.13  DIFFER
n 7 c4 s 3 rows 16  stock    15804  blit    10392  ratio  0.66  DIFFER
n 7 c4 s 4 rows 16  stock    15804  blit    10396  ratio  0.66  DIFFER
n 7 c4 s 8 rows 16  stock    16572  blit    10396  ratio  0.63  DIFFER
n 7 c4 s15 rows 16  stock    18108  blit    10392  ratio  0.57  DIFFER
n11 c1 s 0 rows 16  stock     2556  blit     3884  ratio  1.52  IDENTICAL
n11 c1 s 3 rows 16  stock     5288  blit     4824  ratio  0.91  IDENTICAL
n11 c1 s 4 rows 16  stock     5288  blit     4828  ratio  0.91  IDENTICAL
n11 c1 s 8 rows 16  stock     5672  blit     4828  ratio  0.85  IDENTICAL
n11 c1 s15 rows 16  stock     6440  blit     4824  ratio  0.75  IDENTICAL
n11 c2 s 0 rows 16  stock     4472  blit     5740  ratio  1.28  IDENTICAL
n11 c2 s 3 rows 16  stock     9012  blit     6680  ratio  0.74  IDENTICAL
n11 c2 s 4 rows 16  stock     9012  blit     6684  ratio  0.74  IDENTICAL
n11 c2 s 8 rows 16  stock     9012  blit     6684  ratio  0.74  IDENTICAL
n11 c2 s15 rows 16  stock     9012  blit     6680  ratio  0.74  IDENTICAL
n11 c3 s 0 rows 16  stock     6508  blit     7600  ratio  1.17  DIFFER
n11 c3 s 3 rows 16  stock    12152  blit     8540  ratio  0.70  DIFFER
n11 c3 s 4 rows 16  stock    12152  blit     8544  ratio  0.70  DIFFER
n11 c3 s 8 rows 16  stock    12536  blit     8544  ratio  0.68  DIFFER
n11 c3 s15 rows 16  stock    13304  blit     8540  ratio  0.64  DIFFER
n11 c4 s 0 rows 16  stock     8368  blit     9452  ratio  1.13  DIFFER
n11 c4 s 3 rows 16  stock    15484  blit    10392  ratio  0.67  DIFFER
n11 c4 s 4 rows 16  stock    15484  blit    10396  ratio  0.67  DIFFER
n11 c4 s 8 rows 16  stock    16252  blit    10396  ratio  0.64  DIFFER
n11 c4 s15 rows 16  stock    17788  blit    10392  ratio  0.58  DIFFER
n13 c1 s 0 rows 16  stock     2556  blit     3884  ratio  1.52  IDENTICAL
n13 c1 s 3 rows 16  stock     5288  blit     4824  ratio  0.91  IDENTICAL
n13 c1 s 4 rows 16  stock     5288  blit     4828  ratio  0.91  IDENTICAL
n13 c1 s 8 rows 16  stock     5672  blit     4828  ratio  0.85  IDENTICAL
n13 c1 s15 rows 16  stock     6440  blit     4824  ratio  0.75  IDENTICAL
n13 c2 s 0 rows 16  stock     4472  blit     5740  ratio  1.28  IDENTICAL
n13 c2 s 3 rows 16  stock     9012  blit     6680  ratio  0.74  IDENTICAL
n13 c2 s 4 rows 16  stock     9012  blit     6684  ratio  0.74  IDENTICAL
n13 c2 s 8 rows 16  stock     9012  blit     6684  ratio  0.74  IDENTICAL
n13 c2 s15 rows 16  stock     9012  blit     6680  ratio  0.74  IDENTICAL
n13 c3 s 0 rows 16  stock     6508  blit     7600  ratio  1.17  DIFFER
n13 c3 s 3 rows 16  stock    12152  blit     8540  ratio  0.70  DIFFER
n13 c3 s 4 rows 16  stock    12152  blit     8544  ratio  0.70  DIFFER
n13 c3 s 8 rows 16  stock    12536  blit     8544  ratio  0.68  DIFFER
n13 c3 s15 rows 16  stock    13304  blit     8540  ratio  0.64  DIFFER
n13 c4 s 0 rows 16  stock     8368  blit     9452  ratio  1.13  DIFFER
n13 c4 s 3 rows 16  stock    15864  blit    10392  ratio  0.66  DIFFER
n13 c4 s 4 rows 16  stock    15864  blit    10396  ratio  0.66  DIFFER
n13 c4 s 8 rows 16  stock    17016  blit    10396  ratio  0.61  DIFFER
n13 c4 s15 rows 16  stock    19320  blit    10392  ratio  0.54  DIFFER
n15 c1 s 0 rows 13  stock     2332  blit     4056  ratio  1.74  IDENTICAL
n15 c1 s 3 rows 13  stock     5144  blit     4932  ratio  0.96  IDENTICAL
n15 c1 s 4 rows 13  stock     5144  blit     4936  ratio  0.96  IDENTICAL
n15 c1 s 8 rows 13  stock     5560  blit     4936  ratio  0.89  IDENTICAL
n15 c1 s15 rows 13  stock     6392  blit     4932  ratio  0.77  IDENTICAL
n15 c2 s 0 rows 16  stock     5428  blit     6716  ratio  1.24  IDENTICAL
n15 c2 s 3 rows 16  stock    10932  blit     7784  ratio  0.71  IDENTICAL
n15 c2 s 4 rows 16  stock    10932  blit     7788  ratio  0.71  IDENTICAL
n15 c2 s 8 rows 16  stock    10932  blit     7788  ratio  0.71  IDENTICAL
n15 c2 s15 rows 16  stock    10932  blit     7784  ratio  0.71  IDENTICAL
n15 c3 s 0 rows 16  stock     7724  blit     8960  ratio  1.16  DIFFER
n15 c3 s 3 rows 16  stock    14904  blit    10028  ratio  0.67  DIFFER
n15 c3 s 4 rows 16  stock    14904  blit    10032  ratio  0.67  DIFFER
n15 c3 s 8 rows 16  stock    15416  blit    10032  ratio  0.65  DIFFER
n15 c3 s15 rows 16  stock    16440  blit    10028  ratio  0.61  DIFFER
n15 c4 s 0 rows 16  stock    10032  blit    11196  ratio  1.12  DIFFER
n15 c4 s 3 rows 16  stock    19004  blit    12264  ratio  0.65  DIFFER
n15 c4 s 4 rows 16  stock    19004  blit    12268  ratio  0.65  DIFFER
n15 c4 s 8 rows 16  stock    20028  blit    12268  ratio  0.61  DIFFER
n15 c4 s15 rows 16  stock    22076  blit    12264  ratio  0.56  DIFFER

-- final 3-4 columns (pair + singles):
n 7 c3 s 0 rows 16  stock     6508  blit     9648  ratio  1.48  IDENTICAL
n 7 c3 s 3 rows 16  stock    12408  blit    11528  ratio  0.93  IDENTICAL
n 7 c3 s 4 rows 16  stock    12408  blit    11536  ratio  0.93  IDENTICAL
n 7 c3 s 8 rows 16  stock    12792  blit    11536  ratio  0.90  IDENTICAL
n 7 c3 s15 rows 16  stock    13560  blit    11528  ratio  0.85  IDENTICAL
n 7 c4 s 0 rows 16  stock     8368  blit    13360  ratio  1.60  IDENTICAL
n 7 c4 s 3 rows 16  stock    15804  blit    16180  ratio  1.02  IDENTICAL
n 7 c4 s 4 rows 16  stock    15804  blit    16192  ratio  1.02  IDENTICAL
n 7 c4 s 8 rows 16  stock    16572  blit    16192  ratio  0.98  IDENTICAL
n 7 c4 s15 rows 16  stock    18108  blit    16180  ratio  0.89  IDENTICAL
n11 c3 s 0 rows 16  stock     6508  blit     9648  ratio  1.48  IDENTICAL
n11 c3 s 3 rows 16  stock    12152  blit    11528  ratio  0.95  IDENTICAL
n11 c3 s 4 rows 16  stock    12152  blit    11536  ratio  0.95  IDENTICAL
n11 c3 s 8 rows 16  stock    12536  blit    11536  ratio  0.92  IDENTICAL
n11 c3 s15 rows 16  stock    13304  blit    11528  ratio  0.87  IDENTICAL
n11 c4 s 0 rows 16  stock     8368  blit    13360  ratio  1.60  IDENTICAL
n11 c4 s 3 rows 16  stock    15484  blit    16180  ratio  1.04  IDENTICAL
n11 c4 s 4 rows 16  stock    15484  blit    16192  ratio  1.05  IDENTICAL
n11 c4 s 8 rows 16  stock    16252  blit    16192  ratio  1.00  IDENTICAL
n11 c4 s15 rows 16  stock    17788  blit    16180  ratio  0.91  IDENTICAL
n13 c3 s 0 rows 16  stock     6508  blit     9648  ratio  1.48  IDENTICAL
n13 c3 s 3 rows 16  stock    12152  blit    11528  ratio  0.95  IDENTICAL
n13 c3 s 4 rows 16  stock    12152  blit    11536  ratio  0.95  IDENTICAL
n13 c3 s 8 rows 16  stock    12536  blit    11536  ratio  0.92  IDENTICAL
n13 c3 s15 rows 16  stock    13304  blit    11528  ratio  0.87  IDENTICAL
n13 c4 s 0 rows 16  stock     8368  blit    13360  ratio  1.60  IDENTICAL
n13 c4 s 3 rows 16  stock    15864  blit    16180  ratio  1.02  DIFFER
n13 c4 s 4 rows 16  stock    15864  blit    16192  ratio  1.02  DIFFER
n13 c4 s 8 rows 16  stock    17016  blit    16192  ratio  0.95  DIFFER
n13 c4 s15 rows 16  stock    19320  blit    16180  ratio  0.84  DIFFER
n15 c3 s 0 rows 16  stock     7724  blit    11216  ratio  1.45  IDENTICAL
n15 c3 s 3 rows 16  stock    14904  blit    13352  ratio  0.90  IDENTICAL
n15 c3 s 4 rows 16  stock    14904  blit    13360  ratio  0.90  IDENTICAL
n15 c3 s 8 rows 16  stock    15416  blit    13360  ratio  0.87  IDENTICAL
n15 c3 s15 rows 16  stock    16440  blit    13352  ratio  0.81  IDENTICAL
n15 c4 s 0 rows 16  stock    10032  blit    15520  ratio  1.55  IDENTICAL
n15 c4 s 3 rows 16  stock    19004  blit    18724  ratio  0.99  IDENTICAL
n15 c4 s 4 rows 16  stock    19004  blit    18736  ratio  0.99  IDENTICAL
n15 c4 s 8 rows 16  stock    20028  blit    18736  ratio  0.94  IDENTICAL
n15 c4 s15 rows 16  stock    22076  blit    18724  ratio  0.85  IDENTICAL
```
  Only `n13 c4` (155 calls in the traces, 1.5 % of the draws) DIFFERs (its row layout is not pair + singles; not investigated). Rows 3 / 6 (n7, s 4): c1 1,308 vs 2,592 / 2,256 vs 3,108; c2 2,080 vs 2,940 / 3,724 vs 3,804 (`res_blit_rows3.txt`, `res_blit_rows6.txt`). Fixed cost 2.1 k per call (1-2 columns), 4.2 k (3), 6.2 k (4); slopes 172 / 288 / 460 / 632 cycles per row against stock 334 / 524 / ~775 / 880 (+ 0.4-2.8 k fixed): **break-even 10 / 6 / 13 / 14 rows**; aligned calls always lose (1.1-1.9x).
- **Prediction for the real call lists** (`out/blit_prediction.txt`; blitter used only when cheaper, interior sprites only, type-0 calls only):
```
Predicted saving of the HOG blitter path on type-0 calls (measured fixed costs/slopes, interior sprites only; calls that clip at an edge stay CPU), per frame:
scene        t0 kernel cyc  saving  (% of t0)  calls on blitter/frame   by cols 1,2,3,4
race_grid      155783     23275    14.9%     10.6        [5743, 7344, 926, 9261]
race_start     154916     24662    15.9%     11.3        [4166, 6984, 5190, 8322]
race_up        159102     28990    18.2%      9.0        [2552, 18530, 970, 6938]
race_drive     139002     21963    15.8%     11.4        [3343, 9572, 1726, 7322]
```
  **Measured replay** (`isr.py`, harness `kb3.s`: 17 real type-0 calls of race_start drawn 30 times in a row with interrupts enabled and the game's ISRs running; raw `out/isr_b1800.txt`):
```
stock total cycles for 30 frames of draws (interrupts on): 5645148  Timer B ISR entries: 729
   LineCycles at ISR entry: min 240 median 464 p90 476 p99 492 max 500  (a scanline = 512 cycles)
blit total cycles for 30 frames of draws (interrupts on): 4916668  Timer B ISR entries: 738
   LineCycles at ISR entry: min 0 median 464 p90 472 p99 492 max 508  (a scanline = 512 cycles)
```
  i.e. **-12.9 %** (-24 k per 17-call frame).
- **Raster / IKBD latency (fidelity limit)**: the Timer B ISR `$d616` writes 7 palette longs as soon as it is entered (no beam sync, `00d63a-00d652`), ~32 Timer B interrupts fall into the 1.4 VBL of the stage. A HOG pass of 1,800 cycles (3.5 scanlines) holds off the 68000, and with it the interrupt acknowledge, on real hardware. Hatari's `LineCycles` at the ISR entry did **not** show it (above: median 464, p99 492 for both), i.e. Hatari's blitter/interrupt model does not delay the entry: [INFERENCE] real hardware would, so -13 % is an upper bound for a raster-safe version (passes <= ~200 cycles, or a beam / Timer B guard that falls back to the CPU kernel in the upper ~46 % of every VBL where the raster ISR runs). The IKBD byte time is 10,240 cycles: 1,800 is safe for it (st-game-speedup rule).
- **Mega STE: not measured on the Mega STE machine.** `megaste4m_race_start.sav` restores and runs (VBL and `$100e` advance), but a breakpoint at `$7a88` is never hit; with `$d1ca`/`$7b86`, `:once :file` and a `VBL >` condition the script runs and `loadbin` works, then the game sits in the post-flip VBL wait `$d20c` and my blob never executes (three attempts, scripts `work/sprite/mega_smoke.py`; no Hatari-side explanation found). The only 16 MHz data is the STE model with `hatari-option --cpuclock 16` (`res_blit_clock16.txt`, `res_mk_clock16.txt`): **every number equals the 8 MHz run** (Hatari's CycleCounter scales CPU and blitter alike there), so it says nothing about a real Mega STE, where the 16 MHz CPU (with its cache) runs against an 8 MHz bus and blitter. [INFERENCE] the blitter is relatively worse on a Mega STE (CPU kernels in the cache speed up, the bus-bound blitter does not) and that machine is already at 2.7-2.9 VBL, below the 3-VBL sync floor: keep the CPU path there (probe `$ff8e21` / `$ff8a3c`).
```
n 7 c1 s 0 rows 10  stock     1692  blit     3248  ratio  1.92  IDENTICAL
n 7 c1 s 4 rows 10  stock     3520  blit     3856  ratio  1.10  IDENTICAL
n 7 c2 s 0 rows 16  stock     4472  blit     5800  ratio  1.30  IDENTICAL
n 7 c2 s 4 rows 16  stock     9204  blit     6744  ratio  0.73  IDENTICAL
n 7 c3 s 0 rows 16  stock     6508  blit     9648  ratio  1.48  IDENTICAL
n 7 c3 s 4 rows 16  stock    12408  blit    11536  ratio  0.93  IDENTICAL
n 7 c4 s 0 rows 16  stock     8368  blit    13360  ratio  1.60  IDENTICAL
n 7 c4 s 4 rows 16  stock    15804  blit    16192  ratio  1.02  IDENTICAL
```
- Integration would be a data patch of the pointer tables (`$399c-$3a28` full entries, `$38ac-$3960` post entries: static data, no code writes them) plus a bus-error-guarded probe of `$ff8a28/$ff8a3c`; the HUD routines `$f182 $f690 $f74a $f7d4` also use `$3a14` (nibble-15 kernels) and would be redirected too. One site per patch file in `msrpatch.py` means several `ms_*` files.

## 7. Clouds (`$de1c` erase, `$de6c` draw: 80 k per pass, 10 %)

- 12 slots, 1-plane sprites up to 64-80 px. Per sky pixel (backdrop bit B = 0; backdrop plane `$6f000`, 40 bytes per row): erase `P0 |= ~B` (`$122e4`: `move.w (a1)+,d0 / not.w d0 / or.w d0,(a3)`, 5 words per row), draw `P0 &= ~C | B` (`$15052`: `lsr.l d6 / not.w / or.w x(a4),d / and.w d,x(a3)`), so the pair overwrites P0 on the sky pixels of its rectangle independent of the old content and leaves B = 1 pixels untouched.
- **Positions repeat** (`cloudtrace.py` slot dump at every `$de1c`, `cloudan.py`): cloud (x, y, frame idx) equals the one two passes ago (same back buffer) in **2964 / 2964 cloud-passes standing (race_grid), 1281 / 2496 (51 %) driving (race_start)**; the 12 clouds change together.
- **Skipping is not exact.** Prototype `work/sprite/rejected/ms_cloud_a.s` (site `$de1c`, blob `$BC000`) + `ms_cloud_b.s` (site `$de6c`, blob `$BC400`; data `$BCC00`): all-or-nothing skip when the 12 keys, `$2a` and the pass counter `$100e` match this back buffer's record (record invalidated when every `$28 = $ffff` = race init; rows >= 65 are still erased/drawn because the horizon strip copy overwrites rows 65-69 before the clouds; `$28/$2a/$100c` side effects replayed). Gate output (`out/gate_cloud_rejected.txt`):
```
patch set: ms_cloud_a ms_cloud_b  (live image cloud_a+cloud_b.img, 42752 B)
PIXELS race_grid   at VBL 25100 flip  10: DIFFER (86 bytes of 64000)  md5 641eb859 d5a188cf (stock 81dfec87 d5a188cf)
PIXELS race_grid   at VBL 25100 flip  40: DIFFER (86 bytes of 64000)  md5 b79da283 7481e0c7 (stock 7481e0c7 7481e0c7)
PIXELS race_start  at VBL 16400 flip  10: IDENTICAL  md5 3da506a7 c54efba9 (stock 3da506a7 c54efba9)
PIXELS race_start  at VBL 16400 flip  40: IDENTICAL  md5 90858e13 4858b4b8 (stock 90858e13 4858b4b8)
RESULT: DIFFERENCES FOUND
```
  The 86 bytes are plane-0 bytes of `$70000` in rows 19-64 at cloud rectangles over the minimap box (px 32-111) and the right HUD column (px 288-303).
- **What depends on the erase**: (i) the minimap `$f22c` (after the draw) and the HUD stages are read-modify-write on plane 0; the erase resets plane 0 of the whole cloud rectangle to the sky before they run, so it also removes their previous-pass pixels; (ii) the HUD repair stages between erase and draw write plane 0 inside cloud rectangles in 10-30 % of the passes (`foot.py`/`footan.py`, raw `raw/foot_*.log.gz`: 2,525 bytes written between erase and draw while standing; clouds 2/3/4/7/8 are touched in 22-77 of 250 passes, clouds 0/1/5/6/9/10/11 never in race_grid); (iii) overlapping clouds: skipping one cloud while an overlapping cloud is erased removes its pixels. A provable subset (clouds outside all HUD footprints, closure over overlapping clouds: ~7 of 12 while standing) needs the footprints of 8 HUD routines (all of `f1c0 f3b6 f430 f53c f90c f620 f76a f7f0 f214 f22c` touch the sky band or `$6f000`); not built.
- Race restart does not clear the screens: `$dd18/$dd1c` (cloud init) runs with `$100e = 0` and no `$d8e0` (both-screen clear, callers `$719c $7368 $73e6 $769a $7be0 $7c0c $7d26 $842c` are outside the race loop) (`restart_trace.py`).

## 8. RAM and machines

- Free ranges for any future sprite code/data (per lead): `$B3D00-$B6FFF` and `$B9000-$BFFFF` (same address at 1 MB, 4 MB with `pp_bigram_cache`, and Mega STE 4 MB: patches/README.md map); **`$D0000-$E7FFF` is claimed by rd_***. My unit blobs and test data used `$C0000-$E1000` only inside throw-away snapshots. The blitter prototype needs ~2 KB code + 1 KB mask rows; the rejected cloud patches used `$BC000-$BCE00`.
- Pre-shifted data: 413 KB per shift variant of the whole set, 0.53 variants fit in 215 KB; 4 MB does not help (the free run starts at `$C7900`, and the rd_* claim applies).
- Not tested: cold boots (nothing was built), 2-minute drive, 4 MB / Mega STE boots of any ms_* patch.

## 9. What was built

Nothing is shipped (`patches/` has no `ms_*`). Kept: the harness (`kb.s kb.py kb2.py kb3.s mk.s mk.py msb.s isr.py early.py unit.py trace.py parse.py analyze.py report.py cloudtrace.py cloudan.py foot.py footan.py restart_trace.py dbg_blit*.py mega_smoke.py`), the blitter prototype `msb.s`, the rejected cloud patches, private tool copies `msrpatch_priv.py` / `msrabtest_priv.py` (ROOT / AB overrides; `python3 work/sprite/msrpatch_priv.py verify` ends `ALL OK`).

## 10. Recommendation

| option | measured gain per pass (8 MHz STE) | % of 687 k pass (rd_* on) | risk | machines |
|---|---|---|---|---|
| (a) pre-masked | aligned -16 % (4 % of calls): < 1 k | 0.1 % | persistent masks | all |
| (b) pre-shifted, whole set | -37..-46 % of shifted draws (~50 k) | 7 % | 6 MB needed: **infeasible** | - |
| (b) pre-shifted, player only + validation | ~16 k | 2.3 % | mutable banks; cache + build + validation | all |
| (c) generated kernels | 0.93-1.05 | ~0 | 32 loops rewritten | all |
| (d) early-out | ~0.2 k dead calls + ~1.3 k inactive slots | 0.2 % | low | all |
| (e) blitter, HOG, break-even routing | **-24 k measured (-13 %), 22-29 k predicted** | **3.5-4.2 %** | raster ISR / IKBD latency on real hardware (Hatari shows none); 10-12 passes per part; 4 columns = 3 groups; n13 c4 DIFFER | STE / Mega ST with a blitter at 8 MHz; not Mega STE 16 MHz [INFERENCE] |
| clouds skip | 40-80 k (51-100 % of passes) | 6-12 % | **not identical (86 B), rejected** | all |

The exact CPU levers total 1-2 % of the pass; the blitter is 3.5-4 % with an open raster-latency question for the user (4.29 -> ~4.13 VBL); the clouds are the only 6-12 % item and need the HUD footprints (or a game-side change) before they can be exact. Nothing here brings the pass under 4 VBL on its own.

## 11. Unproven / caveats

- Hatari only. The blitter's bus sharing with the 68000, the HOG hold-off of interrupts and the Mega STE machine are not measured (section 6).
- The type-1/3 composite parts (`$15442`, ~45 k per pass) were not microbenchmarked; they call the same kernels through the post entries, the blitter prediction covers the type-0 calls only.
- The `n13 c4` blitter kernel DIFFERs; the prototypes are interior-only (edge clipping falls back to the stock entry).
- The T4 fits for 3 and 4 columns aligned are poor (12 / 145 calls); the harness matrix (section 4) is the reliable source there.
