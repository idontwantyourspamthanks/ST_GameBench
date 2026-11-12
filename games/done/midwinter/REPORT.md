# Midwinter enhanced: how it was done

This is a plain-English account of the work on *Midwinter* (Atari ST, PP's 2014 hard-disk version). It covers what was changed, what the original code did at each point we changed, and what each change achieved. It follows the Midwinter 2 job (`../midwinter2/REPORT.md`) and reuses its method and much of its tooling. The evidence (disassembly, measurements, raw logs) is in `work/notes/`, and the patch sources are in `patches/`.

## 1. Starting point

PP's package has the same shape as Midwinter 2's:

| File | Role |
|---|---|
| `RUNME.TOS` | PP's self-unpacking loader, with his bug fixes and security-check bypass. |
| `HAGA` | PP's hardware detection and resident disk service; byte-identical to Midwinter 2's. |
| `FILES/MWA`, `MWB`, `MWC` | Raw images of the original floppies (single-sided, 400 KB each). MWC is the data/save disk. |

**Baseline**, unpatched, 1 MB STE at 8 MHz, ski view:

| Scene | Frames per second |
|---|---|
| Standing | 4.0 |
| Walking | 5.4 |
| Turning | 7.5 |
| Busy (several objects) | 3.9 |

Like Midwinter 2, the world runs one step per frame, so it ran **twice as fast at 16 MHz**. Steering was "yoke"-style.

We expected Midwinter to give more than Midwinter 2, being older and simpler. That was half true:
- the per-frame logic is smaller;
- but the renderer has the same per-edge overhead as Midwinter 2's, and it has a few extra costs (below).

### How we worked
- Same as Midwinter 2: Hatari ran headless on a hidden display, driven by a script (`tools/mw1.py`). We worked from saved machine states and profiled.
- Before anything was switched on, it had to pass three gates:
  - **Identical-picture test** (`tools/mw1ab.py`). Midwinter **triple-buffers** (`$58000`/`$68000`/`$78000`), so all three screen buffers are compared byte for byte.
  - **Speed**: exact CPU cycles per frame, and world speed at 8 and 16 MHz.
  - **Cold boot** from the desktop into the ski view: 1 MB STE (TOS 1.62) and 4 MB Mega STE (TOS 2.06). The floppy set boots to the team screen.

## 2. The patch system

`tools/mw1patch.py`; `patches/README.md`; notes `loading.md`, `floppy.md`.

This is a port of Midwinter 2's:
- a 32 KB payload copied to `$B3000`;
- a boot trampoline that checks every original byte before patching. It applies all patches or none, and leaves `MWPO` or `MWPF` at `$B2FF8`.

The differences:
- **Two-pass trampoline.** It verifies every site first, then writes.
- **Different entry points.** It takes over the tail `jmp $800.w` of PP's patcher. The game's load hook is at `$10D6C`.
- **Floppy set.** PP's security-check bypass (`rts` at `$12050`) is applied by our own code.
- **PP's loader fixes carry over unchanged**, because HAGA is identical:
  - `pp_nofade`: palette changes during boot loading dropped from 25 to 1;
  - `pp_bigram_cache`: the 4 MB+ hang.

## 3. Game speed independent of the frame rate

`patches/p3b_*.s` (and the simpler alternative `tick_head.s`); note `timing.md`.

**What the original does.** One pass of the main loop (`$14e00`) does three things:
1. moves the player and the world one step;
2. draws the 3D view;
3. flips the screen.

The game clock advances one minute every 21 passes. Nothing measures real time.

**What we found.** There is a surprise inside the routine labelled "HUD redraw" (`$129d2`). Its last two calls (`$c4f2`, `$ca7e`) are game logic, not drawing:
- they move the 41 map units;
- they draw random numbers;
- they can turn a unit into an enemy object.

So the "drawing" half of the loop is not purely drawing, and skipping it would freeze the map. This changed how the rest of the work was done.

**What we did.**
- **The world runs exactly 5 steps per second of real time.** That covers the state machine, terrain, game clock, units, spawns and objects.
  - The time base is the game's own VBL counter.
  - When ahead, the loop waits. When behind, it catches up by skipping frames, at most 3 steps.
  - After a long pause it resynchronises instead of fast-forwarding.
- **The view runs at 25 steps per second.** Each world step is split into 5 passes of 1/50 s. Heading, position, cells, terrain tilt and camera height are interpolated across them. The 5th pass runs the original chain, so at every world step the state is exactly the original's.
- **Rejected: a full 25 Hz world.** The speed decay (a `divu #3`), the slope and the random spawns cannot give the same result in 5 small steps as in 1 big one.

**Result.**
- **Exact replay.** At every world step, the whole state matched the original game step for step, including the random-number stream and the objects. Tested walking, turning, standing and busy, at 8 and 16 MHz.
- **Same speed at any clock.** 5.00 world steps per second at both 8 and 16 MHz (157/157 steps identical in position, speed and heading). The game clock runs at the same rate at both speeds.
- **The pace at 8 MHz changes slightly.** The original's pace there depended on the frame rate. Against it, standing and walking are now a little quicker (+8 to +23%), and fast turning is slower (it used to run 7.3 steps per second).

## 4. Direct controls

`patches/p5_ctl_turn.s`, `p5_ctl_buggy.s`; notes `controls.md`, `p5_controls.md`.

**What the original does.** Mouse, joystick and keypad all feed one running total (`$24faa`):
- the mouse adds its movement;
- the joystick and keys add 5 counts per screen refresh while held.

The steering routine (`$12fe2`) turns that total into a turn rate (a cubic curve) and never reduces it. So a nudge keeps you turning, and a released key carries on at full rate. It's the same yoke as Midwinter 2.

**What we did.** We replaced `$12fe2`, which skis, the buggy and the hang-glider all share. It takes whatever has built up since the last step and converts it to a turn, then clears it:
- the mouse turns only while it moves;
- the joystick and keys turn at a constant rate while held, and stop on release;
- a small remainder is carried over, so slow mouse movements aren't lost.

One extra 6-byte patch (`p5_ctl_buggy`) keeps the buggy's effort calculation working. Midwinter 2 needed an extra interrupt hook for this; Midwinter 1 didn't, because its joystick path already counts per refresh.

## 5. Faster drawing, identical picture

`patches/p4_*.s`, `p7_cell_*.s`; notes `render.md`, `p4_raster.md`, `p7_cell.md`.

**Where the time goes.** The cost per frame is in per-polygon and per-edge overhead, not pixels:
- about 170 edges per frame, each costing about 1,300 cycles in total;
- the actual pixel stores are about 1.3% of the frame.

Midwinter 2 was the same.

| Patch | What the original did | What changed | Saving (cycles/frame) |
|---|---|---|---|
| `p4_ck_skip` | Before drawing each object, re-summed that object's model data byte by byte (48 cycles a byte, 1–1.6 KB per object). On a mismatch it hung with a flashing screen: an anti-tamper check. | Skipped. Nothing ever modifies that data. | up to 7% (0 with no object in view) |
| `p4_walk_*` | The polygon edge walker saved and restored many registers per edge, and ran an edge-window test that always passes for terrain edges inside the view. | It saves only the two registers it uses. The test is skipped only when provably redundant: both ends inside, and the same clip window. | 0.5–3.8% |
| `p4_pfx_*` | Every frame refilled the whole sky area and replayed the whole goggles frame. | Only the rows the terrain can have touched since that buffer was last drawn are refilled and replayed. State is kept per buffer for all three. | 1.4–4.2% |
| `p4_pfx_ray` | – | A fix for the above: the enemy-impact ray effect draws straight onto the screen. When it fires, the next sky fill is a full one. | – |
| `p4_roll_00..23` | The vertex transform in each of 24 strip loops did 4 multiplies for the roll, even with roll at zero (the usual case). | 2 multiplies when roll is zero; the original code otherwise. | 0.9–1.4% |
| `p4_div_a/b` | Map markers and objects were divided by a scale that is always 512, using the slow divide. | A shift with matching rounding, guarded; the divide is the fallback. | 0.6–1.1% |
| `p4_drv_edge`, `p4_fill_save_*` | Small redundancies in the polygon driver loop and fill setup. | Trimmed. | 0.1–0.9% |
| `p7_cell_*` | Each terrain cell scanned the object list, and clipped five edges even when all four corners were inside the view. | A per-frame table of cells that hold objects skips the scan, and fully inside cells skip the clips. Cells, vertices and polygons drawn are exactly as before. | 1.2–2.5% |
| **All of the above** | | | **11.3% stand, 11.3% walk, 14.8% turn, 12.5% busy** |

Frames per 1000 screen refreshes with all of them, in the identical-picture test: standing 78 → 89, walking 111 → 125, turning 143 → 169, busy 79 → 90.

### Not redrawing a picture that hasn't changed (`p7_skip_*`, note `p7_static_skip.md`)

**Original behaviour.** Standing still, every frame recomputed the same picture.

**The change.** Each frame, the patch builds a signature of everything the 3D drawing reads:
- camera position and heading;
- tilt, roll and camera height;
- the marker table;
- the four object slots.

These inputs were found by tracing the reads, not by guessing. If the last three frames (one per buffer) came from the same signature, all three buffers already hold the right picture. The 3D drawing is then skipped; the HUD, logic and flip still run.

**Never skipped:**
- the first frame after entering the view;
- while a message is shown;
- during the enemy-impact effect, which uses random numbers;
- snipe, buggy and glider views.

**Verified.** In a self-check, every skip decision was re-rendered and compared byte for byte, with no mismatch. That included an approaching enemy and a moving map unit.

**Result.** Standing costs 60–81% fewer cycles per frame; how much depends on whether a map unit nearby is moving. It doesn't fire while moving.

### Tried and dropped
- **Goggles cull** (dropping polygons hidden behind the goggles frame). A per-row test costs more than the rows it saves, and fully hidden polygons are rare: 0.4 per frame walking.
- **Lazy vertex transforms.** About 80 of 190 vertices per frame are never used, but the bookkeeping to skip them costs about as much as transforming them.
- **Reciprocal-table divides in the edge stepper.** An exhaustive simulation of 137,540 edges showed the original's truncation can't be matched, so pixels would shift.
- **Shorter draw distance and a reciprocal edge walker.** Not pixel-identical, so rejected.

## 6. What it all adds up to

**Display cost, identical picture.** Restored saves, all three buffers compared; timing and the redraw skip not included:

| Scene | Cycles per frame, original | Enhanced | Change |
|---|---|---|---|
| Standing | 1,986,679 | 1,761,570 | −11.3% |
| Walking | 1,412,333 | 1,252,736 | −11.3% |
| Turning | 1,092,229 | 930,714 | −14.8% |
| Busy | 1,986,276 | 1,737,216 | −12.5% |
| Standing, redraw skip on | 1,907,634 | 708,345 | −62.9% |

**Same scripted run from a cold boot**, 1 MB STE. Frames per second; the walk followed the same scripted mouse input in both runs:

| | Original 8 MHz | Enhanced 8 MHz | Original 16 MHz | Enhanced 16 MHz |
|---|---|---|---|---|
| Standing | 3.9 | 4.4–7.7 | 7.8 | 19.0 |
| Walking | 4.2 | 4.6 | 10.9 | 12.3 |
| Walking and turning | 5.2 | 5.5 | 9.7 | 11.8 |
| World speed | 1× | 1× | **2×** | **1×** |

- On a stock 8 MHz machine, the gain is about 10% when moving and up to about 2× when standing still. The standing figure depends on whether a nearby map unit is moving.
- On a 16 MHz machine you keep all the extra frames, and the world no longer speeds up.

## 7. Known limits

- **Vehicles.** Buggy and hang-glider get correct speed and direct controls, but no 25 Hz in-between steps and no redraw skip. They were never driven in testing: no test save could reach a garage or glider site.
- **Redraw skip and map units.** A map unit within about 4,700 units stops the skip, even when it's off screen.
- **Not tested:**
  - TT/Falcon;
  - 60 Hz displays (the world would run at 6 steps per second);
  - the "ENEMY IN RANGE" message path with the redraw skip;
  - saving to the data disk on the floppy set.

## 8. Delivered

- `dist/Midwinter_v<VERSION>_patched_<date>.zip`: hard-disk folder `MW1PATCH/`, with `PATCHES.TXT`.
- `dist/Midwinter_v<VERSION>_patched_floppies_<date>.zip`: floppy set; the security check is skipped.
- `tools/play.sh` (launcher for any machine) and `tools/package.sh`.
- The patch tool, 60 patch sources (56 on by default), the study notes and the test tools.
- **Release credit v1.1:** `patches/mw_credit.s` draws `v1.1 enhanced by dad_prg` (game font, colour 5 of the menu's own palette, 211 pixels) in the bottom-left corner of the Game Options screen, HD and floppy; the version is set only by its `; version:` header (`work/notes/credit.md`).
