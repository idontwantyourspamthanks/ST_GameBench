# MW1 3D renderer map (ski view): stages, cycle shares, hot spots, counts, overdraw, MW2 comparison, opportunities

Read-only analysis; no patch was left in place. Evidence: `work/dumps/ram_ski_walk.bin` disassembly (`tools/m68dis.py`), 250-VBL profiles of
`1mb_ski_walk` / `1mb_ski_stand` (`work/prof/*.txt`, plus a Hatari `profile callers/counts` rerun with a symbol file made from `m68dis.call_targets`
plus a few extra split points), Hatari breakpoint captures, and live A/B pokes applied atomically at a flip (all 1 MB STE, TOS 1.62, 8 MHz).
Unproven statements are marked [INFERENCE]. **Caveat on per-frame numbers:** a 250-VBL profile window holds only 22 (walk) / 17 (stand) flips, so
anything "per frame" derived from it has a ±1-frame quantisation (±4.5 % walk, ±6 % stand). Percentages, per-call cycle costs and ratios are not affected; counts marked
"capture" are exact (every `$1b1bc` hit of ~10 consecutive frames).

## 0. Summary (6 lines)

1. One frame (`$14e00`) = logic, sky fill `$1580e`, terrain geometry `$18304` (clear, ring vertex transform, cell cull/clip/emit), painter-list raster `$19ce2`
   (edge walker `$19f20` + 2-pass dithered fill `$1b1bc/$1b0e4`), goggles replay `$1bbe6`, flip `$bd9a`. Walk: 40.0 % geometry, 40.1 % raster, 4.8 % goggles, 2.8 % sky.
2. The baseline buckets are bucketing artefacts: "`$19f20` 17 %" = walker (8.7 %) + the 15 solid-colour fill variants (8.1 %) that sit after it; "`$1b0e4` 11-14 %" = dither fill (8.4 %) + per-polygon fill setup (2.6 %). Real split: fill 19 %, walker+test+driver 14-16 %.
3. Per-edge overhead, not pixels, is the cost: 172.6 edges/frame (walk) cost ~1.3 k cycles each in total, the DDA rows only 15 cy/row. Interior pixel stores are ~1.3 % of the frame.
4. Nothing is cached across frames: a standing frame is recomputed bit-identically (0 differing bytes in the 3D window over 300 VBL, all 3 buffers); 95 % of a standing frame is re-render.
5. Same design family as MW2 (edge→scanline table→unrolled DDA→table-driven span fill, masked-replay goggles list, per-frame rebuild) but a different, simpler code base (no hierarchical cull, no vertex slot cache, no 3D clip, 16 fill variants not 112).
6. Measured, pixel-identical, in-place only: drop the always-passing edge test `bsr $19ed4` + trim the walker's `movem` (walker incl. 1016 → 712 cy/call, stand 1022 → 713), skip the checksum `jsr $122f0`: +3.2 % and +4.0 % flips/1500 VBL (stand); static-frame skip is the only big item (≈95 % standing).

## 1. Pipeline map (frame `$14e00`, order of the `jsr`s at `$14e00-$14e96`)

Walk-snapshot inclusive cycles from `profile callers` (22 flips; % of the 35.14 M profiled cycles). Stand in brackets.

| # | Stage | Routine (disassembly evidence) | Share walk [stand] |
|---|---|---|---|
| 1 | Input, sim, AI, HUD updates | `$14efc` (key scan: `cmp.b #$58`), `$12e9c`, `$129d2` (physics/unit AI: `$9572`, `$a36c`, `$c4f2`…), `$14fac`, `$202c6/$200e8/$1ffe0/$1fa0a/$20d52` | 9.6 % [3.9 %] |
| 2 | **Sky / background clear** | `$1580e`: `movem.l d0-d5/a0-a5,-(a6)` ×3 per row (144 B = 18 groups = px 16-303), rows `$171f4..$171f6` = 51..181 (131 rows = 18 864 B), colour planes `$0000ffff/0` = colour 2 (`$15850` `tst.w $12d54` selects other patterns) | 2.8 % [2.1 %] |
| 3 | Object marker cull | `$1d0a0`: 78 records at `$70010` (`$1d418` = 77), `divs.w $12c5a(=$200)` ×2 (`$1d0d4/$1d0d6`), ±8-cell window, builds cell list `$1d288`/type list `$1d350` | 2.3 % [1.8 %] |
| 4 | **Terrain geometry** `$18304` | see §1a | 40.0 % [34.5 %] |
| 5 | **Raster** `$19ce2` | see §1b | 40.1 % [53.1 %] |
| 6 | **Goggles overlay** | `$14e62 move.l $12d0a,$1bbe2` then `$1bbe6` replay of the list at `$1bbde` (=`$74000`) onto the draw buffer | 4.8 % [3.7 %] |
| 7 | Flip | `$14e90 jsr $bd9a` (triple buffer `$58000/$68000/$78000`, `mw1_state.md`) | 0.0 % |
| – | HUD (top panel rows 0-50: portrait, clock, mph, radar) | **not redrawn per frame.** Standing: 3D window identical in all three buffers (§5); the only differing bytes in the 32 000 B are rows 192-197, cols 18-19 (a 6-row indicator, 49-59 B). No HUD routine is in the profile above 0.5 % | ≈0 |

### 1a. Terrain geometry `$18304` (`jsr` order at `$18304-$1835a`)

| Sub-stage | Routine | Share walk [stand] | What it does (evidence) |
|---|---|---|---|
| Clear ×2 | `$18362` called at `$18304` and `$1835a` | 4.6 % [3.7 %] | `movem.l d0-d6/a0,-(a5)` ×8 × 64 downward from `$12cfa+$4000` (=`$54000+$4000`): zeroes 16 384 B = 1024 grid records of 16 B (row pitch `$150` = 21 records). 36.4 k cy each |
| Viewport corner vertices | `$17f20` | <0.1 % | writes the 4 corners `$171f0..$171f6` = x 28..292, y 51..181 into the vertex pool (`$17f32-$17f7a`) |
| **Transform + project** | `$16cf6` → 8 rings × 4 sides: `$161f6/$163ba/$1657e/$16742` (+ `$16906/$16a02/$16afe/$16bfa`), strip loops `$15a96..$16906`; ring/side enables from `$17140/$17150`, heading sector table `$172d0` via `$1710e` (`asr.w #7` of `$12c98`) | 12.9 % [10.7 %] | per grid vertex: height `(a0)` − eye `$1721c` (=764), 2 `muls` (`$17212/$17210` heading terms) + 4 `muls` (`$17216`=163 focal, `$17214`=0 roll), `swap`, `cmp #1,d5 / ble` (z ≤ 1 ⇒ vertex flagged `$ffff`), then **`divs.w d5,d3 / divs.w d5,d4`** (`$15cf6/$15cfa`), `+$17218`(160), `neg, +$1721a`(132), 4-way outcode vs `$171f0..$171f6` (`$15d0a-$15d32`). 1129 cy/vertex (205.9 k / 182 vertices) |
| **Cell classify / cull / clip / emit** | `$170e6` → `$17444` ×143 | 22.2 % [19.8 %] | cell = quad `(a5)+0/+$10/+$150/+$160` (4 vertex-pointer words). `$17462 bmi` rejects all-invalid; `$1750a/$183b0/$185a8` near-plane path with `$17392` (`divs` interpolation, 34/frame, `cmp.l #$7d00`); full-valid: outcode AND at `$174d0-$174e0`; then `$17b1a/$17b86/$17bbe` (edge-vertex slots `$17a04`, facing flags `$12cd6/$12cd8`), **`$17c6c`**: 5× `bsr $17fa0` (screen-space Cohen-Sutherland per edge, `muls/divs` at `$18028-$1816a`) then one of the triangle emitters `$18802/$188f0/$189de/$18acc` pushing polygons on the painter list (`$18bda`). `$1d41e` (115/frame) pushes object records into the same list when a cell holds an object |

### 1b. Raster `$19ce2` (loop `$19d1c-$19d56`)

`a6 = $18bda` (list), pops `d0 = -(a6)`: `<0` ⇒ `$1d5a6` object (model draw, pushes its polygons on the list); else `$1a942 = (a0,d0.w)` (shade index) and `bsr $19d6a`.

| Sub-stage | Routine | Share walk [stand] | Notes |
|---|---|---|---|
| Polygon driver | `$19d6a` (ring walk `$19d8c-$19df8`) | 3.7 % [4.2 %] + fill setup 2.6 % [3.0 %] | per edge: 14 indexed `move.w` through ring `a1` / edge `a2` / vertex `a3` tables (343 cy/edge), then `bsr $19f20`; after the last edge `bne.w $1b1bc` (fill setup, 717 cy/polygon) |
| Edge test | `$19ed4` (called from `$19f24`) | 2.1 % [2.4 %] | 8 `cmp` of the endpoints vs `$19f16..$19f1c` (=28,292,51,181), 197 cy; **0 rejections** in 7.7 k tests (`$19f0c` never hit in walk/stand/busy captures) |
| Edge walker | `$19f20` | 8.7 % [9.9 %] | §3 |
| Fill | `$1b1bc` → 2 × `$1b0e4` (rows `ymin, ymin+2…` then `ymin+1…`) | 19.0 % [19.4 %] | dither or one of 16 solid variants, §3, §6 |
| Objects | `$1d5a6`→`$1dd14` (checksum `$122f0`→`$12276`, vertex/model `$1e406`, `$1e0d8`, `$1e026`, `$1dfa0`…) | 5.6 % [16.4 %] (0.8 / 1.9 objects per frame), of which checksum 2.6 % [7.2 %] | excludes the object polygons' walk/fill (those run in `$19d6a`) |

Stage totals walk [stand]: geometry 40.0 [34.5], raster 40.1 [53.1], goggles 4.8 [3.7], sky 2.8 [2.1], markers 2.3 [1.8], logic 9.6 [3.9] (sum = 99.6 [99.1] %).

## 2. Cycle shares by stage, walk vs stand

| Stage | walk k cy/frame (%) | stand k cy/frame (%) |
|---|---:|---:|
| Frame total (profile ÷ flips) | 1597 (100) | 2078 (100) |
| Ring vertex transform + divide `$16cf6` | 206 (12.9) | 223 (10.7) |
| Cell cull/clip/emit `$170e6` (of which `$17fa0` 72/85, `$17c6c` excl 18) | 355 (22.2) | 412 (19.8) |
| Grid clears `$18362` ×2 | 74 (4.6) | 78 (3.7) |
| Painter list / driver loop | 59 (3.7) | 88 (4.2) |
| Edge test `$19ed4` | 34 (2.1) | 50 (2.4) |
| Edge walker `$19f20` (setup+rows+exits) | 140 (8.7) | 206 (9.9) |
| Fill setup `$1b1bc` | 41 (2.6) | 61 (3.0) |
| Fill, solid variants `$1aa44-$1b0e0` | 130 (8.1) | 171 (8.2) |
| Fill, dither `$1b0e4-$1b1a8` | 134 (8.4) | 171 (8.2) |
| Objects `$1d5a6` incl. checksum | 90 (5.6) | 341 (16.4) |
| Sky `$1580e` | 44 (2.8) | 44 (2.1) |
| Goggles `$1bbe6` | 75 (4.7) | 75 (3.6) |
| Markers `$1d0a0` | 36 (2.3) | 37 (1.8) |
| Logic, input, AI | 153 (9.6) | 81 (3.9) |

Raw (`profile callers`, walk): `019ce2 incl 640.7k 40.1%`, `018304 incl 639.0k 40.0%`, `019d6a incl 545.0k excl 97.5k calls/frame 53.3`,
`01b0e4 incl 271.3k excl 267.1k calls 103.6`, `019f20 incl 175.4k excl 140.1k calls 172.6`, `019ed4 excl 33.9k calls 172.6`.
Stand: `019ce2 1103.2k 53.1%`, `01d5a6 341.4k calls 1.9`, `012276 151.1k excl 149.1k`.

## 3. Hot spots (function-exclusive, walk / stand) and inner loops

Baseline buckets for reference (call-target bucketing, `baseline.md`): `$19f20` 17.0/18.3 % = walker **8.7/9.9** + solid fill variants **8.1/8.2** (`$1aa44-$1b0e4` are only reached by `jmp (a5)`, so they fall into the preceding bucket); `$1b0e4` 11.2/11.3 % = dither fill **8.4/8.2** + setup `$1b1bc-$1b27e` **2.6/3.0**.

| # | Function | Role | walk % [stand %] | calls/frame (walk) | cy/call | Inner loop / cost split |
|---|---|---|---|---:|---:|---|
| 1 | `$1b0e4` + variants + `$1b1bc` | span fill | 19.0 [19.4] | 51.8 polygons, 103.6 passes | 2578/pass | per **row**: solid 347 cy, dither 444 cy (profile); interior group `move.l d4/d5,(a3)+` = 24 cy per 16 px; 1770 interior stores/frame = 1.3 % of the frame. Row = 2 head loads, 2× `andi/sub/add/add`, mask-table `move.l`, left RMW (`and.l/or.l` ×2), right RMW, `dbra`. Dither mix at `$1b116-$1b12a` (216 cy per pass, done twice per polygon) |
| 2 | `$19f20` walker (+`$19ed4`) | edge → x table | 8.7 [9.9] + 2.1 [2.4] | 172.6 | 812 + 197 | head `movem.l d0-d7/a0-a1,-(a7)` 88 cy; test 197 cy; `divu.w d4,d3` ×2 = 268 cy (`$19f80/$19f86`, `$1a2cc/$1a2d2`); exit `movem.l (a7)+` 92 cy; rows **16 cy** (`move.w d1,(a0)+` 8 + `addx.l d3,d1` 8, measured 15.4). 1393 rows/frame = 21.4 k = 1.3 % ⇒ **setup is 4.6× the row work** |
| 3 | `$19d6a` driver | ring walk + fill setup | 6.1 [7.0] | 53.3 | 1829 | 343 cy/edge (14 table-indexed loads) + 717 cy/polygon for `$1b1bc` (two `movem.l a0-a6`, `mulu.w #$a0`, pattern fetch from `$1b340`) |
| 4 | `$1bbe6` | goggles replay | 4.7 [3.6] | 1 | 75 k | 336 masked records (`and.l/or.l` ×2 + `dbra`, ≈176 cy) + 162 runs (44 cy per 8 B pair); writes 5528 B/frame |
| 5 | `$18362` | grid clear | 4.5 [3.7] | 1.9 | 36.4 k | 8 × `movem.l d0-d6/a0,-(a5)` per `dbra` (2.2 cy/B), 16 384 B |
| 6 | `$17fa0` | screen-space edge clip | 4.5 [4.1] | 212 | 338 | outcode `and`/`or` early outs (`bne $182fc`, `beq $182fa`); full clip = `muls`+`divs` per bound, rare |
| 7 | `$17444` | cell head | 3.4 [2.9] | 143 | 378 | 4 corner loads + `and` (`$17462`), `jsr $1d41e` |
| 8 | `$1580e` | sky clear | 2.8 [2.1] | 1 | 44 k | 3 × `movem.l` of 12 regs (104 cy) per 144 B row (≈340 cy/row × 131) |
| 9 | `$12276` | anti-tamper byte sum | 2.6 [7.2] | 0.8 [1.9] | 53 k / 78 k | `cmp.l a0,d0 / beq / moveq / move.b (a0)+,d2 / add.l d2,d1 / bra` = **48 cy/byte**, 1056 B (walk object) / 1604 B (stand object) per call; hang on mismatch (`mw1_state.md`/baseline) |
| 10 | `$1d0a0` (+`$1d14a`) | marker window test | 2.2 [1.8] | 1 (75.7 divs pairs) | 36 k | 2 × `divs.w` by `$200` = 22 k of the 36 k |
| 11 | `$1d41e` | per-cell object-list check | 1.9 [1.7] | 115 | 262 | `cmp.w (a6)+,d0 / dbra` scan of the in-range object list |
| 12 | `$17392` | near-plane interpolation | 1.5 [0.9] | 34 | 683 | 2 `divs` + 2 `muls` + 4 range `cmp.l` |
| 13 | strip loops `$15c6e,$15d5a,$15f32,$1610a` (+4 more) | ring vertices | 1.5 each [1.3] | 6.7 | 3.7 k | 24.7 k each; ≈1129 cy/vertex incl. loop; `divs.w` pair = 300 cy of it |
| 14 | `$17a04` | edge-vertex slot allocation | 1.5 [1.5] | 37 | 633 | 5 conditional 8-byte slot writes |
| 15 | `$9572`, `$a36c`, `$c4f2`… | physics / unit AI | 2.4 [0] | – | – | outside the renderer |

## 4. Per-frame counts (walk | stand; profile ÷ flips unless marked "capture")

| Item | walk | stand | Evidence |
|---|---:|---:|---|
| Grid vertices transformed (`movem.l d3-d5,(a3)`) | 182 | 191 | `.save` counts at all strip loops |
| of which projected valid (`movem.w d3-d6,(a3)`) | 123 | 143 | same |
| Unique edge endpoints actually walked (capture) | 70-81 | 77 | `r` at `$19f20`, 8-9 frames |
| ⇒ transformed vertices never reaching an edge | ≈55-60 % | ≈60 % | 182/191 vs 77 [INFERENCE: endpoints are also clip points] |
| Cells entered `$17444` | 143 | 150 | |
| – all 4 vertices invalid (`$17462`) | 28 | 21 | |
| – near-plane partial (`$1750a`) | 17 | 14 | |
| – all valid | 98 | 115 | |
| – rejected by corner-outcode AND | 43 | 53 | `$17b1a` count 54.8/62.0 passed |
| – emitted (`$17a04/$17c6c`) | 37 | 52 | |
| Polygons `$19d6a` | 53.3 (capture 54.3) | 79.8 (capture 80) | |
| Edges walked `$19f20` | 172.6 | 254.1 (capture 261) | |
| – horizontal (dy=0, skipped) | 25 | 25 | `$19f38`/`$1a2c4` |
| – with rows (x rising / falling) | 39 / 108 | 135 / 95 | `divu` sites `$19f80/$1a2cc` |
| – unique segments (capture) | 169 of 259 | 164 of 261 | shared edges walked twice: 36 % duplicates |
| Walker rows | 1393 | 1695 | unrolled `move.w` counts; 8.2-9.9 rows/edge |
| Fill passes `$1b0e4` | 103.6 | 155.6 | 2 per polygon |
| – solid (equal shade colours) / dither | 51.0 / 52.6 | 77.4 / 78.3 | `$1b1a8` vs `$1b0fa` counts |
| Fill rows, solid / dither (profile) | 374 / 301 | 493 / 362 | loop-head counts; capture non-empty rows 730 / 906 |
| Interior 16-px groups (24 cy each) | 885 | 1013 | `move.l d4/d5` stream stores |
| Span-fill pixel writes (capture) | 19 385 | 26 267 | rows × (xr−xl+1) |
| Unique pixels covered (capture) | 14 345 | 24 075 | |
| **Painter's overdraw** (writes − unique) | **26 %** of writes | **8.3 %** | busy: 8.9 % |
| 16-px groups written | 1931 | 2546 | |
| Objects drawn `$1d5a6` | 0.8 | 1.9 | |

Window area: x 28..292 × y 51..181 = 265 × 131 = 34 715 px (`$12d4a-$12d50`, `$171f0-$171f6`). Walk terrain covers 41 % of it.

### Hidden under the goggles frame
The replay list (`$74000`, 498 records, 8194 B; decoded: 336 masked + 162 runs, 5528 B written) makes **8 885 px opaque**, all in rows 51..181 and px 16..303; 5 872 of them
are inside the 265-px window ⇒ the lens shows 28 843 of 34 715 px (83 %). Written but invisible:

| | walk | stand | busy |
|---|---:|---:|---:|
| Sky fill px hidden (8 885 of 37 728 written) | 23.5 % | 23.5 % | 23.5 % |
| Span-fill px writes under opaque goggles (capture) | 19.3 % | 12.1 % | 12.2 % |
| Unique terrain px hidden | 20.7 % | 12.8 % | 13.0 % |
| 16-px groups fully opaque | 11.0 % | 8.1 % | 7.3 % |
| Fill rows wholly under goggles | 5.1 % (37/frame) | 2.3 % (21) | 1.2 % (13) |
| **Polygons wholly under goggles** | 0.4/frame | 0 | 0 |

Goggles overlap is real but spread thin: removing it saves only the per-row overhead of ~13-37 rows (≈14 k cy ≈ 0.9 % walk) plus the 0.4 polygon/frame; MW2's cockpit cull gained more because its cockpit hid whole polygons.

## 5. Is anything cached across frames? No.

- Standing, 3 captures at VBL +150, +300, +450: all three buffers `$58000/$68000/$78000`, rows 51..181: **0 differing bytes** between buffers and between times (`cmp` of 20 960 B each);
  full 32 000 B screens differ only at rows 192-197, cols 18-19 (49-59 B). Per-frame counts are exactly periodic (80 polygons, 261 edges, 906 rows in all 9 captured frames).
  Walking: window bytes differ 483-6684 of 20 960 between adjacent buffers (3-32 % of 16-px groups).
- Per frame the code resets the vertex cursor (`$1830a move.w #$8,$12c88`), clears the grid twice, rebuilds all 182 vertices from the height map, re-sorts nothing (ring order = painter order), re-runs checksum per object.
- Persistent data are only static tables (shade table `$1b340`, mask tables `$1a944-$1aa44`, `$1b280`, sin/cos), the goggles list (encoder `$1bab8`, event driven: called from `$d12c/$d8d2/$125be/$12686/$14cb6`, **0 hits** in both profiles) and the height map.
- Grid state: at `$19ce2` entry the 16 KB grid is **all zero** (capture `savebin $54000 $4000`), at `$18304` entry **988 non-zero bytes in 84 records** (offsets `$54000-$57ee5`); a watch on `$54006` shows it toggling `1,0,1,0` once per frame. So both `$18362` calls currently do work; the writer between the end-of-frame clear and the next frame is [INFERENCE: object/marker height stamps `$1d1d2/$1d20e`, not located].

## 6. Fill and dither details (constraints for any pixel-identical rewrite)

- Walker tables: left/"A" table `*$1a61a` (=`$1a622`), right/"B" `*$1a61e` (=`$1a7b2`), 200 words each, one **word x per scanline** (`move.w d1,(a0)+`), row `y` at `+2y`; B is `$190` bytes after A (fill reads `(a0)` and `$190(a0)`). `$1a616` = ymax (init `$9000`), `$1a618` = ymin (init `$7000`) set at `$19d6a-$19d72`/`$19f4c-$19f62`.
- DDA arithmetic (`$19f6e-$19f9c`): `q = dx / dy` (`divu`), `f = (rem<<16) / dy` (second `divu`, truncated), start fraction `$c000` (B) or `$4000` (A), `x_k = x0 + k·q + ⌊(c + k·f)/65536⌋`. **Truncation matters:** I emulated the loop exhaustively (dy 1..130, dx −264..264, both start fractions, 137 540 edges) and a `round(65536/dy)` / ceil / floor reciprocal-table slope differs from the original on **62 k / 83 k / 71 k edges (170 k / 440 k / 326 k rows)**, because exact ties (e.g. dy=4) are frequent and the original's truncated `f` lands just below them. A reciprocal replacement of the two `divu` is therefore **not pixel-identical**.
- Fill setup `$1b1bc`: skips if no edge (`cmp.w #$9000,$1a616 / beq`), `$12d3a == 4` runs `$19e76` [INFERENCE: pick/hit test of one pixel against the span tables], colour index `$1a942` → `$1b340[4·idx]` = `[A0,B0,A1,B1]` bytes at `$1b1b8`; `ymin` odd ⇒ `swap` (phase locked to screen row parity); pass 1 uses `(A0,B0)` on rows `ymin,ymin+2…` (`d7 = n − n/2 − 1`), pass 2 `(A1,B1)` on the others.
- `$1b0e4`: `A0 == B0` ⇒ `$1b1a8` solid: `$1b300[4·colour]` → one of 16 variants (`$1aa44`, `$1ad32`, …); each updates 4 planes per group with `and.w`/`or.w` on `d2/d3`. `A0 ≠ B0` ⇒ pattern `P = (cA & $55555555) | (cB & $AAAAAAAA)` per plane pair (`$1b116-$1b12a`; `$1b280` table of 16 colours × 2 longs) = column-alternating 2-colour dither; swapped on the other pass ⇒ checkerboard. The 399-entry shade table `$1b340-$1b97c` is built of 4-step ramps, e.g. `0:0000 0000`, `1:00 03 00 00`, `2:00 03 03 00`, `3:03 03 03 00`, `4:03 03 03 03`, `5:03 04 03 03`… (colour 0→3→4→5→6→1, then 0→7→8→9→13→15→1), i.e. 25-step brightness/fog ramps per material [INFERENCE: ramp meaning].
- Row geometry (`$1b138-$1b1a2`): `xl&15`, `xr&15` masks from `$1a9c4` (`(a6,d2)` left paint masks, `$40(a6,d3)` right), spans are **inclusive** `[xl,xr]`; group offset `x/2` bytes (`lsr.w #1`), screen address `a2 = [$12d0a] + 160·ymin` (`mulu.w #$a0`); interior stream entered by `jmp (a4,−d1)` into `$1b082-$1b0dc` (`move.l d4,(a3)+ / move.l d5,(a3)+`, 4 B of code per group).

## 7. Comparison with Midwinter 2 (`spanfill.md`, `f38cd0.md`, `projection.md`, `clears_blits.md`, `render_audit.md`)

Verdict: **same design family, different (simpler, probably older) implementation.** No shared addresses or code; the ideas are the same, the refinements MW2 shows are absent. [INFERENCE: "older" from game order and missing refinements.]

| Aspect | MW2 | MW1 (this note) |
|---|---|---|
| Edge → table | `$3c5e2`: per row `{byte offset, mask}` (4 B) into `$7b6b0/$7b9d0`, `mulu #320`, reciprocal `T[dy]` (approximate DDA), 201 unrolled 44-cy bodies, setup 430-760 cy | `$19f20`: **one word x/row** into two tables, exact 2×`divu`, unrolled 16-cy bodies (add and sub variants, entry `jmp (a1,d4.w)`, d4 = −4·dy), setup ≈575 cy + test 197 + driver 343 per edge |
| Span fill | `$38cd0` dispatcher (3 table loads, 262 cy) + ~112 pre-unrolled variants, variant by ymin parity; masks precomputed by walker; 10-13 % | `$1b1bc` + `$1b0e4` + 16 solid variants; **two passes** (even/odd rows), colour pair from the shade table mixed at call time, masks computed per row in the fill (347-444 cy/row); 19 % |
| Clipping | 3D homogeneous Cohen-Sutherland `$1fdf0` on straddling polygons only; polygon-level trivial accept 61 % | **2D screen-space** Cohen-Sutherland `$17fa0` on every visible cell edge (5 per cell) after the divides; near-plane interpolation `$17392`; no polygon-level accept beyond corner-outcode AND |
| Terrain selection | hierarchical 9×9×9 frustum cull, 32×32 grid rebuilt per frame, vertex slot cache `$7c718`, 83-104 transforms/frame | 8 rings × 4 sides chosen by heading sector, grid `$54000` cleared twice, **no slot cache**, 182-191 transforms/frame (6 `muls` + 2 `divs` each), all projected before culling cells |
| Order | terrain pre-ordered back-to-front, objects bucket-sorted | one painter list `$18bda` (stack), objects pushed by cell (`$1d41e`) |
| Objects | BSP leaves with matrices, no checksum | models via `$1d5a6/$1dd14`, **anti-tamper checksum per object** (48 cy/B × 1056-1604 B) |
| Buffers | double `$60000/$70000` | triple `$58000/$68000/$78000` |
| Goggles/cockpit | encode `$30e30` (event) + replay `$30f2c`, records `[off][mask.w×2][or.l×2]` / `[~off][cnt][longs]`, 3-4 % | encode `$1bab8` (event) + replay `$1bbe6`, same record formats (one mask long), 3.6-4.8 % |
| Sky | `$1b996` 22.7 kB, 2.6-3.6 % | `$1580e` 18.9 kB, 2.1-2.8 % |
| HUD | 7.5-14.7 % (radar loop, sprite blits) | none per frame |
| Caching | none; standing frame recomputed (92 %) | none; standing frame recomputed (95 %) |
| Per-frame cycles (8 MHz) | 1.52 / 1.90 / 2.12 M | 1.60 M (walk) / 2.08 M (stand) |
| Counts | 104-173 edge walks, 37-58 polygons, 83-104 vertex transforms, 0-2 objects | 173-254 edges, 53-80 polygons, 182-191 vertices, 0.8-1.9 objects |

## 8. Ranked opportunities (walk / stand % of frame; "MW2" = solved there, port possible)

Pixel-identical = "yes" means by construction or verified by A/B below. All sites are in resident code (`$14e00-$1bc30`) and the MW2 payload scheme (`mw1patch.py`) can carry blobs; in-place pokes need no blob.

| # | Opportunity | % of frame walk / stand | Pixel-identical | Effort | Risk | MW2 port |
|---|---|---|---|---|---|---|
| 1 | **Static-frame skip**: skip geometry+raster+sky+goggles+markers when heading, position, speed, objects and HUD state are unchanged for **3** flips (triple buffer) | 0 / **≈95** (34.5+53.1+3.7+2.1+1.8) | yes (0 byte diff verified) | medium | medium-high (objects, indicator rows 192-197, buffer rotation) | **yes**, `p7_skip_*` (7 patches; MW2 got ≈5× standing; MW1 needs 3 draws, not 2) |
| 2 | Skip the anti-tamper `jsr $122f0` at `$1dd18` (data covered by the sums is never written) | 2.6 / 7.4 (measured +4.0 % flips stand; A/B 3 buffers identical) | yes | trivial (6-byte nop) | low (check with Tamper note: sums cover `$31698-$3ddb4`, nothing else patched there) | no (MW2 has none) |
| 3 | Walker: remove `bsr $19ed4`/`bne.w $1a2c4` at `$19f24` (0 rejects in 7.7 k tests) | 2.4 / 2.7 (218 cy/edge measured, 1022 → 804) | yes in tested scenes | trivial (in place, 8 B) | low-medium: objects near the camera might need it [INFERENCE: unseen]; guard by `$17fa0`-clipped terrain only | MW2 `p4_walk` (setup rewrite) |
| 4 | Walker: save only `d6/d7/a0/a1` (`48e7 03c0` at `$19f20`, `4cdf 03c0` at `$1a2c4`, `$1a610`; callers `$19de4`, `$19e4a` reload d0-d5 each pass) | 1.0 / 1.1 (91 cy/edge measured, 804 → 713) | yes (A/B) | trivial (3 in-place patches) | low | `p4_walk_ret` (shared tail) |
| 5 | **Clean prefix** (sky fill + goggles replay only for rows ≥ min(ymin now, ymin when this buffer was last drawn)); terrain top row 100 (walk), 83 (stand), 88 (busy) so 49/32/37 of 131 rows clean; saves ~16 k sky + ~25 k replay | 2.0-2.6 / 1.5-1.9 (moot when #1 applies) | yes | medium (per-buffer ymin history × 3) | low-medium | **yes**, `p4_hud_pfx_*` (+4 % in MW2) |
| 6 | Grid clears `$18362`: clear only dirty records (track extent) or blitter on STE | 2-4 / 2-3 | yes | medium | medium (writer of the 84 dirty records unknown) | partly: `p4_grid` idea; `p4_blit_*` (MW2 saw 5.5 % of a fill only: not worth) |
| 7 | `$1d0a0`/`$1d14a`: replace `divs.w $12c5a` (=`$200`, 6 readers, 0 absolute-short writers) by sign-correct shift | 1.4 / 1.1 (22 k cy) | yes if `$12c5a` stays `$200` and quotients fit 16 bit | low | low | **yes**, `p4_proj_div` (same code shape) |
| 8 | Vertex transform: skip the two roll `muls` when `$17214 == 0` (0 in walk and turn snapshots; `$144ca` init) | ≈1.0 / 1.0 | yes | low | low | `p4_proj_axis/cols` analogue |
| 9 | Fill trims: compute the dither mix once per polygon (216 cy × 26 polygons), fuse the two passes of solid polygons (≈250 cy × 25), slimmer `$1b1bc` (717 cy/polygon) | ≈1.5 / 1.6 [INFERENCE from per-call cy] | yes | medium | low | `spanfill.md` #2/#3 ideas |
| 10 | Driver loop `$19d6a`: pre-resolved vertex data (343 cy/edge) | ≈1-2 / 1-2 | yes | medium-high | medium | – |
| 11 | Skip fill rows / polygons under opaque goggles (exact mask) | 1.1 / 0.5 | yes | medium | low | `p7_ck_*` (MW2: −3 % foot, here less) |
| 12 | Lazy transform: skip vertices whose cells fail early tests (≈55-60 % of the 182 unused) | ≤4-7 / ≤4 | yes if exact | high | high | `p7_cell_cull` idea |
| 13 | Reciprocal `T[dy]` for the 2 `divu` of the walker | 1.8 / 2.0 | **no** (62 k of 137 k edges differ by ±1 px at ties) | low | – needs sign-off; exact variant needs a ≈34 KB table | MW2 does this natively |
| 14 | Ring count 8→7 / 8→6 (`cmp.w #$10,d7` at `$16d72`, poke `$16d74` word `000e`/`000c`): far ring dropped | +2.4 % / +11.1 % flips (stand, 1500 VBL) | **no** (view distance) | trivial | visual | `Draw distance` experiments in `render_audit.md` §5 |

Already large enough to order: #1 ≫ #2 > #3+#4 > #5 > #6 > #7 ≈ #8 ≈ #9. On moving frames (walk) #2-#9 sum to ≈10-15 % (low-high ends, overlapping little), consistent with MW2's flat-profile result.

## 9. Experiments (live pokes applied atomically at a `$bd9a` hit; restored 1 MB snapshots)

| Poke | Effect | Pixel A/B at flip 8 (3 buffers) |
|---|---|---|
| `$19f24` 8 B → `4e71`×4 (no test) | walker incl. 1022 → 804 cy/call (stand; walk 1016 → 824); flips stand 129 (orig 126) | walk, stand: identical |
| above + `$19f20 48e703c0`, `$1a2c4`/`$1a610 4cdf03c0` | walker incl. 1022 → **713** cy/call (stand; walk 1016 → 712, −304); **130** flips/1500 VBL stand (+3.2 %, resolution ±0.8 %) | walk, stand: identical |
| `$1dd18` 6 B → `4e71`×3 (no checksum) | stand 131 flips (+4.0 %) | stand: identical |
| `$16d74` `000e` / `000c` | 129 / 140 flips (+2.4 % / +11.1 %) | not compared (visual change) |

Orig stand = 126 flips per 1500 VBL (11.9 VBL/frame). A first attempt that poked the `movem` mask non-atomically (while the CPU ran) crashed Hatari with Bus Errors; apply code pokes at a flip breakpoint only.

Method (scripts were throw-away in `/tmp/mw1r`, not kept): `profile on` + `profile callers` + `profile save` after `symbols file` (nm-style `addr T name`); `b pc = $1b1bc :trace :file` with `m $1a616 12`, `m $1a622 400`, `m $1a7b2 400`, `m $1a942 2` to capture every polygon's span table, replayed offline with the fill's exact `[xl,xr]` semantics against the decoded `$74000` goggles list.
