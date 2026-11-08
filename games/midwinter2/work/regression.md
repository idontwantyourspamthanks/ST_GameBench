# P6 Regression report

Builds: `build/game` (default patch set, `verify: ALL OK`) and `build/none` (`mw2patch.py build --only --out build/none`, 0 patches, payload 7936 B).
Hatari 2.6.1, harness `tools/mw2harness.py`. Runner: `work/regress/run_cell.py` (boot_to_game('M'), checks 1-3). Per-cell logs and screenshots are in `work/regress/<cell>.out|.json|_3d.png|_walk.png|_turned.png`. Extras used the interactive screenshots `work/regress/ex_*.png`.

Check definitions as run:
- **C1**: `boot_to_game('M')` reaches `$6220==$d && $700a==2`, and `m $b2ff8 4` reads `MWPO`.
- **C2**: `rel(0,-200)`, `center()`, `rel(0,-200)`, sleep 10 s, then `world_rate(vbls=500)` (`$6888` rate, fps).
- **C3**: `rel(-150,0)`, then `$6742` sampled every 1.5 s for 12 s.

## Hatari restrictions found (affect the matrix)

- **Mega STE with TOS 1.62** cannot be emulated. Hatari log (`/tmp/mw2run-ar8y8alz/log.txt`):
  ```
  ERROR: TOS versions 1.06 and 1.62 are for Atari STE only.
   ==> Switching to STE mode now.
  ```
  The harness then died on `shot()` (IndexError: no screenshot). TOS 1.02 and 1.04 on megaste/tt/falcon give "TOS versions <= 1.4 work only in ... Switching to ST mode with 68000 now".
- **Mega STE, TT, Falcon**: no Atari TOS 2/3/4 image exists on this machine (`~/Emulators/BIOS/AtariST/`, `/usr/share/hatari`). EmuTOS 1.4.0 was found at `/usr/lib/pist/share/emutos/etos1024k.img`, which was already installed and not downloaded. It is used for **megaste, tt and falcon** (and for an ste cross-check). Those cells test our patches on EmuTOS, **not** original TOS. EmuTOS runs at 60 Hz, so the screenshot size differs: 640x436 on TT, 648x602 on Falcon. The runner shifts the `screen_matches` crop for those cells (TT offset -96,-58 was found by exact template match, diff 0.0; Falcon was auto-searched).
  - Update: `tos/TOS_2_06.img` (Atari TOS 2.06) is in the project and works for `--machine megaste`; rows C-fix and P4 and `work/bigram/*.out` use it.
- **Mega STE at 16 MHz with TOS 1.62** is covered by the equivalent "STE TOS 1.62 + `set_cpuclock(16)`" cell, plus a true megaste/EmuTOS/16 MHz cell.

## Matrix (checks 1-3)

| Cell | Machine / TOS / RAM / clock | C1 boot + MWPO | C2 walk (`$6888` rate, fps) | C3 turn `$6742` | Evidence |
|---|---|---|---|---|---|
| A | STE / 1.62 / 1 MB / 8 MHz, `build/game` | **PASS** | **PASS** +27.5/s, 4.5 fps | **PASS** | `ste1_game.out` |
| A0 | control: same, `build/none` | PASS (MWPO marker is present even with 0 patches) | +18.4/s, 4.3 fps (rate-model) | no turn at dx -150 (baseline; the unpatched yoke model needs about -450) | `ste1_none.out` |
| B | ST / 1.04 / 1 MB, `build/game` | **PASS** | **PASS** +28.0/s, 4.5 fps | **PASS** | `st1_game.out` |
| C | STE / 1.62 / **4 MB**, `build/game` **as first built (before `pp_bigram_cache`)** | **FAIL** (never leaves the FLAMES OF FREEDOM title). Cause: OUR payload at `$B3000` is zeroed by PP's whole-image cache read, see `work/notes/bigram.md`. Fixed by `patches/pp_bigram_cache.s` | not run | not run | `ste4_game.out`, `ste4_game_exc.png` |
| C0 | "control": same, `build/none`, polled up to 15 min. **Not an unpatched control**: `build/none` has 0 patches but still contains our RUNME staging (payload copied to `$B3000`), so it fails identically. The really pristine game (original `RUNME.TOS`/`HAGA`) reaches the 3D view at 4 MB (row P4 below) | FAIL, identical (same cause as C) | n/a | n/a | `ste4_none.out`, `ste4_none_long.out`, `ste4_none_long_long_exc.png` |
| C-fix | **Re-test after the fix**, Mega STE TOS 2.06 / 4 MB, `build/game` (default set + `pp_bigram_cache`) | **PASS** | **PASS** (`$66e6` moves) | not run | `work/bigram/mste206_4mb_fix.out` |
| C-fix2 | STE TOS 1.62 / 4 MB and Mega ST TOS 1.04 / 4 MB, `build/game` | **PASS**, **PASS** | **PASS**, **PASS** (`$66e6` moves) | not run | `work/bigram/ste162_4mb_fix.out`, `work/bigram/st104_4mb_fix.out` |
| P4 | **pristine** (original `RUNME.TOS`/`HAGA`, no staging), Mega STE TOS 2.06 / 4 MB | PASS (no `MWPO`: nothing of ours is installed) | PASS (`$66e6` moves) | not run | `work/bigram/mste206_4mb_pristine.out` |
| D1 | STE / 1.62 / 1 MB, 16 MHz (set after boot) | **PASS** | **PASS** +27.9/s, 9.7 fps | **PASS** | `ste16_game.out` |
| D2 | Mega STE / EmuTOS 1.4 / 1 MB / 16 MHz | **PASS** (1 recovered click) | **PASS** +26.0/s, 6.2 fps | **PASS** | `mste_etos_game2.out`, `mste_etos_game2_3d.png` |
| D3 | Mega STE / **TOS 1.62** | **UNTESTABLE** in Hatari | - | - | Hatari log above |
| E | TT / EmuTOS 1.4 / 1 MB ST-RAM, 32 MHz 030 | **PASS** | **PASS** +26.1/s, **25.4 fps** | **PASS** | `tt_game.out`, `tt_game_3d.png` |
| F | Falcon / EmuTOS 1.4 / 1 MB, 16 MHz 030 | **PASS** | **PASS** +27.4/s, 15.2 fps | **PASS** | `falcon_game.out`, `falcon_game_3d.png` |
| X | STE / EmuTOS / 1 MB (cross-check), `build/game` | PASS | PASS +25.5/s, 3.7 fps | PASS | `ste_etos_game.out` |

Notes on the table:
- **The world rate is the same on every machine** (25.5-28.0 units/s at fps 3.7-25.4). Unpatched, it is 18.4/s at 8 MHz (and 45.9/s at 16 MHz per `work/baseline.md`). The rate no longer depends on CPU speed, which is the P3 tick goal.
- **C1 raw lines** (identical in A, B, D1, D2, E, F, X):
  ```
  6220=d 700a=2
  > m $b2ff8 4
  000B2FF8: 4d 57 50 4f                                      MWPO
  ```
- **C3 raw series**:
  - A: `['0x300', '0x2c6', '0x2c6', '0x2c6', '0x2c6', '0x2c6', '0x2c6', '0x2c6', '0x2c6']`
  - B: same as A.
  - D1: `0x300, 0x2c4, 0x2c4 ...`.
  - F: `0x300, 0x2c4 ... 0x2c4`.
  - A0: `0x300` x 9.
- **Observation (not a fail verdict): the 9th C3 sample is `0x0` in D2, E and X** (`... '0x2c4', '0x2c4', '0x0'`). The first 8 samples, covering about 10.5 s, were constant.
  - `ste_etos_game_turned.png` and `tt_game_turned.png` show a changed game state at that moment: compass N, ammo counter changed, a black 3D frame. That looks like a scene or state change, not the turn model.
  - The 1.62 cells never did this within the same 12 s. The A, B and D1 samples are constant at 0x2c4/0x2c6 for all 9 samples.
  - Cause not determined. The unpatched control cannot show it, because it never turns at -150. [INFERENCE: a game event in the later part of the walk on the 60 Hz EmuTOS runs; unverified.]
- **Harness flake**: on EmuTOS megaste and on `--joy1 keys` STE, `boot_to_game` stalls on the "MISSION OBJECTIVE 1" screen (`mste_etos_game_exc.png`, `ex_m_joy.png`). The `?` click is missed. The unpatched control showed the same stall (`mste_etos_none.out`), so this is harness navigation, not our patches. Re-clicking `?` then thumbs-up reaches the 3D view.
- **Cell C (4 MB) was NOT a game or emulator problem, and not the original game's.** The previous version of this note ("patched and unpatched both stay on the FoF title ... a game or emulator problem at 4 MB, not caused by our patches") was wrong: its "unpatched" control (`build/none`) still carried our RUNME staging, which writes the payload to `$B3000`.
  - On a >= 4 MB 68000 machine PP's HAGA init switches the stub's disk cache to whole-image mode (`Fread(64, 737280, $81000)`), which overwrites `$81000-$135000` and so zeroes our payload at `$B3000-$B4EFF`. The game then returns into zeros and hangs after the FoF title (evidence: `work/notes/bigram.md`, section "Evidence").
  - Pristine game at 4 MB: reaches the 3D view (`mste206_4mb_pristine.out`: `6220=d 700a=2`, position changes).
  - Mega STE with TOS 2.06 was in fact testable once `tos/TOS_2_06.img` was available; the "no TOS 2" statement at the top of this file applies to the machine TOS directory searched then.
  - The status bar showed `8MHz(CE)/- 4MB STE, TOS 1.62` (`ste4_game_exc.png`); that was correct, only the conclusion was wrong.

## Extra checks (STE 1.62, 1 MB, `build/game`)

### 4. In-game save / load: **PASS**

- **Save**
  - F10 in the 3D view opens SAVE CAMPAIGN / ABORT MISSION / CONTINUE ACTION (`ex_f10.png`).
  - Click SAVE: screen "OPERATION 'TEST' SAVED" (`ex_save1.png`).
  - FFD md5 before `9e1f74d51d2d670eaf214c3ee1bddf2f` and after `73b9108daae83c2badee2ec12c14a38e` (size 737280, non-zero sectors 1389 to 1392).
- **Load**
  - ABORT MISSION goes to the HQ corridor (`ex_abort.png`), then the war room (`ex_war.png`).
  - LOAD EXISTING CAMPAIGN gives the load-icon prompt (`ex_load1.png`), then "CURRENT MISSION STATUS: GAVIN STEEL / OPERATION TEST / 2 January / Lobos / Helicopter" (`ex_load2.png`).
  - Continue returns to the 3D view (`$6220=0xd $700a=0x2`) with the saved clock 12:20 (`ex_load3.png`).
- **Other F keys found**, for reference: F2 rest, F5 map, F6 stats, F7 diary, F8 objectives, F9 weapons, `p` pause.

### 5. HAGA savestate / exit: **PASS** (restore works)

- **Save**: numpad `/` (KP_Divide) in the 3D view created `C/GS00.TOS`, 525022 bytes (`ex_kpdiv.png`; before/after file diff of the C: scratch dir).
- **Exit**: numpad `*` (KP_Multiply) goes to the GEM desktop (`ex_desktop.png`; GEM desktop with the A:, B:, C: HARD DISK and TRASH icons).
- **Restore**: double-click C: and then `GS00.TOS` (`ex_hd3.png`). The game came back in the 3D view at the saved clock 12:24 (`ex_restore.png`, `$6220=0xd $700a=0x2`).

### 6. Campaign creation: **PASS**

- **Set-up**: `build/blank` is a copy of `build/game` without `work/`, so its FFD is the shipped blank one. Start FFD: 2 non-zero sectors.
- **Click sequence** (screenshot coordinates, all via `goto`):
  1. PERSONNEL (554,105).
  2. USE THIS AGENT (389,140).
  3. War-room door (185,260).
  4. START NEW CAMPAIGN (230,100).
  5. Type `test` + Return (`ex_c_new1.png`, `ex_c_new2.png`).
  6. CREATE CAMPAIGN DISK (270,312).
  7. Copy icon (230,252) gives "Insert MISSIONS disk" (`ex_c_new3.png`). **Click the copy icon repeatedly**, once about every 40 s. Each click moves the prompt between MISSIONS and CAMPAIGN (`ex_c_new4.png`, `ex_c_new5.png`).
- **Result**: non-zero FFD sectors grew 2, 338, 674, 1029, 1389. Final state is the SAVE CAMPAIGN prompt (`ex_c_new6.png`). The final count is 1389 (PLAN.md records 1389 as the expected value). FFD size 737280.
- Waiting without clicking just idles at the prompts: two 10-minute waits showed 2 sectors.

### 7. Joystick mode: **PASS** (via the poke route)

- **Direct J**: `boot_to_game('J')` with `extra=['--joy1','keys']` failed as predicted (`ex_j_fail.png`, `did not reach the 3D view ($6220=0x0)`; it stalls in the corridor).
- **Poke route**:
  - `boot_to_game('M')` plus manual `?` and thumbs-up clicks reaches the 3D view. M-mode reads `$eb76,$eb78,$eb7a = 0000,0000,ffff`.
  - `memwrite $eb76 0xff 0xff 0 0 0 0` sets J-mode: reads `['0xffff','0x0','0x0']`.
- **Held Left for about 3.2 s** (xdotool keydown/keyup of `Left`, with `--joy1 keys`). `$6742` sampled at about 1.4 s intervals (VBL in the third column):
  ```
  (0.0, '0x300', 19624)
  (1.4, '0x25e', 19694)
  (2.8, '0x1a8', 19764)
  ('rel', '0xe0', 19885)   # after key up
  ('rel', '0xe0', 20006) ... ('rel','0xe0', 20486)   # six samples, constant
  ```
  - Per-sample drops are 162 and 182 heading units per 70 VBL. That is a constant rate, with the difference down to the 4.4 fps frame quantisation. The turn continued until key release and then stopped and stayed at 0xe0 for 6 s.
  - Screenshot `work/regress/ex_j_turn.png`.
  - Sampling resolution is coarse (each sample costs about 70 VBL), so "stops within 1 frame" was **not** measured here. That belongs to the P5 gate tests.

## Not done / limits

- `build/none` is NOT a pristine control: it has 0 patches but still contains our RUNME staging. It was run on STE 1 MB (A0), STE 4 MB (C0, which failed because of the staging, see `work/notes/bigram.md`), EmuTOS megaste (nav stall), and EmuTOS STE. The truly pristine game (original files) was run at 4 MB and 1 MB on Mega STE TOS 2.06 (`work/bigram/mste206_4mb_pristine.out`, `mste206_1mb_pristine.out`).
- C3 for D2/E/X ends with the unexplained `0x0` sample described above.
- Mega STE with an Atari TOS is covered only by TOS 2.06 (`tos/TOS_2_06.img`, added later, see rows C-fix/P4 and `work/notes/bigram.md`); TT/Falcon results are on EmuTOS, not Atari TOS 3/4 (none available).
