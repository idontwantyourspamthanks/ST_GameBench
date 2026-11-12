# Powermonger hover tooltips (PMTooltip): `patches/pm_tooltip.s`

Tags: **[obs]** observed in Hatari 2.6.1 (1 MB STE TOS 1.62 snapshots, plain ST cold boot TOS 1.04); **[disasm]** read from `work/dumps/get_men.bin` with `tools/m68dis.py` (addresses given); **[INFERENCE]** not verified.
Patch: `pm_tooltip` (`; default: no`), site `$130a4`, blob `$CD000..$CDA48` (2633 B) + data `$CDC00` (1024 B, zero-filled). The `pm_` prefix range `$CD000-$CDFFF` is the 4 KB after p4_spr's cache (PMRealHD added it to `PREFIX_RANGES`). Wording: one table at the end of the .s (`tools/pmtt_check.py` checks the 52-character limit).

## 1. Layout of the screen (320x200 ST pixels, pixel (0,0) = top-left of the picture; the Hatari screenshot is 2x at (96,58))
* **The top bar is screen rows 0..5** (6 rows, black = colour 0). The frame picture `$78000` (QAZ.DAT) holds, in rows 0-4, the four **map-mode icons** at x 0-63 and a small **job symbol** at x 68-77; the army **status bars** (x 80-102, rows 0-5) are drawn into the screen buffers at run time ([obs]: absent from `$78000`, present in both buffers; max x of any non-black pixel in rows 0-5 right of x 64 = 102 in get_men, map_idle, battle_320 [obs, three dumps]). Row 5 of the picture is black.
* **The free area is x 112..319, rows 0..5** = 16-px word columns 7..19 (13 columns x 8 bytes x 6 rows = 624 B), 52 characters of the game's 4-px font. Nothing else the game draws touches it [obs: the three dumps; the HUD code writes x < 104 only].
* **Top-bar icons** (the only icons in the bar): map modes, hit-tested by the click code at `$13178 -> $131e6` ([disasm]): `cmpi #$40,d0; bge` (x < 64), `cmpi #6,d1; blt` (y < 6), mode = x >> 4 -> `$58098` -> `$107d6` (0 contour, 1 objects, 2 settlements, 3 food [disasm `$107d6`: `cmpi #2/#3,$58098`]). They match the manual's four Map Icons.
* **The command / posture / option symbols are NOT in the top bar**: they are the perspective icon grid painted into the 3D frame, along the bottom of the view and down its left side. The game hit-tests them with two line tables, not rectangles (below). Per the lead's instruction the tooltip appears in the top bar for all of them (and for rotate, zoom, compass).

### 1.1 How the game hit-tests an icon (click path `$13506-$1356a`, [disasm])
* Click position `$2df8e/$2df90` (copied from the pointer words `$2df92/$2df94` when a button event is latched, `$12f6/$1352`). Pointer coordinates are ST pixels, no offset.
* Cell code `d6`: `$12e6a` = 15 lines `{x0,y0,x1,y1}` (the near-vertical separators), `$12ee4` = 14 lines (the near-horizontal ones). Loop 1: for each line `q = (x-x0)*(y1-y0) / (x1-x0)` (`muls.w`, `divs.w`), `d6++`, continue while `(y-y0) < q`. Loop 2 the same with `d6 += $10`, continue while `(y-y0) > q`. `d6 = column + 16 * row`.
* `d6` is looked up in the word table `$19bde` (24 entries, negative word ends): the entry number `i` = icon id (`d1 = 2*i`), then `jmp $135cc(pc,d1)`. Ids with a `0` entry (0, 11, 17, 18) are blank cells. I re-implemented the loops in Python (`tools/pmtt_grid.py`, `icon(x, y)`): over all 320x200 pixels there is no `divs` overflow, no pixel with an icon outside x >= 64, y >= 129, and the cell outlines drawn over a screenshot coincide with the painted icons [obs].
* Other click zones: the four rectangles at `$13250` `{x0,y0,x1,y1}` (rotate left (24,155)-(32,161), rotate right (34,161)-(40,169), zoom in (45,159)-(61,174), zoom out (45,178)-(61,193); left click table `$13270`, right click table `$13278`: right = single step / maximum zoom, matches the manual); the compass = x < 32 and y > $a7 (`$1328e-$132a8`); the overview map x < 64, 6 <= y < $86 (`$13126-$13136`, not an icon).
* **The game never shows hover text for any of these** [disasm]: every reader of `$2df92/$2df94` is a click/drag path, the RNG seed (`$b310 $b416 $13dc8 $13eec`), window dragging (`$7206`) or the 3D-view object pick (`$11252 $1216e`). The only hover feedback is the cell highlight painted by `$189f8` for the active command (`$57fd4`).

### 1.2 Icon table (id = the game's icon number `i` for the grid; 24-32 are ours). Text = what the tooltip shows (1 sword / 2 swords / 3 swords where it differs)
Which icon is which: the jump table `$135cc` and the order handlers `$6b38` (opcode = 2*id) set the job number the captain gets; job names are the strings at `$9486` (1 Waiting, 2 Get Food, 3 Get Men, 4 Meeting, 5 Going To, 6 In Camp, 7 Go Home, 8 Attack, 9 Invent, 10 Equip, 11 Pickup, 12 Supply, 13 Fighting, 14 Alliance, 15 Trading, 16 Spying). id 3 -> `d3 = 2` Get Food, id 4 -> `d3 = 3` Get Men, id 7 -> 9 Invent, id 8 -> 10 Equip, id 13 -> job 12 Supply (`$390e`), id 14 -> 15 Trading, id 15 -> 14 Alliance, id 16 -> 16 Spying, id 1 -> job 5 (`$3888`), id 9/12 -> `$39d4` with `d7 = 1` (moves the food word `$24(a3)`) / `d7 = 2` (moves the item stock `$54(a3)`) = Drop Food / Drop Invention, id 19/20/21 -> the posture orders (`$13676`: opcode `$16`, value `2/3/4`), 22 -> Query (right click toggles the eye/rectangle symbol `$57fea`), 23 -> `$af6c` (the option window). The positions agree with the manual page 9 picture (second row: Supply Food, Derank, Get Men, Equip; bottom row: Drop Food, Drop Invention, Get Food, Attack, Invent, Send Captain; left column: Option, Spy, Alliance, Trade, Query; Transfer Men and Go Home next to the postures). Ids 2, 5, 6, 10 are identified by the manual layout + handler shape (`$1c18`, `$3c08`, `$4a7a`, `$1cc4`) [disasm, not executed individually].

| id | screen area (ST px) | tooltip text |
|---|---|---|
| 1 | cell bbox x 273-319, y 167-199 | Send Captain: walk to a spot you pick |
| 2 | cell bbox x 86-122, y 175-199 | Transfer Men: give 25% of the army / Transfer Men: give 50% of the army / Transfer Men: give the whole army |
| 3 | cell bbox x 184-220, y 171-192 | Get Food: take 25% of a village's food / Get Food: take 50% of a village's food / Get Food: take ALL of a village's food |
| 4 | cell bbox x 256-295, y 154-172 | Get Men: recruit a few men / Get Men: recruit more men / Get Men: recruit nearly every man |
| 5 | cell bbox x 84-117, y 160-180 | Go Home: army walks back to base |
| 6 | cell bbox x 222-269, y 179-199 | Attack: conquer, spare as many as you can / Attack: conquer, some die and some live / Attack: kill everyone and take everything |
| 7 | cell bbox x 249-303, y 173-199 | Invent: peaceful tools first / Invent: a mix of tools / Invent: weapons first |
| 8 | cell bbox x 279-317, y 149-166 | Equip: pick up 25% of the items / Equip: pick up 50% of the items / Equip: pick up all the items |
| 9 | cell bbox x 123-160, y 184-199 | Drop Food: leave 25% of your food / Drop Food: leave 50% of your food / Drop Food: leave ALL of your food |
| 10 | cell bbox x 234-271, y 159-178 | Derank: send 25% of the army home / Derank: send 50% of the army home / Derank: disband the whole army |
| 12 | cell bbox x 154-193, y 177-199 | Drop Items: leave 25% of spare stock / Drop Items: leave 50% of spare stock / Drop Items: leave all spare stock |
| 13 | cell bbox x 209-247, y 165-185 | Supply Food: ferry 25% of food, repeat / Supply Food: ferry 50% of food, repeat / Supply Food: ferry all the food, repeat |
| 14 | cell bbox x 64-85, y 166-185 | Trade: ploughs, boats, pots first / Trade: boats, pikes, ploughs first / Trade: cannons, catapults first |
| 15 | cell bbox x 64-83, y 154-169 | Alliance: pay tribute for a pact |
| 16 | cell bbox x 64-82, y 143-156 | Spy: scout a settlement |
| 19 | cell bbox x 83-112, y 149-165 | Aggressive (3 swords): takes all, kills all |
| 20 | cell bbox x 81-109, y 138-153 | Neutral (2 swords): takes half, spares some |
| 21 | cell bbox x 80-106, y 129-142 | Passive (1 sword): takes a quarter, spares most |
| 22 | cell bbox x 64-88, y 182-199 | Query: info on what you click |
| 23 | cell bbox x 64-80, y 133-145 | Option: speed, save/load, retire, pause |
| 24 | x 0-15, y 0-5 | Map: height contours |
| 25 | x 16-31, y 0-5 | Map: trees, houses, men |
| 26 | x 32-47, y 0-5 | Map: settlements and roads |
| 27 | x 48-63, y 0-5 | Map: settlement food (click: update) |
| 28 | x 24-31, y 155-160 | Rotate left: click 90 deg, right-click fine |
| 29 | x 34-39, y 161-168 | Rotate right: click 90 deg, right-click fine |
| 30 | x 45-60, y 159-173 | Zoom in: right-click: closest |
| 31 | x 45-60, y 178-192 | Zoom out: right-click: farthest |
| 32 | x 0-31, y 168-199 | Compass: scroll the view |

Levels: 1 sword = passive, 2 = neutral, 3 = aggressive (section 2). Texts with a single line do not depend on the level. Rotate "left/right": rect 0 / rect 1 of `$13250` (their left-click handlers subtract / add 4 from the heading `$ff9a`); which way the picture turns was not checked [INFERENCE for the word "left"/"right"].

## 2. The aggression setting
* **Word: `[$51538 + [$57fd2].w + $3c].w`**, the posture of the selected captain: **4 = passive (1 sword), 3 = neutral (2 swords), 2 = aggressive (3 swords)** [disasm `$30fe`: `move.w $3c(a3),d0; subi #2,d0`; the posture click `$13676 -> $6cc6 -> $35a0: move.w d1,$3c(a1)` stores 2/3/4 and highlights the cell `$a4/$94/$84` = ids 19/20/21; strings `$9583 Aggressive / $958e Neutral / $9596 Passive` indexed by value-2]. `$57fd2` is the selected captain's record offset + `$4c` (392 = 316 + 76 for the first captain; `$57ffe` is the captain number). [obs] get_men snapshot: `$57fd2 = 392`, word 2 (the scenario clicked the 3-sword icon); map_idle: 3 (the default `$2766`).
* Verified live: poking the word 4/3/2 (Hatari `w $516fc`) changes the text within one pass; real clicks on the posture icons give 4/3/2 and the matching text [obs, `work/shots/pmtt_live_*`, `pmtt_click_posture_*`].
* **What the level does (game code)**: amounts are shifted right by `posture - 2`: 100 % / 50 % / 25 % for aggressive / neutral / passive [disasm: `$30fe` returns the shift `d0`; users `lsr.w d0,dX` at `$1c58` (Transfer Men: the army count `-$18(a3)`), `$1cec` (Derank), `$3b60` / `$3bba` (Drop Food `$24(a3)`, Drop Invention: the item stock `$54(a3,d1)`), `$628e` / `$6328` (loops over a stock `$c(a0,d1)`, [not traced which command]), `$150e6 $150f0 $15140` (people taken from a village, [not traced which command])]. Matches the manual (25 / 50 / 100 %).
* Manual (our own summary): Get Food / Drop Food / Supply Food / Equip / Drop Invention / Derank / Transfer Men: 25 / 50 / 100 %. Get Men: passive few, neutral a few more, aggressive almost every able man. Attack: the more aggressive, the more food and men taken from a captured village and the more people killed. Trade: passive prefers a plough to a cannon, aggressive the cannon first, neutral between. Invent: the posture steers what the people invent.
* Trade wording comes from the item-priority table `$650a` (3 x 8 bytes, [disasm `$644c`: `d0 = posture-2` selects the row]; items `$a25c`: 0 pike, 1 sword, 2 bow, 3 plough, 4 boat, 5 pot, 6 catapult, 7 cannon): aggressive `7 6 2 1 0 4`, neutral `4 0 3 1 2 6 7`, passive `3 4 5 0 1 2 6 7`. **Invent** wording ("peaceful tools first / a mix / weapons first") is [INFERENCE] from the manual's sentence and the same table; the invent chooser itself was not traced. The Attack wording is the manual's plus the user's description; the exact casualty rule (`$55ce`: branches on `d0 = 0 / 2 / other`, random bit of `$57fec`) was not traced to the end.

## 3. Text and font rendering
* The game has no string routine for the HUD. Window text (`$7a56 -> $8838`, windows table `$7a36`) draws 16-px-wide tiles: four 4-px glyph cells per word, each glyph a **4x6 cell of the game's font**; the font is data at **`$8976`**: block `ch >> 2` is 48 bytes (6 rows x 4 planes x 1 word), column `ch & 3` of the 16-px word holds the character (ASCII codes, 32..126 present, lower case included, descenders use row 5). Rotate counts `(k - c) * 4` bring column k of the block to output cell c (the game reads them from a byte table at `$896e`; the formula is the same). Bytes at `$8960-$8fff` identical in the entry dump, get_men, map_idle, battle_320 [obs].
* **Colours**: glyph pixels are colour indices 1..5; **1 is the window background** (olive in the Option window), 2..5 the antialiased shades (cream in screenshots). The patch maps colour 1 to 0 (`P0 &= P1|P2|P3` per word) so the text sits on the black bar. One palette for the whole frame (`$d538` loads it once; no raster palette changes found [disasm grep of `$ff8240`]).
* Not reusable as a routine from our code: `$8838` needs the window machinery and clips against `$8834`; so the patch has its own composer (about 700 B) that reads the game's font in place.
* Cost: composing a 52-character line = 6 rows x 13 words x 4 planes x 4 cells; measured 88-190 k cycles ([obs] below), once per hover change.

## 4. How the top bar is redrawn, and where the text goes
* **Every rendered pass** the loop copies the whole 32000-byte frame picture `$78000` into the back buffer (`jsr $12ce0` at `$13096`, [disasm]/p4_raster.md section 4); that restores the bar, so **anything drawn into the back buffer after the copy disappears on the next pass by itself** and the frame picture is never written (no state to undo). The status bars / job symbol are drawn later in the pass by the HUD code at x < 104 and never overlap x >= 112.
* **Hook site `$130a4`: `jsr $178ae` (6 bytes) becomes `jsr $CD000`**; the hook saves d0-d7/a0-a6, works, restores and `jmp $178ae`. It runs only in passes that render (tick S passes and the speed-slider skip jump past it) and once per pass in R passes too.
* Per pass: read `$2df92/$2df94`; if unchanged since the last pass reuse the stored id, else run the hit test (section 1.1; outside the icon zones it stops after a few compares). Level = the posture word. Key = id*4 + level; if it differs from the composed key, recompose the 6x104 B buffer; then, while a text is up, **copy it into `[$2df7c]` rows 0-5, byte offset 56 (column 7)** (six `movem.l` rows). Nothing is drawn when not hovering.
* The software pointer is drawn by the VBL handler into the **displayed** buffer; our text goes into the back buffer, so the pointer save/restore (`$1c49e`) and the p4_ptr cache are unaffected. The pointer can overlap the text area only when it is at x >= 96 and y < 16, where there is no icon, so a clear and a stale pointer restore cannot meet (a pointer over the area at most leaves a one-frame artefact in the shown buffer; the next copy replaces it). [INFERENCE for the last clause, not provoked].
* Map-mode icons are suppressed while a window is open (`$7a36 != 0`): the option window covers them.
* Latency: the tooltip appears in the frame of the pass after the pointer moved: one frame time (8 MHz: ~250-400 ms with the stock render cost, 16 MHz ~120 ms), the same as every other response of the game's HUD. Not drawn into the shown buffer.

## 5. Gates (all [obs], get_men snapshot unless noted, 1 MB STE TOS 1.62, Hatari 2.6.1)
Scripts: `tools/pmtt_ab.py` (pmab.py frame gate with the pointer held; both runs carry tick_* + test_walk*), `tools/pmtt_state.py` (pmtick.py's full-RAM per-tick gate, patched = tick set + pm_tooltip), `tools/pmtt_check.py`. Screenshots: `work/shots/pmtt_*.png` (git-ignored).

| gate | result |
|---|---|
| pmab, pointer (150,100) (no icon) | **IDENTICAL**, back frames matched 27, shown+pointer matched 10 (3 runs, also after the last source edit); paired cycles per pass -41 / -2923 (-0.002 % / -0.114 %): the pmab cycle metric has about +-0.1 % run-to-run noise, so the per-call cycle counter below is the cost figure |
| pmab, pointer (229,173) (Supply Food, 3 swords) | DIFFER only in the tooltip: every report `rows 0-5, 16-px columns 7-16` (235 B); 92 reports, overall bbox **rows 0-5, columns 7-16** (inside rows 0-5 x columns 7-19); paired cycles +3133 per pass (+0.157 %) |
| pmab, pointer (40,3) (map icon 2) | DIFFER only rows 0-5, columns 7-13 (151 B), 87 reports; paired cycles -105 (noise) |
| pmtt_state (RAM $0-$60000 per world tick, tooltip up in the patched run) | **IDENTICAL**, 53 loop tops over 53 ticks, negative control 52 of 52 differ, 20 men moved |
| cost per hook call (cycle counter entry -> `$178ae`, cold-run log) | pointer still, no hover: 416 cycles (736 when a VBL interrupt lands inside); hover, text unchanged: 3668-4000 (the 6x104 B copy; up to ~5.7 k with interrupts); pointer moved outside the icon zones: 0.9-1.2 k; pointer moved into the grid: 7-10 k; text change (hit test + compose + copy): 88-190 k (Get Food, the longest text: 187 k) |
| screenshots | every id hovered (`pmtt_tour_all_ids.png`: text correct for ids 1-32), 6 icons x 3 levels (`pmtt_{1,2,3}sword_id{3,6,2,4,9,14}.png`), live change while hovering (`pmtt_live_*`), real posture clicks (`pmtt_click_posture_id{19,20,21}.png`), summary strip `pmtt_levels_sheet.png` |
| cold boot, default floppy set + pm_tooltip (`/tmp/pmtt/bld`) | STE TOS 1.62: BOOT OK in_game=True MARKER PMPO FLAGS 3, hook live (`$cdc00` state VAL = 1); ST TOS 1.04: BOOT OK PMPO FLAGS 6, VAL = 1; hover screenshots on both: see section 6 |

## 6. Cold-boot hover screenshots (default floppy set = p4_ptr_a/b, p4_spr, pm_noprot(+box), snd_*, tick_* + pm_tooltip, `pmpatch.py build --floppy --only ... --out /tmp/pmtt/bld`)
Script: boot to the 3D view with the harness, hover Get Food / Attack / Transfer Men, click the 1-, 2-, 3-sword icons and hover Get Food / Attack again; the posture word was read back from RAM after every step ([obs]):
```
STE TOS 1.62 1 MB: in_game True flags 0x3, sel 392 posture 3 (default); hover shots; click posture icon 21 -> 4, 20 -> 3, 19 -> 2
ST  TOS 1.04 1 MB: in_game True flags 0x6, same sequence, same words
```
Strips (top bar of each step): `work/shots/pmtt_cold_ste_sheet.png`, `pmtt_cold_st_sheet.png` (full screenshots `pmtt_cold_{ste,st}_N_idK.png`): neutral "Get Food: take 50% ...", "Attack: conquer, some die and some live", "Transfer Men: give 50% ...", "Passive (1 sword): ...", then 25 % / spare-as-many wording, neutral posture text, 50 %, "Aggressive (3 swords)", ALL / "kill everyone and take everything" - identical on STE and plain ST.

## 7. Not done / limits
* HD build, Mega STE / TT / Falcon, 4 MB: not run. The hook uses only 68000 instructions and fixed game addresses.
* p4_chase (not default) replaces `$13090` only; `$130a4` is untouched by it, so the patch should coexist [INFERENCE, not run].
* Windows (query windows, option menu) can cover icons; the tooltip then still names the icon under the window (only the map icons are suppressed while a window is open).
* The tooltip is not drawn into the displayed buffer, so it follows the pointer by one frame time.
* The rotate direction words and the Invent wording are the only [INFERENCE] texts.

## 8. Later changes (PMQoL)
Key labels, the Invent wording from the traced chooser, the wording table moved to $CF000 (`ET` / `TXT` equs) and the village hover are described in `qol.md`; the gate numbers in section 5 above predate them.
