# Nebulus in-game level / campaign editor (NebEditor)

Tags: **[obs]** observed (Hatari 2.6.1, scripts in `work/editor/`), **[disasm]** read from `work/train/dis_33000_40000.txt`, **[INFERENCE]** not proven.
Sources: `patches/ed_editor.s` (68000, 9334 B in six blocks since round 3: sections 4 and 13), generated `patches/ed_overlay.nep` (`work/editor/gen_ed.py`), file tool `work/editor/ovl.py`, campaign disk tool `tools/nebcampaign.py` (section 12), tests `work/editor/e*.py`, shots `work/editor/*.png`.
**Round 3 (this edit) changed the following older statements: the cell `$85` is the LIFT START slab, never a "pale block" (sections 3.4, 6, 7, 9; lifts: `work/notes/lifts.md`, section 13.1); the editor has keyboard shortcuts (13.2); "Save to disk" no longer writes the game disk: load/save go to a separate campaign disk in drive A: (sections 12, 13.3).  Where an older section still says "Save to disk" / "pale block" / `NEBLEVEL.OVL` on the game disk, this paragraph wins.**

## 1. What exists (stages, evidence)
| stage | status | evidence |
|---|---|---|
| 1a persistence | **works** STE 1 MB/TOS 1.62 and Mega STE 4 MB/TOS 2.06 | section 2; `e9.py`, `e51.py` |
| 1b file + loader + decode hook | **works**, cold boot both machines | `e20.py` (4 cells differ, zero/absent file = stock), `e33.py` |
| (b) campaign table + progression | **works**: 3 entries orig T1 -> custom -> orig T3 -> victory | `e33.py` log (section 5) |
| (c) list UI on the title (F10) | **works** (real keys) | `e30_*.png`, `e40_*.png` |
| (d) level editor + slot save | **works**: new level, place cells/enemies, Playtest, Leave, Save -> file on the HD image | `e40.py` (`ovl.py dump` of the saved file) |
| playtest | **works**: runs the real game on the working grid, F10 or level complete -> back to the editor, grid intact | `e40.py`, `e41.py` |
| (e) campaign editor | UI built (new campaign, add entry, cycle source, insert, remove, up/down, rename, delete); screens proven (`e50` shots), per-op behaviour **not individually exercised** | `e50_megaste_*.png` |
| Mega STE 4 MB | save proven (`e51.py megaste`: file bytes changed, "Saved to disk", VBL keeps running, keys work after save); campaign progression NOT re-run on 4 MB | |
| round 3: Lift > (replaces "Pale block") | **works** STE 1 MB | section 13.1, `e140.py`, `e150.py` |
| round 3: keyboard shortcuts, T/E vs editor | **works** STE (Mega STE: section 13.6) | section 13.2, `e150.py` |
| round 3: campaign disk Load/Save (drive A:), `tools/nebcampaign.py` | **works** STE 1 MB (22 fuzz disks) and Mega STE 4 MB | sections 12, 13.3, `e161.py` |
Not done / unproven: real hardware, floppy, 2-player, F9 inside the editor, copy/delete/rename ops exercised only by code review. `ed_dir` proven [obs `e61.py`, breakpoint at the spawn `$37a98`, slot-0 speed word]: markers `$10 $20 $40 $60` -> `+1`, `$11 $21 $41 $61` -> `-1` (`ffff`), `$30/$31` -> 0.

## 2. Persistence (how the ST saves its own file)
**Round 3: the game-disk save described here is GONE** (user decision: the editor never writes the game disk).  The same excursion (`swap_tos`, MFP save/restore, ACIA drain, private stack - now at `$AD000`) is `disk_op`, which loads/saves `A:\NEBLEVEL.OVL` on a separate campaign disk (section 12).  The TOS-state copy address/length and TOS's MFP block now come from `RS+rsTosP/rsTosN/rsMfpP` (filled from `$ffd80/$ffd86/$fffaa` in the HD build; the floppy build's stub must fill them, section 13.4).  The text below is kept as the record of how the excursion was found and proven.

Plain `trap #1` from the game crashes: HDDRIVER (`hdv_rw $476 = $ea7c`) and the BDOS data live in `$8..$1b960`, which the game's workspace (`$8700..$33a4f`, cleared at init) destroys [obs: bus error in BDOS `$e09598`].
**TOS excursion** (`save_file`): SR=$2700, park game a7 in a private stack (`STK`), save the game MFP (24 regs + the F9 max-scan for timers A/C/D), **swap** `$8..$8+(n+1)*48` with the Gamex TOS copy (address = long at `$ffd80`, count word at `$ffd86`, both inside the F9 code at `$ffd20`; `$c0108` on 1 MB, `$102008` on 4 MB [obs]), restore START's TOS MFP block (`$fffaa`), SR=$2500 (MFP level 6 on, VBL masked so TOS never touches the screen), `Fopen(NEBLEVEL.OVL, mode 1)`, `Fwrite(8192)`, `Fclose`, swap back, restore game MFP, **drain the ACIA** (a byte left in the ACIA after the excursion blocks all later keyboard IRQs [obs: `$fffc00 = $83`, keys dead; fixed]), restore SR/a7. d7 (result) must be saved across `swap_tos` (it clobbers d0-d7).
Safety: only an EXISTING fixed-size file is overwritten (no Fcreate, no allocation, FAT/dir size unchanged [obs: mdir 8192 B before and after]); the tool creates it (`nepatch build` writes a zero-filled `NEBLEVEL.OVL`). A failed Fopen/Fwrite prints "SAVE FAILED" and returns (no crash). The game never touches the file in normal play. Not proven: real HD/floppy timing, TT/Falcon (excursion address comes from `$ffd80`, so 4 MB works [obs]).

## 3. FORMAT SPEC: `NEBLEVEL.OVL` version 1 (platform neutral)
One file, exactly **8192 bytes**, named `NEBLEVEL.OVL`, in the root of the game disk (the loader opens it by that name; a campaign disk/ADF/ST/MSA just carries this one file next to the game files; absent file = no custom content). All multi-byte values are **big endian**. No field holds a RAM address, pointer or decoder state; the only Atari-specific thing is the *meaning of the cell byte values* (section 3.4), which is the game's own tile code and identical on any port of the game. Read/write/validate/render with `work/editor/ovl.py` (`validate FILE`, `dump FILE`, `render FILE LEVEL out.png`, `import-original MISSION TOWER out.ovl`).

### 3.1 Layout
| offset | size | field | meaning |
|---|---|---|---|
| 0 | 4 | magic | ASCII `NCMP` |
| 4 | 2 | version | `0001`. Any other value: the game treats the file as ABSENT (no crash) |
| 6 | 2 | nlevels | 0..127 |
| 8 | 2 | ncamps | 0..8 |
| 10 | 6 | reserved | zero |
| 16 | 8 x 32 | campaign table (fixed size, `ncamps` used) | below |
| 272 | variable | level records, back to back, `nlevels` of them | below; free space after the last one is zero |

Campaign record (32 B): `name[12]` ASCII, NUL terminated (<= 11 chars) | `count.b` (0..16) | pad.b | `entry[16]` | 2 pad. Entry byte: **bit 7 set = original tower** `0x80 | (mission-1)<<3 | tower` (mission 1..2, tower 0..7 = "tower 1..8"); **bit 7 clear = custom level index** (0..nlevels-1, position in the level list). A campaign plays its entries in order; after the last one the game's own victory screen follows.

Level record: `mission.b` (1|2: which tower set supplies graphics) | `tower.b` (0..7: base tower: palette, backdrop, default time and title) | `rows.b` (16..120; the number of rows the game decodes, = its variable `$33912`; shipped towers 47..96) | `flags.b` (0, reserved) | `len.w` (= 2*rows + number of stream bytes) | `time.w` (BCD, e.g. `0300` = 300 s; 0 = the base tower's time) | `name[12]` (ASCII NUL terminated, <= 11 chars; shown as the level title) | `mask[2*rows]` | `stream[len-2*rows]`. Record size = 20 + len; the next record starts right after.

### 3.2 Grid encoding (decode without the game)
A level is a grid `cell[angle 0..15][row 0..rows-1]` of bytes (angle = column around the tower, wraps; row 0 = bottom). Unlisted cells are 0. Pseudo-code:
```
m = 0; s = 2*rows                       # m walks the mask bytes, s the stream, both relative to the start of mask[]
for row in 0 .. rows-1:
    for half in 0, 1:                    # half 0 = angles 0..7, half 1 = angles 8..15
        mb = body[m]; m += 1
        for bit in 0..7:                 # bit n <-> angle half*8 + n
            if (mb >> bit) & 1:
                cell[half*8 + bit][row] = body[s]; s += 1
assert s == len                          # the stream is consumed exactly
```
Encoder = the inverse (for each row, for each half, set the mask bit when the cell is non-zero and append the cell to the stream in the same order). This is exactly the game's own tower encoding (decoder at `$377a2`/`$37822`), so the original towers can be imported byte for byte.
Validity (the in-game loader checks the same, and treats the whole file as absent if anything fails): size 8192; version 1; nlevels <= 127; ncamps <= 8; every campaign count <= 16; every level: mission 1|2, tower <= 7, 16 <= rows <= 120, len >= 2*rows, record inside the file, **popcount(mask bits) == len - 2*rows**.

### 3.3 Evidence: a freshly saved file (`/tmp/e80.ovl`, written by the ST through the excursion; `ovl.py validate` = OK)
```
header      4e 43 4d 50 | 00 01 | 00 01 | 00 01 | 00 00 00 00 00 00        NCMP v1, 1 level, 1 campaign
campaign 0  54 45 53 54 20 52 45 4d 49 58 00 00 | 02 | 00 | 80 82 82 00 ... "TEST REMIX", count 2, entries orig M1 T1, orig M1 T3, (rest 0)
level 0     01 03 2f 00 | 00 ea | 03 00 | 4e 59 20 4c 45 56 45 4c 00 00 00 00      mission 1, base tower 3, rows 47, flags 0, len 234, time 0300, "NY LEVEL"
mask[0..7]  00 00 | e7 07 | 5c 04 | 04 04 ...                                rows 0 (empty), row 1 = angles 0-2,5-10 (e7 07), ...
stream[0..15] 81 81 81 81 81 81 81 81 81 83 85 85 85 83 83 83
decoded     cell(0,1)=81 cell(1,1)=81 cell(3,1)=00 cell(4,1)=00 cell(3,2)=85 cell(4,2)=85 cell(4,43)=c3 cell(4,44)=c3   (= shipped tower 1 with 4 cells edited)
```
(The `len` of this record is 0x00ea = 234 = 94 mask + 140 stream bytes; record size 254.)

### 3.4 Cell byte values (game semantics; bit 7 = terrain)
`00` empty; `80` pillar/stone; `81` ledge; `82`,`86` blue block, destroyed by one shot; `83`,`87` door opening (drawn as a dark gap, 3 cells tall); `85` **lift start slab** (cream; bottom of a lift, walk onto it and press Up), `89`/`8d` lift platform cells that exist only at run time; `c3` exit door (3 stacked); `91` crumbling ledge, `a1`/`b1` conveyor ledges; `08` **lift end marker** (invisible in the game, bit 7 clear), `0c` **lift stop** (a lift needs: `85` at the lower row, `81` ledge under it, `08` above in the same column; `0c` optional stop between; see `work/notes/lifts.md`); **enemy markers** (bit 7 clear): high nibble `10` stone ball, `20` red ball, `30` red ball (waits), `40`/`50` eye up-down (slow/fast), `60`/`70` eye left-right (slow/fast); **low nibble bit 0 = start in the negative direction** (down / left), other low bits unused. Unknown values are drawn/played by the game as it decodes them (they are never interpreted by the file format). The frog always starts at angle 0 on row 2 (so a ledge on row 1 near angle 0-1 is needed).

### 3.5 Capacity, versioning, packaging
Shipped-size level 250-400 B (record), dense up to ~1.8 KB; 8192-272 = 7920 B of level space = about 20 typical levels (campaigns cost 32 B each, fixed). To change the format: bump `version` (the game rejects unknown versions); the loader in the game only needs `version == 1`. Packaging: put `NEBLEVEL.OVL` (8192 B, any valid content, or zeros) in the disk root; the editor overwrites it in place (it never grows), so a site can ship a ready campaign file or an empty one. Sharing = copying the file.

Budget/limits summary: levels 16..120 rows x 16 angles; at most 127 levels, 8 campaigns x 16 entries, total 8 KB.

## 4. Loader and memory
Lead merged the tool: stub reads `NEBLEVEL.OVL` (absent = all zero) to **`$BC000`** (outside game RAM; the hooks check magic 'NCMP' so an F9 restore, which overwrites `$80008..$ffdc8`, just disables custom levels; the original game is untouched). `block ADDR HEX` = unverified copy into the dead zone `$75728..$77ec0`.
Game RAM (F9-safe), round 3 map (`gen_ed.py` asserts every block against its limit and against the other blobs): CODE1 `$75740..$76bfc` (5308 B; limit `$76c00`), trainers `$76c00..$76c75`, CODE5 `$76c76..$76cf6` (128 B), latch `$76d00..$76d3b`, tables (DATA) `$76d40..$7726c` (1324 B), CODE2 `$77300..$779e8` (1768 B), credit `$77a00..$77a3f`, CODE3 `$77a40..$77c66` (lift block + result strings, 550 B), runtime state `RS $77c80` (64 B: rsCamp.. rsOk +40, rsKey +42, **rsKb +44, rsPv +46, rsLast +48, rsTosP +52 (long), rsTosN +56, rsMfpP +58 (long)**), editor vars `V $77cc0` (256 B, cleared at every editor entry; **vLift +172, vDisk +174, vMed +244, vTxt +208 (32 B message text)**), CODE4 `$77dc0..$77ec0` (256 B, the disk block; this is where the private stack used to be). **The excursion's private stack moved to non-game RAM: `STK = $AD000` (top; `$AC000..$AD000`).**  Free after round 3 (section 13): 4 + 10 + 148 + 24 + 26 B inside the blocks, 24 B `$75728..$7573f`, 4 B `$76d3c..$76d3f`.  Non-game RAM: editor screen `$A0000`, dynamic menu buffer `$A8000`, tiles `ETILE $A8800` (19 x 16 B), **campaign-disk read buffer `BUF $AA000..$AC000`**, stack `$AC000..$AD000`, store `OVS $BC000`, working-copy record `TREC $BE000` (volatile, playtest).  Conflicts checked against `$76c00` (trainers), `$76d00-$76d3b` (input latch), `$77a00` (title banner) and RS/V: none (asserted in `gen_ed.py`).

## 5. Hooks (jump table at `$75740`, 6 B each; sites in `ed_overlay.nep`)
`$377a2` decode (6 B `jmp`): record of `rsLvl` (custom, or `$7fff` = playtest copy) -> clear grid, `$33912` = rows, feed mask/stream to the game's loop `$37812`; else original. `$3adb4` initial time (record time if non-zero). `$3d110` tower name (record name). `$3e352` tower complete -> campaign progression: next entry (original: mission/tower + `rsLvl=0`; custom: `rsLvl=k+1`, mission/base tower from the record, player tower word updated); end of list -> `$3390c = 8` = the game's own victory/Congratulations/hi-score flow, `rsCamp = 0`; a single custom level ends the same way; in a playtest it returns to the editor instead. `$3d6c4` title poll: resets rsCamp/rsLvl/`$33a44` every poll, **F10** (`$38498 == $44`) opens the manager, a finished playtest (game over -> title) re-opens the editor. `$3dfd6` frame flip: F10 during a playtest -> editor. `$37a90` spawn direction (low nibble bit 0 of an enemy marker negates the start speed; all 160 shipped markers have low nibble 0 so originals are unchanged).
Start of play from the manager = `jmp $3d85a` (the title's own exit), restart of a playtest = `lea $800,a7; jmp $3dbb0` (new-game init: lives/score/timer reset), quit to title = `jmp $3db8c`.
**Proof (b)** [obs `work/editor/e33.py`, STE 1 MB, E trainer on, forced door entry]: level 1 `rsPos 0 tower 0`, grid vs stock M1 T1: no diffs; after force 1 `rsPos 1 rsLvl 1 tower 3`, diffs vs stock M1 T1 = `[(3,1),(3,2),(4,1),(4,2)]` (the 4 hand-edited cells), timer starts at 300 (`001800000000`); after force 2 `rsPos 2 rsLvl 0 tower 2`, grid == stock M1 T3; after force 3 `rsCamp 0, $3390c = 8, pl 9`.

## 6. UI
Title: **F10** or **D** (F10 is tap-proof through the ACIA latch, D is read from the cell; see section 11; not a game key; F1-F8 options, F9 Gamex, T/E trainers untouched). Own screen/palette/VBL (game timer B stopped, game state untouched), game font via `$3b344`. Joystick: move, fire = select/open menu, left = last menu item ("< back"), F10 = back/leave.
Manager: `Original game | Campaigns > | Levels > | Save to disk`. Levels: list, `<new level>`; per level Play/Edit/Copy/Delete. Campaigns: list, `<new campaign>`; Play/Edit entries/Rename/Delete; entries: `nn O m-t` (original) / `nn L name` (custom), `<add entry>`, per entry Change source/Insert/Remove/Up/Down. Names: up/down cycle letters (`name_edit`), left/right move, fire done.
Editor: flat 16 x rows map (8 px cells, 25 rows visible, scrolls), XOR cursor box, panel (tower, rows, col/row, cell value + name). Menu: Empty C, Ledge L, Pillar P, Blue block (shoot) B, **Lift >** (from here A / stop here Z / delete / back; replaces the old "Pale block" = `$85`, which was a lift start without an end), Door opening D (x3 vertical), Exit door X (x3), Enemy > (Stone S, Red R, Red waits W, Eye up/down slow U / fast I, Eye left/right J / K), Tower >, Playtest, Save to campaign disk, Leave editor (the letters are the keyboard shortcuts, section 13.2). Tower >: Look next tower / other mission (palette/backdrop/time base), Copy original grid (decode of the base tower = copy-existing-tower start), Blank grid (base ledge ring row 1 + ledge + exit door), Time +-50, Name..., back. Warnings: ground enemy without ledge below, vertical eye without terrain above AND below, pillar between a lift's slab and its end ("Pillar blocks lift").
Why a flat map (not the game's renderer): the renderer needs the play state (scroll, sprites, raster palette chain); the flat view is 8 px tiles from one routine and cannot desync the game; the real renderer is used by Playtest on the same grid.
Playtest: working grid -> TREC record (`rsLvl = $7fff`), game started through the title exit; hooks take time/name/palette/base tower from it; frog start is **fixed** per game (x=4, y=8 = row 2 on ledge row 1, not data [obs: all towers]) so every level needs a ledge at row 1 near column 0-1 (blank template has the full ring). T/E trainers work in playtest [obs: E used in e33/e41]; editor keys (F10 + joystick) do not collide.

## 7. Game facts established for the editor
- Enemies [obs, sheets `enemy_sheet2.png`]: `$10` stone ball (kind 2, rolls along a ledge, turns/drops at ends); `$20` red ball (kind 1, hops, falls off ledge ends); `$30` red ball that waits (kind 1 speed 0, charges when the player is on its row within 32 angles); `$40/$50` blue-eye disc VERTICAL (kind 8, speed 1/2); `$60/$70` blue-eye disc HORIZONTAL (kind 9, wraps the tower). All only rebound off terrain/other creatures (no stored range): the start direction is the only data (low nibble bit 0, hook `ed_dir`). Time-waster flyer = separate (pink cross, countdown `$339bc`).
- Shootable terrain [obs `e13.py`, forced shot]: `$82` and `$86` are destroyed by one shot per cell (cell -> 0, `$33918++`, not restored within 5 s); `$80 $81 $85 $89` are unaffected. A 2-cell block needs two shots.
- Cells [obs `cell_sheet2.png`]: `$80` grey stones, `$81` ledge, `$82` blue grate (shootable), `$83` door opening, `$85` lift start slab (`$89/$8d` = run-time lift platforms; NOT solid blocks), `$91/$a1/$b1` ledge variants (not in the menu), `$87/$c3` door (c3 = exit), `$08` lift end / `$0c` lift stop markers (invisible in the game, drawn as arrows by the editor). Renderer reads the grid every frame [obs].
- Joystick tables: `$338f2` dx (+1 right), `$338f4` dy (+1 up); fire flag `$338f0`.

## 8. Risks / limits
F9 inside the editor or after custom levels is untested (store lost, magic check keeps the game safe); the excursion masks keyboard/VBL for ~0.5-1 s; HDDRIVER/BDOS state is swapped back and forth (the TOS copy is updated in place, consistent with the disk); real hardware timing unproven; 2-player mode not considered in `ed_next`; editor palette uses STE colours (nibble bit 3 = LSB: `$8xx` is dark, use `$6xx`).

## 9. USER GUIDE (self-contained; paste into README.TXT)
```

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
     Empty C / Ledge L / Pillar P / Blue block B (shoot it once per cell to
       remove it) / Lift > / Door opening D (3 cells) / Exit door X (3 cells)
     Enemy >   Stone ball S (rolls along a ledge), Red ball R (bounces), Red
               ball W (waits for you), Eye up/down U slow, I fast, Eye
               left/right J slow, K fast; then choose the start direction.
               Enemies only turn round at walls, ledge ends and other enemies.
     Lift >    Lift: from here A, Lift: stop here Z, Lift: delete (see LIFTS)
     Tower >   Look: next tower / other mission (palette, backdrop, default
               time), Copy original grid (start from a shipped tower), Blank
               grid, Time +50 / -50 seconds, Name... (up/down = letter,
               left/right = move, FIRE = done)
     Playtest  run the real game on what you are editing; F10, finishing the
               level or losing brings you back to the editor, level intact
     Save to campaign disk, Leave editor (keeps the level in the level list)
   F10        leave the editor (the level is kept)
KEYBOARD SHORTCUTS (in the map, no menu needed; the key sets the tile at the
box; keys are named by their US legend, ST key position):
   C or Del clear   L ledge   P pillar   B blue block   D door opening (3)
   X exit door (3)  A lift (see LIFTS)    Z lift stop
   S stone ball   R red ball   W red ball that waits   U / I eye up-down
   slow / fast   J / K eye left-right slow / fast
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
level and "Blank grid" have it, keep it.  Right panel = tower/mission, rows,
column, row, cell value; bottom line = cell name and hints/warnings ("No
ledge below!" for a ground enemy, "Eye needs terrain" for a vertical eye with
nothing above and below, "Pillar blocks lift").  Tile colours: green ledge,
grey pillar, blue shootable block, cream lift platform, arrows = lift end /
stop, red outline door, red filled exit, round enemies with an arrow showing
the start direction.

LIMITS: levels have 16..120 rows (the blank tower has 48; the shipped ones
47..96); at most 127 levels and 8 campaigns of 16 entries; all of it must fit
in 8192 bytes (about 20 normal levels; the editor says "Overlay full!" if
not).  Names have up to 11 letters/digits.  Do not use F9 (Gamex save
state) while editing: F9 itself works, but PP's "PLAY GAME IN RAM" restore was
not tried, and a restore would switch your stored levels off until the next
start (the original game is not affected).

CAMPAIGN DISKS: your levels and campaigns live on a separate 720 KB floppy
(a disk image in an emulator), never on the game disk.  The disk carries one
file, NEBLEVEL.OVL (exactly 8192 bytes, big endian, starts with NCMP + version
1).  This release ships a blank one (Nebulus_campaign_disk.st: an all-zero
file = nothing in it yet); tools/nebcampaign.py (in the source tree) makes
more, shows what is on a disk ("info") and extracts the file.  "Load from
campaign disk" / "Save to campaign disk" ask "Insert campaign disk in drive
A:, then press fire (F10 cancels)": put the disk in drive A: (in Hatari:
floppy A, or --disk-a), press FIRE.  Messages: "Loaded N levels / M
campaigns", "Saved", "No disk", "Not a campaign disk" (no NEBLEVEL.OVL on it,
a file of another size, or damaged content: your levels in memory are kept),
"Disk is write protected".  A save overwrites the file in place (it never
creates a file, never grows it); the game disk is never written.  Loading
REPLACES the levels and campaigns in memory, so Save first.  Your levels also
disappear when you reset the machine: they exist on the campaign disk only.
Share levels by giving someone the disk (or the file); back it up now and
then.  A NEBLEVEL.OVL left next to START.TOS is still read at start (an
optional starting set), but nothing ever writes to it.
```
(Round 3: this guide is the `@@EDITOR` block of `patches/README_HD.TXT`; the three-state hint about F10/D, the shortcuts, lifts and campaign disks are in it.)

## 10. Round 2: gates, hardening, polish (supersedes the "not exercised" remarks in sections 1, 6, 8)
**Header/format check (against the ACTUAL saved file `/tmp/e80.ovl`, section 3.3)**: starts `4e434d50` = `NCMP`; version word `0001` at offset 4 (existed from the start; the loader now REJECTS any other version: magic cleared = treated as absent); no addresses/pointers anywhere (campaign entries = tower codes/level indices, level header = small ints + BCD time + name, body = grid bytes); everything big endian; all lengths/counts validated against the 8192-byte size by `ov_check` in the ST and `ovl.py validate` on the PC (same rules). Nothing in the file had to change.
**Loader hardening** (`ov_check`, run once before the first use of the store, cached in `RS+rsOk`): version, nlevels <= 127, ncamps <= 8, campaign counts <= 16, per level mission 1|2, tower <= 7, 16 <= rows <= 120, len >= 2*rows, record inside the store, popcount(mask) == stream length. Any failure clears the magic (= absent file; the first Save re-initialises it). Entries pointing at missing levels fall back to the stock decode; hooks also re-check the magic on every use.
**Fuzz** [obs `e90.py`/`e91.py`, 22 files restored over `$BC000` in a title snapshot with the hooks, then F10 -> Levels -> Edit (if the file has a level) -> Campaigns -> Play]: 5 random files, magic+random, 6 byte-flip files (1-12 flips in the first 700 bytes), truncated, version 2, nlev 127, ncamp 200, rows 0, rows 255, len 65535, campaign count 255, bad entries `7f 90 05`, valid. Result: **0 crashes** (no Address/Illegal errors in any Hatari log, VBL running); every file `ovl.py validate` rejects had its magic cleared by the game (file/loader rule parity), the 6 accepted ones (flips inside cells/name/time/entries, bad entries, valid) edited and played normally.
**Operations** [obs `e80.py`, menu-driven, STE; stored RAM image parsed with `ovl.py` after every step]: new campaign + 2 add-entry (`80 80`); change source x2 (`82 80`); insert after (`82 80 80`); move down (`80 82 80`); cycle to `86`; remove; rename (`NEW CAMP` -> `ODW CAMP`); delete campaign; copy level (identical grid); edit copy + rename via Tower > Name + Leave editor (commit); delete level 0 -> campaign TEST REMIX lost its custom entry (`80 00 82` -> `80 82`) and the copy became level 0; Save; the saved file validates and dumps correctly. (Move up exercised only on equal entries; the code is the mirror of move down.)
**Full campaign with real input, Mega STE 4 MB / TOS 2.06** [obs `e100.py campaign megaste`]: F10 -> Campaigns -> TEST REMIX -> Play (real keys), forced door entries: entry 1 orig T1, `rsPos 1 rsLvl 1 tower 3` with the 4 custom cells, `rsPos 2 rsLvl 0 tower 2`, then `rsCamp 0, $3390c = 8` (victory). **Playtest on Mega STE** [obs `e100.py playtest megaste`]: Levels -> Edit -> Playtest -> E -> forced completion -> back in the editor (`rsTest 0 rsEd 1`), grid cells intact. Save on Mega STE: file bytes changed, "Saved to disk", game alive, keys work [obs `e51.py`].
**"SAVE FAILED" seen earlier = a bug of mine**: `swap_tos` clobbers d7 which held the write result, so a successful write printed SAVE FAILED (the file was correct). Fixed (result saved on the stack). Real failure path [obs `e120.py A`, game disk WITHOUT NEBLEVEL.OVL]: Fopen returns -33 (file not found), message "SAVE FAILED", no crash, keys and VBL fine afterwards (shot `e120_savefail.png`); the build tool always ships the file so this only happens if the user deletes it (or a read-only medium: same path).
**F9**: F9 inside the editor works through Gamex (GEM desktop reached, `e120_f9.png`); the Gamex restore (GXUT270 "PLAY GAME IN RAM") was NOT run (desktop interaction). Simulated F9 effect (what the restore does to `$BC000..`): store overwritten with garbage while a campaign runs [obs `e120.py B`]: completion falls back to the victory flow, rsCamp cleared, 0 error lines, game alive.
**Default-on equivalence** [obs `e97.py` = NebInput2's scripted2/cmp_sc with the 10 live commands (3 blocks + 7 sites) applied atomically at the first loop-top poll, same input script keyed on the timer words; baseline `e96.py`: stock vs stock = 0 differences]: all 7 hooks installed, NEBLEVEL.OVL absent: 1121 loops compared, non-player block differences 0, player-variable differences 0, creature/timer/energy simulation differences 0 of 1119, framebuffer (event 1) 0 differing bytes. Cost per loop (analytic, 8 MHz 68000): only `ed_game` runs every loop = `cmpi.b #$44,$38498.l` 20 + `bne` 10 + `jmp $3868a.l` 12 = **+42 cycles/loop (0.03 % of a 131,448-cycle VBL budget)**; `ed_title` per title poll ~60 cycles, `ed_dir` per spawn ~30, `ed_dec/ed_time/ed_name/ed_next` once per level (3-40 cycles when no custom level is active). The pacer hides it; frame counts were identical (1121 loops both). => `ed_overlay` can be `default: yes` (the patch only adds code to unused RAM and these hooks).
**UI polish done**: map 16 columns x 16x8 px tiles (256 px wide, 22 rows, scrolls with the cursor), recognisable tiles (ledge green line, pillar, blue shootable block with frame, cream lift slab, door outline, exit with cross, round enemies with an arrow for the start direction, frog marker at column 0 row 2), right panel (tower/mission, rows, column, row, value), bottom line (cell name + hints/messages), menus/lists use the whole screen (`guide_*.png`: `guide_7_editor_custom_level`, `guide_10_editor_copy_of_tower1` shows a copied shipped tower). Not done: ring preview. New-level start = empty tower with a ledge ring on row 1 (safe frog start) + ledge/exit at the top; **Tower > Copy original grid decodes the base tower (mission/tower of "Look") with the game's own decoder into the working grid** [obs `guide_10`: rows 66, shipped tower layout]; Look first, then Copy, to choose which tower.
**PC tool** `work/editor/ovl.py`: `validate FILE` (never raises; same rules), `dump FILE`, `render FILE LEVEL out.png` (same tile glyphs read from `ed_editor.s`), `import-original MISSION TOWER out.ovl` [obs: import 1/5 -> 437 B level, validates OK].
**Screenshots**: `work/editor/guide_1_manager.png` ... `guide_16_saved.png` (+ `guide_13_name_entry.png`, `guide_sheet.png`).
Memory now: code `$75740..$76b09` (5066 B of 5094), tables `$76d40..$772ad`, code `$77300..$778e5`, free before `$77a00`: ~280 B; RS `$77c80` (+`rsOk` at +40), V `$77cc0` (tile scratch at V+192), `ETILE` expanded tiles at `$A8800`.

## 11. F9/F10 "do nothing" under Hatari (user report 2026-11-18, NebF10Debug): findings, fix, how to open the editor
Tags: [obs] = raw output this session (scripts `work/keys/{kh,t1..t7,g1,chain}.py`, logs summarised below); [INFERENCE] = not proven.
**Setup reproduced exactly** (`work/keys/kh.py`): `hatari --machine ste --tos TOS_1_62 --memsize 1024 --cpuclock 8 --monitor rgb --gemdos-drive skip --acsi 0=<copy of dist/AtariST_enhanced_games_2026-11-18.img> --confirm-quit no` + `--cmd-fifo/--screenshot-dir` only, NO `--joy1 keys`, fresh HOME (default config) and a copy of the user's `~/.config/hatari/1040stfm.cfg`; real XTEST key events (not `--window`); program started with `--auto C:\NEBULUS\START.TOS` (mouse double-click automation is unreliable here, see release.md 3b).
**The image is right** [obs]: `NEBULUS\NEPATCH.BIN` 32564 B md5 `4fc66211...` (= the zip's), 1 x `NEPO` marker block, `NEBLEVEL.OVL` 8192 B, START.TOS md5 `4ecf26d8...`; cold boot: `$b0020 = NEPO`, 18 sites, title (`$3d00f` = "High") 50-55 s after Hatari starts (TOS boot ~12 s, AUTO prompt 3 s, HW-detect text screen ~25 s, box-art picture ~15 s), then the attract cycle `page word $3d5b6` 0 (credits, frog) -> 1 (High Scorers) -> 2 (Options) -> ..., 75 title loops (~5 s) per page.
**What does work under Hatari, default config, no `--joy1 keys`** [obs, shipped image]: F10 held 100 ms opens the manager (`$70` = editor VBL `$75a14`, normal `$382d8`) on every page: 3/3 each on pages 0, 1, 2 (`/tmp` log `t3a`), and 10/10 on page 0 at 100 ms; 60 ms: 10/10, 9/10, 10/10 (pages 0/1/2); 30 ms: 7/10, 7/10, 9/10. F9 100 ms on the title: `$70` goes to the TOS vector `$e00802` and the machine restarts (HDDRIVER banner, "Powermonger? P = start", the HW-detect screen again; with `--auto` START runs again): so F9 reaches the Gamex handler and works (it is PP's exit; it acts on the BREAK byte `$c3`, see `$200`: `cmp.b #$c3,d0`). 25 taps of F9/F10 (100 ms, every 1.7 s) during the whole load, then F10 on the title: opens, with the user's own `hatari.cfg` (`USERCFG=1 t4.py A`): early keys do not break anything, they are just ignored. IKBD bytes for a tap [obs, trace `t2.py`]: `$44` (make) ... `$c4` (break) 4-5 VBL later for 100 ms; Hatari without `--joy1 keys` sends no joystick packets at all.
**Hatari/host side** [obs docs + source `hattari/src/sdl/keymap.c`, `shortcut.c`, `doc/manual.html`]: F9 -> ST `$43`, F10 -> `$44` (symbolic and scancode maps); Hatari's own shortcuts are F11 (fullscreen), F12 (options), Pause, and AltGr+key (`--confirm-quit` irrelevant); F9/F10 are NOT Hatari shortcuts. The user's config (`1040stfm.cfg`): `nKeymapType = 0` (symbolic), shortcut tables with F11/F12/Pause and AltGr+F1..F4 only, `Joystick1 nJoystickMode = 1` (real joystick; a gamepad that jitters would overwrite the game's single last-byte cell with joystick bytes, F9 would still work) [INFERENCE for a gamepad], desktop KDE/Wayland (`XDG_SESSION_TYPE=wayland`; a KDE or compositor shortcut or an Fn-row laptop keyboard taking F9/F10 is possible, cannot be tested from here). `Keymap_KeyDown` returns early only for Hatari shortcuts and, with `--joy1 keys`, for the joystick keys (cursor keys, Right Ctrl); `IKBD_PressSTKey` drops keys only while the IKBD is in joystick-monitoring mode (the game never sends IKBD commands: no `$fffc02` write in the game).
**Cause, honestly**: NOT reproduced. Three real defects/gaps found: (1) **no hint anywhere** that F10 exists, and nothing says the keys only work on the game's own title (about 40 s after START.TOS; before it the hardware-detect and picture screens ignore F9/F10; F9 at the HW screen is a no-op) [obs: HW-detect text says "GAMEX: key F9", which invites F9]; (2) the title polls the game's single last-byte cell `$38498` once per title loop (every 3 VBL = 60 ms: POLL events 3 VBL apart in `t2.py`'s trace) and the old hook tested `cmpi.b #$44,$38498`, so a tap whose break byte `$c4` arrives before the poll is lost (30 ms taps: 30% lost; 60 ms: 1/30; >=100 ms: 0/13); (3) the key could not be changed if the host takes F10.
**Fix (in `ed_overlay`, no new patch file; `gen_ed.py` regenerates it)**: new site `$3851a` (6 B `jmp ed_key`; the instruction pair `move.w (a7)+,d0 / bclr.b #6,$fa11.w` that ends the game's ACIA handler is reproduced inside the hook; reached from the Gamex hook, from ni_latch's stub and from the direct drop path): when the byte now in the cell is `$44` it sets the word latch `RS+rsKey` ($77caa). (ni_latch's stub1 has already masked d0 with `$f0`, so d0 is NOT the byte at `$3851a`: read the cell.) `ed_title`/`ed_run`/`ed_game` consume the latch instead of testing the cell, clear it on entry/exit of the editor and every game frame (a key pressed in a tower never reaches the title). `D` (`$20`) is a second title trigger read from the cell like every game key (a latched letter would survive the high-score initials). New site `$3d662` (8 B) puts "F10/D  Level editor" on the empty line 1 of the Options page through the game's own printer (`jsr $3b360`, the displaced `bsr` is redone first). Code1 grew to 5110 B (limit moved from `$76b0e` to `$76c00`: `$76b0e..$76bff` is part of the verified-zero gap, the trainer blob starts at `$76c00`).
Docs: README template ("HOW TO OPEN IT"), `nebrelease.py` DOCS entry, this section and the §9 start paragraph.
F9 then F10 (user remark; F9 work dropped by the user's decision): F9 code `$ffd20` copies game RAM `$8..` to `$80008..`, restores the TOS low RAM from the START-entry copy and ends with `Pterm(0)`; [obs] after an F9 tap on the title the machine restarts (HDDRIVER banner, AUTO prompt, then START again with `--auto`). So a game started after F9 is a second START launch: [INFERENCE, not run] START derives its memory class from `phystop` (`boot.md` section 2: class 1 = 512 KB = no Gamex hooks, game at `$4e000`) and START forces `$42e = $80000` on every machine, so a relaunch in the same TOS session would run in class 1 where neither F9 nor the patch sites (fixed RAM addresses) apply: F10 would then do nothing.  Not investigated further.

**Gates for the fix** [obs, `work/keys/`, image = shipped image with START.TOS/NEPATCH.BIN/NEBLEVEL.OVL replaced by `nebrelease.py build` output, run_ste.sh options, XTEST taps]:
```
cold boot STE 1 MB TOS 1.62:   title 54.5 s after Hatari start; $3851a 4ef9000778e6, $3d662 4ef900077904 4e71 (hooks in RAM); debugger `m $b0020` NEPO count 20 (20 sites = 18 + the 2 new)
cold boot Mega STE 4 MB 2.06:  title 128 s; NEPO count 20, same hook bytes; F10 and D open the manager
F10 taps, nominal hold 20 ms:  pages 0/1/2 = 4/4, 4/4, 4/4 (first build 6/6 x3); the shipped image lost 3 of 10 at 30 ms (page 0)
D, hold 100 ms:                pages 0/1/2 = 4/4 x3
in a tower (--joy1 keys, Right + fire start): F10, D, F10, D taps: $70 stays $382d8 (no editor), rsKey 0, timer keeps counting; Q -> title, page word valid, no spontaneous editor; F10 on the title then opens it (STE and Mega STE)
Options page vs shipped build (same page phase, 832x588 shot): 2328 px differ, all in x 256..557, y 266..289 (= the new line); credits page and High Scorers page 0 px
equivalence (e97, 10 live commands now 3 blocks + 9 sites, scripted input 1113 loops): player vars 0 diffs, creature/timer/energy 0 of 1113, framebuffer 0 bytes; the only non-player word that differs is $33a38 (the game printer's text cursor, 29560 = line 5 vs 16760 = line 1 from loop 247, when the dead frog returns to the title and the Options page's last print is now the hint line instead of line 5; it is reloaded before every print); stock-vs-stock baseline (e96): 0 differences
```

**Why F10 still opens with ni_latch's `andi.b #$f0,d0` in front (NebFloppy question)**: `ed_key` does NOT compare d0. Its first instruction is `move.b $38498.l,d0` and the `$44` compare is on that reload; d0 is dead at `$3851a` anyway (the handler's own `move.w (a7)+,d0` follows). My first build compared d0 and was wrong exactly as suspected: with ni_latch present d0 = `$44 & $f0 = $40`, the latch never set, a 20 ms tap did not open the manager (`t3`: 7/7 lost; trace `t6.py` showed ACIA+KEY events but `$70` unchanged and rsKey 0) [obs]; reading the cell fixed it (same tap: opened, 18/18 over pages 0/1/2). The cell is stored before `$3851a` on both routes: by ni_latch's stub1 (`move.b d0,$38498.l` first) or, with ni_latch absent, by the game's own `$38514 move.b d0,$38498.l`; bytes >= `$f6` jump to `$3851a` without a store, the cell then still holds the previous byte (harmless: at most the latch is set again while F10 is still held down). A break code `$c4` never sets the latch (exact compare with `$44`; `$c4` != `$44`); evidence: every trial's manager was closed by a 0.6 s F10 hold (make `$44` consumed, break `$c4` 0.6 s later) and the title never re-opened it (`close_mgr` returned on the first try in all trials) [obs]. Both compositions tested [obs, cold boot STE, XTEST taps]: default set (ni_latch present): F10 20 ms 12/12, D 100 ms 12/12; `--only ed_overlay` (no ni_latch, `build/keys_only`, 9 sites): see the line below.
`--only ed_overlay` (no ni_latch; `build/keys_only`, 9 sites) [obs]: F10 nominal 20 ms taps pages 0 and 1 = 4/4 + 4/4; D 100 ms page 0 = 3/3. Also on the default set: `hatari-event keydown/keyup 68` 60 ms 4/4 and `hatari-event keypress 68` (immediate down+up) 4/4 on page 0 (the shipped image was not run with keypress).

## 12. CAMPAIGN DISK: game-independent spec (round 3; for the community site's packager) and how the game uses it
Tool: `python3 tools/nebcampaign.py new OUT.st|OUT.msa [--ovl FILE]` / `info IMG` / `extract IMG OUT.ovl` / `check IMG` (pure Python, uses `work/editor/ovl.py` for the content check; `new` output is byte-identical to NebFloppy's `nefloppy.campaign_disk`; `fsck.fat -n` and `mdir`/`mcopy` (mtools) accept the image [obs]).
**Medium**: a 720 KB double-sided double-density FAT12 floppy image, 737,280 bytes = 80 tracks x 2 sides x 9 sectors x 512 B, raw sector dump (`.st`) or Magic Shadow Archiver (`.msa`, uncompressed tracks written, RLE tracks read).  An 880 KB / Amiga `.adf` variant is **not provided**: an ADF is an Amiga OFS/FFS volume, not FAT (the Atari editor cannot read it; the site converts an ADF campaign by extracting the file and writing it into a FAT image).
**Layout** (all little-endian BPB as on every PC/ST disk): boot sector `eb 34 90`, OEM `NEBLV`, bytes 8..10 = volume serial, BPB: 512 B/sector, 2 sectors/cluster, 1 reserved sector, 2 FATs, 112 root entries, 1440 sectors, media `$F9`, 3 sectors/FAT, 9 sectors/track, 2 heads; boot-sector checksum != `$1234` (NON-executable: TOS never runs it; asserted by the tool).  FAT1 sectors 1-3, FAT2 4-6, root directory sectors 7-13, data from sector 14.  Root directory: volume label `NEBCAMPAIGN` (attribute `$08`), then `NEBLEVEL.OVL` (attribute `$20`, start cluster 2, size 8192, fixed time/date so the output is deterministic); clusters 2..9 chained 2->3->..->9->EOF = sectors 14..29.  Nothing else on the disk (other files would be ignored and untouched).
**Serial rule (needed)**: bytes 8..10 of the boot sector = the first 3 bytes of md5(`NEBLEVEL.OVL`).  The game forces TOS to re-read drive A: on every Load/Save (below), so the serial is not needed by the game itself, but any other TOS program (and the desktop) tells a swapped disk from the old one by it.
**Content rule** (what the game accepts): `NEBLEVEL.OVL` must be at least 8192 bytes (the first 8192 are the store; the tool writes exactly 8192; a longer file is read/written in its first 8192 bytes only and never touched beyond), and those bytes must be either a VALID campaign file (section 3.2 validity: magic, version 1, counts, ranges, popcount(mask) == stream length: the same check as `ovl.py validate`) or all zero (= empty store).  Anything else: "Not a campaign disk" and the levels in memory are kept.  Load replaces the whole store (levels + campaigns); Save overwrites the file in place.
**Game flow**: manager `Load from campaign disk` / `Save to campaign disk` (and the cell menu's `Save to campaign disk`) -> own prompt (menu screen, `Insert campaign disk in drive A:` / `then press fire (F10 cancels)` / `< back`; LEFT or F10 = cancel; no disk access before FIRE) -> `disk_op`: SR $2700, game MFP saved, **TOS excursion** (section 2: swap the TOS-owned low RAM with the TOS-state copy, restore TOS's MFP block, SR $2500), then in the TOS world: (1) `etv_critic` ($404) is replaced by `crit` (returns the BIOS error number = abort) so TOS can never raise its retry/abort dialog; (2) BIOS `Getbpb(0)`: a null BPB = nothing readable in drive A: -> **"No disk"**; (3) `hdv_mediach` ($47e) is replaced for the first query of drive A: only (returns 2 = "changed"; then it uninstalls itself) so BDOS drops its cached view of the previous disk (without it a swapped disk was not noticed: all later opens saw the first disk's directory [obs `e160b` run 1]); a PERMANENT 2 hangs BDOS in a retry loop [obs: second op never returned]; (4) `Fopen("A:\NEBLEVEL.OVL")` (mode 0 load, 2 save) -> -33 (file not found) = **"Not a campaign disk"**; (5) `Fread` 8192 bytes into `BUF $AA000` (short = "Not a campaign disk"; for a Save this is the "file exists and is full size" check, so a save never allocates clusters or changes the FAT); (6) Load: `load_fin` validates BUF (valid campaign file or all zero) and only then copies it over `OVS` (a rejected file never touches the store); Save: `Fseek(0)` + `Fwrite(8192)` from `OVS`; (7) `Fclose`; everything is swapped back, the game's MFP restored, the ACIA drained (a byte left in it blocks the keyboard, section 2), SR restored.  The BIOS error -13 (write protected) on the Fwrite -> **"Disk is write protected"** (nothing written: the FDC refuses before the first sector); other errors -> "No disk".  Messages: `Loaded N levels / M campaigns`, `Saved`, `No disk`, `Not a campaign disk`, `Disk is write protected` (manager: line 11 from column 8; editor: status line from column 16).
**Cost**: the screen is frozen (VBL masked, keys not read) during the operation: about 3-5 s with a disk, 5 s when drive A: is empty (Hatari FDC timing) [obs `e160e`]; on a real drive an empty drive spins up/retries for a similar time.
**The game disk is never written** by the editor; the stub's boot-time read of `NEBLEVEL.OVL` from the game folder to `$BC000` is kept (costs nothing in the editor: it lives in `nepatch`'s stub, which still writes a zero file into the build) as an optional starting set; nothing writes it back, and since a zero file means "empty store", leaving it out or zero is the same.

## 13. Round 3 (NebEditor3): lifts, keyboard shortcuts, campaign disk, memory budget, floppy
Tags as above; raw logs of the final build quoted below come from `work/editor/e140.py` (lifts), `e150.py` (shortcuts / trainers), `e160b-e160h.py` + `e161.py` (disk), `e170.py` (cold boots), `e97.py` (equivalence), `e90.py` (fuzz); test disks from `work/editor/mk_disks.py`, debug builds from `work/editor/mkdbg.py` + `dbgbuild.sh`.

### 13.1 Lifts replace the "Pale block" (stage 1)
The cell menu entry "Pale block" placed `$85`, which is the LIFT START slab (`work/notes/lifts.md`): every "pale block" was a lift start with no end (the ride then only ends by hitting terrain and hurts the frog).  `ed_editor.s` now has **Lift >** instead (`work/lifts/ed_lift.s` merged, fourth block `CODE3 $77a40`): `Lift: from here` writes `$85`, arms `vLift` (= row+1), locks the cursor to the column (left/right ignored, status "Lift: U/D = other end"); FIRE (or RETURN/SPACE) at another row sets the end: above -> `$08` there; below -> the first cell becomes `$08` and the picked row the slab (either order); the editor adds the `$81` ledge under the slab when that cell is empty; F10 cancels (the lone slab stays, `Lift: delete` removes it); `Lift: stop here` writes `$0c`; `Lift: delete` removes slab + stops + end of the lift the cursor is in (cursor on its end or in its shaft).  Warning "Pillar blocks lift" when a `$80` sits between slab and end.  Tiles: id 6 = lift slab (name "Lift start"), 17 = `$08` "Lift end" (arrow), 18 = `$0c` "Lift stop" (arrow + bar), so the markers are visible (`classify` returns them for non-terrain cells with `&$0c` = 8/$c).  The format is unchanged (three cell values in one grid column).
`ovl.py` got `work/lifts/ovl_lifts.patch` (applied; byte-identical to `work/lifts/ovl_patched.py`): `lifts FILE LEVEL`, `lifts-orig MISSION TOWER`, lifts in `dump`, drawn in `render`.  Re-run after the patch [obs]: `test3` -> `validate` OK; `dump` lists the two lift starts without an end of that old test level (its `$85` cells at (3,2),(4,2) were the "pale blocks"; they are cells, the test is still valid as a grid edit); `lifts-orig 1 1` = 6 lifts, over all 16 shipped towers 6 9 6 7 10 11 14 9 | 6 6 8 11 10 9 14 9 = 145 lifts, 0 warnings; `import-original 1 5` -> validate OK; `render` writes the png.

**Evidence (`e140.py`, STE, final build, raw)**: F10 -> Levels -> `<new level>` -> cursor (2,2) -> Lift > -> from here: `from_here ... vLift 3 | col2 00 81 85 00 ...`; Up x8: `picking cy 10 vLift 3`; FIRE: `lift_set cy 10 vLift 0 | col2 00 81 85 00 00 00 00 00 00 00 08`; Playtest (E, T trainers; Right 0.6 s; Up held): `frog before ride x 0x13 y 0xc st 0`, `ride 1: x 0x14 y 0x2c st 0 col2 00 81 84 80 80 80 80 80 80 80 89` (frog at row 11, one above the end marker at row 10), `ride 5: y 0xc col2 00 81 85 00 00 00 00 00 00 00 08` (platform returned, end marker restored); F10 back in the editor, grid intact; leave editor; `Save to campaign disk` on a blank disk image -> `nebcampaign.py extract` -> `NEBLEVEL.OVL valid: 1 levels / 0 campaigns`, `ovl.py validate` OK, `dump`: `lift col 2 rows 2..10 stops []`.  Keyboard path and the other orders (`e150.py`): `a`, Up to row 8, Return: col 2 rows 0..9 = `00 81 85 00 00 00 00 00 08 00`; `z` at row 5 = `$0c`; `a` at row 14 then Space at row 8 (end picked BELOW): col 15 rows 6..14 = `00 81 85 00 00 00 00 00 08` (slab at 8, ledge at 7, end `$08` at 14); pillar at row 6, lift 2..9: status "Pillar blocks lift" (`e150_pillar_warning.png`, `e150_lifts.png`); render of the saved level `e140_render.png`.  `lifts-orig` over the 16 shipped towers [obs, re-run]: 145 lifts, 0 WARN.  Screens: `e140_submenu.png`, `e140_picking.png`, `e140_ride.png`.

### 13.2 Keyboard shortcuts and the trainer keys (stage 2)
**Key map** (IKBD make scancodes, ST key positions with US legends; every key is the menu's own action: `kbtab` in `ed_editor.s` = scancode, action.b, param.b, 16 entries; the cell menu shows the letter after each name, which is the legend; the status line says `Fire=menu Ret=again`):
| key (scancode) | action | key (scancode) | action |
|---|---|---|---|
| C `$2e` or Delete `$53` | empty | S `$1f` | stone ball `$10` |
| L `$26` | ledge `$81` | R `$13` | red ball `$20` |
| P `$19` | pillar `$80` | W `$11` | red ball, waits `$30` |
| B `$30` | blue block `$82` | U `$16` / I `$17` | eye up/down slow `$40` / fast `$50` |
| D `$20` | door opening x3 `$83` | J `$24` / K `$25` | eye left/right slow `$60` / fast `$70` |
| X `$2d` | exit door x3 `$c3` | A `$1e` | lift: from here (arms the "other end" pick) |
| Z `$2c` | lift stop `$0c` | Return `$1c` / Space `$39` | repeat the last tile (paint); while a lift end is pending = FIRE (sets the end) |
The same enemy key again on the same enemy turns it round (start direction bit 0, `a_ekey`); a different cell gets the key's default direction.  `rsLast` remembers the last placed value for the menu paths too (`a_set`, `a_tri`, `a_enemy`/`a_edir` call `rec`), so Return repeats what the menu placed.  Shortcuts act only in the map view (not in menus, lists, name entry; during a pending lift pick only Return/Space act).  Letters were chosen because the game's key path delivers them reliably: scancodes `$10..$7f` have bits 4-6 set and can never be mistaken for joystick bytes (which have bits 4-6 clear); digits `$02..$0b` and Backspace/Tab/Esc (`$01..$0f`) are indistinguishable from joystick states (the game's own `$3853a` test) and are NOT used; T `$14` and E `$12` (trainers) and F-keys are not used; **D is the title's second manager trigger, but that is read only by the title poll; in the editor D = door opening**.  Positions, not letters, are what the ST sends: on a non-US ST keyboard (QWERTZ/AZERTY) the key at the US position is meant.
**How the key reaches the editor**: `ed_key` (the ACIA hook `$3851a`, section 11) now also latches every other make byte in `RS+rsKb` (low byte of a word; a byte equal to the previous one is ignored via `RS+rsPv`, so a dropped header byte, which leaves the game's cell unchanged, cannot latch the same key twice); the editor loop takes it each VBL after `jsr $3853a`; a tap shorter than a frame is therefore not lost (same mechanism as F10).  Latches are cleared at editor entry and exit.  Mouse/joystick data bytes are stored by the game as "keys" too; those with bits 4-6 clear never match the table, a mouse byte that happens to equal a shortcut scancode can act like that key (the game itself has the same property) [INFERENCE: no mouse test].
**Trainers (T/E) vs the editor**: the trainer hooks live in the game's frame loop (`$3dcf4` key poll + edge detect on `$38498`, `$3b0a4` timer head, `$3792c` spawn head).  The editor's own loop (`ed_run`) NEVER executes them: the title poll hook (`$3d6c4`) and the flip hook (`$3dfd6`) call `ed_run`, which runs its own `jsr $3853a` poll, and the game loop is suspended below it.  So in the EDIT view T/E can not toggle, by construction, and no code had to be added to the trainer blob (`$76c00..$76c75`, unchanged: that blob also belongs to another patch).  In a PLAYTEST the game loop runs and T/E work as the author's checking aid.  Leak guards: the editor clears the game's key cell `$38498` and both latches on entry and on exit (the trainer's edge detector compares the cell with its `prev` byte, so a stale `$14`/`$12` could otherwise toggle on return), and `ed_game`/`ed_title` consume F10 as before.

### 13.4 Floppy build: what it needs (stage 3, NebFloppy question)
**Finding**: the floppy build has NO Gamex TOS-state copy, so the HD build's `disk_op` cannot run there as it stands (it would read `$ffd80`/`$ffd86`/`$fffaa`, which are random bytes in the floppy flow).  The editor no longer reads those addresses directly: the excursion takes the copy's address, its length and TOS's MFP block from three runtime-state variables, `RS+rsTosP` (long), `RS+rsTosN` (word, bytes/48 - 1), `RS+rsMfpP` (long), and initialises them from the Gamex addresses only when `rsTosP` is zero (the HD build).  **A floppy boot stub that takes the same snapshot at start-up and sets the three variables makes Load/Save work there without any other editor change.**  The snapshot routine is in `patches/ed_floppy_capture.s` (about 100 bytes; copies TOS's low RAM `$8..membot` (`$432`) to `$c0108` (free on a >= 1 MB machine; the editor needs >= 1 MB anyway), appends the 24-byte MFP block (`mfp_save`), sets the variables).  Cost: 1 copy of about 100-110 KB at boot (about 0.1 s) in RAM that is free anyway.  **NOT tested**: there is no floppy harness in this tree that runs the editor's disk code, and I did not run NebFloppy's build with the new editor.  What has to be verified on the floppy flow before trusting it: (a) the TOS state at the stub is intact (TOWERTOP/Atomik may have changed TOS vectors `$70`, `$114`, `$120`, `$134`, the MFP, or its own basepage/TPA could sit in the copied range: the copy is taken from the stub, after the game was relocated); (b) Load/Save with the GAME disk swapped for a campaign disk in drive A: (a single drive: the game never reads its disk again after loading [obs, floppy.md]); (c) the same excursion gates as the HD build (no disk / not a campaign disk / write protected / fuzz).  Until then the floppy build should keep its "Kept in RAM" message.
**What NebFloppy's tool must change for this editor revision** (`tools/nefloppy.py` is not mine; `_asm_editor`/`gen_editor`): (1) the assembly now has SIX segments, not three: `CODE1 $75740`, `DATA $76d40`, `CODE2 $77300`, `CODE3 $77a40` (lifts), `CODE4 $77dc0` (disk module), `CODE5 $76c76` (small helpers); `gen_ed.py` (this tree) shows the order/limits (`LIM`); the assert `[CODE1, DATA, CODE2]` fails otherwise; all six blocks sit at the same addresses on the floppy; none overlaps the stub at `$77ec0` (CODE4 ends `$77ebc`); (2) `save_file:` / `swap_tos:` anchors are gone: the disk code is `disk_op:` (CODE4, up to `crit`/`tos_file`...) and `c_dgo` shows the result: either keep the module (stub captures the TOS state, see above) or replace the block from `disk_op:` to the `rw:` routine by `disk_op: moveq #1,d0` / `rts` (the manager then says "No disk"; a floppy-specific text would replace string 1 of `sMsgs`); (3) the new code has no new game addresses (only `$47e`, `$404` TOS vectors, `$ffd80`-region reads guarded by `rsTosP`), so `remap_source` needs nothing; (4) entry points the `.nep` sites use are still `ed_key` and `ed_opt` (translate by symbol as before); (5) the HD zip now ships a blank campaign disk; the floppy zip's `Nebulus_campaign_disk.st` is byte-identical to `nebcampaign.py new` output (checked [obs]).

**Evidence (`e150.py`, STE, final build; 31 PASS, `FAILS []`)**: blob `$76c00` (prev, pad, frz, noen) = `000000000000` at the title; T,E,T,E pressed in the edit view: unchanged; each of 13 shortcut keys at its own column on row 10 gives the expected cell (`l 81, p 80, b 82, d 83 83 83, x c3 c3 c3, s 10, r 20, w 30, u 40, i 50, j 60, k 70, c 00`); `s` again on the same cell `$11`, again `$10`; `l` then Return, Space: `[81, 81, 81]`; Delete clears; blob still `000000000000` after every shortcut key and after unmapped letters (q y f g h m n o v t e); straight into Playtest: running, timer moves (`002000200014` -> `00200018000d`), trainer flags still 0; in the playtest `e`,`t`: blob `9400ffffffff` (T/E work there); F10 back to the edit view, `t e t e t` pressed: flags stay `ffffffff` (no toggle).  Not run: the shortcuts on Mega STE (the e170 / e161 gates run there; the editor code is machine independent) and with a real keyboard.

### 13.3 Campaign disk: evidence (stage 3)
Test disks (`work/editor/mk_disks.py`, in `/tmp/ne/d/`): `blank` (all-zero file), `t3` (valid, 1 level / 1 campaign), `nofile` (FAT12, no NEBLEVEL.OVL), `short` (file of 4096 B), `big` (8192 B of text), 22 fuzz disks (the 22 files of `e90.py`, each in a disk).  Harness: image inserted at run time with `hatari-option --disk-a IMG` (HD build: game on the ACSI image, floppy A: = the campaign disk), `--protect-floppy on/off` for write protection.  Gate `e161.py` (raw log `/tmp/e161_ste.log`, STE 1 MB / TOS 1.62; `/tmp/e161_megaste2.out`, Mega STE 4 MB / TOS 2.06 (everything except the 22-file loop); every line below is `PASS`, `FAILS []` on both):
```
empty drive                            'No disk'                       (5.3 s: Getbpb(A) -> null BPB)
disk without NEBLEVEL.OVL              'Not a campaign disk'           (Fopen -33)
NEBLEVEL.OVL 4096 B                    'Not a campaign disk'           (Fopen handle 6, Fread 4096 < 8192)
8192 B text file                       'Not a campaign disk'           store unchanged
blank campaign disk (all-zero file)    'Loaded 0 levels / 0 campaigns' store == zeros
valid campaign disk                    'Loaded 1 levels / 1 campaigns' store == file
write-protected disk, load             'Loaded 1 levels / 1 campaigns'
write-protected disk, SAVE             'Disk is write protected'       image unchanged
22 fuzz disks                          valid ones (flip1, flip3, flip5, flip8, badentries, valid) 'Loaded 1 levels / 1 campaigns', the 16 others 'Not a campaign disk'; after EVERY one: store == file (accepted) or store unchanged (rejected); parity with `ovl.py validate` / `nebcampaign.py status`; game alive
Save from the editor root menu         'Saved'  -> RAM store has 2 levels; the image after the save: usable campaign disk (`nebcampaign.py check`), its NEBLEVEL.OVL == the RAM store byte for byte; boot sector, FATs, directory identical to the original image; only the file's 8 clusters differ
Save to a disk without the file        'Not a campaign disk'           image unchanged
Save to a write-protected campaign disk 'Disk is write protected'      image unchanged
Load the disk saved above              'Loaded 2 levels / 1 campaigns' store == saved file
tower after all of it                  timer runs, frog answers the joystick (x changed)  [Original game path: F10 -> title -> fire]
```
Before the final design the same scenarios were probed with a debug build (`mkdbg.py`: raw GEMDOS results in `V+176..188`): Fopen of an empty drive returns -33 (file not found), NOT a drive error, so "No disk" needs the explicit `Getbpb(0)`; the swapped disk was NOT noticed by TOS/BDOS in Hatari (every later Fopen saw the first disk's directory; boot-sector serials differed): `hdv_mediach` override fixed it (a permanent "changed" hangs BDOS; the first-query-only override returns in 3-5 s); with `crit` returning -1 a write-protect error arrived as -1 (generic), not -13: `crit` now returns the BIOS error number (`move.w 4(a7),d0 / ext.l d0`), and "Disk is write protected" works.
Screens: `e161_ste_prompt_in_editor.png`, `e161_ste_nodisk.png`, `e161_ste_notcamp.png`, `e161_ste_loaded.png`, `e161_ste_wp.png`, `e161_ste_saved.png` (+ `e160_prompt.png`, `e160_main.png`).
**Not done / limits**: drive B: (the path is the constant `A:\NEBLEVEL.OVL`, `fname`; no B: option: not built, trivial to add later); real floppy hardware and real disk-change timing (the first-query `hdv_mediach` trick is TOS-version independent in principle: `$47e` is the BIOS media-change vector since TOS 1.0 [INFERENCE: tested TOS 1.62 and 2.06 in Hatari only]); a disk swapped between the prompt and FIRE is fine, one swapped during the 3-5 s operation is not (do not touch the disk while the screen is frozen); TOS 1.04 (ST) not re-run this round.

### 13.5 Code size and memory budget (all six blocks, `gen_ed.py` output)
```
blocks: CODE1 $75740..$76bfc 5308 B (free 4); DATA $76d40..$7726c 1324 B (free 148); CODE2 $77300..$779e8 1768 B (free 24); CODE3 $77a40..$77c66 550 B (free 26); CODE4 $77dc0..$77ebc 252 B (free 4); CODE5 $76c76..$76cfe 136 B (free 2) | total 9338 B
```
Measured totals: round 2 = 8110 B in three blocks (5116 + 1390 + 1604); after Lift > = 8652 B (4 blocks); after the shortcuts = 8908 B; the campaign disk module before the compaction pass = 9498 B (6 blocks); final 9338 B (+1228 B over round 2 for lifts, shortcuts and the disk module together).  Where the room came from: (1) the excursion's private stack moved from `$77dc0..$77eb8` (inside game RAM) to non-game RAM `STK = $AD000` (the stack the TOS excursion needs is far below 4 KB; the region `$AC000..$AD000` is outside game RAM and F9 area problems do not apply to a transient stack) -> `CODE4` (256 B); (2) 108 editor-only `RS+rsXxx.l` absolute accesses (6 bytes) became `RSV+rsXxx(a5)` (4 bytes; a5 = V in every editor-only routine; hooks that run in the game keep the absolute form: ed_dec, ed_dir, ed_time, ed_name, ed_next, apply_entry, ed_game, pt_done, run_result, ed_title, ed_vbl, cur_rec, lvl_ptr, camp_ptr, store_end, ov_ok, ed_key, ed_opt, and the excursion code where a5 is clobbered) = 216 B; (3) 9 unused strings and a duplicate (`sTower`.. `sBackC`, 69 B), the old "H = key list" idea (a legend screen) became the letters in the menus; (4) the `$76c76..$76cff` gap behind the trainer blob is used (`CODE5`).  Free now: 4+2+148+24+26+4 = 208 B in the blocks, + 24 B `$75728..$7573f` (the relocation-table remnant before CODE1; the hook table could start there) + 4 B `$76d3c..$76d3f` = **236 B**.  **The budget is nearly exhausted**: any further editor feature must free room first (candidates: merge `m_levels`/`m_camps` (about 70 B), `colbase` for the four hand-written cursor-column computations (about 50 B), the tile `pad` bytes (19 B)).  Non-overlap (asserted by `gen_ed.py` and visible in the numbers): trainers `$76c00-$76c75`, latch `$76d00-$76d3b`, credit `$77a00-$77a3f`, state `$77c80-$77dbf` (RS 64 B, V 256 B) against all six blocks.

### 13.6 Gates (final build, STE 1 MB TOS 1.62 unless stated)
```
python3 tools/nepatch.py verify         predicted stage-2 image vs ram_stage2_1mb.bin: 271849 game bytes compared, 0 differ; all 20 sites dump-orig OK
cold boot STE 1 MB / TOS 1.62 and Mega STE 4 MB / TOS 2.06 (e170.py): marker NEPO, site count word 0x14 = 20, $3851a/$3d662 hooks 4ef9, CODE1 4ef9 / trainer blob 4eb9 intact, CODE4 filled; F10 (100 ms tap) opens the manager (VBL vector != $382d8), F10 leaves again ($382d8), D opens it again: all PASS on both machines
editing session + Save + reload: e161.py (above, STE and Mega STE); lifts: e140.py (13.1); shortcuts: e150.py (13.2)
equivalence of normal play (e97.py = scripted2/cmp_sc, 10 live commands now 6 blocks + 9 sites + keys): 1117/1120 loops after timer start; player-variable differences 0; creature/timer/energy 0 of 1115; framebuffer event 1: 0 differing bytes; the ONLY non-player word that differs is `$33a38` (the game printer's text cursor, from loop 247, the benign Options-hint effect of 11)
fuzz, boot-time store path (e91.py, 6 of the 22 files restored over $BC000 in a title snapshot: random0, magic+random, flip1, version2, badentries, valid): rejected ones lose the magic, accepted ones edit and play, 0 errors in every Hatari log, VBL keeps running; fuzz, disk path: 22 of 22 (13.3)
```

### 13.7 "No disk" on the floppy build (this session) and the media-change counter
The floppy build's campaign-disk gate found one wrong message: with drive A empty the editor said "Not a campaign disk".  Cause: `tos_file` called `Getbpb(0)` BEFORE
installing the `hdv_mediach` override, so TOS answered from its cached BPB (it had read the game disk at boot) and the Fopen's failure (-33) was all the editor saw.
Fix in `ed_editor.s`: the override is installed first and answers "changed" for **two** drive-A queries (`V+vMcnt` = 2, decremented in `mchg`): the first one makes
`Getbpb` re-read the boot sector (an empty drive -> null BPB -> "No disk"), the second makes the Fopen's own media check re-read the directory (a swapped disk).  TOS's own
routine answers again afterwards (a permanent 2 makes BDOS loop).  Cost: one extra boot-sector read per Load/Save, measured 2 to 5 s with a disk, ~9 s on an empty drive.
`rw` moved from CODE1 to the tail of CODE3 (CODE1 had 4 free bytes; CODE1 is 5306 B now, CODE3 570 B, both 6 free).  Gates: HD `e161.py` all PASS (empty drive "No disk",
swapped disk, save, write-protect, image checks) and the floppy `work/floppy/f161.py` cells (below).

### 13.8 Junk RAM (MiSTer): RS/V are zeroed by the loader
RS `$77c80..$77cbf` and V `$77cc0..` were assumed zero at boot (a junk `rsTest`/`rsKey` opened the editor by itself; junk `rsOk` skips the store validation; junk `rsTosP` breaks the first Load/Save).  `ed_overlay.nep` now carries `clear 77c80 140`, executed by `nepatch`'s core2 at every start; `ed_editor.s` is unchanged.  Inventory, fix and gates: `work/notes/junkram.md`.

### 13.9 `swap_tos` exchanges 24 bytes more than the copy (found on the floppy build; shared code NOT changed)
`swap_tos` uses `lea 8(a0,d0.l),a6` with `a0 = 8`, so its loop runs one 24-byte chunk past `(rsTosN+1)*48`.  Anything placed directly behind the TOS-state copy is swapped with game RAM before `mfp_set` reads it.
The floppy capture did exactly that with TOS's MFP block (-> excursion with the MFP off, no Timer C, empty drive never times out); fixed there by a 24-byte gap (`patches/ed_floppy_capture.s`), see `floppy.md` section 10.
HD: Gamex's MFP block is at `$fffaa`, not behind its copy, so the HD gates are unaffected; the loop was deliberately left alone (CODE4 stays `$77dc0..$77ebc`, 252 B).

### 13.10 Odd-aligned records (NebOddFix, critical fix after NebLooks' report)
**Written invariants of the record layout (section 3; the format is unchanged, `version` stays 1, old files keep working):**
(1) level records are packed **back to back, unpadded**: `record size = 20 + len`, so any level with an odd number of non-zero cells makes the next record start at an **odd** offset, hence at an odd RAM address in the game (the store `OVS` is at the even `$BC000`, the first record at `+272`).  **Every reader must be alignment-safe** (read `len`/`time`, and anything else wider than a byte, as bytes): a 68000 word/long access at an odd address is an address error (bombs/lockup on real hardware, a spinning TOS in Hatari).
(2) `flags.b` (record offset 3) is **reserved**: readers ignore it (`ov_check`, the decode hook and the game side never read it), **writers preserve all 8 bits** (editor Edit/commit, Copy, Delete, Save/Load and every campaign operation); a new level starts with 0.  Its meaning is not defined here (the NebLooks design uses the low nibble for the enemy eye design and the high nibble for the colours: not yet defined, not interpreted by this code; the editor round owns the semantics and the site parser change).

**Bug** [obs, build before the fix, `NebLooks`' `looks.ovl` = ten 159-byte levels, STE 1 MB / TOS 1.62, title, F10]:
```
WARN : Address Error reading at address $bc1b3, PC=$77814 addr_e3=77814 op_e3=3a29      (op 3a29 = move.w 4(a1),d5 in ov_check)
WARN : Address Error reading at address $bc1af, PC=$70 ...                                (the VBL vector $70 is already $e03380 = TOS: the machine spins, the manager never opens)
```
The same file padded by one cell (even record size) works.  The released v1.1 editor can write such a file itself (two levels with odd cell counts, then Save), the site's cart builder and `ovl.py` can too.

**Every 16/32-bit access to record data at a possibly odd address** (pre-fix `patches/ed_editor.s`, HEAD line numbers; all were `move.w` on a pointer that walked the packed records):
| line | routine | instruction | why it can see an odd address |
|---|---|---|---|
| 132 | `lvl_ptr` (every level lookup: level list, Play, Edit, ed_dec/cur_rec, apply_entry, campaign entry names) | `move.w 4(a0),d1` | walks `len` of the preceding records |
| 146 | `store_end` (Copy, Delete, commit: append/replace) | `move.w 4(a0),d1` | same walk |
| 219 | `ed_time` (game hook `$3adb4`, initial time of EVERY custom level start, playtest included) | `move.w 6(a0),d1` | time word of the current record (offset 6) |
| 1365 | `lv_edit` (Levels > n > Edit) | `move.w 6(a0),RSV+rsTime(a5)` | time word of the record |
| 1409 | `lv_copy` | `move.w 4(a3),d3` | len of the record to copy |
| 1436 | `lv_delete` | `move.w 4(a0),d3` | len of the record to delete |
| 2085 | `commit` (replace in place) | `move.w 4(a3),d4` | len of the old record in its slot |
| 2272 | `ov_check` (boot-time/first-use validation `ov_ok`, Load from campaign disk `load_fin` at `BUF $AA000`) | `move.w 4(a1),d5` | len of record k+1 after an odd record k: the crash above |
Checked and **already safe** (byte accesses or even addresses): the game's decoder `$377a2`/`$37812`/`$37822` (`move.b (a0)+,d0` on the mask, `move.b (a1)+,(a2)` on the stream: no word read of record data; mask/stream start at record+20, odd after an odd record start, and work), the name printers `$3b344`/`$3b360` (byte reads, `ed_name` hands them `record+8`), `ed_dec` (`move.b 2(a0),d7`), `apply_entry`, `lv_play`, the level-list/campaign-entry name copies, `mb_add`, the three record move loops (`lv_copy`, `lv_delete`, commit `.cp`/`.ac` are byte loops), `commit`'s own writes (`move.w d0,4(a2)`, `move.w rsTime,6(a2)`: `a2 = TREC $BE000`, even, and the playtest copy `rsLvl = $7fff` is read from TREC, so it was never odd), the header words (`OVS+6/8`: even), `load_fin`'s long copies (`BUF`/`OVS` even).  `$3adb4` initial time and the title name are the only game-side consumers; both go through hooks (`ed_time`, `ed_name`).

**Fix** (no format change; copy/normalise was not needed): two bytewise helpers instead of the eight word reads.
`rdlen` (CODE1, 14 B: `moveq #0,d1 / move.b 4(a0),d1 / lsl.w #8,d1 / move.b 5(a0),d1 / rts`, a0 kept, d1.l = len) and `rdtime` (CODE2, 12 B: `rdlen` at `a0+2`, `tst.w d1` so callers can branch on a zero time).  `store_end` was folded into `lvl_ptr`'s walk (`walk:`; `store_end` = `d0 = nlevels`, `bra walk`: -18 B), which paid for the helpers.  Per-site cost: 0 B for the `len` sites (`bsr.w rdlen` = the 4 B of the word read; `moveq/move.w` pairs became `bsr.w / move.l d1,dN`), +2 B in `ov_check` (`move.l a1,a0` first), +2 B in `lv_edit` (`bsr.w rdtime` + `move.w d1,..`).
Flags (Main's review point): `rsFlg` (`RS+50`, byte): `lv_edit` loads `flags` (`move.b 3(a0),RSV+rsFlg(a5)`, +6 B), `c_newlvl` clears it (+4 B), `commit` writes it back (`move.b RSV+rsFlg(a5),3(a2)` instead of `clr.b 3(a2)`, +2 B); Copy/Delete/the campaign operations move bytes and never touched it; `ov_check` does not read it.
**Bytes**: `gen_ed.py` before: `CODE1 5306 (free 6) | CODE2 1768 (free 24) | CODE3 570 | CODE4 252 | CODE5 136 | DATA 1324`, total 9356 B; after: `CODE1 $75740..$76c00 5312 B (free 0); DATA 1324 (free 0); CODE2 1784 (free 8); CODE3 570 (free 6); CODE4 252 (free 4); CODE5 136 (free 2)`, total **9378 B (+22)**.  **Correction to 13.5**: DATA's real limit is `$7726c` (the ni_ikbd blob `$7726c..$772c5` starts there), not `CODE2`; the old `gen_ed.py` limit let DATA report "free 148" while it was full (the helpers first placed there were caught by `nepatch build`: "block $76d40..$7728a overlaps site $7726c").  `gen_ed.py` now checks DATA against `$7726c` and all blocks against the ni_ikbd blob.  Same six segments at the same addresses: `tools/nefloppy.py` needs **no mapping change** (the floppy capture still sits behind DATA, `$7726c..`, unchanged size).  Trimming candidates left: merge `m_levels`/`m_camps` (~70 B), cursor-column share (~50 B).
**Tools**: `ovl.py validate` unchanged (same rule as the loader; prints a `note:` on stderr when a record starts at an odd offset: valid, but a pre-fix v1.1 game crashes on it), `ovl.py dump` shows `@offset (odd offset)`, `ovl.odd_starts()`.  Fixtures/gates: `work/editor/mk_odd.py` (`work/editor/fixtures/odd2.ovl`, `flags35.ovl`, and `/tmp/ne/odd/`: looks, odd2, flags35, stress01..12), `work/editor/e180.py` (files; `--flow` editor flow; `--flags`; `--disk`).

**Evidence** (STE 1 MB / TOS 1.62, title snapshot of the fixed build, `e180.py`; raw logs `work/editor/logs_oddfix/`, the rest in `/tmp/oddfix/logs/` while it lasts):
```
pre-fix build, looks.ovl, F10 at the title:   Address Error reading at address $bc1b3, PC=$77814 ... $70 = $e03380 (TOS)
fixed build, odd2.ovl (levels 115 B and 165 B: record 1 starts at the odd offset 387 -> $BC183):
PASS odd2.ovl: level list shows all levels: ['ODD ONE', 'ODD TWO']
PASS odd2.ovl level 1 (record size 165) Play: grid == decoded record (ODD TWO): []
PASS odd2.ovl level 1 (record size 165) Play: rows/mission/tower: (40, 2, 5)
PASS odd2.ovl level 1 (record size 165) Play: initial time 480 s (remaining 466): True
PASS odd2.ovl level 1 (record size 165) Play: tower name hook A0=$bc18b text: b'ODD TWO\x00'      (A0 = odd address)
PASS odd2.ovl campaign 0 ODD2 entry 1..3 (custom, original M1 T3, custom): grid/rows/time/name all PASS; victory flow after the last entry: True
PASS odd2.ovl: no Address/Bus Error/exception in the Hatari log: []
looks.ovl (NebLooks, ten odd 159 B levels): list shows M1T1..M2T4; levels 0-5 started with Play: grid == decoded record, name hook A0=$bc118 / $bc1b7 / $bc256 / $bc2f5 / $bc394 ... PASS
flags35.ovl (flags $ca/$35/$ff, three odd records): Edit loads $35, after Edit+commit [202, 53, 255], after Copy [202, 53, 255, 53], after Delete [53, 255, 53], new level clears rsFlg, after a new level [53, 255, 53, 0],
   Save to campaign disk 'Saved', Load 'Loaded 4 levels / 1 campaigns', reloaded flags [53, 255, 53, 0]: PASS (the 2 image read-back checks in that log FAILED because the harness ejected instead of inserting another image; fixed in e180.py)
stress set (12 seeded files, --quick = every level listed/validated, the last and the first odd-start level started, campaign 0 entry 0 started): stress01..04 all PASS, 0 FAIL, no exception in the logs
python3 tools/nepatch.py verify: 27 verified sites, 3 clear ranges (332 B), 10 blocks; python3 tools/nefloppy.py selftest: ed_overlay unmapped generator == patches/ed_overlay.nep blocks: yes (all 5 generators yes)
```
**Open items** (not finished in this session; scripts exist, nothing in the fix depends on them being run other than as confirmation): the forced-door campaign walk over the REAL original towers of `looks.ovl` flakes in the harness (the frog meets enemies; odd2's walk passes: it is the harness, not the loader; the 10 levels themselves start); stress05..12 STE and Mega STE (`e180.py ... megaste`, snapshot boot 130 s), ST TOS 1.04, `--disk` (Load from a `nebcampaign.py new --ovl` disk, 3 machines), `--flow` (create two odd levels in the editor, Save, Load, play), the `--flags` rerun after the image read-back fix, e161 (22 fuzz disks), `work/junkram/gates/e91_jr.py`, e150, e140, e170, e97/e98 equivalence, floppy `fge.py` cells.  [INFERENCE] equivalence of normal play is unaffected: the changes only touch the custom-record readers (no hook on an original tower reads a record: `cur_rec` returns 0), but this is not measured.
**For the PC tool / site**: nothing to change in the format or in `ovl.py validate`; `ovl.py` now warns (stderr note, `dump` shows `(odd offset)`) when a record starts at an odd offset because a pre-fix v1.1 game crashes on such a file (a site that must keep working with v1.1 builds can only pad by adding/removing one non-zero cell per odd level so that every record size is even); the site's cart builder should ship the fixed game build, preserve `flags.b` when it rewrites levels, and read records bytewise if it parses them in a language with alignment rules.
