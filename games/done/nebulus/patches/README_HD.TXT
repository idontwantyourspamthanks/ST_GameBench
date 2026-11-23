Nebulus for Atari ST - enhanced hard-disk release v@VERSION@ (dad_prg)
build: {GIT}
==============================================================================

What it is
  PP's Gamex hard-disk conversion of Nebulus (Hewson, 1987-8; ST version by
  John M. Phillips), with a few changes applied to the game's code in RAM at
  start-up. The game files are PP's, unchanged; only START.TOS (PP's loader)
  is replaced by a copy that also reads NEPATCH.BIN. PATCHES.TXT lists every
  changed byte.

What is new in v@VERSION@ (compared with v1.1.1)
  Level editor: each custom level now chooses its colours from a list (the
  game's 8 tower looks: palette, sky colours, skyline and tower texture;
  the whole editor screen takes the highlighted look while you move the
  cursor) and its enemies from a list (the 4 enemy eye designs). The
  Level > menu no longer has "Look: next tower" / "other mission": the
  colour choice sets the level's tower byte by itself. New cells: Crumble
  ledge (looks like a normal ledge; it disappears under the frog, which falls)
  and Conveyor left / Conveyor right (they look like a normal ledge in
  play; a frog standing on one without moving is carried to its end).
  A door cell now places its opposite door too (3 cells, column + 8), and
  the exit door is 3 cells with no partner. The list pickers are Colours,
  Enemies and Copy tower (the game's 16 towers, both missions).
  The panel shows the choice as "S<colours> E<enemies>". The original
  towers are unchanged. Also included is the v1.1.1 crash fix (Address
  Error with campaign files whose level records have an odd size). Level
  files stay compatible both ways: old files keep their look; a v1.1.1
  game plays a new file with the colours (tower byte) you picked.

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
The Options page lists it on its first line under "Options:": "F10/D  Level
editor".  F9 is not the editor
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
                   Delete; "<new campaign>" creates NEW CAMP and opens its
                   entry list
   Levels >        list of your levels; pick one: Play / Edit / Copy / Delete;
                   "<new level>" opens the editor on an empty tower
   Load from campaign disk    read a campaign disk in drive A: (see below)
   Save to campaign disk      write everything (levels and campaigns) to the
                              campaign disk in drive A:

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
   FIRE       open the menu (the letter after a name is its keyboard key):
     Empty C / Ledge L / Crumble ledge (looks like a ledge; it disappears
       under the frog and the frog falls) / Conveyor left N / Conveyor right M
       (look like a ledge; carry a standing frog to the left / right end of
       the row of conveyor cells) / Pillar P / Blue block (shoot) B (shoot it
       once per cell to remove it) / Lift > / Door opening D (3 cells; the door on
       the opposite side of the tower, 8 columns away, is placed too: the frog
       comes out there) / Exit door X (3 cells, the goal; no partner)
     Enemy >   Stone ball S (rolls along a ledge), Red ball R (bounces), Red
               ball W (waits for you), Eye up/down slow U, Eye up/down fast I,
               Eye left/right J (slow), Eye l/r fast K; then choose the start
               direction.
               Enemies only turn round at walls, ledge ends and other enemies.
     Lift >    Lift: from here A, Lift: stop here Z, Lift: delete (see LIFTS)
     Level >   Colours > (a list: the 1..8 looks of the game's towers; the
               screen shows the highlighted look at once, FIRE picks it,
               "< back" keeps the old one), Enemies > (list of the 4 eye-disc
               designs), Copy tower > (list of the 16 shipped towers: starts
               from that tower's grid and look), Blank grid, Time +50 / -50
               seconds, Name... (up/down = letter, left/right = move, FIRE
               = done)
     Playtest  run the real game on what you are editing; F10, finishing the
               level or losing brings you back to the editor, level intact
     Save to campaign disk, Leave editor (keeps the level in the level list)
   F10        leave the editor (the level is kept)
KEYBOARD SHORTCUTS (in the map, no menu needed; the key sets the tile at the
box; keys are named by their US legend, ST key position):
   C or Del clear   L ledge   P pillar   B blue block   D door (3 + opposite)
   X exit door (3)  A lift (see LIFTS)    Z lift stop
   S stone ball   R red ball   W red ball that waits   U / I eye up-down
   slow / fast   J / K eye left-right slow / fast
   N / M conveyor left / right
   The same enemy key again on the same enemy turns it round (start direction).
   RETURN or SPACE = repeat the last tile at the box (paint: move, RETURN).
   The trainer keys T and E never do anything while you edit (they work in a
   playtest); no editor key reaches the game when a playtest starts.
LIFTS: a lift is three cells in one column (platform, ledge under it, end
marker).  A (or Lift > Lift: from here) puts the lift platform at the box and
locks the box to its column ("Lift: U/D = other end"): move up or down and
press FIRE (or RETURN) where the lift should end; the lower of the two rows
becomes the platform, a ledge goes under it, and the other row the end marker.
F10 cancels.  Z / "Lift: stop here" adds a stop in between (the frog goes on
only while Up is held).  "Lift: delete" removes the lift the box is on.  In
the game the frog walks onto the platform and presses Up; the lift goes back
down by itself after a while.  Keep the shaft free of pillars (the editor warns
"Pillar blocks lift"); blue blocks in it must be shot first; doors and ledge
pieces in the shaft are destroyed by the first ride.  A lone platform with no
end is not a block: it is a lift start and hurts the frog.
Screen: 16 columns x rows of 16x8 pixel tiles (top = higher).  A frog marks
where Pogo starts (column 0, row 2): THE FROG STARTS IN THE SAME PLACE IN
EVERY TOWER, so every level needs a ledge on row 1 near column 0-1; the new
level and "Blank grid" have it, keep it.  Right panel = colours and enemies
(S5 E2 = colour look 5, enemy design 2: the numbers of the lists),
rows, column, row, cell value; bottom line = cell name and hints/warnings ("No
ledge below!" for a ground enemy, "Eye needs terrain" for a vertical eye with
nothing above and below, "Pillar blocks lift").  The whole screen (map,
text, background) is drawn in the colours of the level's look.  A crumble
ledge is drawn dotted below its top line, a conveyor ledge with an arrow
above it (pointing the way it carries the frog); the game draws all three
exactly like a ledge.  Arrows = lift end / stop, round enemies with an arrow
showing the start direction.

LIMITS: levels have 16..120 rows (the blank tower has 48; the shipped ones
47..96); at most 127 levels and 8 campaigns of 16 entries; all of it must fit
in 8192 bytes (about 20 normal levels; the editor says "Overlay full!" if
not).  Names have up to 11 letters/digits.  Do not use F9 (Gamex save
state) while editing: F9 itself works, but PP's "PLAY GAME IN RAM" restore was
not tried, and a restore would switch your stored levels off until the next
start (the original game is not affected).

CAMPAIGN DISKS: your levels and campaigns live on a separate 720 KB floppy
(a disk image in an emulator), never on the game disk and never on the hard
disk.  THIS ZIP CONTAINS ONE: Nebulus_campaign_disk.st, a blank 720 KB disk.
Put it in a floppy image slot of your emulator (Hatari: floppy A, or
--disk-a Nebulus_campaign_disk.st; MiSTer / other emulators: mount it as
disk A) or write it to a real 720 KB disk, and work with that; copy the file
before you use it if you want to keep a blank one.  NEVER save to the game
disk: the editor only ever reads and writes the one file NEBLEVEL.OVL on the
disk that is in drive A: when you press FIRE at its prompt.
The disk carries that one file, NEBLEVEL.OVL (exactly 8192 bytes, big endian,
starts with NCMP + version 1; the shipped one is all zero = nothing in it
yet); tools/nebcampaign.py (in the source tree) makes more disks, shows what
is on one ("info") and extracts the file.
How to use it: manager > "Load from campaign disk" or "Save to campaign
disk" (also in the editor's menu).  The editor asks "Insert campaign disk in
drive A:, then press fire (F10 cancels)": put the disk in drive A:, press
FIRE.  The screen is frozen while the drive is read: 4 to 8 seconds, or
about 10 seconds if drive A is empty (TOS retries the drive).
Messages: "Loaded N levels / M campaigns", "Saved", "No disk" (drive empty),
"Not a campaign disk" (no NEBLEVEL.OVL on it, a file of another size, or
damaged content: your levels in memory are kept), "Disk is write protected".
A save overwrites the file in place (it never creates a file, never grows
it).  Loading REPLACES the levels and campaigns in memory, so Save first.
Your levels also disappear when you reset the machine: they exist on the
campaign disk only.  Share levels by giving someone the disk (or the file);
back it up now and then.  A NEBLEVEL.OVL left next to START.TOS is still read
at start (an optional starting set), but nothing ever writes to it.
@@END

How to run
  Copy the NEBULUS folder to a hard disk (or any GEMDOS drive) and start
  START.TOS from the desktop, as PP's version. All files must stay together,
  and a campaign disk in drive A: (Nebulus_campaign_disk.st, in this zip) is
  needed to load or save your levels (see above).
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
  F9 is PP's Gamex key, not an editor key.  It leaves the game to the desktop
  (press it again if it does not answer); tried from a tower and from the
  editor manager.  F9 copies the game's RAM aside, and in doing so it
  overwrites the memory where the game keeps your levels and campaigns.  So
  after F9 your levels and campaigns in memory are switched off for as long as
  that game stays in memory: the Levels list is empty, the original game plays
  normally, F10 on the title does not crash (tried with the memory of a saved
  store overwritten the way F9 does it).  Nothing is lost on the campaign
  disk.  Save to the campaign disk BEFORE you press F9 (an unsaved level is
  gone), and avoid F9 while editing: after F9 restart the game fresh (from the
  desktop, or reset the machine) and Load from the campaign disk again.
  NOT tried: starting START.TOS again from the desktop after F9 (it may behave
  as a second start of the loader), and PP's GXUT270.PRG ("PLAY GAME IN RAM",
  saved game states).  Whatever GXUT270 restores, the levels are not part of
  it, so expect custom levels to stay off until the game is started afresh.

Tested
  Hatari 2.6.1 only: STE with TOS 1.62 and 1 MB, Mega STE with TOS 2.06 and 4
  MB, ST with TOS 1.04 and 1 MB (all cold-booted from the unzipped release
  into a tower).
  The level editor, lifts, shortcut keys and campaign disk Load/Save were
  tried in Hatari on the STE and Mega STE (the ST: F10/D and playtest).
  NOT tested: real hardware, TT, Falcon, a 512 KB machine, a real floppy
  drive, a second drive (the editor uses A: only), the desktop after F9,
  GXUT270's "PLAY GAME IN RAM".

Floppy
  This is the hard-disk set only.  A separate floppy release of the game
  (Nebulus_floppy_v@VERSION@.zip) exists; its campaign disk works the same way.

Version
  The title screen shows "v@VERSION@ enhanced by dad_prg", so the release
  cannot be mistaken for the original.

Credits
  Nebulus: Hewson, 1987-8, design, programming and audio-visuals John M.
  Phillips. Gamex conversion (START.TOS, GXUT270.PRG, NEBEXE.FIC,
  NEBULTIT.FIC, NEBULUS.PCH): PP, TT update June 2011. Enhancements (patches,
  tools): dad_prg.
