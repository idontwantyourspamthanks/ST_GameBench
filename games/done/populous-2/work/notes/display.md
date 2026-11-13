# Populous 2: display patches (sprite blit, pointer, IKBD clamp) and their pixel gate

2026-11-11, Pop2Display. Hatari 2.6.1, 2 MB STE TOS 1.62 snapshots `busy1` and `game_start` (`work/snapshots/`), 8 MHz and Hatari's `--cpuclock 16` (the Mega STE's CPU speed; see "Limits").
Patches (all `; default: no`): `pop2_spr` + `pop2_spr16` (sprites), `pop2_ptr_a` + `pop2_ptr_b` (pointer), `pop2_clamp` (IKBD).
Test-only (`default: no`, never in a build): `test_walk`, `test_walk2`, `test_walk3` (gate input driver), `test_blit` (random differential test), `test_hog` (bus-hold proof).
Tools: `tools/p2abtest.py` (the gate), `tools/p2blit.py` (differential test), `tools/p2clamp.py` (clamp proof), `tools/p2boot.py` (cold boot).
Evidence = raw tool output (kept in `work/scratch/*.log`, quoted below); `[INFERENCE]` = not run.

## 0. Result

| item | gate (both snapshots, 8 MHz and 16 MHz) | busy1 work/pass, 8 MHz | busy1 work/pass, 16 MHz | game_start, 8 / 16 MHz |
|---|---|---|---|---|
| `pop2_spr` + `pop2_spr16`, STE blitter (auto) | IDENTICAL | -4.13 % (fps 6.184 -> 6.444, +4.2 %) | -4.16 % (11.727 -> 12.309, +5.0 %) | -0.21 % / -0.19 % (no 32 px sprite in that view, 2 sixteen-px sprites per pass) |
| the same, cache path forced (`BLT = $b17e0002`: what a plain ST runs) | IDENTICAL | -1.25 % (6.184 -> 6.250, +1.1 %) | not run | +0.03 % |
| `pop2_ptr_a` + `pop2_ptr_b` | IDENTICAL | -2.46 % (6.184 -> 6.311, +2.1 %) | -0.94 % (11.727 -> 11.792, +0.5 %) | -2.29 % (fps 11.007 -> 11.706, +6.4 %) / -0.19 % |
| `pop2_clamp` | IDENTICAL | +0.08 % (inert) | not run | +0.07 % |
| all five together | IDENTICAL | **-6.40 %** (6.184 -> 6.562, **+6.1 %**, turns/s the same numbers: one turn per flip) | **-4.99 %** (11.727 -> 12.333, +5.2 %) | -2.42 % (11.007 -> 11.727, +6.5 %) / -0.36 % (24.067 -> 24.157, +0.4 %) |

"work/pass" = CPU cycles from the top of a pass (`$1254e`, after the VBL wait) to the flip entry (`$1bfe`), exact in Hatari's cycle counter. fps = flips per emulated second over 130 turns; turns/s = the same number (the game takes one turn per pass, `$22fa2`).
Cold boots of an HD build with all five (plus `pop2_credit`): STE 2 MB reaches play with the blitter path (`BLT = $b17e0001`), ST 2 MB (TOS 1.04) reaches play and takes the CPU path (`BLT = $b17e0002`): section 7.

Why the gains are smaller than `hotpaths.md`'s shares (10.0 % + 6.9 %): section 3 and 4.

## 1. The gate (`tools/p2abtest.py`)

Why it can be exact here: the game is frame-coupled and **VBL-independent in play**. One world turn (`$3979a`, `addi.l #1,d0 / move.l d0,$3979a.l` at `$22f9c`/`$22fa2`) and one flip (`$1bfe`) per pass; a patch only changes how long a pass takes, so frames are matched by TURN, not by flip number.

- Both runs restore the same snapshot (snapshots hold unpatched code), apply a live patch set (`pop2patch.py live`) at the flip of the same turn (snapshot turn + 100; applying by turn, not by VBL, makes the start identical at any CPU clock), and run 130 flips.
- Input is a pure function of the turn (`test_walk*`, carried by BOTH runs): the pointer visits 16 positions two turns each (map, panel, all four edges, corners, x > 304, y > 184), and the view `$3e79e/$3e7a0` is set to (snapshot view - 8) + a point on a 16-cell square walked at one cell per turn (period 64): the view scrolls over the map and sprites cross the screen. The IKBD copies `$1cd0`/`$1cda` take PX/PY (`test_walk2/3`), so a real packet cannot move the pointer; the hook is at the turn increment `$22fa2`.
- At every flip entry (`$1bfe`) the debugger writes both screen buffers (`$2300`, `$a000`) and the world RAM `$39600-$473ff` (56,832 B: map, people, effects, players, view, click state) into a FIFO the harness drains, with turn, pointer, shape `$11d50`, `[$202e]`, VBL, cycle counter. At `$1254e` (first instruction after the pass's VBL wait) it writes both buffers again.
- Compared per turn: `back` (`$392e0` at flip entry = the frame just rendered, byte for byte), `world` (md5 of the 56,832 B), `shown@S1` (`$392dc` at `$1254e` = the frame just flipped plus the pointer the first VBL after the flip drew; every turn), `shown@flip` (`$392dc` at the flip entry: the frame plus the pointer after all the pass's VBLs, i.e. the output of the VBL skip path; see the next paragraph for the one case that is excluded). The first two captured turns are not compared (the apply flip mixes unpatched and patched code). A run that compares fewer than 10 turns fails.
- **Finding: the original game's pointer at the flip is timing dependent.** `$11d50` (pointer shape) is changed by the game's hover logic in the middle of a pass; the pointer on screen shows the new shape only after the next VBL. At 8 MHz that VBL comes before the flip, at 16 MHz it may not. Traced (`work/scratch/ptrtrace_8.log`, `ptrtrace_16.log`, pc = `$1a1a` / `$1bfe` hits, turn 419, game_start): at 8 MHz the VBL at 25754 runs `$1a1a` with `shp 0` right before the flip (`1bfe VBL 25754 ... shp 0`); at 16 MHz the last VBL of the pass (25456) ran `$1a1a` with `shp 300` and the flip entry already reads `shp 0` (`1bfe VBL 25456 ... shp 0`). Base @8 MHz against base @16 MHz therefore differed in the pointer rectangle at 8 turns of 128 (pointer rows 20-35 etc.; `work/scratch/self16.log` of the first version). The gate therefore compares `shown@flip` only when `$11d50` was the same at this flip, at the previous flip, and in both runs (8 of 128 turns excluded, counted in the output), and compares `shown@S1` on EVERY turn (it is drawn by the first VBL after the flip, always a full path, with the shape and position of the pass that just ended: deterministic).
- **Self-test: the same code at two CPU speeds is IDENTICAL** (the proof that the method does not depend on pass timing):

```
$ python3 tools/p2abtest.py --snapshot game_start --turns 130 --bmhz 8 --mhz 16
game_start @16 MHz (base @8): IDENTICAL | turns compared: back 128, shown+pointer 120, world 128, shown@S1+pointer 127, shown@flip+pointer 120 (shape-change passes not compared: 8) (skipped 2); flips captured 130/130; patched min VBL/pass 2 | work/pass 638194 -> 610168 (-4.39 %) | fps 10.988 -> 23.978 (+118.2 %), turns/s 10.988 -> 23.978
ALL IDENTICAL
```
(the 8 MHz run and the 16 MHz run of the unpatched game: 130 turns, same back frames, same world hash, same pointer frames, 2.18 times the speed.)

- **Negative controls (the gate fails on a deliberately broken patch):**

```
$ p2abtest.py --turns 60 --snapshot busy1 --only pop2_spr pop2_spr16 --poke 840b3:05       # the blitter's OR pass becomes LOP 5 (D)
busy1 @8 MHz: DIFFER | turns compared: back 58, world 58, shown@S1+pointer 57, shown@flip+pointer 54 ... flips captured 60/60
      BACK DIFFER turn 16137: 295 B differ, first at offset 22667 (row 141), rows 141-171   (and every later turn)   EXIT 1
$ p2abtest.py --turns 60 --snapshot busy1 --only pop2_ptr_a pop2_ptr_b --poke 8603e:4e714e71   # the x-compare of the skip test becomes nops: a moved x is not noticed
busy1 @8 MHz: DIFFER | ...
      SHOWN DIFFER turn 16144 (pointer 1,100; shape 0x0/0x0, [$202e] 0xde80/0xdf18): 105 B differ, first at offset 16000 (row 100), rows 100-110     EXIT 1
$ p2abtest.py --turns 40 --snapshot game_start --neg        # the patched run does not walk
game_start @8 MHz: DIFFER | ... BACK DIFFER turn 389: 8227 B differ ... WORLD DIFFER turn 389: 8 B differ ... SHOWN@S1 DIFFER turn 389 (pointer 300,30 / 160,100 ...     EXIT 1
```
The pointer control is caught by `shown@flip` only (the broken skip changes pixels in the 2nd..8th VBL of a pass; `shown@S1` is the first, always-full VBL): this is why both pointer comparisons exist.
- Sprite coverage of the base run is printed with every result (breakpoints on the sprite routine's entry points). busy1 (130 turns): front end `$2122e` 768, 16 px front end `$211be` 562, `$212b4` 562, 3-column `$213b0` 762, right-edge two-column `$21530` 6, `$21322`/`$21368`/`$2147e` 0-1. game_start: only `$211be` / `$212b4` (279). So the gate exercises the main variant and the 16 px variant over the whole width of the view; the left-edge variants (`$21322`, `$2147e`) and `$21368` are NOT reached by any scene, and they are not patched (only `$213b0` and `$212b4` carry a hook). The in-bounds edge columns of the patched variants (screen column 0, column 17, clipped top and bottom rows, all shifts) are covered by the differential test of section 3.
- Reproduce: `python3 tools/p2abtest.py --only pop2_spr pop2_spr16 [--base ..] [--snapshot busy1 game_start] [--turns 130] [--mhz 8 16] [--poke ADDR:HEX ..] [--neg] [--no-walk] [--dump DIR]`. Two Hatari instances, about 4 minutes per snapshot and clock.

## 2. Free RAM and map

`pop2_spr` code `$84000-$854xx`, `pop2_spr16` (only the site; its code is in pop2_spr's blob at `$85400`), `pop2_ptr_a` `$86000`, `pop2_ptr_b` `$86200`, `pop2_clamp` `$86400` (+ DROPS counter `$86f10`), tests `$86800-$86fff`. Data outside the payload image: `$88000-$881FF` (pointer record), `$88200-$8FFFF` (sprite: `BLT.l` `$88200`, cache header `$88210`, tags `$88220`, scratch `$88360`, 16 slots of 1,856 B at `$88400`). `$88000-$8FFFF` is free in play (delivery.md section 3: 0 longs changed at 2 and 4 MB through play, effects, save, restart, CUSTOM GAME). It is not zeroed by the copy routine: every use is guarded by a magic long (`PTRV`, `PRS0`, `$b17e000m`), so junk RAM after a cold boot is harmless. `pop2patch.py` now range-checks `; data:` (`DATA_ONLY = ($88000, $90000)`), `patches/README.md` has the map rows.

## 3. `pop2_spr`: sprite blit `$213b0` (and `$212b4`)

Disassembly (busy1 dump): the front end `$2122e` clips and dispatches (`$2129a bmi.w $213b0` when the byte column `d7` < `$90`); `$213b0` = `moveq #$78,d1 / neg.b d1 / subq.w #1,d2` (bytes `7278 4401 5342`, **the same bytes as Powermonger's `$124a8`**) followed by the row loop: per row `moveq #-1,d3 / move.w (a1)+,d3 / ror.l d0,d3` (mask) and `moveq #0,d4 / move.w (a1)+,d4 / ror.l d0,d4` ... for 4 planes, twice (two source columns of 5 words = 20 B), merged into 3 screen words per plane (`$21470 movem.w d4-d7,-$8(a0)`, `$21476 adda.w d1,a0`, `$21478 dbra d2,$213b6`). Entry registers: d0 = shift s = x & 15, d2 = rows, a0 = screen address of the column (the front end added y*160 + x/16*8), a1 = rows, d1 free. Caller `$20cd8 jsr $2122e.l` (width != 8) or `$20ce2 jsr $211be.l` (16 px, rows of 10 B, `$212b4` `7270 4401 5342`), then `bra.w $20f36` = `rts`: only a0/a1/d0/d1/d2 are left as the original leaves them (a0 += 160*rows, a1 += 20*rows (10 for 16 px), d1 = `$88` (`$90`), d2.w = `$ffff`); a2-a6 untouched; d3-d7 are scratch in the original and in the patch.

The two paths (code and algebra in `patches/pop2_spr.s`; the algebra ((D&Ma|Pa)&Mb|Pb = D&(Ma&Mb) | (Pa&Mb)|Pb) and the blitter set-up (NFSR = SKEW bit 6, endmasks in both passes, xcount 3, source xinc/yinc 10, dest yinc 144) are Powermonger's, re-derived and re-proved here):
- **Blitter (STE/Mega STE), HOG**, 8 passes (per plane an AND of the mask, an OR of the plane), each at most rows x 3 words x 12 cycles (about 900 cycles at 25 rows, 1,200 at 33). `pop2_spr16`: xcount 2, dest yinc 152, one source word per row. Selected by a lazy bus-error-safe probe on the first call (`$ff8a28`/`$ff8a2a` read back, BUSY clear; a plain ST has no blitter and takes the bus error, which the probe's temporary `$8.w` handler absorbs): `BLT.l` = `$b17e0001` blitter, `$b17e0002` cache. `$b17e0003` = the original code (tests).
- **Pre-shifted cache (the CPU path for an ST)**: per (a1, s) the shifted words are built once (36 B/row: 3 mask longs + 6 plane longs) and drawn with movem + 5 and.l + 5 or.l + movem + one more long (~325 cycles/row against ~770). Unlike Powermonger the sprite data are NOT assumed static: Populous 2 loads its sprite sheets into the game's own arena (observed `a1` `$69450`, `$6ac38`, `$6baac`, `$71416`-`$74cc4`, all < `$7b380`) and a level or landscape load rewrites them. Every entry therefore keeps a copy of the 20 B/row source and every hit compares the rows being drawn against it (`cmpm`, ~110 cycles/row) before drawing, so a changed or rebuilt sheet is redrawn from the new data (exact for any data; the negative control below proves the compare matters). 16 slots (4 sets x 4 ways) of 1,856 B (<= 33 rows x (36 + 20) B). s = 0, rows 0 or > 33 (> 64 for the blitter), `a1` outside `$20000-$7b37f` take the original code. `pop2_spr16` has no cache: on an ST it runs the original code.
- Blitter bursts stay short (buserr.md): no pass is longer than 1,200 cycles; the IKBD byte time is 10,240. Section 5 proves with a deliberate 128,000-cycle burst what happens otherwise.

**Differential test (`tools/p2blit.py`, patch `test_blit`)**, inside the running game: each trial draws a random sprite through the game's own front end (`$2122e` or `$211be`, half each) onto two identical random screens, once with the original code (`BLT = $b17e0003`) and once with the path under test, x -48..339, y -40..229, rows 1..33, real sheet rows (pool of two sprite addresses, hits the cache) or random rows, one trial in eight with a random source word XOR-ed (restored afterwards, so the cache must notice), shifts 0..15; the affected rows are compared after every trial, the whole screens every 64th:

```
$ python3 tools/p2blit.py --trials 30000
mode 1 (blitter): trials 30000/30000, mismatching trials 0, whole-screen mismatches 0, trials on the pool sprites 15063, through the 16 px front end 15049 -> OK
mode 2 (pre-shifted cache): trials 30000/30000, mismatching trials 0, whole-screen mismatches 0, trials on the pool sprites 15063, through the 16 px front end 15049 -> OK
$ python3 tools/p2blit.py --trials 3000 --neg          # a wrong LOP in the blitter / a nopped `or.l` in the cache: must be detected
mode 1 (blitter): ... mismatching trials 592 ... -> OK          mode 2 (pre-shifted cache): ... mismatching trials 815 ... -> OK
$ python3 tools/p2blit.py --trials 6000 --neg-verify   # the cache's five source-compare branches nopped
mode 2 (pre-shifted cache): trials 6000/6000, mismatching trials 13, ... -> OK (13 mismatches detected: the verify is necessary and the test reaches it)
```
(An earlier 30,000-trial run before `pop2_spr16` and the rows = 0 guards, 32 px front end only: 0 mismatches in both modes, `work/scratch/blit_30k_32px_only.log`.)

Gate results for the sprites are in section 0. Why only -4 % to -6 % of a frame (the profile said 8.75 % + 1.13 % of cycles for the two variants): the blitter's cost is not free: 8 start/stop sequences and about 100 instructions of set-up per call (read from the code), plus the passes themselves ([INFERENCE]: the cycle model of Hatari's blitter was not read, so the split is not measured). Measured on busy1 with the walk switched off (static view, 780 calls of each variant in 130 turns): blitter **-5.63 %** (1,255,126 -> 1,184,520, fps 6.056 -> 6.250), cache **-2.54 %** (-> 1,223,184, fps 6.208); with the scrolling walk it gives -1.25 %. [INFERENCE] the reason is a lower hit rate (clipped row counts and `a1` change while sprites cross the top and bottom edges, a rebuild costs about 600 cycles/row); the hit rate was not counted. The blitter at 16 MHz keeps its gain in Hatari (-4.16 %), which charges it the same cycles at both clocks. [INFERENCE] A real Mega STE runs its blitter at 8 MHz while the CPU runs 16 MHz, so there the cache could be as good or better than the blitter; `BLT.l` can be pre-set to `$b17e0002` to force it. Nothing in this pass runs on real hardware.

## 4. `pop2_ptr_a` + `pop2_ptr_b`: pointer restore + redraw only when something changed

The VBL handler `$18fa` restores the pointer's saved 16 rows (`$1a38`: `$2032` -> `[$202e]`, `$1a3c cmpi.w #$90,d6`: 16 or 8 bytes per row) and redraws it into the shown buffer `[$392dc]` at `$1ab6`-`$1b30` (position `$393fa/$393fc`, shape `$682d0 + (short)[$11d50]`, 4 words per row, mask = NOT of the OR of the four planes) at EVERY VBL, about 9,900 cycles. A pass is 4-8 VBLs, the screen changes once per pass.
- Hook A at `$1a1a` (`move.l $202e.l,d0`, the instruction after the hide test): skip (`jmp $1b34`) iff the last draw's inputs equal the current ones (buffer `[$392dc]`, x, y, shape word `[$11d50]`), `[$202e]` is the address it drew at, the rectangle on screen is byte-for-byte the image that draw left (`cmpm`) and the 16 x 8 shape bytes are the ones it drew from. Then restore writes the saved pixels S over the rectangle, the draw saves S again and ORs the pointer back: the same bytes in the screen, in the save buffer (`$2032`; its only references in the code are `lea $2032.l,a6` at `$1a28`, `$1ac6`, `$1b68`: restore, draw, hide) and the same `[$202e]`, `[$2232]`, `[$2234]` (functions of x and y). Else the original runs.
- Hook B at `$1b34` (`move.w #1,$392cc.l`, the end of the pointer code and the target of the hide path): if A flagged a draw, record the inputs (re-checked: an IKBD packet or a flip during the draw means no entry), the rectangle and the shape rows, then the displaced instruction.
- Data `$88000` (+0 FLAG.l +4 VALID.l magic longs, inputs, IMG[256], SHAPE[128]); a stale or junk record cannot validate (magic + every field compared). The first VBL after every flip is a full draw (the buffer changed), so a pass costs one full draw plus skips.
- Measured (section 0): -2.46 % / -2.29 % of work/pass at 8 MHz (fps +2.1 % / +6.4 %), -0.94 % / -0.19 % at 16 MHz (the passes are 2-4 VBLs long, so there are 1-3 skips to win). The skip is not free: 64 + 32 `cmpm` + branches ~ 3.7k cycles against ~8.4k for the pointer part of a VBL; exactness needs the rectangle and the shape compared. Powermonger's `p4_ptr` result (-4.4 % to -5.6 %) came from passes of 12 VBLs.
- Gate: IDENTICAL on both snapshots (back, world, shown@S1, shown@flip); negative control above.

## 5. `pop2_clamp`: IKBD position clamp (ported from Powermonger's `p4_clamp`, proven first)

Same parser as Powermonger: the VBL writes `$0d` (`$1a0a move.b #$d,$fc02.w`, absolute mode set up from `$1d22` with `$09 $013f $00c7` = 0..319 x 0..199), the ACIA handler `$1c42` -> `$1c68` runs the state machine at `$2022` (`$f7` header -> state 5, bytes stored at `$2025+(5-state)`), the packet completes at `$1cc6 move.b $2025,$2023` followed by the copies `$1cd0 move.w $2026,$393fa` and `$1cda move.w $2028,$393fc`. A lost byte shifts the packet.
Proof (`tools/p2clamp.py`, patch `test_hog`: at the top of every pass a 32,000-byte HOG blitter copy, ~128,000 cycles = 12 byte times of bus hold, which is what a too-long blitter burst does):

```
== A: test_hog, NO clamp
   garbage packets seen at $1cd0 (packet x/y words out of range): 2; first: [{'pkt_x': 63232, 'pkt_y': 150, ... 'turn': 16055, 'vbl': 141002}, {'pkt_x': 150, 'pkt_y': 63232, ... 'turn': 16060, 'vbl': 141046}]
   Bus Error lines: ['WARN : Bus Error reading at address $9b0048, PC=$1aee addr_e3=1aee op_e3=3cd4']
   run reached its end: True; end numbers (turn.w, VBL, DROPS): [16060, 141401, 0]
== B: test_hog + pop2_clamp
   garbage packets seen at $1cd0 (packet x/y words out of range): 0; first: []
   Bus Error lines: []
   run reached its end: True; end numbers (turn.w, VBL, DROPS): [16066, 141401, 5]
```
`pkt_x = 63232 = $f700` is the next packet's `$f7` header eaten as a position byte (x = `$f7 00`), `y = 63232` the same in the y word; `$1aee` is the pointer draw's `move.w (a4),(a6)+` (`$1aec`) writing through `a4 = $392dc + y*160`: the same failure as Powermonger's `$147e`. In A the turn word ends at 16060 (the turn of the second garbage packet) and Hatari reports the bus error; with the clamp (B) five packets were dropped (`DROPS` = 5), no bus error, and the turn reaches 16066 in the same 400 VBLs (a pass is long here: it includes the 128,000-cycle blit). Gate (normal use, nothing dropped): IDENTICAL, +0.08 % / +0.07 % cycles.
Without a blitter burst Populous 2 has no overrun source of its own (the unpatched game plays 15,600 turns in baseline.md); the clamp is a safety net for `pop2_spr` and for anything that holds the bus or masks interrupts on a real machine ([INFERENCE]).

## 6. Not done / limits

- Hatari only. A real STE/Mega STE blitter, ACIA timing and the 2-chunk interrupt latency Powermonger saw in Hatari are not measured on hardware. The 16 MHz rows are Hatari's `--cpuclock 16` on the STE snapshots, not a Mega STE machine (the Mega STE boot in section 7 only proves delivery and play).
- The cache path was gated on an STE with `BLT` forced (`--poke 88200:b17e0002`), proved by 30,000 random trials, and selected by the probe on a cold-booted ST; the ST cold boot shows only the probe's result word (`BLT = $b17e0002`); whether `pre` itself ran during that boot was not checked.
- `shown@flip` excludes the 8 of 128 turns in which the pointer shape changes mid-pass (timing dependent in the ORIGINAL, see section 1); those turns are covered by `shown@S1` (full path) and, for the skip, by the construction argument of section 4, not by a flip-level pixel compare.
- Left-edge sprite variants (`$21322`, `$2147e`), `$21368` and the right-edge `$21530` are not patched (they are rare: 6 calls of `$21530` in 130 turns, none of the others).
- Not covered: 60 Hz machines (the stock game does not run there, delivery.md section 4), TT/Falcon.

## 7. Cold boots (`tools/p2boot.py`, HD build with `pop2_credit pop2_spr pop2_spr16 pop2_ptr_a pop2_ptr_b pop2_clamp`)

```
ste 2048 KB TOS_1_62.img: in_play=True marker='P2PO' turn 177 -> 213 BLT=$b17e0001 (clamp drops 0) patches=[pop2_credit pop2_spr pop2_spr16 pop2_ptr_a pop2_ptr_b pop2_clamp]  shot=disp_ste_2mb.png
st 2048 KB TOS_1_04.img: in_play=True marker='P2PO' turn 177 -> 213 BLT=$b17e0002 (clamp drops 0) patches=[...same...]  shot=disp_st_2mb.png
```
`BLT` is `pop2_spr`'s probe result at `$88200`: the STE takes the blitter, the plain ST (`work/shots/disp_st_2mb.png`: "2MB ST(WS2), TOS 1.04", game in play) the CPU path. Extra boots, same build:
```
megaste 4096 KB TOS_1_62.img: in_play=True marker='P2PO' turn 177 -> 213 BLT=$b17e0001 (clamp drops 0)   shot=disp_megaste_4mb.png
ste 4096 KB TOS_1_62.img: in_play=True marker='P2PO' turn 177 -> 213 BLT=$b17e0001 (clamp drops 0)       shot=disp_ste_4mb.png
```

## 8. Reproduce

```
python3 tools/pop2patch.py verify
python3 tools/p2abtest.py --only pop2_spr pop2_spr16 pop2_ptr_a pop2_ptr_b pop2_clamp --mhz 8 16      # the gate, both snapshots
python3 tools/p2blit.py --trials 30000                                                             # sprite differential test (+ --neg, --neg-verify)
python3 tools/p2clamp.py                                                                           # clamp proof
python3 tools/pop2patch.py build --out build/disp_hd --only pop2_credit pop2_spr pop2_spr16 pop2_ptr_a pop2_ptr_b pop2_clamp
python3 tools/p2boot.py --machine ste --nobuild                                                    # and --machine st
```
