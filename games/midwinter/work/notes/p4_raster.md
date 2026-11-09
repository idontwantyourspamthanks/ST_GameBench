# MW1 P4 raster/geometry patches (`p4_*`, blob range $B3C00-$B4FFF) and the A/B gate `tools/mw1ab.py`

Items are numbered as in `render.md` section 8. Every patch is `default: no`. All gates: 1 MB STE, TOS 1.62, Hatari 2.6.1, restored
snapshots `1mb_ski_{stand,walk,turn,busy}`; compare = the visible 32000 bytes of **all three** buffers `$58000/$68000/$78000`
at `--flips 8` and `--flips 40` after absolute VBL (snapshot VBL rounded up + 300). Evidence for every address: disassembly of
`work/dumps/ram_ski_walk.bin` (`tools/m68dis.py`), cited inline; unproven statements are marked [INFERENCE].

## 1. The gate: `tools/mw1ab.py`

```
python3 games/midwinter/tools/mw1ab.py --only p4_x [p4_y ...] [--base p4_z ...] [--snapshot stand walk turn busy] [--flips 8 40] [--no-fps]
```
Per snapshot and `--flips N`: restore twice (base / patched), at the first `$bd9a` hit after the fixed VBL apply the live patch set
(`mw1patch.py live`) and `savebin` the 3 buffers N flips later; print `IDENTICAL` or `DIFFER {bytes per buffer}`. For the first N it also
traces every flip for 1000 VBL (`e VBL`, `e FrameCycles` at `pc=$bd9a`) and prints flips per 1000 VBL and the **exact mean cycles per
frame** (VBL*160256 + FrameCycles between first and last flip: both ends are flips, so no edge quantisation). Files live under `/tmp/mw1ab/`
(short paths: Hatari truncates debugger lines); the base capture is cached in `/tmp/mw1ab/<tag>/` (delete it if a `--base` set's code changes).
`live` sites longer than 40 bytes are split into 40-byte `w` lines (a 88-byte site produced a >240-char line and `capture_frames` raised).
Exit status 0 = all identical. Only resident code / loaded data can be gated this way; boot behaviour needs the cold boots (section 7).

## 2. Results (cycles per frame, base -> patched; flips per 1000 VBL base -> patched; all IDENTICAL at 8 and 40 flips)

| Item / patch set | stand | walk | turn | busy |
|---|---|---|---|---|
| #2 `p4_ck_skip` | -64048 (-3.36 %) 82->85 | 0 (no object in view) 111->111 | -73808 (-7.17 %) 152->163 | -53180 (-2.67 %) 78->80 |
| #7 `p4_div_a`,`p4_div_b` | -12885 (-0.68 %) | -11048 (-0.78 %) | -10796 (-1.05 %) | -12196 (-0.61 %) |
| #8 `p4_roll_00..23` | -18315 (-0.96 %) | -16401 (-1.16 %) | -14396 (-1.40 %) | -17614 (-0.88 %) |
| #4 `p4_walk_save`,`_ret_a`,`_ret_b` | -38288 (-2.01 %) 82->83 | -21190 (-1.50 %) 111->113 | -3381 (-0.33 %) | -41298 (-2.07 %) 78->81 |
| #3+#4 + `p4_walk_pro`,`p4_walk_test` | -65981 (-3.46 %) 82->85 | -40107 (-2.83 %) 111->114 | -5060 (-0.49 %) | -76333 (-3.83 %) 78->82 |
| #10 `p4_drv_edge` | -12322 (-0.65 %) | -5956 (-0.42 %) | -790 (-0.08 %) | -12258 (-0.62 %) |
| #9 `p4_fill_save_a`,`_b` | -4384 (-0.23 %) | -2350 (-0.17 %) | -293 (-0.03 %) | -4251 (-0.21 %) |
| #5 `p4_pfx_{fill,ymin,replay,msg}` | -29810 (-1.56 %) 82->84 | -44337 (-3.13 %) 111->114 | -43175 (-4.19 %) 152->158 | -28205 (-1.42 %) 78->80 |
| **Combined (all of the above)** | **-185833 (-9.74 %) 82->90** | **-124897 (-8.83 %) 111->121** | **-142181 (-13.81 %) 152->176** | **-206138 (-10.35 %) 78->88** |

Base cycles/frame: stand 1907634, walk 1414722, turn 1029733, busy 1990879 (these are time-between-flips, so they include the interrupt/VBL
overhead; items do not add up exactly because the frame time is the sum over a different number of 8-flip/1000-VBL windows).
Item #11 was **not implemented** (section 6). #12 belongs to MW1Cell, #13/#14 are rejected (not pixel-identical), #1 comes after timing.

## 3. Per-item design and proof

### #2 `p4_ck_skip` (site $1dd18, 6 B -> 3 nops)
`sub_01dd14` starts with `jsr $122f0` = per-object anti-tamper byte sum. `$122f0` (listing `$122f0-$12356`): looks `a4` up in the table
`$123ac`, sums `[$12390,$12394)` through `$12276`, hangs (palette loop `$12318`/`$1234c`) on a mismatch or unknown model. Its only side
effects are `$12390/$12394/$12398`, re-initialised by `$1235c` (global sum: `move.l $1239c,$12390 ...`) before use. The covered range
(`$31698-$3DDB4`, antitamper.md) is never written by any patch. Side effect of the patch: the hang on corruption is gone (user-approved).

### #7 `p4_div_a` ($1d0ce), `p4_div_b` ($1d164)
`$1d0a0` (markers, 78 records) and `$1d14a` (4 object slots) each do `move.w $12c5a.l,d7 / divs.w d7,d0 / divs.w d7,d1` (10 bytes). `$12c5a` = `$0200`
(bytes `0200 0008` in the file) and has no store anywhere in `$800-$31698` (6 readers). Port of MW2 `p4_proj_div`, run-time guarded: `d7 == 512` and
`x*128` without overflow (`asl.l #7` V clear <=> x in [-2^24, 2^24-1] so the quotient fits a word), then `(x<0 ? x+511 : x)>>9` as `x<<7`,
`+511<<7` if negative, `swap`. Otherwise the original `divs` with the dividends reloaded from `0(a0)/4(a0)` resp. `6(a0)/10(a0)`. The upper words
(remainders) are dead: next uses are `move.w`, `sub.w`, `cmp.w`, `muls.w` (all low word). The site is `jmp blob` + 2 nops; the blob ends in `jmp` back.

### #8 `p4_roll_00..23` (24 sites, one 24-byte shape)
`$15af0 ... $17050`: the 24 strip loops of the vertex transform each contain `move.w d3,d6 / move.w d4,d7 / muls $17216,d3 / muls $17214,d7 / sub.l d7,d3 /
muls $17214,d6 / muls $17216,d4 / add.l d6,d4 / movem.l d3-d5,(a3)` (verified by script: identical shape at all 24, displacements re-derived per
site). With `$17214 == 0` (`$144ca` init; `$17214` is also written at `$13c2e`, `$144a2`, `$1451c`, `$15992`: that is why the test is dynamic) both products are 0 so
d3 = d3*$17216, d4 = d4*$17216. In place: `tst.w $17214.l / beq.s fast / jmp slow-copy / fast: 2 muls`. d6/d7 are scratch: next reads come
after `clr.w d6` (outcode) or reloads at the loop head; `$16cf6` reloads d7 before every use ($16d18/$16d38/$16d64).
`tst.w` has no PC-relative mode on a 68000, hence the absolute operand.

### #4 `p4_walk_save`, `p4_walk_ret_a`, `p4_walk_ret_b` (`$19f20`, `$1a2c4`, `$1a610`)
The walker body `$19f20-$1a614` touches only d1-d5, a0, a1 (+ccr): d0, d6, d7, a2, a3 do not occur in it (scan of the listing). d1-d5 are dead on return: the
callers reload d0-d5 for the next edge (`$19d8c..$19dc8`/`$19dcc..`, `$19e2a..$19e46`) and both exits (`$1b1bc`, `rts`) read no data register. a0 (shade table) and a1 (ring
table) are live. So only a0-a1 are saved (measured notes had d6/d7 too; they are not needed): -128 cy per edge. `vasm` encodes the
restore as `move.l (a7)+,a0 / move.l (a7)+,a1` (same 4 bytes, 24 cy).

### #3 `p4_walk_pro` ($19ce6) + `p4_walk_test` ($19de4): edge-window test removal, exact by guard
The test `$19ed4` (197 cy/edge) rejects (and drops the **whole polygon** through `$19f1e`, `tst.w $19f1e / bne.w $19e06` at `$19de8`) any edge with an end outside
the window words copied at `$19ce6-$19d0d` from `$12d4a-$12d50`. Proof of redundancy for terrain edges: a vertex referenced by the terrain driver `$19d6a`
has an outcode word `$6(a3,v)` (written by `$15d36 movem.w d3-d6,(a3)` after `$15d0a-$15d32`: bit0 x<`$171f0`, bit1 x>`$171f2`, bit2 y<`$171f4`, bit3 y>`$171f6`; or `clr.w 6(a3,d7)` for a
clipped slot at `$182c4-$182f2`, accepted only when `tst.w d4` (all four bits clear for both ends) after the Cohen-Sutherland loop `$17fa0-$182fa`; window corners
from `$17f20` are the bounds themselves). Outcode 0 therefore means inside `$171f0-$171f6`; `$171f0..` is written only by `sub_0128bc` (callers `$12590/$12658`: mode
set-up, not per frame) as a copy of `$12d4a..`. Run-time guard, per frame (blob at `$19ce6`): `walk_fast` = 0 iff `$12d4a-$12d50 == $171f0-$171f6` (the walker bounds are
copies of `$12d4a..` made right there). Per edge (blob `$B4310`): `walk_fast == 0` and both end vertices (`(a2,d5.w)`, `2(a2,d5.w)` = the offsets the driver itself loaded
at `$19da0/$19dbc`) have outcode 0 -> jump into the walker past the test (`$19f2c`) with the trimmed save; anything else -> the original entry `$19f20` and its `$19f1e` verdict
(`rej` reproduces `bne.w $19e06`). The object driver `$19e08` (list `$1db80`, window `$1cbbe` set at `$1dd9a`) is not touched and keeps the test.
**Empirical check of the proof** (throw-away probe patch, since deleted): the fast path additionally ran the original `jsr $19ed4` and counted disagreement, 60 flips after the
fixed VBL: stand 15163 fast edges / 0 violations, walk 8695 / 0, turn 1060 / 0, busy 16166 / 0; `walk_fast` = 0 in all four.
The `$171f0` constancy between geometry and raster is [INFERENCE] from the single writer; the per-frame equality check covers a change before `$19ce2`.
Dependencies: `p4_walk_pro`, `p4_walk_test`, `p4_walk_save`, `p4_walk_ret_a/b` must be used together (the blob pushes the trimmed frame).

### #10 `p4_drv_edge` ($19d8c, 88 B in place)
The per-edge head of `$19d6a` is rewritten with the same decision (`v2 == nv1 || v2 == nv2` -> end points (v1,v2) else (v2,v1)) using `move.l` pairs (edge record v1,v2 contiguous;
vertex x,y contiguous). Upper words of d1-d4 are dead (walker word ops only: `cmp.w`, `sub.w`, `ext.l d3`, `swap d1 / move.w d5,d1`); d5 stays the edge offset (read by `p4_walk_test`), d0 dead.
The block is shorter than 88 B; the padding sits between the B path's `bra.s` and the A path and is never executed. `$19e08` (objects) is unchanged.

### #9 `p4_fill_save_a` ($1b1bc) / `_b` ($1b27a)
Fill setup saves/restores a0-a6 per polygon (64+68 cy). The fill code `$1aa44-$1b27e` modifies a0 a2 a3 a4 a5 a6 and d0-d7 (a1 does not occur); the only entries are the two
`bne.w $1b1bc` tails of the drivers, whose frames (`$19ce2`, `$1d71c`, and `$1d5a6`, all `movem d0-d7/a0-a6` at entry) use only a0-a3/a6 in their loops. So a4/a5 are dead and only
a0,a2,a3,a6 are saved. Gain is small (0.2 %). The other "fill trims" of render.md (dither mix once per polygon, fused solid passes) were evaluated and **not done**: the mix block is
`$1b0fa-$1b12c` = 280 k of 35.3 M profile cycles (0.8 %) and the second pass needs its own pattern (A1,B1 from `$1b1ba`) so only a cache could remove it; fusing passes would need edits in all 16
solid variants (each hard-codes `addq.l #4,a0` / `lea $140(a2)`); both fall below the noise floor of this gate.

### #5 `p4_pfx_fill` ($15830), `p4_pfx_ymin` ($1b1ce), `p4_pfx_replay` ($1bbe6), `p4_pfx_msg` ($14ed6): clean prefix (port of MW2 `p4_hud_pfx_*`)
State at `$B4800`: `KB[3]` (per draw buffer `(base>>16)-5`: $58000/$68000/$78000) = number of 8-row blocks from the window top (`$171f4` = 51) that already hold the
**final** sky+goggles image; `YMIN` (smallest first row `$1a618` of any filled polygon this frame, recorded at `$1b1ce` for terrain and objects alike; `$7000` = empty never wins);
skip cache `CK/CD7/CA1/CA0`.
* Sky fill `$1580e`: every variant advances exactly one 160-byte row per `dbra` (`$15860/$15884/$158a8`), so a hook at `$15830` (before the fill words are loaded) does `a6 += 160*8*KB; d7 -= 8*KB`
  (all rows skipped -> restore and `rts`). Exact: final rows = sky + terrain + goggles; transparent goggle pixels show sky, the replay re-asserts the opaque ones, and terrain painted
  into skipped rows only overwrites previous sky.
* Replay `$1bbe6` (list `$74000` encoded by `$1bab8`: row-major ascending; masked record 14 B, run record `~off,count,8*(count+1) B`; **runs never cross a row**, `$1bbc0` resets per row, offsets
  relative to the previous record's end): new `KB = max(0,(YMIN-$171f4)>>3)`, replay only records at or below row `top + 8*min(old KB,new KB)` (a skip loop, cached by min+1); the replay is
  idempotent (and/or), so re-replayed rows are harmless. Only used when called from the frame (`$14e72` return on the stack); `$2d6c` and unknown buffers run the original loop.
* Reset: the sky-fill hook sees the frame's return address at `64(a7)`; `!= $14ac4` (first frame `$14a86` after start / map `$14c2c` / S-key mode switch `$14c24`, redraw `$d1de`; the goggles list is re-encoded
  only on those paths: `$1bab8` callers `$d12c,$d8d2,$125be,$12686,$14cb6`) clears all state. There is deliberately **no hook at `$14e00`** (owned by the timing set).
* `$14e98` (message "ENEMY IN RANGE", x=$a0,y=$64: inside the window) draws **after** the replay into the draw buffer, so `p4_pfx_msg` (`$14ed6`) clears KB whenever it draws.
A/B identical on all four snapshots at 8 and 40 flips. [INFERENCE] Not exercised by the gate: the message path and the map/mode-switch re-entry; both are covered by the argument above only.

## 4. Blob / data map (range $B3C00-$B4FFF)
`$B3C00` div_a, `$B3C60` div_b, `$B3D00 + $2C*n` roll_n (to `$B4120`), `$B4200` walk_pro, `$B4300` `walk_fast` word, `$B4310` walk_test, `$B4440` pfx_ymin, `$B4460` pfx_fill,
`$B44E0` pfx_msg, `$B4500` pfx_replay, data `$B4800-$B4813`. (`p4_pfx_fill` declares `; data: $b4800 20`.)

## 5. Sites used (for conflicts with other sets)
`$1dd18`, `$1d0ce`, `$1d164`, 24 roll sites in `$15af0-$17050`, `$19f20`, `$1a2c4`, `$1a610`, `$19ce6`(10 B), `$19d8c`(88 B), `$19de4`(14 B), `$1b1bc`, `$1b27a`, `$1b1ce`, `$15830`, `$1bbe6`(10 B), `$14ed6`.
None is in the timing set's list ($14e00, $13236, $14e14, $14e32, $14e8a, $12a5e). `p4_pfx_*` depends on the frame call order (`$14e20 jsr $1580e`, `$14e6c jsr $1bbe6` returning to `$14e72`) staying as is.

## 6. Item #11 (goggles cull): not implemented
After #5 the clean prefix already removes the sky/replay rows above the terrain. What is left is skipping fill rows/polygons under opaque goggles: render.md: 5.1 % of walk fill rows (37/frame),
2.3 % stand, polygons wholly hidden 0.4/frame walk and 0 stand, i.e. at most ~14 k cy/frame (0.9 %, walk) and 0.5 % stand. A per-row test needs the opaque extent of each row (a table built from the replay list) and
costs ~30-40 cy for each of the ~675 filled rows per frame (>= 20 k cy) -- more than it can save; a polygon-level test saves 0.4 polygon/frame. Not worth the risk.

## 7. Cold boots (HAGA defaults `pp_nofade pp_bigram_cache` + the full set above; `build --only ... --out /tmp/mw1r4/gb`)
`boot_to_game('M')`, then `MWPO` read at `$b2ff8`, left click (walk), 12 s, `gstate`, `fps(500)`, `in_ski`. Raw output:
```
1mb  (STE, TOS 1.62, 1024 kB)
1mb boot_to_game True MWPO b'MWPO'
1mb before {'x': 25600, 'z': 25600, 'speed': 0, 'heading': 0, 'action': 0, 'exit': 0} after walk {'x': 25600, 'z': 28866, 'speed': 48, 'heading': 0, 'action': 0, 'exit': 0}
1mb fps {'vbls': 500, 'flips': 46, 'fps': 4.6, 'vbls_per_frame': 10.869565217391305}
1mb in_ski True
4mb  (Mega STE, TOS 2.06, 4096 kB)
4mb boot_to_game True MWPO b'MWPO'
4mb before {'x': 25600, 'z': 25600, 'speed': 0, 'heading': 0, 'action': 0, 'exit': 0} after walk {'x': 25600, 'z': 29249, 'speed': 45, 'heading': 0, 'action': 0, 'exit': 0}
4mb fps {'vbls': 500, 'flips': 75, 'fps': 7.5, 'vbls_per_frame': 6.666666666666667}
4mb in_ski True
```
(The 4 MB Mega STE run is faster because the 2.06 machine here runs the CPU at 8 MHz with a different cache/ROM timing profile [INFERENCE: not measured]; both walk and keep skiing.)

## 8. Bug: ghost rays of the enemy-impact effect (found by MW1Static) and the fix `p4_pfx_ray`
Cause (disassembly): `$1d710 jsr $20e4e` (sole caller) runs the impact effect: `$20e4e` sets the clip words `$2c376+$26..$2c` to `$171f0-$171f6`, then 64 x `$20f00` -> `jsr $6ed8` (line draw)
draw rays directly into the draw buffer `$12d0a` over the window, after the sky fill. No polygon is involved, so `YMIN` (recorded at `$1b1ce`) never sees them. Unpatched, the next fill of that buffer
erases the rays; with the clean prefix the sky rows were skipped and the rays stayed.
Proof (state-matched, `/tmp/p7s/enemy.sav` = MW1Static's enemy snapshot, 1 MB; `/tmp/mw1r4/ray/cap.py` captures 13 consecutive flips, all three buffers, plus the render inputs
`$12c60..$24` and the object slots; frames of the two runs with byte-identical inputs are compared on rows 51..181 of all 3 buffers):
* base vs `p4_pfx_{ymin,fill,msg,replay}` (no ray fix), flips 28..40: base: 0 differing pixels between the three buffers; patched: `$78000` differs from `$58000`/`$68000` by **783 px** in every capture;
  matched pairs vs base: `$78000` 783 px, `$58000`/`$68000` 0. Flips 2..14 (effect growing, 15-56 ray px per frame, rays present in the base too): patched identical to base in all three buffers, 13 of 13 pairs (the ghost only shows once the effect has ended and a skipped-sky buffer keeps its old rays).
* Unpatched game: same snapshot, flips 28..40, the three buffers are identical (0 px) -> the unpatched game shows no ghost; the patch caused it.
Fix: `p4_pfx_ray` (site `$1d710`, `jsr $20e4e` -> `jsr $b4700`; blob `clr.w YMIN; jmp $20e4e`): YMIN = 0 makes this frame's new KB[b] = 0 and the replay's min(old,new) = 0 (full replay), so the next fill of this buffer is a full fill.
Gate after the fix: flips 28..40 and flips 2..14, all three buffers of every matched pair: **0 differing pixels** (26 of 26 pairs); mw1ab on stand/walk/turn/busy: `--only p4_pfx_ymin p4_pfx_fill p4_pfx_msg p4_pfx_replay p4_pfx_ray` and the combined set + `p4_pfx_ray` are IDENTICAL on all four snapshots at 8 and 40 flips (combined: stand -185833, walk -124897, turn -142181, busy -206361 cycles/frame; the ray path is idle in these scenes, so their numbers equal the earlier combined run).
Other direct writers into the window after the sky fill: only `$117d8` (message, `p4_pfx_msg`) and this effect were found; the remaining `$6ed8` callers (`$d694..$d75a`) are HUD routines [INFERENCE: not traced into the window rows].
Blob map addition: `$B4700` p4_pfx_ray.
