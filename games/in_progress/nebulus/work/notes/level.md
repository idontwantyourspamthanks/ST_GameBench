# Nebulus: level / tower data format (NebLevel2)

Tags: **[obs]** observed (Hatari 2.6.1, STE TOS 1.62, 1 MB, frozen `boot_to_game()`); **[disasm]** read from `tools/m68dis.py` on `work/dumps/tower_1mb.bin`; **[INFERENCE]** not proven.
Scratch/tools: `work/level/tools/` (`pplz.py` codec, `nebedit.py` prototype, `lvl.py`/`nl2.py`/`run*.py` experiment scripts); runtime dumps `work/level/dumps/m1_t{1,2,5}.bin` (512 KB each, towers 0/1/4 of mission 1), shots `work/level/shots/`.
Addresses: `$RAM` = 1 MB reference run; `U$xxxx` = offset in the **unpacked** NEBEXE.FIC image (`U = RAM - $33B1C + 28`).

## 1. NEBEXE.FIC is PP-LZ packed (not plain)
- Header: `4333 0002 8ad8 0004 25e9 ...` = `'C3'`, packed length `$28AD8` = 166616, unpacked length `$425E9` = 271849, 32-byte header, name `NEBEXE`. File = 166648 B = 32 + 166616 exactly [obs: `pplz.unpack` consumed 166616, produced 271849, asserts passed].
- Token stream (same as `tools/pp_depack.py` / Hunter's HUM.FIC): `00` end; `01..7F` literal run; `80|c` copy c+3 bytes, 1-byte offset; `C0|c` copy c+4 bytes, 2-byte BE offset (overlapping copies allowed). 61 % ratio, so the lz stream is the only thing in the file; no bytes of any table are at a fixed file offset except where they happen to sit in literal runs (below).
- The unpacked image (`work/boot/NEBEXE.FIC.out` is the same, md5-equal decode) is a GEMDOS program: `601A`, text `$A866`, data `$373A6`, bss 0, 1566 relocations (table at the end, 2497 B). Loaded and relocated at **RAM `$33B1C`** (28-byte header sits at `$33B00`). [obs: after relocating with base `$33B1C`, text+data match the tower RAM dump byte-for-byte except 383 bytes in 33 runs of runtime state, e.g. `$3ad97..` timer].
- So the variables `$3390c`, `$33944`, `$33a40`... are **below** the image (loader-side bss, not in the file); the tower tables below are all inside the image.
- **Repacker**: `work/level/tools/pplz.py` `pack_file()`: DP encoder, round-trips, 2 s, gives 164433 B for the unmodified image (< 166648 original) [obs]. A cold boot of a repacked + edited file works (section 5). A smaller packed file is safe; a larger one is untested.
- **In-place patching without repack** works for bytes that fall in literal runs (same file size): `lit[]` map from `pplz.unpack`. Whole time table (`U$729E`) = literals at file offset 15502; the tower grid data is only ~15-18 % literal, so grid edits need the repacker.

## 2. Tower selection: what `$3390c` and `$33910` are
- `$3390c` = tower index 0..7 (`$3dd12: move.w d0,$3390c` from the cheat F1..F8 keys; `$3e37a` from `$3e274/6` current-tower word of player 1/2). `$33910` = mission 1/2 (`$3d794`/`$3d7a8` set 1/2 from title keys F7/F8; strings `$3cfd6 "Mission #1"`, `$3cfe1 "Mission #2"`). Two complete sets of 8 towers (16 towers total).
- **Cheat tower switching works in-tower, not on the title**: type `HELLOIAMJMP` at the title (`$33a40 = 1` confirmed), start with `Right`, `Right Ctrl`, then F1..F8 *in the tower* (`$3dd00: tst $33a40; cmp #8,d0; move d0,$3390c; bsr $3e31a; bra $3dbe0`) [obs: run7: F1 start `tower 0x0 ncols 0x2f`, F2 -> `tower 0x1 ncols 0x47`, F5 -> `tower 0x4 ncols 0x60`; timers `20 20 28` (445) and `28 48 29` (595) = 450/600 minus ~5 s]. F2 on the title only changes options (title key table `$3d6e8..` : F1/F2 = 1/2 players, F3/F4 sound, F5/F6 50/60 Hz, F7/F8 mission).

## 3. Per-tower tables (all indexed by tower 0..7)
| What | RAM | Unpacked `U$` | Size / addressing | Evidence |
|---|---|---|---|---|
| Initial time | `$3AD9E` | `$729E` (file 15502, literal) | 8 words BCD: `0400 0450 0500 0550 0600 0650 0700 0750`; `$3adae: move $3390c,d0; add d0,d0; move.w $3ad9e(pc,d0.w),d0` | [disasm] + [obs] timer `20 20 28` after F2 |
| Palette | `$35250` | `$1750` | 8 x 16 words (STE 0RGB, 32 B); `$35228: (t&7)*$20 -> $351ac` | [disasm] |
| Title strings | `$3D14E` / `$3D16E` | `$964E` / `$966E` | 8 longs each (mission 1/2), value = unrelocated offset (+`$33B1C`) -> C strings `$3CDCE..` ("The Tower Of Eyes", ..., "The Last Trump", ">> GAME O.."); `$3d0f0: (a0)=names[$3390c*4]` | [disasm], strings read |
| Tower graphics/mask | `$3E382` | `$A882` | 8 x 512 B (`$366d8: (t&7)*$200 -> $36406`, 128 longs) | [disasm]; contents not decoded |
| Tile/pattern graphics | `$54ABA` | `$20FBA` | `(t&3)*$A00` per tower (4 variants shared by 8 towers; `$36390`); more at `$4B6BA` (`$36b50`) | [disasm]; not decoded |
| **Layout (the map)** | `$42BFA` (mission 1) / `$44154` (mission 2) | `$F0FA` / `$10654` | section 4 | [disasm] + RAM-verified |

## 4. The tower map (layout) format: `$377a2` decoder
A tower is a **16 x H grid of cell bytes**: 16 angular cells around (8 px each, 128 px circumference; enemy x = `(angle*8+4)&$7f`) by H heights (48..97). In RAM it is `$327F0 + angle*$100 + height` (16 rows of 256, zeroed first); `H-1` is stored in `$33912`. Decoder [disasm `$377a2..$3783a`, the 16-byte-wide bitmap decode]:
```
set base a3 = $42BFA (mission 1) or $44154 (mission 2)        # cmpi.w #1,$33910
mask   = a3 + tower*$200                 # 512 B per tower: for each height column c: 2 bytes = 16 mask bits
hdr    = a3 + $1000                      # 24 B: lo[8] @+0, hi[8] @+8, nrows-1 [8] @+$10  (indexed by tower)
stream = a3 + (hi[t]<<8 | lo[t])         # cell bytes, one per SET mask bit, in (height, angle-bit) order
for c in 0..nrows-1: for half in 0..1: m=mask byte; for bit 0..7: if m>>bit&1: grid[half*8+bit][c] = *stream++
```
- Bit n of the first mask byte of column c = angle n, second byte = angle 8+n. Columns run bottom (0) to top.
- Mission 1: set at `$42BFA`: masks `$42BFA..$43BF9` (8 x 512 B), header `$43BFA..$43C11`, streams contiguous `$43C12..$44152` (tower starts `$43C12 $43C9E $43D2A $43D97 $43E51 $43F32 $43FCD $4406B`, rows 48 72 50 67 97 65 81 97; stream sizes 140 140 109 186 225 155 158 232 B), 1 spare byte `$44153`. Set 2 at `$44154`: header `$45154` (`$44154+$1000`), streams `$4516C..$456C0` (starts `$4516C $4520B $452B3 $4533D $453FE $45482 $4553C $455D9`; rows 55 57 55 65 57 95 81 97). Data follows immediately; **no free space inside or behind either set**, so structural edits must fit the same total bytes (towers can be re-laid within the region).
- Verified: my decoder output equals the `$327F0..$337EF` buffer in RAM for towers 0 (mission 1) in `tower_1mb.bin`, and in fresh dumps for towers 0, 1 and 4 started via cheat (0 differing bytes in 4096 for each; `work/level/dumps/m1_t1/t2/t5.bin`) [obs].
- Unpacked offsets: set 1 masks `U$F0FA`, header `U$100FA`, streams `U$10112`; set 2 masks `U$10654`, header `U$11654`, streams `U$1166C`.

### Cell byte meaning
- **bit 7 set = terrain** (drawn/collidable), **bit 7 clear with bits 6-4 non-zero = enemy spawn marker**, otherwise (`$08`, `$0C`, `$00`) = inert marker.
- Terrain class table is built at run time (`$38028`, 256 bytes at `$315E0`): `v&3 = 0 -> 10, 1 -> 0 (or 20 if v&$C), 2 -> 30, 3 -> 40`, non-terrain `-10`. So `$80` class A, `$81` ledge/platform (`$85` = ledge variant with bit 2), `$82` class C, `$83`/`$87`/`$C3` class "40" (drawn by `$37c06`, `cmpi.b #$28,(a5,d0.w)`): door/tunnel columns. High bits `$10/$20/$40` of terrain bytes do not change the class [disasm]; tower 1 map ([obs] `work/level/tools/nebedit.py dump ... 1 1`) shows: `$81` rows = ledges, `$83` triples = door openings (dark rectangles in the screenshot), `$80` vertical runs and `$91/$B1/$82/$85/$08` auxiliary ledge/step/lift variants, **`$C3` x3 at the top of every tower** (3 per tower in both sets) = the exit door **[INFERENCE for the role; count is exact]**. Which exact cells are tunnel pairs or lifts is not decoded.
- **Enemy markers** (`$37978..$37ABC`, [disasm]): when the scan pointer `$3393C` (scrolls with height, `$3391a`) reaches a cell with bit7 = 0 and `(v&$70) != 0` and a free slot (`$48(slot)==0`, 4 slots at `$33944+2*s`) exists, it spawns: `x($0) = (angle*8+4)&$7f`, `y($C) = height*4`, `$48 = 6`, `$3C = 0`, and by `v&$70`: `$10` -> kind `$6C=2`, `$54=1`; `$20` -> kind 1, `$54=1`; `$30` -> kind 1, `$54=0`; `$40/$50` -> kind 8, `$54 = 1 + ((v>>4)&1)`; `$60/$70` -> kind 9, `$54 = 1 + ((v>>4)&1)`. Low nibble is not read by the spawner. After spawn the AI mutates `$6C/$54/x/y` (slot dumps 3 s later: kinds 8,2,1,8, x not equal to angle*8+4) [obs run10], so kind names need the enemy AI; unnamed.
- Struct-of-arrays `$33944`: field F of slot s = `$33944 + F + 2*s` (F = 0 x, `$C` y, `$3C`, `$48` state, `$54` variant, `$60`, `$6C` kind); 4 slots live (so max 4 enemies on screen).
- Enemy placement therefore is **not a per-floor record list**; it is the marker bytes inside the same grid. There are no separate floors: the tower is one continuous 16-column cylinder; "floor" = ledge rows (`$81` runs); climbing uses ledges and the door cells.

### Level-complete / timer
- Timer: `$3AD98/9A/9C` hundreds/tens/ones, digit*8 (+sub-frame low bits), loaded by `$3adae` (`initial = table[$3390c] + word at $33934/$33936`, then digits split at `$3add2`) and drawn each tick (`$3b0a4` gated by `$33938`) [obs `18 48 45` = 399.5 etc.]. Time-up message "Time Limit Up !!" follows "No Sound" in the string block at `$3cfd6`.
- Exit: the door animation counter `$33A1E` runs 1..7 (`$3bcc8`), at 7 `$3bd18: move.w #4,$33A46` = tower-complete state; the main loop (`$3ddf0`) then clears the tower's bit in `$33A34` (`$3e352`), advances the player's tower word `$3e274/6` (`$3e378: addq #1,(a0); move (a0),$3390c`) and at tower 8 (`cmpi #8,$3390c`) goes to the game-complete path (`$3e33c`, `$3d1e4`) [disasm]. Which map cell starts the animation is [INFERENCE]: `$C3`.

## 5. Proven edits (cold boots of patched NEBEXE.FIC copies, frozen `boot_to_game()` -> `in tower True 23.1 s`)
### 5a. Layout edit (tower 1 of mission 1, 4 cells at the start ledge)
- Runtime proof first: poked `$43C17..$43C1A` (`81 81 81 81`, the stream bytes for angles 5-8 of height 1) to `53 53 53 53` via the Hatari debugger and pressed F1 (cheat restart, re-runs `$377a2`): an enemy (blue eye) appears at the tower [obs `shots/e_a.png`]; with `$50` x4 a stone boulder appears [obs `shots/e_b.png`]. Readback: `before 818181818181`, `after poke 535353538181`.
- File edit: `python3 work/level/tools/nebedit.py set originals/NEBULGX/NEBEXE.FIC work/level/patched/NEBEXE.FIC 1 0 5 1 53 6 1 53 7 1 53 8 1 53` (args: mission, tower, angle, height, hex) prints `cell -> RAM $43c17 unpacked $10117` ... `$1011a`. Diff of the two unpacked images: exactly `U$10117..U$1011A: 81 81 81 81 -> 53 53 53 53` [obs]. Repacked file 164442 B (original 166648 B), md5 `19a00056f89ead635697f3e5527c2c55` vs original `0dd818c552aedc5a2501a7a9a718906e`.
- Cold boot with `Nebulus(game=work/level/patched)`: `in tower True 23.1`, RAM `$43C15..$43C1C = 9191535353538181`, `$327F0+angle*$100+1` for angles 5..8 = `53 53 53 53`, angle 9 = `81`; screenshot `work/level/shots/patched_boot.png` shows a spiked enemy beside Pogo at the start where `shots/m1_t1.png` (unpatched) shows none [obs].
### 5b. Initial time (in-place, no repack: bytes are literals)
- Original file bytes at **file offset 15502 (`$3C8E`)**: `0400 0450 0500 0550 0600 0650 0700 0750` (= `U$729E`, RAM `$3AD9E`). Patched `04 00 -> 09 99` at 15502..15503 in a copy (same file size 166648). Cold boot: table readback `09990450`, timer words `48 48 22` (994), HUD `t-99x` [obs `shots/patched_time.png`].

## 6. Where the data lives in the file (summary for an editor)
Unpack -> modify `U$` bytes -> `pplz.pack_file()`. `U` offsets: layout set 1 `U$F0FA..U$10653`, set 2 `U$10654..U$11BC0` (end `U$11BC1`), time table `U$729E`, palettes `U$1750`, name pointers `U$964E/U$966E`, mission strings `U$94D6`. No relocation entry falls in the layout sets (checked by `nebedit.validate`, 1566 relocs all elsewhere). Literal-only (in-place file patch) bytes: time table at file offset 15502; names/palettes partly; layout ~15-18 %.

## 7. `nebedit.py` design (prototype exists: `work/level/tools/nebedit.py`, uses `pplz.py`)
Feasible now (implemented, verified): `verify` (pack/unpack round trip + structural checks: contiguous streams, 3 exit cells per tower, stream end = region end, no relocs inside), `dump` (times, tower names both missions, ASCII map of any tower), `set` (value-only cell edits where the mask bit exists; any terrain/enemy byte), `time` (initial time per tower), `save` (repack + header fix). To add with no further reverse engineering: palette edit (`U$1750`), name strings (same-length or relocated pointer table + unused space), full tower re-encode (`encode_tower`: build masks/stream from a 16 x H grid, write sequentially into the set region, rewrite header lo/hi/rows bytes, fail if total > region), swapping/duplicating towers by copying a tower's stream + mask, a mission-2 clone of mission 1.
Needs more reverse engineering before a *useful GUI*: (1) cell-code semantics (which `$80/$82/$85/$91/$B1/$08/$0C` cells are lifts, tunnels, pairs; how doors find their partner; the exit trigger cell), (2) enemy kinds `$6C` 1/2/8/9 and `$54` variants -> names/behaviour (the AI changes them), (3) the graphics tables (`$3E382`, `$54ABA`, `$4B6BA`) for tile art, (4) Pogo's start position/height (`$338fe`/`$33a18` constants at `$3dc66`), (5) whether sizes above the original packed length boot (smaller works).

## 8. Gotchas
- `$327F0` rows are 256 bytes apart, only H used; `$33912 = H-1`.
- A poke through Hatari's `w` command takes decimal unless `$` prefixed (`w $43c17 $53`); this cost one run.
- Right after the game starts there is a submarine/Pogo-emerging intro; enemies observed in the first ~3 s are not on screen yet (k_A/k_B shots show the sub, timer `t-400`).
- Cheat F1..F8 in-tower is a restart of that tower: it re-decodes the map from the file image in RAM, which makes live layout experiments quick (poke bytes in `$43C12..` then F1).
