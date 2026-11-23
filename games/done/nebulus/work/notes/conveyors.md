# Nebulus v1.2 round 6: room in the editor, and the conveyor ledges (NebConveyor)

Tags: **[obs]** observed in Hatari 2.6.1 (raw lines in `logs/`), **[disasm]** read from `work/train/dis_33000_40000.txt`, **[INFERENCE]** not proven.
Built and gated in a COPY (`/tmp/nlcv`, RAM disk) on top of the gate2 merge (`work/looks/gate2/merge/` = deliver2 + deliver3 over HEAD 112a411); the real tree is
untouched except this directory.  `PATCH.diff` is against the gate2-merged tree.  Scripts carry `/tmp/nlcv/...` scratch paths.

## 0. Result
* **Room**: a size pass over the editor-only code of `patches/ed_editor.s` freed **346 B** (section 2).  Same seven blocks at the same addresses, no new RAM, no
  change to `nepatch.py`, `nefloppy.py`, the loader, the hook sites, the game-side hooks or the file format.  With the conveyors in (94 B) the editor is **9152 B
  (was 9404), 278 B free (was 26; `gen_ed.py` printed 32 because its CODE2 limit was 6 B past the credit blob's real start, corrected: section 5)**.
* **Conveyors**: cell menu items **Conveyor left  N** (`$a1`) and **Conveyor right  M** (`$b1`) after *Crumble ledge*, keys **N** / **M**, Return/Space repeat them;
  the editor draws a ledge with an arrow above it (tiles 19 / 20) and names them on the status line; the game draws them as plain ledges (unchanged, section 4).
* The pre-existing behaviour of the editor was compared screen for screen with the build before the size pass (section 6, `e208_ab.py`).

## 1. Where can room come from?  The three routes, with evidence
The editor's budget is not disk space: the HD build loads `NEPATCH.BIN` (34 KB of 48 KB allowed) and the floppy build one game file, both at boot.  The limit is
**resident RAM that survives everything the game and Gamex do**: the dead zone inside game RAM `$75728..$77ec0` (`boot.md` 4: the only memory a Gamex F9 saves and
restores is game RAM `$8..$7fdc8`; `$80008..$ffdc8` is F9's swap area and is overwritten, not restored).

### 1a. Size pass over `ed_editor.s` (CHOSEN)
The source had been compacted mechanically twice (short branches, `RSV(a5)` addressing) but never read for dead or duplicated code.  Reading it gave 346 B without
touching one game-side hook or the disk excursion (list in section 2).  Risk = editor-only regressions, which a screen-RAM A/B against the previous build can show
(section 6).  Nothing about memory, loaders or machines changes, so the 1 MB / MiSTer junk-RAM / F9 / floppy / 512 KB behaviour is the previous build's by construction.

### 1b. A block in new, non-game RAM loaded by the same loader (NOT done; design note for the day > ~280 B more are needed)
What is free at run time [obs: `work/dumps/boot/ram_stage2_1mb.bin`, `ram_tower.bin`, `ram_entry.bin`; `boot.md` 4]:
| range | 1 MB | state | editor use today |
|---|---|---|---|
| `$75728..$7573f` | game RAM | dead relocation-table bytes (21 non-zero), never read after the game relocated itself | **free: 24 B in front of CODE1** (inside `BLK_LO..BLK_HI`; the floppy zone starts at `$75720`) |
| `$77ec5..$77fff` | game RAM | HD: 112..116 non-zero bytes at stage 2 and in the tower (START/TOS residue `00e0b4ba 00e0b612 ...`), so not provably dead; floppy: stub `$77ec0` + `ni_ikbd` `$77f00..$77f59`, zero up to `$78000` | not usable on HD without a study |
| `$a0000..$a9af7` | above game RAM | raw NEBEXE.FIC residue at boot; `ES $A0000` (screen), `MB $A8000`, `ETILE $A8800`, `EPAL $A8980` | scratch, rebuilt at every editor entry |
| `$a9af8..$affff` | above | zero | `BUF $AA000` 8 KB, excursion stack below `$AD000` |
| `$b0000..$bbfff` | above | the payload `NEPATCH.BIN` (34118 B now: core, site table `$B0100`, block table `$B6000..` = a second copy of every editor block) | resident after boot, never read again |
| `$bc000..$bdfff`, `$be000..` | above | campaign store (zeroed, then `NEBLEVEL.OVL`), `TREC` | store / playtest record |
| `$c0108..$dba48` (1 MB) / `$102008..` (4 MB) | above | Gamex TOS-state copy (HD); floppy: the stub's own TOS copy at `$C0108..$CA997` | used by the disk excursion |
* **HD**: a block could run in place from the payload (`$B8600..$BBFFF` is free: ~14 KB) or be copied to `$AD000..$AFFFF`; `nepatch.py` needs a new directive (blocks are
  limited to `$75728..$77ec0` today) and `plan_install` its overlap checks.  It is written unconditionally at every boot, so MiSTer junk RAM is not an issue.
  **But everything from `$80008` up is overwritten by a Gamex F9 and not restored**, while the game-RAM part of the editor survives (and is in a GXUT270 state file):
  after F9 + "play game in RAM" the next F10 would jump into garbage.  The store has the same exposure and is protected by its magic; a code block needs the same
  kind of guard at the single entry `ed_run` (~16 B) and a "no editor" way out.  The F9 restore itself has never been run in a gate (`editor.md` 10: only simulated).
* **Floppy**: there is no loader of ours.  The cracker's loader reads ONE file (`TOPPLER.JMP`) to `$33b00` by its directory size and jumps; the file now ends at
  `$78100` (already 256 B into the screen buffer).  A high block would have to be carried inside that file (so it still costs zone or screen-buffer bytes at load)
  and be copied up by the `$77ec0` stub, which also has to skip it on a 512 KB machine (the stub already takes the editor out there) and stay clear of its own TOS
  copy at `$C0108`; `nefloppy.py` (segment list, `gen_editor`, `stub_bytes`, FAT cluster count) and the whole floppy matrix (`fgate`, `f161`, `fge`, 4 machine cells)
  would change.
* Verdict: feasible on both builds, but it adds a new failure mode (F9) and touches both loaders, for room the size pass gave for free.  If it is ever needed, move
  the parts that are only used from the list screens (campaign entry editor `cp_edit`/`a_eop` ~500 B, `lv_copy`/`lv_delete`/`commit` ~500 B) rather than hooks.

### 1c. Loading from disk on demand (an overlay fetched when F10 or a sub-menu opens): NOT recommended
* **No run-time disk path exists except the editor's own TOS excursion.**  Plain GEMDOS/BIOS from inside the game crashes: the game's workspace `$8700..$33a4f` is
  TOS's and the hard-disk driver's memory (`editor.md` 2: bus error in BDOS).  `disk_op` (CODE4 + `tos_file`/`tos_io`, ~500 B) swaps `$8..` with the TOS-state copy,
  restores TOS's MFP state, runs `Getbpb(A)` / `Fopen` / `Fread` and swaps back.  The floppy build has **no FDC code of its own** either: it uses the same excursion
  with a TOS copy its boot stub takes (`ed_floppy_capture.s`, `floppy.md` 9/10).
* That path is hard-wired to drive A:, the name `A:\NEBLEVEL.OVL`, 8192 B and `BUF`.  An overlay loader needs a second name/drive, buffer and length (parametrised
  `tos_io`), a "loaded" flag and an error path: **~60-80 B more resident code** before one byte is saved, plus the guard of 1b (the overlay lives above `$80000` too).
* Cost at run time [obs, `editor.md` 13.3 / `floppy.md` 10]: the screen and keyboard are frozen for the excursion: 0.5-1 s on the hard disk, **4.3-7.2 s on a floppy**
  (Hatari FDC timing), at every F10 (or once, with yet more state).  On the floppy build the **game disk** would have to be in drive A: at that moment; once the user
  has swapped in his campaign disk the editor would have to ask for the game disk back.  The game must also keep working with no overlay file at all.
* The HD build could not use the game partition without the HDDRIVER state swap on every open (today only an explicit Load/Save does it).
* Verdict: more resident bytes than it frees for small features, a visible freeze, a disk-swap prompt on floppy.  Loading at boot (1b) dominates it in every respect.

### 1d. Reserves left after this round (no design change needed)
278 B free now (table in section 5), + 24 B if CODE1 starts at `$75728`.  Size-pass candidates not taken (est.): the four 12-byte name copies (`lv_edit`, `c_newlvl`,
`commit`, `c_newcamp`) as one routine ~12 B; the `lvl_ptr` + `beq a_done` prologue of five routines ~10 B; `a_lop`/`a_cop` as offset tables ~12 B; the two byte-move
loops of `commit` and the ones of `lv_delete`/`cp_delete` ~20 B; `draw_name`'s four `txt` calls ~8 B; `'Save to campaign disk'` is stored twice (22 B) and `'< back'`
eight times (56 B): a menu item that points at a shared text would free ~60 B for ~20 B of code.  The game-side hooks (`ed_next`, `ed_game`, `ed_title`: ~40
absolute `RS+x.l` accesses) were deliberately left alone: they run inside the game and are covered by the equivalence gates of earlier rounds only.

## 2. The size pass (346 B; editor-only code, every item checked against the old build in section 6)
Sizes are label-to-label bytes of the vasm listings of the two sources (`gen_ed.py` assembly: branches unsized, vasm picks the short form).  The total is exact (9404 - 9152 + the 94 B of the
conveyors); the split per row is my reading of the diff and approximate where a row groups several routines; the exact per-label deltas are in
`logs/size_by_label.txt` (raw listing differences, old -> new; moved data labels show up there too).
| what | where | bytes | why it is the same program |
|---|---|---|---|
| `vDirty` (V+162) was written in 8 places and **never read** | `ed_run`, `place`, `lv_edit`, `c_bt`, `c_ldone`, `name_done`, `a_lift`, `lift_set` | -46 | no reader in the source (grep); V is zeroed at every editor entry |
| dead instructions | `cp_edit .l` (a load, four register moves, a push/pop of a value nobody reads, a second load of the entry byte) | -20 | d1 is overwritten before its next read on both paths; d0 is still the entry byte |
| | `name_done` (`move.w vCur,d0` / `tst.l vNDst` in front of `bra m_camps`) | -8 | `m_camps` reads neither d0 nor the flags |
| `move.w #3,vRedraw` after `menu_open` | `m_main`, `ml` (levels / campaigns list), `cp_edit` | -18 | `redraw` only tests bit 0 in the MAP view; these three set `vScr = 0`, where every redraw clears the screen and draws the menu |
| one routine `mb_back` ("< back" item + show the list) for three copies | `ml`, `cp_edit`, `pk` | -34 (+18) | same calls in the same order |
| one routine `nth` (string number n of a list) for three walkers; the 19-word `names` offset table is gone (string number = tile id) | `draw_panel`, `pk` (enemy names), `c_dgo` (result messages) | -50 (+12) | the same strings in tile order; `n16` stays the empty name of the frog marker |
| shared tails `rd2` / `rd2b` (`vRedraw = 2`), `rd3` / `ed_map` (map view, full redraw), `msg2` (status message) | `menu_open`, `no_room`, `a_done`, `c_nav`, `c_ldone` = `c_edroot`, `name_begin`, `move_name`, `name_done`, `lift_set`, `lift_cancel` | -74 (+36) | identical instruction sequences, now reached by a branch |
| `a_enemy` (no-direction case) falls into `a_edir`, `a_ekey` joins at `pe` | CODE1 / CODE2 | -30 (+8) | `vKind | 0` is the same marker; `rec` + `place_enemy` + `a_done` were three copies |
| `kb_key`: Return/Space are tested once (then `vLift` decides), the table walk uses a0 | CODE2 | -14 | same key -> action map; with a lift pick pending only Return/Space act, as before |
| `draw_cell`/`draw_cellf` take the column/line straight from `draw_map`'s counters | CODE1 | -16 | `classify` does not touch d5-d7 |
| plane masks by `lsr.b #1 / scs` instead of `moveq / btst / sne` | `draw_id` | -6 | same three masks |
| `draw_cursor`: one mask register instead of two `eori #imm` triples | CODE1 | -12 | same XOR pattern (full top and bottom line, edge pixels between) |
| `a_sub`, `c_blank` (constants in a register, one base address), `fire_edge` (falls into `menu_open`), `input`, `move_map`, `c_rename` (falls into `name_begin`), `a_set`/`a_tri` (short branches) | | -40 | |
| `ov_check`: the `.bad` exit sits in the middle of the routine so every reject branch is short | CODE2 | -10 | no instruction changed; 12 reject cases re-tested (section 6) |
Moved, not changed: the three list-screen menus `m_lvl`, `m_camp`, `m_ent` (162 B) went from DATA to the tail of CODE1 (that is where the room was; DATA needed it
for the tiles, names, keys and menu items of the conveyors).  **Not touched**: every hook that runs in the game (`ed_lvl`, `ed_dec`, `ed_dir`, `ed_time`, `ed_name`,
`ed_next`, `apply_entry`, `ed_game`, `ed_title`, `ed_vbl`, `ed_key`, `ed_opt`), `ed_run`'s enter/leave sequence, `commit`, the store helpers, the picker's
`a_pick`/`set_theme`/`preview`, `place` (door pairing; only the dead `vDirty` store left it), the whole disk excursion (`disk_op`, `tos_file`, `tos_io`, `swap_tos`,
`mfp_*`, `load_fin`), RS and V layout (V+162 is now unused), all strings.  Binary check of the game-side part: the 808 bytes `$75740..$75a67` (store helpers, all
game hooks, `ed_vbl`; everything in front of `ed_run`) differ from the previous build in exactly three `bsr.w` displacement words, `lvl_ptr` and `camp_ptr` -> `ov_ok`
and `ed_time` -> `rdtime` (those two routines moved inside CODE2): `$75742 202c -> 1ffe`, `$7578c 1fe2 -> 1fb4`, `$75882 1fd6 -> 1f9e`.  The 15 sites of `ed_overlay.nep`: 13 are byte-identical to the previous build (everything in front of `ed_run` `$75a68` kept its address: `ed_dec $75810`,
`ed_lvl $757ce`, `ed_title $759c6`, ...); the two that jump into CODE2 moved with it (`$3851a -> ed_key $7782c`, was `$77864`; `$3d662 -> ed_opt $77864`, was `$7789c`).

## 3. The conveyor ledges
**Game** [disasm `sub_03ab84` `$3ab84`, caller `sub_039c78` `$39c78`]: the cell under the frog (bit 7 set, `(v & 3) == 1`): `(v & $30) == $20` -> d0 = -1, `== $30` -> d0 = +1,
carry set; the caller then tests the joystick dx word `$338f2` and only when it is 0 moves the frog by d0 (`sub_039bee`).  So `$a1` carries a frog that is not
steering to the LEFT, `$b1` to the RIGHT, one pixel per game loop, until the cell under it is no longer a conveyor; with the stick held the frog walks normally in
either direction.  The cell is not consumed.  (`sub_03ab50`: `(v & $30) == $10` = crumble, the cell is cleared.)
**Editor** (94 B): `m_root` has 15 items, `0,$a1,'Conveyor left  N'` and `0,$b1,'Conveyor right  M'` after *Crumble ledge* (action 0 = `a_set`, the plain cell
writer, so the common `place` rules apply: over a door cell the partner door is cleared) (+39 B); `kbtab` + `$31` (N) / `$32` (M) (+6 B); tiles 19 / 20 =
`$10,$30,$7e,$30,$10,$ff,$ff,$00` / `$08,$0c,$7e,$0c,$08,$ff,$ff,$00`, colour 2 = the ledge bar with a 5-row arrow above it (+18 B, `tiles_init` expands 21 tiles;
`ETILE` grows to 336 B, below `EPAL $A8980`); names `Conveyor left` / `Conveyor right` (+29 B); `classify` picks the ledge-family tile from an 8-byte table by
bits 4-6 (`2,3,19,20,2,2,2,2`: `$81` ledge, `$91` crumble, `$a1`, `$b1`; `$c1..$f1` stay plain ledges as before) (+2 B).  Return/Space repeat a conveyor like any
other cell (`rsLast`).  No format change (version 1); old files with `$a1`/`$b1` cells now show the arrows.
Keys: N and M are neighbours on the bottom row (N left of M) on US, UK and German ST keyboards; they were unmapped before (`e150.py` pressed them as "no shortcut"
keys: its list lost them, section 6).

## 4. In the game a conveyor still looks like a ledge; arrows there are not a cheap hook
[obs] start pictures of the same ring with and without `$a1`/`$b1` cells in view are pixel-identical (section 6).  [disasm] The renderer never sees the cell code:
`$38028` builds a 256-byte class table at `$315e0` from `v & 3` and `v & $c` only (ledge 0, lift slab 20, pillar 10, blue block 30, door 40), and the per-column
draw (`$37ba4`/`$37c06`) picks pre-shifted art by class and by the column's angle (tables built at `$38084`).  An arrow needs its own art for every angle and a
blit inside that loop: far more than 40 B, in the game's inner loop.  The only < 40 B trick would be to give `$a1`/`$b1` another existing class in the table (two
byte pokes): they would then be drawn as lift slabs, which says "press Up here" to the player.  Not done.

## 5. Budget (`gen_ed.py`)
| block | limit | before (gate2 merge) | after | free after |
|---|---|---|---|---|
| CODE1 `$75740` | `$76c00` | 5312 | 5276 | 36 |
| DATA `$76d40` | `$7726c` | 1324 | 1216 | 108 |
| CODE2 `$77300` | `$779fa` (the credit blob, `cr_credit.nep` / `nebrelease.CREDIT_ADDR`, on both builds; `gen_ed.py` said `$77a00`: its `LIM` and overlap check are corrected) | 1776 (10 free, not 16) | 1696 | 90 |
| CODE3 `$77a40` | RS `$77c80` | 570 | 542 | 34 |
| CODE4 `$77dc0` | `$77ec0` | 252 | 252 | 4 |
| CODE5 `$76c76` | `$76d00` | 136 | 136 | 2 |
| CODE6 `$772da` | `$77300` | 34 | 34 | 4 |
| total | | 9404 (26 free) | **9152** | **278** |
Start addresses, RS, V, the marker word and the other blobs (trainers, latch, `ni_ikbd`, credit) are where they were.  On the floppy build the TOS-state capture
(110 B) follows DATA, so it now sits at `$77200..$7726d` (was `$7726c..`); it must end before CODE6 `$772da`, which `nefloppy.gen_editor` asserts: DATA may grow
back to its old limit and no further.  `NEPATCH.BIN` 34118 B (was 34370).

## 6. Gates (raw logs `logs/`, shots `shots/`)
Build under test: `/tmp/nlcv/x/b_new` = gate2 merge + this change: `NEPATCH.BIN` 34118 B md5 `f471dd18e595932c00fdb0222eb6cc77`, `START.TOS` md5 `4ecf26d8b38049738a4b1b7448276e10`
(unchanged), `patches/ed_editor.s` md5 see `logs/c0_md5s.txt`, floppy game disk `/tmp/nlcv/x/fl_game.st` 419840 B md5 `7a3b6341c59a3d53ae7506596347e35f`.
**Fresh snapshots per build and per machine** (`/tmp/nlcv/x/title_{ste,megaste,st}_new.sav`, made by the gates from `b_new` after the last rebuild; every snapshot cell
first asserts that the snapshot AND `NEPATCH.BIN` contain `Conveyor left  N`, `Conveyor right  M`, `Door + opposite`, `Crumble ledge` and the 18 bytes of the two conveyor
tiles `10307e3010ffff0002 080c7e0c08ffff0002` (`e208.py` SIGS; `SNAP_EXPECT` for `e180.py`); the old-build side of the A/B gate uses its own fresh snapshot of
`/tmp/nlcv/x/b_old` (= gate2's `b_new`, md5 `e1c304dc...`) and asserts it does NOT contain `Conveyor left`).  One Hatari at a time (`/tmp/nlcv/x/master.sh`).

### 6.1 Static
* `python3 tools/nepatch.py verify` (`logs/c0_verify.txt`): `33 verified sites, 3 clear ranges (332 B), 11 blocks; ZONE_STRICT=False`, 33 x `dump-orig OK`, 0 mismatch.
* `python3 tools/nefloppy.py selftest` (`logs/c0_selftest.txt`): 5/5 `yes` (`ed_overlay   unmapped generator == patches/ed_overlay.nep blocks: yes  ($75740+5276, $76c76+136, $76d40+1216, $772da+34, $77300+1696, $77a40+542, $77dc0+252)`).
* `python3 tools/nefloppy.py build` (`logs/c0_floppy_build.txt`): writes the 419840 B game disk; the capture block is at `$77200` (110 B).
* `python3 work/editor/gen_ed.py` (`logs/c0_budget.txt`): the table of section 5.

### 6.2 `e208.py`: the conveyor gate [obs]
Per machine (title snapshot of this build; the look part plays two stored levels, the rest is one editor session with real keys):
0. stored levels PLAIN (ledge ring) and CONVLOOK (the same ring with `$b1` at columns 1-3 and `$a1` at 13-15, all in view), played from Levels > Play: the start
   screenshot crops (sky, skyline, tower, ring, frog; HUD excluded) are **pixel-equal** (`diff bbox None`): the game draws a conveyor exactly like a ledge.
1. cell menu = 15 items, `Conveyor left  N` (0,`$a1`) / `Conveyor right  M` (0,`$b1`) after `Crumble ledge`, the 13 old items unchanged and in order, `Leave editor`
   last (Left = last item still leaves); the menu items write `$a1` / `$b1`; keys N / M write them, Return and Space repeat, C and Delete clear; a conveyor over a
   door cell clears the partner door cell (`[83 a1 00]` / `[83 00 b1]` in columns 3 / 11).
2. editor screen RAM (ES `$A0000`): the 16x8 cell pictures of `$a1`, `$b1`, `$91`, `$81`, `$80` == tiles 19, 20, 3, 2, 4 of `ed_editor.s` (bit for bit, 3 planes), the
   four ledge kinds are four different pictures; plane-1 rows of the arrows:
   `$a1: 0000001100000000 0000111100000000 0011111111111100 0000111100000000 0000001100000000`, `$b1: 0000000011000000 0000000011110000 0011111111111100 0000000011110000 0000000011000000`.
   Status line under the cursor: the glyph cells of the name == the glyph cells of the menu item's own text, then a blank, for `Conveyor left`, `Conveyor right`,
   `Crumble ledge`, `Ledge`, `Pillar` (so the name list in tile order is right for the new and the old tiles; all other names: 6.3).
3. Level > Time +50 (0450 -> 0500); Leave editor: the store validates (`ovl.validate`), the stored record holds the time and every conveyor cell, stored grid ==
   editor grid; with `rsOk` cleared the game's own validator runs again and keeps the magic; Copy = same grid (n+1 levels), Delete removes it, Edit loads the cells back.
4. playtest of that level (row 1: `$b1` at columns 1-5, `$91` at 7-8, `$a1` at 10-14; E trainer on), with a Hatari change-watch on the frog x word `$33a16` that logs
   every change together with the joystick dx word `$338f2`:
   * at the start (column 0, plain ledge): x 4, **no change in 1.5 s**;
   * Right held until the frog is on the first `$b1` cell, then released: STE log `... (26, 1), (27, 1), (28, 0), (29, 0), ... (47, 0), (48, 0)`: **21 changes with
     dx = 0, every one +1**, up to x 48 = the first pixel of column 6 (plain ledge), then it stands (state 0);
   * Left held (a normal walk, every change -1, over the `$b1` cells and round the tower) until column 14, then released: **24 changes with dx = 0, every one -1**
     (x 103 -> 79 = the last pixel of column 9), then it stands;
   * the conveyor cells are still in the grid afterwards; walking on to the left, the `$91` cell (8,1) is cleared under the frog and it falls (`{'x': 67, 'y': 0, 'st': 8}`).
   No Address/Bus Error/exception line in the Hatari log.
   Mega STE (`logs/e208_megaste.log`): 26 changes without input on `$b1` (x 22 -> 48), 23 on `$a1` (102 -> 79); ST (`logs/e208_st.log`): 21 (27 -> 48) and 25
   (104 -> 79); every one +1 / -1, same end points, same crumble result.  46 PASS, 0 FAIL on each of the three machines.
That the checks can fail: the first runs (history): run 1 compared the playtest picture of the test level with the plain new level and failed (the test level has other cells in view: my
script, now two dedicated stored levels); run 2 passed everything except "at least 16 changes without input" (the Right key was released late because the RAM
sample lags: only 9 free changes were left; the conveyor now starts at column 1 and the threshold is 8, the log line gives the real count).

### 6.3 `e208_ab.py`: the editor before and after the size pass, screen for screen [obs]
The same key session is run on `b_old` (gate2 merge, fresh snapshot, asserted to have no `Conveyor left`) and on `b_new`; at every checkpoint ES (32000 B), EPAL
(32 B), the grid (4096 B), the store (8192 B), RS (52 B), the menu items / selection / scroll, the mode words and the message text are saved and compared.  Covered:
manager main menu; empty and filled level / campaign lists; new level; every tile by its key (panel name and value under the cursor for ledge, pillar, blue block,
the 7 enemies in both directions, exit, door + opposite, markers, lift start / end / stop, crumble, frog start, empty) and by the menu (Enemy > with both direction
menus, the no-direction case, back); "No ledge below!", "Eye needs terrain", "Door + opposite", "Exit (finish)"; Return/Space repeat; C / Delete; scrolling to the
top and back; unmapped letters; lifts (pick mode, ignored keys, "Pick another row", end above / below, by Return, Space and FIRE, stop, "Pillar blocks lift", F10
cancel, Lift > menu, delete from the slab and from the shaft); Level > (menu, colour list with preview up and down, pick, enemy list, pick, reopen on the current,
Left = back, Time +50/-50, Name entry with edits, back); F10 = leave; level menu, Copy, Edit, Copy tower list scrolled with preview, tower M2 T5 copied, Blank grid,
Leave editor, Delete; campaigns (new, add entry x3, change source, insert, move down / up, remove, cycle to a custom level and past the wrap, rename with edits,
entries again, the entry lost when its level is deleted, second campaign, delete); disk prompt, F10 cancel, save with no disk ("No disk"), save to a campaign
disk ("Saved"), delete in RAM, load ("Loaded 1 levels / 1 campaigns"); a full store (3 x 120 rows): list, Copy refused ("Overlay full!").

**Result** (`logs/ab_cmp.log`, session part 1, 116 checkpoints):
```
checkpoints: 116 / 116
FAIL 115 dense level in the editor es: 3134 bytes differ, first at +0x1e2e; menu: [[0, 0, 'Empty  C'], [0, 129, 'Ledge  L'], [0, 145, 'Crumble ledge'], [0, 128, 'Pillar  P'], [0, 130, 'Blue block (shoot) B'], [2, 3, 'Lift >'], [1, 131, 'Door opening  D'], [1, 195, 'Exit door  X'], [2, 1, 'Enemy >'],
bytes compared per part: {'es': 3712000, 'pal': 3712, 'grid': 475136, 'ovs': 950272, 'rs': 6032}
RESULT: 115 of 116 checkpoints identical, 1 differ
```
The one differing checkpoint of part 1 is the cell menu itself: a mistake in my script (after "Overlay full!" the level menu stays open, so the next pick opened
the editor's cell menu at a checkpoint), and the cell menu has 15 items instead of 13 by design.  Everything else: 115 of 115 identical, byte for byte.  (It also shows the gate
sees a difference when there is one: 3134 screen bytes and the item list.)
Part 2 (`PART=2`, the rest of the session from a fresh start, both builds): the full store again, a 120-row level in the editor (scrolled to the middle and the
top), a cell cleared and the level committed smaller, the campaign's entries, then **the in-game validator**: the good store and 13 broken ones (version 2,
nlevels 200, ncamps 9, campaign count 17, mission 0 / 3, tower 8, rows 15 / 121, len < 2*rows, len 65535, a flipped mask bit, a missing 4th record), each loaded
on the title with `rsOk` = 0 and the manager opened on it; the level list, the store and the magic are compared between the builds and the accept/reject decision
with `ovl.py validate`; then Original game -> the title (`$70 = $382d8`, mission/tower words restored).  (`logs/ab2_*.log` is the first attempt at part 2: its 10
checkpoints up to the first broken store are identical on both builds, then my script failed: it swapped the store under an OPEN manager, where the list code
trusts the count it has just read, so both builds listed garbage names, identically; with nlevels 200 the list overflowed my reader.  Not a real case: the store is
validated when the manager opens and after a disk load, never under an open list.)
**Result** (`logs/ab3_cmp.log`, part 2 with the corrected protocol):
```
checkpoints: 25 / 25
bytes compared per part: {'es': 736004, 'pal': 740, 'grid': 102400, 'ovs': 204800, 'rs': 1300}
RESULT: 25 of 25 checkpoints identical, 0 differ
```
Validator parity, new build (`logs/ab3_new.log`: name, the game keeps the magic, `ovl.py validate` accepts):
```
  validator ('good', True, True)
  validator ('version 2', False, False)
  validator ('nlevels 200', False, False)
  validator ('ncamps 9', False, False)
  validator ('campaign count 17', False, False)
  validator ('mission 3', False, False)
  validator ('mission 0', False, False)
  validator ('tower 8', False, False)
  validator ('rows 15', False, False)
  validator ('rows 121', False, False)
  validator ('len < 2*rows', False, False)
  validator ('len 65535', False, False)
  validator ('mask bit flipped', False, False)
  validator ('nlevels 4 (4th record missing)', False, False)
PARITY ok
title vbl 0x382d8 errors []
```

### 6.4 Regression gates on the build with the conveyors [obs] (`logs/<gate>_<machine>.log`; generated from the logs by `mktable.py`)
| gate | STE 1 MB TOS 1.62 | Mega STE 4 MB TOS 2.06 | ST 1 MB TOS 1.04 |
|---|---|---|---|
| `e208.py (conveyors)` | 46 PASS, 0 FAIL | 46 PASS, 0 FAIL | 46 PASS, 0 FAIL |
| `e200.py (pickers, crumble item, playtest of the pick, store round trip)` | 38 PASS, 0 FAIL | 38 PASS, 0 FAIL | 38 PASS, 0 FAIL |
| `e201.py (crumble in play, conveyor levels from the manager)` | 17 PASS, 0 FAIL | 17 PASS, 0 FAIL | not run |
| `e203.py (door pairs, tunnel, original tower)` | 30 PASS, 0 FAIL | 30 PASS, 0 FAIL | 30 PASS, 0 FAIL |
| `e150.py (shortcut keys, lifts, playtest, T/E)` | 32 PASS, 0 FAIL | 32 PASS, 0 FAIL | 32 PASS, 0 FAIL |
| `e170.py (cold boot: NEPO, site count 33, hooks, F10 / D)` | 12 PASS, 0 FAIL | 12 PASS, 0 FAIL | 12 PASS, 0 FAIL |
| `e180.py --quick (odd records; STE odd2+stress01+stress05, Mega STE odd2+stress05)` | 65 PASS, 0 FAIL | 48 PASS, 0 FAIL | not run |
| `fl_ui.py (floppy game disk cold boot, real FDC)` | 29 PASS, 0 FAIL | not run | not run |
The counts on STE are the same as gate2's runs of the previous build (e200 38, e201 17, e203 30, e150 32, e170 12, e180 --quick 65, fl_ui 29).  Each log ends with
`FAILS []`; every gate also asserts "no Address/Bus Error/exception line in the Hatari log".  `e170.py` and `fl_ui.py` are cold boots (HD image / the floppy game
disk with real FDC timing), the others run on the fresh title snapshots.  The floppy image and `NEPATCH.BIN` that were gated are byte-identical to what the
delivered sources build (`logs/c0_md5s.txt`; rebuilt and `cmp`'d after the last comment-only source edits).
Script changes needed by the feature (in `PATCH.diff`): `e150.py` pressed N and M in its "keys that are not shortcuts" list: removed there (they are shortcuts now,
`e208.py` tests them); `e200.py`'s root-menu check now expects the two conveyor items.  `e201.py` is unchanged (its two conveyor levels show the frog already
carried to the end of the run: `CONVR ... [24, 24, ...]`, `CONVL ... [111, 111, ...]`, as in gate2).
History: the first chain (`master.sh`) was stopped by me after `ab_cmp` to change the order (STE regression first); `e200_ste` had just started and was re-run
from scratch by `master3.sh` (the log is the complete second run).
**Not run**: `e201.py` and `e180.py` on the ST (ST = `e208`, `e200`, `e203`, `e150`, `e170`), `e202.py` (the all-games image), `run_look.py`/`check_look.py` (looks15 / base8 / stock: the look hooks `ed_lvl` and the five retargeted sites are
untouched: section 2), `e180.py` full / `--flags` / `--disk`, `e204`-`e207`, `e98` equivalence, the junk-RAM and IKBD gates (`jrg.py`,
`ikg.py`), `f161` / `fge` floppy disk-swap gates (`fl_ui.py` did one Save and one Load on the floppy build), Mega STE / ST floppy boots, TT / Falcon, 2-player,
real hardware / MiSTer.  [INFERENCE] none of those paths has a changed instruction except through the shared tails listed in section 2.

## 7. dadprg (`~/Code/dadprg`, edited in place, not committed; `dadprg.diff` = this round only, on top of HEAD + deliver3's `dadprg.diff`)
The level map and the thumbnails draw whatever `Hub::Ncmp::Legend` says, so the change is in that one file: `TILES` + tiles 19 / 20 (the editor's two patterns, colour
2), `TILE_KINDS` + `conveyor_left` / `conveyor_right`, `tile_for` takes the ledge-family tile from `LEDGE_TILES` (`$10 => 3, $20 => 19, $30 => 20`, else 2: the
same rule as the editor's `ltile` and `ovl.py classify`), the two labels say that the editor adds the arrow.  `LevelMap.vue` / `types/hub.ts` need nothing (the
glyph rows, colour and label come with the level JSON; `kind` is a free string): the map, the legend list and the game legend (`/api/games/nebulus`, now 21 tiles)
show the arrows.  The parser was already code-agnostic.  Tests: `ncmp_test` (tile ids of `$a1`/`$b1`/`$c1`/`$a5`, kinds, the arrow rows, `TILES.size ==
TILE_KINDS.size`), `hub_browse_test` (legend size 21, kinds and arrow rows of the `crumble.ovl` fixture level).  README "Special ledges" paragraph.
`bin/rails test`: **222 runs, 1575 assertions, 0 failures, 0 errors, 0 skips**; `bin/rubocop` on the three Ruby files: no offenses; `npx vue-tsc --build`: exit 0.

## 8. Files
`PATCH.diff` (against the gate2-merged tree = `git archive HEAD` + `work/looks/gate2/merge/`; applies with `patch -p1` in the game dir, checked by `mkdeliver.sh`)
and the same files mirrored: `patches/ed_editor.s`, `patches/ed_overlay.nep` (regenerated by `gen_ed.py`), `patches/README_HD.TXT`, `patches/README_FLOPPY.TXT`
(what is new, menu, keys, what the editor draws), `work/editor/gen_ed.py` (CODE2 limit = the credit blob's real start `$779fa`; comment lines), `work/editor/ovl.py`
(21 tiles, `classify` 19 / 20), `work/editor/e150.py` (N and M left the "not a shortcut" list), `work/editor/e200.py` (the root-menu check now expects the two
conveyor items), `work/notes/editor.md` (section 17, key table row), new `work/editor/e208.py` (conveyor gate) and `work/editor/e208_ab.py` (A/B gate; `run` /
`cmp`).  `e150.py` / `e200.py` keep gate2's path form; the two new scripts carry `/tmp/nlcv/x` scratch paths.  Not regenerated: `patches/PATCHES*.TXT`, the
release zips, `dist/` (the lead's release step).  `dadprg.diff`, `logs/`, `shots/`.
