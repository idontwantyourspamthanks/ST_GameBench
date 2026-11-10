# Midwinter 2 (HAGA HD build): display speed + controls plan

## Decisions (agreed 2026-11-07)

| Topic | Decision |
|---|---|
| Target hardware | **1 MB STE is the primary target**: benchmarks are judged on an 8 MHz STE with 1 MB, and all patches plus their added code must fit in 1 MB. Larger RAM may be used only for optional enhancements. The blitter is in play, and blitter code is chosen at runtime (HAGA already detects the machine). A plain ST must still run the original CPU path unchanged. |
| Visuals | **Small tradeoffs OK**, each approved by you from before/after screenshots. Anything else must be pixel-identical. |
| Controls | **Direct control replaces the current "yoke" model**, where input changes the *rotation rate* and that rate persists. Joystick or keyboard left gives a fixed turn rate while held and zero when released. Mouse turn equals mouse motion: heading changes in proportion to mouse dx, and stops when the mouse stops. The same applies to pitch where a vehicle has it. Map screens also get click-to-select in place of Space-over-target. |
| Game speed | **The world must not speed up when frames get faster** (Mega STE, TT, Falcon, and our own STE speed-ups). Simulation is decoupled from rendering. |
| Delivery | **Patched copies plus a patch tool.** Originals are never modified, and the tool can revert. |

## What we have (observed facts)

There is no source code. Everything here is binary patching of 68000 code.

| Item | What it is | Evidence |
|---|---|---|
| `RUNME.TOS` | PP's loader, self-extracting LZ-packed | Depacked to `work/dumps/RUNME_unpacked.tos` (text $4520, bss 111206) |
| `HAGA` | Hardware detect plus clock/cache menus (Mega STE, TT, Falcon) | Strings |
| `FILES/FFA–FFC` | Original game disks in PP's raw layout. Code is stored **uncompressed** but **fragmented** (not linear) | Of 928 32-byte samples of in-game RAM $4000–$3E000: 591 found in FFA, 111 in FFB, 23 in FFC, 44 not found, 159 low-entropy |
| `FILES/FFD` | Campaign disk. Blank as shipped; the game fills it via War Room → Start New Campaign | 2 → 1389 non-zero sectors after creation |
| `FILES/FFE` | Personnel disk | README |
| `*.HST`, `FF240R.BMP` | Intro pictures (STE hi-colour, TT/Falcon) | `LOG.TXT`, file headers |

These figures are for in-game (on foot at Lobos), 8 MHz STE, TOS 1.62, 2 MB, under Hatari 2.6.1:

- **Code** is resident at $4ECA–$3DB0E. Overlays per screen are not yet mapped.
- **Screens** are double-buffered at $60000/$70000. The game flips them by writing `$ff8201` only.
- **Vectors:**

  | Vector | Address |
  |---|---|
  | IKBD/ACIA `$118` (custom packet parser, state at `$759e/$75a0/$75a2`) | `$26882` |
  | VBL `$70` | `$26298` |
  | Timer B `$120` | `$263de` |
  | Timer C `$114` | `$26a50` |

- **No blitter.** There are no `$ff8a` register references in RAM.
- **Baseline: 3.8–4.8 fps** (10–13 VBLs per frame). Measured twice; this is the run-to-run noise.
- **The profile is flat. No single hotspot.** CPU cycles over about 250 VBLs, bucketed by call target:

| Bucket | Share | First look |
|---|---:|---|
| `$3c5e2` | 10.8% | Scan or line filler: `mulu #320`, then `jmp (a1)` into unrolled code below `$3d30a` |
| `$38cd0` | 10.5% | Unknown, called via full `movem` save/restore |
| `$1d768` | 4.4% | Loop that clears/inits 16-byte records (`clr.l 6(a0)`, `move.b d0,$b(a0)`) |
| `$1b996` | 4.2% | Bulk `movem.l` store: screen/sky fill |
| `$1fdf0` | 3.7% | Projection: `divs` pairs at `$200d2` |
| `$30e30` | 3.3% | Masked 4-plane sprite blit (and/or), probably the cockpit overlay |
| `$383ce`, `$3bfa2`, `$3c02a`, `$3c080` | about 2% each | `muls`/`divs` transform and projection |
| Everything else | about 55% | Dozens of 1% functions |

So any speedup will come from several medium wins plus frame pacing, not from one rewritten loop.

## Harness (already built and verified)

`tools/mw2harness.py` runs Hatari on a private Xvfb display, so input injection never touches your desktop. Hatari works on a scratch copy of the game; the originals are never written.

```
python3 tools/mw2harness.py fps     --snapshot work/snapshots/ingame_lobos_foot.sav --vbls 250
python3 tools/mw2harness.py profile --snapshot work/snapshots/ingame_lobos_foot.sav --top 40
python3 tools/mw2harness.py shot|dump --snapshot ... --out FILE
```

| Path | Contents |
|---|---|
| `work/snapshots/` | Memory snapshots: `corridor_agent`, `warroom_campaign`, `control_map`, `lobos_brief`, `ingame_lobos_foot` |
| `work/disk_overlay/FILES/FFD` | The created campaign disk, which the snapshots depend on |
| `work/dumps/ram_ingame_lobos.bin` | 2 MB RAM image taken in-game |

Gotchas found while building it:

- Any fifo debug command resets the profile buffer.
- Clicks need mousedown and mouseup with a hold between them.
- Map screens select with **Space while hovering**, not with a click.

## Phases

### P0: Benchmark set (small, sequential, mine)
1. Add 3–4 more in-game snapshots, all **in motion**:
   - a vehicle at speed over terrain;
   - a busy scene with several objects;
   - looking at the sea or sky (low load);
   - a turn.

   Standing still is not representative.
2. Freeze a baseline table (fps plus the top-30 buckets) per snapshot in `work/baseline.md`. Every later change is judged against it.
3. Extend the harness to set the CPU clock and machine at restore time (`hatari-option --cpuclock 16`, and Mega STE/TT boots). Record the same snapshots at 16 MHz: fps plus world-units per second. This is the "too fast" baseline for P3.
4. Add a joystick and keyboard input path to the harness: Hatari joystick emulation via cursor keys, or IKBD injection. Mouse already works.

### P1: Map the renderer (read-only reverse engineering; parallel subagents)
1. Build a shared disassembly tool: `tools/m68dis.py` (capstone over a RAM dump). It adds labels from call targets and xrefs, and annotates hardware registers and per-address cycles from a profile.
2. **One subagent per hot function** (about 10). Each writes `work/notes/<addr>.md` containing:
   - entry/exit and register contract;
   - callers and callees;
   - inner-loop cycle cost per iteration;
   - what the function draws or computes;
   - a concrete optimisation idea with an estimated saving.

   Each note must be backed by a dynamic check: a breakpoint plus a register/memory dump showing the claimed inputs and outputs. Any claim without that is labelled `[INFERENCE]`.
3. In parallel, a frame-loop agent:
   - finds the main loop and the flip code;
   - measures how many VBLs are lost waiting after a frame completes, since a single-wait double buffer can lose up to one VBL per frame;
   - splits the frame into stages: clear/sky, ground, objects, cockpit/HUD, transform, game logic, input.
4. In parallel, a simulation-timing agent:
   - finds the per-frame simulation step: player and vehicle integration, AI, projectiles, game clock;
   - finds the state variables for heading, turn rate, pitch, speed and position, by diffing RAM across frames under scripted input;
   - measures world distance per *second* (not per frame) at 8 MHz STE vs 16 MHz Mega STE vs TT, to quantify the speed-up.

   Known so far: the VBL handler increments `$7020` and `$770c` every VBL. `$7020` is used only by UI and cutscene waits (`$2f16e`, `$3300c`, plus `cmpi #$32/#$c8/#$19` delay loops). No in-game use has been found yet.

### P2: Patch delivery (sequential; one owner; blocks P3–P5)
1. Reverse PP's image read routine in `RUNME_unpacked.tos` to get an exact (RAM address → image file + offset) map for every code overlay.
2. Write `tools/mw2patch.py`:
   - Patch specs are declarative: RAM address, **expected original bytes**, new bytes, and a note.
   - It refuses to apply on any byte mismatch, writes patched copies (never in place), and can revert.
   - Free space for new code comes from a verified-unused RAM region or the loader's BSS.
3. Acceptance: boot a patched copy cold to the in-game snapshot path, dump RAM, and diff it. Only the intended bytes may differ.
4. Fallback if image mapping is ugly: patch in RAM from the loader after each overlay load. PP's loader already patches the game for its fixes, so the hook exists.

### P3: Decouple game speed from frame rate (before any speed-up ships)
This must land first. As long as the world advances a fixed step per rendered frame, every fps gain in P4 also makes the game run faster on the STE.

Options, chosen with P1 timing data:

| Option | How | Cost / risk |
|---|---|---|
| A. Frame cap | Hold each frame to a minimum number of VBLs | Trivial. Fixes fast machines only: the STE still slows down under load, and it throws away the P4 gains. A safety net, not the goal. |
| B. Fixed-timestep simulation | Run the logic step `k` times per rendered frame, with `k` taken from the VBLs elapsed (using the existing `$7020`-style counter). Rendering stays once per frame. | Only possible if logic and render are separable calls in the main loop. Logic cost multiplies on slow frames, so it needs measuring; this is the preferred option. |
| C. Variable dt | Scale every integration by elapsed time | Touches every mover, AI and timer. Large, and precision bugs are likely. Last resort. |

Gates:
- World distance per second and the game clock (HUD `12:36` style) per second match within 5% across 8 MHz STE, 16 MHz Mega STE and TT, both before and after a P4 speed-up.
- Saves and loads and the campaign clock are unaffected.

### P4: Display speed (one patch per change; each gated)
The candidates below get ranked by P1 data. Each one ships only if both hold:
- fps improves on **every** benchmark snapshot, with ≥3 runs to beat the ±1 fps noise;
- screenshots are pixel-identical to the original at the same snapshot and frame. The exception is an agreed small visual tradeoff, which needs your sign-off from a before/after screenshot pair.

| Candidate | Idea | Risk |
|---|---|---|
| Frame pacing | Stop waiting a VBL after the flip; triple buffer if RAM allows | Low |
| Bulk clear / sky fill (`$1b996`, `$1d768`) | Clear only what the 3D view overwrites; skip the cockpit area | Low |
| Cockpit overlay (`$30e30`) | Draw once into both buffers; clip the 3D view to the window instead of re-masking every frame | Medium |
| Span filler (`$3c5e2`) | Table instead of `mulu #320`; wider stores; tighter unrolled entry | Medium |
| Projection `muls`/`divs` | Reciprocal tables or shift-based scaling | Medium (precision) |
| Blitter span/clear fill (STE+) | **In scope.** Blitter fills for the clears, sky and polygon spans, plus blitter copies for the cockpit. The path is selected at runtime; a plain ST keeps the original CPU code. Needs a blitter-vs-CPU overlap study, because the CPU halts in blitter HOG mode. | High; largest STE gain |

### P5: Controls (after P3, because direct rates need real time)
1. Reverse the IKBD handler (`$26882`), the mouse/joystick state at `$759e–$75a8`, and the per-mode (M/J/K) control dispatch into each vehicle's steering. Vehicles may each have their own handler.
2. Measure the current "yoke" behaviour from RAM per frame under scripted input:
   - a step input (hold joystick left for 2 s, then release);
   - a mouse burst (dx = +40, then stop).

   Record heading, turn rate, pitch and pitch rate.
3. Direct model:

   | Input | Behaviour |
   |---|---|
   | Joystick / keyboard | Held direction gives constant yaw (and pitch) rate in degrees per *second*. Release gives zero rate at once: no persistent rate, no inertia. |
   | Mouse | Heading delta = k × mouse dx accumulated since the last frame. No motion means no turn. `k` should be tunable in the patch. |

4. Map screens: make a left click inject the same "select" event that Space-over-target does.
5. Gates, using the same scripted inputs as step 2:
   - Joystick/keyboard: constant rate from the first frame of the hold, and exactly zero within 1 frame of release.
   - Mouse: total heading change ∝ total dx, independent of fps. Same within 5% at 8 MHz STE and 16 MHz Mega STE.
   - Each mode (M, J, K) is exercised separately, and UI pointer behaviour is unchanged.

### P6: Regression
Boot every patched build to gameplay on:

| Machine | TOS | RAM | CPU |
|---|---|---|---|
| ST | 1.04 | 1 MB | — |
| STE | 1.62 | — | — |
| Mega STE | — | — | 16 MHz |
| TT | — | — | — |
| Falcon | — | — | — |

On each, check:
- campaign creation;
- in-game save/load;
- the HAGA savestate keys (`*` and `/` on the numpad);
- exit to desktop.

## Subagent protocol (`task` = Sonnet, `smol` = Qwen, `tiny` = DeepSeek Flash)
- **Give exact inputs:** addresses, dump path, snapshot, and the command to run.
- **Require a fixed output file:** `work/notes/...` or a patch spec.
- **Every factual claim must cite one of:**
  - a disassembly line with its address;
  - pasted raw harness or debugger output;
  - a byte diff.

  Otherwise it is marked `[INFERENCE]`.
- Read-only reverse engineering fans out in parallel. **Patch writing has one owner at a time**, because patches share free space and patch sites.
- I re-run every acceptance command myself before accepting a result.
- **Model routing:**
  - Anything that drives the emulator or game UI goes to Opus (me) or Sonnet (`task`): navigation, scripted input, judging screenshots, multi-step dynamic debugging. Small models tend to second-guess when the UI misbehaves.
  - Qwen (`smol`) and DeepSeek Flash (`tiny`) get **pure code tasks only**:
    - writing or optimising 68000 routines against a precise register/memory contract;
    - Python tooling;
    - table generators;
    - static disassembly analysis.

    Their output is checked by a test I or Sonnet run in the emulator.

## P7: Render waste reduction (from `work/notes/render_audit.md`)

Target: a 1 MB STE. No item needs RAM beyond what is already free in game (`$B2852-$E83E5`, about 215 KB on 1 MB). The limit was the size of the patch payload (7.75 KB at `$B3000`, capped by RUNME's pc-relative displacements into bss). Step 0 is DONE: the payload is now 32 KB (`$B3000-$BAFFF`), HD and floppy; `$B4F00-$BAFFF` is free for new patches (`work/notes/payload32k.md`).

| # | Item | Method | Pixel-identical | Est. gain, moving (w / standing f) | RAM |
|---|---|---|---|---|---|
| 0 | Bigger payload | HD: relocate the RUNME instruction at text `$22E` (or its target) so the data segment can grow to about 32 KB. Floppy: FFA file 10 can already be any size. | n/a | 0 | ≤32 KB at `$B3000-$BAFFF` (inside the free 215 KB; still clear of PP's chunk cache, which ends at `$B1D40`) |
| 1 | Polygons wholly under the cockpit | Reject in the stream walker `$1fa54` before walk and fill. Use an exact per-row mask (dashboard rows 182-199 plus pillar extents), not a rectangle. | yes (the opaque cockpit overwrites those pixels) | 3.6% / 2.6% | mask table about 0.8 KB |
| 2 | Terrain rows and pixels under the cockpit | Clip span tables before the fill. Rows 192-199: cut x 34-285. Rows 182-191: the wings. Pillars: trim the span ends that fall under a pillar; never split a span. | yes | about 2-4% / 1-2% (fill is about 15 cy/px; 3.8 k hidden px when walking) | shares the #1 table |
| 3 | Transformed vertices never used | Defer vertex transform until a triangle that survives the cell tests references it. Outcodes come from a cheaper conservative cell bound. | yes | about 1% / 1% (≈330 cy × 46-63 vertices) | slot flags, ≤0.5 KB |
| 4 | Cells that produce nothing | Per-cell early-out: test the cell's 4 corners against the frustum (or the cell bounding box) before classify, slot lookup and polygen prefix. | yes | 1.5-2.5% / 2-3% | none |
| 5 | Caching between frames | (a) Static-frame skip: if camera position, heading, pitch, bank, zoom, object state and the fog band are unchanged for 2 consecutive frames (both buffers hold the image), skip the 3D render and blit nothing; the HUD still updates with its dirty counters. (b) HUD radar and clock caching. | yes if the state test is exact | 0% moving / up to ~90% standing; HUD part 2-5% | state snapshot about 64 B; no extra screen buffer needed |

Expected total while moving: about 8-12% from items 1-4. Item 5 helps only standing or paused frames: menus-in-view, aiming the sniper rifle, waiting. Frame-to-frame retained rendering while moving would need a new engine: frames differ in 3-12% of 16-px groups, but the camera moves every frame, so every vertex changes. It is not worth it.

Order: 0, then 1+2 (one agent, shared mask), then 4+3 (one agent, same cell path), then 5 (one agent; needs an exhaustive list of what makes the view change: animation, sea, fog flicker, objects moving while the player stands still).

Gates are as in `mw2-patching`: abtest pixel-identical at `--flips 10/40`, cold boot at 1 MB, and the 4 MB check (the payload must stay clear of PP's cache).

## Release version
Next release: **v1.2** (user, 2026-11-10). A credit line `v1.2 enhanced by dad_prg` goes on a startup screen (placement: user to choose).

## Test scenarios (user tip, 2026-11-10)
- **Vehicles:** Raids -> different islands start with different vehicles. Select an island with Space -> question icon -> thumbs-up icon -> In. Use this for vehicle snapshots (render patches, controls, p7_cockpit per-vehicle cockpit lists, enemy AI per type).

## Correction and vehicle work (2026-11-10)
- **`$6220` is a 0-based vehicle index** (Tank 0, Jeep 1, Truck 2, Bus 3, Train 4, on foot 5, Speedboat 6, Crawler 7, Minisub 8, Submarine 9, Ship 10, Frogman 11, Biplane 12, Helicopter 13, Zeppelin 14, Balloon 15, Rocket Pack 16, Parachute 17, Flying Boat 18, Hovercraft 19, Flying Sub 20, Swimming 21). **13 is the Helicopter**; every earlier "on foot" / "foot" snapshot and measurement in this plan, `tick_inventory.md`, `timing.md`, `p7_static_skip.md` and the P3b/P7 rows above is the Helicopter. The shipped v1.2 `p3b_*` (25 Hz sub-steps), `p7_skip_*` (static-frame skip) and the optional `p4_hud_crop_*` are gated on `$6220 = 13` and act on the Helicopter only. True on foot (type 5) and the other 20 types run the plain 5 Hz path, and `p7_skip` never fires for them (measured, `REPORT.md` section 4).
- **P3c / P3cp (open, all `default: no`):** type-independent 25 Hz player motion; the original 5 Hz tick runs once per group of five 40 ms passes and the other passes display a pose (p3cp: predicted ahead, user's choice; p3c: interpolated). Group-end world state equal to option A for every type (`work/notes/vehicles_p3b.md`). Needs the lead's review before any default flips.
- **Defects found in v1.2:** `p3b_alt` uses the sub-pass bank coefficients (fix `p3b_alt_fix`), the sea wave phase advances per rendered frame and the sim reads it (fix in `p3b_head_fix`, by construction in p3c/p3cp).

