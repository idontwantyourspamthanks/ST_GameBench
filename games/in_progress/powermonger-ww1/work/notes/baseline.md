# Powermonger WW1: baseline, measurements and the real-hardware report

Evidence: **[obs]** = raw emulator output (reproducible with the stated command), **[user]** =
the user's own real-hardware observation, **[INFERENCE]** = not verified.

Machine for all emulator runs: 1 MB STE, TOS 1.62, 8 MHz unless stated, Hatari 2.6.1,
`PMWW(disk=None, snapshot='work/snapshots/mapview.sav')` (the 3D map view of a fresh
"Start New Conquest" territory, 26 men camped, the starting castle).

## 1. World rate and frame rate at the map view [obs]

Speed period `$5a852 = 1` at the map view, so every pass renders and flips (passes/s = fps).
The world steps once per pass (the pre-tick behaviour).

| | 8 MHz | 16 MHz | ratio |
|---|---:|---:|---:|
| passes/s (= fps) | 3.55 (an earlier run: 4.27) | 6.97 | **1.96x** |

- The world is CPU-speed-coupled: the defect the tick port fixes (the 1990 game showed
  2.1-2.9x; its original 2.38 fps standing at 8 MHz / 6.25 at 16 MHz).
- The pass costs about 1.9-2.3 M cycles at 8 MHz (the 1990 game: 2.1-3.4 M in its scenes) —
  comparable; the scenes are not like-for-like (below).

## 2. Profile at the map view [obs]

Percent of total cycles; raw 16 MHz data in `profile16.txt` (1200 VBL runs).

| page | 8 MHz | 16 MHz | what |
|---|---:|---:|---|
| `$08300` | 39.8% | 40.5% | the block-pattern combine `$8344..$83f0` (called from `$74e0` -> `$82c8`) |
| `$1bc00`/`$11c00` | 14.2% | 11.6% | the timer-C YM sample player `$1bc92+` |
| `$13a00` | 7.6% | 7.7% | the 32,000-byte window copy `$13a94` |
| `$00900` | 6.3% | 3.1% | screen/UI code |
| `$0e800` | 3.2% | 3.2% | entity/HUD code |
| `$00e00` | 2.5% | 4.5% | flip `$e0e`, ACIA, waits |
| `$07500` | 1.9% | — | the blit primitive `$7588` |
| `$17400` | 1.9% | — | pathfinding `divu` math |

The shape matches the 1990 game's profile (terrain 40-48%, window copy 8-12%) except that the
WW1's sound player is much cheaper (14.2% vs the 1990 game's 26.4% while a sample plays) and
the 1990 per-triangle `divu` setup has no WW1 equivalent (the renderer is a block-pattern
combiner — see `frameloop.md` 6a).

## 3. The user's real-hardware report [user, 2026-11-21]

> "on a stock STE, Powermonger WW2 feels about 2 frames per second vs 3-4 for Powermonger."

Corrections/notes:
- The user means the **WW1** edition (the project's game); "WW2" is a slip.
- This is the important counterweight to the emulator numbers: our map-view scene (a starting
  territory) runs 3.5-4.3 fps in Hatari, but the user's experience is **~2 fps on real
  hardware vs 3-4 for the 1990 game**. So the WW1 is plausibly *slower in the scenes that
  matter* (busier territories, more units on screen) even though the starting scene measures
  cheaper. The scene mismatch is real and the user's figures should be treated as the
  real-world baseline for the regression work.
- Consequence: a **like-for-like busy-scene measurement is required** — take a WW1 battle /
  populated-territory snapshot and compare with the 1990 game's battle (3.88 fps) and
  get_men (4.00 fps) at 8 MHz. Until then, no claim that the WW1 is or is not slower should
  be made.

## 4. What this means for the four ports

1. **Tick** — baseline 3.55-6.97 passes/s (1.96x): the biggest, best-understood win. The
   patch map is in `frameloop.md` section 3.
2. **Tooltips / keys** — the mechanisms are in `input.md`; the map-view command cells are the
   remaining map.
3. **Performance** — the sound (11-14%) and the window copy (7.6%) are direct 1990
   transpositions; the 40% renderer needs its own study (no `divu` tables to port).
4. **The user's 2 fps report** sets the bar: after the tick + sound + window copy, the
   measurable goal is the 1990 release's shape of win (fps up 20-100% at 8 MHz).
