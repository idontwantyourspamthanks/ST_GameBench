# P5 direct controls (patches `p5_ctl_vbl` + `p5_ctl_x`, default: no)

Apply **both** together. Blob range `$B4300-$B46FF`: sampler `$B4300`, consumer `$B4400`, data `$B46C0-$B46C7`.
Raw test logs and the scripts that made them: `work/p5_controls_tests/`.

## What it does
Only the X axis (yaw) changes. In `controls.md` §8.1 and the per-type table (`$54dc0+type*$3e`, dumped for all 22 types),
**every vehicle type has X apply selector 4 (`$345c4`, heading) and X rate selector 2 (direct)**. One hook therefore covers all types.
Type 4 has X clamp 0/0, so it has no yaw.

| Mode | Rule |
|---|---|
| M | `$6766 = trunc(dx_counts * MOUSE_GAIN/256)`, capped at ±`MOUSE_CAP`. `dx_counts` = hi word of `$6fb6`, summed since the last tick. `$6fb6` is cleared. |
| J / K | `$6766 = ±YAW_PCT% * (clamp - deadzone of this vehicle) * (VBLs held R-L) / (VBLs since last tick)`. The ramp accumulation in `$6fb6` is discarded. |

- Everything downstream is unchanged: `$6752 = $6766*scale` clamped to the vehicle's limits, `$6740 = >>4`, `$345c4`.
- Deadzone and clamp write-back of `$347f2` are gone for X, so the yoke can no longer persist.
- No motion or no key gives `$6766 = 0` on the next tick. The game's fatigue scalers (`$2f7b0`/`$2f784`) still scale `$6740` (unchanged).

**Tunables** (top of `patches/p5_ctl_x.s`):
- `MOUSE_GAIN` = 384 (8.8 fixed, 1.5). One count gives `1.5*scale/16` heading units; on foot, scale 8 gives 0.75 units, i.e. 0.26° per count.
- `MOUSE_CAP` = 1000.
- `YAW_PCT` = 50. On foot this gives `$6766 = ±50`, then `$6740 = ±25` per tick: 44°/s at 5 Hz.
  100 reproduces the old maximum yoke rate.

## With the P3 partial-B scheduler (`p3b_*`)
The player sim, and with it the consumer at `$34152`, runs on every 2-VBL foot sub-tick (5 per original 5 Hz tick). `p5_ctl_x` reads the
scheduler word `HOLD` (`$B42EA`, owned by `p3b_head`): fresh input is consumed only on the first pass of a group (HOLD = 0; the same once-per-tick
window as before: counters and `$6fb6` are read and cleared there and keep accumulating during the other four passes). On passes 2..5 (HOLD = 1) the same
`$6766` is reused from `PREV` (now written on every fresh pass, mouse included). So the yaw of a group is the 5 Hz yaw: J/K 26 units per group,
mouse gain 1.5, nothing consumed five times. Without `p3b_head` HOLD stays 0 and the consumer behaves as before. Non-foot types get one 10-VBL pass per
tick with HOLD = 0.

## Hooks
1. `$34152` (6 B: `bsr.w $347f2` + `moveq #0,d0`) -> `jsr $B4400.l`. The consumer runs once per logic tick, inside `sub_034142`.
2. `$262c8` (8 B: `bsr.w $26b58` + `bsr.w $26c1e` in the VBL handler) -> `jsr $B4300.l; nop`.
   - The sampler calls both originals, then every VBL counts the VBLs left and right were held since the consumer last read the counters.
   - Left/right: joystick `$75a9` bit 2/3 (J), or the key table `$7686` KP7/4/1 and KP9/6/3 (K).
   - Counts are read and cleared with interrupts masked. Window halving at ELAPSED >= 64.
   - If ELAPSED = 0 (catch-up tick) the previous yaw is reused.
   - A tap shorter than a tick turns pro rata; nothing is lost between polls.

## Verified
`controls_joystick_check.md` is right and `controls.md` §7 is wrong: the joystick feeds `$6fb6` via `$26b58`.
- `d1` = `$75b2/$75ba` ramp, bit 3/2 = right/left.
- `d0` = `$75b6/$75be` ramp, bit 0/1 = up/down, into `$6fba`.
- `bra $26a8e` is reached with `d0/d1` live (`$26b74`, `$26b92`, `$26bb0`, `$26bce`).

In J mode the mouse is gated off by `$eb7a`. In K mode only `$26c1e` feeds the accumulators. So the old `$6fb6` carried exactly one device per mode.

Tests (patched = tick patches + p5): M `-400 px` stops at 630 (unpatched: still turning at tick 40+); M `-150 px` stops at 714.
J Left 3 s: -26/tick (130 units/s) constant, last tick -4 (partial), then 0. J Right: +24/tick. K KP_4 / KP_6 the same.
J tap 0.1 s: -12, -4, then 0.
Poke `$6220=8` (the game remapped it to 5): `$6766 = -75`, the 50 % of the type-5 table (clamp 300 - deadzone 150). Type 4: no yaw.
abtest: pixels identical. Cold boot with the `build/p5` set: the mouse test stops at 710.

## Unchanged / limits
- **Throttle** (mouse Y / J,K up-down, `$6fba` -> `$341dc`) and **bank/pitch** (mouse buttons, `,` `.`, the Left/Right arrows -> `$6fbe`, `$34256`) are untouched.
  The Y axis is the persistent throttle lever by game design (on foot: speed persists after release, which the design intends).
  Types 15 and 17 use Y rate selector 1 (derivative) with apply sel 5 (bank). That is already motion-proportional for the mouse, but J/K ramp-driven. Not converted.
- Heading is stored in even units (`andi.w #$3fe` at `$345ea`): odd steps floor to even, so -25 turns -26 and +25 turns +24.
  This is the original arithmetic. Small mouse dx (< ~2 counts at gain 1.5) can quantise away.
- The downstream rate clamp (`$18/$1a`, type 13: ±80 units/tick) caps a fast mouse flick; the excess is lost.
- K: left = KP7|KP4|KP1, right = KP9|KP6|KP3. The original acted on the first held key in table order, e.g. KP8 + KP4 turned nothing.
- Only types 13 (real), 5 (via poke) and 4 (table inspection) were exercised. Other vehicles use the same code path with their own table, but are not tested in play.
- `$37626` (`$40b6 != 0`) and `$310dc`/`$31776` clears are untouched.
- Not tested: Mega STE / 16 MHz, and joystick packet sources other than Hatari `--joy1 keys`.
