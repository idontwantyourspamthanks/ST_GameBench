# Populous: keyboard shortcuts and icon tooltips (PopUI, 2026-11-12)

Tags: **[obs]** = raw output in `work/gates/ui_*.txt` (Hatari 2.6.1, STE TOS 1.62 1 MB unless said) or quoted here; **[disasm]** = `tools/m68dis.py` on `work/dumps/g0.bin`
(address + text quoted); **[INFERENCE]** = not proven. Patches: `pop_keys`, `pop_keys2`, `pop_keys3`, `pop_keys4` (keys) and `pop_tooltip`, all `; default: no`.
Test tool: `tools/popuitest.py` (`words`, `scan`, `keys`, `realkeys`, `misc`, `phantom`, `gate`, `ttrect`, `tt`, `sheets`, `cold`, `cost`). Screenshots: `work/shots/ui_*.png`.

## 1. What was built

| patch | site (original bytes -> new) | blob | does |
|---|---|---|---|
| `pop_keys` | `$bb7c` `303900021d8e` (`move.w $21d8e.l,d0`) -> `jsr $c7000` | `$c7000-$c7143` hook, `$c7200` key table KT (21 pairs), `$c7240` action rows ACT (21 x 6 bytes); data `$c8000` + 32 | the pass hook: stamps the pass, takes the next key from the ring and performs the icon click |
| `pop_keys2` | `$2008c` `13c000037eec` (`move.b d0,$37eec.l`, the make-code store of the ACIA handler) -> `jsr $c7300` | `$c7300-$c7377` | key recorder (interrupt): scan code -> action number into the ring |
| `pop_keys3` | `$200a6` `2f08428010390002005f` (the first three instructions of the text-key converter) -> `jmp $c7380` + 2 nops | `$c7380-$c73b5` | typed-text guard |
| `pop_keys4` | `$1a508` `4e5600004a790003d566` (`link a6,#0` / `tst.w $3d566.l` of the dialog button test) -> `jmp $c73c0` + 2 nops | `$c73c0-$c73ff` | dialog guard |
| `pop_tooltip` | `$b93a` `4eb90000d4c0` (`jsr $d4c0.l`, the last call of the pass before the flip `jsr $16f16` at `$b940`) -> `jsr $c7400` | `$c7400-$c7901`; data `$c8200` + 1184 | hover tooltip |

Blob map: `$c7000-$c7901` of the allowed `$c7000-$c8fff`; data `$c8000-$c801f` (keys) and `$c8200-$c86a7` (tooltip). Everything below `$c8000` is inside `IMG_LIMIT`; the data blocks are
zero reservations (`; data:`), so `poppatch.py` needed no change. The five sites do not overlap any other patch (`verify: ALL OK`); PopTiming confirmed (IRC) that it touches
`$b632 $b6f4 $b800 $b940 $bbf8 $1672a` only and that `$bb7c` / `$b93a` run once per frame, in T and R passes. The three key-side patches check `cmpi.w #$4eb9,$0bb7c.l` (pop_keys installed)
before they touch their data, and the tooltip does the same for its key labels, so any subset of the five is safe (`pop_tooltip` alone shows names without keys).

## 2. The key map, checked against the real icons

Method: for every icon cell the click was injected (position + latch) at `$bba6` in the unpatched game and the order bytes (`$21e4a`: command, a, b) and the world changes were read
(`popuitest.py scan`; the same bytes appear in the key-vs-click table of section 4). Geometry: `$c424-$c6c2` (u = y + x/2 - 32, v = y - x/2 + 32; right panel u > `$112`: i = (u-`$110`)/16,
j = (v-`$20`)/16; left panel v >= `$92`: i = (u-`$60`)/16, j = (v-`$90`)/16), all 21 click points are the diamond centres (`popuitest.py geom` prints `cell()` for each).

| key | icon (artwork) | cell (panel i,j) -> click point | observed with the click [obs, section 4 table] |
|---|---|---|---|
| R | up / down arrows | left (6,1) -> (96,184) | `$21d8e` := 2, pointer shape 1 |
| Q | question mark | left (6,0) -> (112,176) | `$21d8e` := 1, shape 0 |
| P | ankh with down arrow | left (6,2) -> (80,192) | `$21d8e` := 6 (= 2 + 4), shape 2 |
| M | arrow to ankh | left (3,3) -> (16,176) | order `14,0,1`, behaviour word `$3b268` = 0 |
| S | arrow to flag | left (4,3) -> (32,184) | order `14,1,1`, `$3b268` = 1 |
| G | arrow to man | left (5,3) -> (48,192) | order `14,2,1`, `$3b268` = 2 |
| T | arrow to crossed swords | left (4,4) -> (16,192) | order `14,3,1`, `$3b268` = 3 |
| E | shock waves | left (2,0) -> (48,144) | order `3,x,y` (view position), mana -2500 |
| W | swamp | left (2,2) -> (16,160) | mode 10 (= 2 + 8) when mana > 5000; with 520 mana nothing (greyed): mode stays |
| K | sword and helmet | left (2,1) -> (32,152) | order `14,0,5`, mana -7500 |
| V | volcano | left (1,1) -> (16,144) | order `6,x,y`, mana -10000 |
| F | skull over waves | left (0,0) -> (16,128) | order `14,0,4`, mana -40000 |
| A A | skull and crossbones | left (1,0) -> (32,136) | order `14,0,3` (no mana) |
| L | ankh in brackets | left click on (7,0) -> (128,184) | view to the leader |
| Z | the same cell | **right** click -> (128,184), `$c420(0)` | view to the magnet (right latch `$3c514`) |
| B | crossed swords in brackets | left (7,1) -> (112,192) | view to the next fight (no change when there is none) |
| N | knight in brackets | left click on (8,0) -> (144,192) | view to the next knight (no change when there is none) |
| H | the same cell | **right** click -> (144,192) | view to the next own building |
| Space | zzZ | right (1,3) -> (272,192) | `$3b2b2` toggles |
| U | music notes | right (0,3) -> (256,184) | `$2203a` toggles |
| X | FX | right (0,4) -> (240,192) | `$2195e` toggles |

Draft versus reality: **no key had to be dropped or renamed**; all 21 draft keys are real icons. What the draft left implicit and is now pinned: Z and H are the *right-click* halves of the
leader / knight cells (`$c420` takes the click kind as its argument: `00bbb6 move.w $3d566.l,d0 / 00bbbc seq.b d0 / 00bbc4 jsr $c420` -> 1 for the left, 0 for the right button);
the three icons in the right-hand column that open dialogs have no key in the draft and got none: scales (click at (304,160)) = "OPTIONS FOR GOOD" dialog (can modify land, attack towns ... aggression,
rate), globe (304,176) = "GAME SETUP" (one / two players, game options, save, load, next map, restart, surrender), telephone (304,192) = the link dialog [INFERENCE: nothing visible without a link];
screenshots `work/scratch/popui/dlg_*.png`. The tooltip names them "Options", "Game setup", "Link up". The scroll arrows (left cells (3..5,0..2)) are the keypad's job (unchanged);
the centre cell (4,1) = "view to the selected shield's walker" [disasm `00c708 cmpi.w #$4,-$2(a6) / 00c712 cmpi.w #$1,-$4(a6) / 00c71a move.w $3c504.l,d0` ...; not clicked].
Scancodes are physical key positions (a QWERTZ keyboard's Z/Y are swapped, a French one's A/Q/W/Z/M differ): the table is `KT` in `pop_keys.s`.

Costs shown in the tooltip (verified in the code, mana is the long at `$3b264 + 16 * player + $c`): table of longs at `$219c6 + 4k` = 10, 200, 2500, 5000, 7500, 10000, 40000 [obs, `m` of
`work/dumps/g0.bin`]; compares: raise / lower `$11776 cmp.l $219c6.l` (10 + 4 per cell changed: `$117a8-$117cc`, shown as "UP / DOWN" without a cost), magnet `$11212 cmp.l $219ca.l` (200), earthquake
`$123ae cmp.l $219ce.l` (2500), swamp `$12a72 cmp.l $219d2.l` (5000), knight `$12c16 cmp.l $219d6.l` (7500), volcano `$1269a cmp.l $219da.l` (10000), flood `$11fc8 cmp.l $219de.l` (40000);
Armageddon has none [obs: mana unchanged by the order].

## 3. How a key acts, and the race that decided the design

**A key calls the game's own icon handler** (`pop_keys`, site `$bb7c`, reached by every path of the pass after the keypad scroll): it clears both click latches `$3d566` / `$3c514`, writes the
cell centre to `$3c556` / `$3c55a`, calls `$c420(left?)`, and puts the idle latch back the way the main loop's `$bbcc-$bbf2` would (`(word == 2) ? 2 : 1`; the one `$c420` consumed is 2:
`$d09a-$d0f2 tst.w $3d566.l / bne / move.w #2,$3d566.l`). Everything `$c420` does is the game's: the icon flash `$16b64`, the mana tests, greyed icons, the mode words, the order bytes.

Why not "latch a click and let the main loop find it" (what the first draft assumed): the VBL routine copies the live pointer into the click position whenever a latch is idle
([disasm] `016cb4 move.w #1,$3d566.l / 016cbc btst.b #2,d0 / 016cc0 beq.w $16ccc / ... 016ccc move.w $24786.l,$3c556.l / 016cd6 move.w $24788.l,$3c55a.l`; the right latch does the same at
`016cf8-016d1a`; a latch at 0 skips its half), so a position written at `$bb7c` is overwritten by the pointer at the next VBL, before the land handler `$11a24` (raise / lower mode, `tst.w $3d566.l` at
`$11ccc`) or `$c420` runs. Observed with the debugger-injected reference clicks: **2 of 21** acted at the pointer's position (75,175) instead of the icon (first `scan`/`keys` runs, `work/scratch/popui`).
With both latches 0 for the length of the call `$16c96` copies nothing, and the position is set after the latches, so it cannot move before `$c420` has read it (`$c424-$c450`, the first
instructions). A key with the real pointer on land in raise / lower mode never touches the land (`misc` (A), below).

**At most one order at a time**: the key waits while the local player's command byte (`$21e4a + $2e * $3b03c`) is still non-zero, i.e. until `$1e750` (`jsr` at `$bbfa`) has executed and cleared
the order of the click before (a second click in the same turn would overwrite it). This also keeps working while the world is paused (a turn counter would not: `$3c506` stands still, and Space has
to un-pause) and, [INFERENCE from PopTiming's message, not run together], under its render-only passes (the order stays until the next turn pass). A real click latched at the moment (`$3d566` or `$3c514` = 0) is handled first; the key waits a pass.

**Armageddon needs the key twice** (`AWIN` = 150 VBLs): the first press only arms (`KD+4` = VBL + 1) and `pop_tooltip` shows "ARMAGEDDON? / A AGAIN"; any other key or the end of the window disarms.

## 4. Only keys typed during map play count (Powermonger's phantom-click rule, `powermonger/work/notes/phantom_click.md`)

The interrupt hook runs from the moment the game's ACIA handler exists, long before anybody knows who will read a key. Three independent rules keep typed text and dialog keys out:

1. **Time window** (`pop_keys` + `pop_keys2`): every pass stamps `LASTV` with the VBL counter `$16d2a` (`00016dde addq.l #1,$16d2a.l`, +1 per VBL); the interrupt drops a press more than `WIN` = 150 VBLs
   after the stamp, and the first pass after such a gap empties the ring and the arm. Name entry, the title and menus, long disk accesses are outside the map loop: all dropped.
2. **Text guard** (`pop_keys3`): every text input of the game polls `$200a6` (callers: `$b946` the main loop, `$18a20` the name / file field `$188ee`, `$1f3f6`, `$1fe96`, `$1ff62`). A poll whose return address
   is not the main loop's (`cmpi.l #$0b94c,(sp)`) empties the ring (`head := tail`) and the arm.
3. **Dialog guard** (`pop_keys4`): `$1a508` is the dialog button test, polled by 14 call sites, none in the map loop. Same flush.

Test (`popuitest.py phantom`, raw output `work/gates/ui_phantom.txt`): the game's own text entry `$188ee` is started by a scaffold stub (`move.l ... jsr $188ee`, returns at Return) and the Options dialog is
opened by an injected click on the scales icon; the five shortcut keys `R P M T Q` are typed through the real chain (Hatari key event -> IKBD -> ACIA -> `$2008c`). State before: mode 2, behaviour 1.
Control with `WIN` = 1500 VBLs (so only the guards, not the time window, can stop a key) and without `pop_keys3` / `pop_keys4`:
```
after typing 'RPMTQ' into the text entry: ring (0, 5) ...
after Return + 6 s of map passes: ring (5, 5) state {'mode': 1, 'beh': 3, ...} -> CHANGED (keys acted)
after closing the dialog + 7 s: ... {'mode': 1, 'beh': 3, ...} -> CHANGED (keys acted)
```
All four key patches, `WIN` = 1500: `after typing 'RPMTQ' into the text entry: ring (5, 5)` (recorded and flushed), `after Return + 6 s ... UNCHANGED`, dialog `UNCHANGED`. All four, shipped `WIN` = 150: text entry
`UNCHANGED`, dialog `UNCHANGED`. (The ring numbers are head, tail.) Known limit: a dialog that never polls `$1a508` / `$200a6` between a key and the end of its 3 s window and closes without polling would leak the key; every
dialog tried (Options, text entry) polls on the click that closes it.

## 5. The tooltip

Draws into the back buffer `$3c510` at `$b93a`, after `jsr $d4c0` (the shield panel at the top right, which does not overlap) and before the flip. Every pass begins with the clean-background copy (`$14a28`, the
pass's first drawing step; `pop_bgcopy` makes it a `movem` copy), so nothing is erased and nothing can be left behind: the backdrop is restored exactly when the tooltip clears because the next frame never
contained it [obs: `ttrect`, below].
* Hit test = the game's own geometry (section 2) with `divs` truncating like the game's, then the tables LT (9 x 5) / RT (3 x 5) -> icon number 1-24 (+25 = the Armageddon hint). Cached per pointer position.
* Text: the game's font `$2364a` (40 bytes per character: mask byte + 4 plane bytes per row; `00018162 mulu.w #$28,d0 / 0018166 lea.l $2364a.l,a3 / 0018174 move.b (a0),d0 / and.b d4,d0 / or.b (a3)+,d0`).
  `$180f4` itself cannot be used for the approved rectangles: it rounds x down to a multiple of 8 (`0018106 move.w $c(a5),d0 / 018110 lsr.w #3,d0 / bclr.b #0,d0 / lsl.w #2,d0` plus `btst.b #3,$d(a5)`), but the
  approved rectangle starts at x = 84 and the second line at x = 100 (= 4 mod 8). The blob therefore merges the glyphs itself: character k of a line sits at pixel 84 + 8k, the glyph's left nibble in the low nibble
  of screen byte k, its right nibble in the high nibble of byte k+1, `and mask / or data` per plane, exactly the renderer's per-pixel result. Line 1 (rows 0-7) 16 characters, line 2 (rows 8-15, x 100) 9.
  The game's lower-case glyphs are red, the capitals gold (the font is capitals only): "Earthquake (E)" prints a gold E, red "ARTHQUAKE", gold "(E)".
* Compose once per icon (font -> cache of mask / plane words per 16-pixel group, 1,120 bytes), merge the cache into the buffer every pass (about 7.5-9.4 k cycles).
* Wording (our own; `popuitest.py words` checks <= 16 / <= 9 characters with and without key labels):

| icon | line 1 | line 2 |
|---|---|---|
| flood | Flood (F) | COST 40K |
| Armageddon | Armageddon (AA) | |
| volcano | Volcano (V) | COST 10K |
| earthquake | Earthquake (E) | COST 2500 |
| knight | Knight (K) | COST 7500 |
| swamp | Swamp (W) | COST 5000 |
| go to magnet / settle / gather / fight | Go to magnet (M) / Settle (S) / Gather (G) / Fight (T) | BEHAVIOUR |
| query | Query (Q) | INFO MODE |
| raise / lower | Shape land (R) | UP / DOWN |
| papal magnet | Place magnet (P) | COST 200 |
| leader / magnet view | To leader (L) | Z: MAGNET |
| battle view | To battle (B) | |
| knight / building view | To knight (N) | H: HOUSE |
| scroll arrows / centre | Scroll (KEYPAD) / To selection | |
| scales / globe / telephone | Options / Game setup / Link up | |
| music / effects | Music (U) / Effects (X) | ON / OFF |
| pause | Pause (Space) | |
| armed Armageddon | ARMAGEDDON? | A AGAIN |

"Z: MAGNET" and "H: HOUSE" appear only with the keys installed (marker byte 2 in the string); without `pop_keys` the key labels `(F)` disappear (`ui_tt_keys_off_on_none.png`).
Costs of 10K / 40K are written "10K" / "40K" because line 2 has 9 characters.

## 6. Gates (raw outputs in `work/gates/ui_*.txt`)

**(a) key == click** (`popuitest.py keys --selftest`; `work/gates/ui_keys_vs_click.txt`). Snapshot `genesis_start`, 23 events 5 turns apart (query, raise, magnet mode, the four behaviours, the five views, music and effects twice, swamp,
earthquake, knight, volcano, flood, Armageddon first press, Armageddon), once with mana 520 (greyed icons: swamp and the spells refuse) and once with 60000. Reference = the unpatched game with a debugger-injected
click at `$bba6` and the position rewritten at `$bbc4`; patched = a key (the action number poked into the ring as the interrupt hook does). World RAM `$21100-$3d7ff` compared at `$bbfa` of the pass (orders not yet executed)
and three turns later, excluding the sample player `$24990-$249a3` and, in the first comparison only, the click position `$3c556-$3c55b` which the VBL overwrites with the pointer once the handler has run (it does so
in the original too; it is compared three turns later):
```
-> lowmana key: 23/23 identical        -> lowmana click2: 23/23 identical       (click2 = a second reference run: the harness's own noise)
-> highmana key: 23/23 identical        -> highmana click2: 23/23 identical
```
(orders per event, e.g. `earthquake order click (3, 3, 1) key (3, 3, 1)`, `knight (14, 0, 5)`, `volcano (6, 3, 1)`, `flood (14, 0, 4)`, `armageddon (14, 0, 3)`, `to_magnet (14, 0, 1)`, `settle (14, 1, 1)`.)
Negative control (`--mutant key_pos`, the earthquake click point moved 8 rows down): **17/23 identical, six events differ**: `earthquake order click (3, 3, 1) key (0, 0, 0)`, mana 60042 -> 60042 (no mana spent) ... as the gate must.

**(b) real keys through the whole chain** (`realkeys`, host key -> Hatari -> IKBD -> ACIA interrupt -> `pop_keys2` -> ring -> `pop_keys`): `work/gates/ui_realkeys.txt`. All 23 key presses
act: Q mode 1, R mode 2, P mode 6, M/S/G/T behaviour 0/1/2/3, L/Z/H change the view, B/N leave it (no battle / knight), U and X toggle `$2203a` / `$2195e` twice, W mode 10, E K V F cost 2500 / 7500 / 10000 / 40000
mana, Space pauses and un-pauses (`pause = 1` then `0`). (An earlier build limited a key to one per turn: Space could not un-pause, `$3c506` stands still while paused; fixed by the order-slot rule, section 3, and shown by `misc` (B) `pause = 1` then `0`. Run A was made before that change; run B with order logging aborted at K on a harness log-parsing error and was not repeated: the orders of the 21 key==click gate are the order evidence.)
Cold boots (section 8) repeat Q R M T L on HD, floppy, TT and Falcon.

**(c) pointer on land** (`misc` (A), `work/gates/ui_misc.txt`): pointer poked to (200,100) (land), raise / lower mode, real key M: `behaviour 1 -> 0, orders [(14, 0, 1)], land bytes unchanged: True, mode 2`; then Q, R: land unchanged.
**(d) Space** `Space #1: pause = 1`, `Space #2: pause = 0`. **(e) Armageddon**: A once -> armed, no order; A then X -> disarmed; A after another key -> armed only; 7 s later -> arm ran out; A A -> order `(14, 0, 3)`.

**(f) pixel gate, pointer away from every icon** (`popuitest.py gate --away`; popabtest's machinery, 305-row pointer / click / scroll / junk / shape / x script with every row that would hover an icon moved to (200,100);
`work/gates/ui_gate_away.txt`): both buffers + world RAM every flip + two mid-frame samples per flip, three snapshots:
```
busy_castles         pop_tooltip                                      IDENTICAL: flips compared 305 ..., mid-frame samples 610, bad flips 0, bad samples 0, world 0
busy_castles         pop_keys+pop_keys2+pop_keys3+pop_keys4+pop_tooltip IDENTICAL ... (same for busy_quake_volcano, genesis_start)
GATE IDENTICAL (exit 0)
```
The first flips (1-2) are drawn with the snapshot's own pointer, which stands on a scroll arrow: they correctly show a tooltip (252 bytes in rows 2-6 at byte 40) and are excluded and reported. The script's keypad scroll rows
run with the patches installed and the frames are identical: the keypad scroll works. Negative control (`--mutant tt_always`: the hit test always answers "flood"): **DIFFERENT**, 606 bad flips of 305 x 2 buffers.

**(g) pointer visiting icons** (`popuitest.py ttrect`, popabtest's original script): every differing screen byte of every flip lies inside the two tooltip rectangles (rows 0-7 groups 5-13, rows 8-15 groups 6-10), the flips where the pointer is
not on an icon (this pass or the two before: the older buffer holds the frame before) are byte-identical to the original, world RAM identical: `TTRECT OK` (82 of 303 flips differ, 0 outside the rectangles, 0 with the pointer away,
world differs in 0). Negative control `--mutant tt_wide` (blit one group to the right): `TTRECT FAILED`, differing bytes outside the rectangles.

**(h) phantom keys**: section 4.

**(i) cost** (`cost`, profiler, busy_castles, 8 MHz): cycles inside the blobs per pass: pointer away **789 / 813** (0.04 % of a 1.85 M-cycle pass), pointer on an icon **9,374** (flood) / **7,557** (arrows) (0.4-0.5 %). One key press: the interrupt hook and the pass that performs it add the game's own `$c420` work (not measured separately).

## 7. Screenshots (`work/shots/`)

`ui_tt_spells.png`, `ui_tt_behaviour.png`, `ui_tt_modes.png`, `ui_tt_views.png`, `ui_tt_panel.png`, `ui_tt_armageddon_hint.png` (the whole screen with the group's first icon hovered, below it the top strip, 3x, of every icon of the
group), `ui_tt_keys_off_on_none.png` (names only / with keys / no hover), `ui_cold_ste_hd_{hover,away}.png`, `ui_cold_ste_floppy_{hover,away}.png`, `ui_tt_floppy_hover.png`, `ui_falcon_floppy_hover.png` (cold boots).

## 8. Machines

Cold boots with the five patches (`work/gates/ui_cold.txt`): STE TOS 1.62 1 MB HD build (`POPO`, five sites patched, real keys Q R M T L act, tooltip), STE floppy build (same), TT TOS 3.06 4 MB `--mmu` floppy (text base moved
by `$3e48`: sites patched at `$bb7c + $3e48` ..., blobs and data not moved, keys and tooltip act), Falcon TOS 4.04 4 MB floppy with `pop_fal_ym*` (`D = $5216`, same). Not run: 2 / 4 MB STE, Mega STE, plain ST, 60 Hz, HD on TT / Falcon
(PP's HD build crashes there unpatched), a real two-player link game, paint mode [INFERENCE: keys act as clicks there, like a click would].

## 9. Open points

* The Armageddon second press needs the same arm window at 50 and 60 Hz (150 VBLs = 3.0 / 2.5 s).
* A QWERTZ / AZERTY keyboard's letters are physical positions.
* Keys for the three dialog icons (Options, Game setup, Link) were not in the draft and are not added.
