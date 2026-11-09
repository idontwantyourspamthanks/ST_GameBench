# P7 cell early-outs for the MW1 terrain geometry stage (patches `p7_cell_pre`, `p7_cell_obj`, `p7_cell_edge`)

Render.md row #12 ("lazy transform, ≤4-7 %, high effort, high risk") and the MW2 `p7_cell_cull` idea, applied to MW1.
All three patches are `default: no`, blob range `$B5000-$B57FF`, no site overlaps with p3b/p4/p5 (sites `$18304`, `$1748c`, `$17ca0`).
Every number is from a run in this session (raw output quoted) or marked `[INFERENCE]`. Scripts were throw-aways in `/tmp/mw1c/` (not kept; method in section 7).

## 1. Result

**Built: three exact early-outs in the cell stage (-1.6 … -2.2 % of a frame). Not built: skipping vertex transforms (section 5: net gain ≤ ~1 % for a 25-site patch family, with a pool-layout change).**

| patch | site | what it skips |
|---|---|---|
| `p7_cell_pre` | `$18304` (6 B) | per frame: builds a 256-byte hash table of the in-range object cells (needs `p7_cell_obj`) |
| `p7_cell_obj` | `$1748c` (6 B) | the per-cell scan `jsr $1d41e` (262 cy/cell) when the table proves the cell holds no object |
| `p7_cell_edge` | `$17ca0` (8 B) | the five `bsr $17fa0` edge-clip calls of a cell whose 4 corner outcodes are all 0 |

Enable all three together (`p7_cell_obj` alone never skips: its `VALID` word is 0 until `p7_cell_pre` ran; `p7_cell_pre` alone is inert; `p7_cell_edge` is independent).

**Identity gate** (`mw1ab.py --only p7_cell_pre p7_cell_obj p7_cell_edge --flips 8 40`, all 3 buffers, absolute VBL, patched live at the flip). Raw:

```
stand --flips 8: IDENTICAL; flips/1000VBL 82 -> 84; cycles/frame 1907634 -> 1859829 (-47805, -2.51 %)
stand --flips 40: IDENTICAL
walk --flips 8: IDENTICAL; flips/1000VBL 111 -> 113; cycles/frame 1414722 -> 1384460 (-30262, -2.14 %)
walk --flips 40: IDENTICAL
turn --flips 8: IDENTICAL; flips/1000VBL 152 -> 154; cycles/frame 1029733 -> 1017677 (-12057, -1.17 %)
turn --flips 40: IDENTICAL
busy --flips 8: IDENTICAL; flips/1000VBL 78 -> 81; cycles/frame 1990879 -> 1946292 (-44588, -2.24 %)
busy --flips 40: IDENTICAL
ALL IDENTICAL
```

Split (walk / stand, flips 8): `pre+obj` -11277 (-0.80 %) / -19114 (-1.00 %); `edge` alone -17906 (-1.27 %) / -28810 (-1.51 %).

**View-variation gate** (not in `mw1ab`): same snapshot and absolute VBL, at the first flip poke the master heading `$12c98` and its copy `$15114` to H (16 values 0..960 step 64, i.e. every one of the 8 `$1710e` heading sectors twice), save the 3 buffers 6 flips later, base vs patched. walk 16/16 and stand 16/16 **IDENTICAL** (the md5s differ between headings, so the pokes took effect), e.g. `walk heading= 448: IDENTICAL md5 638f733a 1e3c3e0f 372094b4 | 638f733a 1e3c3e0f 372094b4`.

**Per frame counts** (exactly aligned windows: both runs start at the same flip, `profile on` + the end breakpoint armed from the same debugger file, 15 complete frames, `profile counts`; patched set applied live at the start flip):

| | walk | stand | turn | busy |
|---|---|---|---|---|
| cells entering `$17444` | 150 → 150 | 150 → 150 | 150 → 150 | 150 → 150 |
| … non-all-invalid (`$17466`) | 120.3 → 120.3 | 129 → 129 | 127.7 → 127.7 | 118 → 118 |
| vertices `movem.l d3-d5,(a3)` (24 sites) | 191 → 191 | 191 → 191 | 191 → 191 | 191 → 191 |
| … projected (`movem.w d3-d6,(a3)`) | 129 → 129 | 143 → 143 | 136.5 → 136.5 | 128 → 128 |
| emitted cells (`$17a04`) | 31.3 → 31.3 | 52 → 52 | 5.3 → 5.3 | 50 → 50 |
| polygons (`$19d6a`) | 43.5 → 43.5 | 82 → 82 | 6.6 → 6.6 | 88 → 88 |
| edges walked (`$19f20`) | 140.9 → 140.9 | 261 → 261 | 22.1 → 22.1 | 307 → 307 |
| object scans `$1d41e` | 120.3 → **0** | 129 → **6** | 127.7 → **0** | 118 → **4.9** |
| edge-clip calls `$17fa0` | 183.3 → **87.7** | 285 → **120** | 57 → **50.7** | 300 → **120** |

Cells, vertices, polygons, edges and fill passes are unchanged by construction (no cell or vertex is skipped); only the two redundant call families disappear. (The 8 `$1d41e` calls left in stand/busy are hash collisions or real object cells, which run the original routine.)

**Cycles per frame from `profile cycles`** (same aligned windows):

| | walk | stand | turn | busy |
|---|---|---|---|---|
| total / frame | 1442153 → 1412881 (-2.03 %) | 2104513 → 2058555 (-2.18 %) | 906683 → 892126 (-1.61 %) | 2099122 → 2052379 (-2.23 %) |
| `$1d41e` object scan | 26319 → 0 | 34672 → 1680 | 26070 → 0 | 31692 → 1375 |
| `$17f20-$18304` (clip `$17fa0`) | 52549 → 39148 | 71924 → 48804 | 19418 → 18527 | 69419 → 44203 |
| `$17c6c` emit | 14624 → 11972 | 24907 → 20384 | 2427 → 2201 | 24087 → 19248 |
| blobs `$B5000-$B57FF` (cost of the hooks) | 0 → 13588 | 0 → 15472 | 0 → 12998 | 0 → 14256 |

(`$17c6c` shrinks because the 5 `bsr` sit inside it.) The blob column is the price: 120 `jsr`s into `p7_cell_obj` (≈108 cy each), the `p7_cell_edge` jump on the ≈ 25-55 emitted cells, and 1.1 k for the per-frame table.

**Cold boot** of the build `--only pp_nofade pp_bigram_cache p7_cell_pre p7_cell_obj p7_cell_edge` (`build/p7cell/game`), `MW1.boot_to_game('M')` (training on, mortars/bombers off), marker, the three sites in RAM, one `:once` breakpoint at each blob entry, then a left click (walk). Raw:

```
1 MB STE, TOS 1.62                                        4 MB Mega STE, TOS 2.06 (/home/ryan/Code/AtariST/gamebench/tos/TOS_2_06.img)
boot_to_game ok in 111s                                   boot_to_game ok in 103s
marker: 4d 57 50 4f  MWPO                                 marker: 4d 57 50 4f  MWPO
{'x': 25600, 'z': 25600, 'speed': 0, 'heading': 0,        same state
 'action': 0, 'exit': 0}
VALID $b5300: 00 01                                       VALID $b5300: 00 01
site $17ca0: 4e f9 00 0b 54 00 4e 71                      identical
site $1748c: 4e b9 00 0b 51 a0                            identical
site $18304: 4e b9 00 0b 50 00                            identical
hook $b5000 / $b51a0 / $b5400 hit: True True True        True True True
walk: (25600,25600,0) -> (25600,29397,40) fps 3.5         walk: (25600,25600,0) -> (25600,31034,0) fps 7.5
```
`MWPO` = every site applied; z moved after the walk click on both machines (the 4 MB run is a 16 MHz machine, the speed word was 0 again by the second sample, z had advanced 5434).

## 2. What the code does (citations: `work/dumps/ram_ski_walk.bin`, `tools/m68dis.py`)

* `$18304` = clear `$18362`, vertex pool/strips `$16cf6`, viewport `$17f20`, cells `$170e6`, clear. `$170e6` loops over the cell list `$18f02..$18bde` (`$170f8-$17108`: `movea.l (a4)+,a5 / movem.l d0/a4 / jsr $17444`).
* `$17444` (cell a5): `d1..d4 = $0,$10,$160,$150(a5)` (vertex pool offsets, `$ffff` = invalid); `and` of the four → `bmi $17508` = all invalid (28/frame in the older notes; here 30/frame walk). Else `d5,d6,d7` from `$a,$b,$c(a5)` → `$17436/$17438/$1743a`, **`jsr $1d41e`** (`$1748c`), `clr.w $12cd6/$12cd8`, `or`: all valid → `$174d0` AND of the 4 outcode words `$6(a3,dN)` (`bne $17508` reject), orientation `$17b1a/$17b86/$17bbe`, `$17a04` (5 edge slots), `$17c6c`; any invalid → `$1750a/$183b0/$185a8/$17d2a` (near plane, `$17392`).
* `$1d41e`: `d0 = a5.w`, `d1 = $1d41a`, `bmi` = none, else `cmp.w (a6)+,d0 / bne / dbra` over `$1d288` (the word list `sub_01d0a0` builds: `move.w d1,(a1)+` at `$1d126`, count `$1d41a` incremented per object at `$1d12c`, decremented once at `$1d13e`, cleared at `$1d0b6`; the only writers are in `$1d0a0/$1d14a`, called from `$14e50` before `$14e56 jsr $18304`). A match pushes `$1743a` and `$c6(a6)` on the painter list (`$18bda`). With no match it only stores `$18bda` back unchanged.
* `$17c6c`: `d0..d3` = the four outcode words (or the negative pointer); AND ≠ 0 → reject (`$17d28`); else `lea $152(a5),a4 / bsr $17fa0`, then the slots `$14,$2,$4,$6` (`$17ca0-$17cc4`), then the emitters. `$17fa0`: `(a4)<0 → $18300 (move.w d5,d4; rts)`; endpoints' outcodes d2,d3; AND ≠ 0 → `$182fc → $17c10` (marks the slot `$8f80/$808f`); OR == 0 → **`$182fa rts`** (no state change); else Cohen-Sutherland clip.

## 3. Why each skip is exact

**p7_cell_obj / p7_cell_pre.** Let E = the words `$1d288[0..$1d41a]` (empty iff `$1d41a` is negative as a word, exactly the original `move.w $1d41a.l,d1 / bmi`). `p7_cell_pre` zeroes a 256-byte table and sets byte `(w >> 6) & $ff` for every w in E (the same `dbra` count as `$1d41e`). `$1d41e` pushes something iff some w in E equals `a5.w`; then `hash(a5.w)` is set, so a zero byte at `hash(a5.w)` ⇒ no match ⇒ the original does nothing observable (it reloads `$18bda` and stores it back unchanged; `d0` is clobbered, `d1/a0/a6` restored). Collisions only give 1 ⇒ original routine (`jmp $1d41e.l`, whose `rts` returns to `$17492`). Garbage entries are safe (same mask on both sides). Preconditions: E and `$1d41a` do not change between `$18304` entry and the last cell (all writers are in `$1d0a0/$1d14a`, `$14e50`, i.e. before). `VALID` = 0 until the prologue ran. Registers at `$1748c`: d1-d4 live (the blob never touches them), d5-d7 and d0 dead (`$17436…` stores happen before the call; every later routine loads its own d5-d7), blob uses d0 only.
`p7_cell_pre` saves/restores d0-d7/a0-a1 and ends in `jmp $18362.l`, so the original `jsr $18362` semantics (return to `$1830a`) are kept.

**p7_cell_edge.** Reached only for a cell with all four corners valid whose corner AND is 0 (`$17c9c` not taken). Condition: `d0|d1|d2|d3 == 0`, i.e. every corner outcode is 0. Each of the five slots `$152,$14,$2,$4,$6(a5)` joins two corners of this cell (`$17a04` stores the cell's own corner pointers; a slot already created by a neighbour joins the same two vertex pointers because pointers are per grid record). With both endpoint outcodes 0 `$17fa0` takes `beq $182fa` and returns without touching memory; an edge with both endpoints inside is never rewritten by a neighbour (only clipped/rejected edges are: `$17c10`, `$182c4-$182f2`). A slot word `<0` goes to `$18300 (move.w d5,d4)`, d4 dead afterwards in `$17c6c`. So the five calls are no-ops and `$17cc8` (`tst.w $8(a5)`, the emitters) is entered with the same memory. Registers: a4 and d0-d7 are reloaded by the callee code at `$17cc8`/`$18802…` (`lea $2(a0,d7.w),a4` etc.). Otherwise the blob does the original `lea / jsr $17fa0.l` and continues at `$17ca8`. Evidence beyond the argument: 8/8 snapshot A/B + 32/32 heading A/B identical, 22-36 of the 36-53 emitted cells per frame take the skip (walk 183 → 88 clip calls per frame).

## 4. Frame-level facts measured on 8-frame captures (`/tmp/mw1c/cap`, state at `$18354`, grid `$54000`, pool `$60000`)

Cell classes (original `$17444` logic replayed on the captured grid/pool; A all invalid, P partial (near plane), R corner-outcode AND, B both triangles back-facing by `$17b86/$17bbe`, E rest):

| frame | cells | A | P | R | B | E | valid verts only in R/B cells | invalid verts only in A cells |
|---|---|---|---|---|---|---|---|---|
| walk_0 | 150 | 24 | 19 | 46 | 8 | 53 | 41 | 36 |
| walk_4 | 150 | 33 | 20 | 40 | 21 | 36 | 44 | 46 |
| stand_0 | 150 | 21 | 14 | 53 | 10 | 52 | 52 | 32 |
| busy_0 | 150 | 32 | 19 | 47 | 2 | 50 | 40 | 42 |
| turn_3 | 150 | 33 | 21 | 77 | 15 | 4 | 88 | 45 |
| turn_6 | 150 | 28 | 13 | 100 | 5 | 4 | 115 | 37 |

(190 vertices per frame; "needed" = a corner of an E or P cell.) R cells' common bit: walk 1/2 (left/right of the window) 31 of 46, others 6/9 (top/bottom), stand all 1/2, turn_6 mostly 8 (below). 22-36 of the E cells have all four corner outcodes 0 (walk 35/22/22, stand 33, busy 36).
Per-frame cycle shares (walk, profile of 30.6 frames before patching): transform strips `$15a96-$17058` 168172 (11.7 %), `$17444` head 45928, `$17fa0` family 54863, orientation `$17b1a-$17c6c` 48949 (of which `$17c10` 9198), `$1d41e` 26224, `$17a04` 21902, `$17392` 19523, `$170e6` loop 14158, `$1750a…` 11359, emitters 32042.

## 5. Not built: skipping cells + the vertices only they need (what was tried on paper and why it loses)

Upper bound (table above): 77-84 of 190 vertices per frame (walk/stand) are never needed by an E or P cell, 115-133 in a turn; at the profile's ≈ 880-1130 cy/vertex (`$15a96-$17058` 168172 / 191) the oracle is 68-96 k = 4.7-6.8 % of a walk frame. Everything below is about realising part of it exactly. Cycle figures are 68000 instruction-time sums [INFERENCE] unless a profile is named.

1. **Vertex layout.** Cells are pushed by the strips (`$15ac2 move.l a5,(a4)+`) one per far-corner vertex; a vertex is the `+0` pointer of its own grid record and a cell sees its 4 corners through neighbours' records. Each of the 24 blocks (`$15ad4 … $17034`, identical 0x9a-byte shape, offsets `$0/$10/$150/$160` and `+$e` for the 3D pointer) allocates 12 B (3D record, always) + 8 B (projected record, only when `z>1` and both `divs` fit). A skipped vertex must still write `$ffff`/pointers, and `$17392` (the only reader of 3D records, 12 callers) reads 3D records of *invalid* corners of partial cells. Skipping any vertex changes the pool offsets of every later vertex (identical pixels, different `$62000` table words) unless the allocation is replicated.
2. **Height-free per-vertex tests** (deep-behind: one `cmp.l T,d2`; deep-lateral: `163·xi + 133·z ≤ 0`). Heights span 0..7819 (map `$404c4`, 100×100 words+attr) and objects flatten the map (`$1d1d2` writes `-$190(a0)/4(a0)/-$18c(a0)`), so only per-vertex exact data or a Lipschitz margin is available; a margin of one grid step (64 units, cell size) plus the z-uncertainty of a height range (`S = $17210 = -1735` → ±187 units over the global range, ±20 locally) removes the first cell band, which is exactly the band most R vertices sit in. Per vertex cost of just the stub: `jmp` 12 + 3 replayed instructions (24) + `cmp.l abs,d2` 18 + `bcc` 8 + `jmp` back 12 ≈ 75 cy × 191 = 14 k per frame for the cheapest test, against a saving of ≈ 530 cy per skipped invalid vertex (≈ 25 of them provable) = 13 k: break-even.
3. **Lazy 3D for invalid vertices (z ≤ 1)**: compute z first (`muls $17210`), store a recipe `{$7fff<<16 | xi, d1, hh<<16 | zi}` in the 12-byte 3D slot (a real X has |X| ≤ 163·32768 < 2^23, so the marker is unambiguous), finish X,Y in a hook at `$17392`. Saves ≈ 280 cy per invalid vertex (stub `jsr/rts/bra` 46 + flag test + abs addressing eat the rest) = 16 k; but ≈ 36 near-plane interpolations/frame each need one invalid endpoint, so ≈ 27 recipes are finished (250 cy each + 60 checks) = 9 k. Net ≈ 5 k = 0.4 %.
4. **Lazy projection** (defer the two `divs` and the outcode; exact outcode from `|X| ≥ 133·z` style compares, valid iff `z ≥ 2` and `|X|,|Y| < 16384·z`): saves ≈ 310 cy per vertex never needed (41 of 130 valid) = 12.7 k, costs ≈ 60-120 cy of hook per needed vertex/cell (85 × 60 + 143 cells × 50) ≈ 12 k. Net ≈ 0.
5. **Cell-time classification with exact partial data** (z from `muls`, x free, `A` = four `z ≤ 1`, lateral R = four `163·xi ≤ -133·z` with `z ≥ 32`, `|xi| < 96 z` so no wrap/overflow; replayed on the captures): proves 24-33 A + 35-42 R cells per frame and leaves 114-125 of 190 vertices needing the full transform, i.e. 65-76 avoidable (≈ 60-70 k oracle). Its cost is an L1 evaluation (≈ 150-260 cy) for ≈ 150 vertices, a per-cell hook (≥ 50 cy × 150), the 24-site stub family (+46 cy each) and the ensure plumbing for the 120 needed ones: ≈ 34-45 k, i.e. net 20-30 k (1.5-2 %) in the best case on paper, with no margin for the P cells and with a different pool layout. Top/bottom rejections (turn: 38-58 R cells unproven) need Y (another `muls`) and are not covered.
6. **Strip-type enabling** (`$172c4-$172cf`, copied per heading sector from `$172d0` by `$1710e`): a finer per-frame enabling would remove whole strips at zero per-vertex cost, but a disabled strip leaves its records at pointer 0 (= pool offset 0, the viewport corner vertices) for the neighbouring ring's cells, so it needs a proof for the neighbours and a per-strip geometry model [INFERENCE, not studied further].

Conclusion: with the strip/pool design every stub or hook costs ≈ 50-80 cy on all 191 vertices (≈ 10-15 k/frame), the same order as what a skipped vertex saves, so none of the exact schemes above clears more than ≈ 1 % after its own overhead, against a 25-patch family, an 8-byte-per-vertex pool layout change and a new proof obligation per frame. I built the cell-level skips that are proven exact and net positive (section 1) and left the vertex skip out. Reopen only together with a rewrite of the strip loops (one loop instead of 24 copies).

## 6. Interactions

* p3b/tick patches: `$18304` etc. are render-side; with `p3b_head`'s skip-render tail the geometry is simply not called and `p7_cell_pre` does not run (the table is only read by cells inside the same `$18304` call). MW1Timing's owned sites do not overlap (`$14e00,$13236,$14e14,$14e32,$14e8a,$12a5e`).
* p4_roll_*/p4_walk_*: independent sites (`$15af0…`, `$19ce6…`); not combined in my gates (base = unpatched game) [INFERENCE: additive, the three sites touch other instructions].
* `p7_cell_obj` needs the **hash table of `p7_cell_pre` for the same frame**; a snapshot restored between `$18304` and the cells would see a stale table (impossible inside one call).
* Data: `$B5200-$B52FF` table, `$B5300` VALID word (zero-init payload RAM, only these blobs write it). Blob entries `$B5000` (pre, 106 B), `$B51A0` (obj, 28 B), `$B5400` (edge, 32 B).

## 7. Reproduce

```
python3 games/midwinter/tools/mw1patch.py verify
python3 games/midwinter/tools/mw1ab.py --only p7_cell_pre p7_cell_obj p7_cell_edge --flips 8 40        # identity + cycles/frame
python3 games/midwinter/tools/mw1patch.py build --only pp_nofade pp_bigram_cache p7_cell_pre p7_cell_obj p7_cell_edge --out build/p7cell/game
# cold boot: MW1(game_dir=build/p7cell/game, machine='ste', tos=TOS['1.62'], memsize_kb=1024) / ('megaste', TOS['2.06'], 4096), boot_to_game('M'), peek $b2ff8, walk()
```
View gate: restore the snapshot, `capture_frames(out, 0xbd9a, at_vbl, 6, live=<set + pokes of $12c98/$15114>)` for base and patched, compare the md5 of the three 32000-byte buffers. Counts/cycles: `b VBL > at && pc = $bd9a :trace :once :file a` where `a` loads the live set, `profile on` and arms `b pc = $bd9a :16 :trace :once :file e` (`e` = `profile counts|cycles 30000`); the two flips-aligned windows give identical frames. The state captures of section 4 save `$54000+$4000`, `$60000+$2000`, `$18f02+$400` at `pc = $18354`.
