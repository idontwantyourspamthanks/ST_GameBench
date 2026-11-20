Moonshine Racers for Atari ST - enhanced floppy release v@VERSION@ (dad_prg)
build: {GIT}
==============================================================================

What it is
  The original two-disk Moonshine Racers (Millennium / Peak Star, 1991) converted to plain .ST images (disk_a.st, disk_b.st),
  with the game's code patched: fixed game speed, faster drawing, extra in-between pictures on machines with time to spare, a
  new top-bar HUD, and no manual copy-protection question.  disk_b.st is the original disk 2, unchanged.  PATCHES.TXT lists
  every change.

v1.0.1
  Fixes a frozen mouse pointer in the spare-parts shop after a race (and on the title screen) in v1.0: the shop's EXIT could not
  be used, so the game could not get past race 1.  Nothing else changed.

How to run
  Write disk_a.st / disk_b.st to two floppies (or use them in an emulator / floppy emulator).  1 MB RAM or more.
  Recommended: STE or Mega STE; a plain ST is supported by the code but this set was not booted on one.
  Put disk 1 (disk_a.st) in drive A and boot.  When the game asks you to insert disk 2 either
    - swap disk 2 into drive A and press a key, OR
    - put disk 2 in drive B (if you have a second drive) and press a key.
  With disk 2 already in drive B from power-on there is no prompt at all.
  ONE-DRIVE USERS, what to expect: after a wrong disk in A at the "Insert Disk 2" prompt (the key press before the swap) the prompt
  takes about one second longer to come back (2 s if a second drive is connected but empty).  With the right disk in A nothing
  differs from the original.  Disk 2 in drive B (if there is one) is used automatically.
  Switch off: with the source tree, `python3 tools/msrpatch.py build --floppy --only $(python3 tools/msrpatch.py list | awk '$2 ~ /^yes/ && $1 !~ /^pp_/ && $1 != "fl_driveb" {print $1}')`
  (or `tools/play.sh --floppy --no-driveb`).
  The "Moonshine Racers" title picture (the hot rod, shown while the game loads) carries "v@VERSION@ enhanced by dad_prg" at the bottom.

Game speed
  10 game steps per second, fixed: exact at 50 and 60 Hz, 20 % faster than the original on a stock 8 MHz STE (8.33 steps/s)
  and the same on every CPU clock.  A machine that cannot do a step in time runs late and catches up; it never skips steps.

Extra pictures (smoothness)
  When the machine has time left in a step it draws additional in-between pictures of the same step; the game logic does not
  run in them.  Displayed pictures per second over steered racing (steps after the standing start), measured in Hatari with the
  HD build of the same patches:
     8 MHz STE:          16.0  (an extra picture in 63 % of the steps; the original shows 8.3)
     16 MHz Mega STE:    28.8
     32 MHz:             47.9
  (Floppy release, a different, whole-drive measurement in Hatari: STE 1 MB 15.8 native / 26.6 at 16 MHz.)  None of these are
  real-hardware figures.  Not drawn while the car stands or the race is being set up.

Things that look different from the original (all intended)
  - New HUD: one black bar across the top (score, race clock, position, speed, gear, engine temperature, turbo fuel).  The
    minimap, speedometer, gear lever, thermometer, turbo cup and the clouds are gone; the sky is plain.
  - The talking face is drawn once per message: its mouth no longer moves while a message is typed or held; the same holds for the
    speech/ticker text (unchanged text, box and colours).
  - An extra picture shows the top bar of its own step, and in a collision bounce the two extra pictures of that step still
    show the car before the bounce: a tiny lag in the HUD / bounce in those pictures only.

Mega STE
  Tested in Hatari with TOS 2.06 (4 MB).  The emulator launcher boots the machine at 8 MHz and raises the clock later; whether a
  real machine needs anything similar was not tested; no statement is made.

REAL-HARDWARE CHECK LIST (nobody has run this on real hardware yet - please report)
  Drive 2-3 minutes each time, sky in view at the horizon and over hills:
  1. Sky colour bands: clean, no flicker, no band jumping a line, no colour flash at the horizon.    (tb_blit*, ta_rb, ta_rb0)
  2. Sprites look the same as the original.  STE only; the riskiest item: the blitter is used only between two raster interrupts.
  3. Menus and race-setup screens: the mouse moves the pointer and clicks; in the race joystick/keyboard steer.   (ta_nomouse)
  4. Face area: a radio message while driving: face drawn, mouth held, text and box unchanged.     (ta_facestat)
  5. Disk-2 prompt: swapping disk 2 into A works; with a second drive, disk 2 in B works.    (fl_driveb)

Switching patches off (this zip is a fixed build)
  With the project tree: `python3 tools/msrpatch.py list` shows the patches; `python3 tools/msrpatch.py build --floppy --out DIR`
  builds this set; `tools/play.sh --floppy` takes --no-blit --no-rb --no-nomouse --no-facestat --noextrap --safex N --no-driveb
  (see the HD notes in PATCHES.TXT for what they mean); `build --floppy --only <list> [--set SAFE=3]` for a custom set.

Not tested
  Real hardware (ST, STE, Mega STE), TT, Falcon, MiSTer.  Hatari only: STE TOS 1.62 1 MB and Mega STE TOS 2.06 4 MB.

Credits
  Moonshine Racers: Millennium / Peak Star, 1991.  HAGA conversion technique: PP (the floppy images are converted from the original
  disks).  Enhancements (patches, tools): dad_prg.
