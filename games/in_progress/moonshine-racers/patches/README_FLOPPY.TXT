Moonshine Racers for Atari ST - enhanced floppy release v@VERSION@ (dad_prg)
build: {GIT}
==============================================================================

What it is
  The original two-disk Moonshine Racers (Millennium / Peak Star, 1991) converted to plain .ST images (disk_a.st, disk_b.st),
  with the game's code patched: fixed game speed, faster drawing, extra in-between pictures on machines with time to spare, a
  new top-bar HUD, and no manual copy-protection question.  disk_b.st is the original disk 2, unchanged.  PATCHES.TXT lists
  every change.

v1.1
  New: CAMPAIGNS.  Track sets made with the track tool (tools/msrtrack.py: a file MSTRACKS.TRK, put on a 720 KB campaign disk with
  `msrtrack.py disk`) replace the 15 tracks; see "Campaigns" below.  Needs an ST, Mega ST, STE or Mega STE with 2 MB or more; on a
  machine with 1 MB, a TT or a Falcon the game is exactly the v1.0.1 game.

v1.0.1
  Fixes a frozen mouse pointer in the spare-parts shop after a race (and on the title screen) in v1.0: the shop's EXIT could not
  be used, so the game could not get past race 1.

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

Campaigns (ST, Mega ST, STE and Mega STE with 2 MB or more only)
  A campaign disk is a normal 720 KB (80 tracks, 9 sectors) PC/TOS floppy with the single file MSTRACKS.TRK in its root directory,
  made with `python3 tools/msrtrack.py disk ...` (the file must be stored in consecutive clusters; `msrtrack.py validate X.st`
  checks that).  Nothing on disk 1 or disk 2 changes.
  On the title screen (the face and the typing text, or the hi-score table) press F10:
     ORIGINAL GAME                  start the original game at once and switch the campaign off (a loaded campaign stays in memory)
     LOAD CAMPAIGN FROM DRIVE A     read A:\MSTRACKS.TRK
     LOAD CAMPAIGN FROM DRIVE B     read B:\MSTRACKS.TRK (a second drive)
     LOADED CAMPAIGN: N TRACKS      (once one is loaded) the track list: choose "play from track N" and the game starts there
  INSERT THE CAMPAIGN DISK FIRST, then choose its item: nothing is read before you choose, and the game keeps running while the disk
  is read (about 5 seconds for a 15-track campaign in Hatari; a real drive has the same one-revolution-per-track-side structure,
  untested).  A drive with no disk answers after about 2 seconds with "NO CAMPAIGN DISK IN DRIVE A/B"; a wrong disk (a game disk, an
  unformatted disk, a disk without MSTRACKS.TRK) gives the same message; choosing the same drive again after such a message tries
  the game's own, slower disk routine (up to about 15 seconds) in case the quick test was wrong for your drive.
  Up / Down and Return / Space (or the joystick: up, down, fire), Esc / Backspace / Left = back.  The file is checked before it is
  used (magic, version, sizes, CRC-32 of the table and of every track); a damaged or wrong file gives a message and the game stays
  as it was.  A campaign is ARMED when it has been loaded or when you play from one of its tracks, and stays armed until you choose
  ORIGINAL GAME in the F10 menu (or switch the machine off): while it is armed, ANY key at the title starts it from track 1, F10
  only opens the menu.  After the last track the game's own ending runs and you are back at the title, the campaign still armed.
  Disk 2: the campaign disk replaces nothing.  Disk 1 is never read after the title, so the campaign disk can stay in drive A; the
  game's own "Insert Disk 2" prompt appears at the first race as usual (swap disk 2 into drive A, or into drive B).  With disk 2 in
  drive B from power-on there is no prompt and the campaign disk can go into drive A.  The ending needs disk 2 (it loads the ending
  picture from it), as in the original game.
Switching patches off (this zip is a fixed build)
  With the project tree: `python3 tools/msrpatch.py list` shows the patches; `python3 tools/msrpatch.py build --floppy --out DIR`
  builds this set; `tools/play.sh --floppy` takes --no-blit --no-rb --no-nomouse --no-facestat --noextrap --safex N --no-driveb
  (see the HD notes in PATCHES.TXT for what they mean); `build --floppy --only <list> [--set SAFE=3]` for a custom set.

Not tested
  Real hardware (ST, STE, Mega STE), TT, Falcon, MiSTer.  Hatari only: STE TOS 1.62 (1 MB, 2 MB, 4 MB), Mega STE TOS 2.06 (1 MB, 2 MB, 4 MB), ST TOS 1.04 and Mega ST TOS 1.04 (1 MB, 2 MB, 4 MB).
  The campaign disk read (drive-present test, FDC timing, index pulses) is untested on a real drive, a Gotek or MiSTer.

Credits
  Moonshine Racers: Millennium / Peak Star, 1991.  HAGA conversion technique: PP (the floppy images are converted from the original
  disks).  Enhancements (patches, tools): dad_prg.
