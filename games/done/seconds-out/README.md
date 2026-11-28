# Seconds Out (1988, Tynesoft) — Enhanced STE Edition v1.4

Enhancement of Tynesoft's **Seconds Out** (1988) for Atari ST / STE / Mega STE / TT / Falcon (1 MB+), built from the verified original disk image (`Seconds Out (1988)(Tynesoft).st`, md5 `ea7f80595ef3f30a269cec5642d5db6a`) without modifying any originals.

## Key Enhancements (v1.4)

1. **STE Blitter + Dirty-Strip BG Restore + Uncoupled 50 Hz Engine:**
   - Precomputes 1-plane inverted masks (`$90000..$a5fff`, 88 KB) for all 8 sprite sheets at load/unpack time.
   - Accelerates background restore (`$10b6`/`$10ec` with per-buffer dirty horizontal strip tracking), 4-plane shifted masked sprites (`$bc4`), and 2-plane wireframe Marco sprites (`$1bfa`) with the **STE Blitter**, with a fast register-only CPU fallback for Blitter-less ST/TT machines.
   - Uncouples render rate from a fixed **16.7 Hz (3-VBL) real-time logic tick** with smooth 50 Hz horizontal tweening so gameplay runs at a locked **50.0 fps** with identical world speed on 8 MHz STE and 16 MHz Mega STE.
2. **50 Hz Arcade Juice (v1.4):**
   - **Footwork Bounce:** Subtle rhythmic 50 Hz stance bob for both fighters (half-phase offset; flat-footed when exhausted).
   - **Punch Lunge & Snap:** Forward punch lunge on Marco and windup pull-back/snap on opponents.
   - **Hit-Stop & Hit-Recoil:** 2–4 VBL impact freeze on clean/heavy blows while a decaying 25 Hz horizontal recoil micro-shake plays live; subtle guard-absorption jolt on blocks; seismic ring shake on KO Uppercuts, Dazes, and knockdowns.
   - **Daze Wobble:** Visible `±3 px` horizontal sway on Dazed fighters in the ring.
3. **5-Act Career Mode, *THE RING SUN* Newspaper & `CAREER.DAT` Save (v1.2):**
   - 5-act Rocky-style Career ladder (`Joe Weed → Bonecrusher Jones → [Breaking News: RING TRAGEDY] → Hammerhead Hagman → J. Ronco → Malone`) with Rematch on loss, live `W/L` record, and fight-driven permanent Career upgrades (`BODY POWER`, `HEAD SNAP`, `MAX STAMINA`, `IRON GUARD`, `CHIN`).
   - Dynamic pre-fight and post-fight *THE RING SUN* newspaper headlines & stories covering KOs, Points Decisions, and Breaking News, with fixed portrait palettes (no cream bleed on Bonecrusher Jones).
   - Automatic `CAREER.DAT` save/resume on HD/VHD (silently skipped on write-protected floppies).
   - Repaired original `.ST` bad-sector sprite corruption in `B2B.CSP` (Hagman) and `B1C.CSP` (Jones) during build.
4. **2-Screen Mode UX & 2-Player Versus (v1.3):**
   - Dedicated **Mode Select** (`CAREER`, `EXHIB`, `2P VS`) before **Mode-Specific Options**; stays in chosen mode until `ESC` backs out.
   - Separate Career vs Exhibition fighting styles (`BALANCED`, `SPEEDSTER`, `HEAVY HIT`, `IRON CHIN`); Career locks style after Fight 1.
   - Symmetric **2-Player Versus** with independent P1/P2 fighting styles, opponent selection, KO Tug-of-War, and mouse-safe **`WASD + LShift`** default (or optional **`JOY 0`** with IKBD mouse-off).
5. **Tactical Stamina, Daze & Focused AI Balance (v1.1–v1.3):**
   - Dual Gold/Red Stamina bars (`y = 26..28`), 3-head-hit **Daze**, 3+ hit combo max-stamina attrition, balanced head vs body risk/reward, KO Uppercut 50% High-Guard break vs tired/dazed opponents, and range-aware focused CPU AI with Killer Instinct.
6. **Native HD, Auto-Booting Floppy & Standalone Bootable VHD:**
   - Fixed-address relocator (`$80000`) + HD GEMDOS fixes (`C:\AUTO\SECONDS.PRG` auto-boot on VHD for TOS 1.04 / 1.62 / 2.06 / EmuTOS / MiSTer).
   - Builds `dist/SecondsOut_Enhanced_v1.4_{HD,Floppy,VHD}.zip`.

## Build & Run

```bash
# Build & package HD, Floppy, and standalone VHD
bash games/done/seconds-out/tools/package.sh

# Cold-boot standalone VHD on 8 MHz STE (TOS 1.62)
bash games/done/seconds-out/tools/run_vhd.sh

# Play on 8 MHz STE (GEMDOS HD)
bash games/done/seconds-out/tools/run_ste.sh

# Play on 16 MHz Mega STE (GEMDOS HD, TOS 2.06)
bash games/done/seconds-out/tools/run_megaste.sh

# Play on 8 MHz STE (auto-booting 720 KB floppy)
bash games/done/seconds-out/tools/run_floppy.sh
```

## Real-Hardware Notes
- **STE Blitter HOG bursts:** Each sprite plane pass and dirty-strip BG copy uses HOG mode (`$c0`) in short 4-line bursts for 100% IKBD safety.
- **PSG / Audio:** No YM2149/PSG registers are modified or hooked by any patch; original XBIOS `Dosound` calls are untouched.
- **RAM requirement:** Requires **1 MB+ ST-RAM** (`_phystop >= $100000`) for the `$80000` fixed relocation and `$90000..$a5fff` precomputed mask cache.
