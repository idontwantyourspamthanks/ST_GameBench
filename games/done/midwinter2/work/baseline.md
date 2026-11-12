# Baseline (unpatched)

Recorded 2026-11-07 with Hatari 2.6.1 (STE, TOS 1.62, 2 MB) using `tools/mw2harness.py`.

**Determinism:** a snapshot restore replays deterministically. Three runs per snapshot gave identical flip counts, give or take one flip.

## Primary target: 1 MB STE, 8 MHz

The snapshots were created from a cold boot with `memsize_kb=1024` and navigated to Lobos.

| Snapshot | fps at 8 MHz | fps at 16 MHz | Notes |
|---|---:|---:|---|
| `1mb_ingame_walking` (mouse mode, speed 57) | 5.2 (26 flips per 250 VBL) | 12.4 | Walking at speed. The `$6888` rate goes negative at 16 MHz because the player overshoots the objective within the window. |

Other snapshots:
- `1mb_mode_select`: the M/J/K screen. Use it to create joystick and keyboard snapshots.
- `1mb_ingame_foot`: standing at the mission start.

All 2 MB numbers below are secondary.

## Frame rate, 8 MHz (`fps --vbls 250`, 3 runs each)

All three snapshots are on foot in mouse mode.

| Snapshot | Flips per 250 VBL | fps | VBL per frame |
|---|---|---:|---:|
| `ingame_lobos_foot` (standing) | 21, 22, 22 | 4.2–4.4 | 11.4–11.9 |
| `ingame_foot_walking` (speed 23) | 22, 22, 22 | 4.4 | 11.4 |
| `ingame_foot_turning` (mouse −60 px, no visible turn; effectively a walk) | 22, 22, 22 | 4.4 | 11.4 |
| `ingame_foot_banked_turn` (hard mouse-left; horizon banked, slope fills view) | 18 | 3.6 | 13.9 |

Turning on foot needs a large mouse dx: −450 px gave a visible bank and a new heading arrow, while −60 px did nothing within 6 s. Mouse X sets the turn/bank *rate*, which is the yoke model. Numpad 4 has no effect in mouse mode, so keyboard and joystick tests need J- or K-mode snapshots made from a cold boot.

## Game speed is tied to frame rate (`rate`)

`$6888` is the HUD distance-to-objective word. It was found by diffing RAM against HUD readouts 1127, 1059 and 959: the RAM held 1124, 1056 and 959.

| CPU | fps | `$6888` units/s |
|---|---:|---:|
| 8 MHz | 4.4 | 16.0 |
| 16 MHz | 8.8 | 44.2 |

Doubling fps nearly tripled world speed. This confirms the "game runs faster on a fast machine" report.

An earlier "20 fps at 16 MHz" second sample was wrong. The harness cleared breakpoints with `bc all`, which is not a Hatari command, so the old `$ff8201` watch stayed armed and every flip was counted twice. It now uses `b all`. Repeated `fps()` calls in one session now give 26, 29 and 32 flips (1 MB walking; the scene changes as the player walks), with no stale breakpoints.

## CPU profile, walking, 8 MHz

Cycles are bucketed by the nearest preceding call target. The targets come from `work/dumps/ram_ingame_lobos.bin`.

| Bucket | Share |
|---|---:|
| `$38cd0` | 12.5% |
| `$3c5e2` | 10.5% |
| `$1fdf0` | 4.7% |
| `$1d768` | 4.7% |
| `$1b996` | 4.4% |
| `$30e30` | 3.3% |
| `$3c58c` | 2.5% |
| `$1fa54` | 2.5% |
| `$3c02a` | 2.1% |
| `$3c080` | 2.0% |
| `$2b01a` | 1.8% |
| `$38b8c` | 1.7% |
| `$1da92` | 1.6% |
| `$28f4a` | 1.5% |
| `$200b4` | 1.4% |

## Missing from the benchmark set

- Vehicle snapshots: flying sub, jeep, helicopter.
- A busy scene.
- A sea/sky scene.

These need a vehicle to be reached first. On foot, the mouse controls rates (see `work/controls.md`).

## P3 option A (fixed tick): `tick_vbl` + `tick_head` + `tick_render`, TICK = 10 VBL

All runs are 1 MB cold boots via `boot_to_game('M')`, walking straight, measured over 500 VBL. All four ran concurrently.

| Build | CPU | fps | X units/s (`$66e6`) | `$6888` units/s |
|---|---|---:|---:|---:|
| none | 8 MHz | 4.1 | −99.9 | 15.7 |
| none | 16 MHz | 9.3 | −229.7 | 45.9 |
| tick | 8 MHz | 4.2 | −125.6 | 22.7 |
| tick | 16 MHz | 5.1 | −125.5 | 22.9 |

With the patch, world speed is identical at 8 and 16 MHz (to 0.1%). Unpatched, it is 2.3× faster at 16 MHz.

TICK = 10 runs the simulation at 5 Hz. That is 25% faster than unpatched 8 MHz in this scene, which ran at 4.1 fps, i.e. 12.2 VBL per frame.

On any machine the frame rate is capped at 5 fps until option B (finer ticks) lands.
