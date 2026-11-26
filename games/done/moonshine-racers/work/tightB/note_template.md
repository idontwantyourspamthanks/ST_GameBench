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
- **Cold cost** (generation, once per variant and state, inside the draw that needs it): {{carcost}}
- It is paid lazily during the first passes of a race (and after a restart); no pre-warm site was used because the variant (frame, size, x shift) is only known when the car is drawn. A pass that generates one variant is ~0.4 VBL longer than usual, i.e. inside the 5 VBL tick of the fixed-tick pacer (it never causes an overrun by itself at 8 MHz: 3.06 + 0.4 < 5); two variants in one pass (car + layer) ~0.7 VBL.
- Pool pressure: an emulator run (`L12.bin`, 'zig' steering, 400 passes) filled 23 entries and ~38 KB with the 48 KB pool before the chunk sharing; with sharing and the 24 KB pool see "unproven" (section 6).

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
{{cyc_table}}

Gain at several caps (race_start, race_grid, race_up; no speech; ISR-safety in the last column):
| variant | start | standing | race_up | raster interrupt delay |
|---|---|---|---|---|
| HOG, no cap (`BUDGET 1800`) | -17.0 k | -12.6 k | -14.9 k | up to ~1,800 cycles (3.5 lines) [INFERENCE from burst length; Hatari: section 3.4] |
| cap 800 | -14.6 k | -12.3 k | -9.9 k | up to ~800 |
| cap 400 (first-run router build) | -3.2 k | -5.3 k | n/a | up to ~400 |
| cap 200 (first-run router build) | **+30.2 k** | **+16.0 k** | n/a | up to ~200 |
| **TB guard, GTH 3, 900 (shipped)** | **-4.3 k** | **-8.8 k** | **-8.2 k** | 0 for Timer B by construction; VBL ISR up to the burst (measured +240 cycles) |
| TB guard, GTH 2, 440 (first-run) | +7.6 k | +3.5 k | n/a | 0 |
| TB guard, GTH 4, 1400 (first-run) | -6.0 k | -1.3 k | n/a | 0 |
(the caps 400/200/GTH-2/GTH-4 rows come from the first-run router build, `res/cyc_race_*_base+tbb_*.json`, same measurement method; the table-stub build was re-measured for HOG, 800 and the shipped variant.)

### 3.3 Why the cap loses: a pass costs ~100-250 cycles of CPU register writes whatever its length, 10-12 passes per sprite part; shortening the burst multiplies the passes (cap 200: 5-8 rows per pass). The guard loses the rest to the 25-50 % of the time in which the pass must wait for the raster interrupt (the CPU is idle while spinning).

### 3.4 ISR entry latency (Hatari, `work/tightB/isrlat.py`: persistent trace breakpoints on `$d616` Timer B, `$d11e` VBL, `$cfb4` IKBD; `e LineCycles` / `e FrameCycles`; 1,500 VBL of the driving snapshot, ~560 raster entries, 60 VBL entries per variant)
{{isr_table}}
Reading: nominal raster entry is LineCycles ~464 (end of line); `late` = `((LineCycles - 480 + 256) mod 512) - 256`. **Hatari does delay the interrupts during a HOG burst** (33 of 560 raster interrupts > 100 cycles late with HOG, max >= 250, the later ones alias past one line; VBL ISR entry up to 400-508 against 148); the guarded variant has **no** raster interrupt later than the baseline's own jitter (max 72) and the VBL ISR entry moves up to 388 (a 900-cycle burst; the VBL handler has ~32,000 cycles of margin before the first displayed line [INFERENCE: line 63 of 313 at 512 cycles]). The IKBD/ACIA ISR entry is event driven (no nominal time): a byte takes 10,240 cycles at 7812.5 baud and the ACIA buffers one byte, so a burst <= 1,800 cycles cannot lose bytes by itself [INFERENCE, not measurable here]; the game uses joystick + keys (no mouse packets to clamp).
**Fidelity limit**: Hatari's blitter is a bus-cycle model (CPU stalled for the burst, interrupts accepted when the burst ends); it does not model the real STE bus arbiter, the 68000's `TAS`/RMW atomicity interplay, the MFP's asynchronous latch of Timer B's data register (a read concurrent with the count edge may return the old count: the guard tolerates a one-line error only with GTH >= 3), nor video DMA contention. The raster palette split (`$d616`: 7 palette longs written at entry, no beam sync) was therefore compared by entry timing, not by pixels: a pixel/palette A/B cannot show a delayed split in the emulator because the blitter patches are pixel-identical by construction and Hatari does render the late palette at its (late) cycle: the A/B pictures are IDENTICAL because the snapshot frames are captured from the buffers (`$70000/$78000`), not from the rendered video (palette-per-scanline is not in the buffers). Palette-split integrity is therefore argued from the ISR entry numbers above, not proven per scanline.

### 3.5 Recommendation (decision for the lead)
- **Do not ship HOG without the guard**: -13 k to -17 k, but ~6 % of the raster interrupts (Hatari) are late by 100-250+ cycles; on a real STE a late `$d616` writes the road/sky palette switch up to 3.5 lines late (visible flicker at the horizon) [INFERENCE: the palette write is at the ISR entry, `$d63a-$d652`].
- Shipped candidate = the guarded variant (`GTH 3`, `BUDGET 900`, minimum rows 16/10/16): -4.3 k to -8.8 k (0.9-2 % of the pass), `default: no`. If the lead wants the blitter at all it is a 1-2 % item; the car cache is 8 %.
- The patch fails safe: probe -> stock kernels; any call that is clipped, aligned, small, 4-column, or off the interior = stock kernel.

## 4. Gates (raw)

### 4.1 Verify (private tool, rd_* at the final `$C0000-$D7FFF`)
{{verify}}

### 4.2 Pixels: `tbab.py` = reference set vs reference + patches, both 32,000-byte buffers at the N-th flip after the apply instant (`tools/msrabtest.py` capture), 4 snapshots x flips 10 / 40
{{pix}}

### 4.3 State per pass (`exp_state_tb.py` = `work/hud/build/exp_state_hd.py` with the private tool; T = tick pacer `mt_sync` set, X = extras set; ranges `$1000-$13ff $29c8-$34ff $4500-$4fff $dae6 $1bb0 $23bc $27c8 $3500-$36ff $b8f38`; `cmpstate_tb.py --mask` = the HUD gate's masks; `$100c` is written like the stock kernel anyway)
{{state}}

### 4.4 Emulator (Unicorn, exact 68000 model; `emucmp.py`): reference vs patched live image, every byte below `$80000` per pass, masks = `$100c`, kernel area `$12000-$16000` (self-modified immediates), stack gap, patch sites
{{emu}}

### 4.5 Cold boots and 2-minute drive (`tb_drive.py`: cold boot, SPACE into the race, Up held 6,100 VBL; build `work/tightB/build/hd_tb` = default HD set + `tb_*`)
{{boots}}

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
