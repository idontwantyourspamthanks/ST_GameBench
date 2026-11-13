# Hunter P4 raster speed-ups (`patches/p4_*.s`, blob range $8C000-$8DBFF) and the A/B gate `tools/huntab.py`

All numbers: 1 MB STE, TOS 1.62, Hatari 2.6.1 (fast-forward, cycle-exact), restored snapshots `work/snapshots/*.sav`, every patch `default: no`.
Evidence: disassembly of `work/dumps/ram_foot_stand.bin` (`tools/m68dis.py`), Hatari profiles (`Hunter.profile_cc`), raw tool output quoted below.
Unproven statements are marked [INFERENCE].

## 0. Summary

| patch | site(s) | what | cycles/frame (work) | verdict |
|---|---|---|---|---|
| `p4_ikbd` | `$c5fa` | joystick poll in the VBL handler without the 200-iteration delay (item c) | -1.9 % in every scene | keep |
| `p4_poly` | `$7554` | polygon scan converter re-implemented; exact early rejection of polygons left/right of the screen; block edge walk; table masks (item d) | -3.7 % (stand) ... -11.8 % (walk) | keep (the big one) |
| `p4_edge` | `$7450` | edge set-up without `divs` for dx = 0 and dy = 1,2,4,8,16,32 (item d) | -0.7 % .. +0.2 % | marginal; exact (exhaustive) |
| `p4_col` | `$7518` | skip the `$7a24` colour set-up when the colour repeats (item b) | **+0.1 % (slower)** | rejected, file deleted |
| item a | - | merge `$c91a` with `$c84a`: the premise is wrong (section 3) | - | nothing to merge |
| item e | - | span fills `$7af0..`: no cheap exact trim (section 7) | - | none |
| item f | - | vertex transform reuse: not cheap (section 8) | - | none |
Combined `p4_ikbd + p4_edge + p4_poly`: -6.5 % (hills) ... -13.7 % (walk); fps 4.55 -> 4.70 (stand), 4.74 -> 5.55 (walk), 6.25 -> 7.14 (car turn); every comparison IDENTICAL (section 9).

## 1. The gate: `tools/huntab.py`, `tools/polydiff.py`

`mw1ab.py` compares "N flips after a fixed VBL". That is not valid for Hunter: the world runs on the VBL counter, the movement/NPC code multiplies by the
number of VBLs the previous frame lasted (`$1ac(a5)`, baseline.md section 2). A patch that makes one frame shorter by a VBL changes every later frame's
simulation, not only its pixels. So the gate is built on these facts:

* **flips = 1 (hard gate).** Both runs restore the snapshot; at the first flip `$5fee` after an absolute start VBL the patched run applies the live patch set
  (`huntpatch.py live` image + `w` lines), both runs save the visible 32000 bytes of BOTH screen buffers (`$23000`, `$2AD00`) at the next flip. The inputs of that
  frame (the logic that ran after the flip) were produced by unpatched code in both runs, so the frames are directly comparable. 3 start points (37 VBL apart) per snapshot.
* **flips = N > 1:** also compared, but only a hard gate while the VBL length of every frame so far is equal in both runs; otherwise `DIVERGED-TIME`
  (legitimate divergence) is printed, not counted.
* **`--lock`:** both runs get `$9ad = $0e` (min frame time `$1a7(a5)` = 15 VBL), so frames last 15 VBLs in both runs and the simulation stays frame-for-frame identical
  (observed: `frames=[.., 15, 15, 15, ...]`). Then every `--flips N` is a hard comparison. `--views K` teleports the player (`$ab2` X, `$ab6` Z, `$ae6` heading) to K pseudo-random views
  at the apply flip in both runs (verified: the K views give K different pictures). Result for the combined set: `--views 5 --lock --flips 1 2 3 4 5` on all 7 snapshots: ALL IDENTICAL.
* **Cycles.** `work` = cycles from the VBL lock's return (`$5fa4`) to the next flip entry (`$5fd2`): logic + render + the interrupts inside it, WITHOUT the idle spin to the
  next VBL. Plain flip-to-flip time is quantised to whole VBLs (160256 cycles) and hides everything smaller. `work(first patched frame)` is the exact saving (same inputs in both runs);
  `VBL/frame` and `fps` come from a 600-VBL window after the capture (frames per window; scenes drift a little there). Machine time = VBL*160256 + FrameCycles.
  Base cycles (null patch, work of the first frame / VBL per frame / fps): stand 1,715,099 / 11.00 / 4.55; walk 1,556,173 / 10.55 / 4.74; car_stand 1,367,769 / 9.00 / 5.56; car_drive 1,052,275 / 7.00 / 7.14;
  car_turn 1,177,296 / 8.00 / 6.25; hills 1,028,464 / 7.32 / 6.83; 4 MB stand 1,646,916 / 11.01 / 4.54 (walk/drive/turn rows are the *stationary* views at those places: a restored snapshot has the stick released).
  Run-to-run jitter of a base number: up to ~12 cycles (host mouse events); base and patched run concurrently and match to the cycle in the self-test (`huntab.py` without `--only`: +0 everywhere).
* Hatari runs in `--fast-forward on` (~35x); base captures are cached in `/tmp/hunab/`. Needs `huntpatch.py live` (HunterLoader).
* **`tools/polydiff.py` + `patches/test_polydiff.s` (not a game patch).** A differential oracle for `p4_poly`: on a 4 MB snapshot the wrapper hooks `$7554`, runs the NEW code, saves the 3D window, restores the
  pre-state, runs the ORIGINAL code (re-entered at `$755a`) on the same input and compares the 22400-byte window plus `$1600` and `$1618`. Every polygon of every frame is a test case; views are teleports.
  Negative control: a deliberate off-by-one clamp (`#318` instead of `#319`) was caught: `polygons tested 222  window mismatches 9`.
  Result for `p4_poly`: 8 runs x 10 views x 3 flips = **16,773 polygons, 0 window mismatches, 0 variable mismatches** (counters at `$8dfe0`, run `polydiff.py --views 10 --view-base N`, N = 100..170;
  more than ~15 breakpoints crash Hatari, hence several runs).

## 2. Item (c): `p4_ikbd` - IKBD poll delay

`$c5f0` (VBL, vector `$70`) does `moveq #$16,d0 / bsr.w $afbe` every VBL. `$afbe` stores the byte at `$1d4(a5)`, falls into `$afc4`: wait for ACIA TDRE (`btst #1,$fffc00`), then
`move.w #$c8,d0 / nop / dbra` (200 x 14 = 2800 cycles = 350 us at 8 MHz, 2.4 % of ALL cycles, measured: `$afc4` 3,855 cycles/call, 8.5-11 calls/frame), then `move.b (a0)+,$fffc02`.
The patch replaces `moveq #$16,d0 / bsr.w $afbe` (6 bytes at `$c5fa`) by `jsr $8c000.l`; the blob does the same store, the same TDRE wait, the same write, no delay. The multi-byte command
senders (`$af72` init, `$afaa`) keep the original `$afc4`.
Gate: IDENTICAL on all 7 snapshots, -1.85 .. -2.06 % per frame (about -32k cycles at 11 VBL/frame, -3k per VBL).

Safety argument (the delay sits AFTER the TDRE wait):
1. **Wire timing.** The MC6850 transmitter is double buffered: TDRE returns to 1 as soon as the byte has moved to the shift register. For the poll, the previous byte was written one VBL (20 ms) ago, so TDRE is already 1 and the
   delay delays nothing on the wire except the moment of the write; the wire time is 1.28 ms per byte regardless. For back-to-back bytes (the multi-byte senders, which we leave alone) the write to TDR already waits for the shifter.
2. **IKBD input handling.** Only the single byte `$16` is sent here, one per 20 ms; reset (`$80 $01`, needs up to 300 ms, atari-wiki "Keyboard Protocol") is not involved. The protocol text has no minimum inter-command gap for ordinary commands
   (atari-wiki.co.uk "Keyboard Protocol", read in this session). Hatari's `ikbd.c` header comment (2013/01/02) states that the real IKBD accepts new bytes asynchronously while processing another command and drops one only if its input
   buffer is full [secondary source; the HD6301 ROM was not disassembled here]. TOS 1.62's own `Bconout(4)` (`$e03634`: TDRE wait, then a 950-iteration `bsr/rts` delay, ~5 ms) is more conservative than the game but is a library routine for arbitrary bytes, not a poll.
3. **Existing evidence that the delay is not needed:** the game runs unchanged at `--cpuclock 16` (delay = 175 us; baseline.md walks at 16 MHz) and the delay is CPU-clock dependent on TT/Falcon (87 us / 175 us) - so the original already tolerates a 2-4x shorter delay.
4. **Residual risk [INFERENCE]:** on real hardware with a slow/old IKBD (6301 ROM) a write directly after TDRE could in principle coincide with the IKBD still transmitting the previous reply; the IKBD's receive side is interrupt driven and independent of its transmit side. Not testable in Hatari (high level IKBD).
Input check (Hatari, `snapshot 1mb_foot_walk`, base vs `p4_ikbd` applied live, key `Up` held 3 s, relative mouse moves): joystick decode `$d1(a5)`/`$d0(a5)` = `02`/`02` in all 6 samples of both runs;
mouse accumulators `$d8(a5)`/`$da(a5)` (`$8de`/`$8e0`): (155,51) -> (180,51) -> (180,39) in both runs; forward walk 888 vs 884 units (timing).

## 3. Item (a): the template copy and the dither fill

The premise of the task text is wrong; what the code does [disasm]:
* `$c84a` (called at `$2576` every frame and at `$4962`) fills the **3D window**, bottom up from `draw_buffer + $1a2(a5)` ($5780 = 140 rows): `d4 = $8b - $1544(a5)` rows of the `$aaaaaaaa/$55555555` dither (ground/water), then `$c8a8..` a solid `$ffffffff` fill (sky,
  `moveq #-1,d0 / bra $c8d0`) for `$1544(a5)` rows. So `$c84a` already draws every row of the window exactly once; its cost is 39.5k + ~14k cycles/frame.
* `$c91a` is NOT a background template. It is the HUD copy: `$96f6` ends with `pea $c8fe / bra $c46c`; `$c8fe` = `a1 = $144(a5) + $5780` (the 60 HUD rows below the window, `moveq #$3b,d7`), `a0 = $14c(a5)` (= $3682c, the HUD master that `$a034/$a00e/$a15e/$c46c..` draw into), then `$c91a`: 5 x `movem.l (a0)+,d0-d5/a2-a3 / movem.l .., (a1) / adda.w d6,a1` per 160-byte row.
  The other callers (`$9a3a`, `$9a4c`) are the menu screens. 47.6k cycles/frame (9600 bytes at 4.95 cycles/byte).
* The two ranges are disjoint (rows 0-139 vs 140-199), so there is nothing to merge and nothing the dither fill rewrites. `$c8c0` (screen clear to `$ffffffff`) is called once from `$2518` (mode init), not per frame; the profile bucket `$c8c0` is the sky half of `$c84a`.
* What could still be done, and why not: (i) skip the HUD copy when the master is unchanged: the master is written by at least `$a034 $a00e $a15e $a09e $a11a $c46c/$c4cc ...` (digits are redrawn every frame), no single dirty flag exists; a checksum costs as much as the copy [not implemented]. (ii) wider `movem` (10 registers = 40 bytes = 4.7 vs 4.875 cycles/byte)
  saves 3.6 % of 47k = 1.7k cycles/frame. (iii) the dither/sky stores are `movem.l` to a predecrement address at 2.5 (dither) / 2.25 (sky) cycles/byte; a 10-register store is 2.2: ~5k cycles/frame at best. None is worth a patch (0.1-0.35 %).

## 4. Item (d): `p4_poly` - polygon body (`$7554`, 6 bytes -> `jmp $8c400.l`)

What the original does, from `$7554` (after the colour set-up `bsr $7a24` and the vertex count decode; `$7504` jumps here too) [disasm `$7518-$76f8`]:
A. vertex loop `$7574` (205 cycles/edge): appends the edge offsets to a doubled ring list at `$74b8`, finds the top edge (min y0, ties: x0, then slope low word), the max bottom y.
B. rejection tests (`cmp.w #$8c`, ...), rows count, top edge check `cmp.l 2(a4,d4.w),d2`, `sf.b $1618(a5)` (`st.b $1618(a5)` on every rejection).
C. edge walk `$761c-$768c`: per row `subq.w #1,d4 / bgt`, `subq.w #1,d5 / bgt`, left/right edge loads (x0<<5, `+half slope` for a left edge with negative slope / a right edge with non-negative slope; a right edge with dy = 0 takes the next edge), `addq.w #1,d2 / bmi` (rows above the screen),
   order/clamp (`cmp.l d0,d1 / exg`, `asr.l #5`, clamp to 0..319, empty = -1), store (xl,xr) at `$76fa`, `add.l a0,d6 / add.l d3,d7`, `subq.w #1,(a7)`: ~205 cycles/row.
D. span loop `$76b2`: per row: masks by 5 shifts (189 cycles), `bsr.w $7af0` (self-modified displacement `$76ee`).
Profile (foot_walk): vertex loop 4.9 %, edge walk 18.3 %, span loop 12.3 % of all cycles; `$7518` 38.6 %.

`p4_poly` (everything is reproduced exactly; unusual input re-enters the original code at `$755a` with the original state: n < 3, any edge with dy < 0, no top edge):
* **A:** registers instead of the stack counter; the ring is a list of 16-bit record addresses in my own buffer (`$8d010`), no longer the byte offsets at `$74b8`.
* **B:** the same tests in the same order; the final `$1618` value is identical on every path (`st` on rejection and when the polygon lies completely above the screen - the original only finds that out after the edge walk - `sf` otherwise).
* **C, early rejection (the big win).** In 18 % of the polygons (foot_walk, 5203 polygons traced: 956 draw nothing) every emitted row is empty, 86 % of the empty rows belong to such polygons (39,420 of 100,717 rows = 39 % of all scanned rows; stand: 994 of 7676 polygons, 22 % of the rows).
  They are polygons entirely to the right of x = 319 (rows with xl > 319) or entirely to the left of x = 0 (xr < 0). Exact test, done on the records the scan uses (not on the geometry): the x of every row of an edge lies in
  `[A + min(0,S), A + max(0,S)]` with `A = x0*32`, `S = slope * max(dy,1)` (rows k = 0..dy-1, left edge: + half slope, half = slope>>1 lies between 0 and slope; flat edges have one row). Right reject: for every list edge `x0 >= 320`, `A + min(0,S) >= 10240` and `A + max(0,S) <= $fffff` (so the `cmp.w #$13f`/`cmp.w d0,d1` word compares of the
  original see 15-bit floors and the clamped xr = 319 < xl). Left reject: `x0 < 0` and `A + max(0,S) < 0` for every edge (xr = floor(max/32) < 0, the original's `bmi`). `x0 > 8191` disables the right test (conservative). Decision by the first ring edge's x0, so on-screen polygons pay ~50 cycles.
  `S` uses `muls.w` (slope fits a word for dy >= 2: it comes from `ext.l` after the division; dy <= 1 uses the long slope directly).
* **D:** the left/right run lengths are `max(dy,1)` (a left edge with dy = 0 covers one row in the original: `subq / bgt` falls through on the next row); each block = `min(left run, right run, rows left)` rows. Rows above the screen (`top < 0`) are a separate block loop that only advances the accumulators.
  The row loop is the original arithmetic: 146 cycles/row (was 205) + ~100 per block (an edge segment). Span buffer at `$8d100`.
* **E:** left/right masks from two 16-entry tables (`$8ce00`), `not.l` for the complements, the fill routine is the one the original `bsr.w` at `$76ee` would call (`$76ee + word`), so the self-modified dispatch and the 16 fill routines are unchanged. Row loop ~184 cycles (was 189 + 54 for empty rows; empty rows are 3 cycles of table work now).
Data `$8d000-$8d35f` (zero-init not required), blob `$8c400-$8cdff`, tables `$8ce00`.
Gate (all IDENTICAL): foot_stand -3.69 %, foot_walk -11.78 %, car_stand -3.90 %, car_drive -4.58 %, car_turn -10.79 %, hills -4.06 %, 4 MB -4.54 % (table 9). polydiff: 16,773 polygons, 0 mismatches.

## 5. Item (d): `p4_edge` - edge set-up (`$7450`, 6 bytes -> `jmp $8c100.l`)

Per edge (`$746e-$74b2`, 398 cycles avg, `divs.w d3,d2` = 148 of them): same records (`x0.l, y0.w, dy.w, slope.l, slope>>1`), same preserved registers (a1, a3, a4, a5, a6; the original clobbers a0, a2, d0-d7), `$1604(a5)` = n*16 as before.
Slope: `dx = x1-x0` and `dy = y1-y0` as 16-bit words (`sub.w`), `n = ext(dx)<<5`; original: `dy = 0` -> slope = n (no divide, no `ext.l`); else `divs.w dy,n` then `ext.l`. The patch: `dy = 0` -> n; `dx = 0` -> 0; `dy in {1,2,4,8,16,32}` -> `asl.w #(5-log2 dy)` of dx (exact: n is a multiple of 32);
overflow of the quotient (V of `asl.w`) reproduces the divs overflow result (dividend unchanged, then `ext.l` keeps its low word = `sext16(dx<<5)`); everything else runs the real `divs.w`.
**Exhaustive proof** (`/tmp/hp4/slope_sim.py`, numpy model of `divs` incl. overflow): all 65,536 dx x 2,123 dy values (dy in -64..2048 plus 4095, 4096, 8191, 16383, 32766, 32767, -32768, -32767, -1000, -4096, -32000) = 139,198,464 pairs, original vs patched slope: **0 mismatches**; and `trunc(dx*32/2^k) == dx<<(5-k)` for all dx and k <= 5.
Measured distribution (divs at `$749e`, 4 snapshots, 26-32k divides each): dx = 0: 8-19 %, dy a power of two <= 32: 30-41 %, other dy: 41-54 % (+ real overflow cases: 73 in foot_walk, 39 in hills: |dx|*32/dy >= 32768 does happen).
Result: -0.74 % (stand), -0.23 % (walk), +0.18 % (car_turn): the general-dy edges (41-54 %) pay ~40 cycles more for the extra tests than the original, the rest saves 100-190. **Marginal; exact; the lead can drop it.**
A reciprocal-multiply replacement for the general case was analysed (q = (n*M[dy])>>s with M, s per dy, exact for |dx| <= 1023 by exhaustive check, sign fix-up for truncation) but costs ~110-120 cycles against divs 148+4 and needs a table: -4k cycles/frame, not implemented.

## 6. Item (b): `p4_col` (tried and rejected)

`$7a24` (two `move.w d(pc,d0.w),abs.l`) costs ~90 cycles including the `bsr`. A guard that compares the table entry with the word really in `$76ee` and skips the two stores when equal was written and gated: IDENTICAL, but **+0.05 .. +0.16 % slower** (stand +2099 cycles/frame):
consecutive polygons rarely share a colour, and the compare costs 38 cycles on the path that has to write anyway. Deleted. (Within `p4_poly` the colour is not needed: the dispatch word `$76ee` is read directly.)

## 7. Item (e): span fills

Profile (poly patch applied, `work/prof` style): fill routines `$7a7c-$7d07` = 204k cycles/frame (walk), 185k (stand); 835-843 fill calls/frame, 552 / 445 of them multi-group; the middle loops (`dbra d5` bodies) are 99k / 82k cycles (49 % / 44 %) over 2095 / 1778 iterations/frame = 47 cycles per group
(`move.l d0,(a0)+ / clr.l (a0)+ / dbra` = 12+20+10 ...). The mean number of middle groups per multi-group span is only 3.8 / 4.0. Alternatives and why none pays: a zero register instead of `clr` saves 4-8 per group but the routines have no free 2 bytes for `moveq #0,dX`;
a blob per routine (`jmp` in and out = +24 cycles per call, 16 sites) loses at mean M = 3.8; unrolling x4 or `movem.l` backwards (2.25 cycles/byte, needs 8 pattern registers = ~140 cycles of save/restore/setup) wins only for M >= ~8. Estimated net at most 15-20k cycles/frame (1.2 %) for 16 generated routines: not done.
Span mask prep: 36 % of the active spans repeat the (xl, xr) of the row above (counted with a temporary instrumented copy: foot_walk 308,551 of 849,988, foot_stand 299,089 of 836,165, car_drive 46,069 of 664,090); keeping the masks costs ~116 cycles in memory loads vs 130 to recompute: no gain.

## 8. Item (f): vertex transform reuse

`$5452` (rotation by up to three `muls`-pair stages, flags `$7c/$7e/$80(a4)`, matrix `$15a4(a5)`) is 6.3 % (stand) of the cycles, 131 calls/frame x 849 cycles. Trace of 10,480 calls (foot_stand, ~80 frames): 1,835 distinct (matrix words, d0, d1, d2) = hit-rate upper bound 82 % - but nearly all of it is the *static camera* (identical inputs frame after frame); while moving the matrix changes every frame
and only instances of the same model share it. A cache needs a keyed table (24 matrix bytes + 3 inputs, ~100 cycles per lookup) and invalidation, and the gain is zero when walking. Not cheap -> not done.

## 9. Results (huntab, 3 start points per snapshot, all IDENTICAL)

`work` = first patched frame, cycles; VBL/frame and fps from the 600-VBL window.

| scenario | base work / VBL / fps | p4_ikbd | p4_poly | p4_edge | p4_col (rejected) | combined ikbd+edge+poly |
|---|---|---|---|---|---|---|
| foot_stand | 1,715,099 / 11.00 / 4.55 | -32,452 (-1.89 %) / 4.55 | -63,323 (-3.69 %) / 4.55 | -12,645 (-0.74 %) / 4.55 | +2,099 | **-113,079 (-6.59 %) / 10.64 VBL / 4.70** |
| foot_walk | 1,556,173 / 10.55 / 4.74 | -29,212 (-1.88 %) / 5.00 | -183,373 (-11.78 %) / 5.52 (9.06 VBL) | -3,559 (-0.23 %) / 4.77 | +1,783 | **-212,856 (-13.68 %) / 9.00 VBL / 5.55** |
| car_stand | 1,367,769 / 9.00 / 5.56 | -25,959 (-1.90 %) / 5.56 | -53,339 (-3.90 %) / 5.56 | -4,536 (-0.33 %) / 5.56 | +1,172 | **-90,528 (-6.62 %) / 8.68 VBL / 5.76** |
| car_drive | 1,052,275 / 7.00 / 7.14 | -19,451 (-1.85 %) / 7.14 | -48,169 (-4.58 %) / 7.14 | -2,827 (-0.27 %) / 7.14 | +609 | **-71,959 (-6.84 %) / 6.88 VBL / 7.27** |
| car_turn | 1,177,296 / 8.00 / 6.25 | -23,879 (-2.03 %) / 6.25 | -126,987 (-10.79 %) / 7.14 (7.00 VBL) | +2,064 (+0.18 %) / 6.25 | +599 | **-144,423 (-12.27 %) / 7.00 VBL / 7.14** |
| hills_stand | 1,028,464 / 7.32 / 6.83 | -19,713 (-1.92 %) / 7.03 | -41,707 (-4.06 %) / 7.14 (7.01 VBL) | -2,497 (-0.24 %) / 6.83 | +969 | **-67,071 (-6.52 %) / 7.09 VBL / 7.05** |
| 4mb_foot_stand | 1,646,916 / 11.01 / 4.54 | -33,919 (-2.06 %) / 4.54 | -74,788 (-4.54 %) / 4.61 | -12,455 (-0.76 %) / 4.54 | +2,611 | **-115,773 (-7.03 %) / 10.01 VBL / 5.00** |
fps is 50 / (VBL per frame in the window); "4.55 -> 4.55" means the saving did not cross a VBL boundary yet (stand needs ~-4 % more to be solidly at 10 VBL: the combined set is at 10.64 VBL = 36 % of the frames already take 10).
Hard gates passed: flips = 1 for all rows (21 captures per set), `--lock --views 5 --flips 1..5` for all 7 snapshots, polydiff 16,773 polygons.

## 10. Cold boot (HunterLoader's `huntpatch.py build/boot`, combined set `p4_ikbd p4_edge p4_poly`)

Build: `python3 tools/huntpatch.py build --only p4_ikbd p4_edge p4_poly --out build/game_p4` (payload 6496 B `$8ba00..$8d35f`, site table 64 of 1008 bytes: `$7450 -> $8c100`, `$c5fa -> $8c000`, `$7554 -> $8c400`), then `huntpatch.py boot --game build/game_p4 --machine .. --tos .. --mem ..`
(raw output; `in_game=True` = HUD matched + `$899` bit 7 + flips; `MARKER` `HNPO` = all sites applied; `peek` shows the three sites and the first blob word in RAM after the boot):
```
BOOT OK machine=ste     tos=1.62 mem=1024K  in_game=True MARKER=b'HNPO' FLAGS=00000003 fps={'flips': 25, 'fps': 5.0, 'vbls_per_frame': 10.0}   peek $7450: 4ef90008c100  $c5fa: 4eb90008c000  $8c400: 33c00008d000
BOOT OK machine=ste     tos=1.62 mem=4096K  in_game=True MARKER=b'HNPO' FLAGS=00000003 fps={'flips': 25, 'fps': 5.0, 'vbls_per_frame': 10.0}
BOOT OK machine=megaste tos=2.06 mem=1024K  in_game=True MARKER=b'HNPO' FLAGS=00000003 fps={'flips': 42, 'fps': 8.4, 'vbls_per_frame': 5.95}
BOOT OK machine=st      tos=1.04 mem=1024K  in_game=True MARKER=b'HNPO' FLAGS=00000006 fps={'flips': 26, 'fps': 5.2, 'vbls_per_frame': 9.62}     (blind boot, plain ST: bus error seen, no DMA sound)
```
Unpatched reference (baseline.md): 1 MB STE stand 4.50 fps, 4 MB 4.75 fps; the cold-booted patched game stands at the HQ at 5.00 fps (10.0 VBL/frame) at both sizes, i.e. the "stand" view reaches 10 VBL/frame in the real boot.
TT (`--machine tt --tos 3.06 --mem 4096`) fails with `RuntimeError('no screenshot (Hatari busy, e.g. a dialog, or dead)')` and Falcon (`--machine falcon --tos 4.04`) with `screen 'hw' not reached` - the same TT failure occurs with an EMPTY build (`huntpatch.py build --out build/game_empty`), and the Falcon failure is at the very first
screen (the HW-detect text, before START's tail runs the stub), so both are limits of the STE-crop navigation in `Hunter.boot_to_game`, not of the patches. TT/Falcon in-game behaviour is therefore untested [not verified]; the patches only touch game code and the ACIA at `$fffc00` that every ST-family machine has.
Joystick/mouse with the combined set applied live (foot_walk, `Up` held, relative mouse): joystick `$d1/$d0` = `02/02` x6, mouse `$d8/$da` (155,51) -> (180,51) -> (180,39): identical to the unpatched run.

## 11. Open points

* `p4_poly` reads the fill dispatch word `$76ee`, so it requires the original `$7a24` (untouched). It does not depend on `p4_edge`/`p4_ikbd`; the three are independent patches (3 sites, 64 bytes of the site table).
* Free RAM used: `$8c000-$8c014` (ikbd), `$8c100-$8c1xx` (edge), `$8c400-$8cdff` (poly) + `$8ce00-$8ce7f` (tables), data `$8d000-$8d35f`. Within `$8c000-$8dbff` (test_* patches live from `$8dc00`).
* 68030 machines (TT/Falcon): the blobs are plain code, no self-modification of my own; the original `$7a24` self-modification is unchanged and is the loader's/PP's cache business.

## 12. Addendum: why the HUD copy cannot be skipped
`$14c(a5)` (the HUD master) is dereferenced in only 8 places of the code (`$6a54 $a062 $a0ac $a11a $a160 $a1ca $a5f6 $c902`, scan of `206d/226d/.. 014c` operands over `$800-$12000`), so a dirty flag on the master looks feasible. It is not pixel-identical: the copy `$c8fe -> $c91a` also ERASES whatever else was drawn into
the HUD rows of the draw buffer since the last copy (the software mouse pointer sits in the HUD message area, boot.md section 2, and is drawn into the draw buffer, not the master) [INFERENCE for the exact writers; the pointer location is observed]. Skipping the copy would leave those marks in the buffer.
