# Italy 1990 (Codemasters) — Enhanced STE Edition

Enhancement of Codemasters' **Italy 1990 (11-A-Side Soccer)** for Atari STE (8 MHz) & Mega STE (16 MHz), built from the clean Hotline disk image (`ITALY.TOS`, md5 `3ab489a4c996ca80cb5b661007b2ab6e`).

## Key Enhancements (All 4 Initial Pillars)
1. **Speed (STE Blitter + 1-Call Stadium Renderer + Snappy Movement):**
   - Pre-renders the entire 20×38 tile stadium (`640×1216` px) once into `$92000` and copies the visible `336×168` pitch window in **one single STE Blitter call** per frame.
   - Replaces the software 16px sprite blitter (`$492e`) with an **STE Blitter** masked sprite blitter (`hook_sprite_draw`).
   - Dirty-checks HUD power bars (`$cd52`) and smart-caches the Blitter-shifted bottom HUD copy.
   - Boosts player running speed (+40%) and acceleration (2×) for responsive, Kick Off 2–style arcade pace.
   - **8 MHz STE:** Locked **25.00 fps (2.00 VBLs/frame)** at full 320×168 width (up from choppy 16.7–22.4 fps at 256×168).
2. **Full-Width 320×168 + 1-Pixel STE Hardware Horizontal Scrolling:**
   - Widens the pitch viewport from `256×168` (with black sidebars) to **full-width `320×168`**.
   - Replaces the 3-column screen-flip (`camX = 0 / 192 / 384`) with smooth 1-pixel camera tracking (`camX = 0..320`) driven by STE **`$ffff8265` (HSCROLL)** and **`$ffff820f` (LINEWID)**.
   - Pre-shifts the 26-line bottom HUD right by `fine_x` via Blitter so the HUD stays 100% pixel-locked with zero jitter; Timer B (`$3980`) only swaps palettes.
3. **Kick Off 2–Inspired Player AI (`hook_ai_outfield` + `hook_cpu_joy`):**
   - Replaces the static 128×128 grid lookup table (`$a5fc`) with a dynamic **4-4-2 formation** whose anchors scale smoothly with ball `(X, Y)`.
   - Possession-aware tactical shifts: forwards/wingers make attacking runs when in possession; defenders/midfielders track back when defending.
   - Single-chaser-per-team anti-clumping (`st_t1_chaser`, `st_t2_chaser`): only the single closest AI player per team presses/intercepts the ball, keeping teammates spread in passing lanes.
   - Smart CPU ball-carrier (`$ca8a`): shoots when in range of goal, passes to an open forward teammate when pressured, and dribbles toward goal otherwise.
   - Set pieces (`$ee08 != 0`) defer cleanly to the original game logic.
4. **Kick Off 2–Style Pitch Radar (`X` Key Toggle):**
   - Crisp `40×64` mini-pitch overlay in the top-left corner (`8, 6`) locked to screen coordinates across 1-pixel STE scrolling.
   - Shows touchlines, halfway line, penalty boxes, all 22 players colour-coded by team (Red vs Yellow 2×1 dashes), and a bright White ball pip.
   - Press **`X`** during a match to toggle the radar ON/OFF.

## Build & Run
```bash
# Build dist/hd/ITALY.TOS and auto-booting floppy dist/Italy1990_Enhanced.st
python3 games/in_progress/italy-1990-codemasters/tools/build_italy.py

# Play on 8 MHz STE (HD)
./games/in_progress/italy-1990-codemasters/tools/run_ste.sh

# Play on 8 MHz STE (auto-booting 720 KB floppy)
./games/in_progress/italy-1990-codemasters/tools/run_floppy.sh

# Play on 16 MHz Mega STE (HD)
./games/in_progress/italy-1990-codemasters/tools/run_megaste.sh
```
