# MW2 timing: 5 Hz world tick, 25 Hz foot sub-ticks, real time at 50 and 60 Hz

Patches: `patches/tick_vbl.s` (the real-time clock), `patches/p3b_head.s` (the default scheduler: 5 Hz world, 25 Hz foot sub-ticks) or `patches/tick_head.s` + `tick_render.s` (option A, `default: no`).
The design and the per-tick state equality are in `tick_inventory.md` (sections 4-6, the `t6`/`cmp6` gate in `work/p3b_tests/`); this file holds only what concerns the refresh rate.
Evidence = raw output of `tools/mw2tick.py` (new), `work/p3b_tests/t6.py` + `cmp6hz.py`, `mw2patch.py`; Hatari 2.6.1; anything not run is `[INFERENCE]`.

## 50/60 Hz: the tick is real time, not a VBL count (TickHz)

**Problem.** The clock `tick_vbl` counted VBLs and the schedulers used `GRP = 10` VBL (5 Hz) and `SUBT = 2` VBL (25 Hz): a 60 Hz display (US TOS defaults, NTSC, TOS 2.06 on a Mega STE) ran the world at 6 ticks/s and the foot sub-ticks at 30 Hz.
Hatari with TOS 2.06 `--machine megaste` boots at 60 Hz by itself (`$ff820a = $fc`, cold boot below).

**Change.**
* `tick_vbl` (VBL handler hook at `$262d0`): the free-running clock long at `$B3400` is now in units of 1/300 s. Every VBL adds the length of that frame, read from the shifter sync mode:
  ```
  addq.l #5,$b3400.l        ; 60 Hz frame
  btst   #1,$ffff820a.w     ; bit 1 set = 50 Hz
  beq.s  .done
  addq.l #1,$b3400.l        ; 50 Hz frame: 6 units
  ```
  The hook runs in the VBL handler, so the rate is tracked frame by frame (a runtime switch is exact) and adds a `btst`, a branch and a second `addq.l` per VBL (about 50 cycles [INFERENCE: 68000 timing tables, not measured]). It grew from 16 to 30 bytes, and the old slot `$B40F2` has only 16 bytes before `p3b_render` (`$B4102`): **the blob moved to `$B3700`** (free; `mw2patch.py build` reports no overlap).
* `p3b_head`: `GRP` = 60 units = 0.2 s (5 Hz, 10 VBL at 50 Hz, 12 at 60 Hz), `SUBT` = 12 units = 0.04 s (25 Hz foot sub-tick: 2 VBL at 50 Hz, 2.4 VBL at 60 Hz, so at 60 Hz a sub-tick is paced by the accumulator, not a whole number of VBLs). `ACC` (D+4) is in units; the long delta is compared with `cmpi.l #4*GRP,d1` (0.8 s resync), the clamp is `move.w #3*GRP,d0` (0.6 s: `moveq` no longer reaches 180). `clr.l 8(a0)` clears SUB and HOLD (adjacent words) in one instruction: the 4 bytes this saved are what keeps the blob from running into `fdiv5` at `$B40C8` (it was exactly full).
* `tick_head` (option A): `TICK` = 60. Nothing else.
* Not changed, because they are ratios: `p5_ctl_vbl` / `p5_ctl_x` (held fraction = VBLs held / VBLs elapsed since the last tick), the `p3b_pos/hdg/alt/bank` 1/5 Bresenham accumulators (they divide a tick into 5 passes, whatever the pass length). The world step per tick is identical, only the timing changes.
* 71.25 Hz (mono) is not representable in whole units of 1/300 s and the game has no mono mode: not handled.

**Gate 1: world ticks per emulated second** (`python3 tools/mw2tick.py rate --only tick_vbl p3b_head p3b_render p3b_pos p3b_hdg p3b_alt p3b_bank p3b_save p3b_probe --hz 50 60 --mhz 8 16`; snapshot `1mb_ingame_walking`, live patch set + `w $ff820a $00` for 60 Hz at a flip; a world tick = one arrival at `$3148e`, the instruction after the loop head (`$4f5a` itself is a shared subroutine: 2 hits per tick, rejected as the marker); rate = ticks / (VBL span / hz); cycles per VBL = 8 MHz / hz prove the refresh):
```
RESULT 1mb_ingame_walking 8 MHz 50 Hz: sync $fe, 160270 cycles/VBL, 94 ticks in 938 VBL = 18.76 s: 5.011 ticks/s
RESULT 1mb_ingame_walking 16 MHz 50 Hz: sync $fe, 320584 cycles/VBL, 120 ticks in 1486 VBL = 29.72 s: 4.038 ticks/s; without stalls > 30 VBL [(739, 297)]: 119 ticks in 1189 VBL = 5.004 ticks/s
RESULT 1mb_ingame_walking 8 MHz 60 Hz: sync $fc, 133565 cycles/VBL, 94 ticks in 1129 VBL = 18.82 s: 4.996 ticks/s
RESULT 1mb_ingame_walking 16 MHz 60 Hz: sync $fc, 267099 cycles/VBL, 120 ticks in 1782 VBL = 29.70 s: 4.040 ticks/s; without stalls > 30 VBL [(889, 352)]: 119 ticks in 1430 VBL = 4.993 ticks/s
```
The one stall per 16 MHz window (297 VBL at 50 Hz, 352 at 60 Hz, about 6 s, at about 15 s into the scenario) is **not ours and not a tick problem**: it is the original game's local-map rebuild, see "The 6-second stall" below. It also happens at 8 MHz, where it takes twice as long (594 VBL); the 938-VBL window of the 8 MHz row above simply ends before the player reaches it. The rate with the stall excluded is the tick rate.
Option A (`tick_vbl tick_head tick_render`), 8 MHz: 5.021 ticks/s at 50 Hz, 5.027 ticks/s at 60 Hz.

**Gate 2: the p3b state gate at both refresh rates** (`work/p3b_tests/t6.py` A vs B2, heading 768, 8 MHz, no input; new `HZ60=1` env pokes `$ff820a` at the apply flip; compare with `cmp6hz.py`, group ends of B (PH = 5) against the 5 Hz option A row by row: X, Y, heading, game clock `$eb8c`, minute countdown `$6290`, route `$764c`, speed, bank, type):
```
Anew_768_N50 B2new_768_N50 groups 41 mismatching 0
Anew_768_N60 B2new_768_N60 groups 41 mismatching 0
```
(the lines before it are the first three groups, `EQ`; image sets: A = `tick_head tick_render tick_vbl`, B2 = `p3b_alt p3b_bank p3b_hdg p3b_head p3b_pos p3b_probe p3b_render p3b_save tick_vbl`.)

**Gate 3: cold boot of the default build** (`python3 tools/mw2patch.py build --out /tmp/tickhz/mw2`, `verify: ALL OK`; `python3 tools/mw2tick.py cold --game DIR --mem M --machine X --tos T [--hz 60]`: `boot_to_game` to the Lobos 3D view, 1464 VBL at each clock):
```
boot 240 s; marker 4d57504f ("MWPO"); $31486 4eb9000b...; sync $ff820a = $fe -> booted at 50 Hz         (1 MB STE TOS 1.62, forced to 60 Hz with `w $ff820a $00`)
RESULT cold ste TOS 1.62 1024 KB 8 MHz 60 Hz: sync $fc, 133604 cycles/VBL, 122 ticks in 1464 VBL = 24.40 s: 5.000 ticks/s
RESULT cold ste TOS 1.62 1024 KB 16 MHz 60 Hz: sync $fc, 267208 cycles/VBL, 122 ticks in 1464 VBL = 24.40 s: 5.000 ticks/s
boot 214 s; marker 4d57504f; $31486 4eb9000b...; sync $ff820a = $fc -> booted at 60 Hz                  (4 MB Mega STE TOS 2.06, native 60 Hz, no poke)
RESULT cold megaste TOS 2.06 4096 KB 8 MHz 60 Hz: sync $fc, 133604 cycles/VBL, 122 ticks in 1464 VBL = 24.40 s: 5.000 ticks/s
RESULT cold megaste TOS 2.06 4096 KB 16 MHz 60 Hz: sync $fc, 267208 cycles/VBL, 122 ticks in 1464 VBL = 24.40 s: 5.000 ticks/s
```
(An earlier run of the Mega STE labelled its first row "8 MHz" but measured 267208 cycles/VBL: Hatari's Mega STE starts at 16 MHz and the tool only switched for 16; `cold` now calls `set_cpuclock` for both rows. The rows above are from the corrected run.) The player stands in the 3D view: the tick marker does not depend on input.

Limits: the sync mode is read only (never written); a game that rewrites `$ff820a` is followed frame by frame. The rate was not run on a TT or Falcon (`$ff820a` semantics there not checked).

## The 6-second stall: the game's local-map rebuild (MW2Stall)

**Finding: legitimate original behaviour, identical in the unpatched game; no patch change.** On foot the world is a 100 x 100 cell window (`$66e6/$66ea` in 1/512 cell, centre `$6400`); the world coordinates of its origin are `$66bc/$66be`. When the player leaves the middle of the window the game rebuilds it. `sub_03450a/03451a` (`$3451a`: `cmp.l #$1388,d0 / ble`, `#$b478 / bge`, same for d1) does `clr.w $6288` when X or Y <= $1388 (9.77 cells) or >= $b478 (90.2 cells); `sub_031dee` (`tst.w $6288`, called inside the world logic) then recentres: `$66e6 += 40 cells`, `$66bc` -= 80, and regenerates the terrain (`$2db44`, `$31ece`, `$24d0e`, `jsr $5092` = `$1c832` terrain shading with the `$27462` PRNG and the `$33822` integer square root: the hot spots of the profile). It runs to completion inside one world tick, with the VBL still running.
The walking snapshot has the player walking toward X = 0 at 0xb per 25 Hz sub-tick, so it crosses `$1388` after about 15 s at 5 ticks/s: one rebuild per 16 MHz window.

**Evidence** (scripts `work/stall/{trace,sample,prof,bp}.py`, raw logs next to them; Hatari 2.6.1, snapshot `1mb_ingame_walking`, 1 MB, 50 Hz):
* Tick head log at 16 MHz (patched p3b set): the last head entry before the stall is at VBL 780 (clock 5280, PH 5 pending, X = `$138e`), the next at VBL 1069 (clock 7014, X = `$6383`, `ACC` 0): 289 VBL (5.8 s) with no entry at `$b4000`. Before and after the stall the passes are on time (`ACC` 0..18, 4 VBL per sub-tick at 16 MHz with a render). Only X changes during it; Y `$6400`, type 13, `$40b6` 0, UI context `$700a` 2, render gate `$6298` 0, game clock `$eb8c` 0, countdown `$6290`, route `$764c`, speed, heading all continue as before from the next pass (so: no message box, mode change or cut-scene).
* Breakpoints on the rebuild entry `$31df6` and exit `$31f12` (`bp.py`), CycleCounter (low 32 bits) and `$66e6`, `$66bc`:
  ```
  patched   16 MHz 50 Hz: enter vbl+780 cyc ddd624b8 x1383 wx1152 -> exit vbl+1065 cyc e3469b7c x6383 wx1072  : 285 VBL, 91.6 Mcycles
  unpatched 16 MHz 50 Hz: enter vbl+258 cyc d3db65dc x1383 wx1152 -> exit vbl+543  cyc d94b553c x6383 wx1072  : 285 VBL, 91.5 Mcycles
  patched    8 MHz 50 Hz: enter vbl+984 cyc d572df28 x1383 wx1152 -> exit vbl+1560 cyc daf41fec x6383 wx1072  : 576 VBL, 92.0 Mcycles
  ```
  (cycles = exit - enter, low 32 bits: patched 16 MHz 0x057076c4 = 91.6 M, unpatched 0x056fef60 = 91.5 M, patched 8 MHz 0x058140c4 = 92.0 M; the 0.1-0.5 % difference is [INFERENCE] the VBL clock hook, the p3b blob and the 25 Hz sub-tick bookkeeping; the unpatched run has no clock, `clk0`.) The same trigger X (`$1383`), the same recentre (`$6383`, `$66bc` 1152 -> 1072) and the same duration in cycles in the unpatched game. The original world stops exactly the same way: no frame is run for 285 VBL at 16 MHz.
* PC profile over the stall (`prof.py`, 16 MHz, VBL 830..930): the CPU is busy (the listed addresses alone account for 224 k of the 320 k cycles per VBL), hot spots `$27462-$2749c` (PRNG), `$33822-$3385e` (isqrt), `$1c846-$1c956` (terrain shading): it is computing, not waiting for a clock or a counter.
* So it is CPU-bound: about 92 Mcycles = 5.7 s at 16 MHz, **11.5 s at 8 MHz** (the 8 MHz gate window of 938 VBL ended before it started). With the window extended (`mw2tick.py rate --hz 50 --mhz 8 --vbls 2000`): `RESULT 8 MHz 50 Hz: 140 ticks in 1985 VBL = 3.526 ticks/s raw; without stalls > 30 VBL [(938, 594)]: 139 ticks in 1391 VBL = 4.996 ticks/s`. So it is not 16 MHz-only, and not our clamp: the tick rate outside it is 5.00 at both clocks.
* Our scheduler after the stall behaves as designed: the clock gap (16 MHz: 5280 -> 7014 = 1734 units; 8 MHz: 6486 -> 9942) exceeds `4*GRP` = 240, so the head resyncs (one pass, `ACC` 0, no catch-up burst): the 289 VBL of the stall are not paid back with a burst of ticks, as in `tick_head`. The measured passes right after it are the normal 25 Hz sub-ticks (`acc` 0/12, PH 5 -> 1 -> 2 ...).

No accumulator overflow (`ACC` stays <= 48 at 8 MHz, <= 18 at 16 MHz), no counter wrap and no resync loop were seen; the marker `$3148e` is simply not reached while `$4f5a` (the world logic) is inside the rebuild. Not a measurement artefact: the `$b4000` head entries (`trace.py`) show a 289-VBL gap with no entry; the marker gap in `mw2tick.py` (297 VBL) is the 285-VBL rebuild plus the normal ~10-12 VBL tick interval around it [INFERENCE: 285 + 12].
Gates: no patch changed, so the group-end exactness gates (`t6.py`/`cmp6hz.py`, 41 groups at 50/60 Hz, 8/16 MHz) were not re-run: [INFERENCE] nothing in them touches this path (41 groups, 8 MHz, from the start state; no check was made that X stays above `$1388`). The only edit is a comment in `tools/mw2tick.py` naming the stall.
Consequence for players: walking 40 cells in the same direction freezes the game for about 5.7 s at 16 MHz and 11.5 s at 8 MHz, as the original does; speeding that rebuild up is a separate optimisation (`$1c846`-`$1c956`, `$27462`, `$33822` are its hot spots), not a timing fix.
