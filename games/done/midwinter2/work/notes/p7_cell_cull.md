# P7 items 3 + 4: terrain cells that emit nothing (patches `p7_cell_pre`, `p7_cell_cull`)

Both patches are `default: no`. Blob range `$B5800-$B5FFF`: code `$B5800` (pre) and `$B5B00` (cull), data `$B5C00-$B5D1F` (288 B declared).
Everything below is measured (source named) or marked `[INFERENCE]`. Scripts: `work/p7_cell_gate.py` and `work/p7_cell_poke.py` (identity gates); capture, replica, profile and cold-boot scripts in `work/p7_cell/` (they read and write the capture directory `/tmp/cc`; see "Reproduce").

## 1. Result

**Identity gate** (`python3 work/p7_cell_gate.py --flips 10 40`; p4 default set applied live in both runs, the second run adds
`p7_cell_pre p7_cell_cull`; same absolute VBL and flip; both screen buffers compared). Raw output:

```
1mb_ingame_walking at_vbl=21500 flips=10: IDENTICAL  md5 aba7f684 46811a8d | aba7f684 46811a8d
1mb_ingame_walking at_vbl=21500 flips=40: IDENTICAL  md5 56a68464 1701b6e3 | 56a68464 1701b6e3
1mb_ingame_foot at_vbl=17900 flips=10: IDENTICAL  md5 f608520e 4c53548d | f608520e 4c53548d
1mb_ingame_foot at_vbl=17900 flips=40: IDENTICAL  md5 f30c535e e68d13c7 | f30c535e e68d13c7
ingame_foot_banked_turn at_vbl=419400 flips=10: IDENTICAL  md5 80f9f855 0eda37fc | 80f9f855 0eda37fc
ingame_foot_banked_turn at_vbl=419400 flips=40: IDENTICAL  md5 23a0ce7e 244fee47 | 23a0ce7e 244fee47
```

**View-variation gate** (`python3 work/p7_cell_poke.py`, then `--positions --flips 6 --snapshot <f> <w>`). The three snapshots only show a few headings, so both runs (p4 vs p4 + p7_cell_*, live)
write the same camera state at the first flip after the same VBL and save both buffers 4 (6) flips later. Angles: heading `$6742` (mirrored `$6294`, `$764a`) over 12 values, plus 8 bank (`$6746`) / pitch (`$674a`)
combinations, on w, f and the banked-turn snapshot; positions (`$66e6/$66ea`, copies `$66ee/$66f2`): 14 map cells with the heading varied, among them 8 coast cells (water next to land:
class 0/1 cells next to the hooked land cells, `$1dad0/$1db5e` paths) and the west-edge peak (h 3262), on f and w.

```
60/60 identical   (angles: 20 states x 3 snapshots)          log: /tmp/cc/poke.log, first line of each: "<snapshot> heading/bank/pitch=(...) state0=...: IDENTICAL md5 ... | ..."
28/28 identical   (positions: 14 map cells x 2 snapshots)    log: /tmp/cc/pos.log, e.g.
1mb_ingame_foot ((59, 48), (256, None, None)) heading=0100 alt764c=2000: IDENTICAL  md5 42d96b91 ecd71fa8 | 42d96b91 ecd71fa8
1mb_ingame_walking ((14, 60), (768, None, None)) heading=0300 alt764c=3481: IDENTICAL  md5 d3f931bb eb596db4 | d3f931bb eb596db4
```

Does the hook fire there? Profile (p4 + p7_cell_*, f snapshot, 19 flips) at the coast cell (59,48) heading 256: 76 cells enter classify per frame, 27 of them are land cells that reach the hook, 26 are culled
(kept 1), 58 vertices transformed; at the peak cell (14,60) heading 256: 7.2 cells, all 7.2 reach the hook and are kept (the view there is almost empty: 0.2 stream polygons).

**Cycles per presented frame.** Hatari `profile` of a window of 19 flips that starts at the same flip after the same VBL in both runs (the live patch
is applied at that flip, so both runs render the same frames; `work/p7_cell/prof.py`). p4 set live in both.

| snapshot | p4 | p4 + p7_cell_* | delta |
|---|---:|---:|---:|
| `1mb_ingame_foot` (f) | 1,706,386 | 1,658,496 | **-47,890 (-2.81 %)** |
| `1mb_ingame_walking` (w) | 1,276,881 | 1,246,153 | **-30,728 (-2.41 %)** |
| `ingame_foot_banked_turn` (b, 2 MB) | 2,016,058 | 1,985,607 | **-30,451 (-1.51 %)** |

**Hit counts per frame** (profile execution counts / 19 flips; f is exactly periodic, w and b drift slightly):

| | f before -> after | w | b |
|---|---|---|---|
| cells entering the classify loop (`$1d8f8`) | 63 -> 63 | 67.6 -> 67.6 | 80.1 -> 80.1 |
| cells that reach slot lookup + polygen prefix (`$1d97a`, `$1ec28`) | 63 -> **20** | 67.6 -> **33.3** | 80.1 -> **43.6** |
| slot lookups (`$1da66`) | 252 -> 80 | 270.3 -> 133.1 | 320.4 -> 174.3 |
| vertices transformed (`$1da92`) | 83 -> **35** | 88.2 -> **51.1** | 101.8 -> **63.6** |
| vertices through the outcode/projection loop (`$1fa1a`) | 83 -> 35 | 88.2 -> 51.1 | 101.8 -> 63.6 |
| polygon records in the stream (`$1fa68`) | 38 -> 38 | 59.6 -> 59.6 | 52.0 -> 52.0 |
| polygons filled (`$38c6e`) | 71 -> 71 | 57.5 -> 57.5 | 62.7 -> 62.7 |
| perspective divides (`$1fa44`) | 20 -> 20 | 29.6 -> 29.6 | 23.8 -> 23.8 |

Triangles are unchanged by construction: the stream, fill and divide counts are identical (the stream holds 2 triangle polygons per surviving cell:
f has 19 such cells = 38 records).

**Where the cycles move** (profile address ranges, cycles per frame, after - before):

| range | f | w | b |
|---|---:|---:|---:|
| classify loop `$1d8d4-$1da66` | -7,423 | -6,026 | -6,450 |
| slot lookup + transform `$1da66-$1dad0` | -31,155 | -25,152 | -26,705 |
| polygen prefix + AND test `$1ebda-$1ecd6` | -21,101 | -16,783 | -18,541 |
| outcode chain + projection loop `$1f9b6-$1fa54` | -12,008 | -9,219 | -9,462 |
| other (rounding in the profile, small) | -1,086 | -750 | -588 |
| blob `p7_cell_pre` (`$B5800`, once per frame) | +3,811 | +3,839 | +3,838 |
| blob `p7_cell_cull` (`$B5B00`, once per cell) | +21,072 | +23,363 | +27,457 |
| **total** | **-47,890** | **-30,728** | **-30,451** |

Per-cell numbers from the f profile (unpatched): classify 387 cy/cell, polygen prefix + AND 512 cy/cell, slot lookup 59 cy per call, vertex alloc +
transform 428 cy and outcode/project about 350 cy per vertex. A culled cell saves about 1.7 k cy including its share of vertices (73 k gross for f's 43
culled cells), the test costs 334 cy per tested cell (21,072 / 63) plus 3.8 k once per frame.

**Item split.** Item 4 is the whole patch. Item 3 is **not built**: section 6 shows that after item 4 only 3 / 4.4 / 25.7 vertices per frame (f / w / b)
are still transformed without being drawn, and why a deferral cannot remove them. The vertex part of item 4's saving is the `$1da66-$1dad0` and
`$1f9b6-$1fa54` rows above.

## 2. What the code does (citations: `work/dumps/ram_ingame_lobos.bin`, `m68dis.py`)

Frame order in `$1dc12` (`$1dc62..$1dca4`): `$1d768` grid init, `$20088` object marker pass, `$1d596` view tables, `$1d434` hierarchy (builds the cell list at
`$18758`, `move.l a0,(a6)+` at `$1d578`, only after the per-cell distance test `cmp.w $4(a0),d3` at `$1d572`), **`$1d8d4` classify**, `$1dcd2`, `$1fa04`
project, `$1ebda` polygen, `$1fa04` again, `$1fa54` stream walker.

`$1d8d4` loop per list cell a0 (`$1d8f8-$1da48`): `movem.w $c(a0),d0-d1` (c, e: signed byte offsets of the cell's column and row in the tables
`$188f8` (T1) and `$18a40` (T2), 8-byte entries X,Y,W,dist), `d4 = $188f8+c`, `d5 = $18a40+e`; `tst.w $18768` (mode); mode 1 (`bne.w $1d93a`) reads the four
corner heights `(a0), $10(a0), $200(a0), $210(a0)` into d0-d3, ORs them (`$1d948-$1d94e`) and `bpl.w $1d974` when no height is negative. `$1d974`:
`move.b #$ff,$a(a0)` (class land), four `bsr $1da66` slot lookups (corners (i,j), (i+1,j), (i+1,j+1), (i,j+1), with `addq.l #8,d4/d5` between them),
`move.l a0,(a5)+` appends the cell to the polygen list `$1875c`, then `bra $1da48`.

Slot lookup + transform (`$1da66`, `$1da92-$1dac2`): `X = ((h*$18568)<<2)>>16 + T1x[i] + T2x[j]`, `Y` with `$1856a`, `W` with `$1856c` (3 `muls.w`,
`asl.l #2`, `swap`, six `add.w`), stored at `$6..$a` of a 12-byte data record and indexed from a 16-byte slot header (`word0` = data offset, record `+8`).
The vertex is appended to the projection list. `$1fa04` computes for each listed vertex (`$1fa1a-$1fa2c`): `Y' = 2Y + (Y>>2)` (`add.w d1,d1; add.w d3,d1` with
`d3 = d1 asr 2`), then the outcode chain `$1f9b6-$1f9f6`: W<0 -> `$1010`; `cmp.w d0,d2` X>W `$808`; `cmp.w d1,d2` Y'>W `$202`; `neg.w d2`; `cmp.w d2,d0` X+W<0 `$404`;
`cmp.w d2,d1` **Y'+W<0 `$101`**. The word is stored at data `+4` (`$1f9fc`), or 0 (`$1fa4c`) after the perspective divide.

Polygen `$1ebda-$1ec26`, per list cell a6 (`$1ebf2`): `bsr $1ec28`, then `move.w $6(a6),d0; bpl.w $1ec0e` and, **only if `$6(a6)` is negative**, it emits a stream
marker (`move.w d0,(a5)+; move.w $18766.l,(a5)+`, `$1ec06-$1ec08`). `$1ec28`: fog band into `$18766`, the four slots (`$1ec68-$1ec84`), `tst.w $18768` (`$1ec88`), `tst.b $a(a6)`:
`beq $1f006`, `bmi.w $1ecba` for class `$ff` (`$1ec92-$1ec9a`). `$1ecba-$1ecd4`: `d0 = $4(a0,d1.w) & ... (4 corners)`; `beq.b $1ecd6` (emit triangles) else **`rts`**.

The grid records' `+6` word is the object hash link: `$20222-$20250` (called from `$200b4/$20136/$201ac`) stores `-d2` (key counter >= 4) with
`move.w d4,$6(a1,d1.w)` at the cell `$6c000 + y*512 + x*16 + $1ad0`, and `p4_grid`/`$1d768` clears `+6` every frame.

Tables T1/T2 (`$1d596-$1d6a6`): entry 0 written by `movem.w d0-d2/d7,(a0)` (`$1d5fe`, `$1d65c`), then two 20-iteration loops add (`$1d632-$1d644`) or subtract
(`$1d60c-$1d61e`) the constant step `$18524+` (T1) resp. `$1852a+` (T2) in 16-bit arithmetic: `T[i] = T[0] + i*step (mod 2^16)`.

## 3. Why a skipped cell cannot emit anything (the proof)

Hook: `$1d974` is entered only with mode 1 and all four corner heights >= 0 (flags of `or.w` at `$1d94e`, `bpl.w $1d950`), i.e. class `$ff`, whose polygen path is `$1ecba`
(`$1ec88-$1ec9a`). The hook skips the cell (jumps to `$1da48`, the loop's next entry) when all of the following hold; otherwise it replays `move.b #$ff,$a(a0)` and
jumps to `$1d97a`, which is the unmodified code.

**L1 - the cell would produce nothing.** If `$6(a0) == 0` (the hook keeps every cell with a non-zero `+6`, because polygen emits the object marker even for a cell
without triangles) and the AND of the four corner outcodes is non-zero, polygen returns at `$1ecd4` and does nothing else for this cell (`$6(a6) >= 0`: no marker). The
outcode AND is non-zero if bit `$101` is set in all four, i.e. `Y'+W < 0` at each corner (sign of `cmp.w d2,d1` at `$1f9ec`, no wrap, see L3).

**L2 - the bound.** For corner v=(i+dx, j+dy), height h_v in [0, hmax]:
`Y = floor(h*mY/2^14) + Y1[i+dx] + Y2[j+dy]`, `W` likewise (`mY = $1856a`, `mW = $1856c`, `Y1/W1` = T1 words +2/+4, `Y2/W2` = T2 words +2/+4), and `Y' <= 2.25 Y`
(`Y>>2 <= Y/4`). With `K = 9 mY + 4 mW`, `CB1[i] = 9 Y1[i] + 4 W1[i]`, `CB2[j] = 9 Y2[j] + 4 W2[j]`, `K >= 0`, `h >= 0` (floor(x) <= x):
`4(Y'+W) <= 9Y + 4W <= CB1[i+dx] + CB2[j+dy] + K*hmax/2^14`. The corner maximum separates: `<= max(CB1[i],CB1[i+1]) + max(CB2[j],CB2[j+1]) + K*hmax/2^14`.
`p7_cell_pre` builds `TC[i] = max(CB1[i],CB1[i+1])` and `TR[j] = max(CB2[j],CB2[j+1]) + 1` for i,j = -7..6 (`CB[k] = C + k*S`, exact because the table is an arithmetic progression, `S = 9 dY + 4 dW`),
and `KC = ceil(K/64)` (`K <= 64*KC`). The hook computes `U = TC + TR + ((KC*hmax)>>8)` and skips when `U < 0`: `K*hmax/2^14 <= KC*hmax/2^8 < ((KC*hmax)>>8) + 1`, so
`9Y+4W < U < 0` at every corner.

**L3 - no 16-bit wrap in the game's own arithmetic**, so the sign tests above equal the real flags. The hook requires (all checked at run time, otherwise the original path runs):
`$67be == 0` (no W shift in `$1dcd2`), `|mY|,|mW| <= 16384`, `K >= 0`, `zc = $1878c >= 0`, `|T1y0|,|T1w0|,|T2y0|,|T2w0| <= 12000`, steps
`|dY|,|dW| <= 512` for both tables (so T entries |i| <= 8 are the integers `T0 + i*d`, no wrap, < 16096), c and e a multiple of 8 with `c+64, e+64` in `0..127` and
entries `i = -8` and `i = 7` poisoned (`+$3fffffff`, never culls). With `VY = floor(-zc*mY/2^14)`, `VW` likewise, `Ay = T1y0+T2y0-VY`,
`BY = |Ay| + 7(|dY1|+|dY2|)`, `BW = |Aw| + 7(|dW1|+|dW2|)`, `HLIM = min(7998-BY, 13998-BW)`; required `HLIM >= 0`, `zc <= HLIM`; per cell `hmax <= HI = min(zc+HLIM, 32767)`.
Then for any corner: `Y_true = (hy+VY) + (T1y0+T2y0-VY) + i dY1 + j dY2` with `|hy+VY| <= |h-zc| + 2` (two floors; `|mY| <= 16384`), and
`h-zc` lies in `[-zc, hmax-zc] ⊆ [-HLIM, HLIM]` (h >= 0, `zc <= HLIM`, `hmax <= zc+HLIM`), so `|Y| <= BY + HLIM + 2 <= 8000` and `|W| <= 13998 + 2 = 14000`. Hence `2Y`, `Y'`
(<= 18000), `neg W`, and `Y'+W` (|.| <= 32000) never wrap, and the stored sums of `$1da92` equal the true sums (partial sums wrap modulo 2^16 only,
the true value fits). The same argument covers the corner `W == 0` special case of `$1f9be` (it needs `Y' = 0` and `W = 0`, but we only cull on `Y'+W < 0`).

**L4 - no other side effect.** A culled cell never gets slots, so: (a) `$67c4` ends lower, polygon data offsets shift (addresses only); a vertex shared with a kept cell is allocated and
transformed by that cell the same way (`$1da66` finds the record `+8` empty); (b) `$18766` is written by the skipped prefix `$1ec28` only; its readers (`$1fbc6` loads it from the stream before every
`jsr $1c3fc` object call, `$38bba` runs only under that call, `$1ed3a..` and `$1f10e..` are in polygen itself) never see a stale value, because `$1c3fc` has a single caller (`$1fbcc`);
(c) the record byte `+a` of a culled cell is not written; `$1ec92` reads it only for list cells; (d) the vertex list order changes, `$1fa04` consumes it item by item.

**Not covered (original path):** mode 0 (`$18768 == 0`), water/shore cells (a negative height: the hook is not reached), blocks the hierarchy does not list, cells with `+6 != 0`,
`$67be != 0`, `K < 0`, zc outside `0..HLIM`.

Replica test: `work/p7_cell/blobsim.py` re-implements the prologue and the cell test in integer arithmetic (the same formulas as the blob) and checks against the game's own outcodes in 22
captured frames (w 12, f 2, b 8, state at `$1ebda`) plus 80 stress frames with mouse turning (`sw` 40, `st` 40): **0 false culls in 1,551 + 5,300 cells**; it finds 84 % of the exactly-culled
cells in the 22 frames (f 98 %, w 95 %, b 70 %; stress sets sw 90 %, st 65 %).

## 4. Implementation

* `p7_cell_pre` (site `$1d8d4`, 8 B `48e7fffe 3e3867c4` -> `jmp $b5800.l; nop`). Replays `movem.l d0-d7/a0-a6,-(a7)` and `move.w $67c4.w,d7`, pushes d7 (it uses d7 as scratch), sets `HI = -1`,
  runs the checks and builds `KC`, `HI`, `TC`, `TR` (3.8 k cy per frame, 1.3 k of it the 32-entry build loop), pops d7, `jmp $1d8dc.l`. It only writes blob data.
* `p7_cell_cull` (site `$1d974`, 6 B `117c00ff000a` -> `jmp $b5b00.l`). Registers at the hook: d0-d3 heights, a0 the cell, d4/d5/d7/a1/a4/a5/a6 live and untouched; d6 (the OR) and
  a2/a3 (scratch inside `$1da66`) are used. d0-d3 are dead afterwards (`$1da66`/`$1da92` reload d0-d2, d3 is never read). Culled: `jmp $1da48.l`. Kept: the displaced
  `move.b #$ff,$a(a0)` then `jmp $1d97a.l`.
* Data `D = $b5c00`: `+2 KC.w`, `+4 HI.w`, `TC = $b5c20` (16 x 8 B), `TR = $b5ca0`, scratch `$b5d00-$b5d1f`. Cell test: 334 cy per cell on average (tst/bne 20, max of 4 heights 48,
  guard 26, two index checks 72, tables 54, `muls` 60, shifts 26, adds 20).
* Interactions: both sites are in the FFB-overlay region (`deferred` phase, like `p4_grid`). `p7_cell_pre` alone is inert (it only writes blob data). `p7_cell_cull` alone
  never culls: with the data block all zero `HI = 0`, `KC = 0`, `TC = TR = 0`, so a cell is kept when `hmax > 0`, and when `hmax == 0` the sum `U = 0` is not negative. Enable both together.

## 5. Alternatives measured and rejected

* **Block-level (3x3 cells, hook inside the hierarchy loop `$1d566`)**, same bound on the 16 vertex heights of the block: only 41-59 % of the exactly-culled cells lie in wholly culled blocks (`work/p7_cell/sim2.py`,
  `sim3.py`; f 27 of 44, w 18 of 31-41, b 15-46 of 46-59), object cells (`+6 != 0`) block 2 of 11 blocks in f, and the hierarchy's own test already uses vertical extremes `[-zc-128, zc+1000]` that no
  global height bound can tighten (the terrain array spans -3484..4058, `$40040` rows of 100 x 4 B). Per-cell is simpler and covers 84-98 %.
* **Extra planes.** Only `Y'+W<0` ("below the window", `$101`) is tested. Per-cell, B alone catches f 43.0 of 43.0, w 35.9 of 37.6 and b 37.1 of 51.8 culled cells per frame (cells with `+6 == 0`,
  `work/p7_cell/sim4.py`); adding the right plane (`$808`, `W-X < 0`, needs an X guard and an own table pair) lifts b to 49.9, the left plane adds ~0, w gains 1.1. Cost for a second plane on the kept cells
  is about 190 cy each (b: 43.6 kept cells = 8.3 k cy + 1.5 k once) for 12.8 more culled cells (21.5 k cy): about +0.6 % in a banked frame, about -0.3 % in f and w (no gain, extra cost). Not built:
  it would need to be enabled only for banked frames (mX != 0), and it adds an X guard to the proof. [INFERENCE for the net, measured for the counts].
* Full exact test on the real corner vertices (outcode after transform): no cost saving, the transform is the cost.
* Hook earlier (`$1d8f8`) to skip the classify preamble of culled cells: at most 100 cy x 43 = 4.3 k (0.25 %), needs the heights and mode test replicated.

## 6. Item 3: vertices transformed but never used

Measured per frame on the same frames (stream decoded at `$1dcaa`, `work/p7_cell/item3.py`; a vertex is "used" when a stream polygon that the walker does not reject (OR of outcodes zero or AND zero, `$1fa9a-$1faa4`)
lists it; "after cull" = vertices of the cells the hook keeps):

| | cells (kept) | vertices transformed before | after item 4 | used by a drawn polygon | still wasted |
|---|---|---|---|---|---|
| f | 63 (20) | 83 | 35 | 32 | **3** |
| w (12 frames) | 64.1 (30.3) | 84.2 | 46.2 | 41.8 | **4.4** |
| b (8 frames) | 78.2 (43.6) | 99.6 | 63.2 | 37.5 | **25.7** |

At 428 (alloc + transform) + about 130 (outcode, no divide) cy per wasted vertex the leftover is 1.7 k / 2.5 k / 14.4 k cy per frame = 0.10 / 0.19 / 0.7 % `[INFERENCE: per-vertex cost from the f profile]`.
A deferred transform cannot remove these: whether a corner is used depends on the AND test of all four corner outcodes (needs the transform), unless a cheaper conservative bound decides first, which is
exactly what item 4 is. In f and w nothing is left to defer; in b the 25.7 vertices belong to about 13 kept cells that only a second plane (section 5) would cull. Recommendation: do not build item 3 separately.

## 7. Cold boot of the full default build plus both patches

Build: `python3 tools/mw2patch.py build --only <every default:yes patch except the floppy-only one> p7_cell_pre p7_cell_cull --out build/p7cell/game`; boot with `work/p7_cell/cold.py <mem_kb> build/p7cell/game`
(`boot_to_game('M')`, marker `$B2FF8`, state `$6220/$700a`, one hit of the `$b5b00` hook, walking and turning).

Raw output (`D:` is the first 8 bytes of `$b5c00`: `KC = $0900` = ceil(147456/64), `HI = $270e` = 9998 = zc 2000 + HLIM 7998, i.e. culling enabled at the 3D view entry; screenshots show the normal 3D view):

1 MB STE, TOS 1.62 (`python3 work/p7_cell/cold.py 1024 build/p7cell/game`):
```
boot_to_game ok in 240s
marker: ['4d 57 50 4f                                      MWPO']
6220 0xd 700a 0x2
D: ["00 00 09 00 27 0e 00 00                          ....'..."]
cull hook hit: True
walk: pos (0, 25600, 0, 25600) -> (0, 24484, 0, 25600)
turn: heading 768 -> 856
D after: ["00 00 09 00 27 0e 00 00                          ....'..."]
done
```
4 MB Mega STE, TOS 2.06 (`python3 work/p7_cell/cold.py 4096 build/p7cell/game`):
```
boot_to_game ok in 214s
marker: ['4d 57 50 4f                                      MWPO']
6220 0xd 700a 0x2
D: ["00 00 09 00 27 0e 00 00                          ....'..."]
cull hook hit: True
walk: pos (0, 25600, 0, 25600) -> (0, 24257, 0, 25600)
turn: heading 768 -> 852
D after: ["00 00 09 00 27 0e 00 00                          ....'..."]
done
```
`MWPO` = every patch applied, `$6220 = $d`/`$700a = 2` = on-foot 3D view, the cull hook was reached (`b pc = $b5b00` hit), the position changes after the throttle pull and the heading after a mouse turn. The 4 MB run
is a 16 MHz machine, so it also exercises the cull at the other clock (the patch is cycle-independent, the per-frame world is not touched).


## 8. Reproduce

All scripts are in `work/p7_cell/` (capture output directory `/tmp/cc`; run the analysis scripts from there, `analyze(<capture>)` takes file names relative to the cwd).
```
python3 tools/mw2patch.py verify
python3 work/p7_cell_gate.py --flips 10 40                               # identity gate, p4 vs p4 + p7_cell_*
python3 work/p7_cell_poke.py ; python3 work/p7_cell_poke.py --positions --flips 6 --snapshot work/snapshots/1mb_ingame_foot.sav work/snapshots/1mb_ingame_walking.sav
# state captures at $1ebda (after classify + project, before polygen) or $1dcaa (after polygen): 0..$90000 per hit
mkdir -p /tmp/cc && cd /tmp/cc
python3 <repo>/work/p7_cell/cap.py <snapshot> <tag> <mem_kb> <n> 1ebda      # f_1ebda_*.bin, w_..., b_... (w: 12 frames, f: 2, b: 8)
python3 <repo>/work/p7_cell/cap2.py <snapshot> <tag> <mem_kb> <n> <dx>      # stress frames with mouse turning -> /tmp/cc/s/
python3 <repo>/work/p7_cell/blobsim.py                                       # replica of the blob vs the game's outcodes: 0 false culls
python3 <repo>/work/p7_cell/sim2.py ; sim3.py ; sim4.py                      # block-level and extra-plane coverage (section 5)
python3 <repo>/work/p7_cell/item3.py 'f_1dcaa_*.bin'                         # vertices used by drawn polygons (section 6)
# profile of a fixed window of flips, base vs mine (live sets built by work/p7_cell_gate.py under build/p7cell/)
python3 <repo>/work/p7_cell/prof.py <snapshot> <out> --mem <kb> --at <vbl> --flips 20 --live build/p7cell/{base_p4,mine_p7_cell_pre_p7_cell_cull}/live
python3 <repo>/work/p7_cell/cnt.py <out>
# cold boot of build/p7cell/game (full default set + both patches)
python3 <repo>/work/p7_cell/cold.py 1024 build/p7cell/game ; python3 <repo>/work/p7_cell/cold.py 4096 build/p7cell/game
```
`--at` values used: w 21500, f 17900, b 419400 (the gate's absolute VBL for each snapshot).
