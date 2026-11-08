# MW1 baseline (unpatched), 1 MB STE, TOS 1.62, Hatari 2.6.1

Made with `tools/mw1.py` (`MW1.boot_to_game('M')`, `flip_trace`, `turn_to`), `work/bench.py` (one job per snapshot and
clock) and `work/mkbaseline.py` (the tables below are its output; raw results are in `work/bench/*.json`).
Every measurement restores the snapshot afresh (`MW1(snapshot=...)` retargets the scratch path, see
`work/notes/snapshot_restore.md`) and the 16 MHz runs call `set_cpuclock(16)` right after the restore.
Game state variables and the frame mechanism are in `work/notes/mw1_state.md`.

Game Options used for every snapshot: control = MOUSE, Mortars OFF, Bombers OFF, **Training ON**. With the defaults
(Training OFF) an enemy attack object spawns and ends the ski mode (`mw1_state.md`, last section), which is what
dropped the first attempt back to Decisions.

Soak with these options: restored `1mb_ski_stand.sav`, then for 201 s of wall time (about 9500 emulated VBL) clicked walk every
~19 s and moved the mouse +-120 px between clicks; 11 state samples all had `$1efde == 0` (still in the action mode) and the HUD clock
read 06:46; the last sample shows the position window recentred (x,z 20284,42043 -> 26263,25746, the `$152c0` path after
the `$b478` bound). Without Training (Mortars and Bombers already off) the game left the ski view on three occasions, with the HUD clock at 06:15, about 06:27 and 07:17, each time while Stark stood at speed 0.

## Snapshots (`work/snapshots/`, all 1 MB STE TOS 1.62, Skiing 3D view, Stark at Devils Valley)

| file | what it holds |
|---|---|
| `1mb_ski_stand.sav` | standing at the mission start: x=z=$6400, speed 0, heading 0, view north |
| `1mb_ski_busy.sav` | standing, heading 882 (WSW) at the same spot. The heaviest standing view of a 360 degree sweep (3-5 flips per 50 VBL; heading 835..920 was the slowest): ridges plus a pine, no building or vehicle |
| `1mb_ski_walk.sav` | walking straight south (heading 502) down the slope, a ramp-up to speed $188, run of about 5000 units that ends in a basin at z=20510 where the walk stops by itself |
| `1mb_ski_turn.sav` | the same run with the mouse displaced 150 px: walking and turning (heading rising by about 1 unit per frame) |
| `1mb_ski_stand_J.sav`, `1mb_ski_stand_K.sav` | standing, JOYSTICK / KEYBOARD control selected (made from `boot_to_game('J'/'K')`; for P5 controls work) |

Starting states (first flip after a restore, 8 MHz):

| snapshot | state |
|---|---|
| `1mb_ski_walk` | first flip at 8 MHz: VBL 32736, x=25652, z=24153, speed=392, heading=502 |
| `1mb_ski_turn` | first flip at 8 MHz: VBL 32882, x=25647, z=22900, speed=391, heading=518 |

Not made: a busy scene with a vehicle or buildings (no building is within walking reach of the start: the Decisions screen
at Devils Valley offers only map / portrait / team / snipe / ski, no "enter buildings"; walks die on the first rise, about 5000
units, and Training mode gates the enemy attack objects off, `mw1_state.md`) and a snow-buggy snapshot (no garage near the start).
`1mb_ski_busy` is the heaviest terrain view instead.

## Frame rate: flips (`$ff8201` changes) over 1000 VBL

| snapshot | 8 MHz flips/1000 VBL | fps | VBL/frame | 16 MHz flips/1000 VBL | fps | VBL/frame |
|---|---:|---:|---:|---:|---:|---:|
| `1mb_ski_stand` | 79 | 4.0 | 12.7 | 155 | 7.8 | 6.5 |
| `1mb_ski_walk` | 108 | 5.4 | 9.3 | 227 | 11.3 | 4.4 |
| `1mb_ski_turn` | 149 | 7.5 | 6.7 | 282 | 14.1 | 3.5 |
| `1mb_ski_busy` | 78 | 3.9 | 12.8 | 161 | 8.1 | 6.2 |

The ratio 16/8 MHz is 1.96 (stand), 2.10 (walk), 1.89 (turn), 2.06 (busy): the game is CPU bound and its frame rate
scales with the CPU. At 8 MHz the 3D view runs at 4 to 7.5 fps (VBL per frame 6.7 to 12.8). The profile total is
about 35.3 M cycles per 250 VBL against 40 M available at 8 MHz, i.e. the CPU never idles waiting for a VBL.

## Game speed vs frame rate (8 vs 16 MHz)

`Hatari.world_rate` samples the position with two debugger reads about 1.4 s apart, and the walk's speed word decays on
its own (terrain), so it gives a noisy answer here; it is listed for completeness. The exact test is `MW1.flip_trace`:
at every call of the flip routine `$bd9a` the debugger prints VBL, x, z (`$12c60/$12c64`), speed (`$15112`) and heading
(`$15114`).

Stock `world_rate($12c64, 100 VBL)` on `1mb_ski_walk`:

| CPU | flips/100 VBL | z units/s |
|---|---:|---:|
| 8 MHz | 10 (5.0 fps) | -396.5 |
| 16 MHz | 24 (12.0 fps) | -457.2 |

Flip trace, aligned frame by frame (set_cpuclock takes about a second, so the 16 MHz run starts further along; the first
16 MHz row is found in the 8 MHz trace and both are compared from there):

| snapshot | aligned frames | rows identical (x,z,speed,heading) | path | VBL, 8 MHz | VBL, 16 MHz | units/s, 8 MHz | units/s, 16 MHz | ratio | heading/s 8 MHz | heading/s 16 MHz |
|---|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|
| `1mb_ski_walk` | 14 | yes | 1087 | 142 | 70 | 383 | 776 | 2.03x | 0.0 | 0.0 |
| `1mb_ski_turn` | 16 | yes | 738 | 147 | 73 | 251 | 505 | 2.01x | 5.4 | 11.0 |

The aligned rows are identical (x, z, speed, heading at every frame), so one frame always does the same simulation step
whatever the clock; the same frames take 2.0x fewer VBL at 16 MHz, so **world speed (units per emulated second) and turn
rate double with the CPU**: game speed is tied to frame rate exactly as in MW2. Per frame: the walk moves about 100 units
(speed word / 4: z 24153 -> 24054 with speed $188) and the turn adds about 1 heading unit; the mouse turn rate is
`d0^3/64/65536` of the clamped mouse accumulator added to the heading once per frame (`mw1_state.md`). A fixed logic tick
will therefore be needed for MW1 too (P3).

## CPU profile at 8 MHz (250 VBL, buckets = nearest preceding `jsr/bsr` target, `m68dis.call_targets`)

Top 20 buckets per snapshot. Notes from the disassembly of the biggest ones (`work/dumps/x_exit.bin`):

* `$19f20` (17-18%): `movem.l d0-d7/a0-a1,-(a7)`, `bsr $19ed4`, then `cmp.w d2,d4`, `exg.l d1,d3`, `exg.l d2,d4`, sets
  `$1a616/$1a618` (min/max) and `addq.w #1,$19e6e`: [INFERENCE] the polygon edge setup / scan conversion.
* `$1b0e4` (11-14%): masks with `#$55555555` and its complement between two 4-byte patterns from `$1b280`:
  [INFERENCE] the dithered fill of the spans (the dither the user wants kept).
* `$12276` (7% standing, 2.6% walking): a byte-sum loop (`move.b (a0)+,d2 / add.l d2,d1`). It is called from `sub_0122f0`,
  which `sub_01dd14` calls at `$1dd18` for every object drawn (38 calls per 200 VBL standing, 43 `$122f0` calls, 20 flips,
  measured with `b pc = $...`). `sub_0122f0` looks `a4` up in a 30-entry table at `$123ac` (start, end, sum), sums the
  range and on a mismatch loops `addi.w #$1,$ff8240` forever (a hang with flashing palette). It is an anti-tamper
  checksum over the object model data `$31698-$3ddb4`; the data is constant, so the `jsr $122f0` at `$1dd18` can be
  skipped by a patch [INFERENCE: not tried]. Relevant for P4 because **patching code or data inside those ranges
  changes the sums**.
* `$19d6a` (3.5-4.3%): initialises `$1a616=$9000,$1a618=$7000` and walks polygon vertex/edge index tables:
  [INFERENCE] the polygon edge list walker.

### `1mb_ski_stand` at 8 MHz (250 VBL, 35320288 cycles, 5848 distinct instruction addresses)

| rank | bucket (call target) | share | cycles/VBL |
|---:|---|---:|---:|
| 1 | `$19f20` | 18.1% | 25637 |
| 2 | `$1b0e4` | 11.2% | 15770 |
| 3 | `$12276` | 7.2% | 10189 |
| 4 | `$19d6a` | 4.2% | 5955 |
| 5 | `$18362` | 3.7% | 5169 |
| 6 | `$1bbe6` | 3.6% | 5095 |
| 7 | `$17fa0` | 3.4% | 4865 |
| 8 | `$17444` | 2.9% | 4041 |
| 9 | `$19ed4` | 2.4% | 3388 |
| 10 | `$1580e` | 2.1% | 2993 |
| 11 | `$1d0a0` | 1.8% | 2491 |
| 12 | `$1d41e` | 1.7% | 2357 |
| 13 | `$17a04` | 1.5% | 2129 |
| 14 | `$1e0d8` | 1.4% | 2046 |
| 15 | `$17bf6` | 1.3% | 1863 |
| 16 | `$15e46` | 1.2% | 1765 |
| 17 | `$15b82` | 1.2% | 1765 |
| 18 | `$15a96` | 1.2% | 1758 |
| 19 | `$1601e` | 1.2% | 1750 |
| 20 | `$17c6c` | 1.2% | 1694 |

### `1mb_ski_walk` at 8 MHz (250 VBL, 35288312 cycles, 6788 distinct instruction addresses)

| rank | bucket (call target) | share | cycles/VBL |
|---:|---|---:|---:|
| 1 | `$19f20` | 17.0% | 24049 |
| 2 | `$1b0e4` | 11.0% | 15541 |
| 3 | `$1bbe6` | 4.7% | 6593 |
| 4 | `$18362` | 4.5% | 6384 |
| 5 | `$17fa0` | 3.8% | 5356 |
| 6 | `$19d6a` | 3.7% | 5245 |
| 7 | `$17444` | 3.4% | 4753 |
| 8 | `$1580e` | 2.7% | 3874 |
| 9 | `$12276` | 2.6% | 3664 |
| 10 | `$9572` | 2.4% | 3352 |
| 11 | `$1d0a0` | 2.2% | 3125 |
| 12 | `$19ed4` | 2.1% | 2995 |
| 13 | `$1d41e` | 1.9% | 2654 |
| 14 | `$17bf6` | 1.6% | 2266 |
| 15 | `$15c6e` | 1.5% | 2179 |
| 16 | `$15f32` | 1.5% | 2163 |
| 17 | `$15d5a` | 1.5% | 2163 |
| 18 | `$1610a` | 1.5% | 2160 |
| 19 | `$a36c` | 1.5% | 2143 |
| 20 | `$17a04` | 1.5% | 2062 |

### `1mb_ski_turn` at 8 MHz (250 VBL, 35272096 cycles, 6152 distinct instruction addresses)

| rank | bucket (call target) | share | cycles/VBL |
|---:|---|---:|---:|
| 1 | `$19f20` | 17.3% | 24435 |
| 2 | `$1b0e4` | 11.9% | 16844 |
| 3 | `$1bbe6` | 5.1% | 7193 |
| 4 | `$18362` | 5.1% | 7144 |
| 5 | `$17fa0` | 4.0% | 5687 |
| 6 | `$17444` | 3.8% | 5297 |
| 7 | `$19d6a` | 3.5% | 4938 |
| 8 | `$1580e` | 3.0% | 4227 |
| 9 | `$1d0a0` | 2.5% | 3492 |
| 10 | `$19ed4` | 2.0% | 2823 |
| 11 | `$1d41e` | 1.8% | 2573 |
| 12 | `$9572` | 1.8% | 2560 |
| 13 | `$17bf6` | 1.8% | 2509 |
| 14 | `$15c6e` | 1.8% | 2480 |
| 15 | `$1610a` | 1.8% | 2476 |
| 16 | `$15d5a` | 1.8% | 2472 |
| 17 | `$15f32` | 1.7% | 2436 |
| 18 | `$17392` | 1.7% | 2353 |
| 19 | `$a36c` | 1.6% | 2263 |
| 20 | `$17a04` | 1.5% | 2152 |

### `1mb_ski_busy` at 8 MHz (250 VBL, 35345196 cycles, 5834 distinct instruction addresses)

| rank | bucket (call target) | share | cycles/VBL |
|---:|---|---:|---:|
| 1 | `$19f20` | 18.1% | 25547 |
| 2 | `$1b0e4` | 14.4% | 20387 |
| 3 | `$12276` | 6.9% | 9697 |
| 4 | `$19d6a` | 4.3% | 6126 |
| 5 | `$18362` | 3.4% | 4864 |
| 6 | `$1bbe6` | 3.4% | 4796 |
| 7 | `$17fa0` | 3.1% | 4378 |
| 8 | `$19ed4` | 2.7% | 3853 |
| 9 | `$17444` | 2.5% | 3527 |
| 10 | `$1580e` | 2.0% | 2817 |
| 11 | `$1d0a0` | 1.7% | 2345 |
| 12 | `$1d41e` | 1.4% | 2015 |
| 13 | `$1e0d8` | 1.4% | 1925 |
| 14 | `$17a04` | 1.3% | 1856 |
| 15 | `$1601e` | 1.2% | 1668 |
| 16 | `$15b82` | 1.2% | 1662 |
| 17 | `$17392` | 1.2% | 1653 |
| 18 | `$1610a` | 1.2% | 1649 |
| 19 | `$15a96` | 1.2% | 1636 |
| 20 | `$1e026` | 1.1% | 1582 |

## What the numbers say for later phases

* The profile is dominated by the renderer's rasteriser (`$19f20` + `$1b0e4` + `$19d6a`/`$19ed4`: about 35-38%), with the
  anti-tamper sum as a cheap, safe 3-7% to remove.
* Game speed and turn rate are per frame, so P3 (fixed tick) is mandatory, and the 150 px mouse offset yoke persists
  (`$24faa`).
* The `ski -> Decisions` exits to avoid in benchmarks are the enemy attack object (Training OFF), reaching a building,
  and a fall (`mw1_state.md`).
