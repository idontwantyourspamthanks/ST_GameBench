# STE blitter for sky fill and span interiors (patches/p4_blit_sky.s, p4_blit_hist.s)

Result in one line: **the blitter gives no measurable gain on an 8 MHz STE.** The sky fill is pixel-identical
and saves 5.5 % of the fill (0.15 % of a frame); non-HOG is twice as slow as the CPU; span interiors are too
narrow (max 4-6 groups) for any interior fill, CPU or blitter, to matter (upper bound 0.5 % of a frame).
`p4_blit_sky` stays `default: no`.

All numbers: Hatari 2.6.1, 1 MB STE, TOS 1.62, snapshots `1mb_ingame_foot`/`1mb_ingame_walking`.
Hatari's blitter model (src/blitter.c: `BLITTER_CYCLES_PER_BUS_READ/WRITE 4`, non-HOG = 64 blitter bus
accesses then 64 CPU bus accesses) is the same 4 cycles per 16-bit bus access as the 68000.

## 1. Runtime detection (in the blob, first call, result cached in FLAG `$b4bfe`: 0 unprobed, 1 blitter, 2 CPU)

`$4f2` (_sysbase), `$42e` (phystop) and `$5a0` (cookie jar) are overwritten in-game by PP's patcher block
(`$200-$5E7`; `$5a0` reads `01450809`, `$42e` reads `5188 20fc`), so TOS/cookie queries are impossible.
HAGA's own result (`$F8083` = 2 for STE in the 1 MB snapshot, set by the code at `$1f8100+` in the 2 MB dump)
moves with RAM size. The patch therefore repeats HAGA's idiom (bus-error trap on `$ff8e21`) itself:
1. 68000 test: `lea (0,a0,d0.w*2),a1` (`dc.w $43f0,$0200`); the 68000 ignores the scale bits, a1 = 1.
   Else CPU path (TT, Falcon: 68030).
2. `tst.b $ffff8a3c` under a bus-error trap (vector `$8` swapped, handler does `movea.l a6,a7`): fault = no
   blitter, CPU path.
3. `tst.b $ffff8e21` under the trap: readable = Mega STE (16 MHz CPU beats the 8 MHz blitter; cache
   coherence unknown), CPU path. Fault = plain STE, blitter path.
The game runs in supervisor mode at this point (snapshot `r`: `SR=2304 S=1`).

Evidence (cold boots of `build/blit_cold`, 1 MB, all default patches + p4_blit_sky): see section 5.

## 2. Sky fill `$1b996` (22,720 B/frame = lines 58-199)

Per 160-byte line: bytes 0-7 `7fff7fff 7fff7fff`, bytes 8-159 `$ff` (clears_blits.md). Blitter version:
- pass A = words 4..79 of every line (76 w x 142 lines, dst x-inc 2, y-inc 10, HOP 0, OP 15 = all ones),
- pass B = words 0..3 (4 w x 142, y-inc 154, HOP 1 halftone `$7fff` x16, OP 3).
The entry becomes `jmp $b4700`; the blob replays the displaced `movem.l d0-d7/a0-a6,-(a7)` + first word of
`movea.l $67a6.w,a6`, and on the CPU path jumps back into the original body at `$1b99e`.

Pixel gate (`abtest --only p4_blit_sky`, final patch):
```
1mb_ingame_walking: pixels IDENTICAL; fps base 3.1 (63 flips) -> patched 3.1 (63 flips)
1mb_ingame_foot: pixels IDENTICAL; fps base 4.2 (85 flips) -> patched 4.2 (85 flips)
```
(non-HOG variant `HOG equ 0`: walking IDENTICAL 63 -> 64 flips, foot IDENTICAL 84 -> 82 flips.)

Cycles per call (Hatari `profile cycles`, `1mb_ingame_foot`, 10 calls, `movem` at `$1b9c8` = 73,896 =
10 x 71 x 104):

| Variant | cycles per call |
|---|---:|
| original CPU (`$1b996-$1ba02`) | 53,815 |
| blitter, HOG (`$80+$40` ctrl) | 50,873 (-2,942 = -5.5 %; pass A 47.5 k = 4.40 c/word, pass B 2.5 k = 4.45 c/word) |
| blitter, non-HOG, poll BUSY between passes | 97,150 (+80 %: the CPU spins in its 64-access slices and the blitter only runs in its own) |

Frame rate over 3000 VBL (`1mb_ingame_foot`), flips: original 253, HOG 254, non-HOG-no-wait with pass B on the
CPU (unsafe measurement-only variant that returns without polling, pixels not gated) 254. Even full overlap
gives nothing, as the bus-bound model predicts: elapsed = blitter bus time + CPU work. 2,942 cycles of a
~1.92 M-cycle frame (12 VBL) is 0.15 %, below the 1-flip resolution (0.4 %) of a 3000 VBL window.

Why the blitter cannot win a pure fill: 4 cycles per word on the blitter vs `movem.l` 12 regs = 104 cycles
/ 24 words = 4.33 cycles per word on the 68000. Only loops with instruction overhead per word lose.

Hazard of HOG [INFERENCE, not measured]: the CPU is stalled for ~47 k cycles (5.9 ms, ~93 raster lines); VBL,
Timer B (`$263de` palette splits) and IKBD ACIA (1 byte / 1.28 ms) interrupts are delayed up to that long.
The framebuffer gate cannot see palette-split or keyboard-overrun effects. Non-HOG avoids this but doubles the
cost, so there is no good setting.

## 3. Span interiors (`$38cd0` variants): not implemented, upper bound measured

`patches/p4_blit_hist.s` (measurement only, hooks `$38d14`, `jmp (a2)` dispatch) histograms, per scanline row
of every fill call, the number of interior 16-px groups `g = (offR - offL)/8 - 1` (the `move.l a3/a4,(a2)+`
loop, 38 cycles per group: 12 + 12 + 4 + 10). 600 VBL each:

| Snapshot | flips | calls/frame | rows/frame | rows with g=0 / 1 / 2 / 3 / 4 / 5 / 6 | interior groups/frame |
|---|---:|---:|---:|---|---:|
| `1mb_ingame_foot` | 48 | 81 | 1006 | 19266 / 7125 / 1083 / 0 / 0 / 0 / 0 | 194 |
| `1mb_ingame_walking` | 61 | 75 | 655 | 14664 / 8089 / 1773 / 125 / 4 / 0 / 0 | 197 |
| `ingame_foot_banked_turn` (2 MB) | 41 | 74 | 1436 | 22722 / 5599 / 1547 / 423 / 79 / 19 / 6 | 254 |

(`single/crossed` rows: 20805 / 15275 / 28482, i.e. the other half of all rows are one group or empty.)

The terrain polygons are small; the widest interior in any scene is 6 groups (96 px), and 98 % of rows have
at most 1 interior group (incl. single-group/empty rows). All interiors together cost 194-254 groups x 38 = 7-10 k cycles = 0.4-0.5 % of a frame,
so even a free interior fill could gain at most that. A per-row blit costs ~60 cycles of register writes
(`move.l a2,$32(a0)` 16 + `move.w d,$38(a0)` 12 + `move.b d,$3c(a0)` 12 + pointer/branch work; [INFERENCE]
from the 68000 timing table, not run) + 4.4 cycles/word = ~18 per group, vs 38 per group on the CPU: the
break-even is g = 3. Rows with g >= 3: foot 0, walking 2/frame, banked turn 13/frame; summed saving
~0-150 cycles/frame (< 0.01 %). Per-site patching of the ~78 routines / ~150 interior loops does not fit the
512-byte site table either, and a dispatcher pre-pass (scan d7+1 rows per call, ~80 calls/frame) costs more than
the interiors it could save. Conclusion: no blitter span fill; a CPU-side unrolled interior (`move.l a3,(a2)+`
x2 without `addq/bne`: 24 vs 38 cycles per group) would also be worth at most 0.1 %.

## 4. Where the real cost is
Fill variants cost 12-14 % because of per-row overhead (`move.w (a0)+`..., edges 4 RMW words, dbra), not
interior bytes: ~1000 rows/frame x ~130 cycles. That is a CPU-side problem (notes spanfill.md 6.2, merge walker
and fill), not a blitter one.

## 5. Cold boot evidence (1 MB, `boot_to_game('M')`, then 400 VBL of `b pc = ... :trace` counters)

Label addresses of the final blob: `probe $b4712`, `cpu $b475e`, `blit $b4768`, original body `$1b99e`.

| Machine / build | reached 3D view | FLAG `$b4bfe` | `$b4768` blit | `$b475e` cpu | `$1b99e` orig body | fps (500 VBL) |
|---|---|---:|---:|---:|---:|---|
| STE TOS 1.62, p4_* + p5_ctl_* + p4_blit_sky | yes (`$6220=d $700a=2`) | 1 | 46 | 0 | 0 | 4.6 (46 flips), 4.7 after a mouse wiggle |
| STE, same without p4_blit_sky | yes | 0 | - | - | - | 4.5 (45 flips), 4.8 |
| STE, no patches | yes | 0 | - | - | - | 4.2 (42 flips) |
| ST TOS 1.04 (`machine='st'`), p4_* + p5_ctl_* + p4_blit_sky, run 1 | yes | 2 | **0** | 44 | 43 | 4.6 (46 flips) |
| same, run 2 | yes | 2 | **0** | 44 | 43 | 4.5 (45 flips) |

Hatari's log shows the probes firing: ST run `Bus Error reading at address $ffff8a3c, PC=$b473e` (the
`tst.b $ffff8a3c`, no blitter), STE run `Bus Error reading at address $ffff8e21, PC=$b4746` (the Mega STE probe,
plain STE). The other `$ffff8e21` / `$ffff8924` bus errors at PC `$159xx` are HAGA's own detection.

With the full current default set (p3b_* + tick_vbl + p5 + p4_*, 22:10-22:30 tree state) the cold boot reached
`$6220=d $700a=2` but the screen stayed black with 0 flips over 900 VBL and `$1b996` never ran; the same
happens without p4_blit_sky (`build` of the defaults alone, FLAG stays 0), i.e. it is not caused by this patch.
FLAG was 1 / 2 on STE / ST in that build because the first sky call happens during start-up.

## 6. Reproduce
- Cycles per call: snapshot, apply `mw2patch.py live --only X`, `Hatari.profile(150)`, sum the addresses in
  `$1b996-$1ba03` and `$b4700-$b47ff`; `$1b9c8` / (71 x 104) = number of calls.
- Histogram: `live --only p4_blit_hist`, `fps(600)`, `m $b4b00 192` (48 longs: bins g=0..39, 40 = single/crossed,
  41 = calls, 42 = rows).
- `abtest` of sets that contain p5 is not a clean gate: `p4_* + p5_*` alone gave walking
  `DIFFER (6126 bytes)` in one run (foot IDENTICAL) while `p4_* + p5_* + p4_blit_sky` gave both IDENTICAL; p5 reads
  real VBL time, so the same-flip-same-state assumption of abtest is shaky for p5-containing sets (not caused by
  the blitter patch, which is stateless between calls). fps in abtest varies 3.1-3.6 / 4.2-5.5 between runs of the
  same build, far above the 0.15 % effect measured here; only the per-call cycle profile resolves it.
