# Powermonger baseline (1 MB STE, TOS 1.62, floppy `protected.st`, Hatari 2.6.1)

Snapshots (`work/snapshots/`, all restore with `PM(snapshot=...)`; git-ignored):

| snapshot | state |
|---|---|
| `map_idle.sav` | 3D map view right after `boot_to_game`, main-loop iteration 18-33, a sample is playing |
| `get_men.sav` | overview click on the grey village, 3-sword icon, GET MEN; 16 people moving (iteration 109) |
| `battle_260/290/320/350/380.sav` | from get_men: sword icon + overview click on the village, men fighting at the village; deaths and angels rising from iteration ~290 (screenshot b320 shows angels). Number = loop iteration. |
| `map_idle_4mb.sav` | 4 MB STE, same state (see below) |

Not reached: scroll/rotate snapshot (the compass/keys exist: `$ff9a +-16` per key, `$12f56` rotation step; no snapshot taken), Mega STE (TOS 2.06), TT, Falcon (see "Blockers").
Rain: the weather dissolve (`$1abaa`, `$57fd0` season 0/2/4/6) turns on rain by itself a few hundred iterations after the start (diagonal streaks appear in the shots from iteration ~650); not a user action.

## fps and profile baseline (`work/prof/<scn>_<clk>mhz.txt` = `profile save`, `*_stages.json` = `e CycleCounter` trace)
fps = flips of `$ff8201` over 400 VBL (`h.fps(400)`).

| scenario | 8 MHz fps | VBL/frame | 16 MHz fps | VBL/frame | cycles per loop pass (8 MHz profile) |
|---|---:|---:|---:|---:|---:|
| map_idle | 2.38 | 21.1 | 6.25 | 8.0 | 3 447 000 (CycleCounter, includes a playing sample IRQ) |
| get_men (16 walkers) | 4.00 | 12.5 | 8.25 | 6.1 | 2 334 000 |
| battle_320 | 3.88 | 12.9 | 8.25 | 6.1 | 2 084 000 |

The 8 MHz STE frame budget is 160 256 cycles per VBL, so a pass costs 13-21 VBL: **2.4-4 fps at 8 MHz, 6-8 fps at 16 MHz** in every scenario. The battle at iteration 320 is NOT slower than get_men here: the cost is the number of terrain triangles and object cells in view (about 130 triangles per pass in all three) and the sprite count (16-18 % sprite blit in both), not the fighting itself. [INFERENCE] the "heavy slowdown" the user sees will be a view with many men/angels in the cells (a zoomed-out view; zoom is `$57ffc`, 1..7, 4 default) - not tested.

## Coupling numbers (JOB 1, full table)
Method: restore, `set_cpuclock`, then four absolute-VBL RAM dumps at +10/+110/+210/+310 VBL (`PM.ram_at_vbls`); diff the 512 person records (offsets 8/10 = x/z words).

map_idle 8 MHz (iters/s, movers, L1 distance per mover per pass / per emulated second):
2.14, 6, 28.0 / 60; 2.50, 6, 18.2 / 45.6; 2.00, 6, 12.0 / 24
map_idle 16 MHz: 6.34, 20, 23.6 / 150; 6.00, 20, 41.5 / 249; 6.50, 19, 35.0 / 228
get_men 8 MHz: 4.23, 18, 31.3 / 132; 4.00, 18, 33.8 / 135; 3.50, 18, 33.6 / 118
get_men 16 MHz: 8.45, 18, 24.8 / 210; 8.00, 17, 32.2 / 258; 8.50, 17, 32.6 / 277
`$57fec` (season tick) and `$2df70` (iteration) increased by the same amount in each interval (e.g. 5/5, 7/7). Per pass the step is constant (walkers move exactly 32 units per axis per pass: dx 160/5 passes, 224/7, 480/15 on the explore dev snapshot); per emulated second everything is 2.1-2.9x faster at 16 MHz. **Verdict: coupled** (frameloop.md).

Per-VBL (not per pass) items: mouse pointer redraw, sample IRQ, the VBL counter `$6f304`.

## Stage split (8 MHz, `e CycleCounter` at the loop call sites, cycles per pass, % of pass)

| stage | map_idle | get_men | battle_320 |
|---|---:|---:|---:|
| logic: `$127e6`,`$6522`,`$d322`,`$3e06` | 74 k (2.1 %) | 56 k (2.4 %) | 43 k (2.1 %) |
| VBL wait `$1870` | 13 k (0.4 %) | 95 k (4.1 %) | 104 k (5.0 %) |
| window copy `$12ce0` | 275 k (8.0 %) | 203 k (8.7 %) | 189 k (9.1 %) |
| **landscape + objects `$f898`** | **2 891 k (83.9 %)** | **1 826 k (78.2 %)** | **1 616 k (77.5 %)** |
| HUD / overview / status (`$178ae`,`$17878`,`$165b2`,`$14b62`) | 181 k (5.2 %) | 139 k (6.0 %) | 121 k (5.8 %) |
| weather dissolve `$1abaa`, UI tails | 11 k (0.3 %) | 14 k (0.6 %) | 9 k (0.4 %) |
| flip `$187a` | 0.5 k | 0.2 k | 0.3 k |
| total | 3 447 k | 2 334 k | 2 084 k |

(Interrupts - mouse pointer, sample IRQ - run inside whichever stage they hit; they are split out in hotpaths.md.)
At 16 MHz the same table: `$f898` 2 137 k / 1 617 k / 1 444 k, window copy 198 k / 181 k / 178 k, VBL wait 30 k / 90 k / 114 k.

## Cold-boot log (acceptance)
* run 1 (`/tmp/pm_boot1.py`): name 80 s, options 86 s, chart 114 s, protection 157 s (answer type 1 value 128), 3D view 203 s.
* run 2 (`/tmp/pm_snaps1.py`): name 80, options 86, chart 114, protection 154 (type 1 value 177), 3D view 202 s -> `map_idle.sav`, `get_men.sav`.
* run 3 (4 MB, below).
Restores: map_idle (iteration 33 on restore, fps 2.2 at 250 VBL), get_men, battle_*, all measured above from fresh restores.

## 4 MB
See the end of this file (appended when the 4 MB boot finished).

## Blockers (not reached)
* **Mega STE, TOS 2.06**: cold boot (`PM(machine='megaste', tos=TOS['2.06'])`) stayed on a black screen with the A: LED on for more than 8 minutes (status bar "RGB 60 Hz"); the name prompt never appeared, so no snapshot. I killed it. Not tried: forcing 50 Hz, `--fastfdc`, a different TOS. So the Mega STE 8 vs 16 MHz comparison was done on the STE with `--cpuclock 16` only.
* **TT (TOS 3.06) and Falcon (TOS 4.04)**: not booted (only EmuTOS-era images are supported by the harness for them per its docs, and the floppy loader already failed on the Mega STE). No fps/world-rate numbers.

## 4 MB (appendix)
Third cold boot succeeded on `PM(memsize_kb=4096)`: name 80 s, options 86, chart 114, protection 160 (type 1, value 215), 3D view 204 s; snapshot `map_idle_4mb.sav` at iteration 18. fps over 300 VBL at 8 MHz: **2.33** (14 flips), the same as 1 MB (2.38): memory size does not change the game. Restore check below in the final report.
