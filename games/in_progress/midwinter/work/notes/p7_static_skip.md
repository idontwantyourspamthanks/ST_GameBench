# P7 item 5(a): static-frame skip for MW1 (`patches/p7_skip_sky`, `patches/p7_skip_render`)

Both patches are `default: no`. Port of the MW2 `p7_skip_*` idea (`games/in_progress/midwinter2/work/notes/p7_static_skip.md`) to MW1's frame loop, triple buffer, partial-B timing and clean-prefix set.
Tooling and raw logs: `work/p7_skip/` (`trace.py`, `rdset.py`, `chan.py`, `outputs.py`, `winw.py`, `mutable.py`, `dumps.py`, `gatew.py`, `match.py`, `verify.py`, `vloop.py`, `ctr.py`, `prof.py`,
`flipcmp.py`, `boot_skip.py`, `mkenemy.py`, `run_gates.sh`, `evidence/*.txt`, `boot/*.log`). Evidence is disassembly (`tools/m68dis.py` on `work/dumps/ram_ski_walk.bin`) or raw output pasted/quoted below;
unobserved statements are marked `[INFERENCE]`. All runs 1 MB STE TOS 1.62 Hatari 2.6.1 unless a machine is named.

## 0. Result

| item | result |
|---|---|
| What is skipped | geometry `$18304`, raster `$19ce2`, goggles replay `$1bbe6`, marker prep `$1d0a0`, and the sky fill `$1580e` (deferred, see 1). HUD, logic, message, flip, p3b sub-passes run as before |
| Rule | a render is dropped when the last three presented frames (triple buffer `$58000/$68000/$78000`) were drawn from identical inputs: generation counter GEN raised on every input change, `GENB[b]` = GEN of the last render into buffer b (section 4) |
| Standing, nothing in the window moving | stand snapshot with the map unit removed: **1668907 -> 320516 cy/frame (-80.8 %)**, 94 -> 488 flips/1000 VBL (4.7 -> 24.4 fps; 25 fps is the p3b 2-VBL sub-pass limit). Window identical at flips 10/40/100 |
| Standing, the stock `stand` snapshot (a map unit walks inside +-8 cells and changes the inputs on 63-86 % of the 5 Hz ticks) | **1794208 -> 710716 cy/frame (-60.4 %)**, 88 -> 220 flips/1000 VBL; window identical at flips 10 and 40; at flip 100 six / one / one window bytes differ (rows 90-91, centre of the view) because the two runs are at different game times [INFERENCE: a distant unit shows there as a few pixels] (section 7a) |
| Moving | skip fires ~0 times: `walk` 0 skips in 500 VBL (66 flips), `turn` 6 / 98 passes (the turn had stopped), `busy` 4 / 58; cost of the hook on a moving pass 7.7 k cy (0.5 % of a walking frame) |
| Self-check of every skip decision (A = buffers at the decision, B = after forcing the render) | **stand 30/30, stand turned towards the unit 40/40, walk 24/24, busy 25/25, turn 25/25, enemy snapshot 10/10, cold boot across an enemy episode 11/11 identical, 0 mismatches**; full 3 x 32000 B compared (section 7) |
| State-matched A/B (patched frame vs base frame with byte-identical inputs, drawn into the same buffer) | stand 34/34, walk 17/17, turn 17/17, busy 26/26, enemy 33/33 identical windows (`evidence/match_*.txt`; an earlier run that also compared pairs across buffers: stand 35/35, walk 19/19, turn 8/8, busy 32/32) (section 7b) |
| Cold boot (default build + p7_skip, marker `MWPO`) standing, skip live / reverted in the same session | 1 MB STE TOS 1.62: 222 / 155 vs 84 / 92 flips per 1000 VBL; 4 MB Mega STE TOS 2.06: 184 / 128 vs 124 / 127 (section 7d) |

Dependencies: **needs the timing set** (`p3b_*` or `tick_head`). Without a frame limiter a skipped frame makes the original per-frame game run faster (the world advances per pass).
`p7_skip_sky` without `p7_skip_render` keeps the original behaviour (ENABLE = 0, see 1); `p7_skip_render` without `p7_skip_sky` never skips.

## 1. Patches, sites, blobs

| patch | site | bytes | blob | role |
|---|---|---|---|---|
| `p7_skip_sky` | `$14e20` `jsr $1580e` | 6 | `$B5800-$B5817` | `ENABLE = 0`: `jmp $1580e` (original, same stack). Else only `PEND = 1; rts`: the sky fill is deferred |
| `p7_skip_render` | `$14e50` `jsr $1d0a0` | 6 | `$B5840-$B5ACF`; data `$B6000-$B683F` | the predicate; renders (sky if `PEND`, then `jmp $1d0a0` with the frame's `$14e56` return pushed back) or skips |

Why the hook sits at `$14e50` and not at the sky call: the skip decision must see the state after the object logic of the frame. `$14e32-$14e4a` (`$202c6 $200e8 $1ffe0 $1fa0a $20d52`, hooked by `p3b_logic` for the sub-passes) write the slot records
the render reads (section 3). The sky fill writes the window of the draw buffer, so it is deferred to the hook: `PEND` is set at `$14e20`, the hook runs `jsr $1580e` itself, after popping its own return address so that the sky
sees the layout `p4_pfx_fill` checks (`cmpi.l #$14ac4,64(a7)`: 15 saved regs + the caller's return + the frame's return = the loop `$14ac4`). The first pass after a (re)apply has ENABLE = 0 (sky in place, no skip), the hook sets ENABLE = 1.
Moving the sky fill is exact because nothing outside the render writes into rows 51-181 of any screen buffer (3.4) and the geometry/marker calls between do not draw.

Skip path (all registers restored): drop the return to `$14e56`; `$14e62`'s store `$1bbe2 := $12d0a`; the raster's first store `$14134 := 0` (`$19d0e`); `jmp $14e72` (the `tst.w $13b40` after the replay). Everything from `$14e72` on (message `$14e8a`, flip `$14e90`) is the original.
Not touched: MW1Timing's sites (`$14e00 $13236 $14e14 $14e32 $14e8a $12a5e`), `$129d2` (contains unit logic), `p4_*`/`p7_cell_*` sites.

## 2. What the render writes that something else reads (outputs)

`outputs.py` over the four traces and the enemy trace: render-written bytes read by non-render code before being rewritten:
```
014134-014135    2 read by nr pc ['0x131ae'] written by render pc ['0x19d0e']
01f0d6-01f0d7    2 read by nr pc ['0x13b8e'] written by render pc ['0x1f0c0']
```
`$14134` is the pick result: `$19d0e move.w #0,$14134` at the raster entry, set non-zero only by `$19e76` (`move.w $14132,$14134`), which `$1b1bc` runs when `$12d3a == 4` (`$12d3a` = 0 in the ski view, `m $12d3a 2` -> `0000`).
The skip stores 0 and refuses to skip while `$12d3a == 4`. `$1f0d6/$1f0d8` (nearest-obstacle flag/distance, `$1f0c0`, consumed by the energy/exit test `$13b8e`) are a function of the objects drawn and keep the value of the last render, which had identical inputs (a skip needs three identical decisions in a row).
`$13b8e` reads them only at the tick (`$13244` chain).

## 3. What the render reads (method and result)

### 3.1 Method
`work/p7_skip/trace.py` restores a snapshot, applies the full default set live at a flip (`mw1patch.py live`, 50 sites + payload), then runs `trace cpu_disasm` over 40 passes of `sub_014e00` (about 6-11 renders: at 8 MHz the frames take more than the 2-VBL sub-pass, the others are `SKIP` passes).
Snapshots: `1mb_ski_{stand,walk,turn,busy}` and an enemy snapshot (`mkenemy.py`: cold boot with Training/Mortars/Bombers OFF, saved when slot `$1ce02` is active). `chan.py` classifies every memory access by phase
(render = `$1580e`/`$1d0a0`/`$18304`/`$19ce2`/`$1bbe6` up to the next frame address; interrupt code = entered at the vectors, ended by `rte`; everything else = non-render) and prints
rbw = bytes the render reads before writing them in the pass, channels = rbw bytes some non-render code or interrupt writes, carried = bytes an earlier render wrote and a later one reads first. `winw.py`: non-render writes into the three screen buffers.
`dumps.py` + `mutable.py`: rbw bytes that differ between the four snapshot dumps.

**Parser trap (cost me an hour):** MW2's `rdset.py` header regex `\s{2,}` silently drops every 10-byte instruction (`move.w abs.l,abs.l`, `move.l abs.l,abs.l`: 5 opcode words leave one blank only). With it the stand trace had 134 k instructions, with the fix (`\s+`, `work/p7_skip/rdset.py`) 823 k, and half of the channels were missing.
Also `movem.l regs,-(An)` prints the address of the FIRST transfer (the highest long), so the written block is `[EA-(n-1)*4, EA+4)`, fixed in `rdset.py`.

### 3.2 Channels (stand+walk+turn+busy: 156 passes, 31 renders, 18022 rbw bytes, 8117 non-render written bytes; `evidence/chan_4scenes.txt`)
```
012c60-012c6b    12 w 0x14562 0x14568 0x159be 0x159c4 0xb3230   r 0x1d0e4 0x1d4ba ...   X, Z longs, cells $12c68/$12c6a
012c72-012c83    18 w 0x15a3a-0x15a8a                           r 0x16da2 ...           view origin/offsets of the vertex transform
012c98-012c99     2 w 0xb3224 0xb3318 0xb3862                   r 0x17112               heading
012d0a-012d0d     4 w 0xbdde                                    r 0x15812               draw buffer (the index b, not compared)
0159a0-0159a3     4 w 0x15976 0x1597c                           r 0x1d568               roll terms
0171f8-017217    32 w 0x1309e 0x144ca 0x15922 ...               r 0x16dfe 0x16e10 ...   view vectors, tilt ($17210/12), roll/focal ($17214/16)
01721c-01721d     2 w 0x14722                                   r 0x16df8               camera height
01bbe2-01bbe5     4 w 0x14e62                                   r 0xb4504               replay buffer pointer (re-stored by the skip)
01cdb0-01cdb7     8 w 0x1f848 0x1f84c                           r 0x1d15c 0x1d160       slot 1 position
01cdc2-01cdc5     4 w 0x1f7c6 ...                               r 0x1d67c 0x1d682       slot 1 heading terms
01d816-01d81b     6 w 0x1d7ba ...                               r 0x1deb6               light vector from the heading (`$1d77a`)
carried: $12d4a-51 (the object draw rewrites the window words with the same values, `$1dd9a`), $18bda (painter list pointer, reset by the render), $60cb2-$60d93 (see 9.6), p4 state $b4800-$b4813.
```
Enemy trace (`evidence/chan_enemy.txt`) adds slot 3 `$1ce08-0f` (position), `$1ce1a-1d` (heading terms), `$1ce26` (+$24), all inside the slot fields compared (3.3).

### 3.3 The rest of the read set (`evidence/mutable.txt`: 106 rbw bytes differ between the four snapshots)
12.6-18 k rbw bytes, almost all constants: model data `$352d0-$3a7a9` (the anti-tamper sum range `$31698-$3ddb4`), terrain heights `$44404-$46805` (read through the pointer at `$12ce2`; [INFERENCE] rebuilt only at a window recentre `$152c0`: `$1cf1c` and the height flattening `$1d1d2` are called together from `$14994/$149a0`, `$14cd8/$14ce4`, `$153ac/$153b8` only, and position and `$19cd4` change at a recentre),
strip/sector tables `$17140-$17330`, mask/shade tables `$1a944-$1b97c`, sin/cos `$1c6bc`. The 106 mutable bytes are: the channels above, `$18bdc` (painter pointer), slot 1 model pointer `$1cdae`, the p4 vertex-pool words `$60cb2-$60d93` (9.6) and `$1bbe3`. Nothing mutable is outside the signature except render scratch.
`$1cd64/$1cd66` (`addi.w #4,$1cd64` / `subi.w #4` at `$1cc8e..$1ccbe`: object rotation offsets, read at `$1d614`) never changed in a trace but have writers, so they are compared. `$12d54` (sky pattern selector, `tst.w $12d54` at `$15850`) has no absolute-address writer (`m68dis --xref 12d54`), it is compared anyway (2 bytes).
The marker table `$70010` (78 x 16 B, read 640 of 1240 bytes by `$1d0a0` (position, window test) and `$1d5be` (position, model pointer `+8`, `+$c`)) is written only by `$1cf1c` (build at re-entry/recentre: callers `$14994 $14cd8 $153ac`) - not by any non-render code in the traces (`nrW = 0`), but compared whole because a mission event could rewrite a record.
The goggles list `$74000` (8194 B, replay) is re-encoded only by `$1bab8` (callers `$d12c $d8d2 $125be $12686 $14cb6`); per the `p4_pfx_fill` header these are the start / map / S-key re-entries, which go through the first-frame call of the body (`$14a86`, frame return `$14a8a`, not the loop's `$14ac4`): the hook clears every `GENB` there. The list pointer `$1bbde` is also in the signature. [INFERENCE: a re-encode outside those paths would not be noticed.]

### 3.4 Writers into the window outside the render (`evidence/winw*.txt`)
No non-render write into rows 51-181 of any screen buffer in the four traces nor in the enemy trace (non-render writes: rows 1-50 HUD panel at `$97e2`-`$a56x`, rows 14-20/1-30 gauges). Render writes: rows 51..181, bytes 8..151 (the p4 clean prefix starts them at row 67-107).
The only other writer is the HUD message `$14e98` (`ENEMY IN RANGE` at x=$a0,y=$64, inside the window, drawn after the replay while `$14ee4 >= 0`). `$14ee4` has no writer besides the decrement (`m68dis --xref 14ee4`), so the path was never reached; the hook refuses to skip while `$14ee4 >= 0`.
The `$20e4e` effect (enemy impact: rays through `$6ed8`, PRNG `$d598` per ray) is drawn by the render itself (object draw of a slot with `$26 = 0`, `$1d710`); a skip would also drop its PRNG draws, so such a slot inside the window always renders (4.2).

## 4. The predicate (`p7_skip_render.s`)

### 4.1 Signature (staged to `D+$140`, 248 bytes, compared with `cmpm.l` against `LAST`)
| bytes | content | evidence |
|---|---|---|
| `$12c60-$12c83` (36) | position, cells, in-cell offsets, view origin | channels |
| `$12c98`, `$157a8`, `$159a0` L | heading, `$157a8` (read at `$196f0`, writer `$157a0`), roll terms | channels / xref |
| `$171f0-$1721d` (46) | window `$171f0-f6`, view vectors, tilt `$17210/12`, roll/focal `$17214/16`, centre `$17218/1a`, camera height `$1721c` | channels |
| `$19cd4` L | map window origin (changes at a recentre) | xref `$152c0` |
| `$1d418`, `$1d816-b`, `$1cd64` L, `$12d54`, `$1bbde` L | marker count - 1, light vector, object offsets, sky selector, goggles list pointer | 3.3 |
| 4 x 17 words | object slots `$1cd7e + n*$2c` (`$1d14a` loops them): `$8000` if `$26 < 0` (inactive: `$1d154 bmi`), `$7ffe` if outside +-4700 units of the player (superset of the marker pass's +-8 cells of `$200`), else `$7fff` + `+0, +2L, +6L, +$a L, +$e, +$10, +$12, +$14, +$16, +$18, +$1a, +$24, +$26` (every field `$1d65c-$1d68a` and `$1d6ac` read, from the busy/enemy traces) | disassembly + traces |
| marker records | `$70010`, `$1d418+1` records of 16 B (<= 96): `cmpm.l` against `MKLAST` when the signature is unchanged, `move.l` copy when it changed | 3.3 |

The render writes none of the signature bytes: `sigcheck.py` over the four traces and the enemy trace prints `traces 5 render writes into signature bytes: {}` (`evidence/sigcheck.txt`).

### 4.2 Flow
1. `GENB[b]`: b = bit 16 of `$12d0a` minus 5; not 0..2 -> render, no state.
2. frame return `64(a7) != $14ac4` (first frame `$14a86`, `$d1de`) -> clear all `GENB`, render. `PEND = 0` (sky already ran), `$12d5e != $131ae` (snipe/buggy/glider: other overlays, never traced), `$14ee4 >= 0`, `$12d3a == 4`, `$13b40 == 0` (no flip this pass) -> `GENB[b] := 0`, render.
3. Stage the signature; unsupported content (slot with `$26 = 0` inside +-4700: effect path; more than 96 markers) -> `GENB[b] := 0`, render.
4. Signature differs from `LAST` (copy it) or the marker table differs from `MKLAST` (copy it): `GEN++` (0 is skipped: "no render yet").
5. `GENB[b] == GEN` -> **skip**. Else `GENB[b] := GEN`, render (sky if `PEND`, then `jmp $1d0a0`).
After any change both other buffers need one render each before the first skip: exactly "the last three presented frames came from identical inputs". A frame rendered with an unsupported content invalidates only its own buffer (the pictures in the others are still valid for the same inputs).

### 4.3 Consistency with p4_pfx_* and p3b / p7_cell / p5
* `p4_pfx_*` state is per draw buffer (`KB[3]`, `CK/CD7/CA1/CA0` skip cache) or per render (`YMIN`). A skip leaves buffer b and its `KB[b]` untouched: the picture is the sky + terrain + goggles of identical inputs, so the clean-prefix assumption "rows above `YMIN` hold sky + goggles" holds exactly as after a real render. The reset (`64(a7) != $14ac4`) is reached only by renders through the hook with the same stack layout as the original.
  `carried` shows only `$b4800-$b4813`, `$12d4a-51`, `$18bda`, `$60cb2-$60d93` (9.6) and, with the enemy, the object-draw pointers between renders; none is touched by a skip. A forced render after a run of skips gives A == B (7b, C).
* p3b: the hook is inside the loop body, so sub-passes (`NOLOGIC`), `PH 5`/A passes and their logic run exactly as before; the interpolated heading/position/tilt of a sub-step are signature bytes (a turn of 1-4 units/tick only changes the view at `PH 5`, the other four passes skip; measured: turn 6 skips in 98 passes only because that snapshot's turn had stopped).
* `p7_cell_*` hooks sit inside `$18304`/`$17444`, not reached on a skip. `p5_ctl_*` unaffected (input side).

## 5. Counters (`D = $B6000`, for the gates)
`ENABLE.w +0 PEND.w +2 GEN.w +4 GENB.w[3] +6 RET.l +12 NSKIP.l +16 NREND +20 NCHG +24 NMK +28 NFORCE +32 NINV +36 NUNS +40`; `LAST +$40`, `STG +$140`, `MKLAST +$240`. `m $b6000 64`.

## 6. Cost
`prof.py` (Hatari `profile`, 300 VBL after settling, units removed): a skipped pass runs the hook for **9566 cy** (stage + compare ~2 k, marker compare `cmpm` x 312 ~7.6 k [INFERENCE from the instruction count: 312 x 20 cy + loop]); the whole profile is 43.37 M cycles over 196 passes, 37.70 M of them in `$b3000-$b3fff` (the p3b spin on `$637e`), i.e. 28.9 k busy cycles per skipped pass (largest other pages: `$19000` 1.38 M, `$6000` 0.68 M, `$15000` 0.58 M, `$b000` 0.29 M, `$14000` 0.22 M).
A moving pass: hook 7723 cy (stage + copy of the 248 B signature + the marker copy; walk, 37 passes), 0.5-0.6 % of a 1.4 M cycle frame, no skip.
The marker compare is the biggest part; a cheaper exact scheme needs a writer-side epoch (`$1cf1c` callers), i.e. patches outside the render calls.

## 7. Gates (raw output in `work/p7_skip/evidence/`)

### 7.0 Why plain `mw1ab` equality at equal flip counts is the wrong gate here
With `p3b_*` the frame sequence follows the VBL counter, and the patch makes frames faster or slower. Two runs at the same flip count are at different times, so anything that moves (HUD clock, a walking unit, the player) differs legitimately.
`mw1ab` as is (apply at +300 VBL, whole 32000 B; `evidence/mw1ab_default_gate.txt`):
```
stand --flips 10: IDENTICAL; flips/1000VBL 88 -> 220; cycles/frame 1794208 -> 710716 (-1083492, -60.39 %)
stand --flips 40: IDENTICAL
stand --flips 100: DIFFER {'b58': 41, 'b68': 40, 'b78': 45}      <- HUD clock rows 14-20 / 195-197, plus 6/1/1 bytes in the window rows 90-91 (a distant unit)
walk --flips 8: DIFFER {'b58': 432, 'b68': 0, 'b78': 0}; flips/1000VBL 199 -> 446; cycles/frame 788407 -> 350433 (-55.55 %)
walk --flips 40: IDENTICAL
turn --flips 8: IDENTICAL; flips/1000VBL 202 -> 331; cycles/frame 775058 -> 473672 (-38.89 %)
turn --flips 40: IDENTICAL
busy --flips 8: IDENTICAL; flips/1000VBL 83 -> 299; cycles/frame 1902666 -> 523857 (-72.47 %)
busy --flips 40: IDENTICAL
```
So I report three kinds of evidence: (A) `gatew.py` = the same captures with the 3D window (rows 51..181) separated from the HUD, state words captured too, optional pokes at the apply and at the K-th flip; (B) `match.py` state-matched A/B; (C) `verify.py` self-check inside one run.

### 7a. Standing (A: `gatew.py`, base = default set, patched = + p7_skip, applied live at +300 VBL)
Units frozen too (`w $2baec $ff $ff` stops `$c4f2/$ca7e`; `w $1cdd0 $ff $ff` removes the slot-1 unit; both runs; `evidence/gatew_stand_noUnit.txt`):
```
stand --flips 10: window IDENTICAL; flips/1000VBL 94 -> 488; cycles/frame 1668907 -> 320516 (-80.8 %)
stand --flips 40: window IDENTICAL
stand --flips 100: window IDENTICAL; (HUD differing: rows 14-20 = the clock digits, the two runs are at different game times)
WINDOW ALL IDENTICAL
```
Stop-and-go (`evidence/gatew_stopgo.txt`: same pokes, view turned to heading `$100` at flip 25 and back at flip 60 in both runs, capture at flip 100): window IDENTICAL (every skip -> render -> skip transition of all three buffers and their `KB` prefixes).
The stock snapshot (unit walking). The first `gatew_a.txt` block was run with only `$2baec` frozen (the slot-1 unit is still moved by its own handler `$20ce2`): `flips/1000VBL 78 -> 78`, 0 %, the signature changed on every tick of that window. `ctr.py stand` over 1000 VBL (unit walking, nothing poked): `NCHG 69, NSKIP 163, NREND 73`, 223 flips.
The 6/1/1 window bytes of the unfrozen flip-100 run are at rows 90-91, cols 73-79 (centre of the view) [INFERENCE: a distant unit visible as a few pixels]; its position depends on the time of flip 100 (patched run ~450 VBL, base ~1140 VBL). With the units removed, flip 100 is identical (above).

### 7b. Walk, turn, busy
(A) applied right after the restore, i.e. the moving phase (`gatew.py --soon`, `evidence/gatew_a.txt` second block):
```
walk --flips 8: window IDENTICAL ... cycles/frame 1231828 -> 965506 (-21.6 %)   walk --flips 40: window IDENTICAL
turn --flips 8: window DIFFER {'b78': 188} ... (see below)                       turn --flips 40: window IDENTICAL
busy --flips 8: window IDENTICAL ... cycles/frame 1905629 -> 687149 (-63.9 %)    busy --flips 40: window IDENTICAL
```
`turn --flips 8` b78: `flipcmp.py` (`evidence/flipcmp_turn.txt`) shows the captured state words equal at flip 8 but **the inputs of flip 7 differ** between the runs (patched and base are one sub-pass apart there) and b78 holds the flip-7 picture. Controls: base vs defaults + `p7_skip_render` only (hook never skips, sky in place) is IDENTICAL; with both patches but the skip made impossible (nop over the `beq .skip`) it still differs by the same 188 B, i.e. the difference comes from the 3-4 k cycles of the staging shifting a pass across a VBL boundary, not from skipping. State-matched (B) below removes the timing.
Skip count while moving (`ctr.py`, applied right after the restore, 500 VBL): `walk` NSKIP 0 (66 flips, NREND 86, NCHG 70), `turn` NSKIP 6 (NREND 92, NCHG 64), `busy` NSKIP 4 (NREND 54, NCHG 52).

(B) `match.py` (restore, apply, capture 13 consecutive flips per batch in each run, 3 batches; frames with byte-identical inputs (`$12c60-83 $12c98 $157a8 $159a0 $171f0.. $19cd4 $1d418 $1d816 $1cd64 $12d54` + the slots) drawn into the same buffer must have identical window rows 51..181):
```
stand  : pairs with identical inputs and the same buffer 34, window identical 34, DIFFER 0 (cross-buffer pairs set aside: 1)
walk   : 17 / 17 / 0 (2 set aside)        turn: 17 / 17 / 0 (7)        busy: 26 / 26 / 0 (6)
enemy  : 33 / 33 / 0 (2 set aside; these two differ, see 9.2)
```
(`evidence/match_*.txt`; in these scenes the inputs of nearly all 13 captured frames of a run are distinct (`base inputs distinct 13/13, patched 13/13` in stand/walk/busy/enemy), so the pairs are moving frames. Cross-buffer pairs (same inputs, different draw buffer) are only comparable while no buffer carries a ghost of the `$20e4e` rays (9.2); the first run of this gate compared them as well and had no difference in the four scenes without the enemy.)

(C) `verify.py` (one run: breakpoint at the hook's `.skip` label; at the decision save the three buffers (A), `r pc = .render` (the render the hook would have skipped runs), save them again at `$14e72` (B)):
```
stand 30/30, stand + view turned to heading $ba (towards the unit) 40/40, walk 24/24, busy 25/25, turn 25/25, enemy snapshot 10/10: identical (all 3 x 32000 B), 0 MISMATCH
e.g. check 20: buffer $68000 A vs B differing bytes {'58': 0, '68': 0, '78': 0} OK {'GEN': 379, 'NSKIP': 225, 'NREND': 395}
```
(`evidence/verify_*.txt`). A and B differ in nothing, in particular not in the HUD rows and not in the prefix rows.

### 7c. Something moves while the player stands
* **Map unit in the window**: the stock `stand` and `busy` snapshots. Slot 1 (`$1cdaa`, the first unit inside +-8 cells, `$ca7e`) moves 32 units per captured flip (`$a(a1)` `$69e6 -> $6a06 -> $6a26 ...`, the stand capture of `match.py`); the signature changes on 63-86 of 100 ticks, `NSKIP`/`NREND` follow: stand 1000 VBL: skip 163 / render 73 (-60 % cycles). When the unit leaves the window (`lastdiff.py`: the staged slot-1 words go `7ffe` then `8000`, the differing offsets in `LAST` drop from 4 to 0) the signature stops changing; with the unit and the unit simulation removed by poke the skip fires on nearly every pass (488 flips/1000 VBL, -80.8 %). The matched A/B and the self-check include these frames.
* **Enemy object** (Training OFF, slot `$1ce02`, handler `$20594`): cold boot with `boot_to_game('M', training=False, mortars=False, bombers=False)`, standing (`boot/spawn1mb_sample.log`):
```
sample   0: slot3 flag 1 pos (27187,28086) dist (1587,2486) counter deltas since the last sample {'NSKIP': 0, 'NREND': 18, 'NCHG': 18, 'NUNS': 0}
sample  14: slot3 flag 1 pos (23811,23310) dist (-1789,-2290) ... {'NSKIP': 192, 'NREND': 104, 'NCHG': 101, 'NUNS': 1}      (the 192 skips are the quiet stretch before this approach)
sample  15: slot3 flag 1 pos (25924,26916) dist (324,1316)   ... {'NSKIP': 0, 'NREND': 24, 'NCHG': 25, 'NUNS': 1}
sample  16: slot3 flag 1 pos (23935,22282) dist (-1665,-3318) ... {'NSKIP': 0, 'NREND': 27, 'NCHG': 27, 'NUNS': 0}
sample  17: slot3 flag 1 pos (25397,26512) dist (-203,912)   ... {'NSKIP': 0, 'NREND': 26, 'NCHG': 26, 'NUNS': 0}
sample  18: slot3 flag 0 pos (25591,25697) dist (-9,97)      ... {'NSKIP': 0, 'NREND': 0, 'NCHG': 0, 'NUNS': 0} act 1   (the impact: action mode over)
```
  While the enemy is active every tick changes the signature and renders (NSKIP 0, NREND ~ NCHG); the screenshots `boot/spawn1mb_enemy_{000,015,018}.png` show the attack rays animating in the window (015: rays above the horizon while approaching, 000/018: impact). With the enemy active inside +-4700 units and `$26 = 0` (impact effect) `NUNS` counts the forced renders (the `$20e4e` path draws with the PRNG, so it must run every frame).
  Self-check across an enemy episode (cold boot, `boot_skip.py --spawn --verify`, `boot/spawn1mb_verify.log`): `self-check: 11 identical, 0 MISMATCH` (checks run at the skip decisions of the episode; GEN 132 -> 133 between check 0 and 10 shows the enemy was already gone for most of them, so only the first checks can have had it active [INFERENCE]); enemy snapshot: verify 10/10 (`verify_enemy.txt`), matched A/B 33/33, `chan_enemy.txt` shows slot 3's fields as channels.

### 7d. Cold boot, default build + p7_skip (`mw1patch.py build --only <pp_* + defaults + p7_skip_*> --out build/p7skip/game`; `boot_skip.py`, `boot/ste1mb.log`, `boot/mste4mb.log`)
Marker `MWPO`, `$14e20 4eb9000b5800`, `$14e50 4eb9000b5840`. Skip live vs the two sites restored to their original bytes at a flip (state zeroed on re-apply), same session. `meas` = flips per 1000 VBL (500 for walk/turn):
```
1 MB STE TOS 1.62 (boot 112 s)
  standing   skip live 222 (11.10 fps) {'NSKIP': 166, 'NREND': 67}   reverted 84 (4.20 fps)
  standing   skip live 155 ( 7.75 fps) {'NSKIP': 77,  'NREND': 90}   reverted 92 (4.60 fps)
  walk       skip live  50 (5.0 fps, NSKIP 0)  reverted 69 (6.9 fps)   <- different part of the descent (z 29559 vs 31034), not comparable
  turn       skip live  41 (4.1 fps, NSKIP 0)  reverted 42 (4.2 fps)
4 MB Mega STE TOS 2.06 (boot 103 s)
  standing   skip live 184 (9.20 fps) {'NSKIP': 161, 'NREND': 89}    reverted 124 (6.20 fps)
  standing   skip live 128 (6.40 fps) {'NSKIP': 13,  'NREND': 143}   reverted 127 (6.35 fps)   <- the unit changed the inputs on 111 of ~125 ticks in this window
  walk       skip live  70 (7.0 fps, NSKIP 0)  reverted 102 (10.2 fps)  <- not comparable (z 29975 vs 31034)
  turn       skip live  59 (5.9 fps, NSKIP 0)  reverted  54 (5.4 fps)
```
Walking and turning never skip (NSKIP 0 in every window, also after stopping while the unit walks: `after stopping ... counter delta NSKIP 0, NREND 59`). The walk windows lie at different positions of the same descent, so the fps columns are not a patch effect; the per-pass overhead is section 6. Cold boot with the enemy: `boot/spawn1mb_sample.log`, `boot/spawn1mb_verify.log`.
Both 1 MB and 4 MB boots reach the 3D view, `MWPO`, walk and turn work. (The first 4 MB attempt, started at the same time as the 1 MB boot, failed in `boot_to_game` on a missed Options click - the known harness flakiness; run one boot at a time.)

## 8. Reproduce
```
D=$(python3 tools/mw1patch.py list | awk '$2=="yes" && $1!~/^(floppy|pp_)/ {print $1}')
python3 tools/mw1patch.py live --only $D --out /tmp/p7s/base ; python3 tools/mw1patch.py live --only $D p7_skip_sky p7_skip_render --out /tmp/p7s/sk
python3 tools/mw1patch.py build --only pp_nofade pp_bigram_cache $D p7_skip_sky p7_skip_render --out build/p7skip/game
python3 work/p7_skip/trace.py work/snapshots/1mb_ski_stand.sav /tmp/p7s/t_stand.txt 40 --skipn 20 --live /tmp/p7s/base     # then chan.py / outputs.py / winw.py / dumps.py + mutable.py
python3 work/p7_skip/gatew.py --only $D p7_skip_sky p7_skip_render --base $D --snapshot stand --flips 10 40 100 [--poke 'w $2baec $ff $ff;w $1cdd0 $ff $ff'] [--soon] [--poke-at 'K:cmd;cmd']
python3 work/p7_skip/match.py walk /tmp/p7s/base /tmp/p7s/sk --batches 3 ; python3 work/p7_skip/verify.py stand /tmp/p7s/sk 30
python3 work/p7_skip/boot_skip.py ste1mb ste 1.62 1024 games/in_progress/midwinter/build/p7skip/game ; ... mste4mb megaste 2.06 4096 ... ; ... spawn1mb ste 1.62 1024 ... --spawn [--verify]
work/p7_skip/run_gates.sh
```

## 9. Known gaps and findings

1. **A map unit (or the enemy) inside +-4700 units changes the signature even when it is out of the view.** The stock `stand` snapshot is that case (slot 1 is drawn every frame: `$1d65c` ran once per render in the stand trace, but nothing of it is visible in the screenshot `shot_stand`). Upper bound with the unit removed: -80.8 % instead of -60.4 %. An exact visibility test needs the object's extent: models are edge-vector models (`$1e026`: vertices are sums of three scaled axis vectors, `$20f88` basis), so a radius bound is a model-format study I did not do. [INFERENCE: the unit is outside the view cone (it stood 3325 right and 1510 ahead of a player looking along +Z at the snapshot) and its polygons are dropped by the window test; with a visibility test the stand snapshot would skip ~every pass.]
2. **p4_pfx leaves ghost rays in the sky after the enemy impact effect** (not caused by this patch, found with it): the `$20e4e` rays are drawn by the render into rows above the terrain top (the clean prefix), `KB[b]` is not cleared for them (only `p4_pfx_msg` clears it for the message), so the next renders into that buffer do not refill the sky [INFERENCE for the mechanism]. In the enemy snapshot run buffer `$58000` differs from `$68000` and `$78000` by 378 pixels (the rays) in the **base** run and the patched run alike (`evidence/ghost_rays.txt`, picture `evidence/ghost_rays_base33_vs_patched32.png`), and the matched A/B pairs with identical inputs but different drawn buffers differ by 783 bytes (`enemy: base flip 33 (0x78000) / patched flip 32 (0x58000)`), which is why `match.py` only compares frames drawn into the same buffer. `p4_pfx_*` is outside my assignment: it needs the `$20e4e` effect to clear `KB`/`CK` like `p4_pfx_msg` does.
3. Only the ski/walk mode step `$131ae` skips. Snipe (`$13f36`), buggy (`$1359a`), glider (`$1373c`) render as before; not traced.
4. Coverage: 5 scenes (stand, walk, turn, busy, enemy), 40 passes each. Constants (models, terrain window, tables) are assumed constant because no non-render write was seen; a writer that never ran (terrain damage, a mission script rewriting a model) is missed. The heights `$44404..` and markers are compared only through the signature/marker copy and `$19cd4`.
5. The `ENEMY IN RANGE` message path was never reached (no writer of `$14ee4`); the hook refuses to skip while it is armed.
6. `$60cb2-$60d93` (p4_walk_test vertex-outcode words): 38 bytes the render reads that this render did not write (stale words of the previous frame, `carried`). They only choose between two exact walker paths per p4's argument [INFERENCE: not re-proved]; a skip leaves them as the last render left them.
7. Floppy build not run; sites are resident, blob range `$B5800-$B6FFF` is zero at staging.
8. Mid-frame snapshot restore: the hook assumes the frame body is entered from `$14e00`; a snapshot taken inside the render and restored (not done) would see `PEND`/`ENABLE` from the saved state.
