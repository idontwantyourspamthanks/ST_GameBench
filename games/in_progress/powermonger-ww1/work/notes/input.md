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

The command strip: the input section at `$13e82` routes a pointer in **x < 64, y 7..135**
(the left HUD strip) to `$14608` (the territory/hover helper), then to
`$13f16`: the region id `$5a836` -> `$1a89a` (the 24-entry action list, the same list the
options screen used) -> `jsr $1964a` (the action dispatch). A hover path (`$13eb2` when
`$5a836` is set) exists for the strip — the WW1 has a partial hover mechanism of its own,
relevant to the tooltip port. The click on the MAP (outside the strip) goes to the rectangle
table at `$13fc4` (`$13f6c`), the territory selection.

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
