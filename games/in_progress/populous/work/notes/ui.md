# Populous: mouse, clicks, icons, keys, text, tooltip area

Second pass, 2026-11-11. Dumps `work/dumps/g0.bin`, `busy.bin`. The draft had none of this ("click words and icon table not found").

## Mouse and buttons

The IKBD is in absolute mode and is asked for the position once per VBL (`$16dd0  move.b #$d,$2(a6)`). The ACIA handler `$1ffc8` collects the `$f7` reply (same bytes as Powermonger's handler, `bullfrog_family.md`):

```
020000  cmpi.b #$f6,d0 / bcs $20066          ; a key
020008  cmpi.b #$f7,d0 / bne ... / move.b #5,$2005e      ; 5 more bytes follow
02003e  move.b $20061,$2478a                 ; buttons
020048  move.w $20062,$24786 / move.w $20064,$24788      ; x, y (0..319, 0..199)
```

Keys: make code to `$2005f` and `$37eec` (a release stores 0, so a tap shorter than one pass is lost: a pass is 0.11-0.33 s); Shift sets `$3d576`; `$200a6` turns the code into ASCII (`$37ef8`) with the tables at `$200d8` / `$20158`.

The click latch is a three-state word per button, run by the VBL routine (`$16c96`): left = `$3d566` (packet bit 2), right = `$3c514` (bit 0).

```
016c9c  tst.w $3d566 / beq skip              ; 0 = a click is waiting for the main loop
016ca4  cmpi.w #2,$3d566 / bne + / btst #2,d0 / bne skip     ; 2 = handled, still held
016cb4  move.w #1,$3d566                     ; 1 = up
016cbc  btst #2,d0 / beq + / move.w #0,$3d566                ; pressed: latch
016ccc  move.w $24786,$3c556 / move.w $24788,$3c55a          ; and latch the position
```

The main loop (`$bb90`-`$bbf8`) calls the land handler `$11a24` (pointer modes 2, 4, 8) or the shield test `$d42c`, then `$c420(left?)` when either word is 0, and ends the pass with `word = (word == 2) ? 2 : 1`; a handler that wants no auto-repeat sets 2 itself (`$d0e2`). Raise / lower repeats while the button is held because `$11a24` reads the state, not the latch.

Pointer mode: `$21d8e` (1 shield / query, 2 raise-lower, +4 place the papal magnet, +8 place a swamp); pointer shape `$2169a`.

## From a click to a command

Nothing acts directly. Every order is three bytes in the player's record (`$21e4a` + `$2e` * player: command, a, b), executed for both players at the end of the pass by `$1e750` through the jump table `$21652`. The same bytes go over the serial link in a two-player game, and the computer player writes them too (`$1363a`). **A key patch only has to write these bytes** (or the mode word); `$bab0`-`$baf6`, the game's own "CHEAT" key, does exactly that.

| Command byte | a, b | Routine |
|---|---|---|
| 1 / 2 | vertex x, y | raise `$118aa` / lower `$11738` |
| 3 | view x, y | earthquake `$1238e` |
| 4 | cell x, y | swamp `$12a52` |
| 5 | cell x, y | place the papal magnet `$111fc` |
| 6 | view x, y | volcano `$1267a` |
| 7-13 | cell | paint mode only: place walker / leader, cycle tree, cycle rock, delete |
| 14 | a = argument, b = sub-command | `$1f138` (jump table `$21670`): 1 behaviour a (0 go to the magnet, 1 settle, 2 gather, 3 fight: names from the icon art below), 2 the link dialog, 3 Armageddon, 4 flood, 5 knight, 6 pause (`$3b2b2`), 7 and 8 the two right-hand dialogs |

## Icon hit test (`$c420`)

There is no rectangle table. The handler turns the click into isometric coordinates and divides by 16:

```
00c424  u = y + x/2 - 32        v = y - x/2 + 32
00c454  0 <= u,v < 64           -> the minimap: view = (u-3, v-3)
00c4e2  u > $112                -> right panel:  i = (u-$110)/16, j = (v-$20)/16
00c698  v >= $92                -> left panel:   i = (u-$60)/16,  j = (v-$90)/16
```

The centre of cell (i, j) is at x = u - v + 64, y = (u + v)/2 with u, v at the cell centre; each cell is a diamond 32 wide and 16 high. Decoded from the branches of `$c420` (function names from the commands above; "icon" is what the artwork shows):

| Panel, cell | Centre (ST x, y) | Does (code) | Icon |
|---|---|---|---|
| left (0,0) | 16, 128 | command 14/4: flood | skull over waves |
| left (1,0) | 32, 136 | command 14/3: Armageddon | skull and crossbones |
| left (1,1) | 16, 144 | command 6: volcano at the view | volcano |
| left (2,0) | 48, 144 | command 3: earthquake at the view | shock waves |
| left (2,1) | 32, 152 | command 14/5: knight | sword and helmet |
| left (2,2) | 16, 160 | swamp mode (`$21d8e` \|= 8), if affordable | swamp |
| left (3..5, 0..2) | 48..80, 152..176 | scroll the view by one cell; centre (4,1) = view to the selected shield's walker | eight arrows around a shield |
| left (3,3) | 16, 176 | command 14/1 a=0: go to the papal magnet | arrow to an ankh |
| left (4,3) | 32, 184 | command 14/1 a=1: settle (the default, `$bcac`) | arrow to a flag |
| left (5,3) | 48, 192 | command 14/1 a=2: gather | arrow to a man |
| left (4,4) | 16, 192 | command 14/1 a=3: fight | arrow to crossed swords |
| left (6,0) | 112, 176 | mode 1: query (click a walker or building to put it on the shield) | question mark |
| left (6,1) | 96, 184 | mode 2: raise / lower | up and down arrows |
| left (6,2) | 80, 192 | mode +4: place the papal magnet | ankh with a down arrow |
| left (7,0) | 128, 184 | left click: view to the leader, or to the magnet if there is none; right click: view to the magnet | ankh between brackets |
| left (7,1) | 112, 192 | view to the next fight (peeps with state 8) | crossed swords between brackets |
| left (8,0) | 144, 192 | left click: view to the next knight; right click: view to the next own building | knight between brackets |
| right (0,0) | 304, 160 | command 14/7 | scales |
| right (1,1) | 304, 176 | command 14/8 | globe |
| right (2,2) | 304, 192 | command 14/2 | telephone |
| right (0,3) | 256, 184 | toggle `$2203a` | music notes |
| right (0,4) | 240, 192 | toggle `$2195e` (sound effects: the VBL tests it at `$16d88`) | FX |
| right (1,3) | 272, 192 | command 14/6: pause | zzZ |

Checked against the artwork: `work/shots/ui_left_panel_keys.png` (the left panel, 6x, with the proposed key letter printed on each cell centre) and a screenshot for the right panel (scales at ST (305,160), globe (305,176), telephone (305,192), notes (257,185), zzZ (273,191)). In `$c420` the argument is 1 for a left click (`$bbb6`: `seq` on the left word). [INFERENCE] 14/7 = game balance, 14/8 = world / game options, from the icons only. The manna bar across the top right is display only (no branch in `$c420` for it).

**Draft key map checked.** The draft proposed "S shield, K knight, P ankh, B book, M magnifier, H house, C compass, ? help". There is no book, magnifier, compass or help icon in the handler; shield, knight and ankh exist.

## Keys

The game already reads: keypad 1-9 (scan `$67`-`$6f`) = scroll, at `$bb2e`; keypad `*` with the pointer at the top right in shield mode = the developers' cheat; in paint mode only F1-F8, Delete and 1-9 (`$1d9d4`). Everything else is free in play; the default branch `$bafe` only acts in paint mode.

Proposed map (each key writes the command bytes or mode word listed above; ignored in dialogs, paint mode and while paused except Space):

| Key | Action | | Key | Action |
|---|---|---|---|---|
| R | raise / lower mode | | E | earthquake |
| Q | shield (query) mode | | W | swamp mode |
| P | papal magnet mode | | K | knight |
| M | behaviour: go to the magnet | | V | volcano |
| S | behaviour: settle | | F | flood |
| G | behaviour: gather | | A, typed twice | Armageddon |
| T | behaviour: fight | | Space | pause |
| L | view to the leader; Z view to the magnet | | B | view to the next battle |
| H | view to the next building; N the next knight | | cursor keys | scroll (as the keypad) |
| U | music on / off | | X | sound effects on / off |

A tap must not be lost: take the key in the ACIA handler into a pending byte and consume it in the pass (Powermonger's `qol_keys2`), and count only keys typed while the loop runs (`powermonger/work/notes/phantom_click.md`: this game has typed input too, e.g. the dialog at `$1f3f6`-`$1f416` compares the typed ASCII).

## Text renderer and font

`$180f4(screen, x, y, string)`: 8 x 8 cells at any x on a 4-pixel grid [INFERENCE from the `lsr #3 / bclr #0 / lsl #2` on x], CR / LF = next line (8 rows), characters from `$20`. Font at `$2364a`, 40 bytes per character: 8 rows of mask byte + 4 plane bytes, drawn with `and` mask / `or` data, so the background shows through and the colour is the font's own (gold on brown in the dialogs).

```
01815e  subi.w #$20,d0 / mulu.w #$28,d0 / lea $2364a,a3 / adda.l d0,a3
01816e  move.w #7,d1
018172  move.b (a3)+,d4                      ; mask
018174  move.b (a0),d0 / and.b d4,d0 / or.b (a3)+,d0 / move.b d0,(a0)    ; x 4 planes
0181a2  adda.l #$a0,a0 / dbra d1,$18172
```

It brackets itself with `$16d2e` / `$16d5e` (hide / show the VBL pointer). The game prints with it into the back buffer at the top left (`$ba7c`: "CHEAT" at x 0, y 10).

## Tooltip area

The user's "white area at the top of the book page" is there: the open book's pages run along the top of the screen between the minimap and the manna bar. In the clean background (`work/shots/tt_bg_clean.png`, zoom `tt_book_top_zoom4.png`) every pixel is a page grey (palette 3, 4, 5 = `$444`, `$555`, `$666`; 2 for the gutter line) in these spans:

| Rows | x from..to | Width | Game-font characters |
|---|---|---|---|
| 0 | 70..227 | 158 | |
| 0..7 | 84..213 | 130 | 16 |
| 8..11 | 92..201 | 110 | 13 |
| 12..15 | 100..174 | 75 | 9 |

The span moves right by 2 pixels per row on the left and is cut on the right by the first manna-bar icon from row 8 on. It is not one flat colour: the gutter (7 pixels of palette 3 and 2) and a band of palette 5 cross it diagonally. The draft looked for a flat band and so found none.

Candidates (magenta / cyan / yellow outlines in `work/shots/tt_candidates_rects.png`):

- **A: (84,0)-(213,7)**, one line of 16 characters of the game font drawn with its mask over the page (`tt_candidate_A_text.png`). The page art stays; gold on grey is readable.
- **B: A plus (100,8)-(171,15)**, a second line of 9 characters (`tt_candidate_B_two_lines.png`).
- **C: A with our own 4 x 6 font**: 32 characters in one line, dark ink on the page. More text, one more table (about 400 bytes).

Because the whole frame is rebuilt from the clean background every pass, a tooltip drawn into the back buffer after `$14a28` needs no erase and cannot leave marks; with no tooltip the frame is the original.

Draft wording, ours, sized for C (32) with the short form for A (16) in brackets:

| Icon | Text |
|---|---|
| raise / lower | `Raise/lower land (R) 10 a point` [`Shape land (R)`] |
| shield | `Query a walker or town (Q)` [`Query (Q)`] |
| papal magnet mode | `Place the papal magnet (P) 200` [`Place magnet (P)`] |
| go to magnet | `Walkers go to the magnet (M)` [`To magnet (M)`] |
| settle | `Walkers settle new land (S)` [`Settle (S)`] |
| gather | `Walkers join together (G)` [`Gather (G)`] |
| fight | `Walkers seek a fight (T)` [`Fight (T)`] |
| earthquake | `Earthquake in view (E) 2500` [`Earthquake (E)`] |
| swamp | `Lay a swamp (W) 5000` [`Swamp (W)`] |
| knight | `Leader becomes a knight (K) 7500` [`Knight (K)`] |
| volcano | `Volcano in view (V) 10000` [`Volcano (V)`] |
| flood | `Flood: the sea rises (F) 40000` [`Flood (F)`] |
| Armageddon | `Armageddon: last battle (AA)` [`Armageddon (AA)`] |
| view buttons | `Show the leader (L)` / `Show the magnet (Z)` / `Show a battle (B)` / `Show a knight (N)` / `Show a town (H)` |
| pause, sound | `Pause (Space)` / `Music (U)` / `Effects (X)` |
