Nebulus (Tower Toppler) for Atari ST - enhanced floppy release v@VERSION@ (dad_prg)
build: {GIT}
==============================================================================

What it is
  The original floppy of the game (Hewson's Nebulus, 1987-8, ST version by John M. Phillips; this copy is the US Gold "Tower
  Toppler" release as cracked and packaged by Atari Legend in 2005: intro by The Attacking Shark, crack by Avenger), as a plain
  .ST image, with the game's code patched.  Nebulus_game_disk.st is that disk with one file changed (TOPPLER.JMP, the game) and
  one moved (TOPPLER.NEO, the title picture); boot sector, the Atari Legend intro (AUTO\TOWERTOP.PRG) and the loader are the
  original's, byte for byte.  PATCHES.TXT lists every change.  Nebulus_campaign_disk.st is a blank 720 KB data disk, see below.

What is new in v@VERSION@ (compared with v1.1.1)
  Level editor: each custom level now chooses its colours from a list (the
  game's 8 tower looks: palette, sky colours, skyline and tower texture;
  the whole editor screen takes the highlighted look while you move the
  cursor) and its enemies from a list (the 4 enemy eye designs). The
  Level > menu no longer has "Look: next tower" / "other mission": the
  colour choice sets the level's tower byte by itself. New cells: Crumble
  ledge (it looks like a normal ledge; the frog falls when it steps on it)
  and Conveyor left / Conveyor right (they look like a normal ledge in
  play; a frog standing on one without moving is carried to its end).
  The panel shows the choice as "S<colours> E<enemies>". The original
  towers are unchanged. Also included is the v1.1.1 crash fix (Address
  Error with campaign files whose level records have an odd size). Level
  files stay compatible both ways: old files keep their look; a v1.1.1
  game plays a new file with the colours (tower byte) you picked.

Changes in this release
{WHATSNEW}

@@EDITOR
LEVEL EDITOR AND CAMPAIGNS (floppy build)
=========================================
HOW TO OPEN IT: wait for the game's own title page (after the Atari Legend
intro and the loading picture, about a minute after boot; the keys do nothing
before that).  On the title page press F10 (a normal tap is enough), or D.
The Options page lists it: "F10/D  Level editor".  You get the manager
(joystick: up/down moves, FIRE selects, LEFT = "< back", F10 = leave):

   Original game   leave the manager and play normally (nothing is changed)
   Campaigns >     list of campaigns; pick one: Play / Edit entries / Rename /
                   Delete; "<new campaign>" makes a new one
   Levels >        list of your levels; pick one: Play / Edit / Copy / Delete;
                   "<new level>" opens the editor on an empty tower
   Load from campaign disk    read a campaign disk in drive A: (see below)
   Save to campaign disk      write everything (levels and campaigns) to the
                              campaign disk in drive A:

CAMPAIGNS: a campaign is a named list of up to 16 entries, played in order.
An entry is an ORIGINAL tower (mission + tower) or one of YOUR levels, so you
can mix them.  "Edit entries": pick an entry for Change source / Insert after
/ Remove / Move up / Move down; "<add entry>" appends one.  When the last
entry is finished the normal victory screen follows.

THE EDITOR (a new level starts as an empty tower with a safe ledge ring on
row 1 and a ledge + exit door at the top):
   joystick   move the box (the tower is a ring: left of the left column is
              the right column)
   FIRE       open the menu (the letter after a name is its keyboard key):
     Empty C / Ledge L / Crumble ledge (looks like a ledge, the frog falls
       when it steps on it) / Conveyor left N / Conveyor right M (look like
       a ledge, carry a standing frog left / right; the editor shows an
       arrow) / Pillar P / Blue block B (shoot it once per cell to remove
       it) / Lift > / Door opening D (3 cells; the door on the
       opposite side of the tower, 8 columns away, is placed too: the frog
       comes out there) / Exit door X (3 cells, the goal; no partner)
     Enemy >   Stone ball S, Red ball R, Red ball W (waits for you), Eye
               up/down U slow, I fast, Eye left/right J slow, K fast; then
               choose the start direction
     Lift >    Lift: from here A, Lift: stop here Z, Lift: delete
     Level >   Colours > / Enemies > (lists, the screen shows the highlighted
               look at once), Copy tower > (the 16 shipped towers), Blank
               grid, Time +50 / -50 seconds, Name...
     Playtest  run the real game on what you are editing; F10, finishing the
               level or losing brings you back to the editor
     Save to campaign disk, Leave editor (keeps the level in the level list)
   F10        leave the editor (the level is kept)
KEYBOARD SHORTCUTS (in the map, no menu needed): C or Del clear, L ledge,
P pillar, B blue block, D door, X exit, A lift, Z lift stop, N / M conveyor
left / right, S/R/W/U/I/J/K the enemies; the same enemy key again turns
that enemy round; RETURN or SPACE repeats the last tile (paint).  T and E
(trainers) do nothing while you edit; they work in a playtest.
THE FROG STARTS IN THE SAME PLACE IN EVERY TOWER (column 0, row 2), so every
level needs a ledge on row 1 near column 0-1; the new level and "Blank grid"
have it, keep it.

CAMPAIGN DISKS (this is how the floppy build keeps your levels): a separate
720 KB disk, the Nebulus_campaign_disk.st in this zip (write it to a real
720 KB disk, or mount it as disk A: in an emulator).  One drive is enough:
the game disk goes in drive A: to boot and play; when you Load or Save, the
editor asks you to put the campaign disk in drive A: and press FIRE (the
screen is frozen while the drive is read: 4 to 8 seconds), and you
may put the game disk back afterwards (the game never touches the drive once
it is running: it is all in RAM).  The disk carries one file, NEBLEVEL.OVL
(8192 bytes, all zero when new); a save overwrites it in place and never
creates or grows it, so it must already be there - use the shipped disk or a
copy of it.  Messages: "Loaded N levels / M campaigns", "Saved", "No disk",
"Not a campaign disk", "Disk is write protected".  Loading replaces what is
in memory, so Save first.  tools/nebcampaign.py (source tree) makes more
disks and shows what is on one.
On a 512 KB machine the editor is switched off (it needs RAM above 512 KB);
the game itself plays as the original there.
@@END

How to run
  Write Nebulus_game_disk.st to a floppy, or use it in an emulator / floppy emulator, and boot from it (drive A, any ST, STE or
  Mega STE; one drive is enough).  The image is single sided, 82 tracks of 10 sectors (the layout of the original image).
  The Atari Legend intro comes first and waits for a key: press SPACE.  The game loads from the disk (about 45 seconds with real
  floppy timing in the emulator, a loading picture is shown) and the title page appears; start with the joystick (fire) as in
  the original.  In Hatari: `hatari --disk-a Nebulus_game_disk.st --joy1 keys` (cursor keys + Right Ctrl = fire).
  The game runs at 60 Hz (the floppy's own build; the HD release's Options page has the same F5/F6 line).
  There is no Gamex here: F9 does nothing, and there is no hard-disk part to this release.

Tested
  Hatari 2.6.1 only, cold boot from the single image with real floppy timing (--fastfdc no), no hard disk: @TESTED@
  NOT tested: real hardware, TT, Falcon, MiSTer or other floppy emulators, 2-player mode, a second drive.

Version
  The title page shows "v@VERSION@ enhanced by dad_prg", so the release cannot be mistaken for the original.

Credits
  Nebulus / Tower Toppler: Hewson, 1987-8 (US Gold in the USA), design, programming and audio-visuals John M. Phillips.  The
  cracked floppy: Atari Legend release of July 2005 (intro by The Attacking Shark, crack by Avenger).  Enhancements (patches,
  tools): dad_prg.
