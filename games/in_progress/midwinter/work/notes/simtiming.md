# MW1 simulation timing: what advances per frame, real-time sources, 8 vs 16 MHz, hook sites

Agent: MW1Frame. Read-only study (live RAM pokes in an emulator only, nothing written to game files). Same snapshots, dump and method as
`frameloop.md` (read that first for the loop and the cycle shares). 1 MB STE, TOS 1.62, Hatari 2.6.1. All numbers are from my runs unless a
file is cited; `rate.py` = a throw-away flip logger (`b pc = $bd9a :trace :file` with `e VBL`, `e CycleCounter`, `m $12c60 8`, `m $15112 4`, `m $2c45a 2`,
`m $637e 2`, `m $152a8 2`, `m $24faa 2`, `m $12c98 2`), one row per flip.

## 1. Verdict

**Every simulated quantity is a fixed step per loop pass (= per presented frame). Nothing is scaled by elapsed time and no timer or VBL
counter is read by the simulation.** Game speed (movement, turning, game clock, spawn chances, object lifetimes) is therefore proportional to the
frame rate. One loop pass = one `$12e9c` step = one flip (`$14e04` and `$14e90` hit equally often in every trace). The rate is 4 to 7.5 steps/s at
8 MHz depending on the scene (section 5), and it doubles at 16 MHz. A fixed tick is needed (P3), and partial-B style per-tick scaling is
natural because the step is cheap (19.4k cycles of 1.63M).

## 2. The per-frame update map

All of these are reached from `sub_014e00` (see `frameloop.md` section 2). "Frame" = one pass.

### 2.1 Player: heading, speed, position (`sub_012e9c` -> `$131ae` -> `$13236` chain)

| quantity | address / format | update (disassembly) |
|---|---|---|
| mouse X / Y accumulators | `$24faa` / `$24fae` words, `$24faa` clamped to `[-$200,$1ff]` in `$12ff4/$13000` | **per VBL**: code at `$66c0` (`add.l d1,$24faa.l / add.l d0,$24fae.l / rts`), reached by `jmp (a0)` at `$66be` with `a0 = $62ac[$62b8*4]` (`$62b8 == 2` -> `$62b4 = $66c0`), called from the VBL handler `$61a8` via `bsr $65c0`; *consumed per frame* below |
| turn rate | `$15110` word | `$12fe2`: `d0=$24faa; d1=d0*d0>>6 (asr.l #6); d1*=d0; swap d1` = `d0^3/64/65536`; `$13014 move.w d1,$15110` |
| heading (master) | `$12c98` word, 1024 per turn (only `h & $3fe` is used, table index in bytes) | `$1301a: add.w d1,$12c98.l` once per frame |
| heading copy used by the mover | `$15114` word | `$1323a: move.w $12c98.l,$15114.l` |
| speed command | `$152a8` word (accumulator) | integrated each frame in `$131ae..$1348x`: `$13396 bsr $13040` (`d1 = clamp(d1+d0, 0, d2=$1353e)`), `$1339a move.w d1,$152a8`; stopped state `$1329a divu.w #3,d0 / $1329e move.w d0,$152a8` = `/3` per frame |
| speed (units) | `$15112` word | `$133a0 mulu.w $13548,d1 / asr.l #8 / asr.l #8 -> move.w d1,$15112` or `$13478 asr.w #6,d1 / move.w d1,$15112` (state `$13542`: >0 skiing, 0 stopped, <0 braking) |
| position | `$12c60` X, `$12c64` Z (longs; 512 units = 1 cell, `$12c5a=$200`; window bounds `$1388..$b478`) | `sub_014530` (`$13248`): `d0=sin(h)`, `d1=cos(h)` from `$1c6bc` (word table, cos at +$100, Q14: `$4000` = 1.0), `muls.w d2(=$15112)`, `swap`, `add.l d0,$12c60 / add.l d1,$12c64` = **speed/4 units per frame at most** (observed `-98` at speed 392) |
| cell + offset | `$12c68/$12c6a` words, `$12c6c/$12c6e` | `sub_0158f4/$159a4` (1059 + 2305 cycles) |
| terrain height / slope | `$12c5e`, `$17210`, `$1721c` | `sub_013078` (11716 cycles, the biggest part of the step), `$14716` |

Heading rate at the mouse clamp: `511^3/64/65536` = 31 units per frame max; the measured turn snapshot (`$24faa = 169`) turns +1 unit per frame (`169^3/64>>16 = 1`).
Heading unit = 1/1024 turn; observed: heading 0 = +Z, 256 = +X (per `mw1_state.md`).

### 2.2 Game clock (and what hangs off it)

| item | address | evidence |
|---|---|---|
| clock | `$2c45a` word = `$e4(a6)` of the HUD record `a6 = $2c376`: **minutes of the day** (360 = HUD 06:00, the start) | HUD `sub_00b54a`: `move.w $e4(a6),d0 ... divs.w #$3c,d0` (minutes), `divs.w #$18,d1 / swap` (hours mod 24); read in my runs: 362 (06:02) first row of `1mb_ski_stand`, 462/463 in `1mb_ski_walk`, `$1d0` = 464 in `ram_ski_walk.bin` |
| tick | `$14fd2: addq.w #1,$e4(a6)` inside `sub_014fac` (`$14e14`), no wrap check there | listing: `$14fc0 move.w $15118.l,d0 / dbra d0,$14fd6 / bsr.w $158be / move.w #$14,d0 / addq.w #1,$e4(a6) / move.w d0,$15118.l` |
| frames per game minute | `$15118` countdown from `$14`: the counter runs `$14..0` (20 frames) and the 21st pass falls through `dbra` | **measured exactly 21 flips between consecutive clock changes in all four rate runs** (stand8: 21,21,21,21,21; stand16: 21 x10; turn8: 21 x4; turn16: 21 x9) |
| per game minute | `sub_0158be`: `$2b194 + $2c3d6*$4a` record, byte `$3(a0)` decremented every 3rd call (`$158f2` counter reloads 2) | disassembly [INFERENCE: a character timer such as hunger/health] |
| time jump | `$13d34: add.w d4,$e4(a6)` | disassembly only; not seen running [INFERENCE: some travel/rest event] |

### 2.3 Fatigue / exit timers (per frame)

| address | what | evidence |
|---|---|---|
| `$2c422` byte | energy/stamina; `sub_012f9e` (`$12ea6`, 382 cycles/frame): `d0 = $1354c * $12fe0 / 100; $12fde = ($12fde + d0) & $3ff; $2c422 -= (...) >> 10`, clamped at 0 | `$12f9e..$12fdc` |
| `$14328` word (starts `$40`) | `sub_0142cc`: when `$2c422 == 0`, `subq.w #1,$14328` each frame; below 0 `$14dfc = 1` (ends the action mode) = a 64-frame countdown | `$142d0..$14312` |
| `$12c5e == 0` | `sub_012f3e` sets `$14dfc` and `$12f5a` | `$12f3e..$12f58` |
| `$14ee4` | message timer, `subq.w #1` per pass in `$14e98` | `$14e98..$14ea4` |

### 2.4 Units, aircraft, projectiles, spawn timers (objects)

Four object slots, stride `$2c`, at `$1cd7e`, `$1cdaa`, `$1cdd6`, `$1ce02`. `sub_020d52` (`$14e4a`) loops over them
(`$20d56 lea.l $1cd7e,a5 ... lea.l $2c(a5),a5 ... subq.w #1,$20d9a / bne`) and for each: `tst.w $26(a5)`; `<0` free; `==0` mark free (`move.w #$ffff,$26(a5)`);
`>0` active: `movea.l $28(a5),a6 / jsr (a6)`. So **each active object gets exactly one handler call per frame**.
Record fields seen in the spawn code (`$1fc6e`, `$20026..$200d8`, `$2012e..$201d8`):
`+2` long model pointer, `+6/+$a` longs world X/Z (same units as `$12c60`), `+$10/$12/$14` words zeroed, `+$16` word, `+$18/$1a` words direction sin/cos (from `$1f6f8`/`$20d9c`),
`+$1c/$20` longs target position (copy of the player position at spawn), `+$24` word hit points/range, `+$26` state, `+$28` handler pointer.

| slot | spawned by | handler | gate | notes |
|---|---|---|---|---|
| `$1cd7e` | `$1fc6e` (Space key, grenade: `$25136` counter) | `$208d6`; further handlers set in the same file at `$1fa78/$1fbb2/$1fc5a/$1fe30/$1fef0/$1ffba` = `$20ce2/$20728/$207c4/$20a52/$20b0a/$20be6` (slot of each not decoded) | `tst.w $26(a5)` must be free | `$24(a5) = $28`; `$16(a5) = $15112 + $12c` at spawn (`$1fcde..$1fce8`) |
| `$1cdaa` | `$1fa0a` when `$2bae0 != $1faa4` | `$20ce2` | | [INFERENCE] a friendly/target marker; not identified |
| `$1cdd6` | bombers `$1ffe0` (flag `$2c17c`, `$1fa08` bit 0) | `$2040e` | random timers `$20e4c` | per frame: `subq.w #1,$200e4` (starts `$c8` = 200 frames), `subq.w #1,$200e0`, range word `$200e2` toggled around `$1b58`; at `$200e4 < 0` calls `$1f830`; `$24(a5)` set each frame from the distance |
| `$1cdd6` | mortars `$200e8` (flag `$2c17e`, `$1fa08` bit 1) | `$20524` | random timers `$20e4a` | same record shape as the bomber, range `$bb8`, life `$fa`=250 |
| `$1ce02` | `$201e0` / `$202c6` | `$20594` (attack object, `mw1_state.md`), `$20776` | `$2c180` (Training) must be 0 for `$201e0` | `$20594` counts `$200e4` down and shrinks `$200e2` by `$7b7` per frame (from `mw1_state.md`); on contact `$2061a: move.w #1,$14dfc` |

Spawn timing: each spawner calls `sub_00d57e` (`$d598` multiply-with-carry PRNG, state `$d5d8/$d5da`; `$d57e`: random `mod d1`) once per pass with `d1 = $20e4c/$20e4a` and
spawns when the result is 0 (`tst.w d0 / bne.w exit`): a **per-frame Bernoulli draw**, so the spawn rate scales with the frame rate like everything else. `sub_020db4` (`$20e48`
interval from the distance to `$19cd4/$19cd6`) re-arms them. Initial PRNG seed `$d5d8` comes from `$4ba` in `sub_011c80` (menu code; `$4ba` is frozen at 0 in game, see section 4).

No other per-frame sim code was found in `$12000..$22000`: the list of `addq/subq #1,<abs.l>` in that range (counters) is `$13b5c` (vehicle handler), `$13b60`, `$14328`, `$2c448`
(`$1474e`), `$158f2`, `$12c86`..: each lives inside a function called once per pass.

## 3. Evidence that nothing is per-VBL or scaled by time

1. `--xref 637e` returns the VBL handler increment `$61ac` plus 14 sites in `$114cc..$120d2` (menu/text delays). **None of those addresses has a single hit in `walk.txt` or
   `stand.txt`** (checked all 15 against both profiles); the simulation never reads `$637e`.
2. `$4ba` (200 Hz), `$462`, `$466` are never read by the loop: `--xref 4ba` = `$64f6` (timer C handler), `$10234` (key-wait loop that increments it), `$11c94` (menu seed read), nothing else in `$12000-$22000`.
   They are not even running (section 4).
3. No `$fffa..` / `$ff8209` read exists in `$11000-$22000` except `btst #5,$fffa01` at `$112ca/$11308` (a disk wait, not executed in play).
4. Every per-frame variable above is advanced by a fixed amount in straight-line code and the **8 vs 16 MHz traces have identical per-frame deltas** (section 4).

## 4. 8 MHz vs 16 MHz per emulated second (measured)

Emulated time = VBL delta / 50 (`e VBL`; `$637e` agreed exactly: stand8 1486 vs 1486, stand16 1492 vs 1492, turn8 695 vs 695, turn16 699 vs 699).
After the restore I called `set_cpuclock(16)` which takes about a second of emulated time, so a 16 MHz run starts later in the move; positions are compared on
**aligned frames** (rows with identical `x, z, speed, heading`), as in `baseline.md`.

| quantity | 8 MHz | 16 MHz | ratio | window |
|---|---:|---:|---:|---|
| frames per emulated second (stand) | 4.07 | 7.44 | 1.83 | 1486 / 1492 VBL, 122 / 223 flips |
| frames per second (walk) | 4.62 (10.81 VBL/frame) | 11.0 (4.53 VBL/frame) | 2.4 (scene differs) | 28 / 67 flips |
| frames per second (turn) | 7.34 (6.81 VBL/frame) | 15.02 (3.33 VBL/frame) | 2.05 | 103 / 211 flips |
| **position, walk** (aligned 14 frames, identical rows) | z **-392.96 u/s** (x +21.5, path 393.5) | z **-785.92 u/s** (x +43.0, path 787.1) | **2.00** | 142 VBL vs 71 VBL |
| **position, turn** (aligned 86 frames) | path **92.4 u/s** (z -90.5, x -18.8) | path **186.3 u/s** | **2.015** | 538 VBL vs 267 VBL; dz -974, dx -202 in both |
| **heading, turn** (aligned 86 frames: +86 units) | **+7.99 /s** | **+16.10 /s** | **2.015** | same windows |
| heading, whole turn run | +7.34 /s (102 units / 695 VBL) | +15.02 /s (210 / 699) | 2.05 | |
| **game clock, stand** (5 vs 10 ticks) | 0.193 game-min/s = **5.19 s per game minute** (259.4 VBL) | 0.354 min/s = **2.83 s per game minute** (141.4 VBL) | 1.83 | 1297 VBL / 1414 VBL |
| game clock, turn (aligned 86 frames) | 5 ticks in 10.76 s (0.465/s) | 5 ticks in 5.34 s (0.936/s) | 2.015 | |
| flips per game minute | **21** | **21** | 1.00 | every gap in all four runs |

Per-frame rows are bit-identical between the two clocks (first 8 aligned turn frames, `(dx,dz,dheading)` per flip):
```
8 MHz : (-7,-55,1) (-7,-52,1) (-7,-49,1) (-7,-46,1) (-7,-44,1) (-7,-41,1) (-7,-39,1) (-7,-37,1)
16 MHz: (-7,-55,1) (-7,-52,1) (-7,-49,1) (-7,-46,1) (-7,-44,1) (-7,-41,1) (-7,-39,1) (-7,-37,1)
```
Hence movement per second, turn per second and the clock run **2.0 x (or the frame-rate ratio) faster at 16 MHz**; per-VBL scaling would have left both
windows equal. Raw start/end rows (`turn8` / `turn16`): `VBL 32864 x 25654 z 23102 spd 417 hd 65028 clk 463` ... `VBL 33559 ... hd 65130 clk 468` /
`VBL 32913 ... hd 65044 clk 463` ... `VBL 33612 ... hd 65254 clk 473`. (The heading word reads 65028 = `$fe04`: the master heading is a signed word that wrapped below 0; only bits 0..9 matter.)

Scene dependence at 8 MHz (the speed of the "original" game): stand 12.28 VBL/frame (4.07 steps/s), walk 10.81 (4.62), turn 6.81 (7.34); VBL/frame min..max 11..14, 9..13, 5..11.
A game minute is 21/(steps per s): 5.2 s standing, 4.5 s walking, 2.9 s turning, at 8 MHz.

## 5. Real-time sources

| source | where | state in the ski loop | usable? |
|---|---|---|---|
| **`$637e` word** | `$61ac: addq.w #1,$637e.l` in the game's own VBL handler (`$70 -> $61a8`) | **free-running** in the action mode: +1 per VBL (verified above, 1486/1486, 1492/1492, 695/695, 699/699); no reader or clearer executes in the loop; wraps at 65536 (21.8 min) so use `(new - old) & $ffff`; menu code clears it (`$114f6, $11958, $11a84, $11e24, $11eec, $120cc`) so re-read it when entering the loop | **Yes: the dt source** |
| `$2c31a` + `sub_006840` | VBL handler clears `$2c31a` at `$61b2`; `$6840: move.w #$ffff,$2c31a / tst.w / bne.b / rts` | not used by the loop | a ready-made "wait for next VBL" subroutine (no registers touched) |
| `$4ba` (hz200) | timer C vector `$114 -> $64f6: addq.l #1,$4ba.l` is installed (`$67f2..$6806`) | **frozen at 0**: `m $4ba` read `00000000` twice 4 s apart. MFP `IERA/IERB = $00/$40`, `IMRA/IMRB = $00/$40` (read `$fffa07/09/13/15`): only the keyboard ACIA interrupt is enabled; timers A, B, C, D are all off. `$fffa1d = $51`, `$fffa25 = $13` | dead; the vector is there, enabling IERB bit 5 / IMRB bit 5 would probably give 200 Hz [INFERENCE, untried] |
| TOS `$462/$466/$442` | | frozen (`$466 = $08080000`, `$462 = $01450809` identical 4 s apart): the game replaced vector `$70`, TOS VBL no longer runs | dead |
| `$d5d8/$d5da` | PRNG state | advanced per spawn test | not time |
| VBL handler content | `$61a8`: palette copy `$24f24`, `$69b8` (sound), `$65c0`/`$652e` (input scan), `$66c0` (mouse accumulation), dispatch `jsr (a0)` with `a0 = $62a0[$62b8*4]` (`$6290..$6298`) | in the action mode `$62b8 = 2` -> table entry `$62a8 = $0000675c` = `rts` | **free hook**: the table is data (`$62a0: 000063f4 00006380 0000675c 000066ce 00006712 000066c0`); changing the long at `$62a8` to a payload address gives a per-VBL callback inside the VBL handler (all registers already saved by `movem.l d0-d7/a0-a6` at `$61a8`) with no code splice [INFERENCE: untried; `$62a8` is shared with other modes using index 2] |

Game wait loops (all outside the action loop; each address has 0 hits in both profiles):
* `sub_006840` (VBL wait) callers `$5494, $550a, $552a, $5588, $55a8, $5628, $5648, $56e2, $11930` (jsr) and `$41ae, $41b8, $4296` (bsr): intro/title/menu code.
* `sub_00bf0c` (set palette index `d0`, waits one VBL via `$2c31a`, then `$24f24`): callers `$10892, $11d72, $12a78, $12b6a`.
* key waits: `clr.w $2c324 ... tst.w $2c324 / beq` loops at `$d0f4, $e00a, $fb5a, $fc8e, $100b4, $10168, $101bc, $10240, $102b8, $10e0e, $11392`...; `$10220..$10248` also increments `$4ba` in software while it waits.
* `$637e` timed delays in menu/text code: `$114cc, $11510, $11546` (`cmp.w $637e.l,d0`), `$11e2a`/`$11ef2` (`cmpi.w #$c8` = 200 VBL = 4 s), `$120d2` (`#$4b` = 75 VBL).
* disk: `btst.b #5,$fffa01` at `$112ca/$11308`.

Input timing: the keyboard/mouse interrupt `$6400` (ACIA) stores scancodes in `$2c324` and updates key state `$2c29a[]`; the mouse/joystick delta is integrated per VBL into `$24faa/$24fae` (`$66c0`);
the loop reads them once per frame. So input *sampling* is per VBL but *consumption* is per frame, and a held offset acts as a persistent rate ("yoke", same as `mw1_state.md`).

## 6. Hook sites for a fixed-tick scheduler (like MW2's loop head)

Free RAM for a payload: `$B3000..$BAFFF` (the `mw1patch.py` payload window); in the snapshot `m $b3000/$b3100/$b8000 16` read all zero.
The loop code is resident (identical in the Options-screen dump), so a hook can be applied at boot/load.

| id | site | bytes | what it gives |
|---|---|---|---|
| **H1 (recommended)** | `$14e00..$14e07`: `61 00 00 fa` (`bsr.w $14efc`) + `61 00 e0 96` (`bsr.w $12e9c`) | 8 -> `jsr tramp.l` + `nop` | the head of **every** frame (callers `$14ac0` loop, `$14a86` first frame, `$d1de`), before any logic or drawing. The trampoline re-issues `jsr $14efc` once and `jsr $12e9c` k times. `rts` lands at `$14e06` (the `nop`) -> `$14e08 tst.w $14dfc` as before |
| **H2** | `$14e14`: `jsr $14fac.l` | 6 -> `jsr tramp2.l` | HUD feed **and the game clock**: must run once per tick too (it ran twice in the test) |
| **H3** | `$14e90`: `jsr $bd9a.l` (flip) | 6 | the post-render point: wait for the tick boundary here (`jsr $6840` or spin on `$637e`) before the flip, as in "wait when ahead" |
| **H4** | `$14e56 jsr $18304`, `$14e5c jsr $19ce2` (81% of a walking frame, 88% standing) and `$14e1a $129d2`, `$14e20 $1580e`, `$14e50 $1d0a0`, `$14e6c $1bbe6`, plus the flip | 6 each | skip-render hooks (render only when not behind). They must be skipped together with the flip (frameloop.md section 5) |
| H5 | `$12e9c`: `movea.l $12d5e.l,a0 / jsr (a0) / bsr.w $12f9e` | | where the mode step is dispatched; useful if per-mode behaviour (ski vs buggy) is needed |
| H6 | long at `$62a8` (`$0000675c`, VBL dispatch entry 2) | 4 (data) | a per-VBL callback in the VBL handler (see the table above) |

Live test of H1+H2 (`/tmp/mw1f/rate2.py`, k = 2; two runs, `1mb_ski_turn` and `1mb_ski_walk`, 8 MHz):
```
loadbin  4eb900014efc 4eb900012e9c 4eb900012e9c 4e75   -> $b3200   (poll, sim, sim)
loadbin  4eb900014fac 4eb900014fac 4e75                 -> $b3220   (HUD+clock x2)
loadbin  4eb9000b3200 4e71                              -> $14e00
loadbin  4eb9000b3220                                   -> $14e14
readback: $14e00 4eb9000b32004e71  $14e14 4eb9000b3220
turn:  dheading per flip 2,2,2,2,2,2,2,2,2,2   (unpatched 1)   clock ticks at flips 0,11,21,32,42 (gaps 11,10,11,10; unpatched 21)
walk:  dz per flip -77,-66,-59,-53,-46,-41,-35,-31,...         (unpatched -98,-99,-97,-95,...) ; speed 177 -> 146 -> 126 -> 114 (decays 2x faster per flip)
```
The game ran to the end of the 250 VBL window, flips continued, no exit or hang. Notes for the design: the checksum `sub_012276` covers `$31698-$3ddb4` (object model data), not the loop code, so patching `$14e00` does not touch it (`baseline.md`);
the loop in `$14ac0..$14ae8` has no 6-byte site of its own (`bsr.w $14e00` is 4 bytes), which is why H1 patches the head of `sub_014e00` instead.

## 7. Open items / not done
* No fixed-tick patch was built or tuned (read-only phase). The tick rate to choose is a design decision: the 8 MHz game ran 4.1 / 4.6 / 7.3 steps per second (stand / walk / turn).
* Buggy and glider handlers (`$1359a`, `$1373c`) were not run; their per-frame behaviour is assumed to match through the shared loop [INFERENCE].
* `$13d34` clock jump, `$1fa0a` slot-1 purpose, `$158be` character byte and several slot handlers (`$20728..$20be6`) were not decoded.
* 16 MHz walk windows differ in scene from the 8 MHz ones (the 16 MHz run starts later in the move); that is why the walk fps ratio is 2.4, not a CPU effect.
