# Moonshine Racers: new HUD, SKETCH ONLY (mockups, cost estimates, implementation plan; nothing built, nothing patched)

Decisions taken from the user (binding): minimap removed, clouds removed (sky stays), cup -> small turbo gauge in the top bar, dial half size, speed / gear / temperature as numbers in a single-colour top bar drawn once per change.
Not decided (kept as options below): speech face/text drawing, score digits and race position (kept, cheaper).
Evidence tags: **[M]** = measured, with the raw file named; **[S]** = cycle numbers from `work/notes/hud.md` (stock/shipped measurements of the existing routines); **[INFERENCE]** = hand count / scaling, not measured.
Everything below lives in `work/hud/design/` (files in section 9) and this note; no file in `tools/`, `patches/`, `originals/` was touched.

## 0. One-page answer

* Mockups (pixel-exact 320x200, saved 3x nearest-neighbour) on four real frames (driving / standing, with and without speech + face): `work/hud/design/layout_A.png`, `layout_B.png`, `layout_C.png` (= the driving+speech frame), `layout_<X>_<frame>.png` for the other frames, `*_annot.png` (green = redrawn on change, cyan = static background), and the before/after strips `strip_drv.png`, `strip_drvsp.png`, `strip_gsp.png`, `strip_gno.png` (stock HUD on top, then A, B, C; top 81 rows of the same frame).
* **A** = one 16-row black strip, big 8x14 digits (the game's own score font) + 8x8 labels (the game's message font), the half dial *inside* the strip; **B** = thin 10-row strip with the 8x8 font only, dial / position / turbo hang below it on the sky at the old minimap place; **C** = compact 112x34 black panel in the top-left corner (not a full-width bar), the sky to its right stays completely free.
* Cost per driving pass of the new HUD stage (numbers drawn only when changed, per-buffer shadow, precomposed glyph strips, `movep` kernel): **about 2.4 k (A) / 2.1 k (B, C) cycles, 0.35 k standing**, against 111.4 k (HUD, shipped `mr_*` set) or 148.4 k (stock) for the 13 stock calls. With the clouds (80.8 k) the total saving is **about 190 k cycles per driving pass on the shipped set = 1.18 VBL = 27.6 % of the 4.29-VBL pass (687.5 k), i.e. the driving pass would be about 3.11 VBL** (stock basis: 226.6 k = 26.8 % of 846 k). 3.11 VBL is still ~16 k cycles above 3.00 VBL (481 k): see section 3.4.
* Plan in one line: one new blob with two hooks: `$ef7a` (`jmp NEWHUD`, replaces the whole stage but keeps the ticker `11ef0` and face `f90c` calls) and `$edea` (race init: `jsr $dd18` -> `jsr HUDINIT`, invalidates both buffers so the first pass per buffer paints bar + sky and every field). `mx_sync`'s private copy of the HUD list (`hud:`) must be changed in step.

## 1. Frames, geometry, palette (how the references were made)

Capture tool: `work/hud/design/capture.py` (own Hatari per call, scratch dir `/tmp/mhd_<tag>`, own memstate copy; stopped only by its own `h.close()`; `--borders false`), breakpoint at `$7b86` (end of the pass) with the condition `$100e = pass`, dumps both screen buffers (`savebin $70000/$78000 $7d00`), the palette tables `$3cc4..$3d0f` (`savebin`), `m $ff8200`, `m $ff8240`, `m $100e $11ab $10ba $10c0 $10ca $10d8 $11d9 $11c2`, then a Hatari screenshot. Raw outputs: `work/hud/design/cap/<tag>_{70000,78000}.bin, _pal.bin, _state.txt, _shot.png`.

| tag | snapshot | pass | content |
|---|---|---|---|
| `drv` | `ste1m_race_start` | `$70` | driving, no speech, score 1940, speed 92, position 6 |
| `drvsp` | `ste1m_race_start` | `$a0` | driving, ticker typing "Maybe you'd better patrol the r" + talking face |
| `gsp` | `ste1m_race_grid` | `$e60` | standing (time-out state), message held + face, position 84 |
| `gno` | `ste1m_race_grid` | `$e30` | standing, no speech |

Geometry (verified, not assumed): with `--borders false` the screenshot is 640x436 = 640x400 game area + 36-px status bar; the game area is the top-left 640x400, every 2x2 block uniform (asserted in `common.load_shot`), so 320x200 = every second pixel. `ref/boxes_check_drvsp.png` overlays the ten stock HUD boxes of `hud.md` §1 on the decoded frame: all boxes hug their elements. The captured `$70000` buffers are **byte-identical** to the earlier study's stock buffers at the same pass (`hud/res/shots_race_start_stock/s70_70000.bin`, `sa0_`, `shots_race_grid_stock/se30_`, `se60_`: 0 differing bytes in 4 of 4; python compare, output `work/hud/design/cap/verify.txt`).
The displayed buffer is `$70000` in all four captures (`m $ff8200`: `00 07 00 ..`).

Palette (from the game's own tables, dumped in `cap/*_pal.bin`; screenshot colours = 34 x the 3-bit ST value, checked pixel by pixel against the decoded index images):
`$3cd4` = base palette for colours 0-14 in the top zone: `0:000 1:111 2:000 3:754 4:333 5:330 6:664 7:666 8:221 9:432 10:543 11:765 12:410 13:550 14:667`; `$3cf2` = road palette for colours 1-14 (switched in by timer B at row **74** in all four frames); **colour 15 = the sky** and its colour is rewritten per raster band (`256` rows 0-45, `356`, `357`, `457` below; script `$3cc0`, table `$3cc4`). The sky is **flat colour 15**: in rows 0-64, outside the stock HUD boxes, the buffers contain only index 15 (sky) and 14 (clouds, `0x667`): `Counter({15: 4268, 14: 772})` (gno), `{15: 4234, 14: 806}` (drv) (`cap/verify.txt`). So "restore the sky" = fill with all-ones words, which is also what the message box erase `$12086 -> $1242c` does (colour 15, x 112-303, rows 16-64).
Fonts used in the mockups come from the game RAM dump (`work/dumps/ram_race_start.bin`): 8x14 digit glyphs at `$196ae` (28 B per glyph, index = char - `$2f`, only blank + `0-9` exist: `work/hud/design/cap/glyphs.png`) decoded with the stock kernel formula (`$cd` = yellow 13 / dark-red shadow 12, what `mr_digit` draws), 8x8 message font at `$190be` (16 B per glyph, index = char - `$20`, full ASCII): labels use the ticker colours `$b8` (cream 11 + dark 8), values the digit colours (`$dc`: yellow 13 + dark red 12).
The bottom corners in the mockups are the real road: the all-HUD-calls-skipped buffers of the earlier study at the same pass (`hud/res/shots_*f1c0+efc6+...`, rows 120-199 copied). The top stock HUD boxes and the clouds (colour 14, rows 0-72) are replaced by sky; the face portrait pixels are kept.

## 2. The three layouts (all coordinates in ST pixels; bar/panel colour is one palette index, free choice; no field uses colour 15 except the sky behind B's cluster)

Common to all: message text (ticker, x 112 y 24, box erase 112-303 x 16-64) and face (272,17, 32x48) stay where they are and are not touched; the top-left sky (old minimap/thermometer/dial/score area) is plain sky, the mountains only start at row 65+; bottom corners show road only. The bar never overlaps the ticker box (starts at row 16) or the face (row 17): A's bar ends at row 15, B's at row 9, C's panel at x 111.
All digit cells sit on byte boundaries (x multiple of 8): a glyph is written as four plane bytes (`movep.l`), no shift, no mask; the dial/icons sit on 16-pixel boundaries (word writes).

### Layout A: full 16-row strip, big digits (`layout_A*.png`)
Bar rows 0-15, colour 2 (black, `0x000`; colour 2 is non-zero in plane 1 so a cleared screen is distinguishable, section 5.5). Fields (y = 1 for 8x14 digits, labels 8x8 at y = 4):

| field | x range | what | static / redraw trigger |
|---|---|---|---|
| bar background + labels + cup icon + gauge frame + score trailing `0` | 0-319, rows 0-15 | one pre-composed 2,560-byte bitmap (rows 0-15 x 160 B) | static, copied once per buffer (section 5) |
| SCORE | 8-47 (5 cells), `0` fixed at 48 | `$11c2` as 5 decimal digits, leading blanks; `$11c6` selects the end-of-race colour set | per digit, when that digit differs from the digits last drawn in this buffer |
| DIAL | 64-79, rows 0-15 | half-size clock (16x16): face + hand | when `(hi byte of $10ce) >> 3` differs from this buffer's shadow |
| POSITION | `#` label 88 (static), digits 96-111 | `$10ca` 1..99 | per digit |
| SPEED | digits 120-143, `MPH` 152-175 (static) | hi word of `$10d8` (0..92, 128 with turbo), 3 cells | per digit |
| GEAR | `G` 184 (static), digit 192 | `$11d9` (0/`$ff`) as `1`/`2` | on change |
| TEMP | `T` 208 (static), digits 216-231 | `$10ba` clamped 0..35 (2 cells; "hot" glyph set from 28 up) | per digit |
| TURBO | cup icon 240-255 (static), frame 263-292, fill 264-291 (28 px, 1 px per unit of `$10c0`) | `$10c0` 0..28 | on change |

### Layout B: thin 10-row strip, 8x8 game font, cluster on the sky (`layout_B*.png`)
Bar rows 0-9, colour 4 (`0x333`), text rows 1-8: `SCORE` 8-47 / digits 56-95 / fixed `0` 96, `MPH` 112-135 / digits 144-167, `GEAR` 184-215 / digit 224, `TEMP` 248-279 / digits 288-303. Below the bar at the left, directly on the sky (no bar behind, fields are pre-composed on sky colour 15 so no mask is needed): DIAL 0-15 rows 12-27, `POS` 24-47 / digits 48-63 (y 14), cup icon 24-31 + gauge frame 39-68 / fill 40-67 (y 22-29).
Static: the strip bitmap (1,600 B), the cluster's labels/icon/frame (small bitmap blitted once). The sky below the strip (rows 10-64) is cleared once per buffer.

### Layout C: compact corner panel (`layout_C*.png`) - NOT a full-width bar
Black panel x 0-111 rows 0-33 (112 = 7 sixteen-pixel groups, 56 B/row, 1,904 B): four 8x8 text lines y = 1, 9, 17, 25: `SCORE` / digits 56-95, `SPD` 8-31 / digits 40-63 / `G` 72 / digit 80, `TMP` / digits 40-55 / `#` 64 / digits 72-87, cup icon 8-15 + gauge fill 24-51 (y 27-30); dial 96-111 rows 9-24 (right of the text, under the score line). The rest of the top (x 112-319, rows 0-15) is free sky: the whole width above the ticker/face is empty. This variant deviates from "top bar" and is offered because it is the smallest area to paint and leaves the sky open.

## 3. Cost per pass

### 3.1 What goes away (hud.md, driving, no speech, cycles per pass; "shipped" = `mr_edge+mr_map+mr_digit`)

| removed | stock [S] | on the shipped set [S] |
|---|---:|---:|
| clouds `de1c + de6c` (not HUD) | 80.8 k | 80.8 k (their code is untouched by `mr_*`, **[INFERENCE]** same on the shipped set) |
| minimap `f214 + f22c` | 63.3 k | 39.4 k |
| score `f3b6` | 36.5 k | 17.0 k |
| speedometer `f7f0` | 21.5 k | 18.7 k |
| gear lever `f76a` | 13.1 k | 10.8 k |
| cup `f620` | 11.6 k | 9.9 k |
| dial `f53c` | 11.1 k | 9.4 k |
| thermometer + puff + position | 0.7 k idle (+ ~1.9 k average per race for the 2 redraws per change) | same |
| **all 13 HUD calls** (measured together, includes ticker + face idle 0.18 k) | **148.4 k** | **111.4 k** |

### 3.2 Kernel costs measured for the new design
Micro-benchmark `work/hud/design/bench/kern.s` run in the race snapshot with interrupts off (`python3 work/sprite/unit.py work/hud/design/bench/kern.s --snap race_start`, raw timeline `work/hud/design/bench/kern_result.txt`, 100 calls between two markers; each figure includes the two `lea`, `jsr`, `rts`, `dbra` of the test loop):

| kernel (precomposed strips, no mask, no shift) | cycles per call **[M]** |
|---|---:|
| 14-row glyph, `move.l (a1)+,d0 / movep.l d0,n*160(a0)` per row (odd byte address) | **576** |
| 8-row glyph, same | **360** |
| 14-row glyph with 4x `move.b` per row (same data layout, no `movep`) | 968 |
| 16x16 dial/icon copy (2x `move.l (a1)+,(a0)+` + `lea 152(a0),a0` per row) | 840 |
| word -> 5 decimal digits, 5x `divu #10` loop | 932 |
| sky clear, `movem.l` 12 regs, 6,720 B (loop with counter) | 18,292 (2.72 cycles/B; unrolled 14 regs ~2.14 cycles/B **[INFERENCE]**) |
| bar copy, `movem.l (a1)+` / `movem.l ,(a0)` 12 regs, 2,240 B | 9,596 (4.28 cycles/B) |

For comparison (measured earlier, `render_patches.md` §4 / `hud.md` §7): the existing score path with `mr_digit` costs **2.98 k per glyph** (kernel 1.43 k for 15 rows + the `1235e` occupancy copy + overhead), the stock path 6.06 k per glyph. A pre-composed strip with `movep` is 5.2x cheaper than the `mr_digit` path (576 vs 2,980) and the 8x8 version 8x (360). If the user prefers to reuse `11d42`/`mr_digit` unchanged the glyph price is 2.98 k.
Hand count agreement: 14 rows x (12 + 24) + 70 call overhead = 574 cycles; the measurement says 576.

### 3.3 Per-pass cost of the new HUD stage (value-change redraw, per-buffer shadow, first frame excluded)
Redraw rules (section 5.2): every field is compared with what was last drawn **in the buffer being drawn** (two shadows, one per buffer); nothing is drawn when equal. Rates from `hud.md` (driving, cruise): the score `$11c2` rises by 1 per pass, so the last digit differs from the buffer's shadow every pass (1 draw/pass), the tens digit 2 draws per 10 passes, hundreds 0.02: **1.22 glyph draws per pass**; temperature 124 changes per 1,707-pass race (x2 buffers); position 16 changes per race; dial hand quantised to 32 angles (every 8th hi-byte step = 1 per ~52 passes x 2 buffers = 0.04 draws/pass); speed saturates at hi 92 at cruise (changes only while accelerating / after hits); gear and gauge only on events.

| item | A (14-row glyph) | B / C (8-row glyph) | basis |
|---|---:|---:|---|
| idle compare chain (10 value compares, buffer parity, flag tests) | 350 | 350 | **[INFERENCE]** hand count, ~30-35 cycles per field |
| score: binary -> digits when `$11c2` changed (every pass at cruise) | 932 | 932 | **[M]** K5 simple loop; **[INFERENCE]** ~300 with a divu-by-100 + table variant |
| score glyph draws, 1.22 per pass | 703 | 439 | 576 / 360 **[M]** x 1.22 |
| speed (~0.15 k) + temperature (~0.2 k, 2 redraws per change) + position (0.02 k) + dial (0.04 draws x 840) + gear/gauge (~0) | ~400 | ~340 | **[INFERENCE]** from the rates above and the **[M]** kernel costs |
| **typical driving pass** | **~2.4 k** | **~2.1 k** | (1.8 k / 1.5 k with the optimised conversion) |
| standing, nothing changes | 0.35 k | 0.35 k | idle chain |
| worst pass (everything changes at once: 13 glyphs + dial + gauge + conversions) | ~12 k | ~9 k | rare **[INFERENCE]** |

### 3.4 Saving per driving pass (no speech), cycles / share of the pass / VBL (160,256 cycles per VBL)

| basis | removed | new HUD | clouds | **net saving** | pass |
|---|---:|---:|---:|---:|---|
| shipped set, A | 111.4 k - 0.18 k kept (ticker, face idle) = 111.2 k | 2.4 k | 80.8 k | **189.6 k = 27.6 % of 687.5 k = 1.18 VBL** | 687.5 k (4.29 VBL) -> ~497.9 k = **3.11 VBL** |
| shipped set, B / C | 111.2 k | 2.1 k | 80.8 k | **189.9 k = 27.6 %** | -> 3.11 VBL |
| stock basis, A | 148.4 k - 0.18 k | 2.4 k | 80.8 k | 226.6 k = 26.8 % of 846 k | 846 k -> 619 k |
| standing (race_grid, stock) | 108.8 k - 0.18 k | 0.35 k | 80.3 k | 188.6 k = 24.8 % of 761.4 k | |

Speech passes keep their ticker + face cost unchanged (19.7 k per typing pass, 12.7 k held, 2 x 35 k per message end, `hud.md` §5.2) in every row. The 4.29-VBL figure is the user's; I did not re-measure the shipped pass. **The driving pass at 3.11 VBL is 16.4 k cycles above 3.00 VBL (481 k)**; levers that are not part of this layout: the occupancy-map writers `1231e/1233a/1235e/1237c` and the map write inside `1242c` are dead work once the clouds are gone (nothing else reads `$6f000`; face mask part 5.3 k per active pass, ticker `1237c` ~0.4 k per glyph, `hud.md` §1 last paragraph, **[INFERENCE]** for the total), the face drawn once per message (-12.3 k per active pass), `dd50` (cloud position update, called at `$7b3a` and in `mx`) ~0.8 k **[INFERENCE]**; none of these helps a no-speech pass except `dd50`.

### 3.5 One-off costs (first frame / (re)start, per buffer, both buffers are painted over the first two passes)
Bar bitmap copy A 2,560 B ~ 11.0 k (B 1,600 B ~ 6.9 k, C 1,904 B ~ 8.1 k, at the measured 4.28 cycles/B) + sky clear rows 16-64 (A; 49 x 160 = 7,840 B, ~17 k unrolled / 21 k as measured loop; B rows 10-64: 8,800 B ~ 19-24 k) + every field once (14 glyphs x 0.58 k = 8.1 k, dial 0.9 k, gauge ~1.2 k, 2 conversions 1.9 k) = **~40-45 k per buffer for A, ~85 k over the first two passes** (0.5 VBL, once per race). The stock first pass redraws everything as well (score 36 k, minimap 63 k, ...), so the new first frame is cheaper than the stock one.

## 4. What the new design reads, writes, and must keep working

Reads only (display): `$11c2` score, `$11c6` end-of-race colour flag (`fa8c`/`fad2`: the bonus count draws the score in the `$c7` colours), `$10d8` speed (hi word), `$11d9` gear, `$10ba` temperature (clamp 0..35 as `efc6`), `$10c0` fuel (clamp 0..28, the end-of-race bonus `faae..fad6` counts it down: the gauge animates by itself), `$10ca` position (clamp 1..99), `$10ce` clock long (clamp 0..`$ff0000`, hi byte = hand), `$1226` (state; stock draws a broken thermometer at 1-4: no equivalent needed, the number just shows the clamped value).
Writes: nothing that the game logic reads. hud.md §4.2 measured that the stock caches/flags (`$10bc $11c9`, `$11c4 $11c7`, `$10cc $11cc`, `$10d4 $11cd`, `$11ca/$11cb` puff, `$10c2-$10c8` erase pointers, `$11cf` slosh animation, `$11da-$11dc` lever animation) are HUD-owned: skipping the routines changed **0 other bytes** over 133-177 passes. They are simply left unused (the race init `$edee..$ee60` still initialises them, harmless).
Two behaviours must be kept: (1) the **hit flag `$11ce`**: `f620` consumes it (`tst.b $11ce / clr.b $11ce,$11cf / jsr $7bb2 with d0=$36,d1=2`, `f640..f65c`, `f6f8`): the new routine keeps these 4 instructions so the slosh sound `$36` on a hard hit stays and the flag does not stay set; (2) the **message ticker** `11ef0` must still be called every pass (state `$11ab/$11b1/$11ac...`, the race-end/time-out flow waits on it, `hud.md` §5.2: skipping it soft-locks the game); its drawing is untouched in this plan. The face `f90c` call stays too (the user did not decide).
Nothing else calls the removed routines: single call sites at `$ef7e-$efc0`, the stage itself is called once at `$7b4c` (grep over `work/hud/dis/all_7000_19000.txt`); `11d42` (score text) only from `f428`.

## 5. Implementation plan (not built)

### 5.1 Hook sites
| # | site | original bytes | new | purpose |
|---|---|---|---|---|
| H1 | `$ef7a` (stage `ef7a`, called once from `$7b4c`) | `2a78 1008 4eb9` (6 B, `movea.l $1008.w,a5 / jsr` of the first call) | `jmp NEWHUD.l` | replaces the stage; NEWHUD ends with `rts` to the `jsr $ef7a` at `$7b4c` |
| H2 | `$edea` (race init, called once from `$7926` for every race start/restart, with `$100e` = 0) | `4eb9 0000dd18` (`jsr $dd18`, cloud init) | `jsr HUDINIT.l` | HUDINIT replays `jsr $dd18` (keeps `$29c8..` slot init so the unchanged `dd50` / the `$29c8` table stay consistent) and invalidates both buffers |
| H3 (optional) | `$7b3a` `jsr $dd50` | `4eb9 0000dd50` | `nop` x3 | cloud position update has no consumer once `de1c/de6c` are gone (**[INFERENCE]** ~0.8 k per pass; `mx_sync` also calls it, section 6) |

NEWHUD (the whole stage): `jsr TOPBAR` ; `jsr $11ef0.l` (ticker, same call as `$efa0`) ; `bsr $f90c` (face, as `$efa6`) ; `rts`. Dropped calls: `de1c f1c0 efc6 f214 f3b6 f430 f53c f620 f76a f7f0 de6c f22c f134` (`f1c0/f134` = engine-fire puff over the old thermometer: it would draw into the new bar; the overheat warning becomes the "hot" glyph colour of the TEMP field from 28 up, the level at which the game says "The engine's on fire").

### 5.2 TOPBAR: one combined routine
State (blob data, 2 identical sets S0 for `$70000`, S1 for `$78000`, chosen by `btst #15` of the back-buffer pointer `$1008`): `painted` byte, the digit/value last drawn in this buffer for every field (score 5 digits + colour set, speed 3, gear, temp 2 + hot flag, position 2, fuel, dial angle >> 3). Invalid = `$ff` (differs from every digit/blank code).
Per pass:
1. a5 = `$1008`; select the shadow set; if `painted` = 0: PAINT (bar bitmap copy rows 0..15, sky fill rows 16..64 of the **whole width**, label/icon statics are part of the bitmap), set `painted`, set every shadow value to `$ff`.
2. Per field: read the game variable, clamp as the stock routine does, compare with the shadow (word/byte compare, ~30 cycles); on difference convert (`divu`), compare digit by digit, draw only the differing glyphs (`movep` kernel: `a0 = buffer + y*160 + (x>>4)*8 + ((x>>3)&1)`, strip pointer = base + digit*64 + set*...), update the shadow.
3. Dial: `hi = byte 0 of clamp($10ce)`; angle = hi >> 3; if differs: copy one of 32 pre-composed 16x16 images (128 B each, 4 KB, built offline from the game's own sprite id 32 at `$1b076+14*32`, half-sized, with the hand drawn by the build script) with 2x`move.l (a1)+,(a0)+` per row (**[M]** 840 cycles).
4. Gauge: if `$10c0` (clamp 0..28) differs: draw the fill (28 px, 6 rows x 4 byte columns, mask from a 32-bit shift) ~1.2 k **[INFERENCE]**.
5. `$11ce` consume + sound `$36` (as in `f620`).
Each change is therefore drawn exactly once per buffer, two passes later in the other buffer: the "redraw twice" flags of the stock routines are replaced by the shadows (they also cope with extra frames and with any number of passes between redraws).

### 5.3 Stale pixels: one-time clear, when, how
Stock leaves the previous HUD in both buffers and the cloud erase wipes parts of it; the race restart **does not clear the screens** (`sprites.md` §7, `restart_trace.py`). After the change these regions hold stale pixels: minimap box and frame lines (16,15)-(95,64), thermometer (0,9)-(31,64), score (32,1)-(79,14), dial (80,16)-(111,46), position (80,49)-(111,62), **all cloud pixels** (colour 14, rows 0-~72 over the whole width, the drift of every cloud), the stale minimap contents. Rows >= 65 clean themselves (horizon strip copy `18318` rewrites rows 65-119 every pass, the road rows 120-199 are repainted, `hud.md` §4.3 bottom items: "nothing stale"). So PAINT clears **rows 0..64 of the whole width** in both buffers: bar/panel + sky colour 15 fill (sky = all-ones words, as the ticker's own erase does).
When: at the first TOPBAR call per buffer after HUDINIT (H2) = every race start/restart (the only path into the loop: `$7926`), plus the first frame. Not in the displayed buffer: it is done lazily for the back buffer only. If a message happens to be typed in that very pass the clear wipes its glyphs in that buffer (the ticker does not retype them); at race start/restart no message is active (first message at pass `$14`, previous ones finished before the time-out restart) **[INFERENCE: ticker state is not reset by the init `edea..ef2c`]**.
Sentinel (optional, 30 cycles): compare one bar word (A: row 0 col 0 = plane pattern of colour 2, non-zero in plane 1) with its expected value each pass; if a screen clear (`d8e0`, other callers `$719c $7368 $73e6 $769a $7be0 $7c0c $7d26 $842c` are outside the race loop) ever happened without passing `$edea`, `painted` is reset. Cheap insurance against paths I did not find; not required by anything I traced.

### 5.4 Data and RAM
Code ~1.4 KB + data **[INFERENCE]**: A: bar bitmap 2,560 B + glyph strips 11 chars x 64 B x 3 colour sets (normal, end-bonus `$c7` colours, hot) = 2.1 KB + dial table 4 KB = ~10 KB; B/C: 1.6 / 1.9 KB bitmap + 8x8 strips 11 x 32 x 3 = 1 KB + dial 4 KB = ~8 KB. Free RAM (patches/README.md address map): `$BA8C0-$CFFFF` is free (the image limit is `$C16FF`, default payload ends at `$B8F0B`, mx data up to `$BA8BF`): suggest `$BB000-$BDFFF`. The floppy build needs ~16-20 more sectors for 10 KB **[INFERENCE]**. After the change `mr_map` (minimap kernel `$12690`) and `mr_digit` (score kernel `$14d98`, only reached via `11d42`) are dead code: they can be dropped from the default set.

## 6. The extra-frame prototype (`mx_sync` / `mx_pre`): touchpoints
`mx_sync.s` has its own copy of the HUD stage (`hud:` lines 370-402: `de1c f1c0 efc6 f214 f3b6 f430 f53c`, ticker with saved state, `f90c f620 f76a f7f0 de6c f22c f134`) run for every extra frame. If H1 is applied and `mx_sync` is not changed the extras would call the old routines: the speedometer/gear/cup/minimap would reappear in extra frames only. Required changes:
1. `hud:` -> `jsr TOPBAR`, the ticker block with its state save/restore (unchanged), `jsr $f90c`.
2. `UTAB` entries `$10bc,2` and `$11c4,12` (stock flags/caches) become dead; `$10ec,14` (face state) stays. **The new shadows must NOT be restored by the group undo**: they describe what each buffer really contains, which is exactly the "display history" `mx_sync` already leaves alone (cloud x/y, HUD erase pointers); with per-buffer shadows the extra frames need no flag bookkeeping at all (stock needs the `restoreundo` of `$10bc/$11c4..` so that the main frame takes the same decisions).
3. `.frame`: `clr.b $11ce.w` (alarm flag so the extras do not beep) stays; `move.w UNDO+8.l,$11ca.w` (puff animation) becomes meaningless (puff gone): remove or ignore. `jsr $dd50.l` (cloud update): remove together with H3.
4. KTAB (100 self-modified kernel longs): the face RNG `$dafe` entry stays; kernels that only the dropped HUD sprites patched simply stop changing (restoring them is harmless). Re-run `work/extrap/kern_union.py` once on the new build **[INFERENCE: not needed, not run]**.
5. Extras get cheaper by the removed 100-140 k, so more extras fit into a tick (`exp_mx.py` rate figures change).
`mt_clock/mt_pre/mt_sync`, `rd_*`, `mr_edge`, `pp_bigram_cache`, `core*` do not reference HUD addresses (grep of `patches/*.s`).

## 7. Risks
1. **Stale pixels** (section 5.3): bar/panel and sky are painted per buffer on the first pass after `$edea`; a missed clear shows old clouds forever (nothing erases them any more) or a frozen minimap. Gate: compare rows 70-199 against the all-HUD-calls-skipped reference buffers of the earlier study at the same pass (rows >= 120 identical by construction, `hud.md` §4.3) and rows 65-69 allowing cloud pixels only; check the top rows by eye on the first 10 passes of a restart.
2. **Ticker/face interplay**: ticker erase fills colour 15 in x 112-303 rows 16-64 and the face is drawn at (272,17): both are below A's bar (row 15), B's bar (row 9) and right of C's panel (x 111). Layouts that grow the bar into row 16 or the panel past x 111 collide with them.
3. **Raster palette**: colour 15 changes per band, colours 1-14 switch to the road palette at row 74 (all four frames). The bar must use colours 0-14 only and stay above that row; B's cluster on the sky intentionally uses colour 15 (pre-composed on the sky, follows the gradient).
4. **Extra frames** (section 6) must be changed together with the hook; otherwise old HUD pieces appear in the extras only.
5. **Sound `$36`** kept; without the consume of `$11ce` nothing breaks (the flag is HUD-only) but the sound would be lost.
6. **`$11c6`** (score colour in the end-of-race bonus count) and **`$1226` states 1-4** (stock shows a broken thermometer): handled as above; the second is a look change (the number just shows 35).
7. **Mid-message paint**: if TOPBAR's PAINT runs while a message is typed, that buffer loses the glyphs typed so far; only possible when HUDINIT happens during a message (not seen).
8. **Kernel self-modification quirk** (`extrap.md` stale-immediate): removing all HUD sprite calls changes which kernel immediates were last patched. hud.md §4.2 saw no pixel change outside element boxes in any single skip and state identical for all 13 together; the combined removal plus clouds is not pixel-gated yet: the standard gate (identical pixels outside the HUD zones over several hundred passes) must be run on the first build.
9. **Hatari only**: all cycle numbers are Hatari 2.6.1 STE 8 MHz; `movep` timing 24 cycles (68000) is what Hatari uses; on a real 68000 the same.
10. The shipped patches `mr_map`/`mr_digit` become dead; `patches/PATCHES.TXT`/README entries need updating when built.

## 8. Decisions needed from the user
1. Layout: **A** (full strip, big digits; recommended: best readability, dial fits inside, 2.4 k), **B** (thin strip with labels, dial/position/turbo hanging below; 2.1 k), **C** (corner panel, deviates from "bar", smallest area).
2. Bar colour (any palette index 0-14: black `2` in A/C, grey `4` in B in the mockups), keep the labels (`MPH`, `G`, `T`, `#`, `POS`) in the game's 8x8 font or use pure numbers.
3. What the speed number means: raw hi word of `$10d8` (0..92, 128 with turbo; shown in the mockups) or scaled (x2 ...); unit label.
4. Gear shown as `1`/`2` (the font has digits only; which of `$11d9` = 0 / `$ff` is low gear is **[INFERENCE]** from `010d22..010d70`) or as new `L`/`H` glyphs.
5. Temperature "hot" colour from 28 (the game's own fire warning level) and whether the exploding states 1-4 should show something.
6. Dial hand resolution: 32 angles (4 KB table, ~0.04 draws/pass) or 256 (one pre-composed image per step needs 32 KB, or draw the hand with the line kernel `127fa`: ~1.8 k per redraw, 0.3 draws per pass = ~0.55 k average).
7. Turbo shown as gauge (as in the mockups) or as a two-digit number.
8. Speech: keep face + ticker drawing as is (this plan), draw the face once per message (-12.3 k per active pass), kill the dead occupancy-map writers (up to ~7 k per active pass **[INFERENCE]**), cheaper ticker glyphs (`hud.md` §5.2). Remaining gap to 3.00 VBL for no-speech passes: ~16 k cycles, not covered by this HUD change.
9. Drop `dd50` (H3) and `mr_map`/`mr_digit` from the default set.

## 9. Files
`work/hud/design/`: `capture.py` (Hatari capture, own scratch/memstate), `common.py` (planar decode, palette, font tables), `mock.py` (mockup generator; run `python3 work/hud/design/mock.py`), `cap/` (raw captures: `<tag>_{70000,78000}.bin`, `_pal.bin`, `_state.txt`, `_shot.png`, `glyphs.png`), `ref/` (320x200 stock frames `<tag>_stock320.png`, the earlier raw screenshots cropped, `boxes_check_drvsp.png`), `layout_{A,B,C}.png` (driving + speech, 3x), `layout_{A,B,C}_{drv,drvsp,gsp,gno}.png` and `*_annot.png`, `strip_{drv,drvsp,gsp,gno}.png` (before/after strips), `stock_{tag}.png` (stock frames 3x), `bench/kern.s` + `bench/kern_result.txt` (kernel micro-benchmarks).
Reproduce a capture: `python3 work/hud/design/capture.py ste1m_race_start.sav drv "(\$100e).w = \$70" 4`; micro-benchmark: `python3 work/sprite/unit.py work/hud/design/bench/kern.s --snap race_start`.
Process note: each Hatari was started by the harness with its own `/tmp/mhd_<tag>` or `strun-*` scratch dir and closed by the script; no process of another agent was touched.
