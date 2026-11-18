Nebulus for Atari ST - enhanced hard-disk release v@VERSION@ (dad_prg)
build: {GIT}
==============================================================================

What it is
  PP's Gamex hard-disk conversion of Nebulus (Hewson, 1987-8; ST version by
  John M. Phillips), with a few changes applied to the game's code in RAM at
  start-up. The game files are PP's, unchanged; only START.TOS (PP's loader)
  is replaced by a copy that also reads NEPATCH.BIN. PATCHES.TXT lists every
  changed byte.

Changes in this release
{WHATSNEW}

@@EDITOR
LEVEL EDITOR AND CAMPAIGNS
==========================
HOW TO OPEN IT: wait for the game's own title.  After START.TOS the screens
come in this order and F9/F10 do nothing before the last one: the
hardware-detect text screen (about 25 s, or any key), the box-art picture
(about 15 s; SPACE skips it), then the title, about 40 s after START.TOS was
started: the NEBULUS logo with a text page that changes by itself every 5 s
(credits with the frog on a plinth, High Scorers, Options).  On ANY of those three pages tap
F10 (a normal key press is enough; it does not have to be held), or press D
(for about a tenth of a second).
The Options page lists it on its second line: "F10/D  Level editor".  F9 is not the editor
key: it is PP's Gamex exit-to-desktop key.  Avoid it; after F9 restart the game
fresh (from the desktop, or reset the machine): the editor and your custom
levels are switched off until then.
If nothing happens in an emulator, the key probably never reached the
emulated ST: D is a plain letter key and always passes (F10 is an ordinary ST
key in Hatari too: Hatari's own shortcuts are F11, F12, Pause and AltGr+key;
a desktop, a remote session or a laptop's Fn row may take F9/F10 first).  On a
real ST, or MiSTer, F10 is the ST's F10 key.

You get the manager (joystick: up/down moves, FIRE selects, LEFT = "< back",
F10 = leave):

   Original game   leave the manager and play normally (nothing is changed)
   Campaigns >     list of campaigns; pick one: Play / Edit entries / Rename /
                   Delete; "<new campaign>" makes a new one
   Levels >        list of your levels; pick one: Play / Edit / Copy / Delete;
                   "<new level>" opens the editor on an empty tower
   Save to disk    writes everything (levels and campaigns) into the file
                   NEBLEVEL.OVL next to START.TOS

CAMPAIGNS: a campaign is a named list of up to 16 entries, played in order.
An entry is an ORIGINAL tower (mission + tower) or one of YOUR levels, so you
can mix them ("my remix: original tower 1, my level 3, original tower 8").
"Edit entries": pick an entry for Change source (cycles through your levels
and the 16 original towers) / Insert after / Remove / Move up / Move down;
"<add entry>" appends one.  When the last entry is finished the normal
victory screen follows.  Lives and score carry over like in a normal game.

THE EDITOR (a new level starts as an empty tower with a safe ledge ring on
row 1 and a ledge + exit door at the top):
   joystick   move the box (the tower is a ring: left of the left column is
              the right column)
   FIRE       open the menu:
     Empty / Ledge / Pillar / Blue block (shoot it once per cell to remove
       it) / Pale block (solid) / Door opening (3 cells) / Exit door (3 cells)
     Enemy >   Stone ball (rolls along a ledge), Red ball (bounces), Red ball
               (waits for you), Eye up/down (slow/fast), Eye left/right
               (slow/fast); then choose the start direction.  Enemies only
               turn round at walls, ledge ends and other enemies.
     Tower >   Look: next tower / other mission (palette, backdrop, default
               time), Copy original grid (start from a shipped tower), Blank
               grid, Time +50 / -50 seconds, Name... (up/down = letter,
               left/right = move, FIRE = done)
     Playtest  run the real game on what you are editing; F10, finishing the
               level or losing brings you back to the editor, level intact
     Save to disk, Leave editor (keeps the level in the level list)
   F10        leave the editor (the level is kept)
Screen: 16 columns x rows of 16x8 pixel tiles (top = higher).  A frog marks
where Pogo starts (column 0, row 2): THE FROG STARTS IN THE SAME PLACE IN
EVERY TOWER, so every level needs a ledge on row 1 near column 0-1; the new
level and "Blank grid" have it, keep it.  Right panel = tower/mission, rows,
column, row, cell value; bottom line = cell name and hints/warnings ("No
ledge below!" for a ground enemy, "Eye needs terrain" for a vertical eye with
nothing above and below).  Tile colours: green ledge, grey pillar, blue
shootable block, cream solid block, red outline door, red filled exit, round
enemies with an arrow showing the start direction.

LIMITS: levels have 16..120 rows (the blank tower has 48; the shipped ones
47..96); at most 127 levels and 8 campaigns of 16 entries; all of it must fit
in 8192 bytes (about 20 normal levels; the editor says "Overlay full!" if
not).  Names have up to 11 letters/digits.  In a playtest the trainer keys T
(timer freeze) and E (enemies off) work as usual.  Do not use F9 (Gamex save
state) while editing: F9 itself works, but PP's "PLAY GAME IN RAM" restore was
not tried, and a restore would switch your stored levels off until the next
start (the original game is not affected).

THE FILE, AND SAVING: NEBLEVEL.OVL (8192 bytes, big endian, starts with NCMP
+ version 1) must be in the same folder as START.TOS and must be WRITABLE.
The game reads it once at start; "Save to disk" overwrites it IN PLACE (it
never creates a file or changes the disk structure) and takes about a second.
If the file is missing, or the drive is write-protected, the editor shows
SAVE FAILED and nothing is lost but the save (leave the editor open and fix
that).  The release ships an all-zero file = no custom levels.  To share your
levels give someone that file; to start fresh copy an all-zero 8192-byte file
over it.  A damaged or foreign file is ignored (the original game runs).
Back it up now and then.
@@END

How to run
  Copy the NEBULUS folder to a hard disk (or any GEMDOS drive) and start
  START.TOS from the desktop, as PP's version. All files must stay together,
  and the folder must be writable if you use the level editor (see above).
  The loader reads its files with ordinary GEMDOS calls from the current
  drive: no special hard-disk driver is needed, and any drive TOS can read is
  fine. (In Hatari the folder works as a plain GEMDOS drive and as a HDDRIVER
  partition.) If NEPATCH.BIN is missing START.TOS runs the unpatched game.
  START.TOS from an AUTO folder was not tested.
  1 MB of RAM or more (PP's Gamex requirement). PP's README says 512 KB
  machines play regularly; this release's patch loader uses RAM above 512 KB
  and was NOT run on a 512 KB machine.
  PP's Gamex screens are as before: the hardware-detect screen (press M there
  on a Mega STE, TT or Falcon for the machine settings), then the picture
  (SPACE), then the game. Gamex: F9 leaves the game to the desktop (press
  again if it does not answer); GXUT270.PRG is PP's utility for saving and
  loading game states from the desktop. The cheat code of the original is in
  NEBCHEAT.TXT.
  Controls as the original: joystick, or the cursor keys with Right Ctrl as
  fire in Hatari (--joy1 keys).

F9 and the editor / campaigns (Gamex)
-------------------------------------
  F9 (press it again if it does not answer) leaves the game to the desktop;
  tried from a tower and from the editor manager. F9 copies the game's RAM
  aside, and in doing so it overwrites the memory where the game keeps the
  levels and campaigns it read from NEBLEVEL.OVL. So after F9 your custom
  levels and campaigns are switched off for as long as that game stays in
  memory: the Levels list is empty, the original game plays normally, F10 on
  the title does not crash (tried with the memory of a saved store overwritten
  the way F9 does it). Nothing is lost on disk: after a reboot the file is
  read again. Save to disk BEFORE you press F9, and do not press F9 while
  editing (an unsaved level is gone).
  NOT tried: starting START.TOS again from the desktop after F9 (it should
  read the file again), and PP's GXUT270.PRG ("PLAY GAME IN RAM", saved game
  states). Whatever GXUT270 restores, the levels are not part of it, so expect
  custom levels to stay off until the game is started afresh.

Tested
  Hatari 2.6.1 only: STE with TOS 1.62 and 1 MB, Mega STE with TOS 2.06 and 4
  MB, ST with TOS 1.04 and 1 MB (all cold-booted from the unzipped release
  into a tower).
  NOT tested: real hardware, TT, Falcon, a 512 KB machine, a floppy.

Floppy
  This is the hard-disk set only. PP's Gamex says it also works from floppy,
  but there is no floppy version of this release yet.

Version
  The title screen shows "v@VERSION@ enhanced by dad_prg", so the release
  cannot be mistaken for the original.

Credits
  Nebulus: Hewson, 1987-8, design, programming and audio-visuals John M.
  Phillips. Gamex conversion (START.TOS, GXUT270.PRG, NEBEXE.FIC,
  NEBULTIT.FIC, NEBULUS.PCH): PP, TT update June 2011. Enhancements (patches,
  tools): dad_prg.
