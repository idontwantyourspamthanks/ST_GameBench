# Moonshine Racers: tighten B = sprite items (5) STE blitter and (6) the player car (`tb_*`), built and gated

Machine for every number: Hatari 2.6.1, STE TOS 1.62, 1 MB, 8.02 MHz, 50 Hz, unless named. Cycle numbers are Hatari `e FrameCycles` per pass (`work/tightB/cyc.py` = the `work/hud/build/cyc3.py` recipe: loop top `$796a` to flip `$d1ca`, interrupts included, tick patches OFF), compared **per matched pass** (same snapshot, same `$100e`, `work/tightB/cmpcyc.py`), reference = the default set minus the pacer (`mr_edge rd_geom rd_draw rd_init hd_stage hd_init hd_clouds hd_nomap hd_nomap2`, "base"). Raw outputs are in `work/tightB/res/` and `work/tightB/res2/`, pasted below. `[INFERENCE]` marks what no tool output here proves. Nothing in `tools/`, `patches/README.md`, `PLAN.md`, `integration.md` or other agents' files was touched; I worked from the private tool `work/tightB/msrpatch_priv.py` (patch dir `work/tightB/patches/` = symlinks to `patches/` minus the other agents' `ta_*`/`tc_*`, `mkpd.sh`).

## 0. Result in one page

| item | patches (all `default: no`; **I flipped no default**) | gain per pass at 8 MHz | gates |
|---|---|---|---|
| (6) player car + second layer | `tb_car` (site `$39ac`) + `tb_carph` (site `$ed90`); blobs `$BF500`, `$BFC00`, data `$BF000+1280`, `; ram: $D8000-$DDFFF` | **-39.2 k (start, no speech) / -40.6 k (speech) / -41.9 k (standing) / -40.1 k (race_up)** = -0.245 to -0.26 VBL (8.0 % of the pass) | verify ALL OK; pixels 8/8 IDENTICAL (4 scenes x 2 flips), negative control DIFFERS; state 8/8 equal (tick, extras 8/16/32 MHz, `race_drive` incl. time-out and restart); Unicorn 60-400 passes x 15 levels |
| (5) STE blitter | `tb_blit` (+ `tb_blit11 tb_blit13 tb_blit15`, one table each): table stubs, blob `$B4500`, data `$B5800+512` | uncapped HOG **-17.0 k / -12.6 k / -14.9 k** (start / standing / race_up); cap 800 -14.6 k / -12.3 k / -9.9 k; cap 400 -3.2 k / -5.3 k; cap 200 **+30 k (loss)**; **TB-guarded (the shipped variant) -4.3 k / -8.8 k / -8.2 k** | pixels 8/8 IDENTICAL for the shipped and for the HOG variant; negative control DIFFERS; state 8/8 equal |
| both | `tb_car tb_carph tb_blit tb_blit11 tb_blit13 tb_blit15` | **-44.4 k / -49.5 k / -46.5 k** (start / standing / race_up, no speech) = -0.28 to -0.31 VBL | pixels 8/8 IDENTICAL, state 8/8 equal |

Findings that change the earlier plan:
1. **The player car bank is not static**: the game XOR-toggles wheel-animation lists into it (`$11342`/`$11300` -> `$ed74`/`$ed90`, `eor.w d1,(a1,d0.w)` at `$edc2`) every other pass while driving. Two bank states per bitmap (a second list kind exists: 4 states). A cache keyed by pointer alone draws a wrong frame (emulator A/B showed it: bottom rows 32-35 of the car). The fix (section 2.3) is a state label maintained by a 14-byte hook plus **chunk sharing** between the states, so the second state costs ~0.6 KB instead of 2.9 KB.
2. **Generated straight-line code beats a pre-shifted data cache by a wide margin**: 11.0-11.6 k cycles per car frame (model, Unicorn-verified) against the stock 33-36 k, the layer 5.8 k against 22 k. Pre-shifted data (the earlier option b) was estimated at ~16 k total.
3. **The blitter only pays uncapped.** The raster-safe version (guard on Timer B) recovers ~1/3 to 1/2 of the HOG gain; any burst cap short enough to be safe loses the gain (cap 200 is slower than the CPU). Hatari **does** hold interrupts off during a HOG burst (section 3.4), contrary to the earlier study's reading of `LineCycles`.
4. A bug the gate found and I fixed: the first blitter router passed `rows <= 0` calls (the stage issues them, `race_up`) to the blitter with `ycount = 65534`, which trashed RAM; `race_up` crashed in the A/B. Fixed (`tst.w d7 / ble`), re-gated.

## 1. What was measured about the sprite path (evidence)

- Player slot `$2c68` = type 0, bank `$2156a`/`$25244`/`$28f0c` (`$102c`, `dfa8..dfc8`), frame index `$6(a2)+$8(a2)` (15 bitmaps = 3 sizes x 5 steering frames: indices 0-4, 15-19, 30-34), 4 columns, nibble 7 (3 planes), kernel `$13f6e`; x constant **per bitmap** (the entry's x offset differs per steering frame, so `x & 15` is 1, 2 or 4 depending on the frame); y 151-154, 34-37 rows. Second layer `$3480` = bank `$2ca48`, 56x21, x & 15 = 4 in the traced scenes, other frames/shifts occur in curves (a cache run on `L12.bin` held 5 layer bitmaps with shifts 2-6). `work/sprite/calls.pkl` (traced) and the Unicorn runs (`work/tightB/emucmp.py`).
- Row format (4 columns, nibble 7, 24 bytes per row): `p0c0 p0c1 p1c0 p1c1 p2c0 p2c1 | p0c2 p1c2 p2c2 | p0c3 p1c3 p2c3`; kernel lines `$14030-$14080`. Verified by `work/tightB/model.py` against the stock kernel in Unicorn: 144 draws (15 bitmaps + layer, 3 x positions, 3 y positions) **0 differing bytes** (`test_model.py`).
- Mask coverage of the 37-row car at shift 2 (5 destination columns per row): 47 full, 77 partial, 61 empty destination words (frame 2); layer 36 / 44 / 25. Generated code per car frame: 2.8-3.0 KB (all 15: 43 KB), layer 1.4 KB.
- Stock `$ed90` writer, from `$1137a` (`jsr $ed74` inside the 15-call loop of `$11342`): Unicorn write trace `{0xedc2: 288 writes in $2578a-$28afe}` per toggle pass; `L5.bin` bank diff 357 bytes every second pass.

## 2. (6) The player car: `tb_car`, `tb_carph`

### 2.1 Design
- **Site**: the long `$39ac` of the nibble-7 kernel pointer table `$399c` (entry for 4 columns, stock `$00013f6e`) -> stub `$BF500`. Both object-stage paths (`$ed38` `movea.l (a4,d3.w),a4` / `jsr (a4)` and tc_ord's) call through the table, so no other site is needed. The stub costs only the 4-column nibble-7 calls (about 3 per pass) 2 `cmpa` before it jumps to the stock kernel with the registers untouched.
- **Slots `$2c68` (car) and `$3480` (layer) only**, else `jmp $13f6e`. Conditions for the fast path: rows 1-48, y >= 0, y + rows <= 200, x >= 0, x & 15 != 0, X0 <= 15 (5 destination columns on screen); anything else = stock kernel.
- **Generated code** (`create`, 68k, runs inside the draw that first needs a variant): per row and destination column (shift applied with `lsr.l` on the word pairs; all values are immediates): mask 0 -> nothing; mask `$ffff` -> `move.l #p0:p1,d(a3)` + `move.l #p2:0,d+4(a3)` (or `clr.l`); partial -> `andi.l #~M:~M,d(a3)` x2 (planes 0-1, 2-3) + `ori.l`/`ori.w` per non-zero plane word. Displacements are absolute from the sprite's first row (all rows fit in a signed word), so the code is position independent in y and x (`a3 = a5 + y*160 + X0*8`, `$100c` stored as the stock kernel does).
- **Chunks of 8 rows**, each ended by `rts`; the variant is a list `jsr c0 / ... / jmp cN` (6 bytes per chunk). A chunk identical to the same chunk of the earlier entry for the same (bitmap, rows, shift) = the other wheel-animation state is **shared**, not stored again.
- **Key** = (bitmap pointer, label<<16 | rows<<4 | shift); label = `PH[bitmap index]` (slot `$2c68` only). `tb_carph` (site `$ed90`, the first two instructions of the XOR routine, entered only by fall-through) flips bit `(list index - bitmap index) & 7` of `PH[bitmap index]` (`$BF440`) on every XOR application: the label identifies the exact content state (XOR lists commute).
- **Validity**: (a) label as above; (b) flush of the whole cache when the pass counter `$100e` goes down (race restart); (c) 3 probe longs of the source bitmap (offsets 148, 388, 652) compared on every draw, mismatch = flush and regenerate; (d) entry table 39 entries, pool 24 KB: a variant that does not fit is remembered as "no code" and uses the stock kernel (fill-once policy, no thrash).
- **Machines** (probe at the first call, supervisor mode, SR `$2700` while the vectors are swapped, all restored): enabled only on a plain 68000 (`move.w ccr,d0` is illegal) **without** the Mega STE register `$ff8e21` (bus error on ST/STE). Everything else (Mega STE, 68010+, TT/Falcon, user mode) = stock kernel, `INIT $BF000 = 2`. Generated code is therefore never executed where a CPU cache exists (lead's condition 1). Hatari STE: `INIT = 1` (observed: `mem 000BF000 01`).
- **Memory**: `$BF000-$BF4FF` data (zero at start; the pool pointer is initialised lazily), `$BF500` code (1,083 B), `$BFC00` hook (14 B), `; ram: $D8000-$DDFFF` (24 KB cache, written at run time, lead cap; `$DE000-$E2BFF` stays free). `verify` ALL OK with rd_* at `$C0000-$D7FFF`.

### 2.2 Cost (raw `res/` below)
- Per matched pass: -39.2 k to -42 k (section 0). The remaining car+layer cost is about 17.5 k (57 k before), of which the generated code is ~11.6 k + 5.8 k; the stub / key / probes cost ~0.5-0.6 k per call [carcost below].
- **Cold cost** (generation, once per variant and state, inside the draw that needs it): (Hatari `e CycleCounter` at the stub entry `$BF500`, the hit path `$BF5E6` and the return `$ed70`, `create` `$BF6E8-$BF93A`; interrupts inside the window are included)
```
race_start (400 VBL):
slot $2c68: calls 185 total (stub entry -> return) mean 13556 min 10384 max 401516
slot $3480: calls 188 total (stub entry -> return) mean 6295 min 6184 max 12892
stub overhead (entry -> jmp (a4)) mean 757; compiled code mean 9139
create (generation) calls 4 [68216, 104116, 57824, 89668]
race_drive (400 VBL):
slot $2c68: calls 60 total (stub entry -> return) mean 17737 min 10384 max 334820
slot $3480: calls 60 total (stub entry -> return) mean 6406 min 6184 max 7540
stub overhead (entry -> jmp (a4)) mean 1508; compiled code mean 10563
create (generation) calls 0 []
```
Generation costs 57.8 k - 104 k cycles per variant (0.36-0.65 VBL). The `max` in the total column is the call that generated a variant. Hot calls: car 10.4 k (min) - 13.6 k (mean), layer 6.2 k - 6.4 k (stock 35 k / 22 k).
- It is paid lazily during the first passes of a race (and after a restart); no pre-warm site was used because the variant (frame, size, x shift) is only known when the car is drawn. A pass that generates one variant is ~0.4 VBL longer than usual, i.e. inside the 5 VBL tick of the fixed-tick pacer (it never causes an overrun by itself at 8 MHz: 3.06 + 0.4 < 5); two variants in one pass (car + layer) ~0.7 VBL.
- **Pool pressure** (Unicorn census, 600 passes, 24 KB pool, 39 entries, `work/tightB/census.py`, raw in section 4.4): straight driving (`up`) 94 % of the player draws run generated code (9 entries, 12.9 KB used; the 2-minute cold-boot drive ended with 8 entries, `POOLP $DB052`); with constant steering changes (`zig`/`upleft`, alternate left/right every 15 passes) the 39-entry table and the pool fill after ~100 passes and 47-68 % of the draws run generated code, the rest use the stock kernel (fill-once policy). Model estimate for car + layer per pass (hits x 9 k + stock x 28 k + generations x 80 k; **[INFERENCE]**, not Hatari): 22.6 k straight, 36-46 k with heavy steering, 59 k stock. I also tried "flush everything when full" (variant kept in `work/tightB/tb_car_fillonce.s` = the shipped file; the flush-all edit was discarded): 94 % compiled draws but 145-270 generations per 600 passes, estimated 40-58 k per pass = worse under steering, same when straight. So the shipped car gain is the measured -39..-42 k in the (mostly straight) scenes and shrinks to roughly -15..-25 k under heavy steering [INFERENCE]. A bigger pool ($DE000-$E2BFF is free, 19 KB more, lead cap 24 KB) or shorter code would raise the steering hit ratio.

### 2.3 What changes between passes (answer to the brief)
The bank bytes. The steering frame (`$6(a2)`), the size (`$8(a2)`) and the bounce change the bitmap index; x is constant per bitmap; the scale step is part of the index (3 sizes). The wheel animation XORs `$11342`'s lists (kind +5) and `$11300`'s (kind +10) into all 15 bitmaps every other pass while moving (`$130c != 0`, `$1338 == 0`): the earlier "217 bytes between two snapshots" were this animation, not a one-time patch (the two dumps differ by race pass count).

## 3. (5) The STE blitter: `tb_blit` (+ `tb_blit11`, `tb_blit13`, `tb_blit15`)

### 3.1 Design
- Sites: the 1-, 2- and 3-column entries of the kernel pointer tables `$399c` / `$39b0` / `$39c4` / `$3a14` (nibbles 7 / 11 / 13 / 15), one patch file per table (a file has one site); they point at 12 stubs of 16 bytes at `$B4510-$B45CF`. Hooking the tables (not `$ed6e`) works with and without `tc_ord` (MSRTightC's interface note). 4 columns stay stock (nibble 7: `tb_car`; the blitter ties at 16 rows and the stock `n13 c4` layout is not understood).
- A stub sets d4 = columns, a2 = descriptor (2P, dest plane offsets, P), d3 = stock entry and enters `common`: stock entry (registers untouched, d7 clamped to the bottom like the stock kernel) unless blitter probe OK, x & 15 != 0, x >= 0, y >= 0, rows >= 1 and >= minimum (1 col 16, 2 cols 10, 3 cols 16 rows for the shipped variant), X0 + cols + 1 <= 20.
- Formulation (unchanged from `sprites.md` section 6, differential-tested earlier): mask T = OR of the data planes (P passes into TMP `$B5880`), `D &= ~T` on the 4 destination planes (skew, endmasks), `D |= S` per data plane; 3 columns = plane-major pair + one single (two groups). HOG mode; rows per pass limited to `BUDGET / (12 * n)`.
- **Probe** (first call, supervisor, plain 68000, no `$ff8e21`, `$ff8a28` reads back `$5aa5`; bus-error guarded; all vectors restored): `BST $B5800 = 1` on, `2` off. No blitter (ST, TT, Falcon), Mega STE, 68010+: stock kernels. Mega STE not measured (no gain claimed there).
- **Burst cap and the Timer B guard.** `GUARD=1`: before every pass `TBCR $fffffa1b` must not be 8 (the ISR `$d616` stops Timer B after the last band: `clr.b $fa1b` at `$d674`) or `TBDR $fffffa21 >= GTH`; otherwise a bounded spin (400 iterations) until the raster interrupt has run. With `GTH = 3` and `BUDGET = 900` a pass starts only when the next raster interrupt is at least 2 scanlines (1,024 cycles) away, so a pass of <= 900 cycles cannot delay it; the ISR `$d616` uses 4-line bands (TBDR counts 4,3,2,1).

### 3.2 Gain per pass, matched passes (raw `res2/cyc_summary.txt` below)
```
== race_start
cyc_race_start_base+tb_blit+tb_blit11+tb_blit13+ no speech  n  32 ref    487144 new    482853 delta    -4292 (-0.027 VBL) min -11892 max 820
cyc_race_start_base+tb_blit+tb_blit11+tb_blit13+ speech     n  19 ref    507766 new    501356 delta    -6410 (-0.040 VBL) min -16068 max -892
cyc_race_start_base+tb_car+tb_carph+tb_blit+tb_b no speech  n  32 ref    487144 new    442770 delta   -44374 (-0.277 VBL) min -53828 max -38564
cyc_race_start_base+tb_car+tb_carph+tb_blit+tb_b speech     n  20 ref    510924 new    463962 delta   -46962 (-0.293 VBL) min -51452 max -36232
cyc_race_start_base+tb_car+tb_carph.json         no speech  n  32 ref    487144 new    447908 delta   -39236 (-0.245 VBL) min -45024 max -35356
cyc_race_start_base+tb_car+tb_carph.json         speech     n  19 ref    507766 new    467174 delta   -40592 (-0.253 VBL) min -44532 max -35376
cyc_race_start_base+tbb_800+tbb_80011+tbb_80013+ no speech  n  32 ref    487144 new    472552 delta   -14592 (-0.091 VBL) min -21600 max -7784
cyc_race_start_base+tbb_800+tbb_80011+tbb_80013+ speech     n  20 ref    510924 new    494400 delta   -16524 (-0.103 VBL) min -22236 max -10780
cyc_race_start_base+tbb_h+tbb_h11+tbb_h13+tbb_h1 no speech  n  32 ref    487144 new    470145 delta   -16999 (-0.106 VBL) min -24904 max -8732
cyc_race_start_base+tbb_h+tbb_h11+tbb_h13+tbb_h1 speech     n  19 ref    507766 new    489848 delta   -17919 (-0.112 VBL) min -23896 max -10780
== race_grid
cyc_race_grid_base+tb_blit+tb_blit11+tb_blit13+t no speech  n  19 ref    411560 new    402795 delta    -8766 (-0.055 VBL) min -11356 max -7788
cyc_race_grid_base+tb_blit+tb_blit11+tb_blit13+t speech     n  47 ref    411787 new    403971 delta    -7816 (-0.049 VBL) min -10480 max -7436
cyc_race_grid_base+tb_car+tb_carph+tb_blit+tb_bl no speech  n  19 ref    411560 new    362106 delta   -49454 (-0.309 VBL) min -52888 max -45556
cyc_race_grid_base+tb_car+tb_carph+tb_blit+tb_bl speech     n  47 ref    411787 new    362989 delta   -48799 (-0.305 VBL) min -50396 max -47264
cyc_race_grid_base+tb_car+tb_carph.json          no speech  n  19 ref    411560 new    369688 delta   -41872 (-0.261 VBL) min -43840 max -39292
cyc_race_grid_base+tb_car+tb_carph.json          speech     n  47 ref    411787 new    369770 delta   -42017 (-0.262 VBL) min -43648 max -39324
cyc_race_grid_base+tbb_800+tbb_80011+tbb_80013+t no speech  n  19 ref    411560 new    399274 delta   -12287 (-0.077 VBL) min -16064 max -10848
cyc_race_grid_base+tbb_800+tbb_80011+tbb_80013+t speech     n  47 ref    411787 new    400454 delta   -11333 (-0.071 VBL) min -14156 max -10876
cyc_race_grid_base+tbb_h+tbb_h11+tbb_h13+tbb_h15 no speech  n  19 ref    411560 new    398921 delta   -12639 (-0.079 VBL) min -17744 max -10848
cyc_race_grid_base+tbb_h+tbb_h11+tbb_h13+tbb_h15 speech     n  47 ref    411787 new    400454 delta   -11334 (-0.071 VBL) min -14176 max -10876
== race_up
cyc_race_up_base+tb_blit+tb_blit11+tb_blit13+tb_ no speech  n  37 ref    437152 new    428937 delta    -8216 (-0.051 VBL) min -9800 max -5280
cyc_race_up_base+tb_blit+tb_blit11+tb_blit13+tb_ speech     n  27 ref    457613 new    446287 delta   -11326 (-0.071 VBL) min -16660 max -3856
cyc_race_up_base+tb_car+tb_carph+tb_blit+tb_blit no speech  n  37 ref    437152 new    390699 delta   -46453 (-0.290 VBL) min -48124 max -43556
cyc_race_up_base+tb_car+tb_carph+tb_blit+tb_blit speech     n  27 ref    457613 new    407902 delta   -49711 (-0.310 VBL) min -54568 max -47388
cyc_race_up_base+tb_car+tb_carph.json            no speech  n  37 ref    437152 new    397019 delta   -40133 (-0.250 VBL) min -42352 max -38252
cyc_race_up_base+tb_car+tb_carph.json            speech     n  27 ref    457613 new    416924 delta   -40689 (-0.254 VBL) min -44660 max -38360
cyc_race_up_base+tbb_800+tbb_80011+tbb_80013+tbb no speech  n  37 ref    437152 new    427255 delta    -9898 (-0.062 VBL) min -11776 max -9352
cyc_race_up_base+tbb_800+tbb_80011+tbb_80013+tbb speech     n  27 ref    457613 new    442420 delta   -15193 (-0.095 VBL) min -20936 max -11812
cyc_race_up_base+tbb_h+tbb_h11+tbb_h13+tbb_h15.j no speech  n  37 ref    437152 new    422260 delta   -14892 (-0.093 VBL) min -16752 max -14368
cyc_race_up_base+tbb_h+tbb_h11+tbb_h13+tbb_h15.j speech     n  27 ref    457613 new    437165 delta   -20448 (-0.128 VBL) min -27608 max -16832
```

Gain at several caps (race_start, race_grid, race_up; no speech; ISR-safety in the last column):
| variant | start | standing | race_up | raster interrupt delay |
|---|---|---|---|---|
| HOG, no cap (`BUDGET 1800`) | -17.0 k | -12.6 k | -14.9 k | up to ~1,800 cycles (3.5 lines) [INFERENCE from burst length]; Hatari: 16/560 raster ISRs > 100 cycles late |
| cap 800 | -14.6 k | -12.3 k | -9.9 k | up to ~800 |
| cap 400 (first-run router build) | -3.2 k | -5.3 k | n/a | up to ~400 |
| cap 200 (first-run router build) | **+30.2 k** | **+16.0 k** | n/a | up to ~200 |
| **TB guard, GTH 3, 900 (shipped)** | **-4.3 k** | **-8.8 k** | **-8.2 k** | 0 for Timer B by construction; VBL ISR up to the burst (measured +240 cycles) |
| TB guard, GTH 2, 440 (first-run) | +7.6 k | +3.5 k | n/a | 0 |
| TB guard, GTH 4, 1400 (first-run) | -6.0 k | -1.3 k | n/a | 0 |
(the caps 400/200/GTH-2/GTH-4 rows come from the first-run router build, `res/cyc_race_*_base+tbb_*.json`, same measurement method; the table-stub build was re-measured for HOG, 800 and the shipped variant.)

### 3.3 Why the cap loses: a pass costs ~100-250 cycles of CPU register writes whatever its length, 10-12 passes per sprite part; shortening the burst multiplies the passes (cap 200: 5-8 rows per pass). The guard loses the rest to the 25-50 % of the time in which the pass must wait for the raster interrupt (the CPU is idle while spinning).

### 3.4 ISR entry latency (Hatari, `work/tightB/isrlat.py`: persistent trace breakpoints on `$d616` Timer B, `$d11e` VBL, `$cfb4` IKBD; `e LineCycles` / `e FrameCycles`; 1,500 VBL of the driving snapshot, ~560 raster entries, 60 VBL entries per variant)
```
variant                                       TB n  late>50  late>100  max late | VBL n VBL LC median   max
base                                           560       21         0        72 |    60           132   148
base+tbb_h+tbb_h11+tbb_h13+tbb_h15             560       41        16       248 |    60           132   424
base+tbb_800                                   568       52        25       252 |    61           132   508
base+tbb_400                                   568       60        24       236 |    61           132   488
base+tb_blit+tb_blit11+tb_blit13+tb_blit15     560       28         0        68 |    60           132   444
```
Reading: nominal raster entry is LineCycles ~464 (end of line); `late` = `((LineCycles - 480 + 256) mod 512) - 256` (aliases above 256). **Hatari does delay the interrupts during a HOG burst**: with HOG 16 of 560 raster interrupts are more than 100 cycles late (33 in the first-run router build), max ~250 (later ones alias into the next line), and the VBL ISR entry reaches 424-508 against the baseline's 148. The guarded shipped variant has **no** raster interrupt later than the baseline's own jitter (max 68 vs 72) and its VBL ISR entry moves to at most 444 (a 900-cycle burst; the VBL handler has about 32,000 cycles of margin before the first displayed line [INFERENCE: ~63 lines x 512 before display start on a 313-line frame]). The IKBD/ACIA ISR entry is event driven, no nominal time to compare against: a byte takes 10,240 cycles at 7812.5 baud and the ACIA holds one received byte, so a burst of <= 1,800 cycles cannot lose bytes by itself [INFERENCE]; the game uses joystick + keys (no mouse packets to clamp; no position clamp added).
**Fidelity limit**: Hatari's blitter is a bus-cycle model (the CPU is stalled for the burst; the interrupt is accepted when it ends). It does not model the real STE bus arbiter, video DMA contention, or the MFP's asynchronous latch of Timer B's data register (a read concurrent with the count edge may return the old count: the guard tolerates a one-line error only with GTH >= 3, which is why the shipped value is 3). **Palette-split integrity per scanline is not proven**: the pixel gates compare the screen buffers (`$70000/$78000`), which contain no per-scanline palette, so they cannot show a delayed split; the argument for it is the ISR entry table above plus the guard's construction (a burst never starts closer than 2 scanlines to the next Timer B event), not a rendered comparison.

### 3.5 Recommendation (decision for the lead)
- **Do not ship HOG without the guard**: -13 k to -17 k, but 3-6 % of the raster interrupts (Hatari: 16-33 of 560) are late by 100-250+ cycles; on a real STE a late `$d616` writes the road/sky palette switch up to 3.5 lines late (visible flicker at the horizon) [INFERENCE: the palette write is at the ISR entry, `$d63a-$d652`].
- Shipped candidate = the guarded variant (`GTH 3`, `BUDGET 900`, minimum rows 16/10/16): -4.3 k to -8.8 k (0.9-2 % of the pass), `default: no`. If the lead wants the blitter at all it is a 1-2 % item; the car cache is 8 %.
- The patch fails safe: probe -> stock kernels; any call that is clipped, aligned, small, 4-column, or off the interior = stock kernel.

## 4. Gates (raw)

### 4.1 Verify (private tool, rd_* at the final `$C0000-$D7FFF`)
```
tb_blit            site $039a0 len 12
tb_blit11          site $039b4 len 12
tb_blit13          site $039c8 len 12
tb_blit15          site $03a18 len 12
tb_car             site $039ac len 4
tb_carph           site $0ed90 len 8
verify: ALL OK
```

### 4.2 Pixels: `tbab.py` = reference set vs reference + patches, both 32,000-byte buffers at the N-th flip after the apply instant (`tools/msrabtest.py` capture), 4 snapshots x flips 10 / 40
**tb_car tb_carph**
```
patched  : +  tb_car tb_carph 
PIXELS race_grid   VBL 25100 flip  10: IDENTICAL  md5 13d1cd99 8e758917 (ref 13d1cd99 8e758917)
PIXELS race_grid   VBL 25100 flip  40: IDENTICAL  md5 a48ac4d2 a48ac4d2 (ref a48ac4d2 a48ac4d2)
PIXELS race_start  VBL 16400 flip  10: IDENTICAL  md5 09c8b376 929fc524 (ref 09c8b376 929fc524)
PIXELS race_start  VBL 16400 flip  40: IDENTICAL  md5 5826bbcb 39e01d6e (ref 5826bbcb 39e01d6e)
PIXELS race_up     VBL 18100 flip  10: IDENTICAL  md5 00b9eaf0 1de22f9b (ref 00b9eaf0 1de22f9b)
PIXELS race_up     VBL 18100 flip  40: IDENTICAL  md5 08c2ceca 1397c0ee (ref 08c2ceca 1397c0ee)
PIXELS race_drive  VBL 15300 flip  10: IDENTICAL  md5 8cecd87b 89266370 (ref 8cecd87b 89266370)
PIXELS race_drive  VBL 15300 flip  40: IDENTICAL  md5 48413685 48413685 (ref 48413685 48413685)
RESULT: ALL IDENTICAL
```

**NEGATIVE control: tb_car tb_carph with the tb_carph site restored to the stock bytes (`--poke ed90=302a0006d06a0008`): wheel-XOR state no longer tracked**
```
patched  : +  tb_car tb_carph   pokes ed90=302a0006d06a0008
PIXELS race_grid   VBL 25100 flip  10: IDENTICAL  md5 13d1cd99 8e758917 (ref 13d1cd99 8e758917)
PIXELS race_grid   VBL 25100 flip  40: IDENTICAL  md5 a48ac4d2 a48ac4d2 (ref a48ac4d2 a48ac4d2)
PIXELS race_start  VBL 16400 flip  10: IDENTICAL  md5 09c8b376 929fc524 (ref 09c8b376 929fc524)
PIXELS race_start  VBL 16400 flip  40: DIFFER (38 bytes of 64000)  md5 0e0f8924 b8eabc40 (ref 5826bbcb 39e01d6e)
PIXELS race_up     VBL 18100 flip  10: IDENTICAL  md5 00b9eaf0 1de22f9b (ref 00b9eaf0 1de22f9b)
PIXELS race_up     VBL 18100 flip  40: IDENTICAL  md5 08c2ceca 1397c0ee (ref 08c2ceca 1397c0ee)
PIXELS race_drive  VBL 15300 flip  10: IDENTICAL  md5 8cecd87b 89266370 (ref 8cecd87b 89266370)
PIXELS race_drive  VBL 15300 flip  40: IDENTICAL  md5 48413685 48413685 (ref 48413685 48413685)
RESULT: DIFFERENCES FOUND
```

**tb_blit* (shipped: guarded)**
```
patched  : +  tb_blit tb_blit11 tb_blit13 tb_blit15 
PIXELS race_grid   VBL 25100 flip  10: IDENTICAL  md5 13d1cd99 8e758917 (ref 13d1cd99 8e758917)
PIXELS race_grid   VBL 25100 flip  40: IDENTICAL  md5 a48ac4d2 a48ac4d2 (ref a48ac4d2 a48ac4d2)
PIXELS race_start  VBL 16400 flip  10: IDENTICAL  md5 09c8b376 929fc524 (ref 09c8b376 929fc524)
PIXELS race_start  VBL 16400 flip  40: IDENTICAL  md5 5826bbcb 39e01d6e (ref 5826bbcb 39e01d6e)
PIXELS race_up     VBL 18100 flip  10: IDENTICAL  md5 00b9eaf0 1de22f9b (ref 00b9eaf0 1de22f9b)
PIXELS race_up     VBL 18100 flip  40: IDENTICAL  md5 08c2ceca 1397c0ee (ref 08c2ceca 1397c0ee)
PIXELS race_drive  VBL 15300 flip  10: IDENTICAL  md5 8cecd87b 89266370 (ref 8cecd87b 89266370)
PIXELS race_drive  VBL 15300 flip  40: IDENTICAL  md5 48413685 48413685 (ref 48413685 48413685)
RESULT: ALL IDENTICAL
```

**tbb_h* (HOG, no cap, experiment)**
```
patched  : +  tbb_h tbb_h11 tbb_h13 tbb_h15 
PIXELS race_grid   VBL 25100 flip  10: IDENTICAL  md5 13d1cd99 8e758917 (ref 13d1cd99 8e758917)
PIXELS race_grid   VBL 25100 flip  40: IDENTICAL  md5 a48ac4d2 a48ac4d2 (ref a48ac4d2 a48ac4d2)
PIXELS race_start  VBL 16400 flip  10: IDENTICAL  md5 09c8b376 929fc524 (ref 09c8b376 929fc524)
PIXELS race_start  VBL 16400 flip  40: IDENTICAL  md5 5826bbcb 39e01d6e (ref 5826bbcb 39e01d6e)
PIXELS race_up     VBL 18100 flip  10: IDENTICAL  md5 00b9eaf0 1de22f9b (ref 00b9eaf0 1de22f9b)
PIXELS race_up     VBL 18100 flip  40: IDENTICAL  md5 08c2ceca 1397c0ee (ref 08c2ceca 1397c0ee)
PIXELS race_drive  VBL 15300 flip  10: IDENTICAL  md5 8cecd87b 89266370 (ref 8cecd87b 89266370)
PIXELS race_drive  VBL 15300 flip  40: IDENTICAL  md5 48413685 48413685 (ref 48413685 48413685)
RESULT: ALL IDENTICAL
```

**NEGATIVE control: tb_blit* with the nibble-7 plane offset poked (`--poke b46d2=0006`)**
```
patched  : +  tb_blit tb_blit11 tb_blit13 tb_blit15   pokes b46d2=0006
PIXELS race_grid   VBL 25100 flip  10: DIFFER (478 bytes of 64000)  md5 a3707f2e 079afa96 (ref 13d1cd99 8e758917)
PIXELS race_grid   VBL 25100 flip  40: IDENTICAL  md5 a48ac4d2 a48ac4d2 (ref a48ac4d2 a48ac4d2)
PIXELS race_start  VBL 16400 flip  10: DIFFER (808 bytes of 64000)  md5 4b7c3471 2a2410f2 (ref 09c8b376 929fc524)
PIXELS race_start  VBL 16400 flip  40: DIFFER (114 bytes of 64000)  md5 4249863b 800609e6 (ref 5826bbcb 39e01d6e)
PIXELS race_up     VBL 18100 flip  10: IDENTICAL  md5 00b9eaf0 1de22f9b (ref 00b9eaf0 1de22f9b)
PIXELS race_up     VBL 18100 flip  40: DIFFER (188 bytes of 64000)  md5 76c67138 997ae224 (ref 08c2ceca 1397c0ee)
PIXELS race_drive  VBL 15300 flip  10: DIFFER (966 bytes of 64000)  md5 7b603c0c c44e08ce (ref 8cecd87b 89266370)
PIXELS race_drive  VBL 15300 flip  40: DIFFER (1572 bytes of 64000)  md5 e2da5db1 e2da5db1 (ref 48413685 48413685)
RESULT: DIFFERENCES FOUND
```

**tb_car tb_carph tb_blit***
```
patched  : +  tb_car tb_carph tb_blit tb_blit11 tb_blit13 tb_blit15 
PIXELS race_grid   VBL 25100 flip  10: IDENTICAL  md5 13d1cd99 8e758917 (ref 13d1cd99 8e758917)
PIXELS race_grid   VBL 25100 flip  40: IDENTICAL  md5 a48ac4d2 a48ac4d2 (ref a48ac4d2 a48ac4d2)
PIXELS race_start  VBL 16400 flip  10: IDENTICAL  md5 09c8b376 929fc524 (ref 09c8b376 929fc524)
PIXELS race_start  VBL 16400 flip  40: IDENTICAL  md5 5826bbcb 39e01d6e (ref 5826bbcb 39e01d6e)
PIXELS race_up     VBL 18100 flip  10: IDENTICAL  md5 00b9eaf0 1de22f9b (ref 00b9eaf0 1de22f9b)
PIXELS race_up     VBL 18100 flip  40: IDENTICAL  md5 08c2ceca 1397c0ee (ref 08c2ceca 1397c0ee)
PIXELS race_drive  VBL 15300 flip  10: IDENTICAL  md5 8cecd87b 89266370 (ref 8cecd87b 89266370)
PIXELS race_drive  VBL 15300 flip  40: IDENTICAL  md5 48413685 48413685 (ref 48413685 48413685)
RESULT: ALL IDENTICAL
```

### 4.3 State per pass (`exp_state_tb.py` = `work/hud/build/exp_state_hd.py` with the private tool; T = tick pacer `mt_sync` set, X = extras set; ranges `$1000-$13ff $29c8-$34ff $4500-$4fff $dae6 $1bb0 $23bc $27c8 $3500-$36ff $b8f38`; `cmpstate_tb.py --mask` = the HUD gate's masks; `$100c` is written like the stock kernel anyway)
tb_car + tb_carph only:
```
car_start_T8_ref.json (203 passes) vs car_start_T8_tb.json (203): common 203 (keys 95..297); 1480682 bytes compared; mask=on (masked differing bytes 0); differing addresses 0, differing bytes 0
car_start_X8_ref.json (203 passes) vs car_start_X8_tb.json (202): common 202 (keys 96..297); 1473388 bytes compared; mask=on (masked differing bytes 10241); differing addresses 0, differing bytes 0
car_start_X16_ref.json (202 passes) vs car_start_X16_tb.json (202): common 202 (keys 109..310); 1473388 bytes compared; mask=on (masked differing bytes 45012); differing addresses 0, differing bytes 0
car_start_X32_ref.json (202 passes) vs car_start_X32_tb.json (202): common 202 (keys 111..312); 1473388 bytes compared; mask=on (masked differing bytes 0); differing addresses 0, differing bytes 0
car_drive_T8_ref.json (278 passes) vs car_drive_T8_tb.json (278): common 278 (keys 0..1706); 2027732 bytes compared; mask=on (masked differing bytes 0); differing addresses 0, differing bytes 0
car_drive_X8_ref.json (279 passes) vs car_drive_X8_tb.json (279): common 278 (keys 0..1706); 2027732 bytes compared; mask=on (masked differing bytes 1664); differing addresses 0, differing bytes 0
car_drive_X16_ref.json (274 passes) vs car_drive_X16_tb.json (275): common 274 (keys 0..1706); 1998556 bytes compared; mask=on (masked differing bytes 0); differing addresses 0, differing bytes 0
car_drive_X32_ref.json (277 passes) vs car_drive_X32_tb.json (278): common 277 (keys 0..1706); 2020438 bytes compared; mask=on (masked differing bytes 0); differing addresses 0, differing bytes 0
```
tb_car tb_carph tb_blit* together (reference = the same car_*_ref runs):
```
car_start_T8_ref.json (203 passes) vs both_start_T8_tb.json (203): common 202 (keys 96..297); 1473388 bytes compared; mask=on (masked differing bytes 606); differing addresses 0, differing bytes 0
car_start_X8_ref.json (203 passes) vs both_start_X8_tb.json (203): common 203 (keys 96..298); 1480682 bytes compared; mask=on (masked differing bytes 11692); differing addresses 0, differing bytes 0
car_start_X16_ref.json (202 passes) vs both_start_X16_tb.json (203): common 202 (keys 109..310); 1473388 bytes compared; mask=on (masked differing bytes 27910); differing addresses 0, differing bytes 0
car_start_X32_ref.json (202 passes) vs both_start_X32_tb.json (203): common 201 (keys 112..312); 1466094 bytes compared; mask=on (masked differing bytes 603); differing addresses 0, differing bytes 0
car_drive_T8_ref.json (278 passes) vs both_drive_T8_tb.json (279): common 277 (keys 0..1706); 2020438 bytes compared; mask=on (masked differing bytes 165); differing addresses 0, differing bytes 0
car_drive_X8_ref.json (279 passes) vs both_drive_X8_tb.json (278): common 278 (keys 0..1706); 2027732 bytes compared; mask=on (masked differing bytes 1499); differing addresses 0, differing bytes 0
car_drive_X16_ref.json (274 passes) vs both_drive_X16_tb.json (275): common 273 (keys 0..1706); 1991262 bytes compared; mask=on (masked differing bytes 1126); differing addresses 0, differing bytes 0
car_drive_X32_ref.json (277 passes) vs both_drive_X32_tb.json (278): common 276 (keys 0..1706); 2013144 bytes compared; mask=on (masked differing bytes 156); differing addresses 0, differing bytes 0
```

### 4.4 Emulator (Unicorn, exact 68000 model; `emucmp.py`): reference vs patched live image, every byte below `$80000` per pass, masks = `$100c`, kernel area `$12000-$16000` (self-modified immediates), stack gap, patch sites
```
== tb_car+tb_carph, full RAM < $80000 per pass (screens included), INIT poked to 1
L0.bin zig 100 passes: differing unmasked addresses 0 INIT 1 NENT 19 POOLP 0xdca9a 
L0.bin up 100 passes: differing unmasked addresses 0 INIT 1 NENT 5 POOLP 0xd9e42 
L1.bin zig 100 passes: differing unmasked addresses 0 INIT 1 NENT 20 POOLP 0xdd75e 
L1.bin up 100 passes: differing unmasked addresses 0 INIT 1 NENT 7 POOLP 0xdab34 
L2.bin zig 100 passes: differing unmasked addresses 0 INIT 1 NENT 13 POOLP 0xdca9a 
L2.bin up 100 passes: differing unmasked addresses 0 INIT 1 NENT 3 POOLP 0xd917e 
L3.bin zig 100 passes: differing unmasked addresses 0 INIT 1 NENT 13 POOLP 0xdca9a 
L3.bin up 100 passes: differing unmasked addresses 0 INIT 1 NENT 5 POOLP 0xd9e42 
L4.bin zig 100 passes: differing unmasked addresses 0 INIT 1 NENT 20 POOLP 0xdd57c 
L4.bin up 100 passes: differing unmasked addresses 0 INIT 1 NENT 7 POOLP 0xdab34 
L5.bin zig 100 passes: differing unmasked addresses 0 INIT 1 NENT 12 POOLP 0xdcd16 
L5.bin up 100 passes: differing unmasked addresses 0 INIT 1 NENT 5 POOLP 0xda210 
L6.bin zig 100 passes: differing unmasked addresses 0 INIT 1 NENT 17 POOLP 0xdd7e4 
L6.bin up 100 passes: differing unmasked addresses 0 INIT 1 NENT 7 POOLP 0xdae42 
L7.bin zig 100 passes: differing unmasked addresses 0 INIT 1 NENT 15 POOLP 0xdd7e0 
L7.bin up 100 passes: differing unmasked addresses 0 INIT 1 NENT 7 POOLP 0xdae42 
L8.bin zig 100 passes: differing unmasked addresses 0 INIT 1 NENT 11 POOLP 0xdc46a 
L8.bin up 100 passes: differing unmasked addresses 0 INIT 1 NENT 7 POOLP 0xdae42 
L9.bin zig 100 passes: differing unmasked addresses 0 INIT 1 NENT 12 POOLP 0xdcf74 
L9.bin up 100 passes: differing unmasked addresses 0 INIT 1 NENT 5 POOLP 0xda210 
L10.bin zig 100 passes: differing unmasked addresses 0 INIT 1 NENT 21 POOLP 0xdd31e 
L10.bin up 100 passes: differing unmasked addresses 0 INIT 1 NENT 7 POOLP 0xdb056 
L11.bin zig 100 passes: differing unmasked addresses 0 INIT 1 NENT 26 POOLP 0xdd682 
L11.bin up 100 passes: differing unmasked addresses 0 INIT 1 NENT 7 POOLP 0xdb056 
L12.bin zig 100 passes: differing unmasked addresses 0 INIT 1 NENT 23 POOLP 0xdd65c 
L12.bin up 100 passes: differing unmasked addresses 0 INIT 1 NENT 7 POOLP 0xdb056 
L13.bin zig 100 passes: differing unmasked addresses 0 INIT 1 NENT 23 POOLP 0xdd11c 
L13.bin up 100 passes: differing unmasked addresses 0 INIT 1 NENT 7 POOLP 0xdb056 
L14.bin zig 100 passes: differing unmasked addresses 0 INIT 1 NENT 28 POOLP 0xdd00c 
L14.bin up 100 passes: differing unmasked addresses 0 INIT 1 NENT 9 POOLP 0xdb9b0 
== same, h_*_7a88 dumps
h_start_7a88.bin zig 100 passes: differing unmasked addresses 0 INIT 1 NENT 18 POOLP 0xdcbb6 
h_up_7a88.bin zig 100 passes: differing unmasked addresses 0 INIT 1 NENT 25 POOLP 0xdd5dc 
h_grid_7a88.bin zig 100 passes: differing unmasked addresses 0 INIT 1 NENT 2 POOLP 0xd904a 
(h_drive_7a88.bin: the REFERENCE run itself stops at $72da, the race ends in that dump: not a patch effect)

== tb_blit (blits are no-ops in Unicorn: logic state only, BST=1, TBCR=8/TBDR=1 so the guard spin runs)
L0.bin zig 100 passes: differing unmasked addresses 0
L3.bin zig 100 passes: differing unmasked addresses 0
L5.bin zig 100 passes: differing unmasked addresses 0
L8.bin zig 100 passes: differing unmasked addresses 0
L12.bin zig 100 passes: differing unmasked addresses 0
L14.bin zig 100 passes: differing unmasked addresses 0
h_start_7a88.bin zig 100 passes: differing unmasked addresses 0
h_up_7a88.bin zig 100 passes: differing unmasked addresses 0
h_grid_7a88.bin zig 100 passes: differing unmasked addresses 0
(h_drive_7a88.bin: the REFERENCE run itself stops at $72da, the race ends in that dump: not a patch effect)
== both, logic state
L0.bin zig 100 passes: differing unmasked addresses 0
L5.bin zig 100 passes: differing unmasked addresses 0
L12.bin zig 100 passes: differing unmasked addresses 0
hit ratio of the car cache (draw of slot $2c68/$3480 through the stub; HIT = generated code executed, MISS = stock kernel after a lookup, GEN = create calls) over 600 passes, 24 KB pool; Unicorn, INIT poked to 1
L14 zig     passes 600 stub entries 1271 compiled draws 788 (62.0 %) generations 39 NENT 39 POOLP 0xdd00c
L11 zig     passes 600 stub entries 1290 compiled draws 606 (47.0 %) generations 39 NENT 39 POOLP 0xdd682
L12 zig     passes 600 stub entries 1266 compiled draws 842 (66.5 %) generations 39 NENT 39 POOLP 0xdd65c
L5 zig     passes 600 stub entries 1273 compiled draws 783 (61.5 %) generations 17 NENT 17 POOLP 0xdcd16
L14 upleft  passes 600 stub entries 1264 compiled draws 858 (67.9 %) generations 30 NENT 30 POOLP 0xdd55c
L12 up      passes 600 stub entries 1272 compiled draws 1200 (94.3 %) generations 9 NENT 9 POOLP 0xdbbf4
```

### 4.5 Cold boots and 2-minute drive (`tb_drive.py`: cold boot, SPACE into the race, Up held 6,100 VBL; build `work/tightB/build/hd_tb` = default HD set + `tb_*`)
**STE TOS 1.62, 1 MB**
```
in_race True vbl 5808
marker $b2700: 000B2700: 4d 53 50 4f 00 00 00 00                          MSPO....
after SPACE: $100e 0
(581, 2, 143, 1, 4, 1, 928)   (vbl, mode, pass, INIT, NENT, BST, pos)
(1342, 2, 295, 1, 8, 1, 2448)   (vbl, mode, pass, INIT, NENT, BST, pos)
(2103, 2, 447, 1, 8, 1, 3649)   (vbl, mode, pass, INIT, NENT, BST, pos)
(2864, 2, 600, 1, 8, 1, 4778)   (vbl, mode, pass, INIT, NENT, BST, pos)
(3625, 2, 752, 1, 8, 1, 5830)   (vbl, mode, pass, INIT, NENT, BST, pos)
(4386, 2, 904, 1, 8, 1, 6880)   (vbl, mode, pass, INIT, NENT, BST, pos)
(5146, 2, 1056, 1, 8, 1, 7940)   (vbl, mode, pass, INIT, NENT, BST, pos)
(5907, 2, 1208, 1, 8, 1, 8992)   (vbl, mode, pass, INIT, NENT, BST, pos)
tb_car: INIT/LASTP/POOLP/NENT: 000BF000: 01 00 04 de 00 0d b0 52 00 08 00 c0 00 18 00 00  ...∧..ãR...ĳ....
tb_blit BST: 000B5800: 01 00 00 00 00 07 7f d0                          .......ס
alive, pass counter: 1262
```

**STE TOS 1.62, 4 MB (pp_bigram_cache in the build)**
```
in_race True vbl 5809
marker $b2700: 000B2700: 4d 53 50 4f 00 00 00 00                          MSPO....
after SPACE: $100e 0
(581, 2, 144, 1, 4, 1, 938)   (vbl, mode, pass, INIT, NENT, BST, pos)
(1342, 2, 296, 1, 8, 1, 2458)   (vbl, mode, pass, INIT, NENT, BST, pos)
(2103, 2, 448, 1, 8, 1, 3656)   (vbl, mode, pass, INIT, NENT, BST, pos)
(2864, 2, 600, 1, 8, 1, 4778)   (vbl, mode, pass, INIT, NENT, BST, pos)
(3625, 2, 753, 1, 8, 1, 5837)   (vbl, mode, pass, INIT, NENT, BST, pos)
(4386, 2, 905, 1, 8, 1, 6887)   (vbl, mode, pass, INIT, NENT, BST, pos)
(5147, 2, 1057, 1, 8, 1, 7947)   (vbl, mode, pass, INIT, NENT, BST, pos)
(5908, 2, 1209, 1, 8, 1, 8999)   (vbl, mode, pass, INIT, NENT, BST, pos)
tb_car: INIT/LASTP/POOLP/NENT: 000BF000: 01 00 04 df 00 0d b0 52 00 08 00 c0 00 18 00 00  ...∞..ãR...ĳ....
tb_blit BST: 000B5800: 01 00 00 00 00 07 7f d0                          .......ס
alive, pass counter: 1263
```

## 5. What failed / was fixed
- First car cache keyed by pointer only: bottom rows of the car wrong (wheel XOR) -> label + hook.
- First `create` wrote to address 0 when the pool pointer was uninitialised (emulator test with `INIT` poked) -> lazy init.
- Blitter router passed `rows <= 0` to the blitter (race_up crash) -> `tst.w d7 / ble`.
- `GUARD` spun forever per pass because Timer B is stopped after the last band (TBDR stays 1: +250 k cycles/pass) -> test `TBCR`.
- The first blitter gate harness used `$ed6e`; MSRTightC's note (tc_ord bypasses `$ecc8`): moved to the table entries.

## 6. Unproven / not done
- Real hardware (STE with blitter): nothing here runs on one. Burst/ISR statements are Hatari + reasoning; palette-split integrity per scanline is NOT proven (section 3.4).
- Mega STE, TT, Falcon, ST: the probes select the stock kernels; the probe paths themselves were run on Hatari STE only (68000 `move.w ccr` illegal and `$ff8e21` bus error observed on Hatari STE; the 68010+ and Mega STE branches were not executed).
- 60 Hz: not re-run (the patches do not depend on the VBL rate).
- Pool pressure with the 24 KB pool over a long race with continuous steering: the generator falls back to the stock kernel when full; a long-run census was not done (cold boot drive + state gates only).
- Blitter on the 3-part composites (`$15442`, ~45 k per pass) and 4 columns: not attempted.
