# Powermonger quality-of-life patches (PMQoL): keys, village hover, Invent prediction

Tags: **[obs]** observed in Hatari 2.6.1 (1 MB STE TOS 1.62 snapshots / cold boots); **[disasm]** read from `work/dumps/get_men.bin` with `tools/m68dis.py` (addresses given); **[INFERENCE]** not verified.
Patches (all `; default: no`, the lead decides what ships): `qol_keys` + `qol_keys2` (keys), `qol_hover` + `qol_hover2` (village hover + "Invent here"), changes in `pm_tooltip` (key labels, Invent wording, wording table moved to $CF000), test-only `test_qolclick`, `test_qolinv`.
Tools: `tools/pmqol_state.py` (key == click world-state gate), `tools/pmqol_ab.py` (pixel gate), `tools/pmqol_inv.py` (prediction vs the game's real order), `tools/qol_points.py` (click points vs the game's hit test), `tools/pmtt_check.py` (52-character wording check, now with and without the key label).

## 1. RAM layout (inside the approved `qol_` range $CF000-$CFFFF; `test_` is now $CE000-$CEFFF in `pmpatch.py PREFIX_RANGES`, `pm_tooltip` may also place its wording table at $CF000-$CF7FF via `EXTRA_RANGES`)
| range | owner |
|---|---|
| $CD000-$CD443 | pm_tooltip code (jump table at $CD000: hook, `compose_sb` $CD006, `blit` $CD00C), state S at $CDC00 (+$A key-labels flag, +$E liveness 'PTIP', +$12 hover-text flag); `pm_credit` $CDB00 untouched |
| $CD460-$CD523 | qol_keys data: KS (33 B), REP, OWN9E, ANY ($CD4A2), PEND (128 B at $CD4A4, written by the keyboard interrupt) |
| $CD530-$CD559 | qol_keys2: KH (interrupt hook) |
| $CD560-$CD5D7 | qol_hover2: HVHOOK (the sprite hook) |
| $CD5E0-$CD60F | qol_hover data HS (HIT at $CD5E2) |
| $CF000-$CF73E | pm_tooltip wording table (ET, TXT, entries) |
| $CF860-$CFA7F | qol_keys: pass hook + click table KT |
| $CFA80-$CFFF3 | qol_hover: pass hook (`bra.w` vector, `predict` export $CFA84), strings |

(The qol data blocks and the two small hooks sit in the $CD460-$CD6FF gap of the pm_ range, allowed to the four qol_ patches by `EXTRA_RANGES`; $CF740-$CF85F is free, so the wording table has about 290 bytes of room. pm_tooltip's own blob stays below $CD444; pm_credit and S are untouched.)

## 2. Keys (feature 1 + 2)
### 2.1 What the game already does with the keyboard [disasm]
* ACIA handler `$18be` -> `$18e4`: a make code stores `$ff` at `$2de6c + scancode` (`$1998 st.b (a0,d0.w)`), a break code clears it; `$1c490` / `$2df89` = the last make code; Shift (`$2a`, `$36`) only sets `$2df8a` (it never reaches the table).
* The only reader of the table in the 3D loop is `$13762-$1385c`: cursor keys (`$4d` / `$4b` / `$50` / `$48`) scroll `$4bb3a` / `$4bb3c` by one cell per pass. The Shift + Insert / ClrHome (`$47`, `$52`) rotate, KP- / KP+ (`$4a` / `$4e`) tilt, `(` `)` (`$63` `$64`) `/` `*` (`$65` `$66`) and `,` `.` (`$33` `$34`) zoom blocks sit behind `tst.b $36(a0)` - Shift never lands in the table, so they are DEAD code.
* `$19c2` (ASCII from `$1c490`) is only used by the text windows (`$d03e` = typing; `$cf46`, name prompt). The manual lists no other keys (command symbols are mouse-only in this release).
Conclusion: nothing but the cursor keys is taken, so every letter below is free.

### 2.2 Mechanism (a key = the same click the mouse makes)
* The mouse path: the VBL handler `$1270` (button codes `$12cc-$1368`) copies the pointer `$2df92` to the click position `$2df8e/$2df90`, raises the latch `$2df96` (left) or `$2df98` + held `$2df9e` (right) and stamps `$2df74` with the pass counter; the loop's dispatcher `$7202` / `$13110-$13564` / `$135cc` handles it and `$1373c` drops the latch when the counter has moved.
* `qol_keys` writes exactly those words (position = a point inside the icon's cell, found with the game's own hit test: `tools/qol_points.py` checks every point against `pmtt_grid.icon`, the rect table `$13250` and the map-icon `x >> 4`). Site `$130fc` = the `jsr $7202` just before the dispatch, so the click is handled in the SAME pass (a mouse click latched by the VBL meanwhile would be handled one pass later; the equality gate injects both at that spot).
* The stamp: `movea.l $1373e,a4; move.l (a4),$2df74` - the operand of `move.l $2df70,d0` at `$1373c`, which `tick_click3` redirects to the pass counter; whichever is in force is the right stamp.
* Taps shorter than a pass (a pass is 125-260 ms) must not be lost: `qol_keys2` (site `$199c`, the make-code path of the ACIA handler: `move.b d0,$1c490`) sets `PEND[scancode] = 1` (+2 with Shift) in the interrupt; `qol_keys` consumes PEND once per pass. Nothing else changes in the handler.
* Ignored (the press is swallowed): typing (`$d03e`), any window open (`$7a36`: the option / query windows cover the icons), paused (`$57ff2`). A real mouse click still latched (`$2df96 | $2df98`) postpones a key by a pass.
* Shift + `[` `]` `=` `-` (KP + -) raise the RIGHT button instead (`$2df98` + `$2df9e`, dropped again next pass): fine rotation step / closest / farthest zoom, like a right-click. Shift + `[` or `]` repeats every pass while both stay down (the held right button on a rotate arrow does the same).
* The key labels in the tooltips are switched on by `qol_keys` writing 1 to pm_tooltip's `$CDC0A` every pass (so without qol_keys the tooltips are the old texts).

### 2.3 Key table (scan codes are PHYSICAL positions; `[` `]` are the two keys right of `P`, labelled so on UK / US keyboards; other national layouts print other characters there)
| key | scan | command (icon id) | tooltip |
|---|---|---|---|
| 1 / 2 / 3 (also keypad 1 2 3) | $02 $03 $04 ($6d $6e $6f) | 1 / 2 / 3 swords: passive / neutral / aggressive (21 / 20 / 19) | Passive (1 sword) (1): ... |
| A | $1e | Attack (6) | Attack (A): |
| D | $20 | Drop Food (9) | Drop Food (D): |
| E | $12 | Equip (8) | Equip (E): |
| F | $21 | Get Food (3) | Get Food (F): take 25% of a village's food |
| G | $22 | Send Captain / go to (1) | Send Captain (G): |
| H | $23 | Go Home (5) | Go Home (H): |
| I | $17 | Invent (7) | Invent (I): |
| L | $26 | Alliance (15) | Alliance (L): |
| M | $32 | Get Men (4) | Get Men (M): |
| N | $31 | Drop Items (12) | Drop Items (N): |
| O | $18 | Option (23) | Option (O): |
| Q | $10 | Query (22) | Query (Q): |
| R | $13 | Derank (10) | Derank (R): |
| S | $1f | Supply Food (13) | Supply Food (S): |
| T | $14 | Trade (14) | Trade (T): |
| X | $2d | Transfer Men (2) | Transfer Men (X): |
| Y | $15 | Spy (16) | Spy (Y): |
| F1 F2 F3 F4 | $3b-$3e | map icons contours / objects / settlements / food (24-27) | Map (F1): ... |
| `[` / `]` | $1a / $1b | rotate left / right 90 degrees (rect 0 / 1); Shift = the fine step | Rotate left ([): 90 deg; right-click/Shift+[: fine (keys on) |
| `=` or KP+ / `-` or KP- | $0d $4e / $0c $4a | zoom in / out one step (rect 2 / 3); Shift = closest / farthest | Zoom in (= or KP+): right-click or Shift: closest (keys on) |
| cursor keys | (the game's own) | scroll the view; the compass has no key of its own | Compass (cursor keys): scroll the view |

Wording rule (the lead's): the approved wording is unchanged, the label is inserted before the colon: `Name (K): effect`. Overflow check `tools/pmtt_check.py`: 101 texts, with and without the label, longest 51 characters (`Passive (1 sword) (1): takes a quarter, spares most`), no overflow. DONE (user-approved pattern, adjusted to fit): an effect may carry a keys-only variant after a `$03` byte (pm_tooltip table): keys off keeps the old text, keys on shows `Rotate left ([): 90 deg; right-click/Shift+[: fine` (50), `Rotate right (]): 90 deg; right-click/Shift+]: fine` (51; the `or` form of the approved sentence is 53 / 54), `Zoom in (= or KP+): right-click or Shift: closest` (49), `Zoom out (- or KP-): right-click or Shift: farthest` (51). Screenshot `work/shots/qol_rotate_zoom_sheet.png` (keys on above, off below).

## 3. Village workshop hover (feature 3)
### 3.1 Records [disasm unless noted]
* Houses: table `$4f916`, stride `$12`, 400 records: `+5` owner (0 = unused), `+6` type (2 house, `$10` workshop, `$1e` mine), `+7` kind (7 = WorkShop), `+8` next house of the settlement, `+$a` first resident (person offset from `$51b66`), `+$c` own cell, `+$e` the SETTLEMENT offset.
* Settlements: table `$4e514` (the notes called it "captains/armies" in entities.md: wrong; `$9b16-$9bae` print its fields in the Query window), stride `$20`, 160 records: `+0` owner / kingdom byte (0 = unused), `+1` type (Village..Base), `+2` first house, `+4` cell (name seed, `$a9ce`), `+6` food, `+8` men, `+$c` **item being made** (2 pike, 4 sword, 6 bow, 8 plough, `$a` boat, `$c` pot, `$e` catapult, `$10` cannon; 0 = none), `+$10` **countdown** to the next item, `+$12` mine house (0 = none), `+$18..+$1f` stock of the 8 items.
* Writer of `+$c`: the invention order `$5cde` (called by the captain's order handler `$5fa0` AND by villagers on their own: `$1589a`, with the shift `$e(person) & 3`); readers: the Mine window (`$a63a`: "This Mine ... makes the Pikes", game name strings at `$a242 + $14 + [$a242 + code]`).
* Countdown: `$60dc` (villager work step): `subi.w #1,$10(a3)`; at 0 the item is added (`addi.b #1,$18(a3,item)`, `$6118`) and the countdown restarts at `T = [$580a6 + owner * $20 + 8] + 4`, `+ $2000` for catapult / cannon (`$60e4-$610c`); the order sets the same start (`$5f0c-$5f2e`). Progress shown = `(T - countdown) * 100 / T`, clamped 0..99 [INFERENCE for the meaning "percent of the next item"; the formula is from the code; observed value in the screenshots below].
### 3.2 How the game finds the object under the pointer (and what the hook reuses)
* There is no hit test outside the renderer: the sprite routine `$12138` is called for EVERY drawn object (d0/d1 = sprite top-left, a3 = the object record; ~55 calls per pass in get_men [obs: 1663 calls in 6 s]); it compares the pointer (`$2df92/$2df94`, or the click `$2df8e/$2df90`) with the square `[d0, d0 + s) x [d1, d1 + s)` (`s = 8`, or `$12116[2 * zoom]` for the types flagged in `$120ea`), and only acts when a command is selected (`tst.w $57fd4`) or a click with the Query mode is latched.
* `qol_hover2` replaces its first instruction `tst.w $57fd4` by `jsr HVHOOK`; HVHOOK ends with that same `tst`. Unarmed it costs `jsr + tst + beq + tst + rts` (~78 cycles instead of 16 per call). Armed it runs the same square test with the live pointer and keeps the LAST object that hits and lies in the house table `$4f916..$51536` (the last drawn is the front one; trees / men in front are ignored).
* Throttle: armed for ONE rendered pass after pointer and view (`$4bb3a $4bb3c $ff9a $ff96 $ff98 $ff9c $57ffc`) have been still for 10 VBL (0.2 s): ARM=1 is set by the pass hook (`$130b6`, after the render), the sprite hook of the next render raises it to 2 and fills HIT, the pass hook after that render resolves it. Moving the pointer or the view drops the pick at once. A pass without a render (tick S passes) leaves ARM at 1.
* Text: `<name>: making <item>s (NN%)` (name = the game's own generator `$a9ce` with the settlement's seed `+4`; items lower-cased and pluralised from the game's strings), `<name>: workshop idle` (workshop, nothing made yet), `<name>: no workshop`. Composed into the same 6 x 104 byte buffer / font as pm_tooltip (exports `$CD006`, `$CD00C`), recomposed only when (settlement, item, percent) changes, blitted into the back buffer after the render every pass. An icon tooltip (pm_tooltip) or an open window wins.

## 4. The Invent chooser (feature 4) [disasm, `$5cde-$5f9e`]
`$5cde(a0 = settlement, d1 = posture shift)`; `d1 = posture - 2` (`$30fe`): 0 aggressive (3 swords), 1 neutral, 2 passive. Inputs, all read from RAM, no random number is drawn:
```
5ce4  move.w $2(a0),d0 ; 5cec/5cf2: cmpi.b #7,$7(a2,d0.w)       workshop (house kind 7) in the chain $2(a0), next $8(house), else nothing (rts, Z)
5d08-5d30  d5 |= $7(resident)   over houses -> $a(house) -> $18(person)    profession flags: 1 farmer, 2 merchant, 4 fisher, 8 shepherd, $10 leader
5d34-5d7e  d2 = min over the forest list $57f68 (10 x 8 B, word 0 = cell y<<6 | x, 0 = unused) of max(|dx|,|dy|)   distance to the nearest forest (cells)
5d80  d3 = byte [$3f86c + $4(a0)]            terrain height under the settlement
5d8e  tst.w $12(a0) ; bne 5db0               a mine exists                                  -> IRON
5d94  cmp #$10,d3 ; blt 5e80                 low land (< $10)                               -> WOOD
5d9c  cmp #$14,d2 ; bgt 5db0                 forest farther than 20 cells                   -> IRON
5da4  btst #0,$57fed ; beq 5e80              otherwise bit 0 of the pass counter's low byte: even -> WOOD, odd -> IRON  (time, not a random draw)
IRON  5db0: btst #1,d5 / cmp #0,d1:  merchant AND aggressive -> c = $10 cannon, else c = 4 sword
      5dca: a mine exists -> done.  else a farmer ($7 bit 0) must live there (5dd8-5e06) and a house slot be free ($51536 < $1c20, 5e0a), the mine is built;
      otherwise 5ee4: c = $c pot
WOOD  5e80: forest farther than 20 -> 5ee4 pot.  d1 = 0: merchant ? c = $e catapult : c = 6 bow;  d1 = 1: c = 2 pike;  d1 = 2: fisher ? c = $a boat : c = 8 plough
```
(`$c(a0)` is written at `5dbc/5dc4/5e94-5ec0/5ee8`, the countdown `$10(a0)` at `5f2e`.) Not inputs: the existing stock, the population (it only gates whether a villager starts the order at all, `$1587a-$15890`: men * 4 vs food), the captain's location. So the result depends on the TARGET SETTLEMENT and the captain's sword level.
* Icon hover (a): because it depends on the village, the Invent tooltip names the level's rule: 1 sword `ploughs, boats; iron: swords`, 2 swords `pikes; iron: swords`, 3 swords `bows, catapults; iron: swords, cannons` (wood item first, iron item after the semicolon; the second item of each group needs a fisher / merchant resident).
* Village hover (b), Invent selected (`$57fd4 == $e`): `qol_hover`'s `predict` replays the table above read-only: `Invent here: bows (wood nearby)`, `swords (iron mine)`, `cannons (builds an iron mine)`, `pots (no wood or iron)`, `bows or swords (wood or iron)` (high land with a forest within 20 cells and no mine: the real answer alternates with the pass counter, both are shown), `no workshop here`. It touches no state (one pass hook, reads only; no RNG: the name generator `$a9ce` is only used for the workshop text and restores `$2df84`).

## 5. Gates (all [obs], 1 MB STE TOS 1.62, Hatari 2.6.1, get_men snapshot, 8 MHz, tick set carried by both runs)
| gate | result |
|---|---|
| `tools/qol_points.py`: every click point against the game's own hit test | 32 table rows (33 keys), 0 problems |
| `tools/pmtt_check.py` (52-character limit, with and without the key label) | 101 texts, longest 51, 0 problems |
| **key == click**, `tools/pmqol_state.py get_men 8 700 SET` (SET 0-2 = 24 events; SET 3 = rotations 22 ticks apart): whole RAM `$0-$60000` at every loop top, compared per world tick, pmtick masks + the two hook sites + the camera/renderer words that follow the per-pass heading animation (heading is compared settled, SET 3); click run = `test_qolclick` (independent VBL-style latch), key run = `qol_keys` + `qol_keys2` with PEND poked as the interrupt hook does | 4 runs: **IDENTICAL**, 49 / 53 / 40 / 59 loop tops over 49 / 52 / 38 / 59 world ticks, negative control (key run tick k vs click run tick k+1) differs in 48/48, 48/48, 33/33, 58/58; camera words (tilt, zoom, scroll, map mode; heading in SET 3) equal at the end of every event window. Events that acted (key run, words before > 2 ticks later): Get Food `cmd 1a>6`, Invent `e>8`..., posture `2>3` (key 2), zoom `3>4`, map `2>1`, rotation heading steps, Query `1a>c`. 7 of 8 event breakpoints fired per run (one lands before it is armed, in both runs alike) |
| real keys through the whole chain (xdotool, 30 ms taps, 8 MHz, pass about 260 ms): 1 / 2 / 3, F, O | posture 4 / 3 / 2, `$57fd4` = 6, option window opened (`$7a36` = 374); H while the window is open is swallowed |
| real mouse click on icon 21 vs key 1 | both give posture 4; key at 16 MHz via `hatari-event keypress` is not usable for digits (its codes are shifted by one for the number row: observed, a Hatari quirk, letters and F-keys are right) |
| pixel gate `tools/pmqol_ab.py` (pmab frame matching, pointer held by test_walk): pointer away from villages (150,60) | **IDENTICAL**, back frames matched 50, shown 48, work/pass +3 039 cycles (+0.152 %), paired +5 026 (+0.251 %) |
| same, pointer on the village (223,108), item sword at 7/14 | DIFFER only in the tooltip rectangle: 53 reports, all `rows 0-5, 16-px columns 7-13` (170 B), bbox rows 0-5 cols 7-13; work/pass +13 969 (+0.533 %), paired +14 003 (+0.536 %) |
| same with Invent selected (`$57fd4` = $e) | DIFFER only in the tooltip rectangle: every report `rows 0-5, columns 7-15` (205 B) |
| **prediction vs the game's real order** `tools/pmqol_inv.py` (276 scenarios: 3 postures x 6 resident-profession sets x height x forest near / far / none x mine x free-slot x parity; the emulator writes the scenario into the game's variables, calls `predict`, then the game's own `$5cde` as `$5fa0` calls it) | **276 / 276 match, 0 mismatches**; 48 ambiguous scenarios (two answers) each matched the item of the parity bit that was set; pairs seen: pike/sword, bow/sword, catapult/cannon, plough/pot, boat/pot, ... |
| `predict` changes no state | read-only code (only `move`s from RAM, no write outside its registers / the stack); the pass hook's only RAM writes are HS (own block), pm_tooltip's BUF / S words and the back buffer; the key-vs-click gate runs carried no hover, so the world-state equality of the hover (pointer resting on a village, Invent selected) was NOT run through pmtick `ab` [not done] - the pixel gates above ran with the tick set and show the same frames outside the rectangle |
| screenshots | `work/shots/qol_hover_sheet.png` (20 tooltip bars) and `qol_<tag>.png`: settlements 0 / 1 / 2 (names Tossogy, Ropmmer, Wombetes) with idle / sword 50 % / plough 85 % / pike 14 % / catapult 51 % / cannon 98 % / bow 78 % / 18 % / no workshop; Invent selected at 1 / 2 / 3 swords (boats or ploughs, pikes, catapults / bows: `wood nearby`), with a mine (`cannons (iron mine)`); icon tooltips with keys |
| cold boot, default floppy set + qol_keys qol_keys2 qol_hover qol_hover2 (`pmpatch.py build --floppy --only <defaults> qol_*`, `/tmp/qol/bld`) | **STE TOS 1.62 and plain ST TOS 1.04, 1 MB: BOOT OK** (147 s each to the 3D view, marker `PMPO`, the four new sites `$130b6 $130fc $12138 $199c` live, pm_tooltip alive and key labels on, real key F -> `$57fd4` = 6, Invent icon tooltip composed with the key variant `sKEY` 285 = `$100 + 7*4 + 1`); village hover not exercised in the cold boots (the pointer was not on a house of the new game's view; the hover is covered by the snapshot runs) |

### Cost (cycles per pass, 8 MHz get_men, pass about 2.0 M cycles)
* not hovering anything: +3.0 k (+0.15 %; the paired same-tick measurement says +5.0 k, +0.25 %; pmab's noise is about +-0.1 %): sprite hook about 55 calls x 62 cycles, pass hooks about 1 k, key hook about 0.2 k (it scans its 33 keys only when the interrupt hook set ANY or a repeat runs; before that optimisation it cost +7.3 k).
* tooltip text up (village or icon): +14.0 k (+0.54 %) per pass (6 x 104 B blit; recompose 88-190 k cycles only when settlement / item / percent / level changes).
* armed pass (one per rest of the pointer): the sprite square test for about 55 sprites, about +10 k once.

## 6. Limits / not done
* HD build, Mega STE / TT / Falcon, 4 MB: not run. All code is 68000-only and uses fixed game addresses.
* `[` `]` are scan-code positions; the tooltip shows the character printed on UK / US keys. National keyboards print other characters on those keys.
* Shift + rotate / zoom variants are not named in the tooltips (52-character limit, see 2.3 for the proposed wording).
* The hover shows the settlement's own `$c` / `$10`, i.e. what the game itself would make next; the percentage is the countdown fraction (see 3.1) - its meaning as "progress" is inferred from `$60dc`.
* `Invent here` (feature 4b) predicts for the selected captain's sword level; the alternating high-ground case is shown as two items. The real order also needs the villager to start it (`$1587a`: men x 4 against food) - not predicted.
* The Invent icon tooltip (feature 4a) states the rule by level; it cannot name one item because the result depends on the target village (see section 4).
* Patch pairs: qol_keys needs qol_keys2 for taps shorter than a pass (alone it is harmless but never fires), qol_hover needs qol_hover2 and pm_tooltip (alone it shows nothing); qol_keys2 / qol_hover2 alone are harmless.
* The ISR hook sits in the ACIA handler; hd_kbd (HD build, site `$18e4`) was not combined with it.

## 7. Follow-up gates (lead's request)
* **Hover state equality** `tools/pmqol_hover_state.py` (U = tick set + test_walk + pm_tooltip, P = U + qol_hover + qol_hover2; pointer held on a house of settlement 0 at (223,108) in both runs; hover proven active in P: HIT $4f970, text flag 1; 1600 VBL at 8 MHz; whole RAM $0-$60000 at every loop top compared per world tick, pmtick masks + the hover/test_walk sites; the tooltip buffer is at $CDC00, outside the range): workshop text (sword 7/14) **IDENTICAL** 75 loop tops / 75 ticks, workshop text + Invent selected **IDENTICAL** 87 / 87, Invent selected (idle workshop) **IDENTICAL** 86 / 86; negative controls differ everywhere (74/74, 85/85, 95/95 loop tops).
* **Key-vs-click and the prediction gate re-run after the relayout above**: 4 key sets IDENTICAL (49 / 50 / 39 / 58 loop tops), prediction 276 / 276, 0 mismatches.
* **HD build with hd_kbd**: `pmpatch.py build --hd --only <defaults> qol_keys qol_keys2 qol_hover qol_hover2` (hd_core / hd_kbd / hd_load / hd_s1 / hd_sector added by the tool; hd_kbd mandatory site OK). 1 MB STE TOS 1.62, ACSI + HDDRIVER (`boot_to_game`) and Hatari GEMDOS folder, both: in game, marker PMPO, sites live, F -> `$57fd4` 6, `[` -> heading 240 -> 176 (one 90-degree step), `1` -> posture 4, mouse moves normally (100,100 -> 120,110), save to slot A + load through the game's own menu (`pmpatch.run_saveload`): saved == loaded, SAVEDISK.DAT == saved, game iterates; after the load the keys and the mouse still work (F toggles Get Food off again, as clicking the icon twice does). The kh hook runs in hd_core's replay path ($18e8) with d0/d1/a0 only, the registers hd_core documents as clobbered there. The village hover was not exercised in the HD boots; this HD build was made before the last wording-only edit of pm_tooltip (compose marker `$03`).
