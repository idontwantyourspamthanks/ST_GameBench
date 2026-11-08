# Joystick mode check (lead, 2026-11-07)

This corrects one claim in `controls.md`: "Joystick steering is dead code". **Joystick steering does work** in joystick mode.

## Control-mode flags

| Mode | `$eb76` | `$eb78` | `$eb7a` |
|---|---|---|---|
| J (read on the corridor screen after pressing J at the M/J/K screen) | `ffff` | `0000` | `0000` |
| M (`1mb_ingame_walking`) | `0000` | `0000` | `ffff` |

## Method

1. Restored `1mb_ingame_foot.sav` with Hatari `--joy1 keys`. Cursor keys act as the joystick.
2. Switched the game to joystick mode with `w $eb76 $ff $ff $00 $00 $00 $00`.
3. Read heading `$6742`, speed `$6772`, and `$6888` (distance to objective) while giving joystick input.

## Readings

| Step | Heading `$6742` | Speed `$6772` | `$6888` |
|---|---:|---:|---:|
| Start | 768 | 0 | 1272 |
| After holding Up for 3 s | 768 | 944 | 855 |
| 3 s later, no input | 768 | 944 | 2 |
| After holding Left for 3 s | 268 | 0 | 50 |
| 3 s later, no input | **344** | 0 | 50 |

## Findings

- Joystick Up raises speed, and the speed persists with no input.
- Joystick Left turns the player. After release, the heading **keeps changing**: 268 → 344 over 3 s with no input. This is the yoke behaviour the user described, now confirmed for joystick mode as well.

## Unresolved

- Why speed dropped to 0 during the Left hold. Possibly the player reached or ran past the objective, or this is a mode interaction. Not yet investigated.
- Joystick input reaches steering via some path. Static analysis (`controls.md`) found that `$26b58`'s ramps have no readers, so the path is still unidentified. P5 must trace it dynamically, e.g. with a watch on `$6fb6`/`$6fba` while the joystick is held.
- Menus: in J mode the joystick drives the pointer and the mouse is ignored.

## Joystick feeds the same accumulator as the mouse (`$6fb6`)

Same setup, J mode, with `m $6fb6 8` read at each step:

| Step | Bytes at `$6fb6` | High word | Value (16.16) |
|---|---|---|---|
| Rest | `00 00 00 00 00 00 00 00` | — | 0 |
| After holding Left for 2 s | `fe 3b 40 00 …` | `$fe3b` | −453.75 |
| 2 s after release | `ff 06 40 00 …` | `$ff06` | −249.75 |

So joystick Left ramps the same 16.16 X accumulator that the mouse uses. On release it settles at a non-zero value instead of returning to 0, which is the persistent turn.

The P5 patch at the consumer (`$34152`/`$341dc`, `controls.md`) therefore covers all three modes (M, J and K). The joystick and keyboard ramp source (probably `$26c1e`, 50 Hz) still needs confirming with a watch on `$6fb6`. That watch would also show where the value is written.
