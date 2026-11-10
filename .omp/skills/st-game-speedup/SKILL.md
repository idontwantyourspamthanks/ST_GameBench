---
name: st-game-speedup
description: Method for speeding up and modernising a closed-source Atari ST game by RAM patching, learned on Midwinter 2. Covers phase plan, benchmarks, renderer profiling and auditing, fixed-timestep decoupling of game speed from frame rate, direct controls, cockpit/occlusion culling, static-frame skip, gates and packaging. Use when starting or planning work on a new game in gamebench/games/.
---

# Speeding up an Atari ST game (method)

Reference project: `games/midwinter2`. Its `PLAN.md` holds phases P0–P7 and its `work/notes/*.md` hold the evidence. The user's standing preferences are below.

## User preferences (carry over unless told otherwise)
- **Target:** a 1 MB 8 MHz STE. Nothing may break on ST, Mega ST, Mega STE, TT or Falcon. Test 4 MB too.
- **Pixel-identical by default.** Visual tradeoffs need before/after screenshots and explicit approval.
- **Keep dithered fills:** they make the landscape readable.
- **Game speed must not depend on CPU speed.** Fixed real-time logic rate.
- **Direct controls.** Joystick and keys turn at a constant rate while held and stop on release. The mouse turns by its motion and stops when it stops. No "yoke" (input → persistent rate).
- **Deliverables:**
  - patched copies, never the originals modified;
  - a patch tool that verifies original bytes;
  - zips: HD folder plus a floppy set. **Ship both by default:** a floppy version is mandatory (most ST owners have no hard disk) and an HD version is expected too (essential on Mega STE/TT). Drop one only for a very good, stated reason. If the base release is HD-only, build the floppy set from a floppy release of the same game; if it is floppy-only, build an HD version (file loads) as well;
  - `play.sh`-style launcher scripts.
  - **Release credit (mandatory):** every release shows a version and credit line, e.g. `v1.2 enhanced by dad_prg`, on a startup screen, so archivists can't mistake it for the original release. The user picks the screen and placement per game. Keep the version in one place per game (patch source or build config); it must appear in the README/PATCHES.TXT and zip names too.

## Phases
1. **Harness and benchmarks.**
   - Run the game in Hatari and learn its navigation. Record it as a `boot_to_game()` subclass with reference crops and game-state checks.
   - Make in-game snapshots at 1 MB: standing, moving, turning, plus a busy scene.
   - Record baseline fps, a profile, and world speed at 8 MHz vs 16 MHz.
2. **Reverse-engineer, in parallel and read-only.** Cover the frame loop and flip, the hot functions (one agent each), simulation timing (per-frame or per-VBL), the input pipeline, and the loader/patch delivery. Notes go in `work/notes/`, with evidence or `[INFERENCE]`.
3. **Patch tool.** Copy MW2's `tools/mw2patch.py` design and re-derive the per-game offsets: the trampoline at PP's patcher tail, the load hook, the payload, HAGA file patches, a floppy build, and `verify`/`build`/`live`.
4. **Timing.**
   - Option A: a fixed logic tick from a free-running VBL clock. Wait when ahead; skip renders when behind (clamped); resync after gaps.
   - Then partial B: the player steps at 25 Hz with 1/5 increments, using exact remainder accumulators, and the world stays at the base tick.
   - Prove group-end state equality against A.
5. **Display.** Profile, then attack the hot spots. Rules of thumb from MW2:
   - The profile is flat. Gains come from many 1–4% items plus waste removal.
   - Cull polygons hidden under an opaque cockpit (exact per-row mask).
   - Skip cells or objects that provably emit nothing.
   - Skip the 3D render when its inputs are unchanged for 2 frames (double buffer): about 5× when standing.
   - The STE blitter did NOT help (`movem` matches it; spans are short).
6. **Controls:** decode the IKBD handler, find the accumulators and the consumer, and replace them at the consumer with direct control, scaled per tick.
7. **Regression:** cover every machine/TOS/RAM size, save/load, campaign or data-disk creation, joystick and keyboard modes.

## Gates (every patch)
- `verify`: the original bytes match.
- An A/B pixel gate on snapshots, run before the timing patches, comparing visible bytes only: `--flips 10/40` on standing, moving and turning snapshots.
- Cycles per frame, before and after (`profile`).
- A cold boot of the full default build at 1 MB and 4 MB, reaching gameplay with the marker set.
- A world-rate equality check for timing patches.

## Traps from MW2
- **A zero-patch build is not pristine.** It still contains your staging code. The 4 MB hang was misattributed because of this.
- **Agents' "dead code" or "validated" claims were wrong more than once.** Re-run a live check before building on one.
- **Long debugger lines truncate silently.** Patch-tool site tables and payload size have limits; check build errors.
- **`/tmp` is RAM.** Never copy whole projects per emulator run.
