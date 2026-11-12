# Populous 2: hover tooltips (`pop2_tooltip`)

2026-11-12, Pop2UI. Hatari 2.6.1, snapshots `busy1` and `game_start` (2 MB STE, TOS 1.62), dumps `work/dumps/game_start.bin`. Patch `patches/pop2_tooltip.s` (`; default: no`), site `$12740`, blob `$85800` (1,100 B). Gate tools: `tools/p2tt.py` (shots / tour / rpass / land / lcycle / zoom / cold), `tools/p2ttab.py` (p2tick.py `ab` with the tooltip added), `tools/p2abtest.py`. Raw outputs: `work/gates/ui_*.txt`; screenshots `work/shots/ui_*.png`.
Evidence = disassembly lines (`tools/m68dis.py`, game_start.bin), raw tool output, or `[INFERENCE]`.

## 0. Result

| item | result |
|---|---|
| what it shows | line 1 = the icon's name (17 characters, ST (120,0)-(255,7)), line 2 = its existing key (14 characters, (136,8)-(247,15)); the game's renderer `$168b6`, opaque font `$37c84`, as `tt_candidate_top_text.png` |
| icons | the 6 command-strip icons, the 6 category icons, the 5 effect slots of the current category (only slots the game would act on) |
| p2abtest, pointer away from icons (`--no-walk`) | **IDENTICAL**, busy1 and game_start, back 128 / world 128 / shown 127+128 turns each |
| hover frames | back buffer differs only at x 120-255, y 0-15, 1,984 pixels = exactly the two text boxes (136x8 + 112x8), 16 hover turns on two snapshots (`work/gates/ui_ab_walk_bbox.txt`) |
| world by turn (`p2ttab.py ab`, tick set + tooltip) | **0 differing pass tops** in 7 runs: busy1 8 MHz walk / `--no-walk` / `--spin 12800` (S passes) / 60 Hz, busy1 16 MHz, game_start 8 and 16 MHz; `--no-walk`: IDENTICAL including every T frame; walking runs: the only differing T frames are the hover turns (839 B, rows 0-15) |
| render-only passes | the text is drawn in R passes too: busy1 16 MHz walk, pointer on the Air icon: T 8 of 8 flips with text, R 11 of 11 (`work/gates/ui_rpass.txt`) |
| landscapes | rect free in all four (the clean background is one file, P2D file 14, 32,000 B; only the minimap diamond differs per level; palette index 0 = black in all four) |
| zoomed views | no icons there (the game's click code is off for `$39766 != 8`), the hook returns at once: nothing drawn (screenshots) |
| cold boot | HD build, default set + tick + display + tooltip: STE 2 MB TOS 1.62 and Falcon 4 MB TOS 4.04: in play, marker `P2PO`, tooltips shown on hover (section 6) |

## 1. How the icons are hit-tested (the game's own geometry)

No rectangle tables: iso cells, origin (ox, oy), `dx = (x - ox) >> 1` (asr), `dy = y - oy`, `u = dx + dy`, `v = dy - dx`, `>> 4`. Click path (`work/notes/ui.md`), read again from the code:

```
012dcc  3006 / 3207          move.w d6,d0 / move.w d7,d1           ; d6/d7 = click ($393f6) or held ($393fa) position
012dd0  0440013d / 0441008c  subi.w #$13d,d0 / subi.w #$8c,d1     ; command strip origin (317,140)
012dd8  e240                 asr.w #1,d0
012dda  3601 / 9640          move.w d1,d3 / sub.w d0,d3            ; v
012dde  3400 / d441          move.w d0,d2 / add.w d1,d2            ; u
012dee  e840 e841 e541 d041  asr #4,d0 / asr #4,d1 / asl #2,d1 / add d1,d0   ; index (u>>4) + 4*(v>>4)
012dfa  0c400018 6e00014e    cmpi.w #$18,d0 / bgt                  ; > 24: none
012e04  303b0006 4efb0002    move.w $12e0c(pc,d0.w),d0 / jmp ...   ; word table: only entries 4, 8, 12, 16, 20, 24 are not "none" ($0142 -> $12f4e)
```
Table `$12e0c` read from the dump: entries 4,8,12,16,20,24 -> `$12f2c`, `$12e3e`, `$12e80`, `$12e9a`, `$12e66`, `$12eb4`, i.e. strip cell k = index/4 = 1..6. The category row (`$13b4e`): origin (`$3b`,`$89`), `asr.w #4,d3 / bne` (v>>4 must be 0), `asr.w #4,d2` = 0..5 (`013b74 cmpi.w #5,d2 / bgt`), then `d2 += d2`, `move.w d2,$39794` (2 x category, `013b98`) and `jsr $134fc`. The effect row (`$13ba8`): origin (`$2a`,`$97`), v>>4 = 0, u>>4 = 0..5, then `$13bd2`:

```
013be4  30390039794  move.w $39794.l,d0 ; 013bea c0fc0003 mulu.w #3,d0 ; 013bee 3800 move.w d0,d4 ; 013bf0 d842 add.w d2,d4
013c16  4a314070 6f000390    tst.b $70(a1,d4.w) / ble.w $13fac      ; the slot must be available (a1 = $46fc4 + $4739c * $13a)
```
so effect index = 6 x category + slot (6 slots per category, slot 5 never exists: every category's string pointer for slot 5 is 0 in the table at `$170a6`, and its jump-table entry `$13c88` is the next category's first).

`pop2_tooltip` repeats this arithmetic on the live pointer `$393fa/$393fc` in the same order (strip, category, effect), same index tests, same availability test. Only the normal view: `012cca cmpi.w #8,$39766.l / bne.w $12f6e` makes the game's click code inert in every zoomed view, so the hook starts with the same test.

Cell centres used by the screenshots: category k (59+16k, 145+8k), effect e (42+16e, 159+8e), strip k (317-16k, 148+8k) (`tools/p2tt.py targets()`); overlay of the computed cells on the picture: all three rows and the strip coincide with the painted icons (checked on `game_start`).

## 2. What the icons are

| icon | action (game) | name shown | key shown |
|---|---|---|---|
| strip 1 | `$12f2c`: command `$76` -> `$29b94 move.w #1,$39628` -> the loop calls `$15c62` = the options dialog (strings at `$1a300` `GAME OPTIONS`, `$1ae5c` GOOD/BAD, `$1ae6e` COMPUTER V HUMAN) | GAME OPTIONS | none (F9 is command `$78`, not this) |
| strip 2 | left: pointer mode `$c` (`$12e5a`) = the query pointer; the "?" icon | QUERY | `/` (scan `$35`, `$12b46`: `move.w #$c,$47372`) |
| strip 3 | command `$12` (`$12e90`) -> player word `$c(a1) = $12` (`$294c6`) | GATHER [INFERENCE: name] | keypad `)` (scan `$64`, `$12b0c`: command `$12`) |
| strip 4 | command `$14` (`$12eaa`) | FIGHT [INFERENCE: the sword icon] | keypad `/` (scan `$65`, command `$14`) |
| strip 5 | command `$0e` (`$12e76`); `$0e` is the initial value of `$c(a1)` of both players in game_start | SETTLE [INFERENCE: default behaviour] | keypad `(` (scan `$63`, command `$0e`) |
| strip 6 | left: command `$10` (`$12f22`) = the one behaviour the people code special-cases first (`02318a cmpi.w #$10,$c(a1) / bra.w $23a0a`); right: view to the magnet / leader (`$12ec4`-`$12f1a`) | GO TO MAGNET [INFERENCE] | keypad `*` (scan `$66`, command `$10`) |
| category n (0..5) | `$39794 = 2n`, effect row follows | PEOPLE / PLANT / EARTH / AIR / FIRE / WATER EFFECTS (the draft in ui.md; the category's real contents are listed below) | F1..F6 (scan `$3b`-`$40`, `$12940`-`$129dc`: `move.w #2n,$39794`) |
| effect (n, e) | `$13bd2(e)`; names are the first words of the game's own Help strings (pointer table `$170a6`, 4 bytes per effect) | see the table | F(n+1) THEN (e+1): digits 1-5 (scan `$02`-`$06`, `$12a2c`-`$12a9e`: `move.w #e,d2 / jsr $13bd2`) |

Effect names (own table; category x slot, from the strings at `$170a6` and the jump table `$13c88`; slots a level has not unlocked are skipped because `$70(a1,d4)` is 0): 0: RAISE/LOWER LAND, PAPAL MAGNET, PERSEUS, PLAGUE, ARMAGEDDON; 1: TREES, FLOWERS, SWAMP, FUNGUS, ADONIS; 2: ROADS, BUILD CITY WALL, EARTHQUAKE, BATHOLITH, HERACLES; 3: LIGHTNING, WHIRLWIND, STORM, ODYSSEUS, WIND; 4: FIRE COLUMN, FIRE RAIN, ACHILLES, VOLCANO, (empty: the game's string for slot 28 repeats Achilles and its jump entry repeats the next category's; the hook shows nothing for an empty name); 5: BASALT, WHIRLPOOL, BAPTISMAL FONTS, HELEN OF TROY, TIDAL WAVE. "PLACE PAPAL MAGNET" (18) is shortened to PAPAL MAGNET to fit 17.

Names marked [INFERENCE] (strip 3, 4, 5, 6) are from the icon pictures and the Populous 2 behaviour set (go to magnet, settle, fight, gather) matched to the command numbers by code behaviour, not from any string of the game (the game has none for them); strip 1 and the effects are from the game's own strings. The unlock state decides which effect slots exist: in busy1 Plague (`$70 + 3`) and everything but five slots are 0, so the screenshots `ui_effects_cat*.png` (all 30 names) were taken with the 36 bytes at `$4716e` poked to 1.

## 3. The patch

Site `$12740`: `jsr $1334a.l` (the pointer-shape call) after the render stage `$1255e`-`$1273a` (background copy `$1e7b2`, terrain/sprites, minimap/HUD) of a T or R pass; S passes jump over it (`pop2_tick_render`: `jmp $12746`). The blob saves all registers, hit-tests, builds the two 17- and 14-character lines in two buffers inside the blob (space padded), calls `$168b6` twice into `$392e0` (the back buffer: column 15, pixel row 0; column 17, pixel row 8), then **makes the text transparent (v2)**: the font's paper is colour index 13 (the space glyph is planes `ff 00 ff ff`), and a masked pass (`mask`, `p0 & ~p1 & p2 & p3` cleared in all four planes, limited to x 120-255 on line 1 and x 136-247 on line 2) turns every paper pixel into colour 0, the sky. Glyph pixels keep their colours (the mock's tan on black). Then it restores everything and `jmp $1334a.l`. `$168b6` takes `d0` = column 0..39 (8-px cells, `016906 lsl.w #5,d0` = 32 B per glyph), `d1` = pixel row (`0168ba mulu.w #$a0,d1`).
- **Backdrop safety of the mask**: index-13 pixels of the clean sky inside the two boxes: 0 of 1,984 (P2D file 14, the shared picture) and 0 of 1,984 in the live background; all 1,984 are index 0. The only per-level drawing in the background is the minimap (x 5-131), so this holds for all four landscapes (section 5).
- v2 hover diff: 713 pixels (x 120-207, y 0-15) per hover turn instead of 1,984: only the glyph pixels differ from the stock frame.

- No tooltip: the hook only restores registers and jumps (about 560 cycles per pass, measured +0.04 % / +0.07 % of a pass in the identical-frame gate), screen and world are the stock ones.
- Tooltip: the back buffer is rebuilt from the clean background every rendered pass (`01e7b2`: 32,000 bytes from `$392e4` to `$392e0` before anything else), so the text vanishes by itself when the pointer leaves, nothing is ever erased or saved, and the shown buffer, the pointer sprite code (`pop2_ptr_a/b`) and every world word are untouched. The pointer sprite can overlap the rect only when it is at y < 16 and x >= about 100, where no icon exists.
- Cost while a tooltip is up: about 25,000-28,000 cycles per rendered pass [derived: the walk gate's mean work/pass rises 1,738 cycles (busy1) / 1,574 (game_start) with 2 of 32 turns hovering, x 16] (the 31 glyphs; an 8 MHz pass is 640,000-1,250,000 cycles, about 2-4 %); measured mean work/pass in the walk gate: +0.14 % busy1, +0.25 % game_start.
- Blob `$85800-$85C49`: code, text (last text byte `$85C28`), two line buffers (34 bytes, zero in the image).
- Unlocks: nothing of the game's tables is written; only `$393fa/c`, `$39766`, `$39794`, `$4739c`, `$46fc4+$70+...` are read.

## 4. Gates (raw output in `work/gates/`)

`ui_ab_nowalk.txt` (pointer held at the snapshot's position, no icon; walk driver carried by both runs):
```
busy1 @8 MHz (base @8): IDENTICAL | turns compared: back 128, world 128, shown@S1+pointer 127, shown@flip+pointer 128 ... | work/pass 1255126 -> 1255687 (+0.04 %)
game_start @8 MHz (base @8): IDENTICAL | turns compared: back 128, world 128, shown@S1+pointer 127, shown@flip+pointer 128 ... | work/pass 764060 -> 764621 (+0.07 %)
ALL IDENTICAL
```
`ui_v2_ab_nowalk.txt`, `ui_v2_ab_walk.txt`, `ui_v2_ab_walk_bbox.txt` (v2): `--no-walk` IDENTICAL on both snapshots; hover turns differ only at the glyph pixels, bbox x 120-207, y 0-15 (713 px). `ui_v2_tickab.txt`: `p2ttab ab` and the render-only check on v2. The opaque-box figures (1,984 px, x 120-255) below are v1, superseded. `ui_ab_walk.txt` + `ui_ab_walk_bbox.txt` (v1: the walk driver's 16 pointer positions; (96,170) is the Air category icon, held 2 turns in 32): back DIFFER exactly at the hover turns, `839 B differ, rows 0-15`.
`ui_tickab_final.txt` (`p2ttab.py ab`, base = walk driver, patched = tick set + tooltip): world at pass tops 0 differ in all seven; `--no-walk`: IDENTICAL; walking runs: T-frame DIFFER only at the hover turns. Pass kinds in these runs: T 112-130, R 5-380, S 10-18 (so the tooltip coexists with catch-up and render-only passes).
`ui_rpass.txt`: flips with the pointer on the icon at 16 MHz: `T without text 0, T with text 8; R without text 0, R with text 11`.

## 5. Other landscapes and the zoomed views (the study did not check them)

- The clean background is one raw 32,000-byte file, P2D file 14 (offset table `$18e`: file 14 = `$34363`, length 32000), loaded once per level by `move.w #$e,d0 / jsr $2cc98` (`022960`-`022964`) into `$54c80` = `$392e4`. The rest of the level setup draws into it only the minimap: comparing the live bg with the file, 4,096 differing pixels in rows 0-71, bbox `x 5 - 131, y 4 - 67`, **0 inside (120,0)-(255,15)**. The only non-black pixels of the file in rows 0-15 x 120-255 are 21 pixels at x = 253 (rows 8-15) and x 120-128 (rows 14-15), outside both approved boxes (line 2 starts at x = 136 and ends at 247).
- Four landscapes in one run, with the game's own landscape-cycle command `$7a` (`029bbe addi.w #1,$4737c.l / cmpi.w #4 / move.w #0,$4737c.l`, then fade, `jsr $2d326` loading the landscape's files, `jsr $1f764` redrawing the bg; reached from the Game options dialog; here written into the command slot `[$473c4]+1`): `work/gates/ui_lcycle.txt`, screenshots `ui_land{0,1,2,3}_{cat2,eff0,strip2,none}.png`, sheet `ui_landscapes_cat2.png` (green, snow, desert, rock): per landscape the bg rect colour counts are identical (`{0: 2155, 1: 7, 2: 2, 3: 3, 4: 4, 5: 3, 12: 2}`, i.e. the 21 pixels outside the boxes) and palette index 0 is `000` in all four (the palettes differ only in entries 5/6 as read from `$ff8240`); the tooltip looks the same in each in the sheet.
- The six CUSTOM GAMEs after the first conquest (`work/gates/ui_land.txt`, `ui_land_custom*.png`) all came out as the same green landscape (the "random" landscape of a custom game is the same each time here), the colour counts are the same.
- Zoomed views: keypad Enter (`$39766 = $17`: the full-screen close-up), keypad - (`4`, `1`), keypad + (`6`, `$a`): no frame, no icons, no sky; with the pointer left on the Earth icon position the hook draws nothing (`work/gates/ui_zoom.txt`, `ui_zoom_*.png`), because `cmpi.w #8,$39766.l` fails.

## 6. Cold boots

HD build (`pop2patch.py build --only` default set + tick set + display + `pop2_tooltip`, `p2tt.py cold`, `work/gates/ui_cold.txt`): STE 2 MB TOS 1.62 (`work/shots/ui_cold_ste_{cat2,strip4,none}.png`): `in_play=True marker='P2PO' turn 154`; Falcon 4 MB TOS 4.04 (`ui_cold_falcon_*.png`): `in_play=True marker='P2PO' turn 158`; both show the tooltip on the Earth category icon (EARTH EFFECTS / KEY: F3) and on the Fight icon (FIGHT / KEY: KEYPAD /) and none at (160,100). Not run: floppy build, ST / Mega ST / Mega STE / TT cold boots. The hook is 68000-only code (no 68020 addressing), reads only game RAM and writes only the back buffer through the game's own renderer.

## 7. Limits

- Wording of strips 3-6 is inferred (section 2); effect names are my table, not the game's strings (they agree with the game's Help texts).
- The tooltip follows the pointer by one rendered pass (the position is sampled in the pass; at 6.25 turns/s the render passes are at least one per 8 VBL, more at higher CPU speeds).
- Minimap, scroll pad, colosseum, the other side of the frame and the in-game dialogs have no tooltip (not icons in the sense of the task, or windows with their own loop: the hook runs only in the play loop).
- The strip index test reproduces the game's alias (u>>4 = 4 with v>>4 = 0 hits index 4): not reachable on screen (u <= 60 there).
