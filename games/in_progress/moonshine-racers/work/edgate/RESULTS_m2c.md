# Milestone 2c (tile-grid editor): crash fix, corrections, state and resume steps (MSREditor7, 2026-11-23)

Base: `04df35c` (WIP, broken). Everything below is UNCOMMITTED in the tree. Tags: **[obs]** raw output kept (file named), **[INFERENCE]** not observed.
Build used for every run: `python3 tools/msrpatch.py build --out /tmp/msred7/hd` (overlay 19,088 B, md5 `a5dc74d7...`, == the current source; `msrpatch.py verify`: ALL OK). Hatari 2.6.1, private HOME `/tmp/msred7_home`, env `work/edgate/env7.sh`, logs `work/edgate/logs7/`, screenshots `logs7/shots/` (git-ignored PNGs). Stopped on the lead's scope change: the gate list, the preview zip and the design-note update were NOT done (section 5).

## 1. The draw_panel crash [obs] (`logs7/crashprobe.txt`, build of `04df35c` in `/tmp/msred7/hd_broken`)
* **Cause: `bendtab` / `hilltab` hold LONG entries (`dc.l t_sy0,...`) but four lookups scaled the index by 2 (`add.w d0,d0`) instead of 4**: `draw_panel` BEND and HILL rows, `legend` symbols and hill names. Index 1 therefore read the low word of entry 0 and the high word of entry 1.
* Faulting instruction: `apps` (`$130344: move.b (a0)+,(a1)+`), called from draw_panel's HILL row with a0 from `$130A86: movea.l (a0,d0.w),a0`. Raw lines:
```
> m $150000 4
00150000: 00 48 00 48                                      (TILE[0] = $0048: hill class 1)
00130a4e 2070 0000                movea.l ($00,a0,d0.w) == $001336d6 [00134612],a0     (BEND row, class 0: still right)
WARN : Bus Error reading at address $46640013, PC=$130346 addr_e3=130346 op_e3=12d8
WARN : Address Error writing at address $ffffff6d, PC=$e09598 ...  (repeats)
```
`$46640013` = low word of `hilltab[0]` (`t_hc0` = `$00134664`) + high word of `hilltab[1]` (`$0013....`). The earlier agent's `$46960013` was the same thing in its instrumented build (addresses shifted). The table TARGETS were right; only the scaling was wrong (the lead's hint).
* Fix: index * 4 (`patches/ovl/msedit.s` draw_panel ~1058-1074: `lsl.w #2,d0` / `lsr.w #1,d0 + andi.w #$1c,d0`); the legend is now table-driven (`legtab`, long text pointers read with `(a2)+`), the duplicate `symtab` is gone.
* After the fix the whole screen draws: section 3.

## 2. Other corrections in `04df35c`'s code (found by reading it; `patches/ovl/msedit.s` unless noted; line numbers of the current file)
Crashes / wrong memory:
1. `tiles_calc` (705) walked the segment list from `seg_ptr` (the CURSOR's segment) instead of `SEGT`: tile words of every segment were wrong unless the cursor was on segment 0. Rewritten (registers only).
2. `tiles_calc` hill classes had no LEVEL: `< 1311` gave RISE/DROP SMALL, the rest BIG (thresholds 0.02 / 0.10 of the design = 1311 / 6554 now).
3. `view` initialised ONE of the 128 shadow slots (`moveq #0,d0` as the loop count), and nothing invalidated the shadow after a page was cleared (HELP, menu, type list, check page, test drive): the grid came back empty. Now `draw_full` (1300) = cls + shadow invalid, used for redraw bit 0; `draw_view` (1312) draws what changed.
4. `legend`: `moveq #176,d1` (= -80: text written outside the screen), and PRESS A KEY drawn over the BAR tile. Rewritten.
5. `obj_sort` (1464) moved `n` longs instead of `2n` when closing the gap: corrupted the object list on every MOVE. Now uses `obj_shut` / `obj_open`.
6. `obj_mv_step` (3444): overwrote its step register with the object index (direction lost: always skipped upwards), and read the segment length through the OBJECT pointer. Rewritten to the design (range 1 .. extent-1, skip occupied units in the direction, cursor follows: `obj_follow` 1491).
7. `occ_unit` (3488): `bhi .fr` ended the scan at the first object BELOW the unit (reported "free" for almost every unit); now `bcs`. Its comment said the opposite flag sense of the code.
8. `pick_unit` (1415): inverted test (took the first OCCUPIED unit, skipped free ones); could return unit 0.
9. `curve_step` (2682): with the object list focused it jumped to `edit_list` with a garbage act (table index out of range). Road edits work in both focus states now (design 15.5); `rep_cmd` only requires the list for TYPE / SIDE.
10. `draw_labels` (945): `appn` (takes d0.l) called with a dirty upper word on the first row; the "cursor row" compared the absolute row with the screen row (wrong once scrolled).
11. `draw_panel`: empty object lines printed an empty string (stale text stayed); `.none` likewise.
12. `draw_hint` was never called (no hint row, no messages); `t_hint`, `t_wrongrow`, one help line were longer than 40 columns (the help line would have written past the row).
Behaviour against the design (15):
13. `step_row` in the object list cleared the focus instead of moving the selection; `obj_sel` was never called and wrapped to the last object for UP on object 0 (unsigned compare). LEFT / RIGHT / Home / B did not give the cursor back to the grid (`seg_move` 1717 does now); a segment without objects could keep the list focus (`obj_find` 1360 clears it).
14. `grid_fit` (1323): `seg_move` always re-centred (128 tiles redrawn per row move); the "below the window" case computed a first row that did not show the cursor. Now: scroll one row at the edge, centre only when the cursor is outside the window; the last row of tiles is the grid's last row.
15. `obj_add` let a new object land on the BAR's unit (`pick_unit` called with "BARs do not block"); `bar_here` dropped the BAR's lateral (`clr.w 4(a0)`; the old code kept it).
16. `seg_split` moved the cursor to the second half (design: stays) and used the hill-shape message.
17. `obj_mv_seg` cleared the focus mid-move, used signed compares on units, ignored the extent; `mv_cmd` cancel did not restore the cursor's segment.
18. Tile glyph: the 7th row was never drawn (`cmpi.w #8` for rows 2..8); the BAR chequer was drawn in the hill colour, not white.
19. `check_all` W-HILL (3637) integrated over all 32768 units instead of the race length (msrtrack.py validate uses the race length).
20. `tiles_calc` now calls `find_bar` first: after a LENGTH edit the BAR's unit (`vBarAt`) was stale, so the extent was off by the length delta [obs: `end 21760 vs 21744` in the first full-gate run].
21. FIRE + UP / DOWN was a toggle (design: DOWN in, UP out); HELP flipped both pages at once while fire was held (`in_reset` between pages).
22. `c_td` (4420): P with the object list focused started at the segment's first unit; now at the selected object's unit (design 15.7). NOT run.
23. `patches/cp_title.s` `e3` (86-95, `hint1mb` 131): the 1 MB path tested HAGA machine types 2..3 only (a plain ST / Mega ST, type 1, got no line), clobbered d0 (the routine's seed counter), a0, a5, d4 and called the text routine without saving registers. Now: types 1..3, all registers kept, shares the 2 MB hint's text call. NOT run at 1 MB.
Design choices changed while fixing (deliberate; to be written into `editor_design.md` 15/16): the cursor is a 2-pixel frame + a black ring (a 1-pixel frame was hard to find); the frame is MAGENTA (palette 10) while the object list has the cursor (yellow vanished on yellow tiles); DROP colours `$067` / `$037` (the black symbol was unreadable on `$024`); the object dot is the top-right corner (rows 0-1, columns 13-14) and stays as a notch in the frame; panel lines `CURVE RIGHT 3`, `HILL RISE SMALL ACC +0200`, `01 TYPE 026 SIDE -041 12345` under a `UNIT` heading; header, labels, key column and hint row are redrawn only when they change (shadows `vSLab vSHdr vSKey vSHint`); dead code removed (`qsin` table 2 KB, `cheq`, `symtab`, `lbox`, 16 unused texts, `vAcc vAcc2 vAx vAy vK vBlkEnd`).

## 3. What was run [obs]
| run | build | result | log |
|---|---|---|---|
| `shots.py` STE 2 MB (campaign track, copy of TRACK 04, plain straight; cursor moves, row scroll, object list, curve / hill list preview, HELP x2, menu, Home, S S L I x6 . . O) | fixed build before items 20 / 22 | ALL CHECKS PASS: at 19 points the 128 shadow slots == the tile words and the screen RAM == a Python drawing of every slot (0 wrong pixels); Bus/Address error lines 1 | `logs7/shots_ste2m.txt`, `shots/shots_ste2m_*.png` (+ `_x3` enlargements) |
| `ed2.py --kind stock --quick` STE 2 MB (18 edits of every family incl. O, I, MOVE with a segment change, BAR, undo / redo; keep; validate; re-enter; PLAY to the BAR) | same | ALL CHECKS PASS (lists + tile words == model, kept block 4384 B == model, validate 0 errors, race on the edited track) | `logs7/q_stock_ste.txt` |
| `ed2.py --kind stock` (full) STE 2 MB | CURRENT build | 68 edits, every check PASS (splits, curves, hills, lengths, widths, copies / deletes / merges, 5 object adds, types, sides, 5 moves, 5 deletes), then a HARNESS exception (`seg_goto` pressed DOWN while the object list had the cursor; fixed in `ed2lib.py`, not rerun) | `logs7/ed2_stock_ste2m.txt` |
Screenshot for a first look: `logs7/shots/shots_ste2m_stock_3_down7_scrolled.png` (grid, white cursor frame on segment 118, panel with two objects), `..._stock_4_objects_x3.png` (object list, pre-magenta frame colour), `..._straight_2_edited_x3.png`, `..._help_2_legend_x3.png`.

## 4. Known open points in the source (not fixed)
* `draw_labels`' shadow key is scroll position + cursor row only: when the NUMBER of segments changes without either changing (insert / delete near the end), row labels of rows that gained or lost tiles are not redrawn. Fix: put `seg_last` into the key (make `vSLab` a long). [INFERENCE: read, not provoked]
* Header of a plain straight reads `NEW NEW STRAIGHT` (source tag + name; old behaviour).
* `vTmp2`, `TILEW` are unused equates.
* The direction thresholds (300 / 1200 / 2400) are the previous agent's; whether `c` = 300 already looks like a bend to the player was not judged.

## 5. Resume steps (nothing below was done)
Harness state: `ed2lib.py`, `ed2.py`, `ed2model.py`, `td3.py`, `speed.py`, `welcome.py`, `abs1m.py` are ALREADY ported to the grid (no old variable map left: `VAR` is parsed from the `vName equ` lines of msedit.s, `symbols()` assembles the current source, so REBUILD before every run or breakpoints miss). New: `shots.py`, `chain7.sh`, `env7.sh`. Deleted as obsolete: `eg.py cmpmap.py chain.sh ed3.py prof3.py symlst.py td_probe.py probe8/9/10.py menu6/7.py smoke6.py env6.sh logs6/`. Unrun after their port: `speed.py` (new: ms per step / row / scroll / bend / list preview from Hatari's CycleCounter, bursts), `td3.py`, `welcome.py`, `abs1m.py` (expects exactly the site `$7c04` patched at 1 MB and breakpoints over cp_title's blob minus the 1 MB path), the straight / Mega STE / ST quick cells.
1. `cd games/in_progress/moonshine-racers; work/edgate/chain7.sh` runs everything one Hatari at a time (verify, HD + floppy builds into `/tmp/msred7`, then `ed2 speed td3 shots qstr qmste qst tdmste tdst w2m w1m abs fl`; single cells: `chain7.sh ed2 speed`). v1.1 references are unpacked in `/tmp/msred7/v11` and `/tmp/msred7/v11fl` (from `dist/*_v1.1.zip`; redo if /tmp was cleared). Expect script bugs in the unrun cells first.
2. Floppy: `disk_a.st` now differs from v1.1 (`d6a23ef2...` vs `81e2a7b7...`: cp_title's blob changed; `cp_welcome` is `; media: hd`, so the floppy build has NO `$7c04` site; `editor_design.md` 15.9 still says a `cp_welcome_fl` exists: it does not). The 1 MB title check is `flshot.py` new vs v1.1 (`chain7.sh fl`).
3. Then: `editor_design.md` section 16 (as built, the list of section 2), the open points of section 4, the preview zip (`msrpatch.py build --out work/testdisk/editor_preview2/MOONSHR`, copy `work/testdisk/MSTRACKS.TRK` into `FILES`, zip as `work/testdisk/MoonshineRacers_editor_preview2.zip`).
