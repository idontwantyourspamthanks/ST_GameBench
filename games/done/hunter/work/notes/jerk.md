# Hunter jerkiness on TT / Mega STE: why the user's output differs from the memory traces (HunterJerk)

Status: **mechanism NOT found yet**. Everything reproducible headless or on the user's real display is smooth. This file lists what was
reproduced, what was excluded (with raw numbers) and what is left. Tools: `/tmp/jerk/*` (run_variant.py, probe2.py, real.py, avihash.py, trace.py; scratch, not in the repo).

Tags: **[obs]** measured here; **[src]** Hatari source `/home/ryan/Code/hatari-pist/src` (newer fork than the installed 2.6.1); **[INFERENCE]** unproven.

## 1. The user's recording (tt_2026-11-13_162541.avi) [obs]
- 640x516 AVI, 3337 frames, audio 2,629,348 samples. One AVI frame per emulated VBL: 1201 frames at 50 Hz (game) + 2135 at 60 Hz (TOS desktop/HW screen/title) reproduce the audio length exactly (882 / 735 samples per VBL). So the AVI is NOT sampling the emulation; their emulated game really draws a picture every 3..11 VBL.
- Hash of the top 640x320 per frame from the walk start (frame 2940): 397 frames, 52 changes; gaps `3 3 3 3 2 3 ... 8 8 8 9 9 10 10 10 11 ...`. At game start (first 3D frame) the cadence is already every 3 VBL: `.X.X..X..X..X..X.XX..X..XX.X..X..X..X....X.......X.......X`.
- The ST mouse pointer (grey arrow in the message strip, ST (133,189), clipped by the screen bottom) disappears for exactly 1 VBL at every game frame, same cadence (8,8,8,9,9,10,10,10,11): a software sprite redrawn after each flip. It is a normal pointer (nothing special; my runs have it off-screen at y=51 `$da`).
- The AVI geometry (640x516 = 640x480 game + 36 statusbar, 200 ST lines stretched x2.4) is a consequence of `--avirecord` from power-on (the AVI keeps the desktop's 640x480 surface). Reproduced with `--avirecord` at power-on: same 640x516, same stretch. It does NOT change the rate.
- Boot timeline is VBL-identical between their run and mine until the game starts (scene-change frames: HW screen, title, menu: gaps 116 / 44 / 6 / 2 VBL equal in both). The two runs diverge only in the 3D loop.
- Their first 140 3D frames sampled every 10 VBL show the same views as mine (world time is VBL-based), so game speed is compensated; only the picture cadence differs.

## 2. What I ran (all NEW game, mission 1 "destroy 6 fuel dump", HQ start, standing + walking Up 12 s) [obs]
All with a scratch copy of `~/.config/hatari/hatari.cfg` (= `1040stfm.cfg`: CE, compatible, PatchTimerD, DataCache, VideoTiming 2, FrameSkips 0, Joystick1 real; `--configfile` MUST be the first argument: Hatari reloads the config where it sees the option and drops earlier options, see wrapper `/tmp/jerk/bin/hatari`), image `dist/AtariST_enhanced_games_2026-11-13.img` (scratch copy + autorun), `--sound 44100`, Hatari's `--avirecord`/`recanim` AVI (png level 3, 60 fps), per-VBL hash of the 3D window. Walking, changes per 50 AVI frames:

| variant | change vs run_tt.sh | walking fresh pictures/s (AVI) | memory trace (breakpoint `$c5f0`, 3 pages) |
|---|---|---|---|
| A | harness defaults + `--joy1 keys` | 50 (911 changes / 1036 frames incl. standing) | - |
| B | `--joy1 real` = the host's T300RS wheel (js0, axis1 pegged 32767) | 49-50 | - |
| C | exact run_tt.sh line (harness flags removed: no `--harddrive`, no `--fast-boot yes`, no `--sound off`) | 48-50 | - |
| D | C + real PulseAudio sink (null sink) instead of SDL dummy audio | 50 | 42.4/s (3 pages sample) |
| E | C with dummy audio | 50 | 42.6/s |
| F | C + `--avirecord` from power-on (their AVI geometry) | 50 | 43.9/s |
| G | F + `bKeepResolution=FALSE` | 50 | - |
| H/I | ST pointer moved to bottom / top with xdotool | 50 | 43.5/s |
| K | default soldier name (no typing, as the user's "Trigger Happy") | 50 | 43.2/s |
| mouse | 125-250 xdotool motion events/s (2-3 px) over the window while standing/walking (snapshot and cold boot) | 50 | 45.3/s |
| real display | snapshot restored in a window on the user's real :0 (Wayland/XWayland, default SDL driver), host ran 0.51x real time | loop-top 31.8 fps over 300 VBL at 0.51x host speed, AVI 50/50 changes | 0 samples changed standing |
Memory-fresh (42-45/s) and AVI-fresh (50/s) agree: nothing is lost between the pages the game shows and Hatari's output on the headless/real display paths. Hw base `$ff8201/03` alternates `$23000`/`$2ad00` once per frame, as the game's flip writes it.

## 3. Excluded [obs]
Input device (wheel as real joystick, cursor-key joystick, none), real vs dummy audio, AVI from power-on, window/surface size, bKeepResolution, display (Xvfb vs the user's Wayland session), soldier name, pointer position, mouse motion storms, the AVI recorder (audio/video lockstep proven above). Host timing: `hatari-pist` has no emulated state that reads host time except the RTC (`rtc.c`, `falcon/nvram.c`) and input events [src]; the user also rejects host overload.
`hatari-event keydown 30` (ST key 'A' = drone) stops the game loop (150 VBL/frame) - input CAN change the loop, but not anything the user does.

## 4. Left (the 3-12x heavier frame must come from emulated state) [INFERENCE]
Their first 3D frame already takes 3 VBL where mine takes <= 1 for the same scene (TT 8 MHz measured by HunterTT: 3.96 VBL/frame standing at HQ - matches 3), growing to 11 (HQ-near scenes heavier). That looks like the 68030 running at an effective 8 MHz-ish speed (caches off / different CPU core), or an interrupt (ACIA ISR at `$afde` spins on GPIP4 `btst #4,$fa01` and blocks the level-4 VBL) eating most of the CPU. I could not test CACR / ISR load in their run. The next measurement is in their live session: `hatari-debug r` (CACR, SR, IPL), `profile`, `m $ff8200 16`, `$1a6/$1a7`, `$ab2` pose, the ACIA status `$fffc00`; compare with my smooth state `/tmp/jerk/game_tt.sav` (CACR `$3111`, 1 VBL/frame, `$1a7`=0). Waiting for the files from Main.
