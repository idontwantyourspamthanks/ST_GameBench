# Moonshine Racers: the road (geometry `$100b4` + span draw `$17c42`): how it works, what is invariant, what is faster

Study owner: MSRRoad.  Patch prefix `rd_`, tools and raw data in `work/road/`.  Machine for every Hatari number: Hatari 2.6.1, STE, TOS 1.62, 1 MB, 8.02 MHz, 50 Hz, tick patches (`mt_*`) OFF,
160,256 cycles = 1 VBL.  "Musashi" = the Musashi 68000 core (`work/road/musashi/`, built from the copy in the Python site-packages) running the game's own routines offline on RAM dumped from a live
frame (cycle counts of the plain 68000 table, no wait states): it reproduces Hatari's routine costs (stock edge routine 427 cycles/call vs 424 in the Hatari profile of `render_patches.md`; stock span draw 159.5 k vs
Hatari stage 176 k minus ~17 k interrupts), so it is used for exact-equality gates and per-instruction profiles; all headline numbers below are Hatari.  Unproven items are marked **[INFERENCE]**.

## 0. Result in one page

1. **The road is a compiled-span + pre-rendered-edge-window renderer, not a row-template renderer.**  One record (`w0, A, B, F`, 8 bytes) per screen row; a row is `[grass][edge window A, 32 px][road][edge window B, 32 px][grass]`;
   the fills are 16-px aligned `movem.l` spans, only the two 32-px windows are pixel exact (pattern table `$4ff8`, built from constants).  Section 1.
2. **Template premise (rows = f(row index, stripe phase) + horizontal offset) is false.**  Per row only `w0` (edge thickness class) is a static function of the slice and `F` is stripe phase; the two edge positions `A`, `B`
   come from per-position track tables that the game rewrites every frame while driving, so the road width differs per row and per frame (445 distinct `(w0, A-B)` pairs in 240 frames; between consecutive driving frames only 20 % of the rows are
   identical, 31 % differ only in `F`, 49 % move an edge).  Section 2.  A template needs one pre-rendered row per (w0, width, phase): hundreds of rows x 16 shifts.  What *is* shift-invariant is each edge on its own, and the game already stores exactly that (windows).
3. **Blitter: no gain at 8 MHz.**  Measured in Hatari (section 4): an aligned row copy by the blitter (one blit per row) costs the same as a CPU `movem` copy (59.9 k vs 60.8 k cycles per 80 rows); the blitter does the 0-15 px shift for free
   (62.4 k per 80 rows, +4 %) where the best CPU shift costs 557 k (9x).  But the road is not a copy of template rows, and the blitter's bus cost per word equals the CPU's, so it cannot beat a good CPU draw (95 k).  Mega STE: Hatari's 16 MHz model does not speed up bus-bound code (blitter and CPU copy both unchanged), only register work.
4. **Built and gated (both pixel-identical, `default: no`):** `rd_geom` (geometry: 87.4 k -> 57 k moving, 12 k standing) and `rd_draw` (span draw: stock+`mr_edge` 143 k -> 95 k).  Hatari, cycles per pass, tick patches off:

| scene | stock | shipped render set (`mr_edge mr_map mr_digit`) | + `rd_geom rd_draw` | gain over shipped set |
|---|---:|---:|---:|---:|
| race_start (driving) | 841,010 = 5.248 VBL | 753,865 = 4.704 VBL | **686,662 = 4.285 VBL** | **-67,203 = -8.9 %** |
| race_grid (standing) | 764,627 = 4.771 VBL | 702,780 = 4.385 VBL | **579,531 = 3.616 VBL** | **-123,249 = -17.5 %** |
| (alone, without `mr_*`) race_start | | | 720,661 (-14.3 % vs stock) | |
| (alone) race_grid | | | 598,283 (-21.8 % vs stock) | |

   `rd_geom` alone: race_start -35,434 (-4.2 %), race_grid -83,914 (-11.0 %).  All with `tools/msrabtest.py` ALL IDENTICAL (4 snapshots, flips 10 and 40, per-pass state `$1000-$13ff, $29c8-$34ff, $4500-$4fff` equal), negative control DIFFER, cold boot 1 MB (and 4 MB: see 7.6).
5. Recommendation: ship `rd_geom` + `rd_draw` on top of `mr_*` (8.9 % driving, 17.5 % standing); the two stalls (one-time table generation 0.9 M + 2.0 M cycles at the first road frame) need the tick pacer's resync (section 7.5).  Not worth building: blitter/template, row skipping (section 5).

## 1. How the road is drawn (evidence: disassembly lines, dumps `work/road/dump/`, replay `work/road/geom_test.py` / `draw_test.py`)

### 1.1 Frame order and cost (Musashi, stock, frame "start 20"; Hatari stage numbers are in `rendering.md` section 5)
`$17c24` clears `$4b78-$4ff7` (the stream terminator), `$100b4` geometry builds the record stream, `$17c42` draws.  Geometry 87.6 k (loop 1 10.5 k, loop 2 18.4 k, loop 3 58.0 k = `$10216-$102b0`, 112 iterations, 418 cycles each before the emission).
Draw 173,054: row control 78,360 + edge routine `$1058a` 62,924 (147 calls x 428) + `movem.l` fills 29,312 (`work/road/dump_frames.py` + `rdlib.py`; per-instruction profile via the Musashi `prof_*` calls).
Replays are exact: the stock geometry replayed on the dumped inputs reproduces the dumped record stream and tables on all 240 frames (4 scenes x 60 passes), the stock draw reproduces the screen bytes it painted (0 differing bytes).

### 1.2 Geometry `$100b4` (`work/road/dis_geom.txt`)
Inputs that change per frame: `$1bba` curve phase, `$1318` curve step, `$23c6` hill position, `$13ae` road position, `$130c` speed (stripe phase `$1308/$130a`).  Dynamic tables, written ONLY by `$fe50` (profile bytes `$13b0` left / `$17b0` right, 1024 ring),
`$ff76` (curve `$1bbc`, 1024 words) and `$1003c` (elevation `$23c8`, 1024 bytes), each of which starts `move.w $130c.w,d0 / subq.w #1,d0 / bmi -> rts` (`00fe50-00fe56`, `00ff76-00ff7c`, `00103c-001042`): **no table changes while speed is 0**.
Static tables (generated from constants at level start by `$16404`, `$16428`, `$164c4`, `$164ea`; identical in all 4 RAM dumps and all 240 frames): `$4564` (T1, 112 depth steps), `$4644` (W0 = `((0xea60 + i*0x2249) >> 16 & 0xff) << 8`, multiples of 256, 0..$f00), `$68000` (hill map `[slice][diff+128]`), `$4ff8` (edge patterns).
- **Loop 1 (`$100dc`)**: `X1[i] = (sum_{j<=i} (sin[(2*T1[j] + $1bba) & $7fe] - sin[$1bba])) >> 8` -> words `$4802` downward to `$4724` (curve offset per slice; "sin" is the dynamic curve table).
- **Loop 2 (`$10158`, hills)**: `H_i = map[i][ (elev[(T1[i]+$23c6)&3ff] - elev[ref]) as signed byte + 128 ]`; writes `232 - H_i` to `$49c4` (downward), the per-slice row count list (`$4aa4` upward: 0 = hidden, `H_i - H_prev` rows, `$ffff` after the `$8e` clip) and the pushed differences.
- **Loop 3 (`$10216`)**, for iteration k = 0..111 (far to near, slice `s = 111-k`):
  `C[k] = ((k+1)*S >> 16) + $a0 - hw(W0[min(k,80)]) + X1[111-k]` with `S = ($1318 << 16) >> 5` (`$131c`), `hw(w) = ((w>>8)+1)>>1`; stored at `$4804+2k`.
  **The two `mulu.w`**: `wL = (profile_left[ (T1[s]+$13ae)&3ff ] * ($1316 + k)) >> 4` (`$1025e`, byte at `$13b0+idx`) and `wR = (profile_right[idx] * ($1316+k)) >> 4` (`$1026e`, byte at `$17b0+idx`): profile byte x perspective factor `m = $1316 + k` (9..120),
  `lsr.w #4` on the low word (the product is < 65536 while `m <= 257`).  Then `A = C + wR`, `B = C - wL`.
  **Only the 80 far slices (counter >= 32, `cmpi.w #$20,d4` at `$1027a`) emit records**; the 32 near slices compute `A,B` for nothing (13.4 k cycles in stock).  Emission: stripe state machine (`$10286-$10298`: byte table at `$4563 - $1308`, step `$10`, adds `$2000` to F per
  stripe boundary), `count = -(a0)` rows from the hill list, `movem.w d0-d2/d6,-(a6)` once per row: record = `(w0 = (a3)+, A, B, F)`, `F = stripe bits 15-13 | 2*k`.
- **Incremental / table reproduction.**  Exact: yes for the arithmetic (table `PT[m][b] = (b*m)>>4`, 80 x 256 words, validated on the 240 frames and on 2,100 fuzzed states with random profile/curve/elevation tables, random `$1316`, speed, phases).  Not possible: reuse of a previous frame's per-slice values
  while moving, because the product operands change every frame (`idx` shifts by the speed, the factor `m` is tied to the slice, not to the world point) and all three ring tables change.  Reuse is possible while standing (below).

### 1.3 Record -> row semantics (stock draw, `work/road/dis_draw.txt`; clean model `work/road/model.py`, 0 mismatches against the stock code on random rows)
Record `(w0, A, B, F)` = one screen row, bottom row first (row k = screen row 199-k); `A` = right edge x (up to 341), `B` = left edge x (down to -75), `w0 = k << 8` (k = 1..11 in real rows; the edge band is k+1 px wide: pattern `$4ff8` k=1 -> 2 px `c0000000`, k=5 -> 6 px, k=11 -> 12 px).  Each row is exactly 160 bytes.
Let `Aal = A & ~15`, `Bal = B & ~15`, slot = 16-px group (8 bytes: 4 plane words).  Slots from right to left:
`grass` (`(288-Aal)/16` groups, `$17c88-$17cb8`), `window A` (2 slots at `Aal`, `Aal+16`: three 32-bit masks from `$4ff8[(A&15)<<4 | w0]` = (road, band, grass) run through the edge routine `$1058a`), `road` (`Aal - Bal - 32` px, `$17e30-$17e7a`), `window B` (same table, reversed roles), `grass`.
Group writes are clipped to the screen (each window group individually: `cmpi.w #$130` / `tst.w`); edges closer than 32 px take a merging path (`$17d68-$17dde`, never seen: 0 of 19,969 rows).  Colours come from the 24-word table at `$135a`: grass `(a5)+0/+8` by F bit 15, road `+$10/+$18` by F bit 14, edge band `+$20/+$28` by F bit 13
(decoded for the first level: grass 532/541, road 333/444, edge 541/552).  **F bits 15-13 are a 3-bit stripe counter** (flips every 4 / 2 / 1 stripes; the whole pattern shifts one step per 16 world units: `$101ea: subi.w #$2000,d6`); the low byte (2k) is the fog threshold index compared with `$13a0`
(`$18036-$18046`; `$13a0 = 0` and `$135e = 0` in every dump: the far-colour reload never runs).
Per-row output: 20 slots; fills are 16-px aligned (`movem.l d2/d4-d6,-(a0)`, 16 B per instruction, jump tables `$17cba`, `$17e7c`, `$17f90`), only the windows are pixel exact.  `$12f0 = a0` and `$12f4 = d7` at the end feed the horizon strip (`$18326`) and the raster table (`$10a5e`).

### 1.4 Timer B palette split (evidence: `$d486-$d5ec`, `$d616-$d6f8`, dumps `pal`)
The VBL routine loads palette A (`$3cd4`: HUD/sky) into colours 0-15.  Timer B (event count, every 4 lines from the list at `$3d0e`) fires first at line `$12fe` (= `$22` here): `$d6c0-$d6d8` writes colours 1-14 from palette B (`$3cf2`, the game/road palette: `000 222 333 500 630 421 541 131 210 552 444 223 666 532`)
and colour 15 from the 8-entry list `$3cc4` (`256 256 256 256 356 356 357 457`, a sky/ground gradient); every following interrupt (`$d690-$d6a0`) changes ONLY colour 15.  **The per-4-line palette changes do not colour the road stripes**: stripes are pixel values (above), the interrupts cost 12-14 k cycles per frame
(`rendering.md` section 3) for a 8-step gradient of one colour and the one palette switch.

## 2. Invariant test: is a row a function of (row index, stripe phase) + offset?  No.  (`work/road/dump/{grid,start,up,drive}`, 60 consecutive passes each)

| fact | evidence |
|---|---|
| records per frame | 70-92, mean 83.2 (grid 79 constant, start 81-87, up 75-92, drive 86-90) |
| `w0` | always the static table value of the slice; 100 % equal row-for-row between consecutive frames in a flat stretch; 95.9-97.9 % on hills/curves (rows shift when the hill list changes the counts) |
| `A`, `B` | `A - B` = `wL + wR` = profile bytes x factor: 445 distinct `(w0, A-B)` pairs in 240 frames (grid 79, start 176, up 283, drive 160); change between consecutive frames: start 49 % of rows, up 70 %, drive 24 % |
| `F` | `bits 15-13` = stripe counter shared by whole row bands, low byte = 2k: depends on stripe phase and slice only |
| rows identical (all four fields) to the row above in the previous frame | grid 100 %, start 20.0 %, up 11.5 %, drive 62.1 % |
| of the rest | only `F` differs: start 30.5 %, up 14.7 %, drive 11.5 %; an edge moved: 49.4 / 69.7 / 24.3 %; slice mapping moved (hill/clip): 0 / 4.1 / 2.1 % |
| edge movement per row | 1-8 px typical (start: 621 rows 1 px, 441 rows 2 px, 423 rows 3 px, ...) |
| row structure classes (all 19,969 rows) | both windows fully on screen 68.6 %, A in / B off screen 16.6 %, both off 5.4 %, others (clipped windows) 9.4 %; narrow (< 32 px) 0 % |
| window combinations used | all 8 stripe combos; 2,785 of the 2,816 `(orientation, combo, w0, shift)` entries over 240 frames |

Conclusion: invariant per row = `w0` (slice), the stripe counter (phase) and the screen row's slice mapping while the road is flat.  NOT invariant = both edge positions independently (road width varies with the position-dependent profile tables, edges at 1-8 px steps per frame).
A "pre-rendered straight road row + curve offset" is only valid for rows whose width is constant, which holds for none of the moving scenes.  The sound decomposition is per edge (each edge is a translation-invariant shape), and that is what the game's window table and `rd_draw`'s generated 16-byte windows are.

## 3. How other racers solve it  **[general knowledge, not verified here]**
OutRun-style techniques on 16-bit machines: (a) per-scanline perspective tables with colour per line from the stripe phase (a palette/copper-per-line colour per stripe; cheap but needs per-line palette changes: Timer B every line is too expensive here, and this game draws stripes in pixel values);
(b) pre-rendered road rows (one bitmap per stripe colour) scrolled sideways per line, copied by the blitter (Amiga) or `movem` (ST) with the curve as a per-line shift; (c) compiled/unrolled span code per line (ST/STE `movem` fill chains).
This game is **(c) with pre-rendered edge groups**: unrolled `movem` fills for grass/road/grass and a table of pre-shifted 32-px edge patterns (`$4ff8`), recoloured per stripe by `$1058a`.  Its geometry is the classic z-slice table: per-slice perspective factor, accumulated curve, elevation map for hills.

## 4. Blitter for the road (Hatari 2.6.1 blitter model; blob `work/road/blit/bltest.s`, runner `run_bl.py`, 80 rows x 160 B, HOG blits, interrupts masked)

Cycles per 80-row pass (FrameCycles at labels, wrap-fitted, 0 violations); raw: `work/road/logs/blit_8.txt`, `blit_16.txt`:

| case | 8 MHz | 16 MHz (`hatari-option --cpuclock 16`) | per row |
|---|---:|---:|---:|
| empty loop (overhead) | 1,288 | 1,288 | 16 |
| CPU aligned copy (`movem.l`, 160 B/row) | 60,820 | 60,820 | 760 |
| **CPU shifted copy** (variable shift 1-15 px, `lsr.l d5` on [prev:cur], per plane word) | **556,820** | 236,308 | 6,960 / 2,950 |
| blitter aligned copy, one blit/row (4 plane-lines x 20 words) | 59,868 | 59,868 | 748 |
| **blitter shifted copy**, skew per row, FXSR, 21 words | **62,428** | 62,428 | 780 |
| blitter, one blit for all rows (pure data move) | 51,308 | 51,308 | 8.0 cycles/word |

Per-row blit setup = 5 register writes (src long, dst long, ycount word, skew byte, ctrl byte = about 70 cycles + loop) = 107 cycles/row over the single-blit case.  The blitter costs 8 cycles per copied word (4 read + 4 write), the CPU `movem` copy 9.5: parity.  Fills (no source) 4.0-4.4 per word vs `movem` 4.33 (MW2 `blitter.md`, taken as given).
**Fidelity limit:** Hatari's blitter model is the bus-cycle model of `blitter.c` (4 cycles per bus access, HOG = uninterrupted); real STE contention with video DMA and with a CPU in non-HOG mode is not modelled to the cycle; the 16 MHz run shows that Hatari's 68000 model keeps bus-bound work (prefetch, RAM reads and writes: copy loops, `nop/dbra`) at the 8 MHz cycle count and speeds up only internal (non-bus) cycles (the variable shifts),
and the real Mega STE's 16 KB cache is not modelled, so the Mega STE balance (cache hits for reads, writes still 8 MHz) is **[INFERENCE]** not measured here.
**Verdict:** blitter template drawing could at best equal ~62 k + address work (about 66 k) per frame if every row were one shifted copy, versus 95 k for `rd_draw`; but section 2 shows rows are not one template, a split into left/right half rows needs 2 blits per row (+80 x 107 = 8.6 k), thousands of template rows
(112 KB+ of RAM, generated by the stock edge routine anyway), a probe + CPU fallback for plain ST/TT, HOG-mode IKBD starvation handling and exactness work for a saving of at most ~4 % of a frame.  **No blitter patch built.**

## 5. Skipping unchanged road (repaint avoidance), measured on the same dumps
Road bytes of the new frame vs the same buffer two presented frames earlier (stage c, road only): changed bytes grid 0.0 %, start 19.4 %, up 19.5 %, drive 7.8 %; 16-px groups identical 100 / 44.5 / 43.7 / 78.3 %; whole rows identical 100 / 2.8 / 0.3 / 51.6 %.
Record-level (no byte compare) row equality with the previous frame: 100 / 20.0 / 11.5 / 62.1 %.  Against what the buffer really holds at the start of the draw (the final picture of two frames ago, with sprites and HUD painted over the road) no row is identical (0 / 0 / 0 / 4.2 %): the road area contains
the speedometer, bottom HUD items and the sprites' shadows, which the repaint erases (sprite erase side effect), so any skip needs a per-row/per-slot "overpainted" mask maintained by every sprite and HUD routine.
A group-level compare costs as much as writing the group (2 x `cmpm.l` = 40 cycles vs 40 for a 16-byte `movem`).  Driving gain bound **[INFERENCE: arithmetic on the measured fractions]** (changed groups only, no compare cost): ~55 % of the 34 k fill cycles = 19 k, minus the masks: **not worth it** (< 2.5 % of a frame with high risk); standing frames: every row is identical, but the stock draw can only
be skipped with the overpaint mask (grid has cars and signs on the road).

## 6. What was built

### 6.1 `rd_geom` (`patches/rd_geom.s`, site `$100b4`, blob `$B4000`, tables `$D0000-$DAFFF`)
Whole routine replaced; the stock code runs from `$100bc` when `$1316 > 178`.  Loop 1 unrolled x4 with a doubled T1; loop 2 with a map base pointer that advances 256 per slice (no `or`, no `+$80`, `$e8` in a register); loop 3 as passes A (centre table, 112 slices, 48 cycles each),
B (80 slices: lookups + product table `PT[m][b]`, 140 cycles each), C (stripe machine and `movem.w` emission as stock, 80 slices).  Static helper tables (CBASE = `$a0 - hw`, T2 = 2*T1) derived once behind the magic `RDG1`; `PT` rebuilt when `$1316` changes (0.82 M cycles).
**Standing reuse**: when `$130c == 0` and the 33 state words (`$1308 $130a $130c $1316 $1318 $13ae $1bba $1bb8 $23c6 $102c`, ring state `$13a2-$13ac $23bc $23be $27c8`, pointers `$1bb0 $1bb4 $23c0 $27da $27ca $27ce $27d2`) equal those of the call that saved the result,
the 2,132-byte output region `$4724-$4f77` plus `$23c4 $131c $1320` is copied back (12 k cycles instead of 87 k).  Sound because the three table writers do nothing at speed 0 (1.2) and the generator state is part of the key; the stock memory result is reproduced byte for byte.
Equality: `work/road/geom_test.py` (240 real frames, whole RAM `$0-$B26FF` equal after the call, site bytes masked), `geom_fuzz.py` (2,100 states: random `$1bba $23c6 $13ae $130a $130c $1308 $1318 $1316`, random or smooth profile/elevation/curve tables; negative control = corrupted product table: 10 of 60 DIFFER),
`geom_reuse_test.py` (standing frames: full+save and reuse both equal stock), `geom_sigtest.py` (each of the 33 key words flipped between the saving call and the next: 66 cases, all equal to stock, reuse path never taken wrongly).
Cycles (Musashi, one frame): moving 87.4 k -> 56.9 k (-30.5 k, -35 %), standing 87.4 k -> 12.1 k; first call 0.89-0.90 M (tables).  Breakdown after: loop 1 9.0 k, loop 2 16.8 k, pass A 5.6 k, pass B 11.2 k, pass C ~13 k.

### 6.2 `rd_draw` (`patches/rd_draw.s`, site `$17c42`, blob `$B5000`, tables `$DB000-$E7FFF`)
Row logic rewritten.  Window tables `WA/WB[k][combo][shift]` (16 bytes: both groups, 4 planes) are generated once per colour table (`$135a`) by calling the stock `$1058a` on the `$4ff8` masks (3,072 calls, 2.04 M cycles in Musashi on the first draw) into 2 x 24 KB, plus a 48-byte colour copy.
A row costs: parse (`movem.w`), 3 colour loads, 2 window loads (`movem.l (a5,d1.w),a2-a4/a6`), fills by `jmp t(pc,4n)` into 3 x 2 unrolled chains (`movem.l a2-a4/a6,-(a0)` = 2 groups), a clip-free path (68.6 % of rows: both windows on screen) and a generic path for clipped windows.
Rows with edges closer than 32 px (or crossed), or `w0 > $b00`, hand the REST of the frame to the stock loop at `$17c66` (state rebuilt from the record); the whole frame runs stock when `$13a0 != 0`.  `$12f0/$12f4` are written as stock.
Equality: `draw_test.py` (240 frames, whole RAM `$0-$B26FF` incl. both screen buffers and `$12f0/$12f4` equal), `draw_fuzz.py` (900 random streams of 1-112 records over all 15 colour tables: A, B around every clip threshold, `w0` 0-$f00 and garbage, random F; negative control = corrupted window table: 22 of 60 DIFFER).
Cycles (Musashi, same frames): stock 173.1 / 160.0 / 159.5 / 182.0 k, stock + `mr_edge` 143.3 / 134.4 / 133.3 / 150.4 k, `rd_draw` **94.9 / 91.3 / 87.8 / 102.5 k** (start 20 / up 20 / grid 5 / drive 10).  Profile of `rd_draw` (start 20): fills and window stores 34.2 k (the `movem` floor), window loads 7.4 k, colour loads 6.5 k, row control 46.8 k.

### 6.3 Gates (all raw logs in `work/road/logs/`)
```
msrabtest --only rd_geom rd_draw  (race_grid/start/up/drive, flips 10 and 40, --state 120)         -> RESULT: ALL IDENTICAL   (md5 as stock: 81dfec87 d5a188cf, 3da506a7 c54efba9, 64f19a1d d9cdbe0a, d67d147e ed8944f1 at flip 10)
msrabtest --only rd_geom rd_draw mr_negctl --snapshots race_start --flips 10                        -> DIFFER (1334 bytes of 64000)  RESULT: DIFFERENCES FOUND
rd_geom alone (v1 and final): ALL IDENTICAL (same snapshots, logs/gate_rd_geom.txt);  rd_draw alone: ALL IDENTICAL (logs/gate_rd_draw.txt)
cold boot, build = pp_bigram_cache mr_edge mr_map mr_digit mt_clock mt_sync mt_pre rd_geom rd_draw, STE 1 MB: marker MSPO, race alive 3,600 VBL, RDG1 magic at $d0000, WPTR $e7040 = $000102ba, PM = 10
```
Cycles per pass (`work/road/run_work.sh`, `work_live.py`, raw `logs/work_*.txt`): see the table in section 0.

## 7. Caveats, unproven, what the user must decide
1. **Stalls**: the first road frame after the patches apply (race start) runs the generators: geometry 0.9 M cycles (product table) and draw 2.0 M cycles (window tables from the stock edge routine) = about 18 VBL once; again if the level's colour table pointer (`$135a`) or `$1316` changes.  With the shipped pacer it is one late pass that the MAXLAG resync absorbs **[INFERENCE: not measured with `mt_*` on]**.
2. `rd_geom`/`rd_draw` need free RAM `$D0000-$E7FFF` (96 KB); not declared with `; data:` (the tool would stretch the payload image past `IMG_MAX_LEN`); lazily initialised behind the magic/pointer so a non-zero RAM does not matter; at 4 MB they need `pp_bigram_cache` (default yes) so the area is not the MS1 whole-image cache (cold boot at 4 MB with the same build: marker MSPO, race alive 1,500 VBL, RDG1 magic and WPTR `$102ba` present, `logs/drive_rd4m.txt`).
3. Static-table assumption (rd_draw: `$4ff8` pattern table, colour table content, `$4644` max <= `$b00` for the 80 emitting slices; rd_geom: `$4564`, `$4644`): generated from constants by the level init (`$16404-$164ea`); identical in all dumps/frames (4 scenes of the first level, same level only: **other levels not captured**).  The colour table pointer is the cache key; content changes in place would be missed (as in `mr_edge`).
4. Standing reuse is exact only if no other code writes `$13b0-$27c7` or the outputs between frames; the only writers found (`xref`) are `$fde0-$ffe4` (level init) and the three speed-guarded updaters.
5. `rd_draw`'s fallback to the stock loop and the `$13a0 != 0` path are exercised only by the fuzz (never in real frames); `rd_draw` bypasses `mr_edge` while it runs (`mr_edge` stays correct for the fallback).
6. Not tested: Mega STE, TT/Falcon (plain 68000 code; the generators call stock code only), 60 Hz, floppy build (`build --floppy` not run; the patches have no media tag), long races (3,600 VBL only).
7. Hatari only; Musashi cycle counts have no wait-state model.

## 8. Recommendation
Ship `rd_geom` + `rd_draw` after the user's go-ahead (pixel-identical, gated): -67 k cycles per driving pass (-8.9 % on top of `mr_edge/mr_map/mr_digit`), -123 k standing; the driving pass becomes 4.285 VBL (was 4.704), giving the T=30 pacer 0.7 VBL of headroom instead of 0.3.
The next lever, if more is wanted: the span-draw row control (46.8 k) and geometry loop 2 (16.8 k) are the largest remaining road costs; both are plain 68000 work with no structural shortcut found (rows are not templates, per-frame tables change).  Blitter and repaint skipping are rejected with numbers (sections 4, 5).

## 9. Files
`work/road/`: `dump_frames.py` (chain of one-shot breakpoints: inputs at `$100b4`, records at `$17c42`, screens at `$7b10` and at the flip), `rdlib.py` (loader, Musashi harness, profile/trace), `musashi/` (C driver `drv.c`, `libm68k.so`), `model.py` (clean row model),
`geom_test.py geom_fuzz.py geom_reuse_test.py geom_sigtest.py draw_test.py draw_fuzz.py`, `run_work.sh`, `drive_rd.py drive_rd4m.py`, `blit/` (`bltest.s`, `run_bl.py`), `dis_geom.txt dis_draw.txt`, `dump/` (240 frames x stages), `live_*.img/json`, `rd_geom_v1.s rd_geom_v2.s rd_draw_v1.s` (earlier versions), `logs/`, `work/` (cycle JSONs).
`patches/rd_geom.s`, `patches/rd_draw.s`.

## 10. Integration wave (MSRIntegrate): load-time generation, defaults
`rd_geom`/`rd_draw` are `default: yes` now, plus `rd_init` (site `$78f6`, `jsr $fde0.l` of the race setup) which runs the two generators (`$B4000`, `$B5000` pre-warm entries) before the race loop; evidence, the second-track check and the `$1316`/`$135a` watch are in `integration.md`. Section 7 items 1 (stall) and 2 (RAM, now declared with `; ram:`) are superseded by it.
