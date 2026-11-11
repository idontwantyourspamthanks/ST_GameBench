# MW1 in-game main loop and frame flip (action-mode loop: ski view, probably also buggy/glider)

Agent: MW1Frame. Read-only study; nothing patched on disk. Snapshots: `1mb_ski_stand`, `1mb_ski_walk`, `1mb_ski_turn` (1 MB STE, TOS 1.62,
Hatari 2.6.1). Static disassembly: `games/done/midwinter/work/dumps/ram_ski_walk.bin` (`tools/m68dis.py`). All numbers below are from
runs I made in this session; scripts were throw-aways in `/tmp/mw1f/`.

Method for the cycle shares: `b pc = $X :trace :file cmds` with `e CycleCounter` (exact CPU cycles; at 16 MHz the counter runs at the
16 MHz rate, ~320.5k per VBL) at the entry of every call in the loop body, then differences between consecutive hits. (`profile/*.txt`
has no inclusive cost and its pct column is a placeholder, so it is not used for shares.) 16 / 16 / 18 / 18 complete frames per scenario.

## 1. Where the loop is

| item | address | evidence |
|---|---|---|
| Action-mode driver | `sub_0125a0`, `$125f6: jsr $1498a.l` (`$125de` sets `$1efde=0` before, `$12602` sets it to 1 after) | `mw1_state.md`; disassembly of `$125a0..$12652` |
| Loop prologue | `sub_01498a` (`$1498a..$14aba`): loads screen, `$14a86 bsr.w $14e00` (first frame), `$14aa8 jsr $bd9a` (first flip), `$14aba jsr $12f5c` | disassembly |
| **The loop** | `$14ac0..$14ae8` | below |
| One frame | `sub_014e00` (`$14e00..$14e96`), 21 call sites | below |
| Flip | `sub_00bd9a` | section 5 |

```
014ac0: bsr.w   $14e00          ; one frame
014ac4: tst.w   $14dfc.l        ; "action mode over" (forced exit: dead, fall, ...)
014aca: bne.w   $14b08
014ace: tst.l   $12d76.l        ; pointer to a new mode descriptor (S key switches ski <-> snipe)
014ad4: bne.w   $14c24          ; -> $12654 then bra $149d8 (re-enter)
014ad8: tst.w   $14dfe.l        ; M key (map)
014ade: bne.w   $14c2c
014ae2: tst.w   $14ef6.l        ; X key (leave)
014ae8: beq.w   $14ac0          ; <---- loop back
```
`sub_014e00` has three callers: `$14ac0` (loop), `$14a86` (first frame) and `$d1de: jsr $14e00.l` (`sub_00d1c0`, same
prologue pattern, [INFERENCE] a redraw after returning from another screen). The loop is **generic**: the mode specific part is the
pointer `$12d5e` (`sub_012e9c: movea.l $12d5e.l,a0 / jsr (a0)`), copied from a mode descriptor record by `sub_012d0e`
(`$12d3a` active copy, length `$12d74`, source `$12d76`). The dump holds descriptor records at `$12d80`, `$12dc0`, ...:
```
$12d5e/$12d62/$12d68 = $131ae / $1314c / $130f2     (ski/walk: step / init / exit; also copy at $12d9e..)
records at `$12dc0..` ($1359a / $1354e / $13104) and `$12e00..` ($1373c / $136f8 / $13132)      [INFERENCE: buggy / glider]
```
`$13870` (second handler body in the same file) has its own speed code and calls `$14530`, `$152c0`, `$158f4`, `$159a4`, `$14684`
itself, i.e. the vehicle handlers do not go through `$13236`.

Code residency: bytes `$14e00-$14f00`, `$12e9c`, `$13236`, `$18304`, `$bd9a` are **identical** in `ram_ski_walk.bin`, `ram_ski_stand.bin`,
`x_exit.bin` (Decisions screen) and `ram1mb_options.bin` (Options screen, before any Skiing load) (python `a[lo:hi]==b[lo:hi]`),
so the whole loop is part of the resident image, not an overlay loaded for Skiing. A hook can be installed at boot/load time.

## 2. Ordered per-frame call list (`sub_014e00`) with cycle share

Instruction at the site = the call that the "cycles" belong to (measured: hit at this PC to hit at next PC). Mean cycles per frame,
8 MHz unless noted; "walk8" = `1mb_ski_walk`, etc. 100% = one loop pass = one presented frame.

| site | call | role | walk8 | walk16* | stand8 | turn8 |
|---|---|---|---:|---:|---:|---:|
| `$14e00` | `bsr.w $14efc` | key poll: `jsr $12ac6` (translates `$2c324` scancode via `$24846` to `$12afc`), sets `$14ef6` (X), `$14dfe` (M), `$6a32` (P) | 536 0.03% | 596 | 556 | 676 |
| `$14e04` | `bsr.w $12e9c` | **simulation**: `jsr ($12d5e)` = `$131ae` mode step -> ... -> `$13236` chain, then `bsr $12f9e` (stamina) | 19391 **1.19%** | 19066 1.34% | 18166 0.86% | 19618 1.34% |
| `$14e08..` | `tst.w $14dfc / beq` | if the sim set the exit flag, `rts` before drawing anything | | | | |
| `$14e14` | `jsr $14fac` | HUD gauge values into the `$2c376` record **and the game clock tick** (`$14fd2 addq.w #1,$e4(a6)`) | 1392 0.09% | 1366 | 1336 | 1377 |
| `$14e1a` | `jsr $129d2` | HUD: redraw only the gauges whose dirty counters (`$c0,$ae,$b4,$ba(a6)...`) are non-zero (`$aff2..$ca7e` + `$b1a0..`) | 110926 6.82% | 77420 5.44% | 54221 2.58% | 99328 6.79% |
| `$14e20` | `jsr $1580e` | writes constant fill patterns (`movem.l` of d0-a5 loaded with `$ffff`/`0`) into rows `$171f4..$171f6` of the draw buffer `$12d0a` [INFERENCE: sky/ground bands] | 44733 2.75% | 44286 | 44860 | 45035 |
| `$14e26` | `jsr $19c7a` | view cell origin `$19cd0/$19cd2` from `$12c68/$12c6a` | 164 | 164 | 164 | 164 |
| `$14e2c` | `jsr $1d77a` | sun/light vector from heading (`$1c6bc` table, `$1d816..$1d81a`) | 1060 0.07% | 1060 | 1060 | 1057 |
| `$14e32` | `jsr $202c6` | spawn test, slot `$1ce02` (handler `$20776` set at `$203b6`; gate `$2040c`) | 88 | 140 | 88 | 88 |
| `$14e38` | `jsr $200e8` | spawn test, mortars (gated `$2c17e`, slot `$1cdd6`, handler `$20524`) | 88 | 88 | 88 | 88 |
| `$14e3e` | `jsr $1ffe0` | spawn test, bombers (gated `$2c17c`, slot `$1cdd6`, handler `$2040e`) | 88 | 88 | 88 | 88 |
| `$14e44` | `jsr $1fa0a` | spawn test, slot `$1cdaa` (handler `$20ce2`) | 156 | 128 | 156 | 156 |
| `$14e4a` | `jsr $20d52` | **object update**: for 4 slots `$1cd7e + n*$2c`: `jsr ($28(a5))` if `$26(a5) > 0` | 7730 0.47% | 376 | 7929 0.38% | 8035 0.55% |
| `$14e50` | `jsr $1d0a0` | render prep: world objects (`$70010` list, 16 B each) and the 4 slots, culled to +-8 cells, into draw lists | 38275 2.35% | 36849 | 38089 | 37251 |
| `$14e56` | `jsr $18304` | **scene build**: terrain cells / objects -> polygon list (`$18bda`) | 665704 **40.90%** | 642569 45.13% | 717298 34.10% | 651268 44.54% |
| `$14e5c` | `jsr $19ce2` | **rasteriser**: walks the polygon list, `bsr $19d6a` per polygon (-> `$19f20`, `$1b0e4` fills) | 660770 **40.60%** | 523778 36.79% | 1142446 **54.31%** | 521351 35.65% |
| `$14e62` | `move.l $12d0a,$1bbe2` | | 36 | 36 | 36 | 36 |
| `$14e6c` | `jsr $1bbe6` | cockpit/frame overlay: applies an and/or mask list (`$1bbde`) to the draw buffer | 75785 4.66% | 75234 5.28% | 76488 3.64% | 76070 5.20% |
| `$14e72` | `tst.w $13b40 / bne $14e8a` | `$13b40==0`: `move.w #-1,$13b40; bsr $14246; rts` = **no flip** that pass (`$14a34` sets it to -1 at entry; when it is 0 is [INFERENCE: first frame after a reset]) | 28 | 28 | 28 | 28 |
| `$14e8a` | `jsr $14e98` | message timer (`$14ee4`); the string at `$14ee6` is "ENEMY IN RANGE", drawn through `$117d8` only when armed | 64 | 64 | 64 | 64 |
| `$14e90` | `jsr $bd9a` | **FLIP** | 392 0.02% | 392 | 392 | 392 |
| `$14e96` | `rts` -> `$14ac4..$14ae8` -> `$14e00` | loop tests | 152 | 152 | 152 | 152 |
| | **total per frame** | | **1627556** (10.19 VBL) | 1423881* | 2103706 (13.11 VBL) | 1462322 (9.11 VBL) |

`*` walk16 = same snapshot after `set_cpuclock(16)`; the counter then counts 16 MHz cycles (320,990 per VBL) and the scene is not the
same (the 16 MHz run reaches later frames of the walk), so compare the shares, not the absolute cycles. min/max over the frames for
the three big blocks (walk8): `$129d2` 64968..171208, `$18304` 642148..696260, `$19ce2` 555628..779352.

Result: render side (`$129d2..$1bbe6` less the spawn/object calls) = **about 98%** of a frame, logic (`$14e04`, `$14e14`,
`$14e32..$14e4a`, plus the poll) = **about 1.8% walking, 1.3% standing**. The two big blocks (scene build + rasteriser) are 81.5% of a
walking frame and 88% of a standing frame.

### 2.1 What is inside the big calls (measured the same way, walk8)

`sub_018304` (679474 cycles/frame = 41.7%): `$18362` 38201 (clears a `$4000`-byte work area `$12cfa`) / `$16d9c` 4184 /
`$16cf6` 216523 (terrain cell projection; picks one of 4 view cases from `$17170`) / `$17f20` 392 / `$170e6` 381620 (per-object
polygon generation, `$170f8..$17108` loop calling `$17444` per object in the list `$18f02`) / `$18362` again 38394.

`sub_019ce2` (rasteriser, 40.6% walking, 54.3% standing): loop `$19d1c..$19d56` over the polygon stack `$18bda..$18be2`:
`$19d52 bsr $19d6a` per polygon. The profile buckets (`baseline.md`) put `$19f20` (~17%), `$1b0e4` (~11%) and `$19d6a`/`$19ed4` (~6%) here.
Standing has the heaviest rasteriser (1142446 cycles vs 660770 walking); the scene build is similar (717298 vs 665704).

### 2.2 The simulation chain inside `$14e04` (walk8, 19374 cycles/frame, 12 frames)

```
012e9c sub_012e9c  -> $12ea4 jsr (a0) = $131ae   (mode step: state machine, speed ramp)   1663 (8.6%)  then bra $13236:
$13236 bsr $12fe2   turn (heading += cubic(mouse X accumulator))          268
$1323a move.w $12c98,$15114                                                28
$13244 bsr $141ce   ($14138 gated, 0 here)                                 64
$13248 bsr $14530   MOVE: position += sin/cos(heading)*speed>>16          540
$1324c bsr $13078   terrain height + slope at the new position (`$19558`/`$1957a`)  11716 (60.5%)
$13250 bsr $144ca / $13254 $13bfa / $13258 $152c0 (window recentre)       76 / 64 / 64
$1325c bsr $158f4 / $13260 $159a4  (cell indices, in-cell offsets)         1059 / 2305
$13264 bsr $14684 / $13268 $14716 ($1721c = height + $12c5c)               509 / 84
$1326c bsr $12f6a / $13270 $12f3e (dead if $12c5e == 0 -> $14dfc=1)       208 / 64
$13274 bsr $13b8a / $13278 $142cc (energy countdown $14328, exit at 0)    100 / 116
$1327c rts ; $12ea6 bsr $12f9e (stamina $2c422 -= f($1354c))              382
```
All 22 breakpoints at these PCs fired exactly once per frame, in this order (raw sequence from `t3.py`, 11 frames / 100 VBL):
`12e9c 12ea4 131ae 13236 1323a 13244 13248 1324c 13250 13254 13258 1325c 13260 13264 13268 1326c 13270 13274 13278 1327c 12ea6 12eaa`.

## 3. Flip mechanism and buffer rotation (`sub_00bd9a`)

```
00bd9a: movem.l d0-d2/a0/a6,-(a7)
00bd9e: lea.l   $2c376.l,a6
00bda4: move.l  $0(a6),d0              ; d0 = buffer just drawn (table slot 0)
00bda8: lea.l   $ff8201.l,a0
00bdae: lsr.l   #8,d0
00bdb0: movep.w d0,$0(a0)              ; $ff8201 / $ff8203 = base hi / mid   <-- THE FLIP
00bdb4: move.l  $0(a6),d0 ; move.l $4(a6),d1 ; move.l $8(a6),d2
00bdc0: move.l  d2,$0(a6) ; move.l d0,$4(a6) ; move.l d1,$8(a6)   ; (s0,s1,s2) <- (s2,s0,s1)
00bdcc: move.w  $8c(a6),d0 / addq.w #1,d0 / cmp.w #3,d0 / bne / moveq #0,d0 / move.w d0,$8c(a6)  ; frame phase 0,1,2 at $2c402
00bdde: move.l  $0(a6),$12d0a.l       ; $12d0a = next draw buffer (all renderers draw to a0 = $12d0a)
```
Raw, `b pc = $bdb0` with `m $2c376 16`, `m $12d0a 4`, `m $ff8201 4` at four consecutive flips (VBL 32725..32760):
```
VBL 32725  $2c376: 00078000 00058000 00068000   $12d0a=$78000  $ff8201 still 05 (previous base)
VBL 32736  $2c376: 00068000 00078000 00058000   $12d0a=$68000  $ff8201 = 07 (the base set one flip ago)
VBL 32748  $2c376: 00058000 00068000 00078000   $12d0a=$58000  $ff8201 = 06
VBL 32760  $2c376: 00078000 00058000 00068000   (cycle repeats)
```
So the presented order is `$78000 -> $68000 -> $58000 -> $78000 ...`. It is a **true triple buffer**: the next draw target is
the buffer shown two flips ago (never the one now on screen nor the one pending). The base register is written at an arbitrary
beat of the video frame. `$bdec` (double buffer variant, `sub_00bdec`) and `$12a80` are not used by the loop (0 hits in 100 VBL, per `baseline.md`).
`$8c(a6)` = `$2c402` is a 0/1/2 phase; the HUD dirty counters (`move.w #$3,$c0(a6)`, `subq.w #1,$b4(a6)` in `$aff2`..`$b54a`)
are set to 3 when a gauge changes so the gauge is redrawn into all three buffers.
Palette changes ride on the game's own VBL handler: the loop stores a palette pointer in `$24f24` (`$14a98: move.l #$22efa,$24f24`);
`$61b8..$61d8` loads it into `$ff8240` at the next VBL and clears it.

## 4. Does the loop wait for the VBL? **No.**

* Phase of the flip inside the video frame, `b pc = $bdb0` with `e FrameCycles`/`e HBL`, 34 flips over 300 VBL (8 MHz, walk):
  `FrameCycles` 26612, 5364, 43132, 64264, 85408, 47912, 10356, 131304, 93888, 56468, 19088, 139820, 102712, ... (HBL 51, 10, 84,
  125, 166, 93, 20, 256, 183, ...): uniform over the whole 160256-cycle frame, no alignment to the vertical blank.
* The two VBL waits that exist in the game are never executed in the loop: `sub_006840` (`move.w #$ffff,$2c31a.l / tst.w $2c31a.l /
  bne.b`; the VBL handler clears `$2c31a` at `$61b2`) and `sub_00bf0c` (palette change: waits the same way). Profile (`walk.txt`,
  `stand.txt`): addresses `$bf0c..$bf44` and `$6840..$6850` have **0** hits; `$61a8..$629e` (the VBL handler) has 4400 cycles at `$61ac` = 220 VBL.
* The loop body is straight-line code; the measured loop-to-loop total equals the sum of the call segments (section 2), and 98% of the
  time is render-side (81-88% in the two big calls). VBL per frame: stand 12.28 (min 11, max 14), walk 10.81 (9..13), turn 6.81 (5..11) at 8 MHz; stand 6.72,
  walk 4.53, turn 3.33 at 16 MHz (`rate.py` flip logs, 122/28/103 and 223/67/211 flips). CPU bound; nothing idles.
* The VBL handler itself is minimal in an action mode: it increments `$637e`, loads the pending palette, runs sound (`$69b8`), the joystick/keyboard
  scan (`$652e`, `$65c0`), then calls `jsr (a0)` with `a0 = table[$62b8]`; in the action mode `$62b8 = 2` and entry 2 of `$62a0` is
  `$675c: rts`. It does not touch the display or the game state.

## 5. Is logic separable from rendering? Yes (measured)

Dependency is one way: the sim writes position/heading/speed/cell/clock, the renderer reads them. The renderer writes only the
draw buffer, the polygon list (`$18bda` stack), work areas (`$12cfa`..) and HUD dirty counters; the loop calls it after the logic and
nothing in the logic reads those. The calls divide as follows:

| group | calls | k times per rendered frame? |
|---|---|---|
| input poll | `$14efc` | once per rendered frame (it consumes the scancode `$2c324` and rewrites `$12afc`) |
| simulation | `$12e9c` (+ its `$12f9e` stamina) | yes, this is the player step |
| HUD feed + game clock | `$14fac` | yes (the clock lives here) |
| object/spawn logic | `$202c6`, `$200e8`, `$1ffe0`, `$1fa0a`, `$20d52` | yes, but they sit *between* render calls in the original order |
| render | `$129d2`, `$1580e`, `$19c7a`, `$1d77a`, `$1d0a0`, `$18304`, `$19ce2`, `$1bbe6` + flip | once |

**Live test, k = 2** (restore `1mb_ski_turn` and `1mb_ski_walk`, 8 MHz, then `loadbin` into free RAM `$b3200` and splice
`$14e00` (8 B: `61 00 00 fa 61 00 e0 96`) to `4e b9 00 0b 32 00 4e 71`, and `$14e14` (`jsr $14fac`) to `4e b9 00 0b 32 20`):
```
$b3200: 4eb9 00014efc  4eb9 00012e9c  4eb9 00012e9c  4e75        ; poll, sim, sim, rts
$b3220: 4eb9 00014fac  4eb9 00014fac  4e75                      ; HUD/clock twice
```
Result over 250 VBL of the turn snapshot: **heading +2 per flip (was +1)**, **game clock tick every 11,10,11,10 flips (was every 21)**,
no crash or hang (flips kept coming, 46 flips in 241 VBL; I did not inspect the picture). Walk snapshot: dz per flip `-77,-66,-59,-53,-46,...` at speeds `177,146,126,114,101,...` (unpatched: `-98,-99,-97,-95` at
`382,392,396,388`): two moves of about speed/4 per flip, and the speed decays twice as fast per flip. So the sim chain **can** run k times per
presented frame, with no side effect observed; each extra step costs about 20.8k cycles (`$12e9c` 19.4k + `$14fac` 1.4k), 1.3% of a walking frame at 8 MHz.

Caveats for a fixed-tick implementation (all from the disassembly, not exercised):
* `$12afc` (last key) is re-evaluated by `$131d8..$13226` every step. `sub_012ac6` rewrites it once per poll (0 when no key), so k steps
  see the same key k times. `S` clears it (`$131fa`); Space (`jsr $1fc6e`) is protected by `tst.w $26(a5)` of slot 0 (second throw finds the slot
  busy); to be safe zero `$12afc` between steps.
* Exit/abort flags: after every step test `$14dfc` (set by `$12f48`, `$13986`, `$14312`, `$2061a`, ...) and `$12d76` (mode switch) before the
  next step.
* The PRNG `sub_00d57e`/`$d598` (state words `$d5d8/$d5da`) is advanced by the spawn tests every pass: spawn probabilities (`$20e48..$20e4c`) are
  per-step, so they scale with the step rate, exactly like everything else.
* Skipping a render means skipping `$129d2, $1580e, $1d0a0, $18304, $19ce2, $1bbe6` **and** the flip together (otherwise the draw buffer
  keeps the picture from three flips ago); the HUD dirty counters only count down inside `$129d2`, so they stay consistent.
  `$14e72` (`$13b40`) already has a "no flip this pass" path that could be reused.

## 6. Open items
* The `$1359a`/`$1373c` handlers and descriptor records were read only for their addresses; I did not run buggy or glider (no snapshot). That they use this
  same loop is established by `$12e9c` (`jsr ($12d5e)`), but their timing was not measured.
* Semantics given as [INFERENCE]: terrain projection (`$16cf6`), object polygons (`$170e6`), which scene each descriptor record belongs to.
