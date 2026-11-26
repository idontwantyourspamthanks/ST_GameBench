# Nebulus v1.2 floppy gate (NebGate12Floppy)

Build under test: tree at `cf52f4f` (no commit after it touched `patches/` or `tools/`; `git status patches tools` clean). `nefloppy.py build` -> `Nebulus_game_disk.st` md5 `7a3b6341c59a3d53ae7506596347e35f` (rebuilt later: same md5; campaign disk from `nefloppy.py campaign`). Hatari 2.6.1, TOS 1.62 (STE 1 MB) / 2.06 (Mega STE 4 MB), real FDC (`--fastfdc no`), private HOME, cold boot every cell (no snapshots on the floppy path, so the SNAP_EXPECT guard becomes a content guard, below).
Raw logs: `floppy_logs/`; scripts as run: `floppy_scripts/` (paths rewritten to the private scratch; diffs listed at the end); screenshots: `floppy_shots/`.

## 0. Build / freshness guard
- `nefloppy.py selftest`: 5 lines `unmapped generator == patches/*.nep blocks: yes` (cr_credit, ni_latch, nt_trainers, ed_overlay, ni_ikbd) = 5/5.
- Signature `'Conveyor left  N'` (cf52f4f editor string; also `Crumble`, `Copy tower`, `Door + opposite`): present once in the new `game.st`; **absent** in the v1.1.1 floppy disk from `dist/Nebulus_floppy_v1.1.1.zip` (md5 `46365410...`): guard fails for v1.1.1, passes for the build. Title page of the run shows `v1.2 enhanced by dad_prg` and `F10/D  Level editor` (floppy_shots/opts.png).

## 1. Results (PASS / FAIL counts = raw script lines `PASS ` / `FAIL `)
| cell | STE 8 MHz | STE +`--cpuclock 16` | Mega STE 8 MHz | Mega STE +16 MHz |
|---|---|---|---|---|
| fl_ui (Level > Colours/Enemies lists, live re-theme, playtest look == stock tower, Save to campaign disk, Load, Edit, Play) | 29/0 | 29/0 | 29/0 | 29/0 |
| rt.py (cold boot + editor round trip, see 2) | 26/0 | 26/0 | 26/0 | 26/0 |
| fge (eject/swap, fuzz subset) | 35/**1** (MFP check, see 3) | - | 35/**1** (same) | - |
| fge2 (two campaign disks) | 21/0 | - | 21/0 | - |
| f161_nfe (Load/Save failure modes) | 48/0 (with the 22 fuzz disks) | - | 25/0 (skipfuzz) | - |
| fl_look (15 look cells; `base8` HD dump as reference) | 75/0 (all 15 cells) | - | 30/0 (cells 0,4,9,12,13,14) | - |
| fo180 (odd-record campaign files from the floppy, 15 files, `--quick`) | 358/0 | - | 358/0 | - |
16 MHz = `hatari-option --cpuclock 16` set by the harness after the title (`cpuclock 16 set after the title` in each log); the scripts that support it are fl_ui and rt (a `CPU16=1` hook in `lib.py`). ST (TOS 1.04) not in the assignment, not run. Floppy boot: STE title at 62.6 s.

## 2. Cold boot + editor round trip (rt.py, all four machines identical)
Cold boot -> F10 -> Levels > `<new level>` -> Copy tower > (1st entry: grid replaced, flags 0, tower 0) -> Level > Blank grid (ring back) -> keys M x5 (row 1 cols 1-5 `$b1`), N x5 (cols 10-14 `$a1`), Crumble ledge from the menu (7,1) + Return (8,1) (`$91`), Door D at (3,12) -> partner `$83` at col 11 rows 12-14, Door from the menu at (5,20) -> partner col 13, Exit X at (2,30): `$c3` x3 and **no** partner at col 10, menu Conveyor left/right at (5,6)/(6,6), Colours > 3 (tower byte 2, flags colour nibble 0), Enemies > 2 (flags 2), Time +50, Leave editor: store validates (`ovl.validate` == []), record flags 2 / tower 2 / grid == editor grid. Save to campaign disk ('Saved'), image usable, saved file == RAM store, store zeroed, Load ('Loaded 1 levels / 0 campaigns'), reloaded store == file, Edit: grid/flags/tower equal, Play: running, row 1 in RAM as built. In play (Hatari change-watch on the frog x word): `$b1` carries the frog with no input, +1 per step to x 48 (25 changes), `$a1` carries it left, -1 per step to x 79 (29 changes), conveyor cells not consumed, walking onto the crumble cell clears it (`row 1 [145, 0]`, frog y 0 st 8 = falling). No Address/Bus Error lines in the Hatari logs.

## 3. The one FAIL: fge `MFP block intact at the title (IERB $64 TCDCR $57)`
STE and Mega STE: `(100, 81)  (expected (100, 87))`: the TOS MFP block captured by the floppy stub is `... 00 51 00 50 c0 02 00 88 ...` here, `... 00 57 00 50 c0 64 00 88 ...` in every earlier gate. Control (same private HOME, same script `mfp.py`, STE): the **v1.1.1 floppy disk gives the identical block** (`TCDCR 0x51`, files `mfp_new.txt`, `mfp_old.txt`), so it is not caused by cf52f4f. [INFERENCE] a Hatari/TOS timer-D (RS232 baud) default that differs with the fresh private HOME config from the HOME the earlier gates ran in; not proven. The check is a snapshot of TOS state, and everything that depends on it (all disk swaps/loads/saves in fge, fge2, f161, rt, fl_ui) passes. I report it as a FAIL of the unmodified script, not as a pass.

## 4. Docs vs the actual editor (floppy build in Hatari; `floppy_logs/rt_ste.txt`, `docs2c.txt`)
Checked and matching (README_FLOPPY.TXT and README_HD.TXT):
- Manager: Original game / Campaigns > / Levels > / Load from campaign disk / Save to campaign disk. Campaign menu Play / Edit entries / Rename / Delete / < back; entry menu Change source / Insert after / Remove / Move up / Move down / < back; level menu Play / Edit / Copy / Delete / < back.
- Cell menu (15 items, scrolls): Empty C, Ledge L, Crumble ledge, Conveyor left N, Conveyor right M, Pillar P, Blue block (shoot) B, Lift >, Door opening D, Exit door X, Enemy >, Level >, Playtest, Save to campaign disk, Leave editor. README order identical.
- Enemy >: Stone ball S, Red ball R, Red ball waits W, Eye up/down slow U, Eye up/down fast I, Eye left/right J, Eye l/r fast K, < back. Lift >: Lift: from here A / stop here Z / delete / < back.
- Level >: Colours >, Enemies >, Copy tower >, Blank grid, Time +50, Time -50, Name..., < back (README order identical). Colours list = the 8 tower names, Enemies list = `1 Eyelid, 2 Studded, 3 Four orbs, 4 Split plate`, Copy tower list = 8 + 8 shipped towers (16). Name prompt shows `U/D letter L/R move` / `Fire = done` (= README).
- Door D / menu places the opposite door at col^8 (status line `Door + opposite`); Exit X places 3 cells, no partner (`Exit (finish)`). N/M/C/Del/L/P/Return/Space keys behave as listed; T and E do nothing in the editor map (cell and cursor unchanged). Panel `S3 E2` + rows/column/row/cell value. Crumble cell is cleared under the frog (frog falls); conveyors carry a standing frog to the end of the run.
Mismatches / wording issues (exact text):
1. README_HD.TXT: "Crumble ledge (looks like a ledge, disappears under the frog when it steps on it)" vs README_FLOPPY.TXT: "Crumble ledge (looks like a ledge, the frog falls when it steps on it)". Both are true (cell cleared, frog falls), but the two documents word the same cell differently.
2. README_HD.TXT / README_FLOPPY.TXT list "Blue block B" / "Blue block (shoot it once per cell to remove it)"; the menu item reads `Blue block (shoot) B` (minor). Enemy list "Eye left/right J slow, K fast" (FLOPPY) vs menu `Eye left/right  J` and `Eye l/r fast  K` (no word "slow").
3. README_HD.TXT: "The Options page lists it on its second line: \"F10/D  Level editor\"": on the floppy build it is the FIRST list line under `Options:` (floppy_shots/opts.png). HD build not looked at by me [INFERENCE: same hook, check by the HD agent]. README_FLOPPY.TXT does not claim a line.
4. README_FLOPPY.TXT: "<new campaign> makes a new one": it creates `NEW CAMP` and opens its entry list directly (`<add entry>` / `< back`); the campaign menu (Play/Edit entries/Rename/Delete) is reached by backing out and picking it. Fine as a description, noted only.
5. In-editor help is just the status text `Fire=menu Ret=again` (and the name prompt hints); there is no on-screen key list, so the keys N/M/D/X/C are only discoverable through the menu letters. Not a mismatch with the READMEs.
Not verified: README claims about Lift behaviour, F5/F6 50/60 Hz on the floppy ("The game runs at 60 Hz"), 512 KB behaviour.

## 5. dadprg (no edits there; `git status` unchanged: 9 modified + `doors.rb` untracked, as found)
- `cd api && bin/rails test`: `222 runs, 1575 assertions, 0 failures, 0 errors, 0 skips`.
- `cd front && npx vue-tsc --build`: exit 0, no output.
- Parser cross-check (`floppy_scripts/gen.py`, `dump.rb`, `cmp.py`; log `floppy_logs/parser_xcheck.txt`): 6 levels in 4 files (1 made by the floppy editor in the round trip, `e1.ovl`: `$91 $a1 $b1 $83 $c3`, tower byte 2 / flags 2; 3 generated: conveyors+crumble with flags 3; doors/exit with tower 5 / flags 4 and an odd-size (105 B) record with tower 7 / flags 1; a 120-row level with the legacy colour nibble `flags 0x62` and random cells; a 16-row level flags 0x80). `Hub::Ncmp::Parser` (Ruby) vs `ovl.py parse`: grid, rows, mission, time, tower byte and flags byte identical in all 6 (`grid_equal=True`); `colour_scheme` = (flags>>4 or tower+1) and `eye_design` = (flags&15 or (tower&3)+1) as expected, campaign playlists same length. The first run flagged e1 only because `ovl.py` keeps the trailing space of `NEW LEVEL ` while the Ruby parser strips names (benign; compared stripped). `Hub::Ncmp::Legend.label`: `$91` Crumbling ledge, `$a1`/`$b1` Conveyor ledge pushes left/right, `$83` Door opening, `$c3` Exit door, tiles 3/19/20/7/8.

## 6. Script changes (all in `floppy_scripts/`; tracked files untouched)
- All copies: `/tmp/nfe*`, `/tmp/oddcore`, `/tmp/ne/...`, `/tmp/nlg/...` paths moved to the private scratch; `lib.py` gets the `CPU16` hook (`set_cpuclock(16)` after the title).
- `f161_nfe.py`: `t.K('Down',10)` -> `t.K('Down',13)` in the "Save from the editor root menu" step. The cell menu now has 15 items (Crumble ledge, Conveyor left, Conveyor right added), so `Save to campaign disk` is item 13; with the old 10 the script pressed another item (first run: 9 failures, then 4 failures with a wrong 12; with 13: 0). Script bug, not product.
- `fl_look.py`: reads `looks15.ovl` (`mk_looks2.py`) instead of the `odd/looks.ovl` I first passed; the reference dir must be the HD `base8` dump (the earlier 9-FAIL and 3-FAIL runs used a wrong file / the looks15 dump as reference; `fl_look_ste.txt`, `fl_look_ste2.txt` kept as raw evidence of that, not counted). `MACH` env for Mega STE.
- `fl_ui.py` is the repo's `work/floppy/fl_ui.py` (already the Level > version) with paths only. `fo180.py`/`fge.py`/`fge2.py`: paths only. New: `rt.py`, `docs2.py`, `mfp.py`.
- `base8`/`looks15` reference dumps are HD dumps of the previous build (game side untouched by cf52f4f) [INFERENCE: still valid; fl_ui and fl_look PASS against them].

## 7. Follow-up (lead's request)
- fge `MFP block intact` FAIL: identical on the v1.1.1 floppy in the same environment (section 3), so it is environmental; the script is unchanged.
- HD Options page (STE, build from this tree, 14 screenshots, `floppy_shots/opts_hd.png`): "F10/D  Level editor" is the FIRST line under `Options:` (same as the floppy). README_HD.TXT said "second line"; fixed.
- `f161_nfe.py` (work/gate_NebFloppyEject, same edit in work/gate_NebOddGateCore copy) now selects "Save to campaign..." by name via the menu state instead of a Down count. [INFERENCE: not re-run after the edit; the helper is the same menu reader that rt.py used successfully.]
- README_HD.TXT / README_FLOPPY.TXT: crumble wording, exact menu names, Options line, `<new campaign>` text corrected (doc mismatches 1-4).
