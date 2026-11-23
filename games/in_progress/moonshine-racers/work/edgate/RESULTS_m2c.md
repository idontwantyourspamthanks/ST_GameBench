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


# Finish pass (MSREditor8, 2026-11-23): gates on the CURRENT build, fixes, preview
Build: `python3 tools/msrpatch.py build --out /tmp/msred8/hd` (verify ALL OK; overlay 19,218 B, md5 `3d52ea1c...`; RUNME.TOS md5 `7ff3733d...`). Chain `work/edgate/chain8.sh` (env8.sh, `/tmp/msred8`, logs `logs8/`; chain7 / env7 removed). v1.1 references `/tmp/msred8/v11`, `v11fl`.
## Harness bugs found and fixed (not editor faults)
* `cg.py boot_title`: switched fast-forward OFF at vbl 4500 and polled the title only at 50 vbl/s; on the current machine the attract race had started before the title was seen -> 'title reached: False'. Now fast-forward stays on until the title is seen.
* `speed.py`: the CycleCounter now exceeds 2^31 and Hatari prints `#N/-M (dec)`; the regex matched nothing (every case 'code points hit: FAIL'). Fixed.
* `ed2.py` quick, plain straight: the second split (segment 1) started at 24576 > the race extent 20024; now splits segment 0 twice. Stock full: the BAR's old segment (318) lay beyond the extent once the BAR had been moved to segment 30 (extent shrinks, by design); the last BAR move now uses `min(k0, seg_last)`.
* `abs1m.py`: breakpoints were set after the payload copy, so the welcome screen had already run (hint1mb 0 times); set at power-on now. Defaults point at /tmp/msred8.
## Editor fixes
* `speed` first result: one segment 78 ms, next row 86, scrolling row 176, bend 126, list step 151 (criterion 60 ms): the panel (11 rows x 28 characters at ~1500 cycles per character) dominated. `lp28` now keeps a per-row shadow (`vPSh`) and draws only changed characters, `cls` invalidates it: one segment 21 ms, next grid row 31, row 41, scrolling row 129, bend 60, list step 85 [obs `logs8/speed_ste2m.txt`].
* `draw_labels`: shadow key = (scroll + cursor row, last segment with a tile) (`vSLab`, `vSLab2`): the labels redraw when the segment count changes under an unchanged scroll / row. [INFERENCE: the trigger (insert / delete at the end) was not provoked in a gate; the shots check (screen == drawing) and the ed2 insert / delete / merge checks pass with it.]
* Header of a plain straight: `NEW STRAIGHT` (was `NEW NEW STRAIGHT`): the source tag and number are skipped for source 2 [obs screenshot `q_straight_ste2m_2_start.png`].
## Gates (all on the build above)
| gate | result | log |
|---|---|---|
| ed2 full, STE 2 MB, stock | ALL CHECKS PASS | `ed2_stock_ste2m.txt` |
| ed2 quick, STE 2 MB, plain straight (incl. PLAY to the BAR) | ALL CHECKS PASS | `q_straight_ste2m.txt` |
| ed2 quick, Mega STE 2 MB / ST 2 MB, stock | ALL CHECKS PASS / ALL CHECKS PASS | `q_stock_mste2m.txt`, `q_stock_st2m.txt` |
| speed (ms above; burst checks 10 x RIGHT = 2 redraws, 12 bend steps = 1 recompute, typed-ahead list) | ALL CHECKS PASS | `speed_ste2m.txt` |
| td3, STE 2 MB (test drive from the cursor, incl. start at the selected object) | ALL CHECKS PASS | `td3_ste2m.txt` |
| td3 quick, Mega STE / ST | ALL CHECKS PASS / ALL CHECKS PASS | `td3_mste2m.txt`, `td3_st2m.txt` |
| shots (screen RAM == Python drawing of the shadow slots at every point) | ALL CHECKS PASS | `shots_ste2m.txt` |
| welcome 2 MB (`--full`: F10 menu, play list, race) | ALL CHECKS PASS | `w2m.txt` |
| welcome 1 MB: text row 23 = `2 MB: CAMPAIGNS + TRACK EDITOR` | ALL CHECKS PASS, screenshot `logs8/shots/w1m_1_welcome.png` | `w1m.txt` |
| abs1m (1 MB, exactly the site `$7c04` patched, no blob instruction outside the 1 MB path, no editor / track GEMDOS call, race runs): STE / ST / Mega STE | ALL CHECKS PASS (3 runs) | `abs1m_ste.txt`, `abs1m_st.txt`, `abs1m_mste.txt` |
| floppy 1 MB title vs v1.1 (two points: 32,000 visible bytes) | IDENTICAL; `sitefl` (no campaign site at 1 MB) PASS; `flhint` 2 MB (F10 hint) PASS | `fl1m_new.txt`, `fl1m_v11.txt`, `sitefl_1024.txt`, `flhint_2m.txt` |
Floppy `disk_a.st` differs from v1.1 (`d6a23ef2...` vs `81e2a7b7...`) in the payload sectors only: cp_title's blob changed (shared source). The floppy has had no `cp_welcome` since the campaign feature (`; media: hd`; its screen is never shown there; the hint is `cp_flhint`), so no site reaches `e3`'s 1 MB path and the title is unchanged: intended per 15.9; the design note's `cp_welcome_fl` claim was stale and is corrected. `disk_b.st` is identical to v1.1.
## Bus / Address error lines
3 per race run on STE (the game's own STE probe at `$ff8e21`, PC `$21238` / `$b4928` / `$bf6b2`, same as in logs7), 1 in some cells: not the editor.
## Open
* Bend / hill thresholds left as they are (300 / 1200 / 2400, 0.02 / 0.10): the user to judge on the preview.
* `vTmp2`, `TILEW` unused equates remain.
## Preview
`work/testdisk/MoonshineRacers_editor_preview2.zip` (MOONSHR/: RUNME.TOS md5 `7ff3733d...` and FILES/MSEDIT.OVL md5 `3d52ea1c...` == the gated build; FILES/MSTRACKS.TRK = `work/testdisk/MSTRACKS.TRK`, 11,650 B).
