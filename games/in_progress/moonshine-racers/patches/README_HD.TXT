Moonshine Racers for Atari ST - enhanced hard-disk release v@VERSION@ (dad_prg)
build: {GIT}
==============================================================================

What it is
  PP's HAGA hard-disk conversion of Moonshine Racers (Millennium / Peak Star, 1991), with the game's code patched in RAM at
  start-up: fixed game speed, faster drawing, extra in-between pictures on machines with time to spare, a new top-bar HUD.
  The game files are PP's, unchanged.  PATCHES.TXT lists every change.

How to run
  Copy the folder to a hard disk (or any GEMDOS drive) and start RUNME.TOS from the desktop (or put it in AUTO), as PP's version.
  1 MB RAM or more.  Recommended: STE or Mega STE; a plain ST is supported by the code (no blitter sprites there) but this set was not booted on one.
  At the screens press SPACE; a race starts with one SPACE after the position table.  Joystick, or Hatari's cursor keys + right Ctrl.
  The "Moonshine Racers" title picture (the hot rod, shown while the game loads) carries "v@VERSION@ enhanced by dad_prg" at the bottom.

Game speed
  10 game steps per second, fixed: exact at 50 and 60 Hz, 20 % faster than the original on a stock 8 MHz STE (8.33 steps/s)
  and the same on every CPU clock (the original ran about twice as fast on a 16 MHz Mega STE).  A machine that cannot do a step
  in time runs late and catches up; it never skips steps.

Extra pictures (smoothness)
  When the machine has time left in a step it draws additional in-between pictures of the same step; the game logic does not
  run in them.  Displayed pictures per second over steered racing (steps after the standing start), measured in Hatari:
     8 MHz STE:          16.0  (an extra picture in 63 % of the steps; the original shows 8.3)
     16 MHz Mega STE:    28.8
     32 MHz:             47.9
  Other measurements with other definitions (cold-boot windows etc.) are in the source notes, not here.  None of these
  are real-hardware figures.  Not drawn while the car stands or the race is being set up.
  The default margin lets a few steps (8.5 % at 8 MHz) take more than one frame; the build option SAFE=3 is smoother
  (15.3 pictures/s, 1.5 % such steps): see "Switching patches off".

Things that look different from the original (all intended)
  - New HUD: one black bar across the top (score, race clock, position, speed, gear, engine temperature, turbo fuel).  The
    minimap, speedometer, gear lever, thermometer, turbo cup and the clouds are gone; the sky is plain.
  - The talking face is drawn once per message: its mouth no longer moves while a message is typed or held; eyes etc. as before.
    The message text/ticker are the same.
  - An extra picture shows the top bar of its own step, and in a collision bounce the two extra pictures of that step still
    show the car before the bounce: a tiny lag in the HUD / bounce in those pictures only.  Normal pictures are as the original.
  - Everything else, including the game state at every step, equals the original game on every pass that was compared.

Mega STE
  Tested in Hatari with TOS 2.06 and 1 MB: the emulator launcher boots it at 8 MHz and raises the clock after the TOS start.
  Whether a real machine needs anything similar was not tested; no statement is made.

REAL-HARDWARE CHECK LIST (nobody has run this on real hardware yet - please report)
  Drive 2-3 minutes each time, sky in view at the horizon and over hills:
  1. Sky colour bands: clean bands, no flicker, no band jumping a line, no colour flash at the horizon.   (tb_blit*, ta_rb, ta_rb0)
  2. Sprites (cars, scenery) look the same as the original.  STE only: this is the riskiest item - the blitter is used only
     between two raster interrupts; Hatari does not model a real STE bus.                              (tb_blit*)
  3. Menus and race-setup screens: the mouse moves the pointer and clicks; in the race joystick/keyboard steer and accelerate. (ta_nomouse)
  4. Face area: a radio message while driving: face drawn, first mouth frame held, text and box unchanged.   (ta_facestat)
  5. Top bar: the gauges step once per game step; nothing flickers or tears; frame spacing acceptable.     (mg_sync, mg_pace)

Switching patches off (this zip is a fixed build)
  The sources are in the project tree, not in this zip.  With the tree: `python3 tools/msrpatch.py list` shows the patches;
  `python3 tools/msrpatch.py build --out DIR` builds this set; `tools/play.sh` (Hatari) takes one switch per patch group:
     --no-blit (tb_blit, tb_blit11, tb_blit13, tb_blit15)   --no-rb (ta_rb, ta_rb0)   --no-nomouse (ta_nomouse)
     --no-facestat (ta_facestat; ta_face instead)   --noextrap (mt_sync instead of mg_sync + mg_pace: fixed tick, no extras)
     --safex N (build option SAFE=N; 3 = smoother)
  For a real machine: `python3 tools/msrpatch.py build --only <the list without the unwanted names> --out DIR`
  (add `--set SAFE=3`), then copy DIR.  The default list is `python3 tools/msrpatch.py list` (column default = yes).

Not tested
  Real hardware (ST, STE, Mega STE), TT, Falcon, MiSTer.  Hatari only: STE TOS 1.62 (1 MB, 4 MB), Mega STE TOS 2.06 (1 MB).

Credits
  Moonshine Racers: Millennium / Peak Star, 1991.  HAGA hard-disk conversion: PP.  Enhancements (patches, tools): dad_prg.
