# Midwinter 2 enhanced: how it was done

This is a plain-English account of the work on *Midwinter 2: Flames of Freedom* (Atari ST, PP's 2014 hard-disk version). It covers what was changed, why, what the original code was doing at each point we changed, and what each change achieved. The detailed evidence (disassembly, measurements, test logs) is in `work/notes/`. The patch sources are in `patches/`.

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

`patches/tick_vbl.s`, `p3b_*.s`; notes `simtiming.md`, `frameloop.md`, `tick_inventory.md`.

**What the original does.** The main loop at `$31486` runs the game logic once:
- moving the player,
- running the other units,
- ticking the clock (one game minute every 33 passes).

Then it draws the 3D view once and flips screens. Nothing measures real time: each pass moves the world a fixed step. So the faster the machine draws, the faster the world runs. At 16 MHz everything moved 2.3× faster, and any speed-up we made to drawing would have made the game run faster too.

**What we did, in two layers.**
1. **A fixed logic rate** (`tick_vbl`, plus the scheduler at `$31486`).
   - We added a real-time clock: a counter bumped 50 times a second by the screen interrupt. The game's own counters were unusable, because it clears one every frame and the other wraps at 6.
   - At the top of the loop we now run the logic exactly 5 times a second of real time. If the machine is ahead, it waits. If it falls behind, it skips drawing a frame to catch up, limited to 3 steps. After a long gap, such as returning from a menu, it resynchronises instead of fast-forwarding.
2. **Smooth on-foot motion** (`p3b_*`).
   - A full 25 steps per second would have cost 88% more CPU, because every unit's logic is expensive. Instead, only the player's own movement runs 5× per step, each time 1/5 as far.
   - Exact remainder arithmetic makes the five small steps add up to precisely the original step. Heading, lean, route/altitude and bank are all handled. Everything else in the world still updates 5 times a second.
   - The collision check runs once, on the full step, exactly as before (`p3b_probe`). The camera may therefore creep a fraction into a wall before snapping back.

**Result.**
- World speed is the same at 8 and 16 MHz, and on TT/Falcon (about 26–28 units/s everywhere).
- At every 1/5-second checkpoint, the player's position, heading and game clock are identical to the original game's step for step.
- On foot, the view is redrawn as often as the machine can manage: about 9 fps in heavy scenes at 16 MHz and 23 fps in light ones, against a flat 5 before.

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
  - *Coverage:* the inputs were found by tracing what the renderer reads, not by guessing. Anything not fully understood (vehicles, explosions, messages on screen) simply always redraws.
  - *Result:* standing still runs at about 25 fps instead of 4–6, the ceiling of the 25 Hz on-foot timer.

### 6d. Things tried and dropped
- **The STE blitter** (a hardware fill/copy chip): filling the sky with it was identical but saved only 0.15%. The CPU's multi-register store is as fast as the blitter on an 8 MHz STE, and polygon spans are too short to benefit.
- **Trimming fill rows under the cockpit:** a small loss while walking.
- **A full 25 Hz world:** too expensive.

## 7. What it all adds up to

Compared with the unpatched game, same machine, same scene:

| Situation (1 MB STE, 8 MHz) | Original | Enhanced | Picture |
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

- **Smooth motion is on foot only.** Vehicles still update 5 times a second, and the static-frame skip is on foot only too.
- **Static-frame skip assumption:** terrain heights and object models are assumed never to change during play. If some mission event does change them, the view could stay stale until you move.
- **TT under Hatari:** the top panel shows the 3D palette. This is a Hatari limitation (one palette per TT frame); a real TT should be fine.
- **Untested:** campaign creation on floppy (Hatari discarded the writes), and real TT/Falcon TOS (only EmuTOS was available).

## 9. Delivered

- `dist/Midwinter2_patched_<date>.zip`: hard-disk folder. `dist/Midwinter2_patched_floppies_<date>.zip`: floppy set.
- `tools/play.sh`, `tools/play-tt.sh`, `tools/package.sh`.
- The patch tool, 52 patch sources, the study notes and the test tooling, so every result can be reproduced.
