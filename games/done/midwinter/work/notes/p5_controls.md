# P5 direct controls for MW1 (patches `p5_ctl_turn` + `p5_ctl_buggy`, default: no)

Apply **both** together. Blob range `$B3800-$B3BFF`: code `$B3800` (110 bytes), data `$B3BF0` (long, `; data:` reservation).
Design source: `controls.md` section 8 (H1 + H2), here with a remainder carry, per-device gain and a count cap.
Raw logs and the scripts that made them: `work/p5_controls_tests/` (`p5gate.py`, `p5buggy_check.py`, `p5glider_check.py`,
`coldboot.py`, `*.log`, `run_*.out`, `cb_*.out`). All numbers below come from those files.

## What changes

| site | original | new | patch |
|---|---|---|---|
| `$12fe2` (6 B) | `move.w $24faa.l,d0` (start of `sub_012fe2`) | `jmp $b3800.l` | `p5_ctl_turn` |
| `$13618` (6 B) | `move.w $24faa.l,d0` (buggy exertion test) | `move.w $15110.l,d0` | `p5_ctl_buggy` |

`sub_012fe2` is the turn consumer of every steering vehicle: ski `$13236`, buggy `$135d0`, glider `$13754`
(`m68dis --callers 12fe2`). The old body (clamp +-512 written back to `$24faa`, cubic rate, `$12fe8..$13020`) is never reached any more.
Snipe never calls it (it uses `$24faa` as a position, `controls.md` 5.2) and is unchanged.

### The routine (`p5_ctl_turn.s`, org `$b3800`)
```
d0 = $24faa.l ; sub.l d0,$24faa.l            consume exactly what was read (one RMW; an IKBD add in between is kept)
d0 = signed hi word (counts), clamped +-CAP (200)
d1 = KEY_GAIN (128), or MOUSE_GAIN (192) if $2c176 != 0 (mouse control selected)
d0 = counts*gain (8.8) + REM ; turn = d0 truncated toward zero /256 ; REM = d0 - turn*256
$15110 = turn ; $12c98 += turn ; d1 = d0 = turn ; rts        (only d0, d1 changed; d2 saved)
```
* **Mouse:** the funnel `$66c0` adds dx once per IKBD packet, so counts consumed = motion since the last call. No motion = 0 turn, nothing persists
  (the "yoke" of `controls.md` 5.1 is gone because `$24faa` is cleared by the consume, not clamped and kept).
* **Joystick / numpad keys:** the VBL handler injects +-5 counts per VBL while held (`$65c0`/`$652e`, `controls.md` section 4), so the counts
  consumed between two calls are 5 x VBLs held: **constant rate per real second, zero on release, whatever the interval between calls**
  (a tap shorter than one call interval still turns pro rata). No VBL hook was needed in MW1 (MW2 needed `p5_ctl_vbl` because its
  joystick/key path was a ramp; here the funnel already counts per VBL).
* **Race-free:** the consume is `move.l $24faa,d0` then `sub.l d0,$24faa` (RMW instruction). The IKBD IRQ `add.l d1,$24faa` can fire between the
  two instructions; its counts stay in `$24faa` for the next call.
* **REM:** sub-unit remainder carried so a slow mouse (1-2 counts per call) is not truncated away; `|REM| < 256` always and the turn is computed
  from `REM + counts*gain`, so with zero counts the turn is 0 (REM can never turn on its own: log column REM stays constant after release).
* **CAP:** 200 counts per call (key: 40 VBL worth; mouse: more than any real flick per tick). It bounds a lurch from counts that piled up while the
  sim did not call (e.g. mouse moved in a menu: `$62b8 == 2` there as well). The mode init `sub_012eae` (`$12ee6/$12eee`, called from `$12d30`) clears
  `$24faa/$24fae` on every vehicle change, so snipe -> ski starts clean.
* **Rates:** heading unit = 1/1024 turn (0.352 deg).
  * Keys/stick: 0.5 unit x 5 counts x 50 VBL/s = **125 units/s = 44 deg/s** (measured below: 125/s). The old full-yoke rate was 32 units per frame:
    128/s at the measured 12.5 VBL per frame at 8 MHz, but it needed ~2 s of ramp and never stopped.
  * Mouse: 0.75 unit/count = 0.26 deg/count (the value MW2 uses). Measured: -150 host px = 67 counts (`$24faa = -67` in the unpatched run) -> -50 units.
  * Tune: `MOUSE_GAIN`, `KEY_GAIN` (8.8) at the top of `patches/p5_ctl_turn.s`; `CAP`.
* In **J/K control mode the mouse is also live** (measured: J snapshot, `rel(-150,0)` turned -33 = 67 x 0.5, `run_JM_patched.out`); it gets `KEY_GAIN`
  because `$2c176` is 0 there. Harmless, kept.

### Buggy companion (`p5_ctl_buggy.s`)
`$13618: move.w $24faa,d0 ; cmp.w $1413a,d0 ; beq ; move.w d0,$1413a ; addi.w #$28,$1354c` adds exertion whenever the steering value changed since
the last step. After the new `$12fe2` `$24faa` is always 0 at that point (the same step's `bsr $12fe2` at `$135d0` consumed it), so the test could never
fire. It now compares `$15110`, the turn of this step: the exertion again follows steering changes (start, stop, mouse motion).
The glider's own exertion test (`$13758..$13766`, uses `|$15110| * 7 + 10`) reads `$15110` already, and its second test compares `$24fae` (not touched).

## Interaction with the timing patches (MW1Timing)
Confirmed by MW1Timing (IRC): `$12fe2` is called exactly once per 5 Hz logic tick (TICK = 10 VBL), only from the ski chain `$13236`; the state machine
(including the `$15110` readers `$1335c`, `$134e4`, `$15086`) is never sub-stepped, and the smooth 25 Hz motion is interpolated after the call from
`e = $12c98(after) - $12c98(before)`. So the turn per tick is `5 counts x VBLs held x 0.5` = about 25 units per 10 VBL (old max 32 per frame) and
`$15110` keeps the same magnitude as the original full yoke for the ski-physics terms. A shorter catch-up tick turns less, a longer one more:
the rate per real second is constant. `$12fe2` is a plain subroutine (rts; d0/d1/`$15110`/`$12c98`/REM only), as required.

## Gates (raw logs in `work/p5_controls_tests/`, command `python3 p5gate.py M|J|K unpatched|patched`)
Columns: wall s, VBL, heading `$12c98` (signed word), `$15110` (turn of the last step), `$24faa` (hi word, instantaneous), REM. A row is one sample every
0.5 s of wall time (about 25 VBL: the VBL column shows it is real time). Snapshots `1mb_ski_stand`, `_J` (`--joy1 keys`), `_K`. The patch is applied at a flip
breakpoint (`b pc=$bd9a :trace :once :file apply.txt`: `loadbin` image + 2 site writes, read back: `$12fe2: 4e f9 00 0b 38 00`, `$13618: 30 39 00 01 51 10`,
`$b3800: 2f 02 20 39 00 02 4f aa`).

**M: `rel(-150,0)` at t=1 s** (`patched_M.log` / `unpatched_M.log`)
```
patched                                     unpatched
 wall  VBL   head  rate   acc    REM          wall  VBL   head  rate   acc
 1.45  6518   -16   -16   -45   -128          1.44  6463    -1    -1   -67
 1.52  6521   -50   -34     0    -64          2.02  6492    -4    -1   -67
 2.01  6546   -50     0     0    -64          5.01  6641   -15    -1   -67
 5.51  6721   -50     0     0    -64          8.01  6791   -25    -1   -67
11.52  7022   -50     0     0    -64         11.51  6967   -37    -1   -67      (still turning, 3.3 units/s)
```
Patched: turns -50 (two steps), then heading constant for 10 s. Unpatched: `$24faa = -67` is kept for ever (the yoke), heading drifts -1 per frame without end.

**J: Left held 3 s (key down t=1.0, up t=4.0)** (`patched_J.log` / `unpatched_J.log`)
```
patched (J)                                 unpatched (J)
 wall  VBL   head  rate   acc                wall  VBL   head  rate   acc
 1.51  6256   -50   -35   -30                 1.51  6201    -2    -1  -125     (ramp)
 2.01  6280  -120   -35   -10                 3.01  6276   -50   -22  -500
 2.52  6306  -185   -33   -10                 4.03  6327  -178   -32  -547
 3.50  6355  -285   -33   -55                 5.01  6377  -306   -32  -512     (released at 4.0)
 4.03  6382  -377   -30     0                 7.02  6477  -594   -32  -512
 4.50  6405  -377    0     0                 11.51 6702 -1138   -32  -512     (keeps turning at 32/frame after release)
11.51  ...   -377    0     0
```
Patched: 125 units/s while held (-377 in 3.0 s), exactly 0 after the release. Unpatched: ~2.5 s ramp, then 117 units/s (from rows), never stops.

**K: KP4 (`hatari-event keydown/keyup 106`) 3 s** (`patched_K.log` / `unpatched_K.log`): patched -375 at the release (4.02 s), -377 and constant thereafter;
unpatched -1100 at 11.5 s with `$24faa = -512` persistent, 107 units/s at the end.

**Tap:** KP4 0.2 s (`run_KT_patched.out`): -27 then 0 (0.2 s x 125 = 25). J mouse in J mode: -33 (`run_JM_patched.out`).

**Buggy and glider (poke test; no snapshot reaches them).** On the ski snapshot the step pointer `$12d5e` was poked (`w $12d5e 00 01 35 9a` = `$1359a` buggy with
`$13598 = $104`, `$14774 = 0`; `w $12d5e 00 01 37 3c` = `$1373c` glider) with the patch applied, and a breakpoint logged at `$13618` (buggy) / `$13770` (glider, after `bsr $12fe2`).
* Buggy (`run_B_check.out`, 29 rows, one per buggy step, ~14 VBL): mouse -150 px gives turn `-16, -34` then 0, heading -16 then -50 and constant; `$1413a` takes the
  values `-16`, `-34`, `0` in the rows after (the exertion compare sees every change) and the old value (`0`) for rows with no motion.
* Glider (`run_G_patched.out`, 30 rows): same turn sequence `-33, -17, 0`, heading -50 constant; the glider path runs through `$12fe2` and onward without a hang. The bank store
  `$1377c` (`$12c9c = 2 x d1`) was not reached (`$13b40 < 0` branches to `$139aa` in this state), so the bank value itself is **not tested** [INFERENCE: it follows d1 = turn, 2x].

**Cold boots (build `build/p5ctl` = `pp_nofade pp_bigram_cache p5_ctl_turn p5_ctl_buggy`, control M, `coldboot.py`):**
```
config ste1m ste TOS_1_62.img 1024 KB
boot_to_game ok in 111 s; control mode M gstate {'x': 25600, 'z': 25600, 'speed': 0, 'heading': 0, 'action': 0, 'exit': 0}
MWPO marker $b2ff8: b'MWPO'      $12fe2: 4ef9000b3800     $13618: 303900015110     $b3800: 2f02203900024faa
mouse rel(-150,0): start heading 0; ten samples 0.5 s apart all heading 968 (= -56), rate15110 0 : turned once, then stopped
walk: before {x 25600, z 25600, speed 0} after 8 s {x 24879, z 27556, speed 172}      MWPO after walk: b'MWPO'
config megaste4m megaste TOS_2_06.img 4096 KB   (Hatari reports "16MHz(CE)/- 4MB MegaSTE, TOS 2.06")
boot_to_game ok in 103 s; ...gstate {'x': 25600, 'z': 25600, 'speed': 0, 'heading': 0, ...}
MWPO b'MWPO'; $12fe2 4ef9000b3800; $13618 303900015110; $b3800 2f02203900024faa
mouse rel(-150,0): heading 968 in all ten samples (-56, then stopped)
walk: after 8 s {x 24765, z 27856, speed 0} (walk finished by the basin as in baseline.md)   MWPO after walk: b'MWPO'
```
Screenshots of both (3D view, HUD alive, 06:10 / 06:18) are `/tmp/coldboot_{ste1m,megaste4m}.png` (not kept).

## Limits / not done
* Bank angle on the glider and buggy driving were not exercised in play (no snapshot); the poke tests above only prove the turn path and the buggy exertion compare.
* The Y axis (throttle/lever, `$24fae`) is untouched by design (`controls.md` section 8: a position lever, time based already). Snipe is untouched.
* Keys and stick share one gain; in M mode the stick/keys inject 0 (step tables 0), in J/K the mouse is also live at `KEY_GAIN`.
* Not tested: joystick packet sources other than Hatari `--joy1 keys`, real 16 MHz STE timing with the tick patch (MW1Timing's), the floppy build.
