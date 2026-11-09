# MW1 timing (P3): fixed 5 Hz logic tick (option A) and 25 Hz view sub-steps (partial B)

Author: MW1Timing. Patches: `tick_head` (option A) or `p3b_head` + `p3b_hook` + `p3b_hud` + `p3b_logic` + `p3b_msg` + `p3b_units`
(partial B), all `default: no`. Gate tool: `tools/mw1tick.py` (`ab`, `fps`). Evidence is disassembly addresses (`tools/m68dis.py` on
`work/dumps/ram_ski_walk.bin`, listings in `frameloop.md` / `simtiming.md` / `controls.md` for everything not re-derived here) or raw
output pasted below (1 MB STE, TOS 1.62, Hatari 2.6.1 unless stated). Anything not run is marked **[INFERENCE]**.

## 0. Result

| item | status |
|---|---|
| Option A `tick_head`: simulation at exactly 5 steps/s (TICK = 10 VBL) at 8 and 16 MHz | done; cold boot 1 MB STE / 4 MB Mega STE: 5.003 / 5.003 ticks/s |
| Partial B `p3b_*`: the view (heading, position, cells, terrain tilt, camera height) advances in 5 sub-steps of 2 VBL per tick, i.e. up to 25 renders/s | done |
| Group-end state of B == option A == the original per-frame game | proven, walk / turn / stand / busy, 8 and 16 MHz, plus a 15 units/tick turn (section 8.1) |
| Full B (the whole logic at 25 Hz) | rejected, section 5 |
| Controls (`p5_ctl_turn`) interplay | agreed with MW1Controls, tested with both A and B (sections 7, 8.5) |
| Cold boots (HAGA defaults + mine) 1 MB STE TOS 1.62 and 4 MB Mega STE TOS 2.06: MWPO, walk | done, both A and B (section 8.4) |

**New finding that changes what "logic" means in this game (section 4):** `sub_0129d2` (`jsr $129d2` at `$14e1a`, labelled "HUD redraw" in
`frameloop.md` section 2) ends with `jsr $c4f2` and `jsr $ca7e` (`$12a5e`, `$12a64`): the **map-unit simulation**. It is 46 k cycles a pass
(`$c4f2` 34.5 k, `$ca7e` 11.1 k, measured), 2.8 % of a walking frame, and draws 15 PRNG numbers per pass. The whole logic of a tick
is therefore about 75 k cycles (4.6 % of a walking frame), not the 1.2 % of `$12e9c`. Skipping `$129d2` on a skipped render changes the game.

## 1. What was used (sources, not re-derived)

* One loop pass = one step = one flip; nothing in the simulation is time based (`simtiming.md` section 1). The loop head `sub_014e00`
  is `bsr.w $14efc` (key poll) + `bsr.w $12e9c` (step) at `$14e00..$14e07`; callers `$14ac0` (loop, return `$14ac4`), `$14a86` (first
  frame), `$d1de` (`frameloop.md` section 1; I re-read `$1498a..$14ae8`).
* Real time: the game's own VBL handler does `addq.w #1,$637e` (`$61ac`); free running in the action mode; no reader in the loop
  (`simtiming.md` section 5). It is a word: deltas are taken mod 65536; menu code clears it (resync below). No VBL patch is needed.
* At 8 MHz the original runs 4.07 (standing) / 4.62 (walking) / 7.34 (turning) steps/s, 21 passes per game minute (`simtiming.md`
  section 4); flips per 1000 VBL unpatched in `baseline.md`.

## 2. Base rate: 5 steps/s

TICK = 10 VBL = 5 steps/s, as MW2. The original's natural pace at 8 MHz is scene dependent, 4.07 / 4.62 / 7.34 steps/s standing /
walking / turning (`simtiming.md` section 4), i.e. 4 to 7.5 as the task states. Walking and standing are what the player does most; 5 is
8 % above the walking pace and 23 % above standing, and 32 % below the (lighter) turning frames. A game minute lasts 21/5 = 4.2 s
(5.2 s standing and 2.9 s turning in the original). 10 VBL also divides into five whole 2-VBL sub-steps, so B needs no fractional VBLs.
[INFERENCE] Since the VBL is the time base the tick follows the video refresh: a 60 Hz monitor gives 6 steps/s, as in MW2.

## 3. Option A: `tick_head` (site `$14e00`, 8 B -> `jsr $b3100.l ; nop`, blob `$B3100-$B31BB`)

Scheduler (all state in the data block D = `$B3700`, zero at boot; `D+0 LAST.w, D+2 ACC.w, D+6 SKIP.w`):

* `ACC` = real time not yet simulated, in VBL. Each look: `d1 = ($637e - LAST) & $ffff`, `LAST = $637e`; `d1 > 4*GRP` (first entry, back from
  another screen, counter cleared by a menu, pause) -> resync (`ACC = 0`, then this pass only); else `ACC += d1`.
* Ahead (`ACC < GRP`): spin on `$637e` = frame limiter. Else `ACC -= GRP`, clamp `ACC <= 3*GRP` (catch-up bounded to 3 steps).
* Behind (`ACC >= GRP` after the subtraction): `SKIP = 1`. The pass still runs the key poll and the step, then, instead of returning into the
  loop body, runs only the body's **logic** calls and returns straight to the loop top (`wskip`):
  `$14fac` (HUD feed + game clock), `$c4f2` + `$ca7e` (map units; only if `$12d58 != 1`, the test `$129d2` makes itself), `$202c6 $200e8
  $1ffe0 $1fa0a` (spawn tests), `$20d52` (objects), the message timer `subq.w #1,$14ee4` (what `$14e98` would count); not the six
  render calls `$129d2(HUD part) $1580e $1d0a0 $18304 $19ce2 $1bbe6`, nor the flip. They are skipped together, as `frameloop.md` section 5
  requires (HUD dirty counters only count down inside `$129d2`). `tst.w $14dfc` after the step as the body does.
* The loop top (`$14ac4..$14ae8`) tests `$14dfc`, `$12d76`, `$14dfe`, `$14ef6` after **every** pass, skipped or not.
* Key word `$12afc`: every step has exactly one poll in front of it (`$14efc -> $12ac6` rewrites `$12afc` from `$2c324` and clears the
  latch, `$12ad8`), so no step sees a stale key twice and no explicit clear is needed. This holds for B too: the poll is only done on PH 1.

## 4. Hidden simulation in `$129d2` (affects every patch near the loop body)

`sub_0129d2` (`$129d2..$12a6a`): `$12d58 == 1 -> rts`; then `a6 = $2c376` and the gauge routines `$aff2 .. $baec` (HUD drawing), then
```
012a5e: jsr $c4f2.l    ; sub_00c4f2
012a64: jsr $ca7e.l    ; sub_00ca7e
012a6a: rts
```
* `$c4f2` (`$c4f2..$c72e`): entry gate `$2baec`; spawns walker records in the table `$2d47e` (41 entries x 16 bytes: path pointer, cell x/z,
  direction, flags) from the counters `$2bb0a..$2bb18`, then steps every unit (`$c922` along its path byte stream, `$c9c6` random turn with
  `jsr $d598` at `$c9da`, `$ca00` a blocked-by-terrain test against a byte map at `$3ddb4` [INFERENCE: the semantics of the names are mine]).
* `$ca7e` (`$ca7e..$cb2c`): for each unit inside the view window, `$cb2e` flags it; the first one becomes the object in slot `$1cdaa`
  (`move.l (model table $316e4),$2(a1)`, world position from `$1d048`) which is the handler `$20ce2` (follows its unit via `$cb6e`).
* Measured on `1mb_ski_walk` (Hatari `e CycleCounter` at `$12a5e/$12a64/$12a6a`, 111 samples): `$c4f2` 34 408-37 604, mean **35 316**
  cycles; `$ca7e` 11 020-13 600, mean **11 150**. PRNG draws: 584 hits of `$d598` from `$c9e0` (the `$c9da` call) and 29 from `$d584` (`$d57e`) in
  250 VBL with 39 passes (`b pc=$d598` + `m a7 4`): about 15 draws per pass.
* First symptom (before I knew): with only the render skipped, the PRNG `$d5d8` differed from tick 2 and the slot-1 object diverged at tick
  13 (its target moved one cell, 2 world units). With the units run once per tick (this patch set) the PRNG `$d5d8` and the objects are equal at **every**
  tick end (section 8.1), which also shows the unit draws are the only PRNG users per tick.
* Consequence for any render skip, static-frame skip or HUD cache: hook the gauge part, never call/skip `$129d2` as a whole. In B the
  sub-step passes keep `$129d2` (HUD draw) but not the units (`p3b_units`, site `$12a5e`, 12 B).

## 5. Full B versus partial B

**Costs (cycles per pass, 8 MHz walking, Hatari `CycleCounter`):**

| part | cycles | source |
|---|---:|---|
| `$12e9c` (mode step chain + stamina) | 19 374 | `frameloop.md` 2.2 |
| `$14fac` HUD feed + clock | 1 392 | `frameloop.md` section 2 |
| `$c4f2` + `$ca7e` (units) | 35 316 + 11 150 | measured here |
| `$202c6 $200e8 $1ffe0 $1fa0a` spawn tests | 420 | `frameloop.md` section 2 |
| `$20d52` objects | 7 730 | `frameloop.md` section 2 |
| **whole logic of one tick** | **about 75 400** (4.6 % of a 1.63 M cycle frame) | sum |
| view sub-step (`substep`: heading, position, `$13078 $144ca $158f4 $159a4 $14684 $14716`) | 16 388 (16 292-18 880, 310 samples, mean 16 718) | measured, `b pc=$b3300` .. `$b338c` |

* Full B (the whole logic 5 times per tick) would add 4 x 75.4 k = 302 k cycles per 10 VBL (18.8 % of 1.6 M); partial B adds 4 x 16.4 k = 66 k (4.1 %).
  Cost is not what decides it (both are cheap next to a 1.6 M cycle frame).
* Full B **cannot be exact** at the group end (the stated requirement). What would have to be scaled, with the code that prevents it:
  * speed state machine (`$131ae`..`$13548`): `$152a8 = clamp(d1 + d0, 0, d2)` (`$13396 bsr $13040`) with `d0` from the slope; the stopped state
    divides by 3 each step (`$1329a divu.w #3`), the skiing state has its own accumulator (`$134a4`, `$13496 sub.w d1,$134a4`). Clamps and
    an exponential decay have no exact 1/5 step.
  * slope `$130d8 = ($17210>>2) - ($130d6>>2)` (`$130b2..$130ca`) is the difference of the terrain tilt of **consecutive ticks** and feeds the
    speed (`$13054` -> `$15116`) and the fall test (`$13344 cmp.w $1354a`): a sub-step would need a different definition.
  * random events: spawn tests draw `$d57e` with `d1 = $20e4c/$20e4a` once per tick (Bernoulli 1/N; five draws at 1/5N differ), the unit walkers
    `$c9c6` (15 draws a pass), `$20ce2`'s `$d57e` at `$20d0e`.
  * counters that count passes: `$15118` (21 per game minute), `$14328` (64), `$200e4` (200), `$14ee4`, `$13c5a`, `$13b5c`, `$158f2`, object
    lifetimes (`$fa`), `$200e2 -= $7b7`; about 30 per-object quantities, each a separate patch.
  * `simtiming.md` section 5 / `frameloop.md` section 5 live test with k = 2 unscaled passes: heading +2 per flip, clock every 10-11 flips, speed decaying twice as fast;
    the same would be 5x here.
* Partial B (this work) keeps the world exactly as A: state machine, turn, terrain, exits, clock, units, spawns, objects once per tick (10 VBL), and moves
  only the **view**: the position and heading *between* two tick states are interpolated, and the tick state itself is computed by the original code at
  the 5th pass. Exactness is by construction (section 6) and measured (section 8.1).

## 6. Partial B design

### 6.1 Groups and passes

A **group** is 5 passes of the loop, each 2 VBL (SUBT), PH = 1..5 (`D+4`). One group = one tick of option A (10 VBL), and its end state is A's.

| PH | what runs | notes |
|---|---|---|
| 1 | key poll `$14efc`; mode step `$12d5e` (= `$131ae`) with `SPLIT = 1` | the state machine up to its single exit `$13236`, then `p3b_hook` ends it (below) |
| 2-4 | `substep` only | pure view geometry |
| 5 | heading = HG, position = (X0,Z0), then the original chain `jsr $13244` (to the `rts` at `$1327c`), then stamina `$12f9e` | the whole rest of the A tick |

The loop body after the head runs on **every** pass: on PH 2-4 and 1 with `NOLOGIC = 1` (its logic calls are inert, section 6.4), on PH 5 as the original.

`p3b_hook` (site `$13236`, 14 B = `bsr.w $12fe2` + `move.w $12c98,$15114`, new `jsr $b3500.l` + 4 nops). `SPLIT = 0`: the two original
instructions. `SPLIT = 1` (PH 1 only): the state machine has finished the tick's decisions (speed `$15112`, `$152a8`, state `$13542`, lever `$24fae`, buttons, key, grenade);
```
H0 = $12c98 ; jsr $12fe2 (turn: fresh input, $12c98 += E, $15110 = E) ; HG = $12c98 ; E = HG - H0
(DX,DZ) = floor( (sin,cos)(HG & $3fe) * $15112 / 65536 )      ; the arithmetic of $14530 ($14534..$14560)
(X0,Z0) = ($12c60,$12c64) ; substep(1) ; drop own return -> rts to p3b_head ($12e9c's stamina is NOT run here)
```
**Why the state machine at PH 1 and the chain at PH 5:** A computes speed (state machine) before the move; the sub-steps need that tick's speed from the first pass on.
The state machine only reads state of the previous tick (position/terrain are untouched until the chain), so running it at the start of the group, and the chain
(terrain `$13078`, recentre `$152c0`, cells, exits `$12f3e $13b8a`, energy `$142cc`) at the end, reproduces A's order exactly:
`poll, state machine, turn, [view], chain, stamina, HUD/clock, spawns, objects`.

`substep(k)` (k = PH, 1..4; `$B3300`, 142 B):
```
$12c98 = $15114 = H0 + trunc(k*E/5)          ; muls.w/divs.w #5
$12c60 = X0 + trunc(k*DX/5) ; $12c64 = Z0 + trunc(k*DZ/5)
save $130d6,$130d8 ; jsr $13078 ; restore         ; terrain tilt of the intermediate position; the two words are the previous tick's height
jsr $144ca $158f4 $159a4 $14684 $14716            ; same order as the chain: tilt reset, view vectors, cell + offsets, terrain height, camera height
```
Not run in a sub-step: `$141ce` ($14138 gate), `$13bfa` (fall), `$152c0` (recentre), `$12f6a $12f3e $13b8a $142cc` (exits, energy). Position moves along the tick's *final* direction (`HG`),
so there is no lateral error, only the 1/5 truncation inside the tick; at PH 5 the original `$14530` adds the full `(DX,DZ)` to `(X0,Z0)`, so the position at the group end is A's, exactly, and
`$13078` etc. run once with the real state (the `$130d6/$130d8` words were restored, `$17214/$17216` are reset by `$144ca` first, `$158f4` divides them in place).

### 6.2 What decides whether a group may be split (`p3b_head`, evaluated at the start of a group)

`caller == $14ac4` (the loop; the first frame `$14a86` and `$d1de` always take a full A pass, PH = 0), `$12d5e == $131ae` (ski/walk; snipe, buggy, glider are A passes at 5 Hz),
`$14efa != 0` (window valid: the first pass after a rebuild is a full A pass so `$152c0` runs before any sub-step), `$13c5a == 0` (no fall in progress). A group in progress is
dropped when `$12d5e` changes (`S` key). The prologue `$14a68 bsr.w $12e9c` and every call outside p3b_head see `SPLIT = 0`: the original.

### 6.3 Scheduling

As option A, in units of the pass length (2 VBL on a group pass, 10 on an A pass): ahead -> spin; owed another pass -> `SKIP = 1`; clamp 3*GRP; resync > 4*GRP.
Skipped group passes: PH 1-4 return to the loop top after the sub-step (no body); PH 5 and A passes run `wskip` (section 3). So the world advances in real time, and the view
at each presented frame is the interpolation for that moment.

### 6.4 Loop body on a sub-step pass (`NOLOGIC = 1`), three hooks on the body's logic calls, one in `$129d2`

| patch | site | does |
|---|---|---|
| `p3b_hud` | `$14e14` `jsr $14fac` (6 B) | `NOLOGIC`: HUD values (compass, turn, gauges) are fed, but `$15118` is forced to 1 around the call so the game clock does not tick (restored after; `$14fc6 dbra` no-tick path) |
| `p3b_logic` | `$14e32..$14e4f` the five `jsr $202c6 $200e8 $1ffe0 $1fa0a $20d52` (30 B) | `NOLOGIC`: none of them runs |
| `p3b_msg` | `$14e8a` `jsr $14e98` (6 B) | `NOLOGIC`: message timer `$14ee4` restored after the call (it counts ticks); the message is still drawn into every frame |
| `p3b_units` | `$12a5e` (12 B) | `NOLOGIC`: `$c4f2/$ca7e` skipped |

They are inert without `p3b_head` (`NOLOGIC` is zero data). They hook **logic** calls only, so render-side patches at `$14e50..$14e90` do not clash, and
the render calls of the body are the originals (no copy of the body is made).

### 6.5 Blob map

`$B3100-$B32C7` p3b_head (456 B), `$B3300-$B338D` substep (142 B, fixed: `p3b_hook` jumps to it), `$B3500-$B3591` hook, `$B3600` hud, `$B3640` logic, `$B3680` msg, `$B36C0` units; data `$B3700-$B373F`:
`D+0 LAST.w, +2 ACC.w, +4 PH.w, +6 SKIP.w, +8 SPLIT.w, +10 H0.w, +12 E.w, +14 HG.w, +16 X0.l, +20 Z0.l, +24 DX.w, +26 DZ.w, +28 MODE.l, +32 NOLOGIC.w`.
`tick_head` shares `$B3100` and D (the two are alternatives, same site `$14e00`).

## 7. Coordination with MW1Controls (turn input)

Asked: one `$12fe2` call per tick or sub-steps? Answer given (`agent://MW1Controls`): **`$12fe2` is called exactly once per 5 Hz tick**, from the `$13236` chain (in B: from `p3b_hook` at PH 1),
never on sub-steps; it consumes everything accumulated in `$24faa` since the previous call and adds the turn to `$12c98`. No HOLD word is needed (MW2 needed it because its
sim pass ran 5x per tick; here only the view does and it never reads input). I take `E = $12c98(after) - $12c98(before)` and spread it over the 5 passes of the group; at the group end the heading is exactly
`before + E`. Tested with their `p5_ctl_turn` (below). A held key therefore gives `5 counts x VBLs held` per call, i.e. a constant rate per real second whatever the call interval; a turn is
applied with up to 10 VBL latency (fresh input is consumed at PH 1 only, as in A) and its effect is smeared over the next 10 VBL.
Keys: the poll is once per tick (PH 1), as in A: X/M/P/S/Space respond within 10 VBL.

## 8. Gates (raw output)

### 8.1 Group-end equality: `python3 tools/mw1tick.py ab --only <patches> --snapshot ... --mhz 8 16 [--poke 'w $24faa $01 $90']` (live-applied at the first flip of a snapshot restore; ticks paired by state, see the tool)

Compared at every tick end (A pass, or PH 5): position/cell/heading/clock/speed/state words, the `$1cd7e` objects, `$2d47e` units, `$2bae0` unit counters, tilt `$171f0..`, timers,
PRNG `$d5d8` (REGIONS in the tool). Masked: `$12c88-$12c8f`, scene-build scratch rewritten by every render (`$16d92`). The unpatched run is the original per-frame game = A's step sequence by construction.
```
## A (tick_head) group-end equality, walk+turn, 8 and 16 MHz
1mb_ski_walk  8 MHz: unpatched 80 passes, patched 77 passes (0 view sub-passes), paired U[0]=P[0], 77 ticks compared: IDENTICAL
1mb_ski_walk 16 MHz: unpatched 173 passes, patched 76 passes (0 view sub-passes), paired U[0]=P[2], 74 ticks compared: IDENTICAL
1mb_ski_turn  8 MHz: unpatched 114 passes, patched 78 passes (0 view sub-passes), paired U[0]=P[0], 78 ticks compared: IDENTICAL
1mb_ski_turn 16 MHz: unpatched 226 passes, patched 77 passes (0 view sub-passes), paired U[0]=P[3], 74 ticks compared: IDENTICAL
## B group-end equality
1mb_ski_walk  8 MHz: unpatched 81 passes, patched 389 passes (311 view sub-passes), paired U[0]=P[0], 78 ticks compared: IDENTICAL
1mb_ski_walk 16 MHz: unpatched 173 passes, patched 386 passes (309 view sub-passes), paired U[0]=P[3], 74 ticks compared: IDENTICAL
1mb_ski_turn  8 MHz: unpatched 114 passes, patched 387 passes (310 view sub-passes), paired U[0]=P[0], 77 ticks compared: IDENTICAL
1mb_ski_turn 16 MHz: unpatched 226 passes, patched 385 passes (308 view sub-passes), paired U[0]=P[4], 73 ticks compared: IDENTICAL
1mb_ski_stand  8 MHz: unpatched 59 passes, patched 382 passes (305 view sub-passes), paired U[0]=P[0], 59 ticks compared: IDENTICAL
1mb_ski_stand 16 MHz: unpatched 123 passes, patched 385 passes (308 view sub-passes), paired U[0]=P[2], 75 ticks compared: IDENTICAL
1mb_ski_busy  8 MHz: unpatched 59 passes, patched 387 passes (310 view sub-passes), paired U[0]=P[0], 59 ticks compared: IDENTICAL
1mb_ski_busy 16 MHz: unpatched 123 passes, patched 384 passes (307 view sub-passes), paired U[0]=P[2], 75 ticks compared: IDENTICAL
## B with turn 15 units/tick (poke w $24faa $01 $90 at apply: rate 400^3/64/65536)
1mb_ski_walk  8 MHz: unpatched 61 passes, patched 387 passes (309 view sub-passes), paired U[0]=P[0], 61 ticks compared: IDENTICAL
1mb_ski_stand 8 MHz: unpatched 61 passes, patched 372 passes (297 view sub-passes), paired U[0]=P[0], 61 ticks compared: IDENTICAL
```
Honest history: the first B run on stand/busy printed DIFFER (`$15110 $1cd7e $15118 $d5d8 $2d47e`); a standing player has a constant (x,z,speed,heading) key, so the tick pairing was
off by a few ticks (`$15118` the clock countdown differed). The key now includes `$15118` and the rerun above is IDENTICAL. Earlier, before `p3b_units`, B and A differed in objects/PRNG as explained in section 4;
that was the finding, not noise.
Sub-step interpolation, raw (`1mb_ski_walk`, 8 MHz, turn 15/tick, loop-top rows: VBL, PH, SKIP, `$15114`, E, H0, HG, x, z):
```
32726 PH 5 skip 1 x 25596 z 24254 hd 65059 rate 15 E 15 H0 65044 HG 65059 DX 65516 DZ 65442
32726 PH 1 skip 1 x 25590 z 24236 hd 65062 rate 15 E 15 H0 65059 HG 65074 DX 65506 DZ 65443
32726 PH 2 skip 1 x 25584 z 24217 hd 65065 ...      PH 3: x 25578 z 24199 hd 65068     PH 4: x 25572 z 24180 hd 65071
32727 PH 5 skip 1 x 25566 z 24161 hd 65074 rate 15 E 15 H0 65059 HG 65074   (heading = HG; position = the A tick's)
```
Not a pixel gate: B renders at different moments from A by design; A vs the original is pixel-for-pixel on any frame both render (`$12c88` scratch aside), not re-run here.

### 8.2 Presented frames per 1000 VBL (`mw1tick.py fps`; fps = flips / 20)

| snapshot | MHz | original | A | B |
|---|---:|---:|---:|---:|
| stand | 8 | 80 (4.0) | 81 (4.05) | 77 (3.85) |
| stand | 16 | 155 (7.8) | 100 (5.0) | 165 (8.25) |
| walk | 8 | 108 (5.4) | 100 (5.0) | 106 (5.3) |
| walk | 16 | 227 (11.4) | 100 (5.0) | 230 (11.5) |
| turn | 8 | 149 (7.45) | 100 (5.0) | 163 (8.15) |
| turn | 16 | 281 (14.1) | 100 (5.0) | 360 (18.0) |
| busy | 8 | 77 (3.9) | 77 (3.9) | 74 (3.7) |
| busy | 16 | 161 (8.05) | 101 (5.05) | 159 (7.95) |

(Raw lines of the batch: `1mb_ski_stand 8 MHz 80 81`, `... 16 MHz 155 100`, `1mb_ski_turn 16 MHz 282 100` for A vs `281 360` for B, etc.) A is capped at 5 fps by design (one
render per tick); B presents up to 25 fps and is limited by the renderer: where a frame takes more than 10 VBL (8 MHz stand/walk/busy: 9.3-13 VBL) B cannot beat the original, it
only keeps it (-4 % stand, -2 % walk, -4 % busy: the sub-step costs 16 k cycles each); where frames are shorter (turn 8 MHz, all of 16 MHz) it shows the extra frames (turn 16 MHz: 18.0 fps against 5.0 under A and
14.1 in the original, where the game itself ran at 14.7 steps/s). Full 25 fps needs frames < 2 VBL (P4).

### 8.3 World rate 8 vs 16 MHz on a cold boot

Cold-booted builds (HAGA defaults `pp_nofade pp_bigram_cache` + mine, 1 MB STE, TOS 1.62; section 8.4), `savemem` right after the Skiing view, then restored at 8 and at 16 MHz (`set_cpuclock`),
a real left click (walk), loop-top log for 1500 VBL (`tools` scripts were throw-aways; the numbers are `e VBL` stamps of the tick rows):
```
A1 (tick_head):  aligned 8MHz tick 0 = 16MHz tick 0; 157/157 ticks identical in (x, z, speed, heading)
    8 MHz: 156 ticks in 31.18 s = 5.003 ticks/s; path 4923 u = 157.9 u/s; heading 0; game clock +7 min
   16 MHz: 156 ticks in 31.18 s = 5.003 ticks/s; path 4923 u = 157.9 u/s; heading 0; game clock +7 min
B1 (p3b_*):      aligned 8MHz tick 0 = 16MHz tick 1; 156/156 ticks identical in (x, z, speed, heading)
    8 MHz: 155 ticks in 30.96 s = 5.006 ticks/s; path 4877 u = 157.5 u/s; heading 0; game clock +8 min
   16 MHz: 155 ticks in 31.00 s = 5.000 ticks/s; path 4877 u = 157.3 u/s; heading 0; game clock +7 min
```
(difference 0.1 %; the game clock is quantised: +7 or +8 in 31 s is the same 21-tick period.) The heading rate with a constant mouse accumulator (`w $24faa $01 $2c`, 300 -> 6 units/tick, 41 s windows):
```
A1  8 MHz 207 ticks 41.08 s = 5.039/s; heading 1242 = 30.23 u/s     A1 16 MHz 206 ticks = 5.002/s; 1236 = 30.01 u/s   (0.7 %)
B1  8 MHz 206 ticks 41.18 s = 5.002/s; heading 1236 = 30.01 u/s      B1 16 MHz 206 ticks = 5.002/s; 1236 = 30.01 u/s   (0.0 %)
```
Game clock: every gap between clock changes is 21 ticks at both clocks (A1 8/16 MHz, B1 8/16 MHz; 8 / 9 / 9 / 8 gaps all 21), 202-215 VBL = 209.4 / 209.9 / 209.6 / 210.1 VBL mean = 4.2 s per game minute (the
original: 259 VBL at 8 MHz standing, 141 at 16 MHz, `simtiming.md` section 4). Unpatched on the same snapshots: ticks per second 5.26 / 11.29 (walk) and 7.42 / 14.71 (turn) at 8 / 16 MHz.

### 8.4 Cold boots (`boot_to_game('M')`: Game Options -> PLAY -> Team -> Stark -> Decisions -> Skiing, then walk)

| build | machine | boot | `$B2FF8` | `$14e00` | walk |
|---|---|---:|---|---|---|
| A (`pp_nofade pp_bigram_cache tick_head`) | 1 MB STE TOS 1.62 | 112 s | `MWPO` | `4eb9000b31004e71` | 5.003 ticks/s at 8 and 16 MHz |
| B (`... p3b_head p3b_hook p3b_hud p3b_logic p3b_msg p3b_units`) | 1 MB STE TOS 1.62 | 112 s | `MWPO` | `4eb9000b31004e71` | 5.006 / 5.000 |
| A | 4 MB Mega STE TOS 2.06 | 103 s | `MWPO` | `4eb9000b31004e71` | 5.000 / 5.000 (67 ticks in 13.4 s each at 8 and 16 MHz) |
| B | 4 MB Mega STE TOS 2.06 | 103 s | `MWPO` | `4eb9000b31004e71` | 5.007 / 5.015; z 25959 -> 28937 at 8 MHz, walking, PH rows 1-5 present |

Final re-run of the B build through `tools/mw1tick.py cold` (one command per machine; the 4 MB run when started concurrently with the 1 MB run once failed in `boot_to_game` on a missed Options click, harness flakiness, so run them one at a time):
```
boot 112 s; marker MWPO; $14e00 4eb9000b31004e71; $b3100 48e7e080; state {'x': 25600, 'z': 25600, 'speed': 0, 'heading': 0, 'action': 0, 'exit': 0}      (1 MB STE TOS 1.62)
   8 MHz: 66 ticks in 13.02 s = 5.069 ticks/s; x 25600->25600 z 25899->28913 speed 225->48; clock 363->366
  16 MHz: 66 ticks in 13.18 s = 5.008 ticks/s; x 25600->25600 z 29057->30057 speed 51->278; clock 367->370
boot 103 s; marker MWPO; $14e00 4eb9000b31004e71; $b3100 48e7e080; state {'x': 25600, 'z': 25600, 'speed': 0, 'heading': 0, 'action': 0, 'exit': 0}      (4 MB Mega STE TOS 2.06)
   8 MHz: 66 ticks in 13.18 s = 5.008 ticks/s; x 25600->25600 z 25959->28925 speed 243->48; clock 365->368
  16 MHz: 66 ticks in 13.20 s = 5.000 ticks/s; x 25600->25600 z 29117->30426 speed 51->277; clock 369->372
```
(the 8 and 16 MHz walks sample different parts of the same descent, so only the tick rate is comparable there; the aligned per-tick equality is in 8.3.)

`$B3100` reads `48e7e080` (the head's `movem.l d0-d2/a0,-(a7)`) at both. `python3 tools/mw1patch.py build --floppy --only ...` also builds (all six sites are in the resident game MWA file 1); the floppy was not booted.

### 8.5 Other checks

* Resync: `$637e` poked from ~30575 to 8192 (`w $637e $20 $00`) in the middle of a run: next rows `LAST 30575 -> 8192`, `ACC` restarts at the pass length, no burst, ticks continue (raw rows `78..91` of the run: PH 5 -> 1 with `ACC 8, 0, 7, 5, 4, 2, 0 ...`).
* `S` (snipe) / `S` / `S` / `X` on `1mb_ski_stand` live-patched with B at 8 MHz: `$12d5e` `000131ae -> 00013f36 (PH 0, A passes) -> 000131ae (PH 5) -> 00013f36`, then `X` -> `$1efde = 1, $14ef6 = 1`; flips 19 / 14 / 19 per 200 VBL.
* Controls: `tick_head + p5_ctl_turn` against `p3b_* + p5_ctl_turn`, walk, 8 MHz, a one-off `$24faa` poke: `aligned 0 0 compared 77 ticks; differing regions: NONE`.

## 9. Open items / limits

* B does not make anything faster; it keeps A's world and lets the view follow real time. Below ~10 VBL per frame (16 MHz, or after P4) the frame rate rises above 5; at 8 MHz it equals the original's.
* Snipe (`$13f36`), buggy (`$1359a`), glider (`$1373c`) run as A passes (5 Hz render and 5 Hz view). Their steps have their own position code; not run, no snapshot ([INFERENCE] they would need their own sub-step).
* Static scenes: a standing player with no turn re-renders identical sub-step frames (25/s if the CPU allows). A static-frame skip keyed on `$12c60/$12c64/$12c98` would be valid (the view only changes on sub-steps), but must hook render calls only.
* `E`/`DX`/`DZ` are words (`$12c98` is a word); `trunc(k*E/5)` is truncation, so a turn of 1-4 units/tick moves the view only at PH 5 (heading granularity is 2 anyway: `& $3fe`).
* The first 3 hits of a Hatari `:file` breakpoint after arming were not logged in my traces; tick pairing is by state, not by index.
* TICK follows the VBL rate (50 Hz: 5 steps/s; 60 Hz: 6). [INFERENCE: not run on a 60 Hz or mono setup.]
