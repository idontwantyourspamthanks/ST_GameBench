# Moonshine Racers: the in-game TRACK EDITOR, design and milestone 1 (the viewer) (MSREditor, 2026-11-21)

> **PARKED (user decision, 2026-11-23).** The in-game track editor is not released and work on it has stopped. The released Moonshine Racers is v1.1 (campaigns via `MSTRACKS.TRK` from the PC tool `tools/msrtrack.py`; F10 menu), built from the v1.1 commit, not from this tree. State at parking: tile-grid editor gated in Hatari (`d9f8542`), test drive from the cursor, an unexplained test-drive crash the user hit once (`work/edgate/RESULTS_tdcrash.md`, not reproduced), and the build-as-you-go design (section 17) with its packages A (format v2 in `msrtrack.py`) and B (`cp_len.s` loader, per-track race length) done but the editor side (packages C-F) not started; `cp_len` replaced `cp_td` and the editor's test drive was NOT re-gated with it (`work/edgate/RESULTS_wpab.md`). Open user decision if resumed: the time rule ("scenery pace + 100 passes") leaves an un-upgraded car almost no spare time on 2000-unit roads and cannot finish 6000. Any Moonshine release from this tree must first decide whether to keep the editor code out (build from the v1.1 commit or a clean worktree).

Base: v1.1 (`8440b53`: campaigns, F10 menu, 2 MB gate). Study and facts this builds on: `trackeditor.md` (viability), `trackformat.md` (block / campaign file), `trackloader.md` (redirect sites, HAGA window, free RAM), `campaign_hd.md`, `campaign_floppy.md`. Quality bar: the Nebulus level editor (`games/done/nebulus/patches/ed_editor.s`, `work/notes/editor.md`): clear menus, pick lists with a visible selection, live preview while the selection moves, a status line, keyboard shortcuts with Return / Space = repeat.
Tags: **[obs]** raw output kept in `work/edgate/logs/` (file named), **[disasm]** `tools/m68dis.py` on `work/dumps/ram_race_start.bin`, **[INFERENCE]** not proven. Hatari 2.6.1 only; nothing was run on real hardware.

User decisions (fixed): editing model = SEGMENT LIST with a cursor along the track; main view = TOP-DOWN MAP of the whole track + height / width / object strips; values picked from short lists; objects from the base level's own type list; exactly one BAR; new track = copy of a stock track or a plain straight with the BAR at the end; saving from inside the game on the HD release first (HAGA window, `Dfree` after `Fclose`), floppy saving later; joystick for everything, keys as extras; ST family with 2 MB or more only; no minimap work.

## 1. Architecture: where the editor code lives

**Decision: a lazily loaded overlay file, `FILES\MSEDIT.OVL`, not the payload.**

| option | room | 1 MB machine | cost / risk |
|---|---|---|---|
| payload (`RUNME.TOS` data, as the campaign code) | cap `IMG_MAX_LEN` = 61,440 B, used 55,348 B: **6,092 B** to the cap; the zero gaps inside the image are fragments (largest about 3.4 KB at `$B328A-$B3FFF`, `msrpatch.py list`) | the bytes are in RAM (never executed) | the viewer alone is 8.9 KB (6.9 KB code and text + a 2 KB sine table), editing will roughly double it: it does not fit, and every later feature would fight for gaps with the speed patches |
| **overlay `FILES\MSEDIT.OVL`** (chosen) | 64 KB reserved at `$130000` (`EDBASE`), no fragmenting: one source file, one contiguous image | **no editor byte in RAM**; the only addition to the payload is a 284 B stub inside `cp_title`'s own gap, behind the 2 MB gate | first use reads the file through the HAGA window (the same `trk_read` that loads a campaign: interrupts off for about 0.7 s, `trackloader.md` 5.2); the HD zip gains one file; a missing / damaged / wrong-version file gives a message in the menu and nothing else changes |
| floppy equivalent (milestone 5, not built) | spare sectors of disk A (the payload uses 109 of the 129 allocated blank sectors: more blank track-sides are needed [INFERENCE: not surveyed]) | nothing loaded | recommended: the boot sector (stage 0) reads the overlay to `$130000` right after the payload when it stored phystop >= 2 MB (disk 1 is in the drive by definition, RAM above 1 MB is not touched by the game: `campaign_floppy.md` 1.4; cost about 1 s of boot per 15 KB, 2 MB+ machines only); alternative: lazy read with the game's own driver `$cac0` and an "INSERT DISK 1" prompt. Until then the floppy build has **no editor item at all** (`ifeq FLOPPY` in `cp_title.s`; the floppy `cp_title` blob assembles to the same bytes as before) |

Mechanism as built: `tools/msrpatch.py build` assembles `patches/ovl/msedit.s` at `EDBASE` (predefined equates `EDBASE EDWORK EDVER CPV CPSTORE ...`), writes the header (`MSED`, `EDVER.w`, 0, length.l, CRC-32.l of the bytes from +16) and puts the file into the build's `FILES\`. The F10 menu's new item **TRACK EDITOR** (HD build) calls `ed_load` in `cp_title.s`: on first use `trk_read("MSEDIT.OVL", EDBASE, 64 KB)`, then magic, `EDVER`, length and CRC-32 are checked (`crc_tab` / `crc_upd` of the campaign validator), `V_EDOK` (`CPV+12`) is set and `jsr EDBASE+16` runs the editor; it returns to the campaign menu. Messages: `LOADING THE TRACK EDITOR...`, `MSEDIT.OVL NOT FOUND IN FILES`, `EDITOR FILE DAMAGED OR WRONG VERSION`. The overlay is self-contained (own text, list and drawing code) and uses only fixed addresses of the game: `$d206` (vertical sync), `$d6fa` (file service), the font `$190be`, the key tables `$5ffe` / `$607e`, `$60ff`, the joystick byte `$6105`, the level descriptor table `$28a2`.

Machines: the item exists only where list 2 of the trampoline was applied (ST / Mega ST / STE / Mega STE with >= 2 MB, `; gate: ram2mb`); 1 MB, TT and Falcon keep the stock F10-less title and never read the file.

## 2. RAM map above `$100000` (2 MB ceiling `$1CD000`, `trackloader.md` 2)

| range | use | status |
|---|---|---|
| `$100000-$1007FF` | CRC table, campaign menu scratch | v1.1 |
| `$110000-$12FFFF` | campaign file as read = **the working campaign**: the races read it (`cp_fetch`), the editor's list shows it, milestone 2 writes edited tracks back into it, milestone 4 saves it | v1.1 |
| `$130000-$13FFFF` | `MSEDIT.OVL` image (about 19.2 KB in M2) | M1 / M2 |
| `$140000-$140FFF` | editor variables (4 KB, cleared at entry) | M2 (M1: 2 KB) |
| `$141000-$1427FF` | block buffer: a stock track read by the game's file service (at most 12 sectors) | M2 (M1: `$140400`) |
| `$142800-$142FFF` | the object type table (S5 + end word) of the track being edited, copied from its source block by `parse` and into every block written | M2 |
| `$143000-$148FFF` | segment list, 2048 x 12 B | M1 |
| `$149000-$14AFFF` | object list, 999 x 8 B | M1 |
| `$150000-$167FFF` | per-unit arrays: height, left width, right width (32768 B each) | M1 |
| `$168000-$16C003` | path points: x.w, y.w every 8 units (4097) | M1 |
| `$16D000-$16F7FF` | sine table (4096 per turn + a quarter) | M1 |
| `$170000-$177CFF` | the editor's screen | M1 |
| `$178000-$19FFFF` | undo history: entries `size, counts, cursor, segments, objects, size` (about 8.5 KB for a stock track: about 18 steps; the oldest entry falls out when the ring is full); also the scratch where the campaign file is rebuilt when a track is kept or deleted | M2 |
| `$1A0000-$1AFFFF` | `expand` checkpoints: the start state of every segment (c, 8-unit sum, slope, height, two widths, path accumulators = 32 B) so an edit re-expands only from its segment on | M2 |
| `$1B0000-$1BFFFF` | the encoded track block (the same bytes `tools/msrtrack.py` writes) | M2 |
| `$1C0000-$1C7CFF` | second screen: live-preview pages are drawn here and flipped in at the next vertical sync | M2 |
| `$1C8000-$1CCFFF` | spare | |

`cp_title.s` declares `; himem: $130000-$13FFFF` and `$140000-$1C7FFF`; the tool checks them against the other reservations and the ceiling.

## 3. Taking and giving back the machine (model: Nebulus `ed_run`, simpler here)

The editor is entered from the campaign menu, i.e. inside the title's key exit: main code, supervisor, the game's own VBL handler `$d11e` (frame counters, mouse interrogation, fades, the title music via `$d486`) and IKBD handler `$cfb4` running, no raster split (Timer B is a race thing) [disasm].
* **Kept running, untouched**: the VBL vector, the MFP, the IKBD handler. The title music keeps playing in the editor.
* **Screen**: the editor saves `$ff8201` / `$ff8203` and the 16 palette words, clears its own buffer `$170000`, waits for the game's sync and points the shifter at it (any ST can display from RAM above 1 MB; the base is 256-aligned, so the STE low byte stays 0); own palette. On leaving: sync, the two base bytes and the palette are written back. The game's buffers `$70000` / `$78000` and its pointers `$1004` / `$1008` are never touched.
* **Input**: polled once per frame from what the game's handler maintains: `$60ff` (last make code, cleared when read), the held-key table `$5ffe+scancode` (auto-repeat of the cursor keys, Shift `$2a` / `$36`, Control `$1d`), the latched-make table `$607e+scancode` (cursor keys: a tap shorter than a frame still counts; only the four cursor latches are cleared), the joystick byte `$6105` (bit 0 up, 1 down, 2 left, 3 right, 7 fire). Nothing is hooked, so nothing has to be restored; on leaving `$60ff` is cleared and fire must be released.
* **Disk**: a stock track is read with the game's own call (`$28a2` descriptor, `jsr $d6fa`, exactly as the race setup `$77c6-$77e0` does) into the editor's buffer. HAGA may open its TOS window for it (grey screen for a moment), as in any race load.
* **Milestone 3 (playtest)** adds the only real hand-over: write the track into the store, start the game through the title exit with a "test" flag, and come back at the race's end (`cp_wrap` already wraps the whole race).

## 4. The editable data model

**One segment list for the road, one object list.** A segment = a stretch of road with ONE curve delta, ONE hill accel and ONE pair of width targets: `start.w len.w curve.w hill.w wl.b wr.b` (12 B). Loading builds it as the union of the breakpoints of the four ring streams (S0 curve, S1 left, S2 right, S3 hill); keeping a track writes the four streams back, merging neighbours with equal values per stream. Objects: `at.w type.w lateral.w flags.w` (absolute position; flag bit 0 = the BAR), sorted. The type table S5 is never edited: it is copied verbatim from the source block (E-TABLE cannot occur).

Why this and not the six streams as they are: the user edits "this piece of road" (length, bend, slope, widths) with one cursor; four independent stream cursors would need a layer switch for every change. Cost: none in fidelity. **[obs] all 15 stock tracks survive block -> segment list -> block byte for byte** (Python model of exactly the union / merge rule above: 200..398 segments per track, re-encoded block == stock block 15 of 15; the stock streams never hold two equal neighbours and all four sum to 32768). The in-game `parse` is checked against the same model in the gates (section 9).

Rules the model keeps by construction (milestone 2):
* total length stays 32768 units: the last segment (the padding behind the finish) grows / shrinks when a segment's length changes, so E-SUM cannot occur; objects and the BAR behind an edited segment move with their road.
* exactly one BAR: it can be moved ("put the BAR here"), never deleted or duplicated; the type list does not offer the BAR type. E-BAR can only be shown for a damaged loaded track.
* values come from lists inside the stock envelope (curve -9..+10, widths 10..85, hill accel -6000..4000, lateral -128..127), so E-RANGE / E-LAT cannot be produced; out-of-envelope values of a loaded (`--lenient`) track are shown and kept until changed.
* **Hill** is the one field where the raw value is not what a user thinks in: accel is the second derivative of the height. The hill list therefore offers SHAPES that rewrite the segment into 2 or 4 pieces whose slope ends where it began: `FLAT`, `RISE` small / medium / big (+a for the first half, -a for the second), `DROP` (mirror), `CREST` (+a, -a twice as long, +a), `DIP` (mirror), and `RAW ACCEL` with left / right fine adjustment for experts. The height strip shows the result at once.
* **Undo**: a snapshot ring (segment list + object list + cursor; a stock track is about 4.8 KB + 3.7 KB) taken before every changing action; `U` / Undo steps back, Shift+U forward. At least 16 steps in the 288 KB reserved.
* Keep / save: encode -> replace the entry's block inside the campaign file image at `$110000` (move the later blocks, fix offsets, block CRC, table CRC, file length; E-SIZE = the block would exceed 8192 B: the edit is refused with a message). The store therefore always is a valid `MSTRACKS.TRK`: what the race hooks play and what milestone 4 writes.

Derived data (recomputed by `expand` after a load, later after every edit): per-unit height, left and right width exactly as the game's ring fillers compute them (`$ffe4`, `$fde0`: 32-bit integrator with the 0..127 clamp; 1-per-unit slew), and the top-down path. Path arithmetic = `msrtrack.py render`: heading = curve value / 600 rad, one step per unit; the editor sums 8 units at their mean curve value with a 4096-step sine table and 32-bit accumulators and stores a point every 8 units in world/4 units. Measured error against the PC tool's float path: section 9. A full `expand` of 32768 units costs about 0.6 s at 8 MHz [INFERENCE: instruction counts; the gate logs the VBLs]; milestone 2 must make it incremental (from the edited segment on, extent only) to keep list previews fluid.

## 5. UI specification

### 5.1 Entry points
* F10 on the title (or the hi-score screen) -> campaign menu -> **TRACK EDITOR** (below `LOADED CAMPAIGN`, HD build).
* **[built and observed, milestone 2b: `patches/cp_welcome.s`, `cp_title.s` e3/`t_whint`]** **User requirement (2026-11-21, ship with the editor release):** players can't tell that F10 exists. Accept F10 also on the `WELCOME PARTNERS / ... / PRESS A KEY` screen (the one before the face / typing-text title screen) and print a hint line `F10 = CAMPAIGNS` there (e.g. under `PRESS A KEY`), only where list 2 is applied (>= 2 MB); 1 MB machines keep the stock screen unchanged.
* Editor track list (milestone 1 heading `TRACK EDITOR (VIEWER)`): the tracks of the campaign in memory (`01  NAME  SCENERY nn`), then `COPY OF AN ORIGINAL TRACK >` (list `TRACK 01..15`), `PLAIN STRAIGHT ROAD >` (list: the scenery = base level whose object types, colours and race length the new track uses; one straight segment with the start widths of that track and its BAR where the original has it), `< BACK TO THE CAMPAIGN MENU`. Milestone 2: picking a campaign track opens `EDIT / TEST DRIVE / RENAME / MOVE UP / MOVE DOWN / COPY / DELETE / < BACK`; a copy or a straight becomes a new entry of the campaign (`<NEW CAMPAIGN>` when none is loaded); the list gains `SAVE CAMPAIGN`.
* All lists: a white bar marks the selection; up / down (wraps), FIRE / Return / Enter / Space choose, joystick LEFT / Esc / Backspace / F10 = back; the last item of every list is `< BACK...`; errors appear in red above the hint row.

### 5.2 The map screen (320 x 200, 40 x 25 text cells, own 16 colours)
```
row 0      C01 TRACK NAME                SCENERY 01     source (C campaign, S stock copy, NEW), name, base level
rows 1-13  top-down map of the whole track (104 px high): road, dim behind the BAR, a dot every 1000 units,
           green box = start, red box = the BAR; the cursor's segment thick yellow, the cursor a yellow cross
rows 14-17 HILL    height 0..127 (4 units per pixel row), a grid line every 1000 units, dim behind the BAR
rows 18-20 WIDTH   the road from above, straightened: left half-width above the middle line, right below
row 21     OBJECTS a tick per object: left of the road above the line, right below; the BAR a red full-height line
row 22     SEG 0017/0390 AT 12345 LEN 00120 ZOOM 1
row 23     CURVE R03  HILL +0200  WIDTH 36/34          (objects row: OBJ 012/417 AT 12345 TYPE 026 SIDE -041)
row 24     hints, or a message (yellow) until the next move
```
The three strips share one distance axis (x 64..319 = 256 columns, 128 >> (zoom-1) units per column: zoom 1 shows all 32768 units, zoom 8 one unit per pixel) with the labels in the left margin. The cursor is a full-height line through the strips; the segment's span is marked by a yellow bar above the hill strip and below the object strip. Everything that marks the cursor lives in bitplane 3, so moving the cursor redraws only that plane and the three text rows: the map itself (planes 0-2) is redrawn only when the view changes. **Zoom / scroll**: zoom 1 = whole track; each step doubles the strips' resolution and, up to x16, the map scale; the strips re-centre on the cursor when it comes within 16 columns of an edge, the zoomed map when the cursor leaves the middle of the window.

Milestone 2 list previews: an open pick list takes the right 12 columns of rows 1-21; the map is fitted into the remaining window and the strips scroll so the cursor stays left of the list; moving the selection applies the value to the working copy, re-expands and redraws (the Nebulus "the screen takes the highlighted look" rule); `< BACK` restores the old value.

### 5.3 Key map (the map screen). Joystick does everything; keys are extras. Scancodes = ST key positions, US legends.

| joystick | keys | milestone | action |
|---|---|---|---|
| LEFT / RIGHT | cursor left / right | 1 | previous / next segment (objects row: previous / next object); held = auto-repeat. LEFT inside a segment goes to its start first |
| UP / DOWN | cursor up / down, Tab | 1 | road row <> objects row (the row the strips show underneath: move down to the objects) |
| FIRE + LEFT / RIGHT | Control + left / right | 1 | fine: one strip pixel (1 unit at zoom 8) |
| | Shift + left / right | 1 | coarse: to the next multiple of 1000 units |
| FIRE + UP / DOWN | `+` / `-` (keypad or main row) | 1 | zoom in / out |
| | Clr/Home | 1 | to the start |
| | `B` | 1 | to the BAR (the finish) |
| FIRE (tap) | | 1 | the menu (every item shows its key) |
| | Help, F1 | 1 | key page |
| | Esc, F10 | 1 | leave the track (M2: keep it, back to the track list) |
| | **Return, Space** | 2 | **repeat the last edit at the cursor** (pick a curve once, then RIGHT, Return, RIGHT, Return ...); M1 answers `VIEWER: NOTHING TO REPEAT YET` |
| menu | `C` | 2 | CURVE list: `LEFT 9` .. `LEFT 1`, `STRAIGHT`, `RIGHT 1` .. `RIGHT 10` (opens on the current value) |
| | `,` / `.` (`<` `>`) | 2 | bend one step more to the left / right without a list |
| menu | `H` | 2 | HILL list (shapes, section 4) |
| menu | `L` | 2 | LENGTH list: 10 20 30 50 75 100 150 200 300 400 600 800 1000 1500 2000, and left / right = exact (+-1, with FIRE +-10) |
| menu | `W` / `E` | 2 | WIDTH LEFT / WIDTH RIGHT list: 10 15 .. 85 |
| menu | `I`, Insert | 2 | road row: insert a copy of the segment behind it; objects row: add an object of the last picked type here |
| menu | `S` | 2 | road row: split the segment at the cursor (after a fine move); objects row: SIDE list (far left .. middle .. far right, 9 values, left / right = exact) |
| menu | Delete | 2 | road row: remove the segment (the road behind moves up); objects row: remove the object (never the BAR) |
| menu | `T` | 2 | objects row: TYPE list = the base level's own types (`nnn KIND k SIZE s SPRITE nnn`), without the BAR |
| menu | Shift + `B` | 2 | put the BAR here |
| menu | `U`, Undo / Shift + `U` | 2 | undo / redo |
| menu | `P` | 3 | test drive from the cursor (F10 or the race's end returns to the map) |
| menu | | 2 | `TRACK >`: `NAME...` (up / down letter, left / right move, FIRE done), `CHECK` (all messages of 5.4), `SCENERY` (shown; fixed after creation, the types belong to it) |

Milestone 1 menu (FIRE): `GO TO THE START`, `GO TO THE FINISH (BAR)`, `ZOOM IN`, `ZOOM OUT`, `ROAD <> OBJECTS`, `KEYS`, `< BACK TO THE MAP`, `LEAVE THIS TRACK`, each with its key at the right edge.

### 5.4 Validation messages (codes of `msrtrack.py validate`, shown on row 24 and listed by `TRACK > CHECK`)
| code | text | when |
|---|---|---|
| E-TERM | `TRACK DATA IS DAMAGED (E-TERM)` | a stream or the object list runs past the block (load; built in M1) |
| E-BAR | `THIS TRACK HAS NO BAR (E-BAR)` / `n BARS: ONLY THE FIRST ENDS THE RACE (E-BAR)` | loaded tracks only (M1: the `B` key) |
| E-SIZE | `TRACK FULL: 8192 BYTES (E-SIZE)` | an edit would make the block too big: refused |
| E-HILL | `HILL TOO STEEP: HEIGHT OVERFLOWS (E-HILL)` | a hill pick overflows the 32-bit integrator: refused |
| E-GAP / E-OBJ | `AN OBJECT IS ALREADY HERE (E-GAP)` / `NO OBJECT AT UNIT 0 (E-OBJ)` | adding / moving an object: refused |
| E-TYPE, E-LAT, E-RANGE, E-SUM, E-TABLE | (cannot be produced: lists, fixed total, copied table); a loaded track outside the envelope shows `VALUE OUTSIDE THE ORIGINAL RANGE (E-RANGE)` in CHECK | |
| W-DENS | `OVER 31 OBJECTS IN VIEW (W-DENS)` | after adding an object, and in CHECK (all messages are cut to the 40 columns of the hint row; the long forms of the first draft did not fit) |
| W-HILL | `HEIGHT STAYS AT THE TOP LONG (W-HILL)` | CHECK |
| W-CURVE | `VERY LONG TURN (W-CURVE)` | CHECK |
| W-FINISH | `BAR IS FAR FOR THIS SCENERY (W-FINISH)` | the BAR is put more than the base's race length + 500 away, and in CHECK [INFERENCE: time model `trackloader.md` 3.1] |

## 6. Milestones

| # | content | estimate (agent-hours) | main risk |
|---|---|---:|---|
| 1 | design, overlay delivery, the viewer (this note) | done | |
| 2 | editing: lists with live preview, key map of 5.3, undo, encode + store update, new tracks as campaign entries, CHECK (done, section 10) | 22-26 | incremental `expand` speed at 8 MHz; overlay grows to about 20 KB |
| 3 | test drive from the cursor: the editor calls the race `$76f4` itself, ring fast-forward to the cursor (`trackeditor.md` 8), return to the map (done, sections 13-14) | 10 | the fast-forward and the time bar at a mid-track start; `rd_geom` reuse (`clr.b $C0008`) |
| 4 | HD save: `Fcreate / Fwrite / Fclose / Dfree` of `FILES\MSTRACKS.TRK` through the HAGA window (port of Populous 2 part B, the reader is its read half), kill tests | 8-10 | durability, HDDRIVER / ACSI swap range, real hardware |
| 5 | floppy: overlay delivery (section 1), campaign disk write with the game's FDC driver, prompts | 12-16 | blank sectors on disk A, write path of the driver never used by the game [INFERENCE] |

## 7. What milestone 1 built

* `patches/ovl/msedit.s` (the overlay: 8,942 B): track list, stock and straight sources, `parse`, `expand`, the map screen, cursor (segment / object / fine / coarse), zoom and scroll, the menu, the key page. Read-only: nothing writes to the campaign store or to disk.
* `patches/cp_title.s`: menu item, `ed_load`, messages (HD flavour only; blob 3,068 -> 3,352 B inside its gap, payload image unchanged at 55,348 B).
* `tools/msrpatch.py`: `EDBASE / EDWORK / EDVER` equates, `build_overlay()`, `FILES\MSEDIT.OVL` in the HD build, overlay size in `list`.
* Gates: `work/edgate/` (`eg.py` one-boot viewer gate, `cmpmap.py` screenshot vs `msrtrack.py render`, `env.sh`, logs and screenshots).

## 8. Budget

| item | bytes |
|---|---:|
| payload image (HD and floppy) | 55,348 (unchanged; cap 61,440) |
| `cp_title` blob, HD | 3,352 (+284: menu item, `ed_load`, 5 strings); floppy: unchanged |
| `FILES\MSEDIT.OVL` | 8,942 of 65,536 (code and text about 6.9 KB, quarter sine table 2,050 B) |
| RAM above 1 MB used by the viewer | `$130000-$177CFF`: overlay 64 KB reserved, work 228 KB (three 32 KB arrays, lists 32 KB, path 16 KB, sine 10 KB, screen 32 KB) |
| RAM below 1 MB | none beyond the 284 B stub; 1 MB machines: no site applied, no file read |

## 9. Gates of milestone 1 [obs] (`work/edgate/chain.sh`; raw: `work/edgate/logs/chain.out`, `view_*.txt`, `abs1m_ste.txt`; screenshots `work/edgate/logs/shots/` (git-ignored PNGs))

Fresh `msrpatch.py build --out /tmp/msred/hd` of the final source, Hatari 2.6.1, private `HOME=/tmp/msred_home`, one Hatari at a time, emulated sound on (`--sound 50066`), cold boots, every key a real IKBD scancode (`hatari-event keypress 0xNN`), the campaign `work/camphd/camp/c3.trk` (3 custom tracks, BAR at unit 700-900) copied to `FILES\MSTRACKS.TRK`.

`eg.py`, one boot per cell: title, F10, LOAD CAMPAIGN FROM HARD DISK, TRACK EDITOR (overlay read, RAM == the file, `V_EDOK`, video base `$170000`), then per track: the model in RAM against `tools/msrtrack.py` (segment list == union of the four streams; object list with the BAR flag; height / left / right arrays == `expand_hill` / `expand_width` over the whole extent; path points == a Python model of the fixed-point code; deviation from the float path of `render_png`), RIGHT segment by segment to the last segment (sampled every 20 keys: segment number and unit must be exact), LEFT, CLR/HOME, B, zoom 1 -> 4 -> 1, the objects row, ESC; a plain straight; HELP; FIRE menu; back to the campaign menu (video base and palette as before, no Bus/Address error line added while the editor was open); then the loaded campaign is played: race 1 to the BAR, the shop left with the real EXIT click, race 2 starts on base level 3 and the car moves.

| cell | tracks viewed (walked to the last segment) | result |
|---|---|---|
| STE TOS 1.62, 2 MB | campaign track 1 (404 of 406 segments start inside the extent), stock tracks 1, 8, 15 (396 / 337 / 351), plain straight | ALL CHECKS PASS (100) |
| Mega STE TOS 2.06, 2 MB | campaign track 1, stock track 8, plain straight | ALL CHECKS PASS (62) |
| ST TOS 1.04, 2 MB | campaign track 1, stock track 8, plain straight | ALL CHECKS PASS (62) |

Numbers (identical on the three machines for the tracks they share): segment lists of 406 (campaign track 1), 398, 337 and 351 segments (stock tracks 1, 8, 15) equal to the model, 0 differing bytes in the three per-unit arrays over 20,496 / 20,496 / 21,024 / 24,024 units, 0 differing path points; the editor's path stays within 16.6 units of the PC tool's float path = **0.26 map pixels** (track 1; 0.16 px for tracks 8 and 15). The overlay (8,942 B, md5 `16f4d2db...`) was in RAM and accepted 188 VBL after RETURN on the STE (wait included). A stock track is on screen 138-161 VBL after RETURN (this includes the game's file service read and the script's 0.3 s polling; `expand` alone was not timed). Bus/Address error lines of the whole run: STE 3, Mega STE 0, ST 5 = the v1.1 baselines of `work/campgate/RESULTS.md`; none appeared between opening and leaving the editor.

`cmpmap.py` (screenshot of the viewer at zoom 1 against the PNG of `msrtrack.py render`; both path pixel sets aligned by their bounding boxes, nearest-pixel distance both ways, in ST pixels; pass = max <= 3, 99 % <= 2, same aspect):
```
view_ste2m_camp1   vs render c3.trk entry 0: editor->PNG mean 0.28 p99 0.86 max 0.99 px; PNG->editor mean 0.41 p99 0.88 max 1.23 px: MATCH
view_ste2m_stock0  vs render 0:              editor->PNG mean 0.40 p99 1.09 max 1.15 px; PNG->editor mean 0.48 p99 1.04 max 1.28 px: MATCH
view_ste2m_stock7  vs render 7:              editor->PNG mean 0.38 p99 1.06 max 1.15 px; PNG->editor mean 0.43 p99 0.89 max 1.20 px: MATCH
view_ste2m_stock14 vs render 14:             editor->PNG mean 0.54 p99 1.40 max 1.55 px; PNG->editor mean 0.59 p99 1.42 max 1.50 px: MATCH
Mega STE and ST (camp1, stock7): the same eight numbers as the STE lines, MATCH
negative control, view_ste2m_stock7 vs render 14: editor->PNG mean 6.52 p99 28.49 max 31.33 px: MISMATCH
```
Side-by-side pictures: `shots/cmp_<cell>_<track>.png`.

**1 MB (STE, `abs1m.py`)**: `RUNME.TOS` (73,107 B, md5 `e8ce2f61...`) differs from the shipped v1.1 file in 3,003 bytes, all at payload addresses `$B9F90..$BAC15` = inside `cp_title`'s blob `$B9F00-$BAC17`; HAGA, MS1, MS2, MSR_S1.FIC identical; cold boot: marker `MSPO`, `IB+4 = 0`, the seven campaign sites hold the stock bytes, F10 starts the game like any key, a race runs, an execution breakpoint over the whole `cp_title` blob never fires, and no GEMDOS call names `MSEDIT.OVL` (`--trace gemdos`, 111 trace lines): ALL CHECKS PASS (12).

**Floppy build**: `build --floppy` gives `disk_a.st` md5 `81e2a7b7b2a096000123372cb0f0327e` and `disk_b.st` `0d0be455e4d0389ed98401c0e02d21d9` = the shipped v1.1 images: the editor is absent there by construction (no menu item, no code, no file).

Not run: Mega ST, the 4 MB cells, TT / Falcon (the gate is v1.1's, unchanged), a missing or damaged `MSEDIT.OVL` (the two messages were not provoked), F10 from the hi-score screen, real hardware. Stock tracks other than 1, 8, 15 were not opened in the game (the Python model of the segment rule covers all 15, section 4).

Known limits of the viewer: at zoom 1 the strips use 128 units per column, so a 20,496-unit extent fills 160 of the 256 columns; the viewer menu and the key page replace the map while open; the object row shows type numbers, no sprite thumbnails; a copy or a straight is not kept when the viewer is left (keeping is milestone 2).

Harness finding: `hatari-event keypress N` takes a ONE-character argument as an ASCII character (`control.c`), so `keypress 1` types the key `1`, not Esc; scancodes below 10 must be sent as `0x01`. (`work/campgate/cg.py` sends `key(1)` for Esc in one place: that key never was Esc.)

Seen on the way, v1.1 behaviour, not changed: in the Mega STE run the campaign menu itself was shown in the title's blue-grey palette (`shots/view_mste2m_0_menu.png`, palette registers `0000 0777 0777 0455 ...` instead of the menu's) before the editor was ever opened [INFERENCE: F10 landed in a title fade whose VBL steps then overwrote the palette `cp_menu` had set]. The editor showed its own colours there and gave the same registers back.

## 10. What milestone 2 built (EDITING, in RAM; MSREditor2, 2026-11-21)

`patches/ovl/msedit.s` (overlay interface version `EDVER` 2, about 19.2 KB; payload image unchanged at 55,348 B), `patches/cp_title.s` (the editor now returns d0 = 0 back / n = play track n-1; the menu starts that race: `V_START`, `V_ACT`), `tools/msrpatch.py` (`EDVER` 2).

**Where the design was kept, where the implementation differs**
* Model and rules as section 4: one segment list (12 B per segment), one object list, type table copied verbatim (now into `TYPS` when a track is loaded, so a campaign block can be replaced while its own types are still needed), total length fixed (the last segment, the padding behind the finish, absorbs every length change: it must keep 16 units, else `NO ROAD LEFT: LENGTH IS FIXED (E-SUM)`), objects behind an edited stretch move with their road, objects inside a removed stretch go to its end and an object that would meet its predecessor moves one unit on (`obj_norm`; first object >= 1, last <= 32767, else `OBJECTS WOULD PASS THE END OF THE ROAD`).
* **E-HILL is checked on the whole stream**, as `msrtrack.py validate` does (32-bit slope / height integrator over all 32,768 units, `hill_ovf`), after every edit that can change it: hill shape, raw accel, **length, insert, delete, merge** (lengthening or removing one half of a rise leaves the slope running to the end of the stream: the first gate run produced exactly that and the check page and `Esc` refused it). Refused edits restore the history entry and show `HILL TOO STEEP: OVERFLOW (E-HILL)`.
* **Hill shapes** (`FLAT`, `RISE`/`DROP` small / medium / big, `CREST`/`DIP` small / medium / big, `RAW ACCEL...`): a rise of height `h` = 8 / 20 / 40 height units over a segment of length L is `+a` for n = L/2 units, a flat piece for the odd unit, `-a` for n units, `a = h * 65536 / n^2` (clamped 1..4000), so the slope ends where it began; crest / dip = `+a n, -a 2n, +a n` with n = L/4 and a flat piece for the remainder in the middle. Neighbouring pieces with the same accel are joined; the segment becomes 2..5 segments. `RAW ACCEL...` opens the numeric list (presets -3000..4000 and exact values).
* **Lists with live preview** are as 5.2 describes: the right 12 columns of rows 1..21 (the map is refitted into the left 224 pixels, `map_fit`), a white bar on the selection, heading with the value, up / down (wrap), the last item is `< BACK`; the numeric lists (length, widths, side, raw accel) take left / right = exact +-1 (fire or Control +-10, Shift +-100) and show the value in the heading; fire acts on RELEASE (so fire + direction is not an accept); joystick LEFT = back only in lists without exact values (there: Esc, Backspace, F10 or the `< BACK` item). Every list is applied to the history entry's copy (`hist_cur` + `apply`), re-expanded and drawn into the hidden screen, flipped in at the next vertical sync (`SCR` / `SCR2`, no flicker). The preview runs when no key arrived in that poll: **it takes about 1 to 1.5 s on a stock-length track** (incremental `expand` from the segment on, up to the extent of about 20,000 units, plus the full redraw), and keys that arrive while it runs are lost (the game's key latch holds one make per key): hold-free stepping works, fast repeats do not [obs: gate]. The object TYPE list is a full-screen scrolling list of the base level's own types (`nnn KIND k SIZE s SPRITE nnn`, the BAR type is not offered) without preview.
* **Incremental expand**: the start state of every segment is kept in `CKPT`; an edit at segment k re-expands from k only. Changes of the extent (the BAR moved) re-expand from the segment that holds the old end.
* **Undo / redo** (`U`, Undo, menu; Shift + `U` = redo): the history ring in `$178000-$19FFFF`; every accepted edit pushes the whole working copy (segments, objects, cursor); `hist_cur` (the base of every preview and of every refused edit) keeps the cursor where it is, undo / redo restore the cursor stored with the entry.
* **Repeat** (Return, Enter, Space): the last accepted pick (curve, hill shape, length, width, raw accel, object type, side) is applied again at the cursor segment / object; the road acts need the road row, the object acts the objects row (`THAT VALUE IS FOR THE OTHER ROW (TAB)`). `,` / `.` bend the segment one step left / right without a list and count as the last pick.
* **Menu** (fire tap): the road row's or the objects row's edit items, then undo, redo, check, zoom, row switch, keys, back, leave; every item shows its key. New keys: `M` merge with the next segment (objects row: MOVE THIS OBJECT: left / right = 10 units, fine = 1, Shift = 100, FIRE / Return keep, Esc back), `K` check page, Insert / `I`, Delete, `S`, `T`, `W` / `E`, `C`, `H`, `L`, Shift + `B`.
* **Objects**: `I` adds an object of the last picked type (first type that is not the BAR until a type was picked) and side at the cursor unit (fine-move to a free unit first; an occupied unit gives `AN OBJECT IS ALREADY HERE (E-GAP)`, unit 0 `NO OBJECT AT UNIT 0 (E-OBJ)`), `W-DENS` is reported after the add; Delete never removes the BAR (`THE BAR CANNOT BE DELETED (E-BAR)`), Shift + `B` (menu: PUT THE BAR HERE) moves the BAR to the cursor unit of the road row (removing any other BAR object, so it also repairs a loaded track with none or several), the BAR's type cannot be changed.
* **Leaving** (Esc / F10 on the map): `check_all` runs (E-BAR none / several, E-HILL, E-SIZE >8192 B block block the keep; a loaded value outside the stock envelope is only flagged, `E-RANGE`, and kept until changed; W-DENS / W-HILL / W-CURVE / W-FINISH are listed). A blocked keep shows the reason (`... ESC AGAIN = DISCARD`); the second Esc discards the working copy. A clean track is encoded to the native six streams (`encode`: runs of equal values per stream, objects with gaps, the verbatim type table, end word: the bytes of `msrtrack.encode_track`) and the campaign file in memory (`$110000`) is rebuilt by `store_rebuild`: header, entry table (offsets, lengths, block CRC-32, table CRC-32, count) and blocks in `ARENA`, copied back, so the store is always a valid `MSTRACKS.TRK` and is exactly what the races play (`cp_fetch`). A campaign track replaces its entry; a copy of an original track or a plain straight is appended (a campaign is created when none is loaded; at 15 tracks `CAMPAIGN FULL: 15 TRACKS (E-CAMP)`); an unchanged campaign track is not rewritten.
* **Track list**: a campaign track opens `EDIT THIS TRACK / PLAY THIS TRACK / DELETE THIS TRACK / < BACK`; PLAY leaves the editor and the F10 menu starts the normal race on that track (`V_START` = its position, `V_ACT` set: the same as `PLAY FROM TRACK N`); DELETE (with confirmation, not the last track) rebuilds the file. Not built: rename, move up / down, copy (section 5.1); `TRACK >` NAME / SCENERY (a new track is called `COPY OF TRACK nn` / `NEW STRAIGHT`).
* **Messages** are cut to the 40 columns of the hint row (5.4 table updated); the check page (`K`) lists them in red (blocking / flagged) and yellow (warnings) with the segment, object and byte counts.
* RAM: section 2 (the overlay's `BLK` moved to `$141000`, the variables are 4 KB).

**Known limits**: the live preview takes roughly 1 to 1.5 s on a stock-length track at 8 MHz [INFERENCE from the gate's waits, not timed] (a longer track or an early segment costs more, the extent is the whole race); `W-CURVE` uses a segment's end values (the extremes of an arithmetic progression) and ignores 16-bit wrap; an object moved near unit 32767 compares as a signed word; the history ring holds about 18 steps of a stock track; no floppy build (the item does not exist there; the floppy build shows the F10 menu without the item); no save to disk (milestone 4).  **Superseded for speed by section 12.**

## 11. Gates of milestone 2 [obs] (`work/edgate/ed2.py`, `ed2lib.py`, `ed2model.py`, `env2.sh`; raw `work/edgate/logs2/`, shots `logs2/shots/`; build `/tmp/msred2/hd`)

`ed2model.py` is a Python model of the editing rules (segment list, objects, `road_shift`, hill shapes, undo) that encodes with `msrtrack.encode_track`; `ed2.py` drives the editor with real input (cursor / letter keys via `hatari-event keypress`, joystick = writes of `$6105`: fine moves, menu, fire-release accepts) on the STE 2 MB HD build and compares the editor's RAM after every group of edits with the model.

**STE TOS 1.62, 2 MB, campaign `c3.trk`, copy of TRACK 04, 88 edits through the UI** (5 splits, 7 curves incl. a Return repeat, 6 hill edits incl. a raw accel and a repeat, 5 lengths (preset, exact +3, joystick accept), 5 widths, 5 copies, 5 deletes, 5 merges, 5 object adds, 5 types, 5 sides, 5 moves, 5 object deletes, 5 BAR moves via the menu, 3 undos, 2 redos (menu), FLAT + 14 Return repeats): **36 checks PASS, 1 FAIL**. Passing: the segment and object lists in RAM equal the model after every group (2 edits were refused identically by editor and model: `E-HILL` on an insert and a merge); the block kept in the campaign file in memory equals `encode_track(model)` byte for byte; `msrtrack.py validate` of the file dumped from RAM: 4 tracks, 0 errors (one W-HILL warning: the stock hills of the rest of the track sit at the clamp after the first edits left a slope); the three campaign tracks before it unchanged; re-entering the kept track shows the edits (merged segment list == model); invalid edits: BAR delete refused (`THE BAR CANNOT BE DELETED (E-BAR)`, nothing changed), width 86 refused (`OUTSIDE THE ORIGINAL RANGE (E-RANGE)`, list refuses to close, 85 accepted again, Esc changes nothing), raw accel 4000 on a 2000-unit segment refused (`HILL TOO STEEP: OVERFLOW (E-HILL)`), the check page shows no blocking error on the final track and an earlier run showed `E-HILL` + `W-HILL` on a track the script had made overflow (Esc refused the keep: `ESC AGAIN = DISCARD`).

**Not closed**: the race check FAILED: after PLAY THIS TRACK the editor handed over `vPlay` = 4 and the menu set `V_START` / `CPV+4` / `$102c` to 3 (smoke runs, `$102c = 3`), but the harness's `play_races` then observed a race of campaign track 0 (`ptr` = entry 0, `$102c = 0`); the same happened when the saved file was loaded as an ordinary campaign and played with the harness (`work/edgate/smoke8.py`), so this is [INFERENCE] a harness / start-screen sequencing problem (the first screen after the start waits for a key and the harness's SPACE presses start a new game from the title), not shown to be an editor fault, but it is NOT proven: a race on the edited track was not observed. Also not run: the plain-straight cell (the script exists, `--kind straight`), the Mega STE and ST quick cells (`--quick`), the 1 MB absence check (`abs1m.py` against the new build), the budget table of the final numbers. Floppy build: `disk_a.st` md5 `81e2a7b7...` and `disk_b.st` `0d0be455...` = the shipped v1.1 images [obs]. Sizes: overlay 19,240 B, `cp_title` blob 3,372 B (+20), payload 55,348 B unchanged.

## 12. Milestone 2b: key queue, deferred redraw, closed-form expand, welcome-screen F10 (MSREditor3 / MSREditor4, 2026-11-22) [obs]

Results table and raw logs: `work/edgate/RESULTS_m2.md`, `work/edgate/logs4/`.

**Responsiveness (`patches/ovl/msedit.s`).** The first milestone-2 build recomputed and redrew after every key, 0.9 to 1.8 s per bend step on a stock track, and keys pressed meanwhile were lost or applied late. Now:
* **Key queue**: an IKBD hook (`kbhook`, vector `$118`, a 64-entry ring; `kq_pop`, `kq_popn`, `kq_arrow`) is installed on entry and re-installed after `rd_stock` (the game's own reader replaces `$118`); every key and the joystick-as-cursor taps (`poll_dirs`) come from the queue, so typed-ahead input is not lost (`C DOWN DOWN DOWN RETURN` works).
* **Deferred refresh**: an edit only marks work pending (`refresh` -> `vPend / vPD / vPM`); the view loop and the list loop run the recompute and the redraw (`flush_pend`) only when no key is waiting, so a burst of N bend keys is N applied steps (undo history, model) and ONE recompute/redraw. List rows are redrawn only when no key waits (`vLRd`); the live preview of a list runs for the value the selection ended on.
* **Cheaper recompute**: `expand_from(d0 = first segment, d1 = pass mask)` is split into the passes `xp_hill`, `xp_width` (with an early stop once the stored state matches, bit 3) and `xp_path` (closed-form 8-unit runs, register accumulators); each act runs only the passes it changes (`vXm`, set in `apply` / `act_mask`); `vline` and `cls` are faster; `path()` strides at small map scales and skips repeated pixels.
* Arrays after every edit class == the full reference expansion (`ed3.py`, 8 classes + burst: PASS).

**Welcome-screen F10 (user requirement 5.1).** `patches/cp_welcome.s` (`; gate: ram2mb`) patches `$7c04` (`tst.b $60ff.w / beq.b $7c02`, the key wait of the first screen of the manual-question routine `$7bd0`) to `jmp $B9F0C.l`, third entry of cp_title's jump table = `e3`: first pass per showing draws `F10 = CAMPAIGNS` (`t_whint`, text row 23, `V_WELC` = CPV+13 set), F10 opens `cp_menu` (not while the screen is still fading in, `$3a88`), a start from the menu continues as a key (`$7c0a`), BACK / Esc shows the screen again (`$7bd0`, hint redrawn), any other key = stock exit. 1 MB: the site is not patched (list 2 closed), the screen is byte for byte the stock one. **Floppy**: the site is in the floppy build too (the table is the same) but the floppy flow never reaches this screen (a 200 s unattended boot of disk A: only the intro / hi-score loop, `V_WELC` never set), so there is no hint there; F10 at the floppy title opens the menu as before, without the editor item (HD only).

**Test-harness lessons (all settled, none a product fault):** the earlier 'PLAY races track 0' was the harness (SPACE presses at the start screens start a new game); the race criterion for an edited road is `$23c0 != 0 and $1024 == 0` (`$100e > 30` is not true on a short-lived edited road); `V_START` is consumed by the menu at once, so a gate must not read it after PLAY.

## 13. Milestone 3 (design, written BEFORE the code): TEST DRIVE FROM THE CURSOR (MSREditor5, 2026-11-22)

Facts used: `trackeditor.md` 4 / 8 (re-init sequence, ring updaters, the playtest sketch), `trackloader.md` 3 (finish rule), 4 (wrapper), 6 (`rd_geom` reuse); disassembly of `work/dumps/ram_race_start.bin` (`$76f4` race = setup `$7700-$7926` + loop `$7a88-$7bac` + `rts` at `$7b70`; campaign loop `$7242-$7356`; `$e1e4 / $e218 / $e2e8` objects; `$fd64` speech; `$ee64` time bar; `$11792` bar update; `$7970` F10 abort).

**13.1 How the editor starts a race (decision: a subroutine call, no round trip through the title).** The whole race is ONE routine, `jsr $76f4` (setup, loop and exit, it returns with `rts` when `$1024` goes negative). The editor already runs in supervisor mode on the title's stack with the game's VBL running, so a test drive is `jsr $76f4` called FROM the editor, with the same preparations the campaign loop does just before `$72c4` (`$726c-$72c0`: `$1026 = 0`, `$1021 = $1023` sound mode, `$1020` music enable, the tier byte `$1029`, `$102c := the track's BASE level` as cp_wrap does, `$1028 = $ff` race flag) and the same clean-up after it (`$72ca-$72e4`: `$91f0 = 0`, `$1028 = 0`, fade to black `$d82c`, `$d770` sound reset). Nothing returns through the title, so there is no shop, no `$102c` advance, no map screens, no hi-score: when `$76f4` returns the editor is where it was (the cursor, the working copy and the undo history are the overlay's own variables in `$140000+`, which no race touches). Rejected: ending the race by the campaign loop (`$7306` would run the shop / next level / hi-score; getting back to the editor would need a new title entry and the whole title fade-in).
* The track: the working copy is encoded (`encode`, the bytes `msrtrack.encode_track` writes) into ENCBUF (`$1B0000`) and `PTR` (CPV+8, read by cp_ptr's `$fda2`) = ENCBUF; `hookb` (cp_fetch) gets a first test `tst.b CPV+14 (V_TD)`: when set it does not touch PTR and does not load the stock block, it continues at `$77e6`. The rest of the setup (base-level scenery, colours, sky, object frames, `$57890` race length, opponents, speech table, all via `$102c = base`) is the unchanged campaign path, so a test drive looks exactly like the same track in a campaign race. The editor's block never needs to be written to the store: an unkept edit is test-driven as it is and stays unkept.
* Sound / screen / input hand-over: the editor fades its screen to black through the game's own fade (`$d866`, waits `$3a88`), takes its IKBD hook off (`$118` = the game's handler; the race needs `$60ff` for F1 and the game's own reader), saves `$1004 / $1008` (the two screen pointers the race flips), `$102c`, `$1021`, `$1020`, `$1027`, calls the race, then restores all of them, re-arms its screen (base registers, palette), restarts the title tune (`$8bb6` + `$8380` as the title init `$722c-$7236` does), re-installs the key hook, clears the key queue and waits for fire to be released, and redraws. Not restored because nothing needs it: the game's two screens (`$70000 / $78000`: the race overwrote them; the menu that follows clears both with `$d8e0` and redraws), the race score variables (`$11c2 $176ac-$176b4 $17514`: `$73b8` zeroes them at every game start).

**13.2 The cursor unit -> the race start (fast-forward).** The race state that depends on the position is only: the four rings (curve `$1bbc`, widths `$13b0 / $17b0`, hill `$23c8`, each a 1024-entry circular buffer with its head and integrator state), the object slots + counter `$1346` + stream pointer `$133a`, the speech pointer `$12a4`, the distance `$5ff8` (readers: `$fbbc`, `$fd64`, `$f2de`) and the time bar. New patch `cp_td` (HD, `; gate: ram2mb`) at `$7926` = the call of `$edea` (the LAST step of the setup, after the rings, the objects and the bar were initialised for unit 0): `jsr hooktd` = `jsr $edea / tst.b V_TD / beq / jsr EDBASE+20 (td_ff)`. `td_ff` (in the overlay: no payload bytes) does, for N = the cursor unit:
1. `clr.b $C0008.l` (`rd_geom` standing-frame reuse off: `trackloader.md` 6; the key holds the six stream pointers, which a fast-forward changes anyway, but the invalidation is the documented safe form).
2. Fast-forward by driving the game's own updaters with `$130c` = k in chunks k <= 1023 (the ring updaters' limit) until N units are done: `$e2e8` (object mover: objects that fell behind are freed), `$e218` (spawner: counter and stream pointer advance, new objects enter at `$20 = position - camera`), then `$fe50 $ff76 $1003c` (left width, curve, hill rings). Order is MOVE then SPAWN: in the race loop the order is spawn then move, which is exact for k = 10 but would place objects spawned in the chunk k units too near for k = 1023. Result = the state after really driving N units standing at the grid speed profile of the game's own loop, [INFERENCE until the gate: ring contents == the PC model's expansion of the block at unit N..N+1023].
3. `$5ff8 = N`; `$12a4` advanced over the speech entries (distance + `$320`) that lie below N, otherwise the first ones would all be said at the start.
4. The time bar (13.4).
5. Installs the two test-drive hooks (13.5): they must come after the setup because every `$d6fa` call goes through HAGA, whose TOS window swaps the vectors.
The camera/888-unit view needs nothing else: the rings hold units N..N+1023, the road code reads the rings relative to the head, objects are relative to the camera. The BAR stays at its ABSOLUTE position: it is an ordinary object of the stream, spawned when it enters the 1023-unit window; only the remaining distance BAR - N is driven. A cursor beyond the BAR (N > BAR position) is refused with a message (the BAR would already be behind the camera: no finish possible); a track without a BAR can be test-driven (ends by time-out / F10).

**13.3 Objects and opponents before the start point.** Scenery objects (and the BAR when it is behind) before N do not exist: the mover frees them during the fast-forward, nothing is collided with. The three opponent cars and the fourth slot (`$e0a2`, positions relative to the player, the fourth from the per-level table `$e14a`) are placed exactly as at the grid of a normal race: the pack stands around / ahead of the player at the cursor and the AI steers it by the curve ring (`$1182e`), i.e. a rolling "grid at the cursor". (The game has no absolute opponent positions: `$5ff8` is not read by the car code.) The player starts standing (speed 0), as at every race start.

**13.4 The time bar.** Options: (a) the stock bar (`$10ce = 0`): the player would have the whole race's time for a short remainder, a time-out can never be tested; (b) scale `$10ce` / `$10d2` by remaining / race length; (c) a generous fixed bar. Pick: the bar keeps its STOCK RATE `$10d2` (the base level's difficulty; the clock hand moves as in a race) and its START is set so that the time left is **2 x the remaining distance at full speed + 10 s**, never more than the stock bar: R = max(0, BAR - 500 - N) (the chase starts 500 before the BAR: `trackloader.md` 3.2; without a BAR R = 0 ... the stock bar), passes P = R / 10 * 2 + 100 (10 units per pass at full speed, 10 passes per second at the game's pace), `$10ce = max(0, $ff0000 - P * $10d2)`. Justification: (b) with the race length as denominator would give the player almost no time near the BAR (the remaining fraction of a 20,000-unit bar for a 1,000-unit remainder is 1,000/20,000 of the allowance = about 8 s at best from a standing start, and a start 600 units before the BAR would time out before the car moves) and (c) would hide that an edited track is too long for its base level's time; this rule keeps the stock rate and the "behind schedule" comments of `$fbbc` quiet, always allows the BAR to be reached at normal driving, and still lets a time-out happen (stand still, or drive a quarter of the speed) so it can be tested; a start at unit 0 on a long track simply gets the stock bar (the clamp), exactly as the campaign race would.

**13.5 How a test drive ends and returns.** (a) The BAR: the game's own finish (within 500 units the game takes the car over and stops it at the BAR, `$1024` = 1, then 2 = reached). (b) Time-out: `$11792` sets `$1226 = 5`, the message, then `$1024 = $ff` (and `$102c |= $80`, `$1027++`: both restored by the editor, so a time-out never counts as a lost game). (c) F10: the race loop already aborts on it (`$7970`: `tst.b $6042` -> `$1024 = $ff`, `rts`). (d) **Esc** has no stock meaning in the race: a tiny IKBD wrapper (`tdkb`, installed by `td_ff`, chains the game's handler, then turns a make code `$01` into the F10 hold byte `$6042 = $ff`) makes it end the race the same way. (e) A short VBL wrapper (`tdvbl`, same installation) counts frames once the race is decided (`$1024 >= 2`, or the time-out message `$1226 = 5`) and after 75 frames (1.5 s: the stop at the BAR / the time-out text stay visible) sets `$6042` too, so the 10 s closing message sequence, score count and place text (which a test drive does not need) are skipped. A crash does not end a race in this game: the engine burn (temperature 35) resets the car inside the race; not changed [INFERENCE: not traced]. Nothing is written to the hi-score table or the campaign state, no shop is shown, the campaign position / `$102c` / `$1027` are put back.

**13.6 The key.** Key map (5.3): **`P` = TEST DRIVE FROM THE CURSOR** (road row and objects row; menu item `TEST DRIVE FROM THE CURSOR  P` in both menus; the key page line `P  TEST DRIVE FROM THE CURSOR`). The cursor unit is `vPos` (an object cursor sits on the object's unit). PLAY THIS TRACK in the track list (a full race from the start through the campaign) stays as it is. The block that is driven is the working copy as it is NOW (`encode`), kept or not.

**13.7 What is restored on return:** screen (shifter base = the editor's `vShow`, palette = the editor's), the game's pointers `$1004 / $1008` and bytes `$102c $1021 $1020 $1027 $1028`, the IKBD vector (the editor's `kbhook`; the test-drive wrapper is removed), the VBL vector (the game's handler), the F10 hold byte `$6042`, the key queue, the joystick latch; V_TD cleared; the title tune restarted. Machine gate as the editor: HD build, ST family with 2 MB or more. 1 MB: no site applied (cp_td is `; gate: ram2mb`), nothing runs.

## 14. What milestone 3 built (MSREditor5, 2026-11-22) [obs] (results: `work/edgate/RESULTS_m3.md`, raw `work/edgate/logs5/`)

Built as designed in 13, with these differences found while running it:
* **Files**: `patches/cp_td.s` (new, `; media: hd`, `; gate: ram2mb`, site `$7926`, hook `hooktd` at `$B8260`: 22 B), `patches/cp_fetch.s` (hookb: `tst.b CPV+14 / bne .td` first, +8 B), `patches/ovl/msedit.s` (EDVER 3: `bra.w ed_main` at +16, `bra.w td_ff` at +20; `c_td`, `td_ff`, `tdkb`, `tdvbl`, key `P` = command 26, menu item in both menus, key page line, texts; the pick list's message row moved from 22 to 23 because the road menu now has 20 items), `tools/msrpatch.py` (`EDVER` 3), `patches/cp_title.s` + `patches/cp_flhint.s` (step 2), `patches/README.md`. Payload image size unchanged.
* **td_ff keeps its counters in memory**: the game's ring updaters and `$e218` use every data register (the first run left `$5ff8 = $ffff`: d7 was the loop counter of `$fe50`).
* **tdkb** makes Esc AND F10 sticky through a flag (`vTdKill`) re-asserted after every IKBD byte: the race loop polls `$6042` only once per pass (10 per second) and the BREAK code of a real F10 clears it again within a few ms, so the stock F10 abort missed a quick tap (observed: the first F10 test did not return until the bar ran out, 150 s).
* **tdvbl** records why the race ended in `vTdWhy` (1 = the BAR was reached, 2 = time-out, 0 = F10 / Esc / crashes), read by the gate. 75 frames after the decision the drive is cut: measured 1.6 s from the key press to the editor for Esc / F10.
* The fast-forward is exact: after `P` the four rings of the game (read back from RAM) equal, entry for entry, the expansion of the block the editor encoded (`msrtrack.expand_curve / expand_width / expand_hill` at units N..N+1023 through the rings' head indices), and the 32 object slots equal the objects of the window [N, N+1023] (distance relative to the camera, lateral): 0 mismatches at N = 0, 9054, 17789, 18553 (RESULTS_m3.md).
* Not changed: PLAY THIS TRACK (track list) and the campaign flow; the F10 hook `$7970` of the stock race loop.

**Floppy (step 2)**: the floppy flow never shows the WELCOME PARTNERS screen, so `cp_flhint` (`; media: floppy`, `; gate: ram2mb`, site `$7446`) draws the same `F10 = CAMPAIGNS` line (`t_whint`, cp_title's new jump-table entry `e4` at `$B9F12`) at the start of every message of the title's face / typed-text loop, on both screens (the loop clears both from line 64 down between two messages: a hint drawn once, before the loop, vanished after the first message in the first try). cp_title's table now has four entries; `abs1m.py` anchors on `$B9F18` and allows the hook blobs of cp_fetch / cp_td.


## 15. MAIN-VIEW REDESIGN: the TILE GRID (MSREditor6, 2026-11-23; written BEFORE the code; supersedes 5.2 and the map / strip / zoom / fine / coarse rows of 5.3)

**Why.** The user tried the milestone 3 preview: 'really struggling to use this. It's very hard to know what you're doing in terms of which segment you're editing'; 'we've gone complicated but not really benefitted from it'. The top-down map plus three strips showed the whole track but never said WHICH segment the cursor was on, and every edit needed a "fine move" to a unit inside the segment. Bar: the Nebulus editor (a grid of cells, an obvious cursor, details as text). **User decisions (fixed):** the main view is a grid of tiles, one per segment, in driving order; direction as a symbol, hill as colour, a dot for objects, a chequered tile for the BAR, a bright frame on the selected tile; a text panel underneath; the map and the strips are DROPPED; objects are edited from the selected segment's object list; editing keys, pick lists, Return / Space repeat, undo / redo, test drive and validation stay.

### 15.1 The screen (320 x 200, low resolution, own 16 colours; text = the game's 8 x 8 font, 40 x 25 cells)
```
text row 0     C01 TRACK NAME                      SCENERY 04*     source, name, base level, * = changed
y 9..104       8 rows x 16 tiles; label column (text cols 0-3) = the number of the first segment of the row; tiles from x = 32
text rows 13-23  the PANEL (left 28 columns: segment details and its object list); right 12 columns: key reminder, or a pick list's box
text row 24    hint row (a message once, yellow, else the keys)
```
**Tile = 16 x 12 pixels** (one 16-pixel word per bitplane: a tile is 12 rows x 4 words, no masks): a 15 x 11 coloured area, a black gap column and row; pitch 16 x 12, so the grid is 256 x 96 pixels at x 32..287, y 9..104. 16 x 8 = 128 tiles on the screen; the tile at row r, column c is segment `vFirst + 16 r + c`; `vFirst` is always a multiple of 16. Row labels are drawn with a pixel-row text call (rows 11 + 12 r), the cursor's row in yellow, the others grey.

**What a tile shows is what the player SEES, not the raw field.** A segment stores a curve DELTA (the road direction `c` changes by it every unit) and a hill ACCEL (the slope changes by it), so a segment with `curve = 0` in the middle of a long right turn is still turning. Showing the delta would show 'straight' there (stock segments are 20..50 units long; `c` reaches -4473..8876 only by summing many deltas) [obs: `/tmp/cstat.py`-style run over the 15 stock tracks, medians 20..50 units per segment, `c` at the segment middle 570..2450 at the median]. The editor therefore integrates along the track in one pass (`tiles_calc`, 16-bit wrap for `c` like the game, 32-bit slope) and classifies the VALUE AT THE MIDDLE of each segment:

| symbol (11 x 7 pixels, black on the tile colour) | meaning | `|c|` at the middle |
|---|---|---|
| vertical bar | STRAIGHT | < 300 |
| bar leaning 27 degrees, 45 degrees, 63 degrees to the left / right | GENTLE, MEDIUM, SHARP left / right | < 1200, < 2400, >= 2400 (sign = side) |

| tile colour | meaning | slope at the middle (height units per unit, `|s|` = 1.0 at 65536) |
|---|---|---|
| green | LEVEL | < 0.02 |
| yellow / red | RISE SMALL / RISE BIG (climbing) | < 0.10 / >= 0.10 |
| light blue / blue | DROP SMALL / DROP BIG (dropping) | < 0.10 / >= 0.10 |

Thresholds chosen on the 15 stock tracks (4,630 segments: straight 746, gentle 2,113, medium 1,190, sharp 581; level 2,411, rise 849 / 303, drop 742 / 325 at 300 / 1200 / 2400 and 0.02 / 0.10 [obs, same run]). Heights clamp at 0..127 in the game; a segment that pushes against the clamp is still drawn by its slope [INFERENCE: not worth a second integrator]. The panel gives both views of the segment: the EDITABLE values (CURVE = the delta, HILL = the accel) and what they make (BEND, HILL class), so the numbers and the tile agree.
* **objects**: a 2 x 2 black dot at the top-right corner (x 12-13, y 1-2) when the segment holds an object (not drawn on the BAR tile).
* **the BAR**: a chequered tile (2 x 2 pixel white / black squares) for the segment that holds the BAR object.
* **selected tile**: a 2-pixel frame around the tile, white while the grid has the cursor, YELLOW while the object list of the panel has it; the glyph stays inside the frame.
* beyond the extent (segments that start at or after `vEnd` = max(race length, BAR + 512) + 1024, the part of the stream the race never reaches) no tile is drawn and the cursor cannot go there.
* The legend is on the KEY PAGE: HELP shows page 1 (keys), any key shows page 2 (**WHAT THE TILES MEAN**: the seven symbols and the five colours drawn with the real tile routine, the dot, the chequers, the frame).

### 15.2 Redraw: only what changed
`tiles_calc` (after any edit, undo, redo: one pass over the segments and the object list, about 400 x 100 cycles) fills `TILE[k]` = a word per segment (direction 0..6, hill class 0..4, object flag, BAR flag). The grid keeps a shadow of what each of the 128 screen slots shows (`vShw`: tile word + selection bits); `draw_grid` draws a slot only when its word differs, so a cursor move redraws two tiles, a bend edit redraws the tiles whose class changed, a scroll redraws what moved. The panel (about 12 text rows) is redrawn on every change. No second screen and no page flip any more (`SCR2` is gone): a tile is written as complete words and a text cell as eight complete rows, so nothing is ever half-cleared. The per-unit arrays, the checkpoints and the path (`expand_from`, `xp_hill`, `xp_width`, `xp_path`, `wfill`, `map_fit`, `mapxy`, `path`, `box`, the sine table) are deleted: the preview of a list value is `apply` + `tiles_calc` + `draw_grid` + panel (the old 0.9-1.8 s recompute is gone; what remains is `apply`'s whole-stream hill overflow test for hill / length edits, about 1M cycles).

### 15.3 Scrolling and the cursor on the grid
* **LEFT / RIGHT** = previous / next segment (held = auto-repeat); **UP / DOWN** = one row = 16 segments back / on (stops at the first / last segment of the extent).
* **Scrolling** is by whole rows: when the cursor row is the first or last visible row and more rows exist, the grid scrolls one row so the cursor stays one row from the edge; a jump (Clr/Home, `B`, undo, a list preview that moves the cursor) re-centres the cursor row at row 3.
* **Clr/Home** first segment; **`B`** the segment that holds the BAR.
* The cursor is always a SEGMENT (`vSeg`; `vPos` = its first unit). The old 'fine' (Control + left / right: one strip pixel) and 'coarse' (Shift + left / right: 1000 units) moves and the zoom keys (`+` `-`, FIRE + UP / DOWN) are gone with the strips.

### 15.4 The panel (text rows 13-24; the left 28 columns; the right 12 columns are the key reminder, or the box of an open pick list)
```
13  SEGMENT 0017/0390  AT 12345          number / total, first unit
14  LENGTH 0120                          units
15  CURVE  RIGHT 3                       the segment's delta (STRAIGHT / LEFT n / RIGHT n); what a pick list edits
16  BEND   MEDIUM LEFT                   what the road does here = the tile symbol (STRAIGHT / GENTLE|MEDIUM|SHARP LEFT|RIGHT)
17  HILL   RISE SMALL +0200              the slope class = the tile colour (LEVEL / RISE|DROP SMALL|BIG) and the accel
18  WIDTH  LEFT 36  RIGHT 34
19  OBJECTS 3                            (NONE: O ADDS ONE)
20-23  up to four object lines, the selected one a white bar:   TYPE 026 LEFT 41 AT 12345   /   THE BAR AT 12345
24  hint row: FIRE=MENU RET=REPEAT P=TEST DRIVE HELP=KEYS   (object list: T TYPE S SIDE M MOVE DEL TAB=BACK)
```
Labels are blue-grey, values white; a refused edit or a note is shown once on row 24 in yellow (as before). Longer object lists scroll (`vOTop`); the heading carries the total. The right 12 columns (rows 13-23) show the key reminder of the current focus (grid: `C CURVE H HILL L LENGTH W E WIDTH , . BEND I COPY S SPLIT M MERGE DEL DELETE O OBJECT`; object list: `T TYPE S SIDE M MOVE I O ADD DEL TAB BACK`); an open pick list takes this column (box_clr), so the panel text stays visible and live while the list's selection moves.

### 15.5 The object list of the selected segment (replaces the objects row and its strip)
The objects of the selected segment are those whose unit lies in `[start, start + length)`; `OBJT` is sorted, so they are a contiguous index range (`vOF` = first index, `vON` = count, found by one pass). **Focus**: `vFocus` 0 = the grid has the cursor, 1 = an object of the list has it (`vObj` = its index in `OBJT`; the tile frame turns yellow).
* **Enter the list**: Tab, or joystick FIRE + DOWN, or the menu: the first object of the segment is selected; a segment without objects says `NO OBJECTS HERE: O ADDS ONE`. **Leave**: Tab, FIRE + UP, UP on the first object, LEFT / RIGHT (these also move to the previous / next segment, the focus returns to the grid), the menu.
* **UP / DOWN** inside the list = previous / next object of this segment. Everything that acts on the object uses the selection: `T` TYPE list, `S` SIDE list, `M` MOVE, Delete, `I` or `O` ADD, Return / Space repeat the last picked TYPE or SIDE. Road edits (`C H L W E , .`, hill shapes, length) also work with the list focused: they act on the selected segment.
* **`O` = ADD AN OBJECT** from either focus (the menu has it too): a new object of the last picked type (the first type that is not the BAR until one was picked) and side, in the selected segment, in the list, selected. **Where**: `pick_unit`: candidate = the selected object's unit + 1 (list focus; the segment start when that is past the end) or the middle of the segment, `start + length / 2` (grid focus); scanning up to the segment's last unit, then from its start, the first unit that is not 0 and holds no object; none free = `AN OBJECT IS ALREADY HERE (E-GAP)`. `W-DENS` is checked as before.
* **Delete**: the selected object (never the BAR; the last object of the track is kept); the selection moves to the next object of the segment, or the focus returns to the grid when the segment has none left.
* **MOVE (`M`)**: LEFT / RIGHT = 10 units, FIRE or Control = 1, Shift = 100; **UP / DOWN = into the previous / next segment** (same offset, at most its last unit); the object stays in unit order (it is re-inserted at its new place, `obj_sort`), a unit that holds another object is skipped in the direction of the move, the range is 1 .. extent - 1; the tile frame and the panel follow the object into its new segment. FIRE / Return / Space keep, Esc / F10 put it back. (The old rule 'an object cannot pass its neighbour' is gone with the strip.)
* **Shift+B / menu PUT THE BAR HERE**: the BAR goes to the first free unit (`pick_unit`, BAR objects do not count as occupied) from the START of the selected segment; to place it exactly, select it in the list and move it.

### 15.6 Segment edits without a cursor unit
* **`S` SPLIT** (grid focus; in the object list `S` is the SIDE list): the segment is cut in half, `start + length / 2` (first part `length / 2`, second part the rest); a segment shorter than 2 units says `SEGMENT TOO SHORT TO SPLIT`. The cursor stays on the first half. (The old 'fine-move inside the segment, then split' is gone.)
* **`I` INSERT A COPY** (grid focus), `M` MERGE, Delete: as before. The cursor goes to the copy after an insert, stays on the index after a delete / merge.
* Pick lists (C H L W E T S): the box is the right 12 columns of rows 13-23 (heading row 13, ten items rows 14-23, scrolling); the preview is live in the grid and the panel. TYPES (36 entries) stay a full-screen list without a preview.

### 15.7 Key map: what changed (5.3 stays valid for everything not listed)
| key / joystick | before | now |
|---|---|---|
| LEFT / RIGHT | previous / next segment (object on the objects row) | previous / next segment (leaves the object list) |
| UP / DOWN | road row <> objects row | grid: one row (16 segments); object list: previous / next object |
| Tab | road <> objects row | grid <> object list of the selected segment |
| FIRE + UP / DOWN | zoom | FIRE + DOWN = into the object list, FIRE + UP = back to the grid |
| Control / FIRE + L/R, Shift + L/R | fine pixel / next 1000 units | (removed; in MOVE mode: 1 / 100 units) |
| `+` `-` | zoom | (removed) |
| `S` | split at the cursor unit | split in half (grid) / SIDE list (object list) |
| `I` | insert a copy (road) / add an object (objects) | insert a copy (grid) / add an object (object list) |
| `O` | - | **new**: add an object to the selected segment, either focus |
| Shift + `B` | BAR at the cursor unit | BAR at the first free unit of the selected segment |
| `M`, Delete, `T`, `C`, `H`, `L`, `W`, `E`, `,` `.`, `U`, Shift `U`, `K`, `P`, Return, Space, Help, Clr/Home, `B`, Esc / F10 | | unchanged (`P` starts at the segment's first unit, or at the selected object) |
The FIRE menu loses ZOOM IN / OUT and gains ADD AN OBJECT and OBJECT LIST <> SEGMENTS; `vState` values are unchanged (0 lists, 1 view, 2 menu, 3 help / check).

### 15.8 Budget and RAM (after the redesign)
`SINT` (sine table 10 KB), `PTS` (path 32 KB), `HARR` / `WLARR` / `WRARR` (96 KB), `CKPT` (64 KB), `SCR2` (32 KB) are no longer used; `TILE` (4 KB at `$150000`) replaces them. W-HILL (CHECK) runs its own height integrator over the race length (no array). The overlay shrinks by the map / strips / expand code and the 2,050 B quarter-sine table.

### 15.9 1 MB: the welcome screen says what 2 MB adds (user decision; the only code that runs at 1 MB)
On a machine below 2 MB (the ST family at 1 MB: `$42e` < `$200000`) the WELCOME PARTNERS screen shows the line `2 MB: CAMPAIGNS + TRACK EDITOR` (text row 23, centred) in place of the 2 MB build's `F10 = CAMPAIGNS`. `cp_welcome` (HD build) loses its `; gate: ram2mb`, so its site `$7c04` (the key wait of the screen) is patched at 1 MB as well, to the same `jmp $B9F0C.l`; cp_title's `e3` first tests the gate byte `IB+4`: zero = list 2 closed -> the 1 MB path: draw the line once per showing, then do exactly what the stock loop does (`tst.b $60ff / beq $7c02`, any key `$7c0a`); nothing else of cp_title runs, no campaign code and no editor code is installed or executed, F10 is an ordinary key. TT / Falcon (gate closed, phystop >= 2 MB) show the stock screen. The floppy build has NO `cp_welcome` at all (`; media: hd`, as since the campaign feature: the floppy flow never shows the WELCOME PARTNERS screen; its hint is `cp_flhint`, 2 MB only, at the title's loop `$7446`); there is no `cp_welcome_fl`. The floppy `disk_a.st` still differs from v1.1 in the payload sectors only, because cp_title's blob (shared with the HD build: `e3`'s 1 MB path, the editor entry) changed; no site jumps into the new `e3` at 1 MB on the floppy, so the 1 MB title screen stays byte for byte as before (gate `fl`: the 32000 visible bytes at two points of the title equal v1.1's). Proof obligations (abs1m): the HD 1 MB RUNME.TOS differs from the 2 MB-gated build only in the new site and in blobs; exactly the site `$7c04` holds a changed jump at 1 MB (all other campaign sites stock); the only cp_title code executed is `e3`'s 1 MB path and the hint routine; no GEMDOS call for MSEDIT.OVL; a race runs and its state is identical to a stock run.

## 16. As built (tile grid; MSREditor7 / MSREditor8, 2026-11-23) [obs] (results: `work/edgate/RESULTS_m2c.md`, raw `work/edgate/logs8/`, build `/tmp/msred8/hd`, harness `work/edgate/chain8.sh`)
Deviations from 15 (the code is right, 15 is the plan):
* **Cursor**: a 2-pixel frame plus a black ring; the frame is WHITE while the grid has the cursor and MAGENTA (palette 10) while the object list has it (yellow vanished on the yellow RISE tiles). DROP colours `$067` (small) / `$037` (big): the black symbol was unreadable on `$024`.
* **Object mark**: a notch at the tile's top-right corner (rows 0-1, columns 13-14) that stays visible inside the frame; the BAR tile is chequered white / black.
* **Panel lines** (28 columns): `SEGMENT 0017/0390  AT 12345`, `LENGTH 00120`, `CURVE RIGHT 3`, `BEND MEDIUM LEFT`, `HILL RISE SMALL ACC +0200`, `WIDTH LEFT 36 RIGHT 34`, `OBJECTS 03   UNIT`, then `01 TYPE 026 SIDE -041 12345` (the BAR: `01 THE BAR SIDE +043 19199`); a plain new track shows `NEW STRAIGHT` (no source tag).
* **Redraw**: header, labels, key column, hint row and the panel are redrawn only when they change. Shadows: `vSHdr vSKey vSHint`, `vSLab` + `vSLab2` (labels: scroll position + cursor row, and the last segment with a tile, so an insert / delete at the end redraws the row labels), `vPSh` (11 x 32 B: per panel row the colour and the 28 characters shown; `lp28` draws only changed characters, `cls` invalidates it). The grid keeps its 128-slot shadow (`draw_full` = cls + invalid shadows). A text character costs about 1500 cycles, so the panel shadow cut a one-segment step from 78 ms to 21 ms.
* **Thresholds** (unchanged from the first build, chosen on the 15 stock tracks): bend `|c|` at the segment's middle < 300 STRAIGHT, < 1200 GENTLE, < 2400 MEDIUM, else SHARP; slope < 1311 (0.02) LEVEL, < 6554 (0.10) SMALL, else BIG.
* **Choices from the fix pass**: `P` with the object list focused starts the test drive at the selected object's unit; `S` splits in half and the cursor stays on the first half; a BAR moved inside the race shrinks the extent (`vEnd`), so a segment beyond it can no longer be selected; FIRE + DOWN enters, FIRE + UP leaves the object list (no toggle).
* **Speed** (STE, `speed.py`, Hatari CycleCounter at 8.02 MHz, 313-segment track): one segment 21 ms (1 frame), next grid row 31 ms, one row 41 ms, a row that scrolls the grid (120 tiles) 129 ms, a bend key (apply, history, 313 tile words, redraw) 60 ms, one step of a live list preview 85 ms.
* **1 MB / floppy**: see 15.9 (HD: the welcome line, one site; floppy: unchanged title).

## 17. BUILD WHAT YOU WANT: the road is as long as what you build; NEW / ADD segments; a hill stays one tile; campaign file version 2 (MSRBuildModel, 2026-11-23; DESIGN, written BEFORE the code; nothing here is built or run)

**Why (user feedback on preview 2).** (a) a plain straight is ONE segment of 32768 units with the BAR at 19958, and `H` + RISE BIG turned it into two segments of 16384; (b) the only way to get a new segment is a copy; (c) 'length should be set by what you build rather than being determined before'; (d) the test drive of that track crashed (another agent's ticket; 17.14 lists what this design needs from its result). Supersedes: 4 ('total length stays 32768: the last segment grows / shrinks', 'PUT THE BAR HERE'), 5.1 (`PLAIN STRAIGHT ROAD`), 5.4 (E-SUM / W-FINISH rows), 10 (hill shapes become 2..5 segments), 15.3 (extent), 15.5 (Shift+B), 15.6 (`I`), the `I` / Shift+B / `S` rows of 15.7. Everything else of 15 / 16 stays.
Tags as in the rest of this note. **[obs]** here = a PC-side script or a file read during this design (no Hatari run was made for it); **[disasm]** = `tools/m68dis.py` on `work/dumps/ram_race_start.bin`.

### 17.0 The proposal in one table
| topic | now (preview 2) | proposed |
|---|---|---|
| what the grid shows | every segment up to max(race length + 1024, BAR + 512) (`calc_end`), the BAR somewhere inside | **THE ROAD** (your segments) and, as the last tile, **THE FINISH** (chequered). Nothing behind it is shown |
| track length | fixed: 32768 units, the last segment absorbs every change; the race length is the base level's | **the sum of your segments** (700..28000 units). The BAR always stands at the end of the road and moves with it; the race length (time bar) of the track = that length |
| new track | one segment of 32768, BAR where the scenery's original has it | **5 straight segments of 200 = 1000 units + the FINISH**, in the chosen scenery |
| new segment | only `I` = a copy | **Insert / `I` = NEW segment after the cursor** (straight on, level, 200 long, the widths of the road there), Shift = before the cursor, **`A` = ADD one at the end of the road**; `D` = duplicate (the old copy) |
| length of a segment | `L` list, left / right = 1 unit | panel row `LENGTH 0200 OF 02400 =  8%`; **`+` / `-` = next longer / shorter preset**; `L` list as before with left / right = 10 units |
| hill shape (`H`) | the segment is replaced by 2..5 segments | **the shape belongs to the segment: still ONE tile**; picking another shape replaces it, FLAT removes it, a length change rescales it |
| curve (`C`, `,` `.`) | whole segment (no split) | unchanged; the message says what it made (`ENDS THIS SEGMENT AS: MEDIUM RIGHT`) |
| after KEEP and EDIT again | equal neighbours come back as one long segment | **your segment boundaries survive** (17.7) |
| file | `MSTRACKS.TRK` version 1, no race length | **version 2: a race length per track** (0 = the base level's = a version 1 track); version 1 files load unchanged; a campaign without own lengths is still written as version 1 |
| game | time bar and progress from the base level's length | a track with an own length gets the **same pace as its scenery's level** (17.9); tracks without one are bit for bit as today |

### 17.1 Facts this builds on
* **Readers of the race length** (`--xref 57890`, all five) [disasm]: `$7792` (the load: `lea $57890,a0 / jsr $d6fa`, in EVERY race setup, before the track block fetch `$77da`), `$ee82` (`mulu.w $57890.l,d0` inside `$edea`, the routine `$7926` calls as the last step of the setup: `$10d2 = (100 + $102c) * len / 200 + (10 - $edcc[$102c]) * 200`), `$fbc4` (`divu.w $57890.l,d1`: progress = `$5ff8 * 256 / len`, + 15, compared with the time bar's high word: the 'behind schedule' comments), `$ef00` and `$f280` (`lea`: they read words 2..10 and the nibble path = the minimap, never word 0). So word 0 has exactly two consumers, both after `$7798`.
* **The time bar** [disasm `$11792`]: every pass `$10ce.l += $10d2.w`; high word >= `$ff` = time-out. `$10d2` is PROPORTIONAL to `len`, so the stock formula gives a longer track LESS time: it only works because the 15 lengths are all 18000..23000. Rates and passes allowed (`$ff0000 / rate`) of the 15 levels [arithmetic from the formula, the `$edcc` words `8 10 6 7 5 6 5 5 5 1 4 5 1 14 5` read from the dump and the lengths of `trackformat.md`; level 0's 10136 = the value observed in `timing.md`]: rates `10136 9958 10898 10385 11075 10250 10871 11700 11260 12700 12200 13210 12160 11630 14110`, passes `1648 1678 1533 1609 1508 1630 1537 1428 1484 1315 1369 1265 1374 1436 1184`; the pace this asks (units to the chase start per pass after the 55 passes of the start lights): 12.2 on level 0, 19.1 on level 14 (the car does 10 units per pass at speed `$5c`, `$130c = speed / 9` at `$10d94`; the car's limits `$10ae2..` come from the shop's upgrades `$176b0 / $176b2` and the level tier).
* **End of a stream** [disasm; INFERENCE for the behaviour, not run]: the three initial fillers (`$fe1c`, `$ff3a`, `$ffe4`: 1024 entries) have no terminator test (a stream shorter than 1025 units makes them read the next stream as data); the per-pass updaters (`$fe50`, `$ff76`, `$1003c`) test the count word and, at a terminator, step back and return WITHOUT storing the ring head: the ring stops advancing (the road freezes), no walk through memory. Counts are unsigned 16 bit everywhere (`subq.w #1 / dbeq`), so a count up to 65535 is legal; stock counts are at most 17445 [obs: script over the 15 tracks], the plain straight of preview 2 wrote 32768.
* **Stock tracks** [obs: script on `ed2model.union` over the 15 stock blocks]: the BAR lies INSIDE a segment in all 15 (8..145 units after its start); 2..16 segments and 5..15 objects lie behind the BAR; the last breakpoint of any stream is 40..1469 units behind the BAR, the rest (10300..13900 units) is one constant pair per stream; the longest segment before the BAR is 286..1000 units; none of the editor's 12 hill shapes occurs in a stock track (0 matches of the recogniser of 17.6).
* **Version 1 readers**: `cp_title.s` `validate` has `cmpi.w #1,4(a2) / bne .bad` and `tst.w 26(a3) / bne .bad` (the reserved flags word) [read]: the released v1.1 game refuses a version 2 file as 'not a valid campaign file'. It checks CRCs and the table, not the streams.
* **Keys**: the ST keyboard has no End key; under Hatari the PC's End key IS the ST's Undo (`src/sdl/keymap.c:226 case SDLK_END: code = 0x61`) [read], so 'End = append' cannot be offered: `A` is.

### 17.2 The model: THE ROAD, THE FINISH, THE RUN-OUT
The four ring streams still sum to **32768**, as in every stock track (nothing in the loader changes for that; E-SUM stays true by construction). What changes is what the editor calls the track:
* **THE ROAD** = segments `0 .. F-1`. Its length `L` = their sum = the first unit of segment `F`. This is what the user builds and all the grid shows.
* **THE FINISH** = segment `F`. **Invariant: the BAR stands on the first unit of segment F**, so the BAR's unit, `L` and the race length are one number. The FINISH is the last tile (chequered, as the BAR tile today). It can be selected (its panel: 17.8); its curve / hill / length / widths are not edited (`THE FINISH IS NOT EDITED: A ADDS ROAD`); the BAR's SIDE is (object list, `S`).
* **THE RUN-OUT** = segment `F` and everything behind it: the road the player still sees behind the BAR (the car is stopped about 34 units before it, `trackloader.md` 3.2) and the 1024-unit ring look-ahead. Never shown, never selected. Its LAST segment absorbs every change of `L` (the existing `road_shift`), so the total stays 32768.
  * a NEW track's run-out is one segment (segment F itself): curve 0, accel 0, the widths of segment `F-1` (kept equal to them by `fin_sync` after every edit, so there is no width step at the BAR).
  * a LOADED track (copy of an original, campaign track) keeps the segments and objects behind its BAR exactly as loaded (they move with the road; stock: up to 16 segments and 15 objects).
* **Limits**: `700 <= L <= 28000`. 700: the shortest BAR position that has been raced (`c3.trk`, BAR at 700..900, section 9) [obs there; 600 was never run]. 28000 leaves a run-out of 4768 units = the 1024 look-ahead + 3744 units (about 30 s of rolling at 13 units per pass: a car that timed out may pass the BAR while the message runs [INFERENCE: not measured]); the stock maximum is 22117.
* **Loading (`parse`, new step `fin_norm`, before the hill recogniser)**: no BAR in the block -> one is added at the base level's race length (`NO BAR HERE: FINISH PUT AT 19472`); several -> the first stays, the others are removed (`2 BARS: THE FIRST IS THE FINISH NOW`); then, when the BAR is not on a segment's first unit, **its segment is split at the BAR's unit** (both parts keep every value). `F` = the segment that starts at the BAR. The split costs nothing in the block: `encode` joins equal neighbours per stream, so an untouched copy of an original track still encodes to the stock block byte for byte.
* **Why the BAR is not a thing the user places** (the assignment's 'follows automatically, or stays where placed: decide'): it FOLLOWS, always. (1) it is the user's own model: the road ends where I stopped building; (2) a BAR in the middle of a longer road IS the old confusion (road that is drawn and edited but never driven, a length that was 'determined before'); (3) with the BAR tied to `F`, E-BAR, W-FINISH and 'the cursor is behind the BAR' cannot be produced any more; (4) what placing was used for is still there: a shorter race = **END THE ROAD HERE** (Shift + `B`: the segments behind the cursor's are removed, one undo step) or Delete; a longer one = add segments; (5) the run-out has to exist anyway, and nobody should have to build it.

### 17.3 A new track
Track list: `PLAIN STRAIGHT ROAD >` becomes **`NEW TRACK >`** (`NEW TRACK WITH THE SCENERY OF:` + the level list, as now). It makes: **5 segments of 200 units** (curve 0, FLAT, the start widths of that scenery's own track = the first targets of its S1 / S2, each with a kept boundary, 17.7), **the FINISH at unit 1000** (the BAR of that scenery: its type and the original's side), the run-out behind it (31768 units, one segment), name `NEW TRACK`. Five tiles and a chequered one: the grid shows at once what a segment is, any tile can be changed, `A` adds more. 1000 units = about 12 s of driving; the time bar allows 255 passes (17.9).
No segment of the working copy is 32768 long any more (the longest possible is a run-out of 32068), so `len.w` never reads as negative (`tiles_calc`'s `muls` note) [INFERENCE: whether that was part of crash (d) is the other agent's finding].

### 17.4 Adding and removing road
| act | key / menu | what happens |
|---|---|---|
| NEW segment AFTER the cursor | Insert, `I` (grid focus) | a segment of `vNewLen` units (200; after the user picked a length with `L` / `+` / `-`: the last picked one), curve 0, hill FLAT, the widths of the segment before it. On the FINISH tile it goes before the FINISH. The cursor moves to it. `NEW SEGMENT 0200 LONG: L + - CHANGE IT` |
| NEW segment BEFORE the cursor | Shift + Insert, Shift + `I` | the same, in front (the only way to get a new first segment; widths of the old first one) |
| ADD at the end | `A` (either focus) | the same, in front of the FINISH; the cursor jumps there (the grid scrolls). `A A A` builds road. `NEW SEGMENT ADDED AT THE END: 0200 LONG` |
| DUPLICATE | `D` | today's `I`: a copy of the cursor's segment (with its hill shape) behind it; not on the FINISH |
| DELETE | Delete (grid focus) | the segment AND the objects standing on it go (today the objects pile up on the next segment); not the FINISH (`THE FINISH STAYS: DELETE ROAD BEFORE IT`) |
| END THE ROAD HERE | Shift + `B`, menu | the segments between the cursor's and the FINISH go, with their objects (`ROAD ENDS HERE NOW: 0014 SEGMENTS CUT`); one undo step |
A new segment has curve 0 and accel 0, i.e. it **carries on what the road does there**: after a turn-in segment it keeps turning (the tile shows it: BEND). That is the game's own model (15.1) and is not changed here (17.14).
Every act: one history entry; `road_shift` moves everything behind (segments, objects, the BAR, the run-out's own segments); refused with a message when `L` would leave 700..28000 (`ROAD FULL: 28000 UNITS AT MOST`, `ROAD TOO SHORT: 700 UNITS AT LEAST`), at 2048 segments, or by E-HILL. The BAR cannot be moved (`M` on it: `THE BAR IS THE END OF THE ROAD: A / DEL`), deleted or retyped (as now).
Implementation: `seg_new(index)` = `seg_open(index)`, fill (start = end of `index-1`, length, values, flags), `road_shift(P = start, +length, first moved = index + 1)`, `hill_ovf`, `vSeg = index`; `F` is recomputed by `find_bar` + `seg_of` in `tiles_calc` (it already calls `find_bar`). `seg_copy` -> `seg_dup` (refuse on `F`). `seg_del`: refuse on `F`, delete the segment's objects (`vOF` / `vOCnt` range) before `road_shift`. `bar_here` is replaced by `end_here`.

### 17.5 Length
* **Panel row 14**: `LENGTH 0200 OF 02400 =  8%` = this segment, the whole road, the share (integer per cent). The FINISH panel shows `ROAD LENGTH 02400` and the time limit (17.8).
* **`+` / `-`** (main row `$0d` / `$0c`, keypad `$4e` / `$4a`): the next longer / shorter value of the `L` list (10 20 30 50 75 100 150 200 300 400 600 800 1000 1500 2000); immediate, like `,` `.` for bends; counts as the last pick (Return / Space repeat it on another segment). At 2000: `2000 IS THE LONGEST: ADD A SEGMENT (A)`.
* **`L` list**: presets unchanged; left / right = **10** units, Shift = 100, FIRE or Control = 1 (was 1 / 10 with FIRE / 100; a per-list step `vLStep` in `ad_tab`); hint `U/D PICK  L/R +-10 (SHIFT 100 FIRE 1)`. Range 1..2000; a loaded longer segment keeps its length until it is changed.
* Every accepted length (list, `+`, `-`) sets `vNewLen`; the message tells the result: `LENGTH 0300 (WAS 0200): ROAD NOW 02500`.
* The messages `THE LAST SEGMENT IS THE PADDING (E-SUM)` and `NO ROAD LEFT: LENGTH IS FIXED (E-SUM)` go (the padding cannot be selected; the limit is the road's).

### 17.6 Hills: the shape belongs to the segment (rule for `H`); the rule for `C`
**Rule: a hill shape is applied to the WHOLE segment and the segment stays ONE segment.** Not chosen: 'split at the cursor with a marker'. Reasons: the split was the confusing part; and pieces that are separate segments are a trap (delete or lengthen one half of a RISE and the slope runs on to the end of the track: section 10's first gate run produced exactly that E-HILL; pick DIP on the first half of a RISE and the second half still pulls down). With the shape as an attribute, every tile starts and ends with the slope it found: insert, duplicate, delete, re-length and re-pick are all safe, and E-HILL can only come from RAW ACCEL.
* **Segment record** (12 B, size unchanged): `start.w len.w curve.w hill.w wl.b wr.b shape.b flags.b`. `shape` 0 = RAW (`hill.w` = the accel, as now); 1..12 = RISE small / medium / big, DROP x 3, CREST x 3, DIP x 3 (the list's own index; `hill.w` = 0). `flags` bit 0: 17.7.
* **`seg_pieces`** (a0 = segment -> `vPcN`, `vPc`: up to 5 x `len.w, accel.w`): RAW = one piece; a shape = exactly today's arithmetic (`ap_hill .shape .. pc_add`: RISE `+a n, 0 (odd unit), -a n` with n = len / 2; CREST `+a n, -a n, 0 (rest), -a n, +a n` with n = len / 4; `a = clamp(h * 65536 / n^2, 1..4000)`, h = 8 / 20 / 40). `ap_hill` only stores the code (and refuses a segment shorter than 2 / 4 units: `TOO SHORT FOR ITS HILL SHAPE`, also in `ap_len`). Four routines walk pieces instead of `6(a0)`: `hill_ovf`, `tiles_calc` (slope), `check_all` (W-HILL) and `encode` (the hill stream gets its own writer; the other three streams keep the `enc_tab` loop).
* **Coming back from the block (`parse`, after `fin_norm`)**: the block has no shapes, only hill pairs. `shape_scan` walks the road's segments: at segment i with accel != 0 whose successor has the opposite accel (or is a 1-unit accel-0 piece followed by the opposite accel: a RISE of odd length), for the next k = 2, 3, 5 segments with equal curve and widths and no kept boundary inside, and each of the 12 codes: build `seg_pieces(total length, code)` and compare lengths and accels with the k segments; equal -> they become one segment with that code. 'Recognised' therefore always re-encodes to the same pairs (lossless by construction); what is not recognised stays RAW pieces. With 17.7 every shape the editor wrote is found again [INFERENCE: argument below, to be proven by the gate]; stock tracks: 0 matches [obs 17.1].
* **`S` (split)**: a RAW segment is cut in half (as now); a shaped one is split **into its pieces** (2..5 RAW segments: what `H` did until now), `SPLIT INTO ITS 3 HILL PIECES (RAW ACCEL)`. `M` (merge): this segment's values and shape win (as now). `D` copies the shape.
* **What the user sees**: the `H` list opens on the segment's shape; the preview and the result are one tile; message `RISE BIG: +38 OVER THE WHOLE SEGMENT` (the height really reached, `a * n^2 >> 16`: on long segments the integer accel rounds, e.g. RISE SMALL over 2000 units gives +15, not +8). Panel row 17: `HILL   CREST MEDIUM (+19)` for a shape, `HILL   RAW +0200 RISE SMALL` for a RAW segment (accel and slope class, as now).
* **Tile colour = two halves**: the left half is the slope class at 1/4 of the segment, the right half at 3/4 (today: one class at the middle, which shows a CREST as LEVEL because its slope is 0 there). RISE = both halves yellow / red, CREST = rise | drop, DIP = drop | rise; a RAW segment looks as today unless its slope changes class inside it. Tile word: bits 3-5 = left class, **8-10 = right class** (new); the selection bits of the shadow `SHW` move from 8 / 9 to 12 / 13. Legend page: one line + two example tiles.
* **`C`**: the delta is applied to the whole segment, as always; nothing splits. Because its effect adds up along the segment, the message says what it made: `ENDS THIS SEGMENT AS: MEDIUM RIGHT` (class of `c` at the segment's end), and `VERY LONG TURN (W-CURVE)` at once when `c` leaves -4473..8876 (today only on the check page).
* Cheap fallback if the lead wants `H` untouched in the next preview: keep the pieces but say so (`RISE BIG: SEGMENT 0012 IS NOW 2 PIECES`); about 1 h instead of WP-D's 7, and the trap above stays.

### 17.7 Your segment boundaries survive KEEP
Today KEEP joins equal neighbours per stream and the next EDIT shows the union of the stream breakpoints: five equal 200-unit tiles come back as ONE tile of 1000 (and a join can exceed the `L` list's 2000). The block format allows two neighbouring pairs with the same value (the fillers just load the next pair [disasm]; the game never compares), so:
* `flags` bit 0 = **kept boundary at this segment's start**. Set by the editor on every boundary it creates: the new segment and its successor (`seg_new`, `seg_dup`), the second half (`S`), pieces 2..n of an exploded shape, the 5 segments of a new track.
* `encode`, curve stream only: a new pair starts when the delta differs **or the flag is set**. The other three streams join equal neighbours as now.
* `parse`: a segment whose start is a pair boundary of the CURVE stream with the same delta on both sides gets the flag (the union loop knows when the curve count ran out).
* Stock blocks hold no equal neighbours (section 4 [obs]), so a copy of an original track gets no flag and still encodes byte for byte; an edited copy gains 4 bytes per boundary the user made. Worst case a track of 2048 equal-curve segments costs 8 KB in the curve stream alone: E-SIZE (8192 B) is checked on leaving, as now.
* This also makes the shape recogniser exact for editor-made tracks: every shaped segment starts and ends on a union boundary (its own first / last hill pair, or the kept boundary when a neighbour has the same accel), so two equal CRESTs side by side, whose `+a` pieces join in the hill stream, are still two segments in the union.
* `tools/msrtrack.py`: nothing to do (`decode` / `encode` keep pairs as they are; `validate` has no rule against equal neighbours). `ed2model.py`: `union` returns the flag, `track()` honours it.

### 17.8 Screen and keys
**Tiles**: only segments `0 .. F`; the FINISH tile = today's BAR tile (white / black chequers + the direction symbol of what the road does at the BAR); two-half hill colour (17.6); `vEnd` / `calc_end` / `seg_last` are replaced by `F` (`vFin`). Row labels unchanged.
**Panel, a road segment** (rows 13-23, 28 columns; changed rows marked):
```
13  SEGMENT 0017/0390  AT 12345          (0390 = the road's segments, the FINISH not counted)
14  LENGTH 0200 OF 19958 =  1%           <- new
15  CURVE  RIGHT 3
16  BEND   MEDIUM RIGHT
17  HILL   CREST MEDIUM (+19)            <- shape name and height, or RAW +0200 RISE SMALL
18  WIDTH  LEFT 36  RIGHT 34
19-23  the object list, as now
```
**Panel, the FINISH tile**:
```
13  FINISH             AT 19958
14  ROAD LENGTH 19958
15  TIME LIMIT 3:13 (SCENERY 04)         the passes of 17.9 / 8.33 passes per second (the paced rate of the shipped build, timing.md 3); here 1609 passes
16  BEND   STRAIGHT                      what the road does at the BAR: the run-out carries it on
17  HILL   LEVEL
18  WIDTH  LEFT 36  RIGHT 34
19  OBJECTS 01   UNIT
20  01 THE BAR SIDE +043 19958
```
**Key column** (right 12 columns): `KEYS / INS NEW SEG / A ADD AT END / D DUPLICATE / DEL DELETE / L + - LENGTH / C , . CURVE / H HILL / W E WIDTH / S SPLT M MRG / O OBJECT`. **Hint row**: `INS=NEW A=ADD FIRE=MENU P=DRIVE HELP`.
**FIRE menu (grid)**, the building items first: `NEW SEGMENT AFTER THIS  INS`, `NEW SEGMENT BEFORE THIS  SHIFT INS`, `ADD A SEGMENT AT THE END  A`, `CURVE...`, `HILL...`, `LENGTH...  L + -`, `WIDTH LEFT...`, `WIDTH RIGHT...`, `DELETE THIS SEGMENT`, `ADD AN OBJECT HERE`, `MORE: COPY SPLIT MERGE END HERE...`, `UNDO`, `REDO`, `TEST DRIVE FROM THE CURSOR`, `OBJECTS <> SEGMENTS`, `CHECK THE TRACK`, `KEYS`, `< BACK TO THE GRID`, `LEAVE AND KEEP THIS TRACK` = 19 rows (the menu holds 20). `MORE` opens a second list: `DUPLICATE THIS SEGMENT  D`, `SPLIT  S`, `MERGE WITH THE NEXT  M`, `END THE ROAD HERE  SHIFT B`, `< BACK`. The object menu loses `PUT THE BAR HERE`.
**Key map: what changes** (everything not listed stays as 15.7 / 16)
| key | now | proposed |
|---|---|---|
| Insert, `I` (grid) | a copy of the segment | a NEW segment after the cursor (object list: add an object, unchanged) |
| Shift + Insert, Shift + `I` | - | a NEW segment before the cursor |
| `A` | - | ADD a new segment at the end of the road (either focus) |
| `D` | - | DUPLICATE the segment (the old `I`) |
| `+` `-` (main row, keypad) | - | LENGTH: next longer / shorter preset |
| left / right in the `L` list | 1 unit (FIRE 10, Shift 100) | 10 units (Shift 100, FIRE / Control 1) |
| Shift + Clr/Home | - | to the FINISH (Clr/Home alone: the first segment; `B`: the FINISH too, as now) |
| Shift + `B` | put the BAR on the selected segment | END THE ROAD HERE |
| `H` | shape = 2..5 segments | shape = this segment (17.6) |
| `S` (grid) | split in half | RAW: in half; a shaped segment: into its pieces |
| Delete (grid) | segment (objects move on) | segment with its objects; never the FINISH |
| `M` on the BAR (object list) | move it | refused |
| `P` on the FINISH tile | (was: refused behind the BAR) | test drive of the last 1000 units (`TEST DRIVE OF THE LAST 1000 UNITS`) |
End: not used (17.1). Scancodes: `A` `$1e`, `D` `$20`, `-` `$0c`, `=` / `+` `$0d`, keypad `-` `$4a`, keypad `+` `$4e`; Shift = `$5ffe + $2a / $36` as for Shift + `B`. HELP page 1 and the legend page are rewritten to match.

### 17.9 The game side: a race length per track
**File, `MSTRACKS.TRK` version 2** (`trackformat.md` 4): the reserved word at entry `+26` (v1: flags, must be 0) becomes the **race length**: `0` = the base level's (exactly a version 1 track), else `700..28000`. Nothing else moves (header 16 B, entries 40 B, blocks, CRCs). Header version = **2 when any entry has a race length, else 1**: every writer (`msrtrack.py`, the editor's `store_rebuild`) applies that rule, so a campaign of original copies stays loadable by the released v1.1 game, and v1.1 refuses the files it would mis-time (17.1). Readers accept version 1 (word must be 0) and 2 (0 or 700..28000).
**Loader** (payload; all `; gate: ram2mb`, HD and floppy: floppy campaigns come from the same file):
* `cp_title.s` `validate`: version 1 or 2; the entry check becomes 'version 1: `+26` = 0; version 2: 0 or 700..28000 (unsigned)'. About 20 B (the blob has 674 B to the next one). No stream check in the game, as now (CRCs; `msrtrack.py validate` and the editor guarantee E-SUM).
* `cp_fetch.s` `hookb` (site `$77da`, runs right after the minimap header load): campaign path `move.w 26(a0),V_RLEN` (a0 = the entry it already points at), stock path `clr.w V_RLEN`, test-drive path untouched (the editor sets it). **`V_RLEN` = `CPV+16`** (w; `CPV+15..31` are unused [obs: grep of `CPV+` over `patches/`]). +12 B (the blob has 48 B to `$B8100`).
* **new patch `cp_len.s`** owns site `$7926` (`jsr $edea.l`) on BOTH media and replaces `cp_td.s` (HD only until now; deleted; its test-drive call moves into the HD flavour of the new hook, same blob address `$B8260` so the editor's site test in `c_td` still matches; the hook is about 70 B and `$B8276-$B82FF` is free, `$B8300` belongs to the non-default `mf_pre` / `mx_pre` [obs: `msrpatch.py list`]):
```
hookl:  jsr     $edea.l                 ; stock: $10d2 = the BASE level's rate ($57890 word 0 is still the base level's Lb here)
        movem.l d0-d2,-(a7)             ; ($edea's own register use was not traced: save what the hook touches)
        move.w  V_RLEN.l,d1             ; this track's own length L (0 = none: every v1 track, the original game)
        beq.s   .n
        move.l  #$ff0000,d0
        divu    $10d2.w,d0              ; Tb = the passes the base level allows (1184..1678)
        subi.w  #100,d0                 ; less the start allowance P0 = 100 passes (lights 55 + getting up to speed)
        mulu    d1,d0
        divu    $57890.l,d0             ; (Tb - 100) * L / Lb   (<= 2455 for L <= 28000)
        addi.w  #100,d0                 ; P = the passes this race allows
        move.l  #$ff0000,d2
        divu    d0,d2                   ; the rate; overflows (V) for P < 256 ...
        bvc.s   .ok
        moveq   #-1,d2                  ; ... then the fastest bar a word holds: 255 passes
.ok:    move.w  d2,$10d2.w
        move.w  d1,$57890.l             ; progress ($fbc4) is measured against the built length from here on
.n:     movem.l (a7)+,d0-d2
        ifeq    FLOPPY
        tst.b   CPV+14.l                ; V_TD: the editor's test drive (was cp_td)
        beq.s   .x
        jsr     EDBASE+20.l
        endc
.x:     rts
```
**Why this rule and not 'write L into `$57890` before `$edea`'**: the stock rate grows with `len`, so a 2000-unit road would get 11900 passes and a 28000-unit one 1150 (too few to drive it). The rule above keeps **the pace of the scenery's own level** (a track as long as the original gets exactly the original's time: P(Lb) = Tb) and adds a fixed start. Numbers [arithmetic]: scenery 1 (level 0): L 1000 -> 255 passes (31 s at 8.33 passes per second), 2000 -> 258 (31 s), 6000 -> 576 (69 s), 12000 -> 1053 (126 s), 19472 -> 1648 (198 s, the stock value), 28000 -> 2325 (279 s); scenery 15: 6000 -> 382, 28000 -> 1419. Roads up to about 2000 units sit on the 255-pass floor. `$57890` is reloaded by every race setup (`$7792`), so the overwrite never reaches the next race; word 0's only other reader is the progress compare. [INFERENCE: whether the pace FEELS right on a short road was not driven; gate 17.12 measures a flat-out test.] Unchanged and worth knowing: the speech stream (`$1286[]`, distances along the base level) and the fourth opponent's start distance (`$e14a[]`, 5000..17000 units ahead) follow the BASE level, so on a short road late speech lines and that car simply do not appear [INFERENCE from `trackloader.md` 4.5].
* A test drive: `c_td` sets `V_RLEN` to the word the track would be kept with (below) before `jsr $76f4` and clears it afterwards; `td_ff`'s bar rule (13.4) is unchanged and uses the new rate.
**Editor (`store_rebuild`, `leave`)**: the word kept with a track = `L` when the track is a NEW TRACK, or its entry already had a length, or **the BAR's unit differs from the one it was loaded with**; else 0. So a copy of an original track keeps the original's timing and the file stays version 1 until its LENGTH is changed; curve, hill, width and object edits do not touch it. `store_rebuild` copies the other entries' words and writes the header version by the rule above. `EDVER` 4 -> 5.

### 17.10 `tools/msrtrack.py` (and `trackformat.md` 2-5, `test_msrtrack.py`)
* JSON `race_length`: absent or equal to the base level's = the base level's (file word 0); another value = the track's own (format string stays `msr-track/1`: old files mean the same).
* **E-RACELEN becomes a range check**: an own length must be 700..28000. New **W-FINISH**: the BAR's position and the race length differ by more than 1100 (stock: -1043..+486, `trackloader.md` 3.2).
* **E-SUM**: every ring stream >= `max(race length, BAR position) + 1024` (today: base length + 1024; all stock tracks and `c3.trk` pass).
* `build_campaign(entries)` takes the word per entry and writes version 1 or 2 by the rule; `parse_campaign` accepts both (v1: word 0; v2: 0 or the range) and returns it; `entry_track` puts it into the track; `campaign list` prints it; `campaign add / new` take it from the JSON; `render` uses it for the extent.
* `patch-ms2` refuses an entry with an own length (MS2 has no place for it) unless `--force`.
* `selftest`: `campaign new --stock` is still the 64,676-byte version 1 file byte for byte; a v2 round trip; the released rule 'v2 only when needed'.

### 17.11 Existing tracks
| track | what happens |
|---|---|
| version 1 campaign file, played | unchanged: word 0, `V_RLEN` 0; `cp_len` adds `movem / move.w V_RLEN / beq / movem` to the race setup, nothing else |
| campaign track or copy of an original, opened and left untouched | shown as ROAD + FINISH (the stock road behind the BAR is hidden, not lost); not rewritten (as now); a kept copy = the stock block, byte for byte |
| the same, edited without a length change | block rewritten, word 0, version stays 1 |
| the same, a length changed (any segment's length, add, delete, end here) | word = the new BAR unit; the file becomes version 2; the stock segments and objects behind the BAR move with it |
| a track with no BAR / several (damaged, `--lenient`) | repaired on loading with a message (17.2) |
| a track whose BAR is outside 700..28000 | shown; CHECK and KEEP refuse it: `ROAD LENGTH NOT 700..28000 (E-RACELEN)` until it is edited into range |
| preview 2's plain straight (never saved to disk: milestone 4 is not built) | none exist outside RAM |

### 17.12 Gates: what changes, what is new
* `ed2model.py`: `union` + kept boundaries, `fin_norm`, `shape_scan`, `pieces()`; `hill_shape` = attribute; `tiles()` two classes + FINISH + no tile behind it; `seg_new / seg_dup / seg_del (objects go) / end_here`, road limits, `race_word()`; `track()` expands pieces and honours boundaries; the new-track constructor replaces `straight=True`.
* `ed2.py`: `copy()` sends `D` (`$20`), not `I`; `barhere` -> `end_here`; hill checks expect an unchanged segment count; new cell **`--kind new`** replaces `--kind straight`: FIRST the untouched new track is test-driven to the BAR and PLAYed to the BAR (the user's crash scenario), then `A` x 3, Insert, Shift + Insert, `D`, `+` / `-`, each hill family, `S` on a shape, Delete down to the 700 refusal, growth to the 28000 refusal, END THE ROAD HERE, undo / redo over all of it; keep; store: header version 2, entry `+26` = the BAR unit, block == model; `msrtrack.py validate` of the dumped file: 0 errors; EDIT again: segment list (count, lengths, shapes, boundaries) == what was left.
* `ed2.py --kind stock`: untouched copy kept = stock block byte for byte, word 0, version 1; a curve edit keeps word 0; a length edit sets it.
* `td3.py`: on a track with a word: `$57890` word 0 == L and `$10d2` == the formula while the race stands; on a word-0 track both are the stock values; rings / objects / bar-start checks as now (they read `$10d2` from RAM).
* **new `len2.py`** (HD STE 2 MB; quick cells Mega STE, ST; floppy STE 2 MB with a campaign disk): a v2 file made by `msrtrack.py` (track A own length 3000, track B word 0) loaded through the F10 menu: race A `$57890` = 3000, `$10d2` = the formula, driven flat out to the BAR (records the bar's high word at the chase start = the pace evidence); race A standing still times out after P passes (+- 2, counted on `$100e`); race B right after shows the base level's `$57890` and the stock `$10d2` (no leak); a v1 file: everything as v1.1; the v2 file on the RELEASED v1.1 build: refused with its message.
* `shots.py` (`tile_px`: two halves, selection bits 12 / 13, FINISH; new panel rows), `speed.py` (add: `A`, a hill pick; criteria as now).
* `abs1m.py` / `sitefl.py`: `cp_td` -> `cp_len` in the blob list; the floppy build gains the gated site `$7926` (stock bytes at 1 MB); `disk_a.st` changes in the payload sectors again.
* Rerun unchanged: `work/campgate` (v1 campaigns: finish, time-out, ending), `welcome.py`, the floppy title cells; `msrtrack.py selftest` + `test_msrtrack.py`.

### 17.13 Work packages (one Sonnet agent each; estimates in agent-hours, Hatari gate time included)
`msedit.s` is one file: C, D and E need ONE owner at a time, in that order, starting from the commit that holds the crash fix (d). A and B touch no editor file and can run beside C. Contract between them: this section's 17.9 (entry `+26`, version rule, `V_RLEN = CPV+16`, hook `$B8260`).
| WP | files | content | acceptance | h |
|---|---|---|---|---:|
| A | `tools/msrtrack.py`, `work/trackedit/test_msrtrack.py`, `work/notes/trackformat.md` | 17.10 | selftest + tests pass; stock campaign byte-identical (v1); v2 round trip; a v2 fixture for WP-B (`work/trackedit/fixtures/len2.trk`) | 3 |
| B | `patches/cp_len.s` (new), `cp_td.s` (deleted), `cp_fetch.s`, `cp_title.s` (`validate`), `requires:` lines, `patches/README.md`, `PATCHES*.TXT`, `work/edgate/len2.py`, `abs1m.py`, `sitefl.py` | 17.9 loader | `msrpatch.py verify` ALL OK; `len2.py` cells; `abs1m`; campgate cells with a v1 file | 5 |
| C | `patches/ovl/msedit.s`, `tools/msrpatch.py` (`EDVER` 5), `ed2model.py`, `ed2.py`, `ed2lib.py`, `td3.py` | 17.2-17.5, 17.7, the editor half of 17.9: `fin_norm`, `vFin`, new track, `seg_new / seg_dup / seg_del / end_here`, limits, BAR rules, `fin_sync`, kept boundaries (`parse`, `encode`), race word + version in `store_rebuild`, `V_RLEN` in `c_td`, the keys of 17.8 (plain key table entries), messages | `ed2 --kind new`, `--kind stock`, `td3` pass | 8 |
| D | the same files + `shots.py` | 17.6: `shape.b`, `seg_pieces`, the four consumers, `shape_scan`, `S` on a shape, two-half tiles, HILL row, legend | `ed2` hill cells (count unchanged, re-edit finds the shapes, block == model), `shots` (screen == Python drawing) | 7 |
| E | `msedit.s`, `shots.py`, `speed.py` | 17.8 rest: LENGTH row, FINISH panel + time limit, key column, hint, menu + MORE list, `+` / `-`, `L` step, the `C` message, HELP pages | `shots`, `speed` (criteria of section 16), every text <= its columns | 4 |
| F | `work/edgate/chain9.sh`, `RESULTS_m4.md`, this note ('as built'), preview 3 zip | the whole chain on one fresh build, quick cells Mega STE / ST, 1 MB, floppy | all cells pass or are listed plainly | 4 |
Total about **31 h**. Order of value: A + B + C + (E's keys, hint, LENGTH row) answer (b) and (c) = about 20 h; D (7 h) answers (a) properly, its 1 h fallback is in 17.6.

### 17.14 Depends on, open, not in this proposal
* **Crash (d)** (other agent): this design assumes the cause is not 'a track whose only object is the BAR' and not 'a stream pair longer than the stock maximum 17445'. If it is the first, the new-track recipe gets one scenery object (first type that is not the BAR, unit 100); if the second, `encode` cuts the run-out into pairs of at most 16384 (legal: 17.7; `parse` then sees several hidden run-out segments). Either is a few lines in WP-C.
* **Open for the user**: (1) the time rule is 'the scenery's own pace'; the later sceneries ask 13..19 units per pass (level 14: 19.1; 17.1), which needs the shop's upgrades. If an EASY / NORMAL choice per track is wanted later, the entry has no spare word: bit 15 of the race-length word is free (lengths are <= 28000) and reserved (must be 0 in version 2). (2) Default segment length 200 and the new track's 5 x 200: numbers to taste.
* **Not in this proposal** (same mechanism, next round if wanted): BEND shapes (turn in + hold + turn out as ONE tile, so every tile also ends as straight as it began; the second spare byte is `flags`, bits 1-7 free; note that a delta of at most 10 per unit needs about 270 units of turn-in for a SHARP bend, so such a tile is 600+ units long); a `STRAIGHTEN` key (delta = -c / length for the cursor's segment); track RENAME / MOVE / COPY in the track list (5.1, never built); saving to disk (milestone 4).
