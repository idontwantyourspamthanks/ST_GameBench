# Seconds Out (1988, Tynesoft) — Enhanced STE Edition v1.1

Enhancement of Tynesoft's **Seconds Out** (1988) for Atari ST / STE / Mega STE / TT / Falcon (1 MB+), built from the verified original disk image (`Seconds Out (1988)(Tynesoft).st`, md5 `ea7f80595ef3f30a269cec5642d5db6a`) without modifying any originals.

## Key Enhancements (v1.1)

1. **STE Blitter + Dirty-Strip BG Restore + Uncoupled 50 Hz Engine:**
   - Precomputes 1-plane inverted masks (`$90000..$a5fff`, 88 KB) for all 8 sprite sheets (`BOX1.PI1`, `PUNCHES.PI1`, `BxA/B/C.CSP`, etc.) at load/unpack time.
   - Accelerates background restore (`$10b6`/`$10ec` with per-buffer dirty horizontal strip tracking), 4-plane shifted masked sprites (`$bc4`), and 2-plane wireframe Marco sprites (`$1bfa`) with the **STE Blitter**, with a fast register-only CPU fallback for Blitter-less ST/TT machines.
   - Uncouples render rate from a fixed **12.5 Hz (4-VBL) real-time logic tick** so gameplay speed is identical on 8 MHz and 16 MHz machines.
   - **8 MHz STE:** Locked **50.0 fps (1.00 VBL/frame)** — up from `12.6 fps` (4× increase!).
   - **16 MHz Mega STE:** Locked **50.0 fps (1.00 VBL/frame)** with identical 12.5 Hz world speed.
2. **Smooth 50 Hz Motion Tweening:**
   - Records the draw list on each 12.5 Hz logic tick and interpolates both fighters' horizontal motion smoothly across every 50 Hz display frame.
3. **Stamina System & Fatigue Penalties:**
   - Dual **Gold Stamina Bars** right beneath the white Energy bars (`y = 26..28`, dirty-checked on both buffers), turning **Bright Red** when exhausted.
   - Punches (`-6` stamina), Special moves (`-14`), blocking (`-5`), and ducking (`-2`) drain stamina instead of draining player health.
   - Reaching 0 stamina triggers **Exhaustion** (until recovered to 25%): slower movement and halved punch ferocity for both human and CPU fighters.
   - CPU fighters are fully stamina-aware and back off to recover instead of spamming endlessly.
4. **Rebalanced Fighter AI (All 5 Opponents):**
   - Full analysis in [work/notes/ai_and_frame_budget.md](work/notes/ai_and_frame_budget.md).
   - Fixes the late-game unblockable spam on **J. Ronco** and **M. Malone** (which previously read the player's guard height every 0.24–0.32 s with 1-frame punch telegraphs and 10× HP regen): rebalanced reactive timers, HP regen curves, human-reactable `(2,2,2)` telegraphs, 50% fair-read gate, 2.0 s Special cooldown, and stamina-gated auto-blocks.
5. **2-Player Versus Mode (`F1` / `F3` on Title Screen):**
   - Press **`F1`** on the title screen to toggle **1P Career** / **2P Versus**.
   - Press **`F3`** in 2P Versus to pick which opponent Player 2 controls (Joe Weed, B. Jones, M. Hagman, J. Ronco, M. Malone).
   - Player 2 controls: **Joystick Port 0** or **Keyboard (`A`/`D` move, `W`/`S` high/low guard, `Left Shift` + `A`/`D` Punch A/B, `Left Shift` + `W` Special, `Left Shift` + `S` Duck)**.
6. **Career Fighting Styles / Perks (`F2` on Title Screen):**
   - **`BALANCED`:** Standard speed, power, chin, and stamina.
   - **`SPEEDSTER`:** Faster footwork (`+33%`), 2× stamina recovery, lighter punches (`-25%` dmg).
   - **`HEAVY HIT`:** Devastating power (`+50%` dmg), Glass Jaw (`+40%` dmg taken), slower footwork.
   - **`IRON CHIN`:** Tough defense (`-25%` dmg taken), lower punch stamina cost (`-4` vs `-6`), slower footwork.
7. **Native Hard-Drive Install & Auto-Booting Floppy:**
   - Fixed-address relocator (`$80000`) + HD GEMDOS fixes (`a:.tos` -> `b.tos`, stripped `\r` filenames, NOP'd `Dsetdrv(0)`), so the game installs cleanly to any hard drive folder and never collides with `trainer.pi1` (`$1ffde`) on TOS 2.06+.
   - Also builds a 720 KB auto-booting FAT12 floppy image (`dist/SecondsOut_Enhanced_v1.0.st`).

## Build & Run

```bash
# Build dist/hd/SECONDS.PRG and auto-booting floppy dist/SecondsOut_Enhanced_v1.0.st
python3 games/in_progress/seconds-out/tools/build_so.py

# Play on 8 MHz STE (HD)
./games/in_progress/seconds-out/tools/run_ste.sh

# Play on 16 MHz Mega STE (HD, TOS 2.06)
./games/in_progress/seconds-out/tools/run_megaste.sh

# Play on 8 MHz STE (auto-booting 720 KB floppy)
./games/in_progress/seconds-out/tools/run_floppy.sh
```

## Real-Hardware Notes
- **STE Blitter HOG bursts:** Each sprite plane pass and dirty-strip BG copy uses HOG mode (`$c0`) in short bursts; IKBD joystick packets are 1-byte events (not mouse streams), verified in Hatari; real-hardware STE/Mega STE soak test recommended.
- **PSG / Floppy:** No YM2149/PSG registers are modified or hooked by any patch; original XBIOS `Dosound` calls are untouched.
- **RAM requirement:** Requires **1 MB+ ST-RAM** (`_phystop >= $100000`) for the `$80000` fixed relocation and `$90000..$a5fff` precomputed mask cache.
