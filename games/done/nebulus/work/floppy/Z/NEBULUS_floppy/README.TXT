Nebulus (Tower Toppler) for Atari ST - enhanced floppy release v1.0 (dad_prg)
build: git 613b9f6 + uncommitted changes
==============================================================================

What it is
  The original floppy of the game (Hewson's Nebulus, 1987-8, ST version by
  John M. Phillips; this copy is the US Gold "Tower
  Toppler" release as cracked and packaged by Atari Legend in 2005: intro by
  The Attacking Shark, crack by Avenger), as a plain
  .ST image, with the game's code patched.  Nebulus_game_disk.st is that disk
  with one file changed (TOPPLER.JMP, the game) and
  one moved (TOPPLER.NEO, the title picture); boot sector, the Atari Legend
  intro (AUTO\TOWERTOP.PRG) and the loader are the
  original's, byte for byte.  PATCHES.TXT lists every change.
  Nebulus_campaign_disk.st is a blank 720 KB data disk, see below.

Changes in this release
  * Title screen: a small line "v1.0 enhanced by dad_prg" in the game's own
    title font between the copyright and "Mission #", so this release cannot
    be mistaken for the original.
  * Level editor: F10 on the title page opens a menu to build your own towers
    and campaigns (original and own towers mixed) and to try them in a
    playtest. On this floppy build the levels live in RAM only (no disk save
    yet, see LEVEL EDITOR below).
  * Fire jump: a jump while walking now starts in the same game loop as the
    fire press (40 ms sooner); nothing else in the move changes.
  * Short fire presses are no longer lost: a tap that is released before the
    game's next key poll still counts.
  * Stand-and-fire shot appears one game loop sooner.
  * Trainers (keys in a tower): T freezes / releases the level timer, E
    removes / restores the enemies. Both start OFF: the game is unchanged
    until you press a key.

LEVEL EDITOR AND CAMPAIGNS (floppy build: levels are kept in RAM only)
=====================================================================
Start: on the title page press F10 (or D).  You get the manager (joystick:
up/down moves, FIRE selects, LEFT = "< back", F10 =
leave):

   Original game   leave the manager and play normally (nothing is changed)
   Campaigns >     list of campaigns; pick one: Play / Edit entries / Rename /
   Delete; "<new campaign>" makes a new one
   Levels >        list of your levels; pick one: Play / Edit / Copy / Delete;
   "<new level>" opens the editor on an empty tower
   Save to disk    on this floppy build: keeps everything in RAM and says
   "Kept in RAM (no disk)"

CAMPAIGNS: a campaign is a named list of up to 16 entries, played in order.
An entry is an ORIGINAL tower (mission + tower) or one
of YOUR levels, so you can mix them.  "Edit entries": pick an entry for Change
source / Insert after / Remove / Move up / Move
down; "<add entry>" appends one.  When the last entry is finished the normal
victory screen follows.

THE EDITOR (a new level starts as an empty tower with a safe ledge ring on row
1 and a ledge + exit door at the top):
   joystick   move the box (the tower is a ring: left of the left column is
   the right column)
   FIRE       open the menu:
     Empty / Ledge / Pillar / Blue block (shoot it once per cell to remove it)
     / Pale block (solid) / Door opening (3 cells) /
       Exit door (3 cells)
     Enemy >   Stone ball, Red ball, Red ball (waits for you), Eye up/down
     (slow/fast), Eye left/right (slow/fast)
     Tower >   Look (palette, backdrop, default time), Copy original grid,
     Blank grid, Time +50 / -50 seconds, Name...
     Playtest  run the real game on what you are editing; F10, finishing the
     level or losing brings you back to the editor
     Save to disk, Leave editor (keeps the level in the level list)
   F10        leave the editor (the level is kept)
THE FROG STARTS IN THE SAME PLACE IN EVERY TOWER (column 0, row 2), so every
level needs a ledge on row 1 near column 0-1; the new
level and "Blank grid" have it, keep it.

WHAT THE FLOPPY BUILD CANNOT DO (yet): keep your levels.  The hard-disk
release writes them into NEBLEVEL.OVL with a call into TOS
that the game's own start-up has switched off; on this disk the game does not
talk to the drive after it has started.  Levels and
campaigns live in RAM until you reset or switch off.  Nebulus_campaign_disk.st
(one all-zero NEBLEVEL.OVL, the file format of the
hard-disk release) is shipped for the day a build can load and save on it;
this one does not read or write it, and the game disk
is never written.  On a 512 KB machine the editor is switched off (it needs
RAM above 512 KB).

How to run
  Write Nebulus_game_disk.st to a floppy, or use it in an emulator / floppy
  emulator, and boot from it (drive A, any ST, STE or
  Mega STE; one drive is enough).  The image is single sided, 82 tracks of 10
  sectors (the layout of the original image).
  The Atari Legend intro comes first and waits for a key: press SPACE.  The
  game loads from the disk (about 45 seconds with real
  floppy timing in the emulator, a loading picture is shown) and the title
  page appears; start with the joystick (fire) as in
  the original.  In Hatari: `hatari --disk-a Nebulus_game_disk.st --joy1 keys`
  (cursor keys + Right Ctrl = fire).
  The game runs at 60 Hz (the floppy's own build; the HD release's Options
  page has the same F5/F6 line).
  There is no Gamex here: F9 does nothing, and there is no hard-disk part to
  this release.

Tested
  Hatari 2.6.1 only, cold boot from the single image with real floppy timing
  (--fastfdc no), no hard disk: TBD
  NOT tested: real hardware, TT, Falcon, MiSTer or other floppy emulators,
  2-player mode, a second drive.

Version
  The title page shows "v1.0 enhanced by dad_prg", so the release cannot be
  mistaken for the original.

Credits
  Nebulus / Tower Toppler: Hewson, 1987-8 (US Gold in the USA), design,
  programming and audio-visuals John M. Phillips.  The
  cracked floppy: Atari Legend release of July 2005 (intro by The Attacking
  Shark, crack by Avenger).  Enhancements (patches,
  tools): dad_prg.
