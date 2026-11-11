# Populous: algorithms, and where a better one gives the identical result

Second study pass (2026-11-11). Dumps: `work/dumps/g0.bin` (start), `work/dumps/busy.bin` (busy scene). Addresses are RAM addresses of the PP HAGA build at 1 MB. Disassembly is `tools/m68dis.py` on those dumps. Anything not backed by a listing or a raw number is marked [INFERENCE].

The game is compiled C (`link a6` / `jsr abs.l` / a 32-bit multiply helper for every struct index) around a few hand-written assembly routines (blits, pointer, sound, text, `$181d6`, `$18244`).

## 1. Data

| What | Where | Shape | Evidence |
|---|---|---|---|
| vertex heights `alt` | `$34c22` | 65 x 65 words, 0..8 | save routine `$1dbd6` writes `$2102` bytes; `$bf9e` indexes `x + 65*y`, `asl #1` |
| cell base height `map_alt` | `$33c22` | 64 x 64 bytes | written by `$c12c` |
| cell tile `map_blk` | `$36eb6` | 64 x 64 bytes: 0 water, 1..14 slope shapes, `$f` flat, +`$10` coast, `$1f`/`$20` fields of player 0/1, `$2f`..`$31` rock (cycled by paint command 12); `$35` and `$42` are tested by the walker code and not identified | `$c12c`, `$18244`, `$1363a`, `$1ed3c` |
| cell object `map_bk2` | `$3c560` | 64 x 64 bytes: `$21..$2c` buildings, `$32..$34` trees | `$18244` tests `$20 < v <= $2c` |
| cell occupant `map_who` | `$38012` | 64 x 64 bytes, peep index + 1 | `$114c4` |
| per-cell step count | `$39016` | 64 x 64 words | `$ef8a` `addq.w #1`; cleared by `$c12c` |
| peeps | `$3b2b6` | 208 usable x 22 bytes; count `$3c520` | `$114c4`, `$db8a` |
| per-player "god" | `$3b264` | 2 x 16 bytes: +0 leader peep+1, +2 magnet cell, +4 behaviour 0..3, +8 population (long, rebuilt every turn), +`$c` manna (long) | `$1f144`, `$db8a`, `$118aa` |
| per-player record | `$21e4a` | 2 x `$2e` bytes: +0 command, +1/+2 arguments, +8 "human" flag, +`$e` power bits | `$1e750` |
| game turn | `$3c506` | word, +1 per pass | `$db96` `addq.w #1,$3c506` |
| RNG seed | `$3d56c` | word | `$16740` |

Peep record (22 bytes), from `$114c4` and `$db8a`: +0 state bits (1 in a building, 2 walking, 8 fighting: read in the listings; `$20`, `$40`, `$80` are tested and their meaning is [INFERENCE] waiting / drowning / dying), +1 owner, +4 life (word; 0 = free slot), +6 animation counter, or the turn a building was founded (`$f2a6`), +8 cell (`x + 64*y`), +`$a` step offset, +`$c` sprite / building type, +`$e` long (non-zero for a knight [INFERENCE]), +`$12` previous cell, +`$14` AI scratch.

## 2. Landscape generation

`$b354` (called for a new world) does, in order: seed, `$bc12` (clear all maps), `$bec2`, `$c12c(0,0,63,63)`, `$12e44` (first objects and people).

**RNG** (`$16740`): a 15-bit linear congruential generator, one word of state.

```
016740  move.w  $3d56c,d0
016746  mulu.w  #$24a1,d0
01674a  addi.w  #$24df,d0
01674e  bclr    #$f,d0
016752  move.w  d0,$3d56c
```

The world is fully decided by the seed: `$b42a` copies it to `$37f00`, which the save routine `$1dbd6` stores.

**Hills** (`$bec2` calls `$befa` three times, with spreads (2,4), (4,2), (3,3)). `$befa(sx,sy)` picks a random vertex and then random-walks: `x += rand % (2*sx+1) - sx`, `y += rand % (2*sy+1) - sy`, clamped to 0..64, calling `$bf9e(x,y)` at each step until that call returns 6 (a vertex reached height 6).

```
00bf24  jsr $16740 ... divs.w d0,d1 / swap d1 ... add.w d0,d7      ; x step
00bf84  move.w d6,-(a7) / move.w d7,-(a7) / jsr $bf9e
00bf90  cmpi.w #$6,d0 / bne.b $bf24
```

**Raise one vertex** (`$bf9e`, the same routine the player's left click uses): add 1 to the vertex (limit 8), then for each of the 8 neighbours whose height is now more than 1 below, recurse. It also widens a dirty rectangle (`$36d26`/`$3b044` min/max x, `$3d560`/`$37ef6` min/max y) and counts raised vertices in `$37fc8` (the manna cost multiplier).

```
00bfe2  cmpi.w #$8,(a5) / bge $c122
00bff0  addq.w #1,(a5)
00bffa  move.w (a5),d0 / sub.w (a4),d0 / cmpi.w #1,d0 / ble.b +  / jsr $bf9e   ; x 8 neighbours
```

Lowering is the mirror routine `$d2a0`. So an edit propagates as a cone: slopes never exceed one step per vertex.

**Cell tiles from heights** (`$c12c(x0,y0,x1,y1)`): for every cell in the rectangle, `avg = (sum of the 4 corners) >> 2`; a 4-bit shape = which corners are above `avg`; shape 0 on raised ground becomes "flat" `$f` with base height `avg-1`; a sloped cell at sea level gets +`$10` (coast); rock `$2f` is kept; a water cell loses its object; the step count is cleared. It is called for the dirty rectangle after every edit, and for the whole map once at generation. The minimap is redrawn for the same rectangle by `$c2b8` (one `$167b0` pixel plot per cell into the clean background).

Better algorithm: none needed. Edits already update only the dirty rectangle. Cost is nil outside edits (2 calls in 30 frames in the busy profile).

## 3. Isometric terrain rendering

`$143a2(xoff,yoff)` draws the 8 x 8 cell window, every frame, back to front (rows y, columns x):

1. `$14314(x, y, height, tile)` for the cell's tile `map_blk` (water uses tile 0 or `$10` depending on the frame-parity word `$3b260`, which is the water animation);
2. `$14314` again for `map_bk2` (tree, building) 8 pixels higher, if any;
3. `$145bc` for the people standing on the cell (`map_who`), so they are sorted with the land;
4. `$14314` for the two cursor tiles (`$2e` at cell `$3d564`, `$2d` at `$3c508`);
5. after all cells, the two visible cliff faces, column by column (`$1457e`, 16 x 16 pieces stacked `map_alt` times).

`$14314` computes the screen position as X = 16*(x-y), Y = 8*(x+y) - height and blits a 32 x 24 tile, mask + 4 planes, read-modify-write:

```
014326  mulu.w #$a0,d0 / mulu.w #$a0,d1 / ... mulu.w #$a0,d2      ; three multiplies per tile
014348  mulu.w #$1e0,d3 / adda.l d3,a6                            ; tile * 480
01434e  move.w #$17,d5
014352  move.w (a6)+,d4                                           ; mask
014354  move.w (a0),d6 / and.w d4,d6 / or.w (a6)+,d6 / move.w d6,(a0)+   ; x 4 planes, x 2 words
014396  adda.l #$90,a0 / dbra d5,$14352
```

Before that, `$14a28` copies the whole 32,000-byte clean background (book, icons, minimap: buffer `$3b016`) over the back buffer with `move.l (a1)+,(a0)+ / dbra` (8,000 iterations).

Measured in the busy scene (`hotpaths.md`): 91 tile blits and one background copy per frame, 34.9% of all cycles.

### Better, with identical pixels

- **A. Keep the terrain between frames (dirty-rectangle redraw).** Proof that the inputs do not change: over 13 consecutive turns of the busy scene, 0 of the 64 view cells changed in `map_blk`, `map_alt` or `map_bk2`, and the view did not move (`baseline.md`, "per-frame invariants"). The only per-frame changes are the water parity (2 phases) and the 4-5 cells that hold people. Method: keep two composed pictures (background + terrain, one per water phase); each frame copy the right one (same cost as today's background copy) and then, for each cell with people in painter's order, draw the people and redraw, clipped to the sprite's word columns and rows, only the later tiles that overlap them. Rebuild a composed picture when the view scrolls, when `$c12c` runs on a rectangle that intersects the view, when a building or tree in view changes, or when the clean background is written (minimap dots, manna bar, icon highlights). Gain [INFERENCE]: most of the 24.8% (tiles) in a static view; nothing while scrolling. Exactness risk: medium. The rule "later tiles overlap earlier sprites" has to be reproduced exactly, and every writer of the clean background has to invalidate (the minimap plot `$167b0` runs 50 times per frame). It needs the byte-for-byte frame gate on scenes with people behind hills and buildings.
- **B. Faster full copy.** `move.l/dbra` costs 30 cycles per long: 7.7M cycles in 30 frames = 257,000 per frame. A `movem.l` block copy (Populous 2's own routine `$1e7c6` does this: 152,700 cycles per frame for the same 32,000 bytes, `../populous-2/work/notes/hotpaths.md`) saves about 100,000 cycles per frame, 4% of the busy frame, 10% of an idle one. Exact, low risk. An STE blitter copy is not faster than `movem` (8 cycles per word, 128,000 + chunk overhead) and has the HOG-chunk limit of `powermonger/work/notes/buserr.md` (this game polls the IKBD every VBL too, see `ui.md`); not worth it.
- **C. Tile setup arithmetic** (table candidates, section 7).

## 4. Sprites and the pointer

- People and flags: `$16954(screen,x,y,sprite)`, 16 pixels wide, 16 rows, `ror.l d0` on mask + 4 planes for every row, then `and`/`or` into the screen (`$169dc`). 6.2 calls per frame in the busy scene (1.8%). A 32-wide variant is `$16a26`.
- The mouse pointer is not drawn by the frame. The VBL queue routine `$16d70` restores the saved background (`$16dea`) and redraws the pointer (`$16e20`, the same shift-and-merge plus a save-under) **every VBL**, into the shown buffer:

```
016d74  bsr $16c96            ; button state machine
016d78  tst.w $16d26 / bne    ; pointer hidden?
016d80  bsr $16dea            ; restore
016d84  bsr $16e20            ; draw
016dd0  move.b #$d,$2(a6)     ; ask the IKBD for the mouse position again
016dd6  move.w #1,$16d28      ; VBL flag
016dde  addq.l #1,$16d2a      ; free-running VBL counter
```

Measured: 470 draws and 473 restores in 500 VBLs, 5.56M cycles = 7.4% of an 8 MHz CPU, whether or not the mouse moves. Better and identical: skip both when the position, the shape (`$2169a`), the shown buffer and the saved rectangle are unchanged since the last VBL. This is Powermonger's `p4_ptr`; the code is the same code (`bullfrog_family.md`).

## 5. People: movement, settling, fighting

`$db8a` runs once per pass. It zeroes each god's population, then loops over the peep table; the per-state work, from the listing:

- **In a building** (state 1): every turn it calls `$18244(owner, cell)` to measure the land around the building, adds manna from the table `$3b24a` and a growth value from `$249d6`, and when life exceeds the building's capacity it splits off a new walker into the first free slot (linear scan of the table from slot 0, `$e716`): the building keeps half the capacity, the walker gets the rest (`$e73a`-`$e75c`).
- **Walking** (state 2): `$101de` advances the step; on arriving at a cell centre `$ef8a` chooses the next move: `$f6f0` when the behaviour is "go to the papal magnet", for knights, and during Armageddon; otherwise `$f332`, the settle search. Life drops by `$37eee` per arrival.
- **Meeting** on a cell: same owner joins (`$ff08`, lives add up), enemy fights (`$10ebc`, then state 8 handled by `$10678`).
- **Computer player** (`$21e4a`+8 = 0): each walker also calls `$1363a`, which scans 81 offsets around it (table `$22816`) and queues one raise or lower command for the first vertex that is not level with the walker. `$13f18` and `$13a82` run once per turn for a computer player (0.1 calls per frame in the profile) and were not read; [INFERENCE] they decide the powers.

**Settle search** (`$f332`, read only in part): try the 9 directions (0 = stay) starting from a random one, test each step with `$181d6(cell, offset)` (off-map 1, rock 2, water 3) and score flat cells with `$18244`; "stay" with a non-zero score turns the walker into a building (`$f29a`: state 1, then `$103a4` sets the building type from the score). How far it looks along a direction is [INFERENCE] up to 5 cells (the initial "best distance" is 5 at `$f34c`).

**Land score** (`$18244(owner, cell)`), the routine that decides hut / house / castle: for 17 offsets (the cell, its 8 neighbours, 8 cells at distance 2; table `$22b8c` = 0, -64, 1, 64, -1, -63, 65, 63, -65, -128, 2, 128, -2, -126, 130, 126, -130) add 15 for every cell that is flat (`$f`) or already this owner's field; 0 if the cell itself is not; 0 if another building is inside the pattern; 305 (all 17) becomes `$bea`, a castle.

```
01827a  move.w (a2)+,d3
01827c  move.w d3,-(a7) / move.w d2,-(a7) / jsr $181d6 / adda.l #4,a7
01829e  add.w d2,d3
0182a0  cmp.b (a0,d3.w),d6 / beq ...          ; own field
0182a8  cmpi.b #$f,(a0,d3.w) / bne ...        ; flat
0182c2  addi.w #$f,d4
018318  addi.w #1,d5 / cmp.w #$11,d5 / bne $1827a
```

### Better, with identical world state

- **D. The land score is recomputed for every building on every turn.** Busy scene: 77.2 calls of `$18244` and 1,389 calls of `$181d6` per frame, 33.0% of all cycles. Proof that the inputs do not change: a Python model of the two routines, run on RAM captured at 14 consecutive turns, gave the same result as the turn before in 1,073 of 1,078 building-turns (`baseline.md`); `map_blk` changed in 0-5 of 4,096 cells per turn and `map_bk2` in none.
  - D1, exact and local: rewrite the pair. `$181d6` is 346 cycles per call because of `link`, `movem`, and a stack frame; the test itself is two range checks and a byte compare. An inlined version of `$18244` with the edge test done once per cell (the 17 offsets only leave the map when the cell is within 2 of an edge) costs about 1,000 cycles instead of 10,400 [INFERENCE: instruction count], with the same three outputs (`d0`, `$3b040`, `$37ef4`). Gain [INFERENCE]: about 30% of the busy frame, 9% of an idle one. Risk: low; gate by comparing the three outputs against the original routine over every cell and both owners on several dumps, then the turn-by-turn state gate.
  - D2, a cache per building invalidated when a cell within 2 changes: not recommended. About 60 code sites write `map_blk` (xref list in this session's log); D1 already removes most of the cost.
- **E. The 32-bit multiply helper** `$20796` is called 191 times per frame (391 cycles each, 3.0%) to compute `index * 22` and `index * 46`. A drop-in replacement with a 16 x 16 fast path (`mulu`) is exact; gain about 2% [INFERENCE]. The free-slot search for a new walker (linear from slot 0) and the per-peep sound and minimap calls (`$166f0`, `$167b0`: 50 each per frame) are the remaining per-peep overheads; they are small (1.4% together).

## 6. Effects

Commands are bytes in the player's record, executed by `$1e750` (jump table `$21652`), so a keyboard patch can issue them without touching the mouse path (`ui.md`).

| Command | Routine | Manna (`$219c6`..) | Power bit |
|---|---|---:|---|
| 1 raise, 2 lower | `$118aa`, `$11738` -> `$bf9e`, `$d2a0`, then `$c12c` on the dirty rectangle | 10 per vertex | |
| 5 place papal magnet | `$111fc` | 200 | |
| 3 earthquake at the view | `$1238e` | 2,500 | `$08` |
| 4 swamp | `$12a52` | 5,000 | `$10` |
| 14/5 knight | `$12bde` | 7,500 | `$20` |
| 6 volcano at the view | `$1267a` | 10,000 | `$40` |
| 14/4 flood | `$11fa8` | 40,000 | `$80` |
| 14/3 Armageddon | `$12d64` (sets `$3d562`) | 80,000 | `$100` |

[INFERENCE from the call lists, the routines were not read to the end] Earthquake and volcano are bursts of raise / lower calls around the view followed by `$c12c`; flood lowers every vertex once and recomputes the whole map. None is a per-frame cost. Measured frame rates during and after them are in `baseline.md`.

## 7. Arithmetic done by hand in the hot paths

| Where | What | Calls per busy frame | Operand range | Exact replacement |
|---|---|---:|---|---|
| `$14326`-`$14348` | 3 x `mulu #$a0`, 1 x `mulu #$1e0` per tile | 91 x 4 | x, y 0..7 (x 8), height 0..64, tile 0..`$42` | two small tables (160*n for n < 128: 256 bytes; tile*480: 134 longs) or, with change A, nothing. Gain under 1%. |
| `$20796` | 32 x 32 multiply by loop-free 3 x `mulu` with `link`/`movem` | 191 | index < 208 by 22 or 46 | fast path (E) |
| `$181d6` | bounds test with sign fix-ups | 1,389 | cell 0..4095, offset from the 17-entry table | inlined (D1) |
| `$20724` | 32-bit divide by shift-subtract loop | 4.5 | manna ratios | leave |
| `$b6b0`, `$b7bc` | `divs #3`, `divs #2` in the main loop | 1 each | small | leave |
| `$169dc`, `$16ebe` | `ror.l dN` x 5 per sprite row | 6 sprites + 16 pointer draws per frame | shift 0..15 | pre-shifted pointer (16 shapes x 16 rows x 2 words x 5 = 3.2 KB) after `p4_ptr`; sprites are too few to matter |

## 8. Work repeated with unchanged inputs (summary)

| Work | Per busy frame | Share | Inputs unchanged? (evidence) | Fix |
|---|---:|---:|---|---|
| land score of every building | 77 calls + 1,389 sub-calls | 33.0% | same result in 99.5% of 1,078 building-turns | D1 |
| 64 terrain tiles + objects | 91 blits | 24.8% | 0 view cells changed in 13 turns; water phase alternates | A |
| clean-background copy | 32,000 bytes | 10.2% | needed by the redraw-everything design | B, or folded into A |
| pointer restore + draw | 15.7 each (one per VBL) | 7.4% | pointer did not move (no input in the run) | `p4_ptr` |
| minimap dot + sound call per peep | 50 + 50 | 1.4% | not examined | none planned |
