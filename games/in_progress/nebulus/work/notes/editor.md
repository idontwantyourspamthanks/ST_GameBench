# Nebulus in-game level / campaign editor (NebEditor)

Tags: **[obs]** observed (Hatari 2.6.1, scripts in `work/editor/`), **[disasm]** read from `work/train/dis_33000_40000.txt`, **[INFERENCE]** not proven.
Sources: `patches/ed_editor.s` (68000, ~7.6 KB), generated `patches/ed_overlay.nep` (`work/editor/gen_ed.py`), file tool `work/editor/ovl.py`, tests `work/editor/e*.py`, shots `work/editor/*.png`.

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
Not done / unproven: real hardware, floppy, 2-player, F9 inside the editor, copy/delete/rename ops exercised only by code review. `ed_dir` proven [obs `e61.py`, breakpoint at the spawn `$37a98`, slot-0 speed word]: markers `$10 $20 $40 $60` -> `+1`, `$11 $21 $41 $61` -> `-1` (`ffff`), `$30/$31` -> 0.

## 2. Persistence (how the ST saves its own file)
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
`00` empty; `80` pillar/stone; `81` ledge; `82`,`86` blue block, destroyed by one shot; `83`,`87` door opening (drawn as a dark gap, 3 cells tall); `85`,`89`,`8d` pale solid block; `c3` exit door (3 stacked); `91`,`a1`,`b1` ledge variants; `08`,`0c` inert markers; **enemy markers** (bit 7 clear): high nibble `10` stone ball, `20` red ball, `30` red ball (waits), `40`/`50` eye up-down (slow/fast), `60`/`70` eye left-right (slow/fast); **low nibble bit 0 = start in the negative direction** (down / left), other low bits unused. Unknown values are drawn/played by the game as it decodes them (they are never interpreted by the file format). The frog always starts at angle 0 on row 2 (so a ledge on row 1 near angle 0-1 is needed).

### 3.5 Capacity, versioning, packaging
Shipped-size level 250-400 B (record), dense up to ~1.8 KB; 8192-272 = 7920 B of level space = about 20 typical levels (campaigns cost 32 B each, fixed). To change the format: bump `version` (the game rejects unknown versions); the loader in the game only needs `version == 1`. Packaging: put `NEBLEVEL.OVL` (8192 B, any valid content, or zeros) in the disk root; the editor overwrites it in place (it never grows), so a site can ship a ready campaign file or an empty one. Sharing = copying the file.

Budget/limits summary: levels 16..120 rows x 16 angles; at most 127 levels, 8 campaigns x 16 entries, total 8 KB.

## 4. Loader and memory
Lead merged the tool: stub reads `NEBLEVEL.OVL` (absent = all zero) to **`$BC000`** (outside game RAM; the hooks check magic 'NCMP' so an F9 restore, which overwrites `$80008..$ffdc8`, just disables custom levels; the original game is untouched). `block ADDR HEX` = unverified copy into the dead zone `$75728..$77ec0`.
Game RAM (F9-safe): code `$75740..$76ae3` (5028 B), tables `$76d40..$7728f` (1360 B), code `$77300..$777b1`, runtime state `RS $77c80` (rsCamp/rsPos/rsLvl/rsEd/rsTest/slot/name... 48 B), editor vars `V $77cc0` (256 B), private stack top `$77eb8`. Non-game RAM: editor screen `$A0000`, dynamic menu buffer `$A8000`, working-copy record `TREC $BE000` (volatile, playtest). Conflicts checked against `$76c00` (trainers), `$76d00-$76d3b` (input latch), `$77a00` (title banner): none.

## 5. Hooks (jump table at `$75740`, 6 B each; sites in `ed_overlay.nep`)
`$377a2` decode (6 B `jmp`): record of `rsLvl` (custom, or `$7fff` = playtest copy) -> clear grid, `$33912` = rows, feed mask/stream to the game's loop `$37812`; else original. `$3adb4` initial time (record time if non-zero). `$3d110` tower name (record name). `$3e352` tower complete -> campaign progression: next entry (original: mission/tower + `rsLvl=0`; custom: `rsLvl=k+1`, mission/base tower from the record, player tower word updated); end of list -> `$3390c = 8` = the game's own victory/Congratulations/hi-score flow, `rsCamp = 0`; a single custom level ends the same way; in a playtest it returns to the editor instead. `$3d6c4` title poll: resets rsCamp/rsLvl/`$33a44` every poll, **F10** (`$38498 == $44`) opens the manager, a finished playtest (game over -> title) re-opens the editor. `$3dfd6` frame flip: F10 during a playtest -> editor. `$37a90` spawn direction (low nibble bit 0 of an enemy marker negates the start speed; all 160 shipped markers have low nibble 0 so originals are unchanged).
Start of play from the manager = `jmp $3d85a` (the title's own exit), restart of a playtest = `lea $800,a7; jmp $3dbb0` (new-game init: lives/score/timer reset), quit to title = `jmp $3db8c`.
**Proof (b)** [obs `work/editor/e33.py`, STE 1 MB, E trainer on, forced door entry]: level 1 `rsPos 0 tower 0`, grid vs stock M1 T1: no diffs; after force 1 `rsPos 1 rsLvl 1 tower 3`, diffs vs stock M1 T1 = `[(3,1),(3,2),(4,1),(4,2)]` (the 4 hand-edited cells), timer starts at 300 (`001800000000`); after force 2 `rsPos 2 rsLvl 0 tower 2`, grid == stock M1 T3; after force 3 `rsCamp 0, $3390c = 8, pl 9`.

## 6. UI
Title: **F10** or **D** (F10 is tap-proof through the ACIA latch, D is read from the cell; see section 11; not a game key; F1-F8 options, F9 Gamex, T/E trainers untouched). Own screen/palette/VBL (game timer B stopped, game state untouched), game font via `$3b344`. Joystick: move, fire = select/open menu, left = last menu item ("< back"), F10 = back/leave.
Manager: `Original game | Campaigns > | Levels > | Save to disk`. Levels: list, `<new level>`; per level Play/Edit/Copy/Delete. Campaigns: list, `<new campaign>`; Play/Edit entries/Rename/Delete; entries: `nn O m-t` (original) / `nn L name` (custom), `<add entry>`, per entry Change source/Insert/Remove/Up/Down. Names: up/down cycle letters (`name_edit`), left/right move, fire done.
Editor: flat 16 x rows map (8 px cells, 25 rows visible, scrolls), XOR cursor box, panel (tower, rows, col/row, cell value + name). Menu: Empty, Ledge, Pillar, Blue block (shootable), Pale block, Door opening (x3 vertical), Exit door (x3), Enemy >, Tower >, Playtest, Save to disk, Leave editor. Tower >: Look next tower / other mission (palette/backdrop/time base), Copy original grid (decode of the base tower = copy-existing-tower start), Blank grid (base ledge ring row 1 + ledge + exit door), Time +-50, Name..., back. Warnings: ground enemy without ledge below, vertical eye without terrain above AND below.
Why a flat map (not the game's renderer): the renderer needs the play state (scroll, sprites, raster palette chain); the flat view is 8 px tiles from one routine and cannot desync the game; the real renderer is used by Playtest on the same grid.
Playtest: working grid -> TREC record (`rsLvl = $7fff`), game started through the title exit; hooks take time/name/palette/base tower from it; frog start is **fixed** per game (x=4, y=8 = row 2 on ledge row 1, not data [obs: all towers]) so every level needs a ledge at row 1 near column 0-1 (blank template has the full ring). T/E trainers work in playtest [obs: E used in e33/e41]; editor keys (F10 + joystick) do not collide.

## 7. Game facts established for the editor
- Enemies [obs, sheets `enemy_sheet2.png`]: `$10` stone ball (kind 2, rolls along a ledge, turns/drops at ends); `$20` red ball (kind 1, hops, falls off ledge ends); `$30` red ball that waits (kind 1 speed 0, charges when the player is on its row within 32 angles); `$40/$50` blue-eye disc VERTICAL (kind 8, speed 1/2); `$60/$70` blue-eye disc HORIZONTAL (kind 9, wraps the tower). All only rebound off terrain/other creatures (no stored range): the start direction is the only data (low nibble bit 0, hook `ed_dir`). Time-waster flyer = separate (pink cross, countdown `$339bc`).
- Shootable terrain [obs `e13.py`, forced shot]: `$82` and `$86` are destroyed by one shot per cell (cell -> 0, `$33918++`, not restored within 5 s); `$80 $81 $85 $89` are unaffected. A 2-cell block needs two shots.
- Cells [obs `cell_sheet2.png`]: `$80` grey stones, `$81` ledge, `$82` blue grate (shootable), `$83` door opening, `$85/$89/$8d` pale slab (solid), `$91/$a1/$b1` ledge variants (not in the menu), `$87/$c3` door (c3 = exit), `$08/$0c` invisible markers. Renderer reads the grid every frame [obs].
- Joystick tables: `$338f2` dx (+1 right), `$338f4` dy (+1 up); fire flag `$338f0`.

## 8. Risks / limits
F9 inside the editor or after custom levels is untested (store lost, magic check keeps the game safe); the excursion masks keyboard/VBL for ~0.5-1 s; HDDRIVER/BDOS state is swapped back and forth (the TOS copy is updated in place, consistent with the disk); real hardware timing unproven; 2-player mode not considered in `ed_next`; editor palette uses STE colours (nibble bit 3 = LSB: `$8xx` is dark, use `$6xx`).

## 9. USER GUIDE (self-contained; paste into README.TXT)
```
NEBULUS LEVEL EDITOR AND CAMPAIGNS
==================================
HOW TO OPEN IT: wait for the game's own title (START.TOS -> hardware-detect text screen ~25 s or any key -> box-art picture ~15 s, SPACE skips -> the title about 40 s after START.TOS: NEBULUS logo with a text page that changes by itself every 5 s: credits with the frog on a plinth, High Scorers, Options).  F9/F10 do nothing before that (the game's keyboard code is not running yet).  On ANY of the three title pages tap F10, or press D (a plain letter key, for emulators/desktops that take F10; hold it ~0.1 s: F10 is tap-proof, D is read like every other game key, once per title loop = 3 frames).  A normal tap is enough, no need to hold.  The Options page lists it on its second line ("F10/D  Level editor").  F9 is PP's Gamex exit-to-desktop key: avoid it; after F9 restart the game fresh (the editor and custom levels are switched off until then).
You get the manager (joystick: up/down moves, FIRE selects, LEFT = "< back", F10 = leave):

   Original game   leave the manager and play normally (nothing is changed)
   Campaigns >     list of campaigns; pick one: Play / Edit entries / Rename / Delete; "<new campaign>" makes a new one
   Levels >        list of your levels; pick one: Play / Edit / Copy / Delete; "<new level>" opens the editor on an empty tower
   Save to disk    writes everything (levels and campaigns) into the file NEBLEVEL.OVL on the game disk

CAMPAIGNS: a campaign is a named list of up to 16 entries, played in order; an entry is an ORIGINAL tower (mission + tower) or one of YOUR
levels, so you can mix them ("my remix: original tower 1, my level 3, original tower 8").  "Edit entries": pick an entry for
Change source (cycles through your levels and the 16 original towers) / Insert after / Remove / Move up / Move down; "<add entry>" appends one.
When the last entry is finished the normal victory screen follows.  Lives and score carry over like in a normal game.

THE EDITOR (a new level starts as an empty tower with a safe ledge ring on row 1 and a ledge + exit door at the top):
   joystick       move the box (the tower is a ring: left of the left column is the right column)
   FIRE           open the menu:
       Empty / Ledge / Pillar / Blue block (shoot it once per cell to remove it) / Pale block (solid) / Door opening (3 cells) / Exit door (3 cells)
       Enemy >     Stone ball (rolls along a ledge), Red ball (bounces), Red ball (waits for you), Eye up/down (slow/fast), Eye left/right (slow/fast);
                   then choose the start direction (right/left or up/down).  Enemies only turn round at walls/ledge ends/other enemies.
       Tower >     Look: next tower / other mission (palette, backdrop, default time), Copy original grid (start from a shipped tower),
                   Blank grid, Time +50 / -50 seconds, Name... (up/down = letter, left/right = move, FIRE = done)
       Playtest    run the real game on what you are editing; F10 or finishing the level (or losing) brings you back to the editor, the level is intact
       Save to disk, Leave editor (keeps the level in the level list)
   F10            leave the editor (the level is kept)
   Screen: 16 columns x rows, 16x8 pixel tiles (top = higher), a frog marks where Pogo starts (column 0, row 2: keep a ledge on row 1 near column 0-1),
   right panel = tower/mission, rows, column, row, cell value; bottom line = cell name and hints/warnings
   ("No ledge below!" for a ground enemy, "Eye needs terrain" for a vertical eye with nothing above and below).
   Tile colours: green ledge, grey pillar, blue shootable block, cream solid block, red outline door, red filled exit, round enemies with an arrow
   (right/left or up/down) showing the start direction.

RULES AND LIMITS: levels have 16..120 rows (the blank tower has 48; the shipped ones 47..96); at most 127 levels and 8 campaigns of 16 entries; all of it must fit
in 8192 bytes (about 20 normal levels; the editor says "Overlay full!" if not).  Names have up to 11 letters/digits.
In a playtest the trainer keys T (timer freeze) and E (enemies off) work as usual.  Do not use F9 (Gamex save state) while editing.

THE FILE: NEBLEVEL.OVL (8192 bytes, big endian, starts with NCMP + version 1) lives next to the game files; the game only ever reads it at boot and
the editor only overwrites it in place (it never grows or changes the disk structure).  To share levels give someone that file; to start fresh use an
all-zero file of 8192 bytes.  A damaged/foreign file is ignored (the original game then runs as usual).  Format: see work/notes/editor.md section 3;
PC tool: python3 work/editor/ovl.py validate|dump|render|import-original.
```

## 10. Round 2: gates, hardening, polish (supersedes the "not exercised" remarks in sections 1, 6, 8)
**Header/format check (against the ACTUAL saved file `/tmp/e80.ovl`, section 3.3)**: starts `4e434d50` = `NCMP`; version word `0001` at offset 4 (existed from the start; the loader now REJECTS any other version: magic cleared = treated as absent); no addresses/pointers anywhere (campaign entries = tower codes/level indices, level header = small ints + BCD time + name, body = grid bytes); everything big endian; all lengths/counts validated against the 8192-byte size by `ov_check` in the ST and `ovl.py validate` on the PC (same rules). Nothing in the file had to change.
**Loader hardening** (`ov_check`, run once before the first use of the store, cached in `RS+rsOk`): version, nlevels <= 127, ncamps <= 8, campaign counts <= 16, per level mission 1|2, tower <= 7, 16 <= rows <= 120, len >= 2*rows, record inside the store, popcount(mask) == stream length. Any failure clears the magic (= absent file; the first Save re-initialises it). Entries pointing at missing levels fall back to the stock decode; hooks also re-check the magic on every use.
**Fuzz** [obs `e90.py`/`e91.py`, 22 files restored over `$BC000` in a title snapshot with the hooks, then F10 -> Levels -> Edit (if the file has a level) -> Campaigns -> Play]: 5 random files, magic+random, 6 byte-flip files (1-12 flips in the first 700 bytes), truncated, version 2, nlev 127, ncamp 200, rows 0, rows 255, len 65535, campaign count 255, bad entries `7f 90 05`, valid. Result: **0 crashes** (no Address/Illegal errors in any Hatari log, VBL running); every file `ovl.py validate` rejects had its magic cleared by the game (file/loader rule parity), the 6 accepted ones (flips inside cells/name/time/entries, bad entries, valid) edited and played normally.
**Operations** [obs `e80.py`, menu-driven, STE; stored RAM image parsed with `ovl.py` after every step]: new campaign + 2 add-entry (`80 80`); change source x2 (`82 80`); insert after (`82 80 80`); move down (`80 82 80`); cycle to `86`; remove; rename (`NEW CAMP` -> `ODW CAMP`); delete campaign; copy level (identical grid); edit copy + rename via Tower > Name + Leave editor (commit); delete level 0 -> campaign TEST REMIX lost its custom entry (`80 00 82` -> `80 82`) and the copy became level 0; Save; the saved file validates and dumps correctly. (Move up exercised only on equal entries; the code is the mirror of move down.)
**Full campaign with real input, Mega STE 4 MB / TOS 2.06** [obs `e100.py campaign megaste`]: F10 -> Campaigns -> TEST REMIX -> Play (real keys), forced door entries: entry 1 orig T1, `rsPos 1 rsLvl 1 tower 3` with the 4 custom cells, `rsPos 2 rsLvl 0 tower 2`, then `rsCamp 0, $3390c = 8` (victory). **Playtest on Mega STE** [obs `e100.py playtest megaste`]: Levels -> Edit -> Playtest -> E -> forced completion -> back in the editor (`rsTest 0 rsEd 1`), grid cells intact. Save on Mega STE: file bytes changed, "Saved to disk", game alive, keys work [obs `e51.py`].
**"SAVE FAILED" seen earlier = a bug of mine**: `swap_tos` clobbers d7 which held the write result, so a successful write printed SAVE FAILED (the file was correct). Fixed (result saved on the stack). Real failure path [obs `e120.py A`, game disk WITHOUT NEBLEVEL.OVL]: Fopen returns -33 (file not found), message "SAVE FAILED", no crash, keys and VBL fine afterwards (shot `e120_savefail.png`); the build tool always ships the file so this only happens if the user deletes it (or a read-only medium: same path).
**F9**: F9 inside the editor works through Gamex (GEM desktop reached, `e120_f9.png`); the Gamex restore (GXUT270 "PLAY GAME IN RAM") was NOT run (desktop interaction). Simulated F9 effect (what the restore does to `$BC000..`): store overwritten with garbage while a campaign runs [obs `e120.py B`]: completion falls back to the victory flow, rsCamp cleared, 0 error lines, game alive.
**Default-on equivalence** [obs `e97.py` = NebInput2's scripted2/cmp_sc with the 10 live commands (3 blocks + 7 sites) applied atomically at the first loop-top poll, same input script keyed on the timer words; baseline `e96.py`: stock vs stock = 0 differences]: all 7 hooks installed, NEBLEVEL.OVL absent: 1121 loops compared, non-player block differences 0, player-variable differences 0, creature/timer/energy simulation differences 0 of 1119, framebuffer (event 1) 0 differing bytes. Cost per loop (analytic, 8 MHz 68000): only `ed_game` runs every loop = `cmpi.b #$44,$38498.l` 20 + `bne` 10 + `jmp $3868a.l` 12 = **+42 cycles/loop (0.03 % of a 131,448-cycle VBL budget)**; `ed_title` per title poll ~60 cycles, `ed_dir` per spawn ~30, `ed_dec/ed_time/ed_name/ed_next` once per level (3-40 cycles when no custom level is active). The pacer hides it; frame counts were identical (1121 loops both). => `ed_overlay` can be `default: yes` (the patch only adds code to unused RAM and these hooks).
**UI polish done**: map 16 columns x 16x8 px tiles (256 px wide, 22 rows, scrolls with the cursor), recognisable tiles (ledge green line, pillar, blue shootable block with frame, cream solid block, door outline, exit with cross, round enemies with an arrow for the start direction, frog marker at column 0 row 2), right panel (tower/mission, rows, column, row, value), bottom line (cell name + hints/messages), menus/lists use the whole screen (`guide_*.png`: `guide_7_editor_custom_level`, `guide_10_editor_copy_of_tower1` shows a copied shipped tower). Not done: ring preview. New-level start = empty tower with a ledge ring on row 1 (safe frog start) + ledge/exit at the top; **Tower > Copy original grid decodes the base tower (mission/tower of "Look") with the game's own decoder into the working grid** [obs `guide_10`: rows 66, shipped tower layout]; Look first, then Copy, to choose which tower.
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
