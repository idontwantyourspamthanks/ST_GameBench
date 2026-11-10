# 25 Hz player motion for every vehicle type (p3c / p3cp), display patches per type

Author: MW2VehImpl. Evidence = raw output of the scripts in `work/vehicles_p3b/` (`vgate.py` per-tick gate, `runtype.py`, `vcmp.py`, `latency.py`, `ab2.py`, `fpsrun.py`, `skipcnt.py`, `cklist.py`, `coldboot.py`); raw logs were in `/tmp/vg/` (not kept). Anything not run is `[INFERENCE]`.
Related: `vehicles_air.md` (MW2VehAir), `vehicles_water.md` (MW2VehWater), `tick_inventory.md`, `raids.md`.

## 0. Summary
* `$6220 = 13` is the **Helicopter**. The shipped v1.2 `p3b_*`, `p7_skip_*` (and the default-off `p4_hud_crop_*`) act on the Helicopter only; every other mode, true on foot included, is plain 5 Hz and `p7_skip` never fires for it (section 1).
* New, all `default: no`: **p3cp** (`p3cp_head.s` + `p3c_sim.s` + `p3b_render.s`) = the user's predict-ahead variant, and **p3c** (`p3c_head.s`, interpolated alternative, same sim hook). Both give 25 Hz player motion for **all 22 types**. Design: the original 5 Hz tick runs once per group of five 40 ms passes, completely unmodified (PH 1), so group-end state is the unpatched game's by construction, including the parts that cannot be split exactly (parachute fall, speed ramp, probes, derivative/integrator selectors, fatigue). The other passes only display a pose (p3cp: `T_end + (T_end - T_start)*(PH-1)/5`; p3c: `T_start + (T_end - T_start)*j/5`) and refresh the view; no game logic runs in them.
* Per-type exactness gate (section 4): 77 type x scenario runs at 16 MHz; 66 identical first time, the other 11 are explained (A render-skip noise, resolved at 32 MHz, section 4.3).
* Latency (section 3): p3c/p3cp add no input lag against the shipped p3b. Predict reaches 90 % of a tick's turn up to 200 ms sooner at 16 MHz and snaps back 0.8 of a tick step when motion stops.
* The two v1.2 defects (bank coefficients in `p3b_alt`; sea wave phase per rendered frame) are fixed in `p3b_alt_fix.s` / `p3b_head_fix.s` and, by construction, in p3c/p3cp. The two p3b fixes were assembled (`mw2patch live` OK) but their per-tick gate run **hung and was not completed**: untested.
* **Not done:** the cold boots (STE 1 MB, Mega STE 16 MHz, TT `--mmu true`, plain ST) were NOT run (`work/vehicles_p3b/coldboot.py` and `build/vehp3cp` exist, never executed); the real-key Esc test is inconclusive (section 5).

## 1. Correction of the record, measured on shipped v1.2 (default set live-applied to Raids snapshots, 2 MB STE, fps over 1000 VBL)
| situation | 8 MHz | 16 MHz | p7_skip |
|---|---|---|---|
| true on foot (5) standing | 3.85 fps (13.0 VBL/frame) | 5.00 | never fires (`NUNS` 95/1000 VBL) |
| Jeep (1) standing | 4.20 | 5.00 | never |
| Helicopter (13) standing | 25.05 | 25.00 | fires (`NSKIP` 560/1000 VBL) |
| Helicopter moving | 5.30 (first measure 4.85) | 11.70 | no |
| on foot moving | 5.00 | 5.05 | no |
Documented in `tick_inventory.md` (banner), `REPORT.md` (section 4 correction, 6c, 7, 8) and `PLAN.md`.

## 2. Mechanism (p3cp, `patches/p3cp_head.s`; blob `$b8000-$b86xx`, NPC snapshot `$b8700`, data `$b8f00`)
* Head `$31486`: real-time clock scheduler as p3b_head (GRP 60 = 5 Hz, SUBT 12 = 40 ms), `TAB[type]` per-type on/off (all 1; 0 = plain option A pass; also off when `$40b6 <> 0`).
* PH 1: normal flow; hook `p3c_sim` at `$31570` only records the pose before the tick. Pre-calls, sim, post-calls, render, flip, post-flip handler as the original. PH 1's render is skipped only when a whole tick is owed (option A's rule), so the render data the next tick's pre-calls read is option A's.
* PH 2: `cap1` = end-of-tick state (after the whole of PH 1) into a shadow (pose + `$763e-$7648 $7652/54 $7662-$767d $53ac/ae $670a-$6711 $6780-$6791`) and `INT` decision; NPC table snapshot; `$676e` cleared (the post-flip handler acted once at PH 1). PH 2-5: predicted pose, `$3467c $346a2 $37a62 $37afa`, `$3158c` (gauges, render, flip). Next PH 1 restores pose, view words and NPC table from the snapshots.
* Overshoot limits: no prediction in a tick that changed the type, jumped (|dX|,|dY|,|dAlt| > `$1000` = map re-centre, |dHeading| > 256, |dBank|,|dPitch| > 128), ended with `$676e` (collision revert/arrival) or `$767e` (landing) set, nor in the first group after such a jump; altitude never extrapolated downwards, lean never.
* Wave phase: the head writes `$1877c/$1dfba` itself, once per tick before the pre-calls, and again before every extra render (the original adds +8 per render and the sim reads it through `$506e`).
* NPC render-animation words (`+$36 +$38 +$3a` of each `$3532 + n*$42`, advanced by the renderer at `$1ce38`, read by `$33a08`) depend on the number of renders; the NPC table is restored after the extra renders. They are not game state: unpatched option A itself gives different values when started one VBL later (checked, ship), so the gate masks them.
* p3c differs only in showing `T_start..T_end` and running the post-calls at PH 5 (forced PH 5 render unless a whole tick is owed). p3c was gated before the last fixes (NPC snapshot, `$676e` withholding) only on foot/Jeep/Heli/Speedboat/Biplane; **re-gate it before use**.

## 3. Latency (mouse impulse, p5 consume-and-clear, 10 poke phases across the tick; first presented flip whose live heading differs; `latency.py`)
First-change latency, mean ms, 8 / 16 MHz: Helicopter orig 358/162, p3b 264/178, p3c 222/149, p3cp 278/180; on foot orig 435/212, p3c 407/196, p3cp 402/260; Jeep orig 332/178, p3c 302/207, p3cp 316/209. Time to 90 % of the tick's turn (p5 impulse): Helicopter p3b 502/384, p3c 511/380, p3cp 278/180; on foot p3c 412/296, p3cp 402/260; Jeep p3c 318/300, p3cp 316/209. Max overshoot beyond the final heading: p3b/p3c 0.00, p3cp 0.80 (of one tick's turn). Input is read at PH 1 in every design, so the first visible change is the same; p3cp shows the full tick at PH 1 instead of 1/5 of it. At 8 MHz (about one render per group) all variants are frame-time bound. (Numbers measured with the earlier p3cp that ran the tick at PH 5; the PH 1 version is the same in the metric above by construction but was not re-measured.)

## 4. Exactness gates (`runtype.py TYPE SCEN P`, A = `tick_vbl tick_head tick_render`, P = `tick_vbl p3cp_head p3c_sim p3b_render`)
Method: both runs start from the same Raids snapshot at the same flip with the same pokes of the input accumulators (`$6fba` forward, `$6fb6` turn, `$6fbe` button), sampled at `pc=$31586` (once per tick in A and per group in P), 41 ticks, 16 MHz; compared byte by byte over `$6600-$77ff`, NPC `$3530-$3cee`, effects, projectiles `$40b0`, HUD `$18100`, fatigue `$efa0`, odometer `$f960`, `$eb80`, `$34930` (terrain/sea probes), wave `$1877c`. Masked as render/HUD/sound scratch (writers checked by xref): `$5380-53af 53c0-53ff 6776 67a6-67ff 6808 6900-695f 6a00-6eff 682a-686f 6840-6860 6f7a-6fcf 7020 7682 770c-7714 7706 71c0 77c0-77d0 18124-18140 672e-6733 7710-7750`, NPC render-animation words. Forced types (0 Tank, 4 Train, 8 Minisub, 11 Frogman, 14 Zeppelin, 16 Rocket, 20 Flying Sub) = `w $6220` into the Jeep / Submarine / Biplane / Helicopter / Flying Boat snapshot (no cockpit of their own).
Scenarios: stand; move+turn; move+turn+right button (bank). Result: **identical for all 22 types** at 16 MHz except: Bus allin, Train stand, Hovercraft x3, Zeppelin allin, Speedboat stand/movturn, Tank movturn (11 runs). Re-run at 32 MHz: Bus allin, Train stand, Hovercraft stand/movturn/allin, Zeppelin allin, Tank movturn **identical**. Cause of the 16 MHz noise: option A itself skips a render (wave phase `$1877c` of A lags P at the first differing tick), i.e. the reference is not deterministic. Open: Speedboat stand and movturn at 32 MHz differ at tick 2 only (wave-aware heights `$34938`, view words, then the speed ramp `$688e` for 10 ticks); at 16 MHz movturn is identical and stand differs only after A's wave phase lags (tick 26+). Cause not isolated (first group of A vs P).
Left-button/firing scenarios were not used for the bank test (the buttons also fire: render data feeds the aim lists), right button only.
Bank-coefficient freeze and wave phase are inside the by-construction argument (the sim runs unmodified at PH 1); the shipped p3b_alt bug itself was reproduced by MW2VehAir (25/25 groups).

## 5. Mode switches
* Parachute -> Swimming and Parachute landing (`Parachute_*` runs, 43 ticks, includes the type change): identical to A.
* Type change inside the tick, pose jumps and re-centre: `INT = 0`, the tick is shown unchanged; the next group is not predicted.
* Esc by poking the key table (`$7687`, held 40 VBL) at 4 phases: Jeep identical in all 4 (**but the type change was not verified**: `$6220` was not in the dump then); Biplane (-> Parachute 17) reaches type 17 one tick later in P than in A in all 4 phases (A tick 3, P tick 4: the key is consumed at a different pre-call because pass start times differ), after which the NPC histories differ even with a one-tick shift. So: no crash, no stuck state, **exactness across an Esc is not shown**.

## 6. Display patches per type
* Shipped `p4_*`, `p7_cell_*`, `p7_ck_*`, `p4_hud_pfx_*` vs unpatched, flips 10 and 40 (`ab2.py`): identical for 13 of 15 vehicle snapshots. Ship and Biplane differ (pfx set, from flip 4), **but** an unpatched 8 vs 16 MHz control shows these scenes' frame N depends on real time (moving objects), and with the sim frame-locked (`tick_*` set at 16 MHz) both are IDENTICAL at flips 10 and 30: not a display bug.
* `p7_skip_render_t` (type table, all types on): identical vs the display base on all 15 snapshots at flips 10/40 (tick-locked, 16 MHz). It fires (16 MHz standing, 600 VBL): Bus 361 skips, Helicopter 360, Submarine 54; never on foot, Jeep, Truck, Crawler (sea in view: `NWAV`, the wave moves every 5 Hz tick), nor Biplane, Balloon, Flying Boat, Hovercraft, Ship, Swimming (the vehicle drifts: `NSC`). Transition (stop-and-go) was not re-tested per type; the signature already contains type, pose, view matrix, angles, fog band, units, markers.
* `p4_hud_crop_*_t` (type table `1 3 6 7 9 10 12 13 15 19`; visual tradeoff, `default: no`): visible pixels lost in rows 182-199 vs the pfx set: Heli 2086 B, Bus 1094, Submarine 484, Jeep 20, Ship 14, Speedboat/Crawler/Biplane/Balloon/Hovercraft 0 (cockpit covers the band); differences confined to rows 182-199 for every enabled type; non-enabled types (Truck, on foot, Parachute, Swimming, Flying Boat) identical. Cockpit opacity of rows 182-199 from the in-RAM lists (`cklist.py`): Jeep 100 %, Truck 60, Bus 78, Speedboat 86, Crawler 100, Submarine 90, Ship 100, Biplane 100, Helicopter 67, Balloon 100, Flying Boat 62, Hovercraft 100; types 5/17/21 skip the cockpit replay (never cropped). Tank, Train, Minisub, Frogman, Zeppelin, Rocket, Flying Sub: no list measured, excluded. Crop conflicts with `p4_hud_pfx_*` (as before). A first version had a flag bug (`move.l (a7)+` before `beq`), fixed (`movem`).

## 7. fps, v1.2 vs candidate (default set - p3b motion + p3cp + p7_skip_render_t), standing, 8 / 16 MHz (`fpsrun.py`)
on foot 3.85/5.00 -> 3.80/8.25; Jeep 4.20/5.00 -> 4.15/8.90; Truck 2.95/5.00 -> 2.90/6.35; Bus 5.00/5.05 -> 25.05/25.00; Speedboat 4.05/4.85 -> 4.35/8.85; Crawler 5.00/5.05 -> 6.40/13.85; Submarine 5.00/5.00 -> 4.90/13.85; Ship 3.70/5.00 -> 3.60/8.15; Biplane 5.05/5.00 -> 10.15/22.25; Helicopter 25.05/25.00 -> 25.05/25.05; Balloon 4.50/4.50 -> 12.45/22.30; Parachute(Swimming at 16) 4.95/5.05 -> 5.75/14.25; Flying Boat 5.00/5.00 -> 14.60/25.05; Hovercraft 1.85/4.00 -> 1.80/4.00; Swimming 5.00/5.00 -> 6.05/13.50. Moving (forward+turn): on foot 5.00/5.05 -> 6.30/13.70; Jeep 5.00/5.00 -> 5.25/11.20; Speedboat 3.85/5.00 -> 3.65/8.45; Biplane 5.00/5.00 -> 10.70/24.65; Helicopter 5.30/11.70 -> 5.50/11.70. The cand fps counts the extra predicted frames; at 8 MHz heavy scenes are render bound (about 1 render per group) and gain nothing, the Speedboat/Hovercraft lose 5 % to the extra bookkeeping.

## 8. Per-type table
smooth = p3cp 25 Hz pass with group-end exactness (section 4); crop = in the `_t` table; skip = `p7_skip_render_t` fires in the standing snapshot.
| type | smooth / gate | skip | crop |
|---|---|---|---|
| 0 Tank, 4 Train, 8 Minisub, 11 Frogman, 14 Zeppelin, 16 Rocket, 20 Flying Sub | yes (forced-type pokes; exact, Tank/Train/Zeppelin at 32 MHz) | not tested standing | no |
| 1 Jeep, 2 Truck, 5 on foot, 7 Crawler | yes | no (sea/NPC) | 1 7 yes, 2 5 no |
| 3 Bus | yes (32 MHz) | yes | yes |
| 6 Speedboat | yes at 16 MHz; tick-2 transient at 32 MHz (open) | no | yes |
| 9 Submarine | yes | partial | yes |
| 10 Ship, 12 Biplane, 15 Balloon, 19 Hovercraft | yes (Hovercraft 32 MHz) | no (drift) | yes |
| 13 Helicopter | yes | yes | yes |
| 17 Parachute, 21 Swimming | yes (landing/dive transition identical) | no | no |
| 18 Flying Boat | yes | no | no |

## 9. Patch files and gates for the lead
New (all `default: no`): `p3cp_head.s`, `p3c_head.s`, `p3c_sim.s` (shared hook), `p3b_alt_fix.s`, `p3b_head_fix.s`, `p7_skip_render_t.s`, `p4_hud_crop_{clip,fill,replay}_t.s`. Sets: p3cp = `tick_vbl p3cp_head p3c_sim p3b_render` (+ p5, p4, p7); do not mix with `p3b_pos/hdg/alt/bank/save/probe/head`. Blobs: `$b8000-$b8ec0`, data `$b8f00`; crop blobs `$b4d00/$b4e00/$b4540`. `mw2patch.py build --only` of the candidate set (`/tmp/cand_names.txt` list in section 7) assembled and verified. Not yet run: cold boots (STE 1 MB, Mega STE 4 MB 16 MHz, TT `--mmu true`, plain ST), floppy build, p3b_fix gate, p3c re-gate, a post-fix p3cp latency re-run, Esc exactness.
