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
| `$130000-$13FFFF` | `MSEDIT.OVL` image (8,942 B now) | M1 |
| `$140000-$1407FF` | editor variables (2 KB, cleared at entry) | M1 |
| `$140400-$1423FF` | block buffer: a stock track read by the game's file service (at most 12 sectors) | M1 |
| `$143000-$148FFF` | segment list, 2048 x 12 B | M1 |
| `$149000-$14AFFF` | object list, 999 x 8 B | M1 |
| `$150000-$167FFF` | per-unit arrays: height, left width, right width (32768 B each) | M1 |
| `$168000-$16C003` | path points: x.w, y.w every 8 units (4097) | M1 |
| `$16D000-$16F7FF` | sine table (4096 per turn + a quarter) | M1 |
| `$170000-$177CFF` | the editor's screen | M1 |
| `$178000-$1BFFFF` | planned: encode buffer (8 KB), undo ring (snapshots of the two lists), second screen for flicker-free live preview | M2 |
| `$1C0000-$1CCFFF` | spare | |

`cp_title.s` declares `; himem: $130000-$13FFFF` and `$140000-$177FFF`; the tool checks them against the other reservations and the ceiling.

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
| W-DENS | `MORE THAN 31 OBJECTS IN VIEW: SOME WILL NOT SHOW (W-DENS)` | after adding an object |
| W-HILL | `HEIGHT STAYS AT THE TOP FOR LONG (W-HILL)` | CHECK |
| W-CURVE | `VERY LONG TURN (W-CURVE)` | CHECK |
| W-FINISH | `THE BAR IS FAR FOR THE TIME LIMIT OF THIS SCENERY` | the BAR is put more than the base's race length + 500 away [INFERENCE: time model `trackloader.md` 3.1] |

## 6. Milestones

| # | content | estimate (agent-hours) | main risk |
|---|---|---:|---|
| 1 | design, overlay delivery, the viewer (this note) | done | |
| 2 | editing: lists with live preview, key map of 5.3, undo, encode + store update, new tracks as campaign entries, CHECK | 22-26 | incremental `expand` speed at 8 MHz; overlay grows to about 20 KB |
| 3 | test drive from the cursor: test flag around `cp_wrap`, ring fast-forward to the cursor (`trackeditor.md` 8), return to the map | 10 | the fast-forward and the time bar at a mid-track start; `rd_geom` reuse (`clr.b $C0008`) |
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
