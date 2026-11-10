# Midwinter 1 (PP HAGA HD build): speed-up plan

This follows the Midwinter 2 job (`../midwinter2/PLAN.md`), using the method in the `st-game-speedup` skill. The user's preferences carry over:
- Target is a 1 MB 8 MHz STE, and nothing may break up to TT/Falcon or at 4 MB.
- Output must be pixel-identical by default, and the dithering is kept.
- Game speed must not depend on CPU speed.
- Controls become direct.
- Deliverables are patched copies plus zips (HD and floppy).
- The user expects MW1 to be simpler than MW2, so it can probably run faster.

## Known so far
- **HAGA:** identical to MW2's, so `pp_nofade` and `pp_bigram_cache` should apply unchanged.
- **RUNME:** close to MW2's (unpacked text `$44ba`).
- **Images:** `FILES/MWA`/`MWB`/`MWC` are 409600 bytes each (10 spt × 1 side × 80 tracks). MWC is the save/data disk.
- **Path to the 3D view:** cold boot, then space presses through the intro to Game Options, then PLAY (screenshot 415,385). That leads to The Team, then Stark's portrait (178,170), then the Decisions icon (450,425), then the Skiing icon (384,424).
- **Snapshot restores:** after a restore, the game cannot load files ("Insert graphics disk"), so any flow that needs a load must start from a cold boot. Under investigation.
- **Controls** (`work/manual-proper.md`):
  - On foot / skiing (mouse): LMB starts walking; mouse forward/back changes speed; mouse left/right steers (on the spot when stopped); RMB stops.
  - S toggles ski/snipe, Space throws a grenade, X exits an action mode, M opens the map, P pauses.
  - Snow-buggy: the mouse is throttle and steering; X exits. Hang-glider: the mouse is pitch and steering.
  - Keyboard: numpad 8/2/4/6 plus `<` `>` for the buttons. Joystick in port 2, with `>` acting as the right button.

## Phases (same as MW2)
- **P0 Harness and benchmarks:** `tools/mw1.py` (`boot_to_game`); 1 MB ski snapshots (standing, moving, turning, busy); baselines (fps, profile, world rate at 8 vs 16 MHz).
- **P1 Read-only study:** frame loop and flip; hot functions; simulation timing; input pipeline.
- **P2 Patch delivery:** `tools/mw1patch.py`, ported from MW2 (`MW1Loader` agent).
- **P3 Timing:** fixed tick, then partial B if motion is per-frame.
- **P4 Display:** speed-ups, then waste removal (occlusion, cell culling, static-frame skip).
- **P5 Controls:** direct control.
- **P6 Regression:** all machines and RAM sizes; data-disk save/load; joystick and keyboard modes.
- **P7 Packaging:** zips, launcher scripts.

## Release version
Next release: **v1.1** (user, 2026-11-10). A credit line `v1.1 enhanced by dad_prg` goes on a startup screen (placement: user to choose).
