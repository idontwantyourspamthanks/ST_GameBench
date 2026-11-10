# 25 Hz player motion for every vehicle type (p3c / p3cp), display patches per type

Author: MW2VehImpl. Evidence = raw output of the scripts in `work/vehicles_p3b/` (`vgate.py` per-tick gate, `runtype.py`, `vcmp.py`, `latency.py`, `ab2.py`, `fpsrun.py`, `skipcnt.py`, `cklist.py`, `coldboot.py`); raw logs were in `/tmp/vg/` (not kept). Anything not run is `[INFERENCE]`.
Related: `vehicles_air.md` (MW2VehAir), `vehicles_water.md` (MW2VehWater), `tick_inventory.md`, `raids.md`.

## 0. Summary (2026-11-10, final)
* `$6220 = 13` is the **Helicopter**. v1.2's `p3b_*` and `p7_skip_*` acted on the Helicopter only (section 1). They are now REMOVED (`git log`); **p3cp** replaces them for all 22 types (section 9 = the exact set to ship).
* Design: the original 5 Hz tick runs once per group of five 40 ms passes, completely unmodified (PH 1). PH 2-5 only display a pose extrapolated from the tick that just ran and refresh the view; no game logic runs in them. Group-end state is the unpatched game's by construction.
* Fixes since the first p3cp (section 2): (a) the **wave pointer** `$1dfba` (Speedboat divergence): the map-window rebuild `$1dd7e` resets the pointer to the table base without touching the phase `$1877c`, the next sim reads it, and the first p3cp rewrote it; now the end-of-tick phase AND pointer are saved at PH 2 and restored before the next PH 1; (b) **deadline-aware extra passes** (Esc one tick late): an extra pass renders only if it ends before the next PH 1 is due, so tick starts keep the original's schedule (without it PH 1 started 0-4 VBL late at 16 MHz).
* Exactness gate (section 4, A = option A vs P = p3cp, group ends, 22 types x stand / move+turn / move+turn+button, 41 ticks): 16 MHz 64/66 identical, 32 MHz 66/66 identical after reruns (see the flake note); Esc (section 5): 40/40 identical, type change verified.
* p7_skip_render (type table): 15 snapshots x flips 10/40 IDENTICAL; stop-and-go per type: 22/22 identical (section 6).
* Latency/overshoot (section 3), fps (section 7), cold boots (section 10).

## 1. Correction of the record, measured on shipped v1.2 (default set live-applied to Raids snapshots, 2 MB STE, fps over 1000 VBL)
| situation | 8 MHz | 16 MHz | p7_skip |
|---|---|---|---|
| true on foot (5) standing | 3.85 fps (13.0 VBL/frame) | 5.00 | never fires (`NUNS` 95/1000 VBL) |
| Jeep (1) standing | 4.20 | 5.00 | never |
| Helicopter (13) standing | 25.05 | 25.00 | fires (`NSKIP` 560/1000 VBL) |
| Helicopter moving | 5.30 (first measure 4.85) | 11.70 | no |
| on foot moving | 5.00 | 5.05 | no |
Documented in `tick_inventory.md` (banner), `REPORT.md` (section 4 correction, 6c, 7, 8) and `PLAN.md`.

## 2. Mechanism (p3cp, `patches/p3cp_head.s`; code from `$b8000` (below `$b8700`), NPC snapshot `$b8700-$b8ebf`, data `$b8f00`)
* Head `$31486`: real-time clock scheduler on the `tick_vbl` clock (GRP 60 units = 5 Hz, SUBT 12 = 40 ms), `TAB[type]` per-type on/off (all 1; 0 = plain option A pass; also off when `$40b6 <> 0`).
* PH 1: normal flow; hook `p3c_sim` at `$31570` only records the pose before the tick. Pre-calls, sim, post-calls, render, flip, post-flip handler as the original. PH 1's render is skipped only when a whole tick is owed (option A's rule). Keys (Esc) and the mouse are read in the pre-calls (`$50d4` -> `$1b43a` reads `$7687`; p5_ctl_x reads the accumulators in the sim), i.e. only at PH 1.
* PH 2: `cap1` = end-of-tick state into a shadow (pose + `$763e-$7648 $7652/54 $7662-$767d $53ac/ae $670a-$6711 $6780-$6791`) and the `INT` decision; NPC table snapshot; `$676e` cleared (the post-flip handler acted once at PH 1); **`wavesave`: live `$1877c` and `$1dfba` after PH 1 (`EPH`, `EPT`)**. PH 2-5: predicted pose, `$3467c $346a2 $37a62 $37afa`, `$3158c` (gauges, render, flip). The next PH 1 (and any resync) restores pose, view words, NPC table and wave phase+pointer (`fixup` -> `wavefix`).
* Overshoot limits: no prediction in a tick that changed the type, jumped (|dX|,|dY|,|dAlt| > `$1000` = map re-centre, |dHeading| > 256, |dBank|,|dPitch| > 128), ended with `$676e` (collision revert/arrival) or `$767e` (landing) set, nor in the first group after such a jump; altitude never extrapolated downwards, lean never.
* **Wave phase and pointer (Speedboat root cause).** The renderer advances `$1877c` (+8, `$1dcae`) and sets `$1dfba = $18574 + $1877c`; the sim reads the wave through the pointer (`$506e` -> `$1fd1c: movea.l $1dfba(pc),a0`). The map-window rebuild (`$31efe -> $5050 -> $1db94 -> $1dd7e: move.l a1,$1dfba` with `a1 = $18574`) resets the POINTER to the table base and leaves the phase. In option A the next tick's sim then sees phase 0 (until the next render re-derives the pointer); the first p3cp re-derived the pointer from the phase at every PH 1 (`wavetick`) and so lost that one-tick glitch. Evidence: Speedboat stand at 32 MHz, tick 2: `$1dfba` A `...74` (base) vs P `...ec` (base + `$78`), `$1877c` equal `$78`, then `$34938`, `$764c`, `$688e`, NPC words differ; after the fix 0 diffs (stand/movturn/allin x 16/32 MHz). 16 MHz stand differed only after A's own wave lag (the 16 MHz noise of the old note) and is clean too.
* **Deadline-aware extra passes (Esc/input at the original's tick).** `ACC` after the pass subtract = lateness L; an extra pass at PH k renders only if `REST <= 12*(6-k) - L`, `REST` = the longer of the last two measured extra-pass durations (measured at the next head entry from the clock; decays by 1 unit per group so a stale long value is re-probed; cleared at a resync). Measured tick starts (`e VBL` at `$1b43a`, Biplane 16 MHz): option A every 10 VBL; first p3cp 0..+4 VBL late every group; with the rule A-exact except one +1/+2 VBL probe now and then; at 32 MHz exact.
* NPC render-animation words (`+$36 +$38 +$3a` of each `$3532 + n*$42`, advanced by the renderer at `$1ce38`, read by `$33a08`) depend on the number of renders; the NPC table is restored after the extra renders. They are not game state (unpatched option A itself gives different values when started one VBL later); the gate masks them.
* p3c (`p3c_head`) differs only in showing `T_start..T_end`; it was NOT re-gated and lacks the two fixes above: not shipping.

## 3. Latency and overshoot (mouse impulse -300 counts on `$6fb6` at 10 poke phases across the tick, p5 consume-and-clear; first presented flip whose live heading differs; `latency.py orig|cand SNAP MHZ 10`, 2 MB STE; re-run after the PH 1 rewrite and both fixes)
First-change latency, mean (min-max) ms, orig (unpatched game) vs cand (p3cp + p7_skip_render + defaults); at 8 MHz / 16 MHz:
| | orig 8 | cand 8 | orig 16 | cand 16 |
|---|---|---|---|---|
| on foot | 382 (260-560) | 411 (260-620) | 231 (120-300) | 224 (120-340) |
| Jeep | 329 (200-540) | 316 (180-540) | 180 (100-240) | 196 (100-280) |
| Helicopter | 329 (240-480) | 291 (180-380) | 140 (100-180) | 187 (100-280) |
Time to 90 % of the tick's turn (cand): foot 406 / 224, Jeep 316 / 196, Helicopter 291 / 187 ms (8 / 16 MHz). First displayed frame shows 1.00 of the tick's turn in every trial. **Overshoot beyond the final heading** (extrapolated frames, max over trials, fraction of one tick's turn; mean in brackets): 8 MHz foot 0.00 (0.00), Jeep 0.00 (0.00), Helicopter 0.80 (0.71); 16 MHz foot 0.60 (0.20), Jeep 0.60 (0.33), Helicopter 0.60 (0.44). Input is read at PH 1 (the original tick, now on the original's schedule): the first visible change follows the tick as in the original; at 8 MHz (one render per group) the numbers are frame-time bound. The overshoot is the extrapolation: when a turn stops, the extra frames of that group have shown up to 0.8 of a tick step beyond the end pose, and the next PH 1 snaps back.

## 4. Exactness gates (`gate_all.py MHZ OUT` -> `runtype.py TYPE SCEN P`; A = `tick_vbl tick_head tick_render`, P = `tick_vbl p3cp_head p3c_sim p3c_render`)
Method: both runs start from the same Raids snapshot (2 MB STE) and apply their live patch set at the SAME flip (the VBL read over the fifo is published by the A run through `--sync`: the earlier harness let each run pick its own and could start A and P one logic step apart); same pokes of the input accumulators (`$6fba` forward, `$6fb6` turn, `$6fbe` button); P's ACC is poked to -48 so its first PH 1 is due at clock 60 like A's first tick; sampled at `pc=$31586` (once per tick in A and per group in P), 41 ticks; compared byte by byte over `$6600-$77ff`, NPC `$3530-$3cee`, effects, projectiles `$40b0`, HUD `$18100`, fatigue `$efa0`, odometer `$f960`, `$eb80`, `$34930`, wave `$1877c`, wave pointer `$1dfba`. Masked as render/HUD/sound scratch: `5380-53af 53c0-53ff 6776 67a6-67ff 6808 6900-695f 6a00-6eff 682a-686f 6840-6860 6f7a-6fcf 7020 7682 770c-7714 7706 71c0 77c0-77d0 18124-18140 672e-6733 7710-7750`, NPC render-animation words. Forced types (0 Tank, 4 Train, 8 Minisub, 11 Frogman, 14 Zeppelin, 16 Rocket, 20 Flying Sub) = `$6220` poked into a snapshot of another type. Scenarios: stand; move+turn (`movturn`); move+turn+right button (`allin`: bank; the left button also fires, whose render data feed the aim lists, so it is not used).
Result (raw one-line-per-run output: `GATE ...` lines, `/tmp/gate16.txt`, `/tmp/gate32.txt`, copied below as the summary):
* **16 MHz: 64 of 66 identical on the first pass.** Jeep allin differed in all ticks on the first pass (effects table `$40e4`.., A one tick off P) and was identical on both reruns. Not identical, reproducibly: **Hovercraft stand** (tick 13: A's wave phase `$1877c` stays `$30` for one tick = A skipped a render, option A is behind real time at 16 MHz with the slowest vehicle (1.8 fps at 8 MHz); `$66fe`, `$6887`, `$688b` follow) and **Zeppelin allin** (tick 34: P's phase lags one tick instead, NPC bytes `35c5 3607 3649 36cd` for one tick). Both are render-skip noise of the real-time reference (a skipped render moves the wave phase, which the sim reads); both are identical at 32 MHz.
* **32 MHz: 66 of 66 identical** after reruns: first pass 59 identical; Speedboat stand/allin, Helicopter stand, Parachute stand/movturn, Flying Boat allin differed in ALL 41 ticks on the first pass (state one logic step apart, i.e. the two runs started one flip apart); rerun twice: Speedboat stand/allin, Parachute stand/movturn, Flying Boat allin identical both times, Helicopter stand identical once and differing once. The same pair re-run gives different answers (Speedboat stand: 3 runs, 1 differing); A vs A2 (the same option-A set twice, same sync) and Speedboat stand A vs P re-run twice were identical. [INFERENCE] the flake is the harness: each Hatari gets xdotool pointer/focus events at start-up at a wall-clock time, which reach the emulated IKBD at a different frame, so a run's pre-apply game state can differ by one frame. It is never a partial difference: a run is either identical in all ticks or off by one step in all ticks.
Not run: the left button (firing), p3c.

## 5. Esc and other mode switches
* **Esc (the vehicle-exit key) is read once per tick**, in the pre-calls: `$50d4 -> jmp $1b43a` (`tst.b $7687`, then `clr.b $7687`, then by type: 5/21/11/17/16 -> `$1b6bc`/`$1b574`; otherwise the eject, type := 17 or 5, via `$32e9c`/`$3308a` in the next tick). It runs at PH 1 only (the extra passes do not call it) and there is no per-pass read to align. The first p3cp showed Esc "one tick later" for two reasons that were not mechanism bugs: (1) the harness armed the Esc pokes over the fifo after the apply, so their VBL was wall-clock dependent (a poke landing within 1 VBL of a tick start goes either way), and P's first PH 1 was due 8 VBL before A's (ACC not aligned); (2) P's PH 1 really did start 0-4 VBL late at 16 MHz (an extra render overran the group), which moves the read past a poke that A's on-time tick had already seen. Fixes: pokes are armed inside the apply file; ACC aligned; **deadline-aware extra passes** (section 2).
* Test (`esc_batch.py MHZ TYPES DVS`: `$7687` poked to `$ff` every 4 VBL for 40 VBL starting at 12/14/16/18/20 VBL after the apply flip = 5 phases around the tick start (ticks at 11/12 + 10k); A and P from the same snapshot, same flip; the tick at which `$6220` changes and the type sequence are compared, plus the full group-end diff): **40 of 40 identical** (Jeep, Biplane, Speedboat, Helicopter x 5 phases x 16 / 32 MHz): type change at the same tick in A and P and identical type sequences: Jeep 1 -> 5 (on foot), Biplane 12 -> 17 (Parachute) and later 17 -> 21 / 5 on landing, Speedboat 6 -> 5 at 16 MHz and 6 -> 21 (Swimming; boat in the sea) at 32 MHz or 6 -> 11 (Frogman) at one phase, Helicopter 13 -> 17 (Parachute) -> 5. The earliest phases (12, 14) consume the key at the first tick, so the type is already changed at sample 1. 3 of the 40 differed in every tick on the first pass (one logic step start offset, the harness flake of section 4) and were identical on rerun; the type change tick equalled A's in those three as well.
* Parachute -> Swimming and Parachute landing (`Parachute_*` runs, 43 ticks, includes the type change) identical to A (earlier gate, unchanged code path).
* Type change inside the tick, pose jumps and re-centre: `INT = 0`, the tick is shown unchanged; the next group is not predicted.

## 6. Display patches per type
* Shipped `p4_*`, `p7_cell_*`, `p7_ck_*`, `p4_hud_pfx_*` vs unpatched, flips 10 and 40 (`ab2.py`): identical for 13 of 15 vehicle snapshots. Ship and Biplane differ (pfx set, from flip 4), **but** an unpatched 8 vs 16 MHz control shows these scenes' frame N depends on real time (moving objects), and with the sim frame-locked (`tick_*` set at 16 MHz) both are IDENTICAL at flips 10 and 30: not a display bug.
* `p7_skip_render` (the former `p7_skip_render_t`, type table, all 22 types on; **proposed default, replaces the Helicopter-only v1.2 patch**): (1) pixel gate (`skip_gate.sh` -> `ab2.py`, tick-locked A set + the shipped display patches, with vs without the p7_skip set, flips 10 and 40, 16 MHz, 2 MB STE): **IDENTICAL on all 15 snapshots x 2** (30/30). (2) Stop-and-go (`skipgo.py TYPE 16`): the same two frame-locked runs, forward input poked at 30 and 230 VBL after the apply, stopped at 130 and 330, the visible 2 x 32000 B of both screen buffers hashed at EVERY flip: **22 of 22 types identical in all 40 flips** (the 15 snapshot types + Tank, Train, Minisub, Frogman, Zeppelin, Rocket, Flying Sub by forced-type pokes); one first-pass run of the Speedboat differed in all 40 flips with NO skip fired (`NSKIP` 0: the harness start-offset flake of section 4) and was identical on rerun. Skips fired in these runs (NSKIP at the end of 40 flips): Bus 19, Helicopter 21, Rocket (forced into the Helicopter cockpit) 19, all others 0 in the stop-and-go window (the stopped state drifts or has sea in view: `NSC`/`NWAV`). Standing-fps skip counts at 16 MHz (600 VBL, earlier run): Bus 361, Helicopter 360, Submarine 54; never on foot, Jeep, Truck, Crawler (sea in view), nor Biplane, Balloon, Flying Boat, Hovercraft, Ship, Swimming (the vehicle drifts). The signature already contains type, pose, view matrix, angles, fog band, units, markers; with p3cp the extra passes with an unchanged pose may skip too (the wave replay `$1dcae` is the same as a render's).
* `p4_hud_crop_*_t` (type table `1 3 6 7 9 10 12 13 15 19`; visual tradeoff, `default: no`): visible pixels lost in rows 182-199 vs the pfx set: Heli 2086 B, Bus 1094, Submarine 484, Jeep 20, Ship 14, Speedboat/Crawler/Biplane/Balloon/Hovercraft 0 (cockpit covers the band); differences confined to rows 182-199 for every enabled type; non-enabled types (Truck, on foot, Parachute, Swimming, Flying Boat) identical. Cockpit opacity of rows 182-199 from the in-RAM lists (`cklist.py`): Jeep 100 %, Truck 60, Bus 78, Speedboat 86, Crawler 100, Submarine 90, Ship 100, Biplane 100, Helicopter 67, Balloon 100, Flying Boat 62, Hovercraft 100; types 5/17/21 skip the cockpit replay (never cropped). Tank, Train, Minisub, Frogman, Zeppelin, Rocket, Flying Sub: no list measured, excluded. Crop conflicts with `p4_hud_pfx_*` (as before). A first version had a flag bug (`move.l (a7)+` before `beq`), fixed (`movem`).

## 7. fps: v1.2 vs candidate (defaults + p3cp_head + p3c_sim + p7_skip_render, crop OFF), `fpsrun.py cand SNAP MHZ stand|move`, 1000 VBL after a live apply, 2 MB STE, same host
Standing = the snapshot as is; moving = forward + turn pokes (`runtype.pokes movturn`) at the apply flip. v1.2 numbers are from the earlier measurement (`fpsrun.py v12`, 8 / 16 MHz only; the p3b patches no longer exist). The fps counts the extra predicted frames. `skips` = `p7_skip_render` NSKIP per 1000 VBL (standing).
| type | v1.2 stand 8/16 | cand stand 8 | 16 | 32 | skips/1000 VBL at 8/16/32 | v1.2 move 8/16 | cand move 8 | 16 | 32 |
|---|---|---|---|---|---|---|---|---|---|
| 5 on foot | 3.85/5.00 | 3.80 | 5.55 | 21.70 | 0/0/267 | 5.00/5.05 | 5.25 | 10.90 | 24.90 |
| 1 Jeep | 4.20/5.00 | 4.15 | 5.85 | 25.05 | 0/0/337 | 5.00/5.00 | 5.00 | 9.50 | 22.05 |
| 2 Truck | 2.95/5.00 | 2.90 | 5.20 | 10.40 | 0/0/2 | - | - | - | - |
| 3 Bus | 5.00/5.05 | 25.05 | 25.00 | 25.05 | 560/561/561 | - | - | - | - |
| 6 Speedboat | 4.05/4.85 | 4.05 | 7.60 | 17.85 | 0/0/0 | 3.85/5.00 | 3.40 | 6.30 | 16.05 |
| 7 Crawler | 5.00/5.05 | 5.25 | 10.25 | 25.05 | 0/0/113 | - | - | - | - |
| 9 Submarine | 5.00/5.00 | 4.90 | 10.00 | 25.05 | 0/0/337 | - | - | - | - |
| 10 Ship | 3.70/5.00 | 3.60 | 6.00 | 15.10 | 0/0/0 | - | - | - | - |
| 12 Biplane | 5.05/5.00 | 8.30 | 21.05 | 24.90 | 0/0/0 | 5.00/5.00 | 9.15 | 24.45 | 24.85 |
| 13 Helicopter | 25.05/25.00 | 25.00 | 25.05 | 25.00 | 560/561/561 | 5.30/11.70 | 5.15 | 10.15 | 23.65 |
| 15 Balloon | 4.50/4.50 | 10.65 | 22.30 | 22.30 | 0/0/0 | - | - | - | - |
| 17 Parachute (21 at 16/32) | 4.95/5.05 | 5.10 | 12.65 | 24.40 | 0/0/0 | - | - | - | - |
| 18 Flying Boat | 5.00/5.00 | 13.05 | 25.05 | 25.00 | 0/0/0 | - | - | - | - |
| 19 Hovercraft | 1.85/4.00 | 1.80 | 4.00 | 5.30 | 0/0/0 | - | - | - | - |
| 21 Swimming | 5.00/5.00 | 5.20 | 11.15 | 25.05 | 0/0/0 | - | - | - | - |
* Cost of the deadline rule: Helicopter moving at 16 MHz 10.15 fps now vs 11.70 for v1.2 and for the first p3cp (it draws an extra frame only when it ends before the next PH 1 is due).
* At 8 MHz a frame takes 5-14 VBL (Hovercraft 28), so there is hardly room for extra frames except in the light scenes (Biplane 8.3, Balloon 10.7, Flying Boat 13.1 standing); the walking/driving views gain from 16 MHz up (on foot 10.9, Jeep 9.5 moving at 16 MHz; 24.9 and 22.1 at 32 MHz).

## 8. Per-type table
smooth = p3cp 25 Hz pass with group-end exactness (section 4: stand / move+turn / move+turn+button, 16 and 32 MHz); skip = `p7_skip_render` fires in the standing snapshot (section 6 / 7); crop = the rejected `p4_hud_crop_*_t` table (default: no, not shipping).
| type | smooth / gate | skip | crop |
|---|---|---|---|
| 0 Tank, 4 Train, 8 Minisub, 11 Frogman, 14 Zeppelin, 16 Rocket, 20 Flying Sub | yes (forced-type pokes; exact at 16 and 32 MHz; Zeppelin allin 16 MHz = reference skip noise) | Rocket yes in the Helicopter cockpit; others not tested standing | no |
| 1 Jeep, 2 Truck, 5 on foot, 7 Crawler | yes | 32 MHz only (foot 267, Jeep 337, Crawler 113, Truck 2 per 1000 VBL); never at 8/16 (sea/NPC) | 1 7 yes, 2 5 no |
| 3 Bus | yes | yes | yes |
| 6 Speedboat | yes (the wave-pointer fix) | no | yes |
| 9 Submarine | yes | 32 MHz (337) | yes |
| 10 Ship, 12 Biplane, 15 Balloon, 19 Hovercraft | yes (Hovercraft stand 16 MHz = reference skip noise, 32 MHz identical) | no (drift) | yes |
| 13 Helicopter | yes | yes | yes |
| 17 Parachute, 21 Swimming | yes | no | no |
| 18 Flying Boat | yes | no | no |

## 9. Proposed default set and what the lead flips
Currently `default: yes` (32 patch sources + 2 HAGA file patches + floppy_copybuf): `mw2_credit p3c_render p4_grid p4_hud_pfx_fill p4_hud_pfx_replay p4_hud_pfx_ymin p4_hud_reset p4_proj_axis p4_proj_cols p4_proj_div p4_walk p4_walk_c4 p4_walk_ret p4_walk_tab p5_ctl_vbl p5_ctl_x p7_cell_cull p7_cell_pre p7_ck_enter p7_ck_exit p7_ck_obj p7_ck_poly p7_ck_tab p7_skip_enter p7_skip_gate p7_skip_scn p7_skip_wv1 p7_skip_wv2 p7_skip_wv3 tick_vbl pp_bigram_cache pp_nofade floppy_copybuf`.
**To flip (three lines `; default: no` -> `yes`): `p3cp_head`, `p3c_sim`, `p7_skip_render`.** Until then the default build has NO scheduler (unpatched timing: p3b_head is gone) and no static-frame skip. Crop (`p4_hud_crop_*`, `_t`) stays OFF. `p3c_head` (interpolated), `tick_head`/`tick_render` (option A, the gate reference), `p4_blit_*`, `sync_blip`, tests stay `no`.
Retired (deleted with `git rm`, history kept): `p3b_head p3b_pos p3b_hdg p3b_alt p3b_bank p3b_save p3b_probe p3b_alt_fix p3b_head_fix`, `p7_skip_render` (Helicopter-only; the type-table `p7_skip_render_t` took its name). Renamed: `p3b_render` -> `p3c_render` (still needed: gauge draw once per presented frame + SKIP). `p5_ctl_x` no longer reads the p3b `HOLD` word. Nothing else depended on the p3b blobs (grep over patches/ and tools/). Old scratch scripts under `work/stall`, `work/vehair`, `work/p3b_tests` still name p3b patches and need `git show` of the old files to rerun.
Blobs: p3cp_head `$b8000`+ (below `$b8700`), `$b8700` NPC snapshot, `$b8f00` data, `$b42e0` block D; p3c_render `$b4102`.

## 10. Cold boots (candidate = `build/vehp3cp`: defaults + p3cp_head + p3c_sim + p7_skip_render, crop off; `coldboot.py MACHINE`: cold boot to the Raids map, then each island via `mw2raids.enter_raid`; per-flip pose dump while turning, contact sheet `work/vehicles_p3b/cold/<machine>_<type>.png`, fps at 8/16/32 MHz after the move)
Done: **STE 1 MB (TOS 1.62) and Mega STE 4 MB (TOS 2.06, 16 MHz)**: cold boot to the map 108 s / 93 s, marker `MWPO` before and after, hook `$31570 = jsr $b8000`, head `$31486 = jsr $b8100`; on foot (5), Jeep (1), Speedboat (6), Biplane (12), Helicopter (13) all entered via the Raids map (types as wanted), no bus error. Pose per presented flip while turning: every flip carries a new pose (pose_changes = flips-1) on foot, Jeep, Biplane, Helicopter on both machines; mean flip gap STE 8 MHz 9-13 VBL, Mega STE 16 MHz 2.6 (Biplane), 5.9 (Jeep, Heli), 10.9 (foot) VBL. **Speedboat: the boat did not move during the turn window (0 pose changes in 6 / 11 flips), so smoothness of the boat was NOT shown on a cold boot** (it moved earlier; stopped/blocked). PH samples show the extra passes running (values 2-5) on Mega STE. Measured ticks/s 4.4-4.6 (target 5.0) on both, over a 400 VBL window [INFERENCE: includes a map-rebuild stall / 8 MHz frame-time bound; not investigated]. fps after the move at 8/16/32 MHz (STE): foot 11.2/25.0/25.0, Jeep 5.2/7.3/25.1, Speedboat 2.9/6.6/14.6, Biplane 1.4/19.1/23.1, Heli 5.2/19.3/25.0 (these include skip-fired stopped states); Mega STE: foot 4.0/11.3/19.1, Jeep 4.3/6.8/19.7, Speedboat 4.4/6.6/18.4, Biplane 3.8/17.6/21.3, Heli 4.4/12.2/21.3.
**NOT done: TT (`--mmu true`), plain ST, floppy STE and floppy TT cold boots** (`coldboot.py tt4|st1` and `floppy_cold.py ste|tt` are written; floppy_cold.py has never been run). No frame strip was looked at by eye (images saved only).
**Open design choice (not done): the deadline rule costs fps at saturated settings.** Standing at 16 MHz the first p3cp (extra passes ran late) gave on foot 8.25, Jeep 8.90, Speedboat 8.85, Crawler 13.85 fps; with the deadline rule 5.55, 5.85, 7.60, 10.25 (Section 7), because the machine cannot fit an extra frame between the end of PH 1 and the next tick start. A `SLACK` (allow an extra pass to end up to ~1 VBL late) would give some back at the price of 0-1 VBL tick-start jitter; not implemented or measured.

## 11. Middle ground: an extra pass may end up to 1 VBL after the next PH 1 is due (user decision)
`p3cp_head`: `SLACK = 6` clock units (1 VBL at 50 Hz) is added to the deadline budget; tuning word `SLKX` (`$b8fb2`, zero-initialised, only the gates poke it: -6 = the strict rule, +1000 = no rule). The clock grid is untouched (`ACC` keeps the due times), so a late PH 1 does not push later ticks back: measured intervals come in pairs such as 12/8 VBL, the mean stays 10.0 (foot 16 MHz: 172 ticks in 1712 VBL; option A 171 in 1700, every interval exactly 10).
fps (`fps_rules.sh`, `fpsrun.py cand`, 1000 VBL, 2 MB STE; strict / middle / none, same snapshots and pokes as section 7):
| type | scen | MHz | strict (SLKX=-6) | middle (default, SLACK 6) | none (first p3cp) |
|---|---|---|---|---|---|
| foot | stand | 8 | 3.80 | 3.80 | 3.80 |
| Jeep | stand | 8 | 4.15 | 4.15 | 4.15 |
| Speedboat | stand | 8 | 4.05 | 4.05 | 4.05 |
| Crawler | stand | 8 | 5.25 | 5.30 | 6.40 |
| Helicopter | stand | 8 | 25.05 | 25.05 | 25.05 |
| foot | stand | 16 | 5.55 | 5.95 | 8.25 |
| Jeep | stand | 16 | 5.85 | 7.60 | 8.90 |
| Speedboat | stand | 16 | 7.60 | 8.00 | 8.85 |
| Crawler | stand | 16 | 10.25 | 12.90 | 13.85 |
| Helicopter | stand | 16 | 25.05 | 25.05 | 25.00 |
| foot | stand | 32 | 21.70 | 23.20 | 23.15 |
| Jeep | stand | 32 | 25.05 | 25.00 | 25.05 |
| Speedboat | stand | 32 | 17.80 | 18.95 | 19.20 |
| Crawler | stand | 32 | 25.05 | 25.05 | 25.05 |
| Helicopter | stand | 32 | 25.05 | 25.00 | 25.05 |
| foot | move | 8 | 5.25 | 5.25 | 6.35 |
| Jeep | move | 8 | 5.00 | 5.05 | 5.25 |
| Speedboat | move | 8 | 3.40 | 3.40 | 3.40 |
| Crawler | move | 8 | 5.25 | 5.40 | 7.00 |
| Helicopter | move | 8 | 5.10 | 5.20 | 5.45 |
| foot | move | 16 | 10.90 | 12.80 | 13.70 |
| Jeep | move | 16 | 9.55 | 10.35 | 11.25 |
| Speedboat | move | 16 | 6.30 | 7.30 | 8.45 |
| Crawler | move | 16 | 13.50 | 14.75 | 15.35 |
| Helicopter | move | 16 | 10.15 | 10.30 | 11.70 |
| foot | move | 32 | 24.95 | 25.00 | 24.95 |
| Jeep | move | 32 | 22.05 | 22.45 | 22.75 |
| Speedboat | move | 32 | 16.05 | 17.20 | 17.70 |
| Crawler | move | 32 | 25.05 | 25.05 | 25.05 |
| Helicopter | move | 32 | 23.65 | 23.90 | 24.10 |
Lateness of PH 1 (`gaps.py`, 97 ticks, VBL of `$31586` minus the 10-VBL grid from tick 0; max / ticks later than 1 VBL): 16 MHz middle: foot 2/18, Jeep 4/5, Biplane 3/12, Helicopter 1/0; strict: foot 2/10, Jeep 4/1, Biplane 2/1, Helicopter 1/0; 32 MHz: at most 2 VBL in 1 tick of 97, usually 0. **The 1-VBL bound is NOT strictly guaranteed**: the clock and the pass-duration measure are VBL-quantised (measured duration = a multiple of 6 units, true value up to 6 less or more), so the knob is effectively binary (3 behaves as 0), and even the strict rule shows 2-4 VBL late ticks when PH 1 itself overruns. A hard bound would need a sub-VBL timer (e.g. the video address counter `$ff8209`); not done.
Gates with the middle ground (default build): exactness subset on foot, Jeep, Speedboat, Biplane, Helicopter x stand, move+turn x 16/32 MHz: **20 of 20 identical**. Esc batch (4 vehicles x 5 phases x 16/32 MHz = 40): type changes on the SAME tick as A in **39 of 40**; one Jeep case (dv 16, 16 MHz) shifted by one tick (A consumed it at tick 1, P at tick 2; accepted jitter); state identical in 38 of 40 (the shifted one, and one Jeep 32 MHz run with the all-ticks-differ harness flake while the type tick matched).
Tick rate: the 4.4-4.65 ticks/s of `coldboot.py` / `fpsrun.py` (hits of `$31586` over a 400-500 VBL window) is also 4.6 for the first p3cp and at 32 MHz standing, but a direct interval trace (`gaps.py`: VBL of every `$31586` hit, 800 VBL) gives 171-172 ticks in 1700 VBL for both option A and p3cp (5.0 per second, no gap > 14 VBL). [INFERENCE] the 4.6 is the window-end measurement of those two scripts (the VBL breakpoint is armed after the tick breakpoint over the fifo), not a slow world; the cold-boot figure was not re-measured with `gaps.py`. The catch-up code (clamp ACC to 3*GRP, `SKIP` = no render when another pass/tick is owed, resync after > 4*GRP) still exists in p3cp_head as in tick_head; it is not what the 4.6 shows.
