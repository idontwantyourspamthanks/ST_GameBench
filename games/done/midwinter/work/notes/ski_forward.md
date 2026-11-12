# "Can no longer move forwards on skis" (user report, TT, joystick and mouse): NOT reproduced (MW1Ski, 2026-11-12)

Raw logs and scripts: `work/ski_forward/` (`fwd.py` = the matrix run, `logs/*.log`, `logs/TABLE.txt`; `reenter2.py`, `head.py`, `skistate.py`, `reenter.py` = follow-up probes). Hatari 2.6.1, host `~/.config/hatari/hatari.cfg` (cycle-exact CPU, `bPatchTimerD = TRUE`, `bFastBoot = FALSE`, Joystick1 = real stick; the harness adds `--fast-boot yes`).
No patch was changed: there is nothing to fix, so the mw1ab gate was not re-run (no code differs from HEAD).

## 1. What was tested
* **(a) = the user's build.** `mw1patch.py build --only <default set minus jag_*> pp_nofade pp_bigram_cache --out build/MW1Ski/a` (the v1.1 set of 2a8d881: `git diff --stat 2a8d881 HEAD -- patches` lists only `jag_*` and README as new; no worktree needed). **Byte identity with the user's drive image** (mtools extract of `MIDWINTR` from `dist/AtariST_enhanced_games_2026-11-11.img`, built 2026-11-11 16:44):
  ```
  7ffa1f6a6e32f2095ef37059d48ca863  build/MW1Ski/a/RUNME.TOS
  7ffa1f6a6e32f2095ef37059d48ca863  /tmp/MW1Ski/vhd/RUNME.TOS     (cmp a/HAGA vhd/HAGA: identical)
  c384811a77ffb129285c98cf59cf7c81  build/MW1Ski/b/RUNME.TOS      (b = current default, with jag_*)
  ```
* **(b)** = current default (`build --out build/MW1Ski/b`, 58 patches incl. `jag_vbl/mrg/btn/rmp`). **(c) stock** = the game dir as shipped (`RUNME.TOS` + `HAGA` from PP).
* **vhd** = the user's image itself, booted the user's way: ACSI + HDDRIVER, `--gemdos-drive skip --acsi 0=<scratch copy>`, `DESKTOP.INF` autorun line for `C:\MIDWINTR\RUNME.TOS` (`tools/test_hd_image.py` helpers), TT flags of `dist/run_tt.sh`: `--machine tt --tos TOS_3_06_uk --memsize 4096 --cpuclock 32 --monitor vga --mmu true` (VGA 60 Hz in the status bar).
* Every run is a **cold boot** to Game Options -> control mode M/J/K (RAM check `control_mode()`) -> PLAY -> Team -> Stark -> Decisions -> Skiing; Game Options toggles Mortars/Bombers off, Training on (harness default), `FWD_DEF=1` = the shipped defaults (Mortars/Bombers ON, Training OFF).
* "Forward the way the manual says" (`work/manual-proper.md` lines 118-135, 45-52): standing, **left button sets you walking** (M: left click; J: fire = Control_R with `--joy1 keys`; K: `<` = scancode 51); then the lever: mouse back/forward (M), stick Down/Up (J), KP2/KP8 (K); right button / `>` (scancode 52) stops. Sampled every ~1 s over the debugger: VBL, position `$12c60`/`$12c64` (x, z), speed `$15112`, buttons `$24fba`, lever `$24fae`, `$152a8`, state `$13542`.

## 2. Table: build x mode x machine, "moves forward" (first walk, 7 s after the click; raw: `logs/TABLE.txt`)
```
log                  build  mode machine   z(walk0) z(walk7) dz    maxspeed dVBL moves
a_J_ms               a      J    megaste    25650   28404   2754    361   463  YES
a_J_ste              a      J    ste        25657   28425   2768    361   386  YES
a_J_tt               a      J    tt         25679   28434   2755    359   462  YES
a_K_ms               a      K    megaste    25650   28404   2754    361   463  YES
a_K_ste              a      K    ste        25657   28404   2747    361   386  YES
a_K_tt               a      K    tt         25679   28425   2746    361   463  YES
a_M                  a      M    ste        25618   28338   2720    356   386  YES
a_M_ms               a      M    megaste    25636   28383   2747    356   463  YES
a_M_tt               a      M    tt         25630   28361   2731    356   463  YES
a_M_tt_shots         a      M    tt         25618   28503   2885    359   504  YES
b_J_ms               b      J    megaste    25657   28404   2747    361   463  YES
b_J_ste              b      J    ste        25664   28404   2740    361   386  YES
b_J_tt               b      J    tt         25643   28383   2740    361   463  YES
b_K_ms               b      K    megaste    25694   28443   2749    359   463  YES
b_K_ste              b      K    ste        25657   28404   2747    361   386  YES
b_K_tt               b      K    tt         25664   28404   2740    361   462  YES
b_M                  b      M    ste        25618   28338   2720    356   385  YES
b_M_ms               b      M    megaste    25643   28373   2730    356   462  YES
b_M_tt               b      M    tt         25630   28361   2731    356   463  YES
stock_J_ste          stock  J    ste        25664   28250   2586    352   386  YES
stock_K_ste          stock  K    ste        25664   28250   2586    352   386  YES
stock_M_ms           stock  M    megaste    25630   28811   3181    346   462  YES
stock_M_ste          stock  M    ste        25630   28511   2881    351   421  YES
vhd_J_tt             vhd    J    tt         25679   28425   2746    361   462  YES
vhd_J_tt_noFastBoot  vhd    J    tt         25643   28383   2740    361   462  YES
vhd_M_tt             vhd    M    tt         25630   28361   2731    356   462  YES
```
Condensed (all rows YES, z grows about +2700 in 7 s, peak speed `$15112` 346-361, HUD about 55 mph):

| build | STE 1 MB TOS 1.62 (M / J / K) | Mega STE 4 MB TOS 2.06 (M / J / K) | TT 4 MB TOS 3.06 `--mmu true` vga 32 MHz (M / J / K) |
|---|---|---|---|
| (a) v1.1 = user's build | YES / YES / YES | YES / YES / YES | YES / YES / YES |
| (b) current default (+jag) | YES / YES / YES | YES / YES / YES | YES / YES / YES |
| (c) stock | YES / YES / YES | YES (M only run) | n/a (see 4) |
| user's drive image `.vhd` via ACSI, run_tt.sh flags | | | YES / YES / - (M, J; J also with `--fast-boot no`: YES) |

Same trajectory in all builds, e.g. TT, drive image, M (`logs/vhd_M_tt.log`) and stock STE (`logs/stock_M_ste.log`):
```
vhd M tt  walk0 vbl=5796 z=25630 speed=120 | walk3 z=26595 speed=265 | walk5 z=27464 speed=356 | walk7 z=28361 speed=235 | walk9 z=28663 speed=48
stock STE walk0          z=25630 speed=120 | walk3 z=26491 speed=263 | walk5 z=27411 speed=351 | walk7 z=28511 speed=161 | walk9 z=28701 speed=44
```
The screen changes while walking (TT, a, M: image difference between consecutive screenshots 5-24 grey levels per 1 s step, `/tmp/MW1Ski/shots_a_M_tt`; screenshot of the moving view with `51mph` HUD was inspected).

## 3. Observations that look like "no forward motion" but are the original game (identical in stock)
All of these are measured the same in the stock game (logs `stock_*`, `re2_stock_*`, `re3_stock_*`, `re4_stock_*`, `head_stock_*`):
1. **Standing, mouse/stick forward does nothing**: the lever only matters once walking (manual: "Clicking on the left mouse button sets you walking. Your walking speed may be increased by pushing forward"). In J mode the walk key is the fire button, in K `<`.
2. **The start walk runs into a rise**: at z about 28500 the speed collapses from 356 (HUD 55 mph) to 44-51 (HUD 7 mph) even with the lever at its maximum `-512` (`walk7..walk9` above; `a_M_tt_def.log` walk8-walk17: 92, 48, 45, 46 ... 51). Heading 0 = +z; turning around gives full speed again (`head_*.log`, speed 271 at heading 512).
3. **"Skiing" state is slower, not faster**: a left click when the terrain term `$4d66-$96+$15116` is below `$1f4` (`$13454`) starts the true skiing state (`$13408`/`$13426`): speed = lever x 16 / 64 (`$13432 asl.w #4,d0 ; move.w d0,$152a8` ... `$13478 asr.w #6,d1 ; move.w d1,$15112`), lever starts at `-213` => constant speed **53** (HUD 8 mph); the mouse/stick forward raises it by the lever only (max 128). Seen on the 2nd/3rd entry into the skiing mode (positions around z 25000): patched and stock give the same `speed=53 lever=-213 st13542=ffcb`; pushing forward gives `lever=-273 speed=68` (M, STE; stock and patched) and `lever=-427 speed=106` (J, TT, patched):
   ```
   re4_stock_M_ste  r2 walk2 z=24948 speed=53 lever=-213 | pushed forward | walk3 z=25143 speed=68 lever=-273
   re4_a_M_ste      r2 walk2 z=25204 speed=53 lever=-213 | pushed forward | walk3 z=25329 speed=68 lever=-273
   re4_a_J_tt       r2 walk2 z=25215 speed=53 lever=-213 | stick Up 1.5 s  | walk3 z=25522 speed=106 lever=-427
   ```
4. With the **shipped Game Options (Mortars/Bombers ON, Training OFF)** the action mode ends by itself after about 17 s of walking (`a_M_tt_def.log`: `act=1` from `walk17`; the world position stops at z=29117, speed shows 51 in the last row because the loop is gone). Cause not investigated [INFERENCE: an enemy event, as `tools/mw1.py boot_to_game` docstring says for these toggles]; not tested with the stock game.

## 4. Not testable / not done
* **Stock on the TT**: with PP's unpatched `RUNME.TOS`/`HAGA` the Game Options screen is never reached (GEMDOS folder: desktop; image with `original=True`: 600 s without options). `README.TXT` of the image says the same ("On a TT the Midwinters did not start from an ACSI/HDDRIVER disk there (PP's unpatched versions neither)"). The patched build starts (section 2).
* A real TT (hardware), real joystick/mouse, the user's exact Hatari command line: unknown. `--ttram 16` was tried and failed on a harness screenshot error before the game started (not retried to the end).
* Pressing keys/clicks with a host mouse that is not grabbed by Hatari: not tested.

## 5. What the user may be doing differently (hypotheses; none proven)
* Not clicking/firing first (section 3.1), or holding the button instead of one click ([INFERENCE from `$133c2..$133d0`: with the speed command `$152a8` below `$13540` a held left button re-enters the skiing state at the slow constant speed 53, section 3.3; not run with a held button).
* Standing at the first rise (section 3.2, 7 mph) or in the slow skiing state (3.3) and reading it as "no forward motion"; pushing the mouse forward only adds to the lever (max speed 128 in skiing), pulling back removes it.
* A Hatari setup without `--mmu true` on the TT (HAGA trashes TOS, `tt.md` section 3; `run_tt.sh` has had `--mmu true` since its first commit 014128a, 2026-11-11 12:47) or a different joystick mapping: [INFERENCE] Hatari port 1 is the ST joystick port (the user's cfg: Joystick1 = real stick); `--joy1 keys` maps cursor keys + Right Ctrl here. The fire button of the real stick may be another button than the one pressed.
* If a screenshot/log of the failing session (control mode, Game Options toggles, what the HUD speed shows after the click) is available, the numbers `$15112`, `$13542`, `$24fba`, `$24fae` above identify which of the cases applies.

## 6. Conclusion
(a) the user's v1.1 build, (b) the current default with the Jaguar patches and (c) the stock game all move forward in M, J and K on a 1 MB STE; (a) and (b) also on a 4 MB Mega STE and on the TT (TT with the user's own image booted through ACSI/HDDRIVER with the `run_tt.sh` flags). Because nothing fails, there is no patch to bisect; `p5_ctl_*`, `p3b_*`, `p4_*`, `p7_*`, `jag_*` are not implicated (the position/speed trajectories of (a), (b) and (c) agree to the sample).
