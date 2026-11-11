# Midwinter 2 enhanced: how it was done

This is a plain-English account of the work on *Midwinter 2: Flames of Freedom* (Atari ST, PP's 2014 hard-disk version). It covers what was changed, why, what the original code was doing at each point we changed, and what each change achieved. The detailed evidence (disassembly, measurements, test logs) is in `work/notes/`. The patch sources are in `patches/`.

## What's new (2026-11-11)

- **Smooth motion in all 22 vehicle types and on foot** (`p3cp_head` + `p3c_sim`), replacing v1.2's Helicopter-only scheme: the game's own 5 steps per second are unchanged and identical to the original's at every step; the view is redrawn between the steps at an extrapolated pose, as often as the machine manages (on foot / Jeep moving: 5 fps at 8 MHz, about 11-13 at 16 MHz, about 22-25 at 32 MHz). An extra frame is only drawn if it ends at most one 50 Hz frame after the next real step is due, so Esc and the mouse are read at the original's moments.
- **Static-frame skip for every vehicle type** (`p7_skip_render`, was Helicopter-only): standing still, the view is only redrawn when something in it changes.
- World speed is exactly 5.0 steps per second on every machine tested: STE 8 MHz, plain ST, Mega STE 16 MHz, TT 32 MHz (direct per-step trace on cold boots).
- Cold boots verified on HD (STE, ST, Mega STE, TT with `--mmu true`) and floppy (STE, TT): section 4a.

## 1. Starting point

There is no source code: only the compiled 68000 program inside PP's hard-disk conversion. PP's package contains:

| File | Role |
|---|---|
| `RUNME.TOS` | PP's loader, a compressed program that unpacks itself. |
| `HAGA` | PP's hardware-detection program, which then stays in memory as a small **disk service**. |
| `FILES/FFA`–`FFE` | Raw images of the original floppies: game disks A, B and C, plus the campaign disk and the personnel disk. |

So every change is a **patch**: replacing a few bytes of the game's machine code in memory with a jump to new code that we wrote.

### How we worked
- Hatari ran headless on a hidden virtual display. A script drove the mouse and keyboard, took screenshots, saved and restored complete machine states ("snapshots"), and read the CPU profiler.
- We found where the time goes by profiling, then read the machine code of the hot spots and wrote up what each routine does (`work/notes/`).
- Every change had to pass gates before it was switched on:
  - **Identical-picture test:** restore a snapshot, apply the patch, let the game run N frames, then compare both screen buffers byte for byte against the unpatched game at the same frame.
  - **Speed and correctness:** cycle counts or frame rates, and world speed at 8 MHz and at 16 MHz.
  - **Cold boot:** a full start of the patched game, from the desktop into the 3D world, on a 1 MB STE and a 4 MB Mega STE (TOS 2.06). Some steps were also run on ST, Mega ST and TT/Falcon (EmuTOS).

Baseline: the unpatched game managed **about 4 frames per second** on an 8 MHz STE. Its world ran **2.3× faster** when the CPU was doubled to 16 MHz.

## 2. Getting our code into the game (the patch system)

`tools/mw2patch.py`, `patches/core.s`, `patches/README.md`.

**How the original loads.**
1. RUNME unpacks itself and loads HAGA.
2. It loads the game's boot program from disk A, which loads the two big code files.
3. PP's own little patcher, which applies his bug fixes and copy-protection bypass, then jumps into the game.
4. Later, the game loads more code and data from disk B/C through its own loader, and PP's HAGA service reads the image files for it in 200 KB chunks.

**What we added.**
- **A 32 KB block of our own code and data**, carried inside RUNME and copied to unused RAM at `$B3000` before the game starts. That area was proven unused at every stage of the game, on 1 MB and 4 MB machines.
  - Making RUNME bigger shifts its uninitialised-data area. Four instructions in RUNME reached that area by a position-relative offset, which stops working past about 8 KB of growth. Each was rewritten to read the address from a small pointer table instead, keeping the same 4-byte size.
- **A boot trampoline** in place of the last instruction of PP's patcher (its jump into the game). It checks that every patch site still holds exactly the original bytes the tool expects. If all match, it applies them all and writes the marker `MWPO` at `$B2FF8`. If any differ, it applies none and writes `MWPF`. Then it jumps into the game as before.
- **A load hook** for code that arrives later from disk B. The game's per-file load routine has a single "success" exit, and that exit was replaced with a jump to our code, which applies any patches belonging to the file just loaded.
  - It must be a *jump*, not a subroutine call: the original exit unstacks saved registers, and an extra return address on the stack made it crash.
- **Patches to PP's HAGA service**, made to the HAGA file itself. It moves in memory depending on RAM size, so the patches have to be position-independent code.

**Floppy version.** The same patches also go onto a bootable copy of disk A. Our code is stored as an extra file on spare tracks. A 32-byte addition to the game's own boot loader loads it and starts it before the game runs. A floppy boot never runs PP's patcher, so the trampoline also applies PP's security-check bypass itself.

## 3. Fixes to PP's loader

| Change | What PP's code did there | Why it was a problem | What we did | Result |
|---|---|---|---|---|
| `pp_nofade` | Every 200 KB disk read faded the whole palette to grey and back, as a "loading" indicator. | One screen change does many reads, so you saw a string of grey flashes, and each fade took about 0.5 s. | The two read routines skip the fade; the restore step becomes a no-op. | No flashing. Disk time per screen change roughly halved (349 → 173 frames to the Personnel screen). |
| `pp_bigram_cache` | On machines with 4 MB or more, PP's service switched to reading each whole 720 KB disk image into one buffer starting at `$81000`. | That buffer runs to `$135000` and overwrote our code at `$B3000`, so the patched game hung on the title (it was found on your MiSTer Mega STE). | One branch changed so 68000 machines with ≥4 MB use the same 200 KB chunks as smaller ones. TT/Falcon, which put their buffer elsewhere, are unchanged. | Boots at 1, 2, 4, 8 and 14 MB. Loading at 4 MB is a few seconds slower than the unpatched original, but still faster overall because of `pp_nofade`. |
| `floppy_copybuf` (floppy only) | The campaign-disk copy used an 80-track-side buffer from `$80000`. | It covered our code area on the floppy version. | Halved the buffer to 40 track-sides. | Our code survives campaign creation. Copying needs more passes; Hatari couldn't complete a full copy for an unrelated write-back reason. |

## 4. Making game speed independent of frame rate

`patches/tick_vbl.s`, `p3cp_head.s`, `p3c_sim.s`, `p3c_render.s`; notes `simtiming.md`, `frameloop.md`, `tick_inventory.md`, `vehicles_p3b.md`.

**What the original does.** The main loop at `$31486` runs the game logic once:
- moving the player,
- running the other units,
- ticking the clock (one game minute every 33 passes).

Then it draws the 3D view once and flips screens. Nothing measures real time: each pass moves the world a fixed step. So the faster the machine draws, the faster the world runs. At 16 MHz everything moved 2.3× faster, and any speed-up we made to drawing would have made the game run faster too.

**What we did, in two layers.**
1. **A fixed logic rate** (`tick_vbl`, plus the scheduler at `$31486`).
   - We added a real-time clock: a counter bumped 50 times a second by the screen interrupt. The game's own counters were unusable, because it clears one every frame and the other wraps at 6.
   - At the top of the loop we now run the logic exactly 5 times a second of real time. If the machine is ahead, it waits. If it falls behind, it skips drawing a frame to catch up, limited to 3 steps. After a long gap, such as returning from a menu, it resynchronises instead of fast-forwarding.
2. **Smooth motion in every vehicle** (`p3cp_head`, predict-ahead; it replaces v1.2's Helicopter-only `p3b_*`, now removed).
   - A full 25 steps per second would have cost 88% more CPU, because every unit's logic is expensive. Instead the original 5 Hz step runs once per group of five 40 ms passes, completely unchanged. The other four passes of the group redraw the view at a pose extrapolated from the step that just ran (the next step is assumed to repeat it), without running any game logic. Before the next real step the pose, view state, unit table and sea-wave state are put back, so the world at every 1/5-second checkpoint is exactly the original game's.
   - This works for all 22 vehicle types, including the ones whose movement cannot be cut into fifths exactly (the parachute fall, speed ramps, the water probes). Moving, turning and the walking view therefore redraw as often as the machine can manage instead of 5 times a second.
   - An extra frame is drawn only if it will be finished before the next real step is due, so the keys and mouse are read at the original's 5 Hz moments (Esc takes effect on the same step as in the unpatched game).
   - The collision check runs once per real step, as before. When the vehicle stops, or turns back, the extra frames of that group may have shown up to 0.8 of one step beyond the final position, and the next real step snaps back (the measured overshoot is 0 at 8 MHz on foot and in the Jeep, up to 0.6-0.8 of a step in the Helicopter).

**Result.**
- World speed is the same at 8 and 16 MHz, and on TT/Falcon (about 26-28 units/s everywhere), and at 50 and 60 Hz (5.00 ticks/s, `mw2tick.py rate`).
- At every 1/5-second checkpoint, the player's position, heading, bank, altitude, the unit/effect tables, HUD state, clock, RNG and the terrain/sea probes are identical to the original game's step for step: 22 vehicle types x standing / move+turn / move+turn+button, 41 steps each, 16 and 32 MHz (section 4a).
- Redraw rate (fps) of the candidate, standing / moving, 8 / 16 / 32 MHz: see section 4a.

**Correction (2026-11-10): v1.2 smoothed the Helicopter only.** `$6220` is a 0-based vehicle index (Tank 0, Jeep 1, Truck 2, Bus 3, Train 4, on foot 5, Speedboat 6, Crawler 7, Minisub 8, Submarine 9, Ship 10, Frogman 11, Biplane 12, Helicopter 13, ...). v1.2's scheduler, `p7_skip_render` (and the optional `p4_hud_crop_*`) tested `cmpi.w #13,$6220`, and 13 is the Helicopter: the snapshots earlier notes called "on foot" were helicopter cockpits. Every other vehicle, including true on foot, ran the plain 5 Hz path. Measured on v1.2 (2 MB STE, fps over 1000 VBL; `work/vehicles_p3b/fpsrun.py`):

| v1.2 situation | 8 MHz | 16 MHz | p7_skip |
|---|---|---|---|
| true on foot (type 5), standing | 3.85 fps (13.0 VBL/frame) | 5.00 fps | never fires |
| Jeep (1), standing | 4.20 fps | 5.00 fps | never |
| Helicopter (13), standing | 25.05 fps | 25.00 fps | fires (560 skips per 1000 VBL) |
| Helicopter, moving | 5.30 fps | 11.70 fps | not while moving |
| true on foot, moving | 5.00 fps | 5.05 fps | no |

Two further defects of the shipped p3b were found: `p3b_alt` used the sin/cos of the sub-pass bank instead of the previous tick's (with a mouse button held, the Helicopter's altitude and speed differed from the 5 Hz game in 25 of 25 groups), and the sea wave phase (advanced by every rendered frame, read by the player sim) made the world result over water depend on the frame rate. p3cp has neither: its sim runs unmodified once per group and the wave phase and wave pointer are restored per group.

### 4a. Type-independent 25 Hz player motion (`p3cp`; shipped default since 2026-11-11)
Details and raw gate output: `work/notes/vehicles_p3b.md`.
- **Exactness.** Group-end state equal to the 5 Hz reference (option A) for all 22 types x stand / move+turn / move+turn+button: 16 MHz 64 of 66 runs identical (the two others are the reference itself skipping a render: Hovercraft standing, Zeppelin with all inputs; both identical at 32 MHz), 32 MHz 66 of 66 after reruns (a few first-pass runs started one step apart in the test harness and passed on rerun).
- **Esc and the other keys** are consumed on the same step as in the original: 40 of 40 runs (Jeep -> on foot, Biplane -> Parachute, Speedboat -> Swimming/on foot, Helicopter -> Parachute; 5 phases around the step start; 16 and 32 MHz), with the type change verified.
- **Speedboat.** The only real divergence found was the sea wave pointer: the game's map-window rebuild resets the pointer (not the phase) and the next step reads it; p3cp now saves and restores both.
- **Input latency** (first visible change after a mouse impulse, mean, 8 / 16 MHz): on foot 411 / 224 ms (original 382 / 231), Jeep 316 / 196 (329 / 180), Helicopter 291 / 187 (329 / 140).
- **Redraw rate**, candidate, 1000 VBL, 2 MB STE, standing: on foot 3.8 / 5.6 / 21.7 fps at 8 / 16 / 32 MHz; Jeep 4.2 / 5.9 / 25.1; Biplane 8.3 / 21.1 / 24.9; Helicopter 25.0 / 25.1 / 25.0; Speedboat 4.1 / 7.6 / 17.9; Bus 25.1 / 25.0 / 25.1. Moving: on foot 5.3 / 10.9 / 24.9; Jeep 5.0 / 9.5 / 22.1; Biplane 9.2 / 24.5 / 24.9; Helicopter 5.2 / 10.2 / 23.7; Speedboat 3.4 / 6.3 / 16.1 (all 15 vehicle types: `work/notes/vehicles_p3b.md` section 7). Cost of keeping the steps on the original's schedule: the Helicopter moving at 16 MHz draws 10.2 fps against v1.2's 11.7. At 8 MHz a frame takes 5-14 VBL, so the extra frames can hardly be drawn; the gain there is mainly in the types with light scenes.
- **Cold boots (2026-11-11, `work/notes/vehicles_p3b.md` section 12):** HD on STE 1 MB, plain ST (TOS 1.04) 1 MB, Mega STE 4 MB (16 MHz) and TT with `--mmu true` (32 MHz), floppy on STE 1 MB and TT `--mmu true`: `MWPO`, on foot / Jeep / Helicopter entered (floppy: Lobos Helicopter, Esc -> Parachute -> on foot), no bus error. World rate by a direct per-step trace: 4.98-5.05 steps/s on every machine and vehicle (the 4.4-4.65 printed by the earlier test scripts was a measurement artefact: a stray log line counted as a step, and a fixed 50 Hz divisor on the 60 Hz machines). On HD, every presented frame while moving and turning carries a new pose (e.g. TT: 104 flips, 103 new poses; plain ST: 24 flips, 23 new poses); the contact sheets show steady motion with no tearing or flicker.

## 5. Direct controls

`patches/p5_ctl_*.s`; notes `controls.md`, `controls_joystick_check.md`, `p5_controls.md`.

**What the original does.** The keyboard interrupt routine adds every mouse movement into two running totals, at `$6fb6` (sideways) and `$6fba` (forward/back). Nothing ever resets them. The steering code reads the sideways total as a turn rate, so:
- a mouse nudge left keeps you turning until you nudge it back;
- the joystick and the numeric keypad feed the same total through a ramp that accelerates while held and stays non-zero when released.

That is why it felt like pushing a yoke rather than steering. (An early study note claimed joystick steering was unused code. A live test proved it wrong.)

**What we did.** We replaced the code that reads the sideways total, at `$34152`, in two parts:
- **Mouse:** the turn this step is proportional to the mouse movement since the last step, and the total is then cleared. No movement means no turn.
- **Joystick and keys:** a hook in the 50 Hz interrupt (`$262c8`) counts how long left or right was held during the step. The turn is a constant rate for that time, and zero when released.

Both rates are set in `p5_ctl_x.s` (`MOUSE_GAIN`, `YAW_PCT`). Forward/back (throttle) and nose up/down are unchanged.

**Result.** Turns start and stop with the input in all three control modes. The turn rate is the same at any CPU speed, because it is tied to the logic rate.

## 6. Faster drawing (identical picture)

All of these were checked to produce byte-identical screens.

### 6a. Leaner versions of the hottest routines
| Patch | What the original did | What changed | Saving |
|---|---|---|---|
| `p4_grid` (`$1d768`) | Every frame, a loop cleared two fields in each of the 1024 terrain-cell records (16 bytes each) and wrote a checkerboard bit. It cost 86 cycles per record, with a full loop step for each one. | The loop is unrolled per row, and the alternating bit is precomputed. | 28 cycles per record, about 3% of a frame |
| `p4_proj_cols` (`$3c02a`) | Rotating object vertices repeated 6 multiplications per coordinate, when 4 of them gave the same answer every time. | The repeated sums are worked out once. | About 0.7% |
| `p4_proj_div` (`$200ce`) | Map-marker positions were divided by a scale that is always 512, using the 68000's slow divide (about 150 cycles). | A shift with correct rounding is used, with the original divide kept as a fallback if the scale ever differs. | About 0.75% |
| `p4_proj_axis` (`$3bfa2`) | Every vertex went through a general 3×3 rotation, even when the rotation was a simple axis-aligned one. | Fast paths for axis-aligned and part-zero rotations. | About 0.8% |
| `p4_walk*` (`$3c5e2`, `$3c5c4`) | The polygon edge-walker set up each edge by saving all 15 registers and doing a multiply by 320 (`mulu #320`). | It saves only the 8 registers actually needed and does the ×320 with shifts and adds. | About 184 cycles per edge, about 2% |

### 6b. Cockpit overlay (`p4_hud_*`)
The visor pillars and dashboard are drawn on top of the 3D view every frame, from a list of 382 masked pieces (about 3.4% of a frame). They can't simply be drawn once, because the sky fill repaints the whole window each frame. The patch fills and redraws only the cockpit rows that the terrain can have touched that frame. About +4% fps on foot.

### 6c. Removing wasted work (P7)
- **Cells that can't produce anything** (`p7_cell_*`)
  - *Original behaviour:* the terrain is a grid of cells. The game took each cell inside the rough view area and transformed its four corners before checking whether any triangle survives. 56–70% of those cells produced nothing.
  - *Change:* a cheap test on the corner heights now proves when all four corners lie below the view, so the cell can't produce a triangle, and skips it before any corner work. Triangles drawn are exactly the same.
  - *Result:* cells processed per frame dropped from 63–80 to 20–44, about 2–3% of a frame.
- **Polygons hidden behind the cockpit** (`p7_ck_*`)
  - *Original behaviour:* 45–59% of the terrain pixels drawn while walking end up under the solid dashboard and pillars. Up to a fifth of the polygons are entirely hidden there, but each one was still edge-walked and filled at full cost.
  - *Change:* an exact outline of the solid cockpit, one row at a time, is rebuilt from the game's own cockpit data whenever it is loaded (it differs per vehicle). Polygons entirely behind it are dropped before edge-walking.
  - *Result:* about 3%.
- **Not redrawing a picture that hasn't changed** (`p7_skip_*`)
  - *Original behaviour:* when standing still, every frame recomputed the identical picture, about 1.75 million cycles of work for zero change.
  - *Change:* a signature of everything the 3D renderer actually reads is compared each frame. That includes the camera, the player's state, every unit and map marker in range, and the sea-wave state. If it matches for two frames running, both screen buffers already hold the right picture, so the 3D drawing is skipped. The HUD still updates.
  - *Coverage:* the inputs were found by tracing what the renderer reads, not by guessing. Anything not fully understood (explosions, messages on screen) simply always redraws. The skip is on for every vehicle type (a per-type table); it only fires when the picture really is unchanged.
  - *Result:* standing still in the Helicopter or the Bus runs at about 25 fps instead of 4–6, the ceiling of the 25 Hz pass timer; at 32 MHz also on foot and in the Jeep (267 and 337 skips per 1000 VBL). Pixel-identical on 15 vehicle snapshots at flips 10 and 40 and in a stop-and-go run (stand / go / stop / go) of all 22 types, every flip.

### 6d. Things tried and dropped
- **The STE blitter** (a hardware fill/copy chip): filling the sky with it was identical but saved only 0.15%. The CPU's multi-register store is as fast as the blitter on an 8 MHz STE, and polygon spans are too short to benefit.
- **Trimming fill rows under the cockpit:** a small loss while walking.
- **A full 25 Hz world:** too expensive.

## 7. What it all adds up to

Compared with the unpatched game, same machine, same scene:

| Situation (1 MB STE, 8 MHz; the rows are the Helicopter, see the correction in section 4) | Original | Enhanced | Picture |
|---|---|---|---|
| Walking | 56 frames | 69 frames (+23%) | identical |
| Standing | about 4 fps | about 25 fps | identical |
| Hard banked turn | 75 frames | 83 frames (+11%) | identical |
| World speed at 16 MHz vs 8 MHz | 2.3× faster | the same | n/a |
| Loading-screen grey flashes | many | none | n/a |
| Steering | yoke-like | direct | n/a |

**Where the rest of the time goes.** The game isn't wasteful in what it draws: only 37–60 triangles and 0–2 objects per frame. But each polygon carries about 14,500 cycles of fixed overhead (edge setup, clipping, dispatch). The cheap identical-picture wins are now used up. Further big gains would need a visible tradeoff:
- a shorter draw distance (5–19%);
- a cockpit crop (about 8%);
- simpler distant objects.

A new renderer is the other route.

## 8. Known limits and open items

- **Smooth motion in every vehicle uses extrapolation**: when a turn or move stops, the extra frames of that last group can show a pose up to 0.8 of a step too far, and the next real step snaps back. Hovercraft (1.8 fps at 8 MHz) and the Zeppelin are frame-time bound anyway.
- **Static-frame skip assumption:** terrain heights and object models are assumed never to change during play. If some mission event does change them, the view could stay stale until you move.
- **TT under Hatari:** the top panel shows the 3D palette. This is a Hatari limitation (one palette per TT frame); a real TT should be fine.
- **Untested:** campaign creation on floppy (Hatari discarded the writes), and real TT/Falcon TOS (only EmuTOS was available).

## 9. Delivered

- `dist/Midwinter2_v<version>_patched_<date>.zip`: hard-disk folder. `dist/Midwinter2_v<version>_patched_floppies_<date>.zip`: floppy set. The version (1.2) lives in one place, `patches/mw2_credit.s`.
- **Release credit:** the orange MIDWINTER II logo screen (the loading screen on both builds; on floppy it is followed by "Insert Graphics Disk") shows a small dim `v1.2 enhanced by dad_prg` at the bottom (`mw2_credit`, `work/notes/credit.md`). Only 343 black pixels change (rows 188-196, colour 2 of the screen's own palette), in both screen buffers; cold boots to the 3D view with MWPO on STE and plain ST, floppy and HD.
- `tools/play.sh`, `tools/play-tt.sh`, `tools/package.sh`.
- The patch tool, 53 patch sources, the study notes and the test tooling, so every result can be reproduced.
