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
The one stall per 16 MHz window (297 VBL at 50 Hz, 352 at 60 Hz, about 6 s, at about 15 s into the scenario) is the tick marker not being reached for about 6 s (cause not investigated), not a slower tick: the same stall, 4.023 ticks/s raw, with the committed (pre-change) `p3b_head`/`tick_vbl` at 50 Hz (`mw2tick.py rate --live <image of git HEAD patches>`), so it is not caused by this change; its cause was not investigated. The rate with the stall excluded is the tick rate.
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
