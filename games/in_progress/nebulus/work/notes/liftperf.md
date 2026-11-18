# Nebulus lift-ride performance: measurements, cause, patch np_lift  (NebLiftPerf)

Tags: **[obs]** raw Hatari 2.6.1 output this round, **[disasm]** `work/train/dis_33000_40000.txt` + `tools/m68dis.py` on the RAM dumps in `/tmp/lp`, **[INFERENCE]** not proven.
Files: `work/liftperf/` (scripts, §7), `patches/np_lift.s` + `patches/np_lift.nep` (the patch, `default yes`), raw logs/dumps/snapshots in `/tmp/lp`
(RAM scratch: `tr_*/log.txt` traces, `sq_*/` per-loop captures, `prof_*.txt` + `ram_*.bin` profiles, `*.sav` snapshots).

## 1. Answer in one paragraph
**There is no lift-specific hotspot.** A lift ride costs what any frame costs at that height plus the stem, and the tower
renderer is already at 70-98 % of the 2-VBL budget on the later towers; in **tower 6 with enemies on** the ride crosses the
budget and the game drops to **23.0 fps (16 of 92 ride loops take 3 VBL, mean 2.174)** while everything else in the same run
stays at 25 fps. Cause of the extra cost during the ride = (a) the frog's rising y scrolls the camera up into the band where
the most tower tiles are on screen (+50k cycles of `37e28`-family tile blits over the ride, `timing.md` §3 measured the same
routine), and (b) the stem the lift draws is a vertical run of masked cell blits (~23 k cycles at the top of a 22-row ride).
**Patch `np_lift`** makes the renderer's per-cell "is this cell drawable" test cheaper (bit-7 test right after the cell load
instead of a class-table lookup + compare), 6 in-place same-size sites, **no RAM blob**: measured **-9.2 k cycles/frame
(-2.8 %)**, tower-6 ride back to **25.00 fps, 0 of 92 loops over 2 VBL** (max busy 319,656 of 320,512 = margin 856 cycles),
and every ride/walk frame **bit-identical** to stock (per-loop framebuffer + variable-block compare, §5). The margin is thin:
the real problem is that the renderer has no headroom left on the later towers, and the only further safe saving I could find
is 0 cycles (the blit loops are already at the 68000's memory bandwidth, measured, §4) - a structural change would be needed.

## 2. Method
* Rides are reproducible without host timing: the global module `work/liftperf/lp.py` boots a build (`tools/nebulus.py`,
  lead-owned) or restores a snapshot; `ride2.py` puts a lift at column 0 straight under the frog's tower-start cell
  (`(0,1)` -> `$85`, shaft cleared, `$08` at row END, exactly the cells a shipped lift uses) and holds **Up**; `seq.py`
  drives input by poking the IKBD cell `$38498` at the loop-top poll `pc=$3dcf4` with **breakpoint hit counts as the loop
  index** (no host timing at all) and dumps per loop.
* Per-loop cost: breakpoints at the pacer entry `$3822c` and the flip `$3868e`, each logging `e VBL` + `e CycleCounter`:
  **busy = CycleCounter(pacer entry) - CycleCounter(previous flip)**, spin = flip - pacer entry, VBL/loop = VBL delta
  (`ana.py`). Budget = 2 VBL = **320,512 cycles** (8 MHz, 50 Hz; `timing.md` §1-2).
* Profiles: Hatari `profile save` windows armed by conditional breakpoints on the player state, `cmp_prof.py` compares two
  windows per function (`jsr/bsr` target buckets), `m68dis.py --profile` per instruction.
* Snapshots (`/tmp/lp/ste_s_t1..t8.sav`, `/tmp/lp/mste_s_t*`): cold boot of a build -> `HELLOIAMJMP` (`$33a40`) -> F1..F9,
  snapshot taken at the new tower's first loop with the frog standing alive (the enemy-spawn routine is `rts`-ed for the
  snapshot so the frog does not die before the save; `ride2` restores `$3792c` = `4e b9` when enemies should be on).
  The deterministic `seq.py` gates additionally freeze the level timer (`$3ad98` = `00 20 00 00 00 00`, `$3b0aa` = `60`) and
  the water phase (`$338fc` = 0) - without the latter the sea animation differs between *two runs of the same build*.

## 3. Measurements [obs]
### 3.1 STE 1 MB, TOS 1.62, 8 MHz, default patched set (no np_lift in the snapshot), ride col 0 rows 2..24, enemies ON
| tower | ride loops | VBL/loop | loops >2 VBL | ride fps | ride busy mean | ride busy max | after np_lift: VBL/loop (loops >2), max |
|---|---|---|---|---|---|---|---|
| 1 | 92 | 2.000 | 0 | 25.00 | 267,541 | 293,120 | 2.000 (0), 282,652 |
| 2 | 92 | 2.000 | 0 | 25.00 | 262,384 | 284,840 | - |
| 3 | 92 | 2.000 | 0 | 25.00 | 260,428 | 285,232 | 2.000 (0), 274,440 |
| 4 | 92 | 2.000 | 0 | 25.00 | 282,703 | 298,368 | 2.000 (0), 286,604 |
| 5 | 92 | 2.000 | 0 | 25.00 | 266,765 | 285,788 | (not measured) |
| **6** | **92** | **2.174** | **16 (17.4 %)** | **23.00** | **301,899** | **328,400** | **2.000 (0), 319,656** |
| 7 | 92 | 2.000 | 0 | 25.00 | 246,885 | 281,624 | - |
| 8 | 92 | 2.000 | 0 | 25.00 | 282,621 | 315,816 | 2.000 (0), 304,360 |
Whole-run numbers of the same traces (`all`): tower 6 base 2.103 VBL/loop, 10.3 % of *all* loops over 2 VBL, 23.78 fps
(after np_lift 2.000, 0 %); tower 8 base max 315,816 (98.5 % of the budget) - i.e. only tower 6 actually drops, tower 8 is
one stem away from dropping. Enemies OFF (same ride): tower 1 mean 243,254 / max 262,036, tower 7 246,885 / 281,624, all 2 VBL.
Standing next to the lift in tower 6 (state 0, before the ride): 229,831 mean; the same tower standing at the top of the ride
afterwards: 276,568. So the ride's +72 k over standing = +50 k scroll/tile (camera rises into the fullest band) + ~20 k stem
and creature work. The lift mover itself (`$3a3e6`, state 6) is trivial: it is a few dozen instructions per loop plus
`sub_03a7ce` (terrain test) every 4th loop.
### 3.2 Mega STE 4 MB, TOS 2.06
TOS 2.06 boots the STE **60 Hz** video mode in Hatari (`info video`: `Refresh rate: 60 Hz`), so a VBL is 133,600 cycles:
every loop - standing *and* riding - takes **3 VBL = 16.67 fps** (142/142 loops, base and patched alike; tower 6 ride busy
mean 298,874 / max 326,060). The pacer (`timing.md` §2) needs a *new* tick after entry in addition to `$38216` ticks, so a
2-VBL frame at 60 Hz always lands one tick later. Tick trace (`tick.py`: `$382ba` and `$3868e` with VBL + FrameCycles):
* STE: `t1921..t1930` = one timer-B tick per VBL, `f1931, f1933, ...` = a flip every 2nd VBL.
* Mega STE: `t3887..t3898` = one tick per VBL, `f3898, f3901, f3904, ...` = a flip every 3rd VBL.
[INFERENCE] Therefore: on a 60 Hz machine the game is 16.67 fps in *every* scene, ride or not, and np_lift cannot change it
(it would need busy < 1 VBL = 133,600). The Mega STE snapshots were taken from the build that *already contains* np_lift
(default set), so the MSTE table does not measure the patch; the STE table does.
### 3.3 The user's report, or: which ride drops
Only tower 6 dropped in every configuration I could build (88-row tower, 9 lifts, 4 creatures + the flyer). The user sees
the ride slow down because the ride is exactly where a nearly-full frame tips over: the stem and the upward scroll are the
last 20-50 k cycles of a frame that already spends 230 k.

## 4. What the ride loops spend (tower 6 ride, cycles/frame, Hatari profile, [obs])
Window y=36..50 (the overflowing part), stock vs np_lift: total busy 333,044 -> 314,231 (the rest is the pacer spin).
| range | routine | stock | patched |
|---|---|---|---|
| `37e76..37ea6` | 8-row masked cell blit (ledges/pillars, 8-long row loop) | 58,221 | 58,221 |
| `37eaa..37f4e` | clipped variants of the same | 27,669 | 27,669 |
| `37f50..37f7e` | 6-long masked cell blit (stem `$80`, 100.8 rows/frame) | 32,049 | 32,049 |
| `37ffa..38027` | 16-px masked sprite blit | 21,619 | 21,619 |
| `37cd6..37de7` | cell scan: tiles | 44,096 | 37,558 |
| `37c06..37cd5` | cell scan: doors | 21,942 | 19,309 |
| `36b3e..` | sky/background fill (16 x 11 rows of `movem.l`) | 44,549 | 44,549 |
| `33f8a..` | timer-B raster chain (palette splits) + tick + music | 24,130 | 16,880 |
| `3920c..396xx` | HUD | 9,092 | 9,092 |
Cell scans walk 16 columns x 22 cells x 2 passes (~700 cells/frame, `move.b -(a3),d0` / class lookup / `cmp.b #$28` / branch).
**Why not the blit loops**: each longword is `and.l dM,(a0)` + `or.l dD,(a0)+`; on the 68000 a memory read-modify-write is
20 cycles, so `move.l (a0),d6/and.l dM,d6/or.l dD,d6/move.l d6,(a0)+` is 32 = the same 40 with the loads - I built that
variant, moved both loops into free RAM at `$76c76`, measured **no change** (319,660 vs 319,380 max) and dropped it again.
The stem tile itself is `ff00ff00 0063001f 00000000 00ff00ff c600f800 00000000` per row (class 10, `$315e0[$80..$8f]` = 10,
table `$2fce0+phase*$32+10` -> `$37f50`); a byte-only fast path for it would save ~25 % of that 32 k but needs a per-class
dispatch change (two table halves) - not worth the risk for ~8 k.
## 5. The patch: `patches/np_lift.nep` (`default yes`, source `np_lift.s`, generator `work/liftperf/gen_lift.py`)
`a5` = the class table `$315e0`, built once per level by `sub_038028` (only writer, only readers `$37ba4`/`$38028`):
**every cell whose bit 7 is clear maps to class `$f6`** ("skip"), every bit-7-set cell maps to `$00/0a/14/1e/28`. The scans
therefore no longer need the table for the skip decision: the `move.b -(a3),d0` that loads the cell sets N, so `bpl.b skip`
leaves right after it. The drawings path is unchanged byte for byte; the branch target is the same one, and d0 on the skipped
path is dead (reloaded by `clr.w d0` at the next cell / already restored by the loop exit).
| site | length | original | new | what |
|---|---|---|---|---|
| `$37d5a` | 16 | `4240102310350000b03c002864000022` | `424010236a2a10350000b03c00286420` | `sub_037cd6` inner loop (8 cells/column) |
| `$37d0c` | 16 | `...b03c00286400002c` | `...6a34...642a` | `sub_037cd6` first cell |
| `$37d90` | 16 | `...b03c00286400001c` | `...6a24...641a` | `sub_037cd6` last cell |
| `$37c74` | 14 | `424010230c35002800006600000e` | `424010236a140c3500280000660c` | `sub_037c06` inner loop (door pass) |
| `$37c42` | 14 | `...6600001a` | `...6a20...6618` | `sub_037c06` first cell |
| `$37c96` | 14 | `...66000010` | `...6a16...660e` | `sub_037c06` last cell |
Per empty cell: 46 -> 24 cycles (scan 1), 34 -> 12 (scan 2). **RAM used: none** (in-place, same size, no blob, so nothing to
add to the dead-zone map; `ni_ikbd` at `$7726c` and the other blobs are untouched).
Measured effect, same ride/tower/enemies (STE): tower 6 ride mean 301,899 -> 291,956, max 328,400 -> 319,656, 16 -> 0 loops
over 2 VBL (23.00 -> 25.00 fps); tower 8 max 315,816 -> 304,360; standing/walking frames -6..-11 k.
## 6. Gates [obs]
* `python3 tools/nepatch.py verify`: `predicted stage-2 image vs ram_stage2_1mb.bin: 271849 game bytes compared, 0 differ`,
  every site `dump-orig OK` (30 sites in the default set with np_lift, 6 of them np_lift), no overlap.
* Cold boot of the default build with np_lift (`/tmp/lp/patched2`): `boot to tower: True`, marker `NEPO`, count `30`, the six
  np_lift sites read back `424010236a..` exactly as in the .nep.
* **Bit-exact equivalence, per loop** (`seq.py` + `cmpseq.py`: breakpoint-count loop index, input poked at the loop top,
  per loop the *displayed* framebuffer (32000 B, chosen by `$38758`), the whole variable block `$33900..$33a4f`, the timer
  words and the lift column are compared):
| gate | loops | differing loops |
|---|---|---|
| tower 1 ride to row 24, 110 loops | 110 | **0** |
| tower 6 ride, enemies on, 100 loops | 100 | **0** (base 2.152 VBL/loop, 15 loops >2 -> patch 2.000, 0) |
| tower 8 ride, enemies on, 100 loops | 100 | **0** |
| tower 7 ride to row 40 (long ride + return), 150 loops | 150 | **0** |
| tower 1 walk/jump/shoot script, 90 loops | 90 | **0** (VBL/loop identical: 3.360 both, same long animation loops) |
| tower 3 walk with enemies, 90 loops | 90 | **0** (identical VBL/loop) |
  Control: the same comparator run twice with the same build gives 0 differing loops (deterministic), so a 0 here is real.
* Trainers on the np_lift build: `T` `$76c02` `0000 -> ffff`, `E` `$76c04` `0000 -> ffff`.
* **Editor gates with np_lift in the default set** (build `/tmp/lp/patched3`, 30 sites, `0 clears`, 6 blocks; the set also
  contains `ni_ikbd`/`ni_turn`), all from a **cold boot with the game's own title up**:
  * F10/D manager entry, STE 1 MB **and** Mega STE 4 MB (`work/liftperf/edgate.py`, model `work/editor/e170.py`, 100 ms
    taps): `PASS marker NEPO`, hooks `$3851a`/`$3d662` = `4ef9`, `PASS F10 (100 ms) opens the manager (VBL vector leaves
    $382d8)`, `PASS F10 (100 ms) leaves again: 230104` (=$382d8), `PASS D (100 ms) opens the manager`, `PASS F10 leaves the
    D-opened manager`, `PASS F10 re-enters`, `PASS and leaves again` - **FAILS [] on both machines**.
  * Playtest of a lift placed by the editor (`work/editor/e140.py`, same flow as `lifts.md` §6b): `Lift: from here` at (2,2)
    -> `col2 00 81 85 00 00 00 00 00 00 00 00`, end picked at row 10 -> `00 81 85 00 00 00 00 00 00 00 08`; Playtest: frog
    `x 0x13 y 0xc st 0` -> ride -> `x 0x14 y 0x2c` with `col2 00 81 84 80 80 80 80 80 80 80 89` (stem + top platform), then
    `col2 00 81 85 00 00 00 00 00 00 00 08` again and the frog back at `y 0xc` (platform returned); save + validate:
    `extracted 8192 B -> /tmp/e140.ovl (NEBLEVEL.OVL valid: 1 levels / 0 campaigns)`, `OK`, `level 0 'NEW LEVEL' ...
    time 0450 size 140 cells 24`, `lifts 1`, `lift col 2 rows 2..10`.
  * Shortcut gate (`work/editor/e150.py`): every shortcut key + door/exit triples + `l`/Return/space/Delete + lift via
    `a`/Up/Return + `z` stop + lift end picked below + pillar warning + playtest + T/E in the playtest: all `PASS`,
    `blob after T,E,T,E in edit view: 000000000000`, `blob after e,t in the playtest 9400ffffffff`, **FAILS []**.
* Not run: np_lift's own effect on Mega STE (the MSTE snapshots already contained it, §3.2), real hardware, floppy build.
## 7. Files (work/liftperf/)
`lp.py` (boot/snapshot/read helpers, `live_cmds` chunks `nepatch live` for live testing), `ana.py` (per-loop busy/spin/VBL),
`ride2.py` (poke a lift at col 0, hold Up, trace), `seq.py` + `cmpseq.py` (deterministic per-loop equivalence),
`prof_ride.py` + `cmp_prof.py` (profile windows), `mksnap2.py` (per-tower snapshots), `gen_lift.py` (assembles
`np_lift.s` blocks -> `.nep`), `tick.py` (tick/flip VBL trace), `coldgate.py`, `edgate.py` (F10/D manager entry, cold boot),
`matrix.sh`, `gate.sh`, `tailgate.sh`.
Reproduce: `python3 work/liftperf/gen_lift.py && python3 tools/nepatch.py verify`; ride: `python3 work/liftperf/ride2.py
/tmp/lp/ste_s_t6.sav TAG 24 1` (LIVE=np_lift for the patched variant); gates: `./gate.sh` (~5 min); editor gates: `python3 work/liftperf/edgate.py /tmp/lp/patched3 /tmp/lp/w_lped1 ste|megaste`,
`cd work/editor && python3 e140.py /tmp/lp/patched3 /tmp/lp/w_lped140` and `python3 e150.py /tmp/lp/patched3 /tmp/lp/w_lped150`.
## 8. Floppy build (NebRelease3's job; exact data)
All six sites lie in text before the first shifted block (floppy delta 0 for text offsets < `$4c46`, `tools/nefloppy.py`
SEG), so **the floppy addresses are identical**: `$37c42`, `$37c74`, `$37c96`, `$37d0c`, `$37d5a`, `$37d90`. Checked with
nefloppy's own `site_equivalent` against `alt/floppy/Nebulus (1988)(Hewson)[cr Atari Legend].st`:
| PP site | floppy | PP original bytes | floppy original bytes | equivalent |
|---|---|---|---|---|
| `$37c42` | `$37c42` | `424010230c35002800006600001a` | same | yes |
| `$37c74` | `$37c74` | `424010230c35002800006600000e` | same | yes |
| `$37c96` | `$37c96` | `424010230c350028000066000010` | same | yes |
| `$37d0c` | `$37d0c` | `4240102310350000b03c00286400002c` | same | yes |
| `$37d5a` | `$37d5a` | `4240102310350000b03c002864000022` | same | yes |
| `$37d90` | `$37d90` | `4240102310350000b03c00286400001c` | same | yes |
The class-table builder `sub_038028` is byte-identical too. **Needed change in `tools/nefloppy.py` (not mine):**
`SITE_ONLY` must gain `"np_lift"` (no blob, no remapped operands - the new bytes contain only relative branches), otherwise
`nefloppy.py verify/build` stop with `np_lift: no floppy translation ...`. Note the floppy build is the **60 Hz-only** game
(`tools/nefloppy.py` header), so on real hardware at 60 Hz np_lift will not raise the fps - it removes the extra cost but the
loop stays 3 VBL there (same as everything else, §3.2).
## 9. Not proven / limits
* Only tower 6 was found to drop; other towers, other lifts, 2-player mode and a level with several stems on screen were not
  swept. A tower whose frame is already at 320 k can still drop (the patch buys ~9-10 k, not a new structure).
* Margin after the patch is 856 cycles in the worst loop measured (0.3 %): a busier frame (more creatures, HUD change) will
  drop again. A real fix = reduce the renderer's per-frame work structurally (draw only the visible columns/cells, cache the
  sky fill, or split update/draw like `timing.md` §4 describes) - out of scope for a small patch.
* The MSTE numbers are from snapshots that already contained np_lift, so they do not measure the patch (they measure the
  60 Hz pacing). Real hardware, 512 KB mode, TT/Falcon, floppy build and the editor playtest with a lift: not run here.
