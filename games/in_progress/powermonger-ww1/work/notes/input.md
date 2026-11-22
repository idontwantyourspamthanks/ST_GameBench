# Powermonger WW1: the input pipeline and the click synthesis

Evidence tags: **[obs]** = raw emulator/debugger output pasted or reproducible with the stated
command, **[disasm]** = read from a live RAM dump (`work/dumps/mapview_live.bin`) or the
options-screen dump, **[INFERENCE]** = not verified. The 1990 sibling
(`../../done/powermonger/`, `work/notes/qol.md`, `patches/qol_keys.s`) is the reference.

## 1. The IKBD ACIA handler (vector `$118` -> `$e52`) [disasm, obs]

```
0e52: movem.l d0-d2/a0-a1,-(a7)
0e56: lea $fc00.w,a1
0e5a: d2 = (a1)                 ; ACIA status
0e5c: btst #7,d2 / 0e62 btst #0,d2   ; RDA and IRQ set?
0e68: bsr $e78                 ;   process the data byte ($fc02 = 2(a1))
0e6c: bclr #6,$fa11.w          ; ack the MFP ACIA interrupt
0e72: movem.l (a7)+,d0-d2/a0-a1 / rte
0e78: d0 = (a1)+2              ; the byte ($fffc02)
0e7c: tst.b $1d2ae             ; the packet state
0e82: bgt $eb8                 ;   >0: a packet body byte
0e84: blt $ea8                 ;   <0: the $fe joystick state
0e86: cmpi.b #$f6,d0 / bcs $ef6    ; scancodes < $f6 = the keyboard path
0e8e: cmpi.b #$f7,d0 / bne $e9e    ; $f7 = the absolute-mouse packet header
0e94: move.b #5,$1d2ae         ;   state = 5
0e9e: move.b #$fe,$1d2ae       ; any other byte = the joystick state
```

### The keyboard path `$ef6` [disasm]
- Every scancode is stored in the **keydown table `$2ec8c`** (`st.b (a0,d0.w)` on down,
  `sf.b` on up alike), the **last key byte at `$1d2b0`**, a copy at `$2eda9`.
- Shift tracking: scancodes `$2a`/`$36` set, `$aa`/`$b6` clear `$2edaa`.

### The absolute-mouse packet `$eb8` [disasm, obs]
- Body bytes (`$f7` + 5) are stored at **`$1d2b1..$1d2b5`**: `[buttons, x, y]` (x at
  `$1d2b2/3`, y at `$1d2b4/5`).
- At packet end: **`$1d2af` = the buttons byte**, `$2edb2/$2edb4` = x/y (the title program's
  tracked words; the 3D view copies them the same way).
- [obs] A live capture during a host mouse move showed the packet words: buttons went
  `$00`, then `$04` with a movement packet during a host button hold (the release encoded `$08`).

## 2. The VBL dispatch and the click latch (vector `$70` -> `$75e`) [disasm, obs]

`$1d2af` (the buttons byte) indexes the dispatch table at `$79a` **every VBL**:

| index | target | action |
|---|---|---|
| 0 | `$866` | the idle path: sends the IKBD "set absolute mouse position" (`move.b #$d,$fc02`, then x/y from the game's own state) **every frame** |
| 1 | `$7c2` | right-button latch: `$2edb8 = 1`, `$2edae/$2edb0 = $2edb2/$2edb4`, `$2ed90 -> $2ed94`; down-seen `$2edbe` |
| 4 | `$81e` | **left-button latch: `$2edb6 = 1`**, click pos `$2edae/$2edb0 = $2edb2/$2edb4`, `$2ed90 -> $2ed94`; down-seen `$2edbc` |
| 8 | `$85e` | release: clears `$2edbc` |
| 10 | `$856` | release: clears `$2edbe` and `$2edbc` |
| 2/5/6 | `$804`/`$80e`/`$7fa` | button variants (edge cases) |

- The latch's **click lifetime**: the latch copies the **pass counter `$2ed90`** to
  `$2ed94`; the main loop clears the latch when `$2ed90 != $2ed94` (`$144b2`/`$144c0` at the
  options screen). This is the 1990 game's `$2df70`/`$2df74` click lifetime (see the tick
  port: once the world counter becomes per-tick, these three operands need the per-pass
  counter).
- The latch is consumed by screen-specific handlers; at the map view the input/UI section
  starts at `$13e82` (`tst.w $2edb6` / `$2edb8`), and the icon hit test `$6c16` runs at
  `$13e70`.

## 3. The icon panel (`$6c16`, the consumer family) [disasm, obs]

- `$74b8` set = a **drag-scroll** of the panel (moves the panel by the pointer delta,
  `$6c22-$6ca8`).
- Otherwise (`$6cac`): the click latch + the click position are tested against the panel
  descriptors.
- Panel descriptor table (up to 4 entries, 8 bytes each) at `$74c0`: `{icon_set_offset,
  packed_box}` where the box's top y = the low byte, left x = `(word >> 4) & $1f0`.
- The icon set: `(height, width, then height*width icon ids)` — cells are **4 x 6 px**; the
  clicked cell = `((x - left) >> 2, (y - top) / 6)`, the icon id = the cell's byte.
- [obs] At the options screen the panel resolved to: (112,72) selects "Start New Conquest",
  (130,88) activates it, (130,106) = "Continue Conquest" (opens the save-disk requester
  "DISK STATUS REQUESTER / SAVE GAME DOES NOT EXIST"), (60,20) on the chart = the first
  island. The rows have a select spot and a separate activate spot (+18,+16 px).
- At the map view the live table had two active entries: icon set `$017c` at box (0,0) and
  icon set `$05e8` at box (0,12) [obs: live dump; the map-view command cells still need
  mapping — see the open items].

## 4. Why clicks need `poke_click` in Hatari [obs, INFERENCE]

The idle path (`$866`) re-programs the IKBD's absolute mouse position **every VBL**. Hatari
only delivers an absolute-mouse button packet together with movement, so a stationary host
click never reaches the game (verified: the buttons byte stayed 0 during a 6-sample stationary
hold; it became `$04` only in packets that carried a move). `PMWW.poke_click(x, y)` therefore
moves the host pointer to the target (the game's own position-forcing feedback then keeps its
tracked words there), writes the buttons byte the parser would have written (`$1d2af = 4`),
re-arms it until the down-seen word `$2edbc` proves the game's latch code ran, then releases
(`10`, then `0`). This is the qol_keys synthesis template: **write the same words the mouse
path writes** — click position + latch + pass stamp — and the game handles it as a click.

## 5. The map-view keys and the command strip [disasm, obs]

The pass tail (`$144d8-$145da`, from the 3D view) is the keyboard consumer; the keydown
table `$2ec8c` is read by scancode:

| scancode | key | effect |
|---|---|---|
| `$4d`/`$4b` | Right/Left | `$50fd4 += 1` / `-= 1` (the map scroll) |
| `$50`/`$48` | Down/Up | `$50fd6 += 1` / `-= 1`, clamped at 0 |
| `$34`/`$33` | `.`/`,` | `$5a860 += 1` / `-= 1` (the selection) + `jsr $10274` |
| `$36`-gated | RShift + ... | the camera fine controls: `$47`/`$52` -> `$1040a` +/- $10; `$4a`/`$4e` -> `$10406` +/- $a; `$63`/`$64` -> `$10408` +/- $a; `$65`/`$66` -> `$1040c` +/- 1 |

[obs] The arrow keys were verified live: holding Right/Left/Up/Down scrolls the map
(43-45k changed pixels per key hold). **Every other key is free** — the qol_keys port can
use A-Z and the map mode keys exactly as the 1990 patch did.

### 5.1 The screen regions and what a click does [disasm, obs]

The input section `$13e82-$13f6c` splits the pointer by position:

- **x < 64, y 7..135: the overview map** (the left strip).
  - A click scrolls the close-up view there: `$50fd4 = x`, `$50fd6 = y-7` (`$13ed8`).
    [obs] clicking (30,100) changed 38k pixels (a large scroll). The strip itself is a
    **64x64 word grid at `$4ce5a`**: `word[(y-7)*64 + x]` = an offset into the record table
    `$55df4` (0 = empty). `$146c2` does exactly that lookup, and the hover helper `$14608`
    reads the record (`$5574e + territory*$154` -> a `$55df4` record; fields `$8`/`$a`
    build the packed `d6`) and draws with `$e9d2`.
- **x < 64, y >= 135: four jump/mode cells** (`$13f5a`: `x >> 4` = 0..3 -> `$5a906` ->
  `jsr $10c92`). `$10c92` walks the `$4ce5a` grid and the `$55df4` records, filtering by
  record type (`$6(a4,d2)` against 2/4/...), i.e. **"jump to the next object of a kind"**
  controls. [obs] clicking (37,165)/(53,166)/(53,185) all caused large view changes (jumps).
- **x >= 64: the close-up map** (`$13f6c`): the rectangle table at `$13fc4` then the
  territory selection; a click changed 41k pixels (the view/selection reacted).

### 5.2 The action layer (the command cells) [disasm]

- **`$5a836`** = the *armed action/region id* (0 = none). `$5a834` (byte) = the current
  territory.
- The **action list `$1a89a`** = 24 word entries: action id -> **icon id**
  (`0, $ea, $c4, $d7, $da, $b4, $e8, $e9, $db, $d5, $d9, 0, $d6, $d8, $b3, $a3, $93, 0,
  0, $a4, $94, $84, $c3, $83`). `0` = no separate icon; `$c3`/`$c4` are the pointer icons.
- **`$1964a`** arms/draws an action: it looks the icon up in `$1a89a`, draws it with
  `$196b4` (the icon draw, icon positions from the table at `$19672`), and stores the
  action in `$5a836` (`$1968e`). The final call site `$19688` is self-modified at run time
  (the dump shows `$aaaaaaaa`; live it is `jsr $196b4`).
- The click path in the input section (`$13f06-$13f56`): the armed `$5a836` + the hovered
  region -> the message record at `[$5a8a2]` (action id + click x/y) -> the icon id ->
  `jsr $1964a`.
- The 1990 command set (Attack, Get Food, Get Men, ...) is 17 actions + 3 postures; the WW1
  list has 24 slots, several non-command (pointer/icons). The **action-id -> command-name
  mapping is not yet established.** The static route was tried and is exhausted: the
  `$4ce5a` grid cells point at byte offsets into `$55df4` whose `+6` byte reads as image-like
  noise for most cells (143 non-zero cells, ~60 distinct byte values) — i.e. the records are
  rebuilt/live data, not a static type table (`work/dumps/ovmap_grid.bin` is the scan). The
  two remaining ways: (a) **drive the live selection flow** (select a village/army, watch
  `$5a836` and the drawn icon appear — the reliable route), or (b) decode `$14608`/`$148e0`
  against a freshly poked record (place a known type in a cell and observe). The start
  territory's army/village screen positions were not found by brightness either (the
  bright-block clicks all scrolled the view), so (a) needs the game's own selection cues
  (the map icons) to be studied first.

### 5.3 The command cells: the 1990 manual layout, transposed [user, disasm, obs]

**The user's manual page (the 1990 Powermonger SYMBOL SUMMARY) and the user's statement:
"the WW1 edition has different icons in the same places doing the same job."** So the
command icons are at the 1990 screen positions. Proof: the WW1's rotate/zoom rectangle
table at `$13fc4` — `(24,155)-(32,161)`, `(34,161)-(40,169)`, `(45,159)-(61,174)`,
`(45,178)-(61,193)` — is **byte-identical** to the 1990 game's `$13250` table in
`../../done/powermonger/work/notes/tooltip.md` (section 1.1), and the WW1's command grid
uses the 1990 algorithm exactly (below).

**The command-icon hit test** (the 1990 structure, found at the map view `$1427c-$1433c`):
two line tables — near-vertical separators at `$13bde` (15 lines), near-horizontal at
`$13c58` (14 lines) — give the cell code `column + 16*row` exactly as the 1990
`pmtt_grid.py` does; the code is looked up in the 24-entry table `$1a89a`, whose **entry index
= the 1990 icon id**. Live oracle (the game stores the cell code at `$5a8ba`):

| click | cell code | icon id | 1990 command |
|---|---|---|---|
| (285,168), (275,162) | $da | 4 | **Get Men** |
| (250,165) | $d9 | 10 | Derank |
| (202,181) | $d7 | 3 | Get Food |
| (245,189) | $e8 | 6 | Attack |
| (300,150) | $db | 8 | Equip |
| (100,150) | $94 | 20 | Neutral posture |

`tools/pwwgrid.py` transcribes the two tables and the loops (`icon_id(x, y)`,
`icon_centres()`); its self-test passes all seven live points. The exact centre of every
icon cell in the WW1:

| id | centre | command | id | centre | command |
|---|---|---|---|---|---|
| 1 | (299,182) | Send Captain | 12 | (173,188) | Drop Items |
| 2 | (103,186) | Transfer Men | 13 | (227,174) | Supply Food |
| 3 | (201,181) | Get Food | 14 | (74,175) | Trade |
| 4 | (275,162) | Get Men | 15 | (73,161) | Alliance |
| 5 | (100,170) | Go Home | 16 | (72,149) | Spy |
| 6 | (243,190) | Attack | 19 | (97,156) | Aggressive (3 swords) |
| 7 | (274,187) | Invent | 20 | (94,145) | Neutral (2 swords) |
| 8 | (297,156) | Equip | 21 | (92,135) | Passive (1 sword) |
| 9 | (142,193) | Drop Food | 22 | (75,191) | Query |
| 10 | (252,168) | Derank | 23 | (71,138) | Option |

**The action gate** [obs]: after the cell lookup the action is gated by `tst.l $1c54(a0)`
with `a0 = $13d44` = the longword at **`$15998`**; zero = the action does not run (the click
is recognised — `$5a8ba` gets the cell code — but nothing happens). `$15998` is compared
against `$2c` in the window code (`$a912-$a944`, `$14c2c`) and cleared when a window closes
(`$ae26`), i.e. it is the game's own **mode/selection context**, not a window flag. The
command actions therefore require the game's own selection/precondition (in the 1990 game
the captain is auto-selected; the WW1's start state does not satisfy it, and selecting an
object on the map (the object rects at `$14662`, walked at `$1412e`, `jsr $8ac6`) did not
set `$15998` in the probes). **Consequence for the ports: a synthesized click is faithful —
it is exactly the mouse click, preconditions and all.** The 1990 command semantics are
given by the manual; the WW1's own activation flow is a play-driven question still open.

Also from the docs/manual: "You use the Overview Map, Map Icons, Conquest Meter, Close-Up
Map, and Map Controls just like you did in the original PowerMonger" — the left strip is the
Overview Map (5.1), the four rectangles are the Map Controls, and the command icons are the
perspective grid along the bottom and left, exactly as in 1990.

**The enemy village on the minimap** [user]: a slightly darker grey. In the palette the
greys are colour 1 `#484824` (background), 2 `#6c6c48`, 3 `#90906c`, 4 `#b4b490`, 5 `#d8d8b4`.
The village markers on the Overview Map read as colour-3 clusters (e.g. around ST (32,15)
and (41,15) in `mapview.sav`); clicking that cell scrolls the view to the village
(`work/snapshots/village.sav`). The user's hover cue (a red line to the village) was not yet
reproduced: hovering the minimap grid and the close-up centre on both `mapview.sav` and
`battle.sav` left the red colour (index 8, `#b44800`) counts unchanged. The trigger is still
open (likely needs the army with a target and the exact hover cell/close-up unit).

### 5.3a The keyboard-shortcuts prototype [obs]

`work/keyproto/keys.s` (org $72400) follows the 1990 `qol_keys` design: the IKBD key path
store $f30 (`move.b d0,$1d2b0`) is hooked to a table of {scancode, cell centre} pairs; the
pass hook at $13e6a (before the input section) writes the same words a real click writes —
the click position `$2edae/$2edb0`, the tracked pointer words `$2edb2/$2edb4`, the left
latch `$2edb6`, the down-seen `$2edbc` and the pass stamp `$2ed94 = $2ed90` — then releases
the down-seen on the next pass. [obs] Pressing M sets the game's cell code `$5a8ba` to `$da`
(the Get Men cell) — the synthesized click reaches the game's own dispatch exactly like a
mouse click at that cell. Keys: A D E F G H I L M N O Q R S T X Y the commands, 1/2/3 the
postures (the table's comments name them). Every other scancode is untouched.

### 5.4 Busy-scene snapshots (for the gates) [obs]

- `work/snapshots/march.sav`: Get Men then Send Captain + a target; the army marches
  (scene activity ~6.3k between frames), 3.35-3.78 ticks/s at 8 MHz.
- `work/snapshots/battle.sav`: Get Men, scroll to the village cell (32,15), Attack (245,189),
  target the village centre; a battle runs (activity ~12.7k), 3.56-3.67 ticks/s at 8 MHz,
  7.13 at 16 MHz.

## 6. Open items (for the keys/tooltip ports)

- [ ] The map-view keyboard consumption: which scancodes does the 3D view read (the 1990 game
      read only the four cursor keys and text windows). Search `$2ec8c`/`$1d2b0` readers in
      the map-view input section.
- [ ] The map-view command-icon cells: decode the two live panel descriptors' icon sets and
      their icon-id -> command mapping (the icon draw `$196b4` and the action dispatch).
- [ ] The tooltip surface: the HUD bar's free area and the game's own font/line writer (the
      1990 `pm_tooltip` wrote a 52-character line in the game's font into the black bar).
- [ ] The Falcon `movep` trap for the sound (`$1bc92` writes `$ff8800/02/04/06`): the 1990
      `fal_ym` pattern applies if the sound is touched.

### 5.5 The phantom click at the start of play — fixed in the port [obs, disasm]

The 1990 project's hardest keys bug (`../../done/powermonger work/notes/phantom_click.md`)
applies here too, and the prototype had it. The interrupt hook records a make code from the
moment the game's keyboard handler exists — which is **before the name prompt**. The letters of
the player's name therefore sat in the pending slot and were replayed as icon clicks, one per
pass, on the first passes of the map. A name containing `R` (Derank) disbanded the starting
formation; `H` (Go Home) issued an order.

The 1990 fix, adopted here:

* the **pass hook stamps `LASTV`** ($72806, a long) with the VBL counter `$71b7c` every pass;
* the **interrupt drops** any press whose VBL count is more than `WIN` = 150 (3 s at 50 Hz)
  past that stamp.

So a key only counts while the map loop is actually running. `LASTV` is zero at boot, making
the first difference huge, so every press before the first pass is dropped — including the
name.

The gate uses a name with no command letter in it (`BENCH`), so the test measures the keys and
not the phantom.
