# Moonshine Racers: the in-game TRACK EDITOR, design and milestone 1 (the viewer) (MSREditor, 2026-11-21)

Base: v1.1 (`8440b53`: campaigns, F10 menu, 2 MB gate). Study and facts this builds on: `trackeditor.md` (viability), `trackformat.md` (block / campaign file), `trackloader.md` (redirect sites, HAGA window, free RAM), `campaign_hd.md`, `campaign_floppy.md`. Quality bar: the Nebulus level editor (`games/in_progress/nebulus/patches/ed_editor.s`, `work/notes/editor.md`): clear menus, pick lists with a visible selection, live preview while the selection moves, a status line, keyboard shortcuts with Return / Space = repeat.
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

