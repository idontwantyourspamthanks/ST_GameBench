# MW2 terrain: how the landscape is generated, stored, lit and drawn

Source of facts: disassembly of `work/dumps/ram_ingame_lobos.bin` (`tools/m68dis.py`), Hatari 2.6.1 runs on the unpatched `1mb_ingame_walking` snapshot (1 MB STE, 16 MHz clock so a run takes seconds), and the existing notes (`timing.md`, `p7_cell_cull.md`, `render_audit.md`, `spanfill.md`, `f38cd0.md`, `projection.md`, `cockpit.md`).
Every number is either measured (source named) or marked `[INFERENCE]`. Scripts that reproduce everything are in `work/terrain/` (section 10); figures are in `work/shots/` (git-ignored PNGs).

## 0. Summary (for the article)

1. **The whole world is stored as 8,798 bytes**: one 83 x 53 array of signed 16-bit heights (FFB file 96, `$49c80` in RAM), one sample per 128 world units. Nothing else describes the land.
2. **The 100 x 100 cell landscape around the player is generated, not stored.** A midpoint-displacement (diamond-square style) subdivision runs 6 times on the player's neighbourhood: sample spacing 128 -> 64 -> 32 -> 16 -> 8 -> 4 -> 2 world units. Amplitude of the added noise halves each level (`$80` ... `$04`) and is scaled by the local slope. The noise is a small 3-multiply hash PRNG (`$27462`) whose seed is keyed to the world position, so the result is **fully deterministic and position-consistent**.
3. **Proof**: a 100-line Python replica (`work/terrain/replica.py`) reproduces every interior cell of every level and the final window **bit for bit** (16,362 / 16,362 interior words at each of 6 levels; 10,000 / 10,000 window words; 79,182 PRNG calls = the count measured in Hatari). Moving the window by 40 cells and regenerating gives **4,224 / 4,224 identical cells in the overlap**.
4. After generation the rebuild post-processes the grid: heights x2, roads and flat pads stamped, persistent craters re-applied, **trees placed by a pure function of the heights** (1 position in 32 on a half-resolution lattice; 55 / 55 tree records in RAM reproduced by the rule), then **per-triangle Lambert lighting is baked into 2 bytes per cell**.
5. The rebuild costs **91.2 M cycles** (5.7 s at 16 MHz, 11.4 s at 8 MHz): 48% fractal subdivision (79,182 PRNG calls), 47% baked lighting (20,000 integer square roots), 5% everything else. This is the "6-second stall".
6. Per frame, the renderer sees a 27 x 27 cell block around the camera cell, keeps cells inside a **6.5-cell radius**, and draws 2 triangles per cell back to front with a painter's order and no sort. Colour = `(fog band << 8) | shade byte`: the baked slope shade picks a green/sand/blue/grey ramp, and the **last 1.5 cells fade to the sky colour in three dither steps (25/50/75%)**, which hides the draw-distance cut.
7. There is **no terrain LOD** (every cell is the same 2-unit grid at every distance), **no height-band colouring** (no snow line), and the horizon is simply where the terrain stops: the sky is a flat colour-15 fill.

## 1. World representation

### 1.1 What is stored

| Item | Where | Size | Evidence |
|---|---|---|---|
| World seed map | FFB file 96 -> `$49c80` | 83 x 53 words = 8,798 B | `sub_028d7e`: `move.w #$60,$116(a6)` (file 96) `move.l #$49c80,$6918.w`, then `jsr $2783e`. Dir entry (RAM `$e57e+96*8`): `01b0 0cfe 6e 00225e`: checksum `$01b0`, length `$225e` = 8,798. Extracted from `FILES/FFB` with the loader's own track-side rule: XOR checksum = `$01b0` (match). |
| Area-id table | `$11058` | 80 x 50 bytes | `sub_02bf16`: `lsr.w #7,d0 / lsr.w #7,d1 / mulu.w #$50,d1 / add.w d0,d1 / lea $11058.l,a0 / move.b (a0,d1.w),d0` |
| Per-area data file (objects, roads, ...) | loaded into `$b3fa` when the area id changes | - | `sub_02db44` -> `$289ac` -> `$2783e` (file `$eb9c - 1`) |
| Local landscape | `$40040-$49c7f` | 100 x 100 x 4 B = 40,000 B | section 3 |

In RAM the world map differs from the disk file in only **6 words** (`$49c80..$49c8a`, the first six even words of row 0: `1140 1140 1045 981 924 924` instead of `-2000 -2488 -3248 ...`); everything else is byte-identical. The first row is outside every playable area. (Measured: `entry.bin[$49c80:+8798]` vs the extracted file.)

### 1.2 The seed map: format and scale

* 83 columns x 53 rows of big-endian signed words. Range **-4536 .. +4944**, every value a multiple of 8 (768 distinct values). 925 samples are exactly **-2000**: a sentinel for "open deep sea", flat.
* One sample = **128 world units**. Evidence: the first call of the subdivision driver crops with shift 6 (64 units) on the *output* of the first subdivision (`$24d12: move.w #$6,$66c4.w`), and the world coordinates `$66bc/$66be` (units) run 0..`$27d8` (10,200) x 0..`$1900` (6,400), i.e. 79.7 x 50 samples (`$31e42: cmpi.w #$27d8,$66bc.w`, `$31e4a: cmpi.w #$1900,$66be.w`; 80 x 50 blocks of 128 are also what `$2bf10` indexes). The extra 3 columns/rows are margin for the neighbour reads of the subdivision.
* The world is therefore **10,240 x 6,400 units. At the final 2 units per cell that is 5,120 x 3,200 = 16.4 million cells, generated 10,000 at a time** (0.06%): an expansion of about 3,700 : 1 over the 8.8 KB map (2 bytes per final cell would be 32 MB).
* Picture: `work/shots/world_base_83x53_marked.png` (the red box is the player's 100-cell window, 1.5 samples wide).
* The area-id table: 80 x 50 bytes; values **1..42** (42 named areas) and **128/129/130** (three sea zones); 0 = off the map. Name text for the area is printed by `$2dbc6` when the player crosses into a new block ("2 January / Deepwater Cove / Lobos", seen in a screenshot after poking the position).
* Off-map blocks are walls: `$2db44` returns `d0 = 0` for id 0 -> `move.w #$ffff,$629c.w` (`$2dbbe`); `sub_031dee` then restores the saved position (`$31eb0: tst.w $629c.w / bne $31e52`, which copies `$66f6..$66fa` and `$66c0..$66c2` back). `[INFERENCE: not exercised live]`.

### 1.3 Units

| Quantity | Unit | Evidence |
|---|---|---|
| World position `$66bc/$66be` | 1 unit = half a final cell | `sub_031dee`: `divs.w #$200` of X-`$6400`, `add.w d1,d1` (x2) into `$66bc`; one recentre of 40 cells changes `$66bc` by 80 (`1152 -> 1072` in `timing.md`) |
| Player position `$66e6/$66ea` (window) | 1/512 cell; window centre `$6400` = 50.0 cells | `$31e0a-$31e16` |
| Final grid height (after the x2 pass) | 1/512 of a cell = the same unit as position. 512 = one cell edge | T1/T2 view tables step 512 per cell (`$188f8`, `$18a40` live: dist column steps of 512); view-space Y = h x `$1856a`>>14 (`$1da9a-$1dab0`), `$1856a`=16069..16384 |
| Seed map / generator height | half of the final unit | `$1c996` doubles every height; replica: `pre == 2*raw` for 9,843 / 10,000 cells, the other 157 are road / pad cells |

Real-world scale (miles, feet) is not in the binary. In the DOS game one final cell is 2 strategic units = 1,320 ft (docs/time_distance_units_original.md); if MW2 uses the same unit the draw radius of 6.5 cells is about 1.6 miles `[INFERENCE]`.

## 2. The local-map rebuild (`sub_031dee`)

### 2.1 Trigger

Called inside the world logic each tick; it returns at once while `$6288 != 0` (`$31dee: tst.w $6288.w / bne.w $31f16`). `sub_03451a` clears `$6288` when the player's window X or Y is <= `$1388` (9.8 cells) or >= `$b478` (90.2 cells) (`timing.md`). The rebuild:

```
031e0e  move.l $66e6.w,d1 ; subi.l #$6400,d1 ; divs.w #$200,d1   ; whole cells moved (quotient), remainder kept
031e2a  add.w d1,d1 ; add.w d1,$66bc.w                           ; world position in units = 2 per cell
031e72  d3 = $6400 + remainder  ->  $66e6                       ; player is put back at the window centre
031eaa  jsr $2db44                  ; area check / load a new area file if the area id changed
031ede  jsr $24d0e                  ; THE GENERATOR (section 2.3)
031ee4  jsr $274e4
031eea  jsr $50f8  ($1bfba)         ; bind objects, roads, trees (2.5)
031eee  jsr $508c  ($1c996)         ; heights x 2
031ef2  jsr $50fe  ($1c146)         ; flatten pads under objects
031ef6  jsr $5104  ($1c180)         ; re-apply craters
031efa  jsr $5092  ($1c832)         ; BAKED LIGHTING (2.6)
031efe  jsr $5050  ($1db94)         ; rebuild per-frame tables (wave table, distance table, fill-table setup)
```

Out-of-world positions (`$66bc < 0`, `$66bc > $27d8`, `$66be < 0`, `$66be >= $1900`) are undone (`$31e52-$31e70`) and the recentre is retried.

### 2.2 Cycle budget of one rebuild (measured)

Hatari, unpatched game, X poked to `$1350` so the rebuild fires at once; breakpoints `$31df6` .. `$31f12`; `profile` with exec counts; `$CycleCounter` deltas at phase breakpoints.

| Phase | Cycles | Share |
|---|---:|---:|
| `$31c60`, `$38252`, `$2db44` (unit rebasing, area check) | 5 k | 0.0% |
| `$2dbc6` area-name text | 0.84 M | 0.9% |
| **Subdivision, 6 levels** (level 0 incl. setup 7.23 M; levels 1-5: 7.38 / 7.37 / 7.34 / 7.35 / 7.31 M) | **44.0 M** | **48.3%** |
| window copy `$24d4e` + store to grid `$24d84` | 0.61 M | 0.7% |
| `$274e4` (unidentified, scans the new grid) | 0.58 M | 0.6% |
| `$1bfba`: object bind, roads, trees (`$1be92` trees = 0.57 M) | 1.06 M | 1.2% |
| `$1c996` height doubling (10,000 x 53 cycles) | 0.53 M | 0.6% |
| pads `$1c146`, craters `$1c180` | 0.03 M | 0.0% |
| **Baked lighting `$1c832`** | **43.3 M** | **47.5%** |
| tail: `$5050` (`$1db94`) tables, `$3827a`, `$3198a`, `$50bc` | 0.26 M | 0.3% |
| **Total (profile)** | **91.22 M** | 100% |

91.22 M cycles = 11.4 s at 8 MHz, 5.7 s at 16 MHz, equal to the `timing.md` stall (285 VBL at 16 MHz, 576 VBL at 8 MHz). Raw: the profile total printed `91222448`; `CycleCounter` entry `3460347496`, exit `3551569416`, difference `91221920`.

### 2.3 The generator: a midpoint-displacement pyramid

Driver `$24d0e`:

```
024d0e  bsr $25a00           ; reset parameters (amplitudes $80/$40/$20, seeds 0, counters)
024d12  move.w #$6,$66c4.w   ; sample-spacing shift for the first crop (64 units)
024d24  jsr $2616a           ; LEVEL 0: subdivide the whole world map 83x53 -> 166x106 (spacing 64)
024d2a  jsr $24d9e  x5       ; levels 1..5: crop 83x53 around the player, subdivide again
024d48  bsr $24d4e           ; cut out the 100x100 window, flip rows (Y), store as grid words
```

Level `k` (levels 1..5, `$24d9e` + `$25fec` + `$26128` + `$26186`):

1. Window origin in the previous level's samples: `ox = ((X - accX) >> shift) - 40`, `oy = ((Y - accY) >> shift) - 25`, clamped to 0..80 / 0..50 (`$24d9e-$24dbe`, `$24de2`); `acc += origin << shift`; `shift` falls 6,5,4,3,2.
2. Copy an **83 x 53 window** (origin + 1) from the previous 166 x 106 result into `$7a580` (`$26128`: 53 rows x 83 words, row stride `$14c` = 332 B).
3. Subdivide it (`$26186` -> `$25a8a`, 53 times, once per source row) into a new **166 x 106** array at `$40040` (stride 332 B). Sample spacing halves: 64 -> 32 -> 16 -> 8 -> 4 -> 2 units.
4. The noise amplitude (word `$1103a`) is `$80, $40, $20, $10, $08, $04` for levels 0..5 (`$25fec` shifts `$11032 <- $11034 <- $11036`, `$11036 >>= 1`).

**One source row (`$25a8a`)** makes three kinds of new samples. For source samples P and 4 neighbours it is a classic diamond-square step, done in a row-interleaved order so that only two 83-word scratch rows are needed:

```
025ad0  move.w (a1)+,d0 ; move.w (a2)+,d1     ; P[r][x] , P[r+1][x+1]
025ad4  add.w (a3)+,d0  ; add.w (a4)+,d1      ; + P[r][x+1] , + P[r+1][x]
025ad8  move.w d0,d2 ; add.w d1,d0 ; sub.w d2,d1 ; (bpl / neg.w d1)
025ae4  asr.w #2,d0                           ; d0 = mean of the four corners
025ae6  asr.w #1,d1                           ; d1 = |bottom - top| / 2   (local slope)
025ae8  add.w d6,d1                           ; + level amplitude ($1103a)
025aea  move.w d1,$68f4.w                     ; PRNG range
025aee  bsr.w $27462                          ; random in about +-range/2
025af2  add.w $68f6.w,d0 ; 025af6 move.w d0,(a5)+   ; new sample
025af8  add.w d6,$11048.l                     ; seed advances by the amplitude per sample
```

* Part 1 (`$25a8a`...`$25afe`): the **centre** of each cell from its 4 corners -> scratch row (`$10f08`).
* Part 2 (`$25b1c`...): the **horizontal-edge midpoint**: corners `P[r][x]`, `P[r][x+1]`, centre above (previous scratch row `$10f04`), centre below. Output row `2r`: `P, edge, P, edge ...`.
* Part 3 (`$25b7e`...): the **vertical-edge midpoint**: corners `P[r][x]`, `P[r+1][x]`, centres left and right. Output row `2r+1`: `edge, centre, edge, centre ...`; the Y flip is done later, in the final copy (section 2.8).
* The row result swaps the two scratch buffers (`$25bf6-$25c08`).

So the roughness added to a new sample is `rnd * (|slope|/2 + amplitude)`: **flat terrain gets only the small per-level amplitude, steep terrain gets large noise**. In the data this keeps the sea (where all neighbours are -2000) nearly flat while ridges break up.

**The PRNG** (`sub_027462`, 12 instructions, state in two words `$11048` / `$1104a`, range in `$68f4`, result `$68f6`):

```
027478  eori.w #$fade,d0   ; d0 = s0 ^ $fade
02747c  eori.w #$bead,d1   ; d1 = s1 ^ $bead
027482  mulu.w d0,d2       ; d2 = d1*d0              (d2 = d1 first)
027484  muls.w d2,d2       ; d2 = (low word of d2)^2
027486  add.w d2,d0 ; swap d2 ; add.w d2,d0 ; add.w d1,d0      ; fold the 32-bit square into 16 bits
02748e  muls.w $68f4.w,d0 ; swap d0 ; move.w d0,$68f6.w         ; scale to +-range/2
```

**Seeds are keyed to world position.** `$26212` builds three start seeds per level from `$1102e/$11030`, which accumulate `(origin+1) * amplitude` for the crops of all previous levels (`$26074..$260b6`); the first seed word then advances by the amplitude per sample along a row and the second by the amplitude per source row (`$25afe`, `$25b02`). Because the amplitude halves exactly as the sample spacing halves, the seed of a given *world point* is the same whichever window it is generated in.

**Evidence (all reproduce with `work/terrain/replica.py`):**

| Test | Result |
|---|---|
| Replica vs captured `$40040` arrays after level 0..5 (Hatari `savebin` at `$24d2a, $24d30, ... $24d48`) | interior (excluding the outer 2 cells): **16,362 / 16,362 words equal at every level**. Whole-array equality is 17,072-17,097 / 17,596; the differences are only at the borders, where the original reads stale scratch memory (`$10f08 - 2`, row `r+1` beyond the last row) |
| PRNG calls | replica 79,182; Hatari exec count at `$27462` = **79,182** (= 6 levels x 53 rows x 249) |
| Final window (`$24d4e`, rows 1..100, cols 31..130 of the 166 x 106 level-5 array, row-reversed) vs captured grid | **10,000 / 10,000** words |
| Terrain is a function of world position: window at player X vs at X+80 units (a 40-cell recentre, exactly what the game does) | overlap of the new window with the old one: **4,224 / 4,224 cells identical** (col shift -40); same for Y (+80 units -> row shift +40: 4,224 / 4,224) |
| Window quantisation | moving the player by 2 units (1 cell) leaves the window unchanged; 4 units shifts it by exactly 2 cells (100% match); the window origin is quantised to 4 units |
| **Live before/after of the same rebuild** (Hatari `savebin` of RAM at `$31df6` and `$31f12`; the player was recentred from window column 9.5 to 49.5, a 40-column shift) | new grid vs old grid shifted by 40 columns: 6,000 overlapping cells, **5,982 heights equal (99.7%)**, 5,858 height + both shade bytes equal (97.6%). The 18 height differences are 2 x 2 pads under objects/trees at the old window's edge. The shade-only differences are mostly the new window's last column (x = 99), whose lighting reads the next row's first cell as its east neighbour (a fake cliff, shade 0): never visible, the player is recentred long before |

Visual: `work/shots/levels_L0_L5_arrays.png` (the six 166 x 106 arrays, level 0 = whole world at 64 units ... level 5 = 2 units around the player: the coast gets fractal detail at each step).

### 2.4 Is it the same as the MW1 DOS fractal?

Same family, different detail. Section 7 has the full table. In short: both crop an `N x N` window around the player at each of 5-6 levels, double the resolution with the four-neighbour rule, end at a 100 x 100 patch at 2 units per cell and Y-flip the rows. MW1 (DOS) uses 32-bit cells whose low bits recycle as the "hash" (no RNG at all) and scales roughness by altitude (`avg*8 + 5000`); MW2 has an explicit PRNG keyed to position and scales roughness by local slope (`|dh|/2 + amplitude`).

### 2.5 After the fractal: what is added to the grid

Order from `sub_031dee` (addresses in 2.1):

1. **`$1bfba` (clears `$78000` mask + the shade bytes via `$1be66`, then)**
   * binds the area file's object list (`$b3a2`, 8-byte records `x(14 bit), y, type`; this area has 131 records) into the 16-byte marker table at `$4bfa8`, for objects within +-90 units (45 cells) of `$66bc/$66be` (`$1bff0: cmp.w #$5a,d2`). **In the captured Lobos window none were in range.**
   * stamps **roads** (`$1c9d2`, lists via `$b3d2`): axis-aligned segments; every cell on a segment gets `move.w #$4040,$2(a2)` (both shade bytes get class `$40`) and its four corner heights are set equal to its own height (`$1ca8c-$1ca9c`): flat road cells. The second list (`$1cbba`, via `$b3da`) stamps `$7070` and a quantised constant height (`$1ccb4`: `d7 = 50` if below 50 else `(d7 & $ff00) + $80`), looks like causeways/bridge decks `[INFERENCE]`. Measured here: 184 shade bytes = 92 road cells, all class `$40`.
   * places **trees** (`$1be92`), section 2.5.1.
2. **`$1c996`**: every height `h -> 2h` (`d1 = (a0); add.w d1,d1; move.w d1,(a0)+`). The code after the `bra.w $1c9c8` at `$1c9a2` (negative -> 0, `<= 9` -> `(h+1)*24`, else `h+250`) is **unreachable**: leftover from an earlier height mapping.
3. **`$1c146` pads**: for each marker record (**trees included**, `$6f78` counts them), the 2 x 2 cell patch under it is flattened to the height of its NW cell (`$1c164-$1c16e`): palms stand on flat 2 x 2 pads. Same idea as the DOS `0x78B8` (their pads are under buildings).
4. **`$1c180` craters**: a 128-entry ring (`$b3f6`, 4 bytes per entry, write index `$b3ce`, written by `$1c1f6` from `$1ada4` when the player uses a consumable: `$ef8a[..]` count is decremented and the player's position is stored). Every entry within +-90 units is applied: **the 2 x 2 patch is set to its NW height - 200** (`$1c1d2: subi.w #$c8`). So explosions leave craters that **survive regeneration** `[INFERENCE for "explosion"; mechanism read from the code, ring empty in the capture]`.
5. **`$1c832` lighting**, section 2.6.

#### 2.5.1 Trees: no data, a rule on the heights

`sub_01be92` (called from `$1c02e` inside `$1bfba`, on the raw heights after the road stamps):

```
loop y = 4,6,...,96 ; x = 4,6,...,96            (d1,d0 from 4 to $62 step 2)
  h = H[y][x]
  if h >= 20:      if h >= $1770 (6000) skip ; type = $ff     (cmp #$14 / cmp #$1770)
  else:            type = $fe ; if h > -180 skip              (cmp.w #$ff4c,d2 / bgt: the -180..19 band gets no object; only deep water gets type $fe)
  if (h + H[y-1][x] + H[y][x+1] + H[y-1][x+1]) & $1f != 0   skip    (1 in 32 gate; N, E, NE corner heights)
  if mask[y][x] or any of the 8 neighbours marked          skip    (3 x 3 clear)
  if any of the 16 cells at distance 2 is marked and the OR of the marks != 2   skip   (trees may stand 2 cells apart, objects need 3)
  place object at cell centre  x = (2x+1)<<8, y = (2(99-y)+1)<<8 ;  type byte $1d = d4 ; mask[y][x] = 2
```

* Heights here are the **raw (generator) units**, before the x2 pass (`$1bfba` runs before `$1c996`), so "20" is 40 final units and the tree line "6000" is above every height in the data (max 2514 in this window): effectively no tree line. Type `$ff` = land tree (20 <= h < 6000); type `$fe` is only produced for `h <= -180` (deep water), none passed the gate in this window. Model = `$514a[type & $1f]` (entries 31 = `$5ca3e`, 30 = `$5e144`). Roads write the mark `3` into the same mask (`$1ca7a: move.b #$3,(a3)`; the second list writes `4`), so **trees keep away from roads**.
* **Verification:** after the rebuild `$4bfa8` held **55 marker records, all type `$ff`**. The rule above, run on the captured generator heights with the road cells marked, reproduces **exactly the same 55 positions (identical sets, no extra, none missing)** (`replica.py`: `trees: replica 55, RAM marker records 55, identical sets: True`). Without the road marks the replica yields 59 (the 4 extras stand next to roads).
* Palm trees are what the screenshots show standing on the terrain (`banked.png`, `walking.png`); that model 31 is the palm is `[INFERENCE]` (the model was not rendered in isolation). If so, **in a window without buildings nearly all the "objects" the renderer pays for (57 marker records, 1-2 drawn per frame, 242-370 k cycles each, `render_audit.md` section 2) are procedurally placed palms.** The rule is the same as MW1 DOS (`terrain_fractal_original.md` section 8.4: `h <= 0 or h > 3000`, `(h+N+E+NE)&0x1F`, no neighbouring tree).

### 2.6 Baked lighting (`$1c832`, `$1c846`, `$1c956`)

For each of the 10,000 cells (`$1c832: move.w #$270f,d7`, loop calls `$1c846` with `a0` stepping 4 bytes) it computes **one brightness per triangle** and stores them in the cell's two spare bytes (`add.b d6,$2(a0)`, `add.b d6,$3(a0)`).

* Cell coordinates come from `divu.w #100` of the linear index (`$1c85c`), the diagonal parity is `(x + y + $5404) & 1`; `$5404 = ($66bc + $66be) & 1` (`sub_033748`). Odd cells are split NW-SE, even cells NE-SW (`$1c876` / `$1c8e4`). The renderer uses the same parity (`$1d768`: `(camX + camY + i + j) & 1`).
* Per triangle two height differences `d2`, `d3` (the two edges) go to `sub_01c956`:

```
01c95a  move.w $6792.w,d4            ; $0100 = 256
01c95e  move.w d4,d6 ; add.w d3,d6 ; add.w d6,d6 ; sub.w d4,d6        ; d6 = 256 + 2*d3        (n . L)
01c966  muls.w d2,d2 ; muls.w d3,d3 ; muls.w d4,d4 ; sum -> d0
01c972  jsr $4fe4.w  (-> $33822)     ; d1 = floor(sqrt(dx^2 + dy^2 + 256^2))   (|n|)
01c978  asl.l #3,d6 ; divs.w d1,d6   ; 8 * (256 + 2*d3) / |n|
01c97c  clamp to 0..15 ; add.w $5356.w,d6
```

  i.e. **shade = 8 (n . L)/|n| with L ~ (0, 2, 1)**: a flat triangle gives 8, a face turned towards the light up to 15, away from it down to 0. The sun is **fixed** (it never moves: no time of day in the formula) and low: elevation `atan(1/2)` = 26.6 deg, horizontal component along the grid's row axis. Rows increase southwards (the window is Y-flipped), a slope that rises towards the south is the brightest, so the sun is in the north `[INFERENCE: sign conventions]`. The normal uses 256 as the vertical component while one cell is 512 height units across, so relief is lit as if twice as steep as drawn (measured constants; the reason is not in the code).
* `$5356` is **+16 when any corner of the triangle is below 0 and the cell's byte pair has no class nibble yet** (`$1c846: moveq #$10,d5 ... andi.w #$f0f0 / beq`; `$1c87a-$1c890`): land triangles touching the sea get `shade + 16`, which the fill table maps to the **sand ramp** (section 5). Road cells already hold `$40` so they never get it.
* **Replica:** `light()` in `replica.py` (isqrt = `math.isqrt`) reproduces both shade bytes of every cell in rows/columns 0..98: **0 mismatches** (class-`$40` road cells given as presets). The last row/column differ because the original reads linearly past the grid (the next row, then the world map at `$49c80`).
* Result in this window: land triangles 0..15 histogram `[473,152,249,459,702,1075,1455,1817,1397,744,364,218,128,65,28,20]` (mean about 7), shore triangles 16..31 (470), road triangles 64..76 (184).

### 2.7 Why the hot loops are slow (profile of exactly one rebuild)

| Loop | Calls | Cycles | Per call | What it does / why it costs |
|---|---:|---:|---:|---|
| `$27462` PRNG | 79,182 | 28.86 M (31.6%) | **364** | three 16-bit multiplies per call: `mulu.w d0,d2` 59.8 cy, `muls.w d2,d2` 54.3, `muls.w $68f4.w,d0` 55.4 (the 68000 `mul` takes 38-70 cycles by operand), plus 2 absolute-word loads, 2 `eori`, 3 `add.w`, `movem.l` save/restore (36 cy): 169 cy of multiplies, the rest overhead. A 6-level pyramid needs one call per new sample. |
| `$25a8a` loops excluding the PRNG | 318 rows | 14.02 M (15.4%) | 177 per sample | neighbour loads through 4 post-increment pointers, `asr`, `neg`, scratch-row traffic, 3 passes per source row |
| `$33822` integer sqrt | **20,000** | 27.33 M (30.0%) | **1,366** | bit-serial (pair-of-bits) square root: **8.06 normalisation shift-pairs + 9.06 compare/subtract iterations per call** (exec counts 161,264 at `$33838`, 181,264 at `$33858`). Needed once per triangle to normalise the slope vector. |
| `$1c956` (excluding the sqrt) | 20,000 | 9.41 M (10.3%) | 470 | 3 `muls` (squares), 1 `divs.w d1,d6` (148.6 cy, 2.97 M), clamp |
| `$1c846` per cell | 10,000 | 6.03 M (6.6%) | 603 | `divu.w #100` to split the linear index (~140 cy), parity, corner loads/tests for 2 triangles |

Rebuild = 79k PRNG samples x 541 cycles (364 + 177) + 20k sqrt/shade x (1,366 + 470 + share of 603): the cost is **arithmetic, not memory**: no table lookups, no hardware assist, 68000 multiplies and divides, 16 MHz would still be 5.7 s. The world "stops" because this runs synchronously inside the world logic (`timing.md`).

`[INFERENCE]` Reuse would be possible in principle because the overlap with the old window is 60% identical, but the old grid has been doubled/stamped/lit already; not examined.

### 2.8 Memory map of the terrain data

| Address | Size | Content |
|---|---|---|
| `$40040-$49c7f` | 100 x 100 x 4 B | grid: height word, shade byte A (triangle 1), shade byte B (triangle 2); **row 0 = northernmost** (`$24d62` writes rows bottom-up: `suba.l #$190,a1` after each 100-word row) |
| `$40040-$48a38` during generation | 166 x 106 words, row stride 332 B | the level arrays (overwritten per level) |
| `$49c80` | 83 x 53 x 2 B | world seed map |
| `$7a580` | 83 x 53 words | window copy fed to the next level |
| `$78000` / `$78320` | 2 x 83 words | the two scratch rows of the subdivision (later reused: 100 x 100 byte object mask) |
| `$4bfa8` | 16 B per record | marker table (objects, trees) |
| `$6c000` | 32 x 32 x 16 B | per-frame cell records (section 3.2) |
| `$7c718` | 16 B per vertex | per-frame vertex cache |
| `$11048`, `$1104a`, `$68f4`, `$68f6` | words | PRNG state, range, result |
| `$18574` | 128 words | wave table (section 4) |
| `$3ac1a-$3b85a` | 112 x 28 B | span-fill variant records |

## 3. Height and cell data

### 3.1 The grid

`$40040`: 10,000 entries of 4 bytes, row stride `$190` = 400 B.

```
(50,50)  0c c2 05 05   height 3266 (= 6.4 cells above the sea), shade A 5, shade B 5
(97,0)   01 c8 08 0a   height  456 , shades 8, 10     (not a road cell itself: its height was overwritten as the east corner of the flattened road cell (96,0))
(96,0)   01 c8 48 48   height  456 , shades $48,$48   (road: class $40 + shade 8)
(99,90)  fc 6e 10 10   height -914, shades $10,$10    (land triangle touching the sea: +16)
```

* Heights range **-1482 .. +5028** in the captured Lobos window (-3484 .. 4058 in the older dump). Sea = negative; the map's flat deep sea is -2000 raw = -4000 final.
* Slopes are not stored; they live implicitly in the height differences and explicitly as the baked shade bytes.
* 2 triangles per cell, checkerboard diagonal.

### 3.2 The per-frame cell records (`$1d768`, `$6c000`, 1024 x 16 B)

A 32 x 32 array of records re-based on the camera cell every frame (record (13,13) = camera cell). Live example (record (13,13) at exit): `0c14 06 0a | 0000 | 0000 | 0a88 | ff | 01 | 0000 | 0000`.

| Offset | Meaning | Evidence |
|---|---|---|
| +0 word | height (copied from the grid by `$1d434`: `move.l (a5)+,(a4)` copies height + both shade bytes as one long) | `$1d51c-$1d562` |
| +2, +3 | shade bytes A / B | same copy |
| +4 word | squared distance from the camera cell in (1/8 cell)^2 units; table built once by `$1e54c`: `d0,d1 = -104 + 8i`, `d0^2 + d1^2` (record (14,13) holds 64 = (8)^2) | `$1e556-$1e580` |
| +6 | object hash link, cleared every frame (`clr.l $6(a0)` at `$1d782`) | `$1d768`; set by `$20222` |
| +8 | vertex-cache slot for the cell's NW corner, cleared every frame | same `clr.l` |
| +a byte | class: `$ff` land, `1` open sea, `0` shore | `$1d974 move.b #$ff,$a(a0)`, `$1d9a2 #$1`, `$1d9d0 clr.b` |
| +b byte | diagonal parity | `$1d790` |
| +c, +e | camera-relative x, y of the cell in 1/8 cell | `$1e564-$1e568` |

### 3.3 Sea level and waves

* **Sea level is height 0; negative = water.** The seabed is never drawn.
* Cell classes by corner heights (`$1d8d4`): all four >= 0 -> land (`$a = $ff`, `$1d950: bpl $1d974`); all four < -128 (`addi.w #$80` then AND sign, `$1d954-$1d96c`) -> open sea (`$a = 1`); otherwise **shore** (`$a = 0`), where `$1f006` splits each triangle **exactly at the waterline** against the wavy surface (`$a(aN)` = height above the wave at each vertex; `$1f796/$1f336/$1f3c2`).
* **Sea vertices lie on a wave surface**, not at 0: height = `wave[(h & $7e)/2 + phase]`, table `$18574` = 128 words built by `$1dd7e` as `sin >> 8 - 64`, i.e. a sine between **0 and -128** (+-64 about -64) (`$1dafc-$1db16`: `andi.w #$7e,d0 / movea.l $1dfba(pc),a3 / move.w (a3,d0.w),d0`). The phase advances by 8 bytes (4 entries) per frame: `$1dcae: addq.w #$8,$1877c / andi.w #$7e` -> period 16 frames. The low bits of the (negative) height act as a per-vertex phase, so the wave field is a free noise function. Sea triangles are coloured `40 + ((wave2 - wave1) >> 5)` (`$1edb6-$1edfc`, `$1ef02`): +-4 around 40, glints of two blues.
* **Underwater camera** (`$20272`..`$202e0`: `jsr $506e` = height of the wave surface at the camera; `cmp.w $18786,d5`; if the camera is below the surface `$18768 = 0`): the draw radius shrinks to 4.5/4.0/3.5/3.0 cells (`$510,$400,$310,$240`).

## 4. Display pipeline per frame

`sub_01dc12` (called from `$1dbbe` -> `jsr $505c`), order from `$1dc12-$1dcaa`:

| Step | Routine | What | Per-frame figure |
|---|---|---|---|
| 1 | `$20272` (once per frame from the main loop: `$315a0 jsr $5086` -> `jmp $20272`) | **view setup**: `$18784 = X - $6400`, `$18788 = -(Y - $6400)`, `$18786 = altitude $764c`, draw thresholds `$18772..$18778`, underwater test, heading `$6742/2 + $100`, bank, pitch | thresholds `$a90 $900 $790 $640` |
| 2 | `$1dc12` start | `$67c4 = 8` (vertex-slot cursor reset), camera cell `$18790/$18792 = (x >> 9) + 50`, fraction `$1878a/e = x & $1ff` | |
| 3 | `$1d88e`, `$1d768` | vertical bounds of the block cull (`$187ae = zc + 1000`, `$187b0 = -zc - 128`, `$1d88e`; mode 0 uses different bounds) and **grid init**: 1,024 records re-initialised | 85-87 k cy (4.5%; `p4_grid` brings it to 31 k) |
| 4 | `$20088` | **marker pass**: ~57 marker records, 2 `divs` each, +-8-cell window, hash insert into the cell record `+6` | 39-41 k (2-2.6%) |
| 5 | `$1dcfa`, `$1d596` | rotation matrix from heading/pitch/bank (`$18562`, 2.14 fixed point), then the **separable view tables T1/T2** (`$188f8`, `$18a40`, 41 entries x 8 B): `entry[i] = entry[0] +- i*step` (two 20-iteration loops) | |
| 6 | `$1d434` | **hierarchy cull**: three nested 9 x 9 loops = 729 cells = a 27 x 27 block around the camera; each 3 x 3 level is tested by the AND of 4 precomputed corner outcodes (`$1e750`: 6 bits = 5 frustum planes + "beyond draw distance"); then per cell `cmp.w $4(a0),d3` against the radius; accepted cells are appended to the list `$18758` | 60-66 k (3.2-4.2%); 99-116 cells tested at the last level, **63-80 accepted** |
| 7 | `$1d8d4` | **classify + vertex transform** per accepted cell (the hook `$1d974` of the P7 cull sits here): class, slot lookup, vertex `X = ((h*$18568)<<2>>16) + T1x[i] + T2x[j]`, same for Y with `$1856a`, W with `$1856c`; cached per frame in the 16-byte slots at `$7c718` | 83-102 vertices per frame, **no vertex is transformed twice**; 3.0-3.2 slot lookups per transform (`render_audit.md`) |
| 8 | `$1fa04` | **outcodes + perspective divide** | see below |
| 9 | `$1ebda` | **polygen**: per cell, pick the fog band, look up the 4 vertex slots, AND of the 4 outcodes (skip if all outside), then emit 0-2 triangle records into the stream `$66d0` (colour word + 3 slot offsets, `movem.w d0-d2/d4-d5,(a0,d7.w)`) ; if the cell holds an object, emit a marker | 38 / 60 / 51 triangles (f / w / b) |
| 10 | `$1b996` | **sky fill** | 55 k (2.6-3.6%) |
| 11 | `$1fa54` | **stream walker**: per polygon, OR/AND of the vertex outcodes: trivial accept -> `$501a` (edge walker `$3c5c4`); straddling -> `$1fdf0` clip per edge; marker -> object draw `$1c3fc` (models) | |
| 12 | `$38c6e` -> `$38cd0` | **span fill** per polygon after its last edge | |
| 13 | `$30f2c` | **cockpit overlay** replay | 63 k (3.0-4.1%) |

### 4.1 Projection and clipping (terrain path)

* Terrain vertices are projected by `$1fa04`, not by the polygon-engine routines. The view vector for a vertex is `h * (mX, mY, mW) + T1[i] + T2[j]` (three `muls.w` + `asl.l #2` + `swap` = `>> 14`, six adds, `$1da92-$1dac2`): **the x/y part of the camera-space position comes from two small per-frame tables (one per column, one per row), only the height needs multiplies.**
* `Y' = 2Y + (Y >> 2)` (`$1fa24-$1fa2a`), then `x = X*159 / W`, `y = Y'*71 / W` (`$1fa40: muls.w d5,d0 / $1fa44: divs.w d2,d0`, d5 = 159, d6 = 71). So `Y'*71 = 159.75*Y`: both axes use about the same scale, **horizontal field of view about 90 deg**. Verified on one vertex in `projection.md` 7(b).
* Outcodes, `$1f9b6-$1f9f6`: `W <= 0 -> $1010`, `X > W -> $808`, `Y' > W -> $202`, `X < -W -> $404`, `Y' < -W -> $101`. A vertex with a non-zero code skips the divide (`$1f9f8 beq $1fa2e`).
* Polygon level (`$1fa54`): wholly outside -> dropped; wholly inside (61% of the polygons, `render_audit.md` 4c) -> no clip; straddling (22.9 / frame in w) -> `$1fdf0`, a Cohen-Sutherland clipper in homogeneous (X, Y, W) coordinates with `muls`/`divu` (45.7 full clips per frame, ~1.2 k cy each).
* The object polygons (trees etc.) go through the other engine: `$3838c` outcodes, **`$38442` polygon reject/accept pass, `$385b4` clip against each of 4 planes** (`$67c6` = plane 0..3), `$383ce` divide with the focal length **`$682a` = 164**: `x' = x*164/z + 160`, `y' = y*164/z + 128` (`f38cd0.md` 7.3), bounds `$67ae..$67b4` = 1 / 319 / 58 / 199 (the 3D window is lines 58-199).
* Terrain has **no backface test that ever fires** (0 removed in all three captured scenes, `render_audit.md`); triangles are culled only by the outcode AND.

### 4.2 Draw order and objects

* **Terrain is not sorted.** The 3-level nested loops of `$1d434` walk blocks in a precomputed camera-relative order, far to near: the distance word of the accepted cells falls `2624, 2176, 2560, 1856 ... 128, 64, 0` along the list (measured on the list `$18758` in the entry dump: 76 cells). Within a block the order is the loop order; painter's overdraw is only 6.7-10.6% of span pixels (`render_audit.md` section 3).
* **Objects are merged into the same order by cell.** An object lives in the hash slot of its cell (`+6`); in `$1ebf2-$1ec06` polygen emits the cell's triangles and then, if `+6 < 0`, a stream marker `(key, fog band)`. `$1fa54` calls the model drawer `$1c3fc` when it meets the marker, so the object is drawn after its own cell's terrain and before nearer cells. Inside an object, polygons are depth-bucketed (`$3bd0c/$3bda0`, 0.3-0.7%).
* Objects have no distance LOD: `$1c456-$1c488` indexes `$514a[type & $1f]` only (`render_audit.md`).

### 4.3 Span fill and the sky

* `$38c6e` sets up (450 cy) and `$38cd0` dispatches (262 cy, three dependent table loads) to one of ~112 pre-unrolled variants (`f38cd0.md`, `spanfill.md`), chosen **per polygon**; the row-parity bit of the first row picks the even/odd entry (the 2-row dither phase). Interior spans are opaque `move.l a3,(a2)+ / move.l a4,(a2)+` stores (16 pixels per 8 bytes); the two edge groups are read-modify-write with the `$40000` masks.
* **Sky**: `$1b996` fills lines 58-199 (`$2440` offset, 71 passes x 2 lines) with colour 15 (planes `$7fff7fff` / `$ffffffff` ...: only the first pixel of each line is colour 0). It is repainted every frame (45,440 px); terrain is drawn over it. **There is no horizon line or gradient; the horizon is where the last fog band ends**, and the same palette entry 15 is the haze colour. The `p4_hud_pfx_*` patch skips the rows terrain never reaches.
* **Cockpit**: `$30f2c` replays a list of 382 masked records (5,396 opaque pixels, 11.9% of the 3D window) over the terrain (`cockpit.md`); 45-59% of terrain pixels when walking end up under it.

### 4.4 Cost per stage and counts (from the existing notes; unpatched, `render_audit.md`)

| Stage | w (walking) | f (standing) | b (banked turn) |
|---|---:|---:|---:|
| Frame, cycles | 1.524 M | 1.903 M | 2.116 M |
| Transform (cell classify, slot, vertex) | 14.3% | 17.3% | 17.9% |
| Clip (`$1fa54`, `$1fdf0`, objects) | 12.5% | 14.8% | 12.0% |
| Edge walk (`$3c5c4`, objects) | 12.4% | 14.2% | 12.2% |
| Span fill (`$38cd0`, 112 variants) | 10.1% | 12.3% | 12.7% |
| Terrain grid init + polygen | 10.0% | 7.1% | 7.3% |
| World / object selection (hierarchy, markers) | 8.2% | 7.5% | 7.3% |
| Sky `$1b996` | 3.6% | 2.9% | 2.6% |
| Cockpit replay | 4.1% | 3.3% | 3.0% |
| (HUD 12.3 / 7.5 / 14.7%, logic 8.6 / 7.4 / 6.4%) | | | |
| Cells in the 27 x 27 block / within radius / with at least one visible triangle | 729 / 68.8 / 30.2 | 729 / 63 / 19 | 729 / 80 / 25.5 |
| Triangles generated (= in the stream; 0 removed by backface) | 60.5 | 38 | 51 |
| Polygons filled (terrain) | 58.4 | 37 | 48.5 |
| Vertices transformed (unpatched -> with `p7_cell_*`) | 89.8 -> 51 | 83 -> 35 | 102 -> 64 |
| Vertices perspective-divided | 30 | 20 | 24 |
| Edge-walker calls | 172.8 | 104 | 142 |
| Fill rows / spans (16-pixel groups written) | 442 / 857 | 829 / 1,377 | 1,434 / 2,629 |
| Span pixels written (terrain + objects) | 7,001 (15%) | 9,717 (21%) | 20,104 (44%) |

Per-triangle cost is about 14.5 k cycles of fixed overhead (edge setup, clip, dispatch); the profile is flat after the shipped patches (`render_audit.md` section 6).

## 5. Shading: how a triangle's colour is chosen

**There are three inputs: the baked shade byte (slope vs sun), the cell/feature class, and the distance band. There is no height-based colouring and no snow.**

Fill selector for a terrain triangle: `$6808 = (fog band << 8) | colour byte` (`$1ed3a-$1ed46`: `move.w $18766,d0 ; move.b $2(a6),d0`). The dispatcher `$38cd0` maps it through `byte map $3ba5a[colour]` + `band*64` -> word table `$3b85a` -> 28-byte record in `$3ac1a` (two code entry points for even/odd rows, two dither words, four per-plane pattern longs). Decoded for every colour byte and band with `work/terrain/decode_fill.py` (palette = `$4a6a`: `000 030 430 040 025 411 540 050 333 444 740 777 036 522 650 057`, ST 3-bit RGB).

**Fog band** (`$1ec28-$1ec66`): `d = $4(cell)` (squared distance in (1/8 cell)^2): `d < $640` -> band 0; `< $790` -> 1; `< $900` -> 2; else 3 (cells are not drawn beyond `$a90`).

| Band | Distance from the camera cell | Terrain colour mixed with the sky colour (palette 15 = `$057`) |
|---|---|---|
| 0 | < 5.0 cells (`$640` = 40^2 / 64) | 100% terrain |
| 1 | 5.0 - 5.5 | 75% terrain / 25% sky |
| 2 | 5.5 - 6.0 | 50 / 50 |
| 3 | 6.0 - 6.5 (`$a90` = 52^2) | 25 / 75 |

(Underwater: radii 3.0 / 3.5 / 4.0 / 4.5 cells.) In band 0 the 16 shade values are a **ramp with 3 dither steps between neighbouring palette colours** (a 4 x 2 ordered pattern: 25% = every 4th pixel, 50% = checkerboard, 75%; the pattern shifts by 2 pixels on the next row). Pattern words seen live (`spanfill.md` E7-E9): `$7777/$dddd` (75%), `$5555/$aaaa` (50%), `$1111/$4444` (25%).

**Colour byte -> ramp (band 0; palette indices; "k:25" = 25% of the pixels are colour k)**:

| Colour byte | Source | Ramp (shade 0 .. 15) |
|---|---|---|
| `$00-$0f` | land triangle, all corners >= 0 | `0:75,1:25` (black-green) -> 1 (`$030` dark green) -> 1/3 -> 3 (`$040`) -> 3/7 -> 7 (`$050` bright green). Shades 0,1,2 are the darkest; 13-15 are pure 7 |
| `$10-$1f` | land triangle with a corner below sea level (+16 in `$1c846`) -> **shore / sand** | black -> 2 (`$430` brown) -> 6 (`$540`) -> 14 (`$650` tan) |
| `$20-$2f` | **sea** (computed at render time as `40 + (wave diff >> 5)`, so 36..44) | 8 steps (the byte pairs map to one record): 36-37 `4:75,0:25`, 38-39 pure 4 (`$025` blue), 40-41 `4:75,12:25`, 42-43 `4:50,12:50`, 44-45 `12:75,4:25`, 46-47 pure 12 (`$036` lighter blue) |
| `$30-$3f` | (table only; nothing in the terrain code writes it) | black -> 5 (`$411`) -> 13 (`$522`) |
| `$40-$4f` | **road** (`$4040` stamp + shade 0..15) | black -> 8 (`$333` grey) -> 9 (`$444` lighter grey) |
| `$50-$5f` | (table only) | solid 10 (`$740`, the animated palette entry) |
| `$60-$6f` | (table only) | solid 11 (`$777` white) |
| `$70-$7f` | second linear feature (`$7070` stamp) | shades 0-5 black, 6-15 grey ramp as `$40` |

Bands 1-3: every one of the 15 distinct base colours (1 3 7 2 6 14 4 12 5 13 8 9 10 11 0) becomes *colour + sky*: `X:75,15:25`, `X:50,15:50`, `15:75,X:25`. The terrain table (`$3ba5a`) needs **96 records** (51 in band 0 + 15 each in bands 1-3) of the 112 in `$3ac1a-$3b85a`; the second byte map `$3baea` (selected when `$6806 != 0`, used by object polygons `[INFERENCE]`) uses the rest.

So the "dithered fills" are two different things at once: (1) a 16-step *lighting ramp* simulated with 5 palette colours and ordered dither; (2) a *fog ramp* that mixes the same colour with the sky colour. A far, sunlit slope in band 3 is a 25% scatter of green on a blue sky.

## 6. Draw distance and level of detail

* **Radius 6.5 cells** from the camera *cell* (the fractional position is ignored): `$20272` thresholds `$a90 = 2704 = 52^2` in (1/8 cell)^2 units; replica of the `$1e54c` table: the disc contains **137 of the 28 x 28 cells**, the frustum cull leaves 63-80 per frame. Measured effect of shortening it (`render_audit.md` section 5): cut `$a90 -> $900` (no band 3) saves 9.0% (f) / 12.2% (w) / 5.2% (b); `-> $790` saves 12.9 / 19.3 / 9.9%.
* **No LOD**: terrain cells are the same 2-unit quads at every distance; only the fog band changes the colour. A band-3 polygon of 80 px costs the same ~5 k fixed cycles as a 600 px one; a far-cell merge was estimated at 5-8% and not built. Objects: no LOD either.
* **Vertical**: the camera altitude does not enter the draw radius; only the underwater switch changes it.
* **Window of generated terrain** is much larger than what is drawn: 50 cells each way vs 6.5.

## 7. Comparison with Midwinter 1

### 7.1 MW1 DOS (docs/terrain_fractal_original.md, vcheckk-archive/midwinter-decode) vs MW2 Atari (this note)

| Aspect | MW1 DOS (their decode) | MW2 Atari (measured here) |
|---|---|---|
| Seed data | `ZBUFFER.BIN`: 50 x 50 x 32-bit (height + noise word), one island 3,200 units | file 96: 83 x 53 x 16-bit, 42 areas in a 10,240 x 6,400 unit world, 128 units per sample |
| Levels | 5 (shifts 4,4,5,6,7), 50 -> 100 per level, window crop around the player | 6 (amplitudes `$80..$04`), 83 x 53 -> 166 x 106 per level, window crop around the player |
| Final patch | 100 x 100 at 2 units/cell, patch rows Y-flipped | 100 x 100 at 2 units/cell, rows Y-flipped (`$24d62` bottom-up copy) |
| Four-neighbour rule | centre, H-edge, V-edge per source row, stale scratch at the borders | the same row-interleaved order, same stale-scratch border quirk (`$10f08 - 2`) |
| Noise source | none: the low 16 bits of the corner sum are recycled as the hash ("zero RNG") | explicit hash PRNG `$27462`, seed keyed to position |
| Roughness | altitude-scaled: `mult = avg*8 + 5000`, shift grows per level | slope-scaled: `|dh|/2 + amplitude`, amplitude halves per level |
| Determinism | yes | yes (replica bit-exact; overlap identical) |
| Trees | rule on heights (`h <= 0 or h > 3000`, `(h+N+E+NE) & 0x1F`, no neighbour tree) | same rule (`20 <= h < 6000` raw heights, `& $1f` hash gate, 3 x 3 clear, 5 x 5 ring may only hold trees, roads/objects block; type `$fe` for deep water `h <= -180`) |
| Pads under buildings | 2 x 2 flattened under every object (`0x78B8`) | same (`$1c146`) |
| Roads, craters | not in their decode | roads (flat grey cells), craters ring |
| Triangles | 2 per cell, checkerboard diagonal | same |
| Triangle colour | hash byte low/high + "row class"; 8 sun sectors x 12 slope classes; palette bytes still open | baked Lambert shade (16 levels) per triangle, fixed low sun in the north `[INFERENCE]`; class nibble for sand/road; fog band |
| Draw window | +-8 cells (17 x 17) around the camera cell | 27 x 27 hierarchical block, radius 6.5 cells |

The MW2 numbers (a 4-neighbour mean + noise, window pyramid, trees by hash gate) show the same author's design carried forward; the *differences* (noise scaling by slope, explicit seeded PRNG, baked lighting, roads, craters, area files) are real improvements, not a different algorithm.

### 7.2 MW1 Atari ST renderer (`games/done/midwinter/work/notes/render.md`) vs MW2

* MW1 Atari draws a fixed **8 rings x 4 sides** grid of 21-column rows chosen by heading sector, transforms **182-191 vertices per frame with no slot cache**, projects before culling, 2D screen-space clipping per edge, one painter list for terrain and objects, 16 solid fill variants plus a two-pass 2-colour dither; MW2 culls hierarchically, caches vertices, clips in homogeneous space, orders terrain without sorting and has 112 fill variants. MW1's heights come from "the height map"; **its generator was not analysed on the Atari**, so whether it runs the same fractal on the ST is `[INFERENCE]` (the DOS decode says the data file is stored big-endian "Atari ST heritage").
* Both share: edge -> per-scanline table -> unrolled DDA -> table-driven span fill, a masked-replay cockpit/goggles list, and a complete per-frame rebuild (no inter-frame caching).

## 8. Clever tricks (and how they are paid for)

1. **8.8 KB of data become a 16-million-cell world** by midpoint displacement; a different 83 x 53 array would give a different world. Detail below one base sample (128 units) is pure algorithm.
2. **Coordinate-keyed PRNG** (state = world position x amplitude): no per-tile storage and no seams. The same island point has the same height from any window: 4,224 / 4,224 cells equal in the overlap after the 40-cell recentre.
3. **A window pyramid with constant cost**: only an 83 x 53 patch is subdivided at each level (about 7.3 M cycles per level, independent of the level), never the whole world.
4. **Slope-adaptive noise** (`|bottom-top|/2 + amplitude`) in one `asr` + one `add`: coasts and ridges get detail, calm sea stays calm, and no per-height table is needed.
5. **Row-interleaved diamond-square with two scratch rows** and no second full array; the Y flip is paid for by a negative row stride in the final copy.
6. **Trees need no data**: a 1-in-32 hash of four corner heights on a half-resolution lattice plus a clearance mask. The same rule since MW1.
7. **Lighting is baked into 2 bytes per cell**, computed per *triangle* once per rebuild and consumed as the fill selector. The renderer never lights anything; shade byte + fog band index the fill tables directly (`(band << 8) | byte`).
8. **One palette, two meanings of dither**: the same ordered-dither mechanism gives a 16-step lighting ramp from 5 palette entries *and* a 3-step haze to sky colour; the hard 6.5-cell cut is invisible because the last band is 75% sky.
9. **The horizon is free**: the sky is a flat fill, terrain stops, nothing is drawn for the far field.
10. **Separable vertex transform**: per-frame column and row tables (`T1`, `T2`, 41 entries each) so a vertex costs 3 multiplies (height) and 6 adds; and a per-frame vertex cache with a generation reset (`$67c4 = 8`) so no corner is transformed twice.
11. **Hierarchical culling with precomputed corner outcodes** (9 x 9 x 9 loops, the AND of 4 corner codes, 6th bit = beyond draw distance).
12. **Sea waves from a 128-word sine and the sea floor's own height bits** as the per-vertex phase; the wave surface is also what the shoreline is clipped against.
13. **Underwater is just a different set of four thresholds** (visibility 3.0-4.5 cells).
14. **Craters survive terrain regeneration** because the game re-applies a 128-entry ring of crater positions after every rebuild (the terrain itself is never saved).
15. **Reusing registers as addresses**: the span filler keeps the buffer's high word in `d0` and ORs in the 16-bit offset (`move.w (a0)+,d0 / movea.l d0,a2`), so double buffering needs no extra arithmetic (`spanfill.md`).

## 9. Open items and inferences

* The meaning of `$274e4` (0.58 M cycles in the rebuild) is not identified.
* Colour bytes `$30`, `$50`, `$60` have table entries but nothing in the terrain code writes them; they may be used by objects sharing the table `[INFERENCE]`.
* Sun direction sign (north) and the 2x relief exaggeration in the lighting (256 vs 512 per cell) are derived from the constants, not observed in a render.
* Real-world units (feet per height unit) are not in the binary.
* Roads / second linear feature types (bridges?) and crater semantics are read from code, not exercised live; the road list in this area did exist (92 road cells measured) but the crater ring was empty.
* Area files (`$289ac`): what else they carry (island text, unit lists) was not decoded; the cost and mechanics of an area switch were not measured.
* Not run: a vehicle's view, other islands, or a TT/Falcon; the generator is independent of the view so the numbers should hold.

## 10. Reproduce

All in `games/in_progress/midwinter2/work/terrain/` (run from the gamebench root; Hatari needs the `snapshots/1mb_ingame_walking.sav`):

```
python3 games/in_progress/midwinter2/work/terrain/cap_rebuild.py      # RAM at rebuild entry/exit, level arrays L0..L5, grid before/after each stage -> /tmp/terr/*.bin, log.txt (CycleCounter deltas)
python3 games/in_progress/midwinter2/work/terrain/prof_rebuild.py     # one-rebuild profile: cycles + exec counts -> /tmp/terr/plog.txt, prof_full.txt
python3 games/in_progress/midwinter2/work/terrain/replica.py          # bit-exact replica checks against /tmp/terr (levels, window, lighting, trees)
python3 games/in_progress/midwinter2/work/terrain/overlap_live.py      # live old-vs-new grid overlap after the 40-column recentre
python3 games/in_progress/midwinter2/work/terrain/decode_fill.py 0    # fill-table decode ($3ba5a terrain table; 1 = object table)
python3 games/in_progress/midwinter2/work/terrain/figs.py             # work/shots/world_base_83x53*.png, levels_L0_L5_arrays.png, window_100x100_*.png
python3 games/in_progress/midwinter2/work/terrain/shot_at.py 66 72 800 at3.png 2900   # screenshot after poking the player (cell x, row, heading, altitude)
```

Files in `work/shots/`: `world_base_83x53_marked.png`, `levels_L0_L5_arrays.png`, `window_100x100_lit.png` (baked shading with the road stairway), `window_100x100_height.png`, `at3.png` (hills fading into the sky), `banked.png` (fog bands, a palm), `walking.png`, `foot.png`.
The extraction of the world map from `FILES/FFB` uses the loader's rule from `loading.md` (file 96: track-side 110, offset `$cfe`, length 8,798; checksum `$01b0` verified).
