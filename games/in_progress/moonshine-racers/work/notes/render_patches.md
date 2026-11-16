# Moonshine Racers: pixel-identical render patches `mr_edge`, `mr_map`, `mr_digit` (wave 2 of the speed-up plan)

Goal (rendering.md section 6, tick.md): cut the raw work per pass below the fixed tick so that T can drop from 36 (6 VBL, 8.33 passes/s) towards 30 (5 VBL, 10 passes/s).
Everything here is **byte-identical output** (same screen memory, same per-pass game state); nothing is visible, nothing is a trade-off.
Machine: Hatari 2.6.1 STE, TOS 1.62, 1 MB, 8.02 MHz, 50 Hz. Disassembly lines are from `tools/m68dis.py` on `work/dumps/ram_race_start.bin`;
gate outputs are pasted raw from `work/render/logs/`. Unproven statements are marked **[INFERENCE]**.

## 0. Result in one table

Cycles of raw work per pass = loop top `$796a` to flip entry `$d1ca` (interrupts included, the idle wait after the flip excluded), the same passes (key `$100e`)
of stock and patched game, tick patches (`mt_*`) OFF, `work/render/work_live.py` (raw: `logs/work_cum.txt`, `logs/work_up_drive.txt`). 160,256 cycles = 1 VBL.

| scene | stock | + mr_edge | + mr_map | + mr_digit (all three) | saving |
|---|---:|---:|---:|---:|---:|
| race_start (driving) | 843,983 = 5.266 VBL | 793,501 = 4.951 | 772,673 = 4.821 | **757,788 = 4.729 VBL** | 86,195 = **10.2 %** |
| race_grid (standing) | 762,256 = 4.756 VBL | 720,107 = 4.493 | 700,168 = 4.369 | **700,168 = 4.369 VBL** | 62,088 = 8.1 % (no digits redraw standing) |
| race_up (mid race) | 831,203 = 5.187 VBL | | | 755,920 = 4.717 VBL | 75,283 = 9.1 % |
| race_drive (mid race) | 815,853 = 5.091 VBL | | | 736,590 = 4.596 VBL | 79,263 = 9.7 % |

Per item, driving (race_start): `mr_edge` -51,244 cycles (6.1 %), `mr_map` -20,066 more, `mr_digit` -14,885 more; cumulative -86,195 (10.2 %).
Standing (race_grid): `mr_edge` -42,149, `mr_map` -19,939 more, `mr_digit` 0 (the score does not change).
Worst single pass driving (race_start, 58 passes): stock max 895,356 = 5.59 VBL; all three on: max 809,640 = 5.05 VBL, mean 760,181 = 4.744 VBL.

**T = 30 is reachable at 8 MHz** (mean work 4.73 VBL < 5 VBL; the worst single passes of a long drive can still exceed 5 VBL by about 1 %, then that pass
simply runs late and the tick pacer re-syncs: no burst). Measured with the tick patches at TICK 30 (a scratch copy of `mt_sync.s` in `work/render/patches30/`, not shipped),
pass rate over 600 VBL (`work/render/rate30.py`, raw `logs/rate_t30.txt`):
```
race_start T=30 mt_clock mt_sync mt_pre:                       112 passes / 600 VBL =  9.333 pass/s (5.357 VBL/pass)   <- stock render: overloaded
race_start T=30 mt_clock mt_sync mt_pre mr_edge mr_map mr_digit: 121 passes / 600 VBL = 10.083 pass/s (4.959 VBL/pass)  <- on schedule (window edge +-1)
race_grid  T=30 mt only: 120 = 10.000 pass/s;   with mr_*: 120 = 10.000 pass/s
race_up    T=30 mt only: 115 passes = 9.583 pass/s;  with mr_*: 121 = 10.083 pass/s
```
(race_drive is a snapshot taken at the time-out: it restarts the race inside the window and runs 5.1 pass/s at T=36 as well: `rate30.py race_drive 36 ...` = 5.167; ignore it for rates.)

## 1. Method and tools

- `tools/msrabtest.py --only P... [--snapshots race_grid race_start race_up race_drive] [--flips 10 40] [--state N] [--rate] [--poke addr=hex]`: per snapshot, stock vs patched
  (`msrpatch.py live`, applied at the first flip `$d1ca` after a fixed VBL) both screen buffers (`$70000`, `$78000`, visible 32,000 B each) md5-compared at flip N; `--state N`
  dumps at every `$7b86` (first instruction after the flip) `$1000-$13ff`, `$29c8-$34ff` (object slots), `$4500-$4fff` (road geometry tables), `$dae6` (RNG), keyed by `$100e`,
  stock vs patched: every common pass must agree on every byte; `--poke` writes extra bytes in both runs (used for the `$11c6` colour variant of `mr_digit`).
  Base captures are cached in `work/render/ab/base/`. Exit status 0 = identical. One Hatari at a time. Negative control: `patches/mr_negctl.s` (default no).
- `work/render/work_live.py`: raw cycles per pass keyed by `$100e` (`b pc=$796a` / `b pc=$d1ca` one-shot chain with `e VBL`, `e FrameCycles`, wrap offset fitted as in `tools/msrstages.py`:
  0 violations in every run). `work/render/prof_live.py`: Hatari instruction profile of a patched snapshot. `work/render/run_unit.py` + `test_*.s`: unit tests inside a snapshot (section 6).
- `work/render/msrpatch_priv.py` is a private copy of `tools/msrpatch.py` (two lines changed: ROOT, `MSR_PATCHDIR` override) used while the tool was being edited by another agent; the gates also run with the real tool
  (`python3 tools/msrpatch.py list|verify|build` = ALL OK; build `build/render_default`).

Negative control (raw, `--only mr_negctl`: `$1058e move.l d4,d1` -> `move.l d3,d1`):
```
PIXELS race_start  at VBL 16400 flip  10: DIFFER (1712 bytes of 64000)  md5 61a3dd16 78c0a017 (stock 3da506a7 c54efba9)
RESULT: DIFFERENCES FOUND
```

## 2. `mr_edge` (site `$17c4a`, blob `$B3040`): road edge colour expansion `$1058a`

**Routine.** The road span draw `$17c42` calls the edge routine through `jsr (a4)` (a4 = `$1058a`, set by `017c4a: 49f90001058a lea.l $1058a.l,a4`) 153.2 times a pass
(`$1058a movem.l d1/d3,-(a7)`: n=4443 in 29 frames, `work/prof/race_start.txt`). Inputs d4,d5,d6 (three span plane words/longs), d7 (bits 15/14/13 select colour groups), a5 = the colour table
(`$135a` holds the pointer, `$102ba` + 48 B per scheme: 24 words, each 0 or `$ffff`, `m`: `0000 ffff ffff ffff ...`). Outputs d0,d2,d4,d6 = four plane longs:
```
01058a: movem.l d1/d3,-(a7) / 01058e: move.l d4,d1 / 010590: move.l d6,d3 / moveq #0 x4
01059a: tst.w d7 / 01059c: bmi.w $106a8            ; d7 bit 15: group A at (a5)+0 or +8
0105a0: tst.w (a5) / beq.b $105a6 / 0105a4: move.l d1,d0 ... (4 tests: d0,d2,d4,d6 = d1 or 0)
0105be: btst.b #$d,d7 / 0105c2: bne.b $10636       ; bit 13: group B at $20.. or $28.. ORed in from d5
0105e4: btst.b #$e,d7 / 0105e8: bne.b $10610       ; bit 14: group C at $10.. or $18.. ORed in from d3
```
12 `tst.w d16(a5)` + `beq` and 8 `or.l/move.l` per call: about 440 cycles (24 for the `movem`, `rts` 16, jsr 16 included). Table is a constant of the level colour scheme.

**Change.** Output k (d0,d2,d4,d6) = (A_k ? in4) | (B_k ? in5) | (C_k ? in6) with flags from the table words and d7 bits 15,14,13 (8 combinations).
The hook at `$17c4a` (replaces the `lea`; sets a4 itself) checks `$135a` against the last table pointer and, if it changed, **generates 8 slots of 32 bytes**
(straight-line `move.l/or.l/moveq` code, `move.l d1,-(a7)` ... `move.l d1,d4 / move.l (a7)+,d1 / rts`: d1 holds output 4 while d4/d6 are still inputs) and flushes the 68020+ caches
(copy of `core.s cflush`). The new routine at a4 does `move.w d7,d0 / lsr.w #8,d0 / and.w #$e0,d0 / jmp slots(pc,d0.w)`. The stock routine is untouched: the reload at `018040: movea.l $1356.l,a4`
(`$1356` = `$1058a`) and `movea.l $135e.l,a5` still gets the stock routine together with its a5 (never executed in the 29 profiled frames: no `$18040` line in the profile). d1,d3,d5,d7,a-regs are preserved, only d0/d2/d4/d6 change, as in the stock routine; flags are not live (every `jsr (a4)` return is followed by `movem.w`/`cmpi`).
Cost per call about 16 + 48 + 12 + ops + 12 + 16 = ~150 cycles. **[INFERENCE]** The generated slots are only regenerated when `$135a` changes: valid because the 15 tables are static data in the code image; checked after the 2-minute drive (section 5).

**Gates (raw, `logs/gate_edge.txt`):**
```
patch set: mr_edge  (live image edge.img, 22784 B)
PIXELS race_grid   at VBL 25100 flip  10: IDENTICAL  md5 81dfec87 d5a188cf (stock 81dfec87 d5a188cf)
PIXELS race_grid   at VBL 25100 flip  40: IDENTICAL  md5 7481e0c7 7481e0c7 (stock 7481e0c7 7481e0c7)
STATE  race_grid  : stock 109 passes, patched 100, common 100; differing bytes 0 at 0 addresses
PIXELS race_start  at VBL 16400 flip  10: IDENTICAL  md5 3da506a7 c54efba9 (stock 3da506a7 c54efba9)
PIXELS race_start  at VBL 16400 flip  40: IDENTICAL  md5 90858e13 4858b4b8 (stock 90858e13 4858b4b8)
STATE  race_start : stock 100 passes, patched 107, common 95; differing bytes 0 at 0 addresses
PIXELS race_up     at VBL 18100 flip  10: IDENTICAL  md5 64f19a1d d9cdbe0a (stock 64f19a1d d9cdbe0a)
PIXELS race_up     at VBL 18100 flip  40: IDENTICAL  md5 58491371 19ced56f (stock 58491371 19ced56f)
STATE  race_up    : stock 100 passes, patched 107, common 94; differing bytes 0 at 0 addresses
PIXELS race_drive  at VBL 15300 flip  10: IDENTICAL  md5 d67d147e ed8944f1 (stock d67d147e ed8944f1)
PIXELS race_drive  at VBL 15300 flip  40: IDENTICAL  md5 3d3df84c 3d3df84c (stock 3d3df84c 3d3df84c)
STATE  race_drive : stock 108 passes, patched 101, common 101; differing bytes 0 at 0 addresses
RESULT: ALL IDENTICAL
```
Unit test (`work/render/test_edge.s`, `run_unit.py`, raw `logs/unit_edge.txt`): inside the snapshot, stock `jsr $1058a.l` and the generated routine (`jsr (a4)`) are called with the same random d0-d7 (random 32-bit d4,d5,d6,d1,d3,d0,d2,d7 with each of the 8 bit combinations of d7 bits 15-13), for the game's 15 colour tables and 200 random tables (words 0 or random nonzero); all of d0-d7 compared:
```
> m $c4100 20     (cases)  $C4100 = 0x00006b80 = 27520 comparisons,  $C4104 = 0 mismatches            (negative control: input d5 corrupted for the fast call only: $C4104 = 0x6b80 = 27520 mismatches)
```
Gain: -51,244 cycles/pass driving (6.1 %), -42,149 standing (5.5 %): edge `$1058a` cost 64,950 cycles/pass in the profile (`work/render/prof/start_stock.txt`) -> the blob costs about 16-19 k.

## 3. `mr_map` (site `$126d4`, blob `$B3400`): minimap bitmap `$12690`

**Routine.** The minimap `$f22c` calls `$12690` once (`00f34a: jsr $12690.l`, d2 = 1: `00f33e: moveq #$1,d2`, d7 = `$30` rows). It ANDs/ORs a 1-bit shape (a1) into the four screen planes of 3 sixteen-pixel groups per row:
```
0126da: movea.l a3,a0 / 0126dc: moveq #$2,d6
0126de: move.w (a1)+,d1 / 0126e0: move.w d1,d3 / 0126e2: not.w d3
0126e4: btst.b #$0,d2 / 0126e8: bne.b $126ee / 0126ea: and.w d3,(a0)+ / bra.b $126f0 / 0126ee: or.w d1,(a0)+     ; x4 planes (bits 0..3 of d2)
012714: dbra d6,$126de / 012718: lea.l $a0(a3),a3 / 01271c: adda.w d0,a1 / 01271e: dbra d7,$126da
```
`btst` + branch per plane and group: about 176 cycles per group, 144 groups: `$12690` = 30,609 cycles/pass (profile `map $12690`).
**Change.** Site `$126d4` (`subi.w #6,d0 / subq.w #1,d7`, 6 bytes; the loop tops `$126da`/`$126de` are untouched) -> `jmp $B3400.l`; the blob replays the two instructions, jumps through a 16-entry table indexed by `d2 & 15` to one of 16 unrolled row loops (plane op fixed per variant: `or.w d1,(a0)+` or `and.w d3,(a0)+`, 3 groups unrolled), generated by a macro. Every `d2` value is implemented (no fallback). It ends exactly like the stock routine: d6 = `$0000ffff`, d7.w = `$ffff` (same `dbra`), a0 after the last group, a3, a1, d1/d3 = last word and its complement. About 306 cycles per row instead of 560.

**Gates (raw, `logs/gate_map.txt`):**
```
patch set: mr_map  (live image map.img, 22784 B)
PIXELS race_grid   at VBL 25100 flip  10: IDENTICAL  md5 81dfec87 d5a188cf (stock 81dfec87 d5a188cf)
PIXELS race_grid   at VBL 25100 flip  40: IDENTICAL  md5 7481e0c7 7481e0c7 (stock 7481e0c7 7481e0c7)
STATE  race_grid  : stock 109 passes, patched 100, common 100; differing bytes 0 at 0 addresses
PIXELS race_start  at VBL 16400 flip  10: IDENTICAL  md5 3da506a7 c54efba9 (stock 3da506a7 c54efba9)
PIXELS race_start  at VBL 16400 flip  40: IDENTICAL  md5 90858e13 4858b4b8 (stock 90858e13 4858b4b8)
STATE  race_start : stock 100 passes, patched 101, common 95; differing bytes 0 at 0 addresses
PIXELS race_up     at VBL 18100 flip  10: IDENTICAL  md5 64f19a1d d9cdbe0a (stock 64f19a1d d9cdbe0a)
PIXELS race_up     at VBL 18100 flip  40: IDENTICAL  md5 58491371 19ced56f (stock 58491371 19ced56f)
STATE  race_up    : stock 100 passes, patched 108, common 95; differing bytes 0 at 0 addresses
PIXELS race_drive  at VBL 15300 flip  10: IDENTICAL  md5 d67d147e ed8944f1 (stock d67d147e ed8944f1)
PIXELS race_drive  at VBL 15300 flip  40: IDENTICAL  md5 3d3df84c 3d3df84c (stock 3d3df84c 3d3df84c)
STATE  race_drive : stock 108 passes, patched 102, common 102; differing bytes 0 at 0 addresses
RESULT: ALL IDENTICAL
```
The scenes only use `d2 = 1`; the other 15 plane combinations are covered by the unit test below (section 6). Gain: -20,066 cycles/pass driving, -19,939 standing (`$12690` 30.6 k -> ~11 k).

## 4. `mr_digit` (site `$14d98`, blob `$B3C00`): HUD score/time glyph kernel `$14d98`

**Routine.** `$11d42` (called by `$f3de`, `00f428: jsr $11d42.l`, the score redraw whenever `$11c2` changed = every pass while driving) draws each character with `00011db8: jsr $14d98.l`; `$14d98` converts a glyph byte pair (d1 shape, d2 shadow) into four plane bytes per row, one `btst`/`sne`/`btst`/`beq`/`or`... group per plane (colour d4 = `$cd`, or `$c7` if `$11c6`: `00f412: move.w #$cd,d4 / 00f41a: beq / 00f41c: move.w #$c7,d4`):
```
014d9c: move.b (a1)+,d1 / 014d9e: move.b (a1)+,d2 / 014da0: move.b d1,d0 / 014da2: and.b d2,d0
014da4: btst.b #$0,d4 / 014da8: sne.b d3 / 014daa: and.b d1,d3 / 014dac: btst.b #$4,d4 / 014db0: beq.b $14db4 / 014db2: or.b d2,d3 / 014db4: or.b d0,d3 / 014db6: move.b d3,(a4)   ; x4 planes (bits n, n+4)
014dfa: lea.l $a0(a4),a4 / 014dfe: dbra d7,$14d9c / 014e02..: a3 = (a3+7) & ~6 ... rts
```
(about 270 cycles per row; 5 characters x ~15 rows.) Because d1&d2 is contained in d1 and in d2, each plane byte is one of d1, d2, d1&d2 or d1|d2 and for the two colours the choice is constant: `$cd` -> d1, d1&d2, d1|d2, d1|d2; `$c7` -> d1, d1, d1|d2, d2.
**Change.** Site `$14d98` (`subq.w #1,d7 / movea.l a3,a4 / move.b (a1)+,d1`, 6 bytes; **the stock loop top `$14d9c` lies inside these bytes**, so the blob carries a verbatim copy of the stock loop for every other d4: `$14d98` is also reached by `0122dc: jmp $14d98.l`) -> `jmp $B3C00.l`;
the blob tests d4.b against `$cd`/`$c7` and runs 94-cycle row loops with byte operations only (d0-d3 low bytes end like the stock ones), then the stock tail (`move.l a3,d0 / addq.l #7,d0 / andi.w #$fff9,d0 / movea.l d0,a3`).

**Gates (raw, `logs/gate_digit.txt`, `logs/gate_digit_c7.txt`):**
```
patch set: mr_digit  (live image digit.img, 22784 B)
PIXELS race_grid   at VBL 25100 flip  10/40: IDENTICAL (81dfec87 d5a188cf / 7481e0c7 7481e0c7)      STATE race_grid : common 103; differing bytes 0
PIXELS race_start  at VBL 16400 flip  10/40: IDENTICAL (3da506a7 c54efba9 / 90858e13 4858b4b8)      STATE race_start: common 95; differing bytes 0
PIXELS race_up     at VBL 18100 flip  10/40: IDENTICAL (64f19a1d d9cdbe0a / 58491371 19ced56f)      STATE race_up   : common 95; differing bytes 0
PIXELS race_drive  at VBL 15300 flip  10/40: IDENTICAL (d67d147e ed8944f1 / 3d3df84c 3d3df84c)      STATE race_drive: common 100; differing bytes 0     RESULT: ALL IDENTICAL
--poke 11c6=01 (colour $c7, both runs):
PIXELS race_start  at VBL 16400 flip  10: IDENTICAL  md5 c41bd95d b046d155 (stock c41bd95d b046d155)    (stock pixels differ from the `$cd` run 3da506a7: the poke is effective)
PIXELS race_start  at VBL 16400 flip  40: IDENTICAL  md5 9245a948 c0d2ac2b (stock 9245a948 c0d2ac2b)
PIXELS race_up     flips 10/40: IDENTICAL (same md5 as without the poke: the digit area of that snapshot is unchanged by `$11c6`)
```
Gain: -14,885 cycles/pass driving; nothing standing (the score does not change, the glyphs are not redrawn): `$B3C00` costs 8.6 k/pass in the patched profile (`work/render/prof/start_all3.txt`).

## 5. Combined, cold boots, long run

Composite gate (all three, raw `logs/gate_all3.txt`):
```
patch set: mr_edge mr_map mr_digit  (live image edge+map+digit.img, 22784 B)
PIXELS race_grid   at VBL 25100 flip  10: IDENTICAL  md5 81dfec87 d5a188cf (stock 81dfec87 d5a188cf)
PIXELS race_grid   at VBL 25100 flip  40: IDENTICAL  md5 7481e0c7 7481e0c7 (stock 7481e0c7 7481e0c7)
STATE  race_grid  : stock 109 passes, patched 100, common 100; differing bytes 0 at 0 addresses
PIXELS race_start  at VBL 16400 flip  10: IDENTICAL  md5 3da506a7 c54efba9 (stock 3da506a7 c54efba9)
PIXELS race_start  at VBL 16400 flip  40: IDENTICAL  md5 90858e13 4858b4b8 (stock 90858e13 4858b4b8)
STATE  race_start : stock 100 passes, patched 107, common 94; differing bytes 0 at 0 addresses
PIXELS race_up     at VBL 18100 flip  10: IDENTICAL  md5 64f19a1d d9cdbe0a (stock 64f19a1d d9cdbe0a)
PIXELS race_up     at VBL 18100 flip  40: IDENTICAL  md5 58491371 19ced56f (stock 58491371 19ced56f)
STATE  race_up    : stock 100 passes, patched 100, common 95; differing bytes 0 at 0 addresses
PIXELS race_drive  at VBL 15300 flip  10: IDENTICAL  md5 d67d147e ed8944f1 (stock d67d147e ed8944f1)
PIXELS race_drive  at VBL 15300 flip  40: IDENTICAL  md5 3d3df84c 3d3df84c (stock 3d3df84c 3d3df84c)
STATE  race_drive : stock 108 passes, patched 104, common 102; differing bytes 0 at 0 addresses
RESULT: ALL IDENTICAL
```
Cold boots of the default build (`python3 tools/msrpatch.py build --out build/render_default`: `mr_edge mr_map mr_digit mt_clock mt_sync mt_pre pp_bigram_cache`; `tools/msr_boot_test.py --game build/render_default`, raw `logs/boot_ste1m.txt`, `logs/boot_ste4m.txt`):
```
STE TOS 1.62 1 MB: RESULT in_race = True vbl 5807     PEEK $b2700: 4d 53 50 4f = MSPO (every site matched and applied)
STE TOS 1.62 4 MB: RESULT in_race = True vbl 5808     PEEK $b2700: 4d 53 50 4f = MSPO
```
`boot_to_race()` returns while the game is still in PP's position-table screen (tick.md): the race loop, and with it the three hooks, runs after the first SPACE, so the two drives below are what exercises them.

2-minute drive, STE 1 MB cold boot of the same build, SPACE, Up held, 6,500 VBL = 130 s (`work/render/drive2min.py`, raw `logs/drive2min.txt`; tuple = VBL since start, mode `$1021`, loop counter `$100e`, time-out flag `$1226`, world position `$5ff8`):
```
marker $b2700: 4d 53 50 4f 00 00 00 00 = MSPO     after SPACE: 17 flips/100 VBL
(481, 2, 137, 0, 728) (1082, 2, 237, 0, 1728) (1682, 2, 337, 0, 2719) (2283, 2, 437, 0, 3481) (2884, 2, 537, 0, 4197) (3485, 2, 638, 0, 4946)
(4085, 2, 738, 0, 5636) (4686, 2, 838, 0, 6334) (5287, 2, 938, 0, 7020) (5888, 2, 1038, 0, 7716) (6488, 2, 1138, 0, 8412)     alive, fc advancing: 1167
table check $102ba: 00 00 ff ff ff ff ff ff ff ff ff ff ff ff 00 00 | ff ff ff ff 00 00 00 00 ff ff ff ff 00 00 ff ff | ff ff ff ff ff ff 00 00 00 00 ff ff 00 00 ff ff
```
No crash; the pass rate is the T = 36 schedule (about 100 passes per 600 VBL = 8.3/s, world +700 units per 600 VBL = 83.3/s, as in tick.md); the first colour table (24 words) is unchanged after the run (equal to the dump `work/dumps/ram_race_start.bin`: `0000 ffff ffff ffff ffff ffff ffff 0000 | ffff ffff 0000 0000 ffff ffff 0000 ffff | ffff ffff ffff 0000 0000 ffff 0000 ffff`).
TT (68030 with caches, TOS 3.06, 4 MB; `work/render/tt_drive.py`, raw `logs/tt_drive.txt`): `in_race True vbl 5878`, marker MSPO, after SPACE and Up held 1,500 VBL: `(456, 2, 120, 508) (1021, 2, 198, 1288) (1586, 2, 277, 2078)` (the game runs, no crash), and the generated slots exist in RAM (`m $b3186`: `2f 01 20 05 80 86 24 04 ...` = `move.l d1,-(a7) / move.l d5,d0 / or.l d6,d0 / move.l d4,d2 ...`): the hook, the generator and the cache flush ran on a 030. Pixel identity there is **not** compared (no TT reference captures).

## 6. Unit tests of the paths the scenes do not reach

Each patch has a unit test run inside a snapshot (`work/render/run_unit.py SNAP PATCH TEST.bin $C5100 20 $C5114`; the test blob is loaded at `$C0000`, runs once from the race loop's call site `$7b74`):

- `test_edge.s`: stock `$1058a` vs generated routine, 15 real + 200 random colour tables x 8 d7 combinations x 16 random register sets, d0-d7 compared: **27,520 comparisons, 0 mismatches** (negative control, wrong d5 for the fast call: 27,520 mismatches). Raw `logs/unit_edge.txt`:
  `000C4100: 00 00 6b 80 00 00 00 00 ...` (comparisons, mismatches) / negative `000C4100: 00 00 6b 80 00 00 6b 80 ...`.
- `test_map.s` (needs the patch image but writes the original bytes back at `$126d4` for phase 0 and the `jmp` for phase 1): stock `$12690` vs `mr_map`, 128 cases (every `d2 & 15` value 8 times, random geometry/rows 1-16/source offsets, 15 registers + a checksum of the 8 KB scratch screen compared): **0 mismatching words**; negative control (blob entered 4 bytes late): 0x2e8 = 744 mismatching words. Raw (`logs/unit_map_digit.txt`):
  `== map` `000C5100: 00 00 00 80 00 00 00 00 ...` (128 cases, 0 mismatches); `== map NEG` `000C5100: 00 00 00 80 00 00 02 e8 ...`.
- `test_digit.s`: stock `$14d98` vs `mr_digit`, d4 = every low byte 0-255 (random upper bits), rows 1-16, random glyph data, same comparison: **256 cases, 0 mismatches**; negative control (entry 2 bytes late): 0x500 = 1,280 mismatches. Raw: `== digit` `000C5100: 00 00 01 00 00 00 00 00 ...`; `== digit NEG` `000C5100: 00 00 01 00 00 00 05 00 ...`.

## 7. What remains (per pass, driving, all three on; `work/render/prof/start_all3.txt`, instruction profile, cycles per pass by 256-byte block)

| bucket (cycles per pass) | cost | note |
|---|---:|---|
| sprite kernels `$12000-$16000` (object sprites `$e406`, clouds `$de1c/$de6c` kernels `$122e4/$15052` ~31 k, HUD parts, score glyphs now in the blob) | 345,862 | shift-per-row masked blits (`lsr.l d6,d1/d2/d3` etc. `$12b5c`, `$14100`, `$15100`): inherent work; the largest remaining cost, no cheap exact rewrite found |
| road span draw `$17c24-$18068` (excluding the edge blob) | 123,006 | 83.5 segments a pass at ~1,380 cycles; the `movem.l d2/d4-d6,-(a0)` writes are about 35 k **[INFERENCE: instruction counts x 40 cycles]**, the rest is per-segment setup (`swap/lsl/andi/cmpi` chains `$17c66-$17cb8`, `$17d60-$17d9e`, `$17e30-$17e7a`): a hand rewrite could save perhaps 10 k, risky |
| road geometry `$100b4-$102b8` | 91,795 | 3 loops x 112 lines, 2 `mulu.w` per line cost 9.7 k (`$1025e`/`$1026e`: 4,872 cycles/pass each); loop `$10216` ~61 k |
| objects `$e2e8-$ef7a` (sort, 37 slots, `$e338` loop 13.8 k) | 45,750 | game logic |
| VBL ISR `$d11e-$d616` (incl. sound `$8bf2` 19.7 k, `$d486` 17 k) | 42,382 | per VBL (about 5 per pass), scales with the VBL count; timer B ISR `$d616` another 12 k |
| idle wait (stock sync) | 34,789 | not work |
| `mr_edge` blob / `mr_map` / `mr_digit` | 22,995 / 10,840 / 8,575 | were 64,950 (edge) / 30,609 (map) / not measured separately (digit) |
| horizon strip `$18318` | 10,430 | movem copy at the bus limit |

Next-largest levers (not done here; all either visible, risky or small): road repaint avoidance (plan item 7, `$17c42` + `$100b4` ~ 215 k, high risk), hardware-scroll horizon (visible), sprite kernels (flat), geometry loop restructure (-15..-20 k, medium risk), per-segment setup of the span draw (-10 k).

## 8. Unproven / caveats

- Hatari only (8.02 MHz model); no real hardware. The 68020+ cache flush in `mr_edge` is the same code as `core.s`; it ran on Hatari's TT (68030, TOS 3.06) in the drive above (slots generated, game alive), but a stale-I-cache failure would only show on real silicon **[INFERENCE]**; Falcon not run.
- `mr_edge` assumes the 15 colour tables (`$102ba..$1055a`) are never modified at run time: they are static data in the code image; checked for the first table only after the 2-minute drive (section 5) and by the 215-table unit test of the generator; no write watch was run on the whole range.
- `mr_edge` regenerates the slots only when `$135a` changes; a table content change in place would be missed **[INFERENCE: nothing in the game writes there]**.
- The pixel gates compare two buffers at flips 10 and 40 and 95-103 passes of state per snapshot; the scenes are one track (`$102c` scheme of the first race) and `d2 = 1` for the minimap, `d4 = $cd/$c7` for the digits: other schemes and values are covered by the unit tests only.
- Worst single passes while driving can exceed 5 VBL by about 1 % (max 809,640 cycles = 5.05 VBL); they run late once and the pacer re-syncs.
