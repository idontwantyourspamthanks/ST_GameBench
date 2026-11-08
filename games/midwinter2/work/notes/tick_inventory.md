# Tick inventory: what a 25 Hz logic tick (P3 option B) has to scale

Author: TickInventory2. Scope: the in-game frame loop logic block `$31486-$315a4` (`frameloop.md`), which P3 option A runs at 5 Hz (`TICK = 10` VBL). Evidence is cited as disassembly addresses (`tools/m68dis.py` on `work/dumps/ram_ingame_lobos.bin`) or raw Hatari output (§5). Anything unobserved is marked **[INFERENCE]**.

## 0. Summary

* **Full B is not viable.** One logic pass costs 22 % of a frame (§1). Five passes per 5 Hz group add 88 % to the frame time. It would also need about 30 per-object counters, the RNG-driven fatigue drift, an exponential fall accumulator and the projectile table scaled one by one (§2).
* **Partial B is viable and its core is validated** (§5). Heading, lean and the position integrator, driven at 5 passes per original tick with the scratch patches, give exactly the 5 Hz game state at every group end:
  * straight walk: `$66e6/$66ea/$6742` identical for 12 groups;
  * turns: heading and lean identical;
  * turns, position: identical with the `_end` variant (§5.4); the as-found sub-tick-heading variant stays within the bounded lateral offset of §5.3.
* **A second, previously unlisted accumulator exists.** `$764c` (route/altitude, `$33f40`) steps +5 per tick on foot. It makes the HUD distance `$66e2/$6888` fall. Without a 1/5 patch it runs 5× fast (§5.6). `scratch_tick_alt` (new) fixes it and is validated.
* **Recommendation: partial B, foot type only first, scheduled with P4** (§4). A costs nothing until frames get faster than 10 VBL. Today they are 12.2 VBL. B is the thing that lets P4 gains show up at all.
* **Previous agent's status line "player-sim validated (straight + turning)" is only half true.** Straight: exact. Turning: heading exact, position off by up to 18 units (turnA, −14/tick) and 42 units (turnB, −50/tick) after 12 ticks (§5.3). That is a modelling difference, not an arithmetic bug (§5.3), and the exact variant is `scratch_tick_*_end.s`.

## 1. Cost of the logic block (measured, 1 MB STE snapshot `1mb_ingame_walking`, no patches)

Method: a `:trace :file` breakpoint at every `jsr` site of the loop, each logging `e CycleCounter`. Cost of call *i* is the delta to the next site. Median over about 165 frames. Cycle units are Hatari `CycleCounter` ticks; the loop sums to 1 287 k per frame, so only the shares are used below.

| Call site → routine | Median cycles | Share of loop |
|---|---:|---:|
| `$315a4` → `$1dbbe` renderer | 1 001 166 | 77.8 % |
| `$3158c` → `$19f54` HUD gauge draw | 157 126 | 12.2 % |
| `$31570` → `$33bca` player sim | 45 020 | 3.5 % |
| `$31546` → `$36ad8` projectiles | 30 696 | 2.4 % |
| `$31552` → `$34adc` visibility/aim lists | 19 956 | 1.6 % |
| `$3152a` → `$30130` object ref clear | 7 156 | 0.6 % |
| `$3149e` → `$2ea04` campaign/page layer | 6 176 | 0.5 % |
| all other logic calls (22 of them, each ≤ 2.3 k) | about 17 200 | 1.3 % |
| **logic block `$31486-$315a0`, incl. `$19f54`** | **283 334** | **22.0 %** |
| logic block excluding `$19f54` | 126 208 | 9.8 % |

Inside `$33bde` (separate run, 26 sites, 115 frames):

| Part | Cycles |
|---|---:|
| whole `$33bde` | about 43 100 |
| the two `bsr $34006` (`jsr $50c2` → `$1ba24` collision/arrival probe), at `$33dc6` and `$33e30` | 14 809 + 14 689 |
| control dispatch `$33c1e-$33c46` (rate → `$6740` → apply handlers; contains `$344ac` and `$345c4`) | about 5 300 |
| `$348ec` (range/bearing) | 2 513 |
| `$37a62` + `$37afa` (view matrix + cell) | 1 248 + 2 183 |

Consequences:
* `$19f54` draws gauges into the screen buffers (dirty flags `$1812a-$18138`, `$1813e` set by `$1a706`). It is rendering, not logic, and must run **once per presented frame**. The A patch currently re-runs it on every skipped tick.
* A fast 25 Hz sub-tick that is just the control dispatch costs about 5.3 k cycles (0.4 % of a frame). Calling whole `$33bca` costs 45 k (3.5 %).

## 2. Inventory: what advances per logic pass

Columns: *update* = address of the per-pass write; *format*; *1/5 exact?*; *method*. Methods:
* **ACC** = fractional accumulator (Q16 or Bresenham), cleared at the group start;
* **WORLD** = run only on the 5th sub-tick (the "world tick"), same as A;
* **LEVEL** = recomputed every pass from other state, so nothing to scale;
* **REAL** = already driven by the VBL or IKBD interrupt, so it is real-time.

### 2.1 Player (`$33bca` → `$33bde`, call at `$31570`)

| Quantity | Update (per pass) | Format | 1/5 exact? | Method |
|---|---|---|---|---|
| Position X/Y `$66e6/$66ea` | `$34504 add.l d0,$66e6.w`, `$34508 add.l d1,$66ea.w` in `sub_0344ac`; `Dx = floor(sin·speed/65536)` (`muls.w d2,d0; swap`, `$344f8-$34502`); sin/cos Q14 from `$44a4[$6294&$3fe]` and `+$100` | long, 1/512 cell (`$66e0 = 512`) | **Yes** at group end when sin and speed are constant over the group (validated, §5.2). With the heading changing per sub-tick the result differs by a bounded lateral offset (§5.3). Exact again if every sub-tick uses the heading the 5 Hz tick would end on (`_end` variants, §5.4). | ACC (Q16 remainder per axis), scratch `pos` / `pos_end` |
| Speed `$6772` | `$33f66` (`$764c` branch, flags bit0/6) or `$33fac` (`= $6750`, types 1-3 `·($688e+8)>>4`) | word | n/a | LEVEL (`$6750` is `clr.w`'d at `$33c02`, `+= $6740` at `$344bc`) |
| Heading `$6742` (+`$6294`, `$764a`) | `$345ee/$345f2/$345f6` in `sub_0345c4`: `h = (h + $f984 + $6740) & $3fe`; skipped when `$6220 = 4` (`$345c8`) | word, 10-bit even grid | **Yes** (Bresenham on `e = (f984+6740)&~1` in units of 2, remainder `S` word) — validated, 3 snapshots | ACC, scratch `hdg` / `hdg_end` |
| Lean `$674e` | `$34610`; `clr.w` at `$33bfe`, recomputed from the same `x` each pass (`$345fa-$34610`) | signed 10-bit | n/a: it is a level (turn rate), not an integral. Left unscaled; equals the original at every group end (§5.2-5.4). | LEVEL |
| Bank `$6746` | `$34656` in `sub_03461a`: `(($6746 + $6740) & $3fe)` sext10, clamped by table `$7250` unless flags bit0/6 (foot `$21`: not clamped); `$6740 = $675a>>4` (`$3411e`) | word | Yes with the same Bresenham as heading. **Not yet patched.** | ACC (new patch `bank`) |
| Pitch `$674a` | `$34674` in `sub_034660` | word | n/a | **Dead:** selector 6 does not occur in any of the 22 control blocks (dump of bytes `$30,$31,$33,$34,$36,$37,$3c,$3d`: values 0-5 only), so `$3499a[6]` is never selected |
| Route/altitude `$764c` | `$33f6a-$33f7a` in `sub_033f40` (flags bit0/6 types, incl. foot `$21`): `+= floor(thr·$7652/131072)`, clamp `[−8000,12000]`. Also `$345be` (`$34586`, sel 3: `+= $6740`, types 9/15/16/17) and `$33d9c/$33e14/$33e2c` (re-derived from range for other flags) | word | **Yes** with a Q16 accumulator on `P0 = thr·$7652`: `floor(ACC/655360)` | ACC (`scratch_tick_alt`, validated §5.6). Clamp boundary behaviour **[INFERENCE]**: not exercised |
| `$7680` (type `$11` fall) | `$33cce/$33cd2`: `$7680 *= 2`, `$764c += $7680` | word, exponential | **No** (doubling cannot be split) | keep type `$11` on A (5 Hz, unscaled) |
| Speed ramp `$688e` | `$33e74` in `sub_033e46`: ±1 per pass, 0..8, from `|$7646|>>10` | word | No (integer ±1) | WORLD |
| Throttle/yaw/button rates `$6752/$6756/$675a` | `$34172`-`$3430e` per selector: **direct** (sel 2) = clamp(level) | word | n/a | LEVEL (all of type 13). **Derivative** (sel 1, `$676a/$676c` = last input, types 15/17) and **integrator** (sel 3, `$6754`/`$675c`, type 16) are per-pass differences/sums: **No** | WORLD for those types |
| Fatigue drift `$f984` (`$f986` sign) | `$2f778/$2f772` in `sub_02f726`: random walk `±(rand&15)·$f986`, clamp ±32, RNG `$26fd0` (LCG `$6904/$6906`) every pass while `$efb4>1000 && $6750≠0` | word | **No** (random draw per pass) | WORLD; it is an input to `x` in `hdg`, constant between world passes, so the heading patch needs no change |
| Pre-move position copies `$66ee/$66f2/$66fe` | `$33be6/$33bec/$33bf2` | long, long, word | n/a | save **only at group start**: `$34006/$340a8` (arrival/collision) *revert* to them (`$34056`, `$340d4`). **Needs a gate patch**; observed skew in §5.7 |
| View matrix `$7662-$767a`, cell `$670a-$6710`, range `$66e4/$6774` | `$37a62`, `$37afa`, `$3489a`, `$348ec` | words | n/a | LEVEL; needed only once per rendered frame, i.e. at the world pass |
| View decay `$7646/$7648 / $6794` | `$37ae4/$37ae8 divs.w $6794.w` (`$6794 = 100`) | word | n/a | **LEVEL, not a decay across passes:** `$346a2` → `$347be` (foot, `$34708`/`$34748` others) reloads `$7646/$7648` from sin/cos of lean before every `$37a62`. The RAM dump has `$7648 = 163 = $4000/100`, i.e. a fresh reload divided once. Types with a separately written `$53a0/$53a2` **[INFERENCE]** same |

### 2.2 Game clock, timers, counters

| Quantity | Update | Format | 1/5 exact? | Method |
|---|---|---|---|---|
| Game-minute countdown `$6290` | `$1a70a dbra`, store `$1a73a`; reload `$753a[$6220] << $f970` (`$1a72e-$1a738`), foot: `16<<1 = 32`, so 33 passes per game minute | word | Yes if gated; reload×5 would also work but changes three table values | WORLD (observed 5× fast if ungated: §5.5) |
| Game clock `$eb8c` | `$1a716 addq.l #1,$eb8c` on countdown expiry | long, minutes | as above | WORLD |
| HUD message timers `$7590/$7582/$759c` | `$1a744/$1a74e/$1a758 subq` | word | No | WORLD |
| Odometer `$f968` / tick count `$f96c` (`$2f4b8`) | `$2f4f8 add.l`, `$2f4fe addq.w`; 5-game-minute settlement `$2f504-$2f5b2` (`$eb8c - $f974 >= 5`) | long, word | The ratio is scale-invariant, but settlement is clock-driven | WORLD (observed equal to the 5 Hz run when gated: §5.6) |
| `$66d4/$66d6` charge counter (`$33b7c`) | `$33b82 subq #2` while flag set (until <0), else `$33b9e +1` (cap `$1f5`) | word | No (steps −2/+1) | WORLD |
| Timers `$4072/$4074` (`$32f06`) | `$32f0e/$32f1a subq` to 0 | word | No | WORLD |
| SFX timer `$677c` (`$1aedc`) | `$1aee2 subq`; acts every second pass (`andi #1`) | word | No | WORLD |
| Sound/music `$7628/$7634` and the sequencer | `$262fc`, `$26308-$2633a` in the **VBL handler** | words | n/a | REAL; `$3232c` only polls `$762a/$7628` |
| Input ramps: IKBD mouse/keyboard/joystick accumulators `$6fb6/$6fba` (16.16), keyboard ramp `$75c8-$75f4` | `$26882` IRQ, `$26c1e`/`$26b58` from the VBL (`$262c8/$262cc`) | long | n/a | REAL. The per-pass consumer only clamps and reads the high word (`$347f2/$3481e` → `$6766/$6768`), so finer passes see more samples with no change of semantics. P5 direct control must be applied in the 25 Hz pass |

### 2.3 AI, vehicles, projectiles and the other logic calls (sites at `$31498-$3158c`)

| Site → routine | What it does (disassembly) | Per-pass state | 1/5 exact? | Method |
|---|---|---|---|---|
| `$31498 $2e36e`, `$3149e $2ea04`, `$314ba $2d4be`, `$314d2 $2dad2`, `$31504 $2e756` | campaign/page/overlay layer driven by `$eb8c − $e218 ≥ 3` and `$eb96`; date fields from `$eb8c` | gated by the game clock, idempotent | n/a | WORLD (clock-driven) |
| `$31512 $2f4b8` | odometer + 5-game-minute fatigue/stamina settlement (`$efb2`) | see 2.2 | No | WORLD |
| `$31518 $2fa0a` | proximity (`|dx|,|dy| < $200`) test of the player against records `$4bfa8`+, stride 16 (count `$6f78`), `$eb8c` cooldown `$f978/$f97c` | event latch | n/a | WORLD |
| `$3151e $2f968` | stamina-zero failure (early-out `$efb2≠0`, `$efb0≠0`); contains the only blocking `$7020` waits | edge event | n/a | WORLD |
| `$31524 $2f726` | fatigue drift | see 2.1 | No | WORLD |
| `$3152a $30130` | clears `+8` of the lists `$efc0` (stride `$30`) and `$b3aa` (stride `$10`), recounts `addq $8(a3)` from the NPC table (`$30192`) | per-pass level, must pair with `$34adc/$34bbe` | n/a | WORLD |
| `$31530 $3232c` | `$762a/$7628` sound-script state machine | timers are VBL-driven | n/a | WORLD (or any) |
| `$31536 $33b7c` | charge counter | see 2.2 | No | WORLD |
| `$3153c $350c4` | counts the NPC table `$3532-$3cee` by class `$3a` into `$6820/$6822/$6824/$6826` | level | n/a | WORLD |
| `$31542 $1aedc`, `$31564 $18e44`, `$31568 $1b43a`, `$3158c $19f54` | SFX timer (2.2); mode HUD text (`$732c`, `$19218`); **key events from `$7686[]` (one-shot, `clr.b 1(a0)` at `$1b446`)**; HUD gauge draw | one-shot reads / draw | n/a | WORLD, except `$19f54` which is once per **presented frame** |
| `$31546 $36ad8` (+`$36b08`, `$36eb2`) | **projectiles/moving objects**, table `$40e4`, count `$40ba`, stride `$1e`: `t(+6) += speed(+8)` (`$36b24-$36b2e`), position = `dir·t·4>>16 + origin`, path-table stepping `+$12 += $18` (`$36b7a`), end timer `subq.b $1d` (`$36bd8`), hit test `$36eb2` | word per entry; observed 20 entries stepping by constants 2, 3, 5 per pass in the walking snapshot | **No** (integer steps ÷5 are not integers; each entry would need its own accumulator) | WORLD (as A: fast projectiles are as choppy as in A) |
| `$31552 $34adc`, `$31558 $34bbe` | visibility/aim lists over `$b3aa` (stride `$10`) and `$efc0` (stride `$30`), `$6824 < 5` limit, using `$66e6/$66ea` via `$318c4`; `addq $8(a0)` | per-pass level | n/a | WORLD |
| `$3155e $335ce` | objective arrival and mode switches (modes 5/`$b`/`$15`, `$6888 + $6884 ≥ $6886`) | edge | n/a | WORLD |
| `$31576 $359c2` | **NPC/vehicle table** `$3532-$3cee`, 30 entries × `$42`: state `$3a` (0-`$f`, dispatch `$35b30`), countdowns `$36/$38/$3c` (`subq` at `$35b9e`, `$35bc6`, `$35be8`, `$35bf6`), speed ramp `$18` via `$36ac4` (`+= accel`, clamp `$6(a0)`), positions `$6/$a`, `$22/$26`; weapon fire `$36a7e` | per-entry words/longs | **No** | WORLD |
| `$3157c $351a8` | effects table `$3cee-$3fbe`, stride `$18`: countdown `$14(a5)` (`subq` at `$3521c`), dispatch `$351ea` | word | No | WORLD |
| `$31582 $1a706` | clock (2.2), HUD value writers (`$180fe` compass from `$6294`, `$18108` lean, `$18102` speed, `$1810e` route, …), dirty flags `$1812a-$18138` | levels + dirty flags | n/a | WORLD (so the HUD gauges update at 5 Hz) |
| `$31586 $32ee0`, `$3148a/$3156c $32574` | HUD numerics from `$670a/$670c` (`$66b8/$66ba`), video scroll regs | level | n/a | WORLD |
| `$315a0 $20272` | view/projection setup from `$66e6/$66ea` | level | n/a | per rendered frame (after the last sub-tick) |

Types: `$6220` indexes the control block at `$54dc0 + $6220·$3e`. Selector bytes (dump): throttle-apply `$30` ∈ {1,3,5}, heading-apply `$33` ∈ {3,4,5}, button-apply `$36` ∈ {0,1,3,5}; type 4 skips heading (`$345c8`). The special bodies for types `$f` (`$33c60-$33ca6`), `$10` (`$33d26`), `$11` (`$33cc2`) and `$14` (`$33daa`) call `$344ac` with their own `$6740` and accumulate `$764c` themselves. **Only type 13 (foot) was run for validation**; other types stay on A until each is tested.

## 3. Options and cost

| Option | What it is | Cost per group of 5 passes | Patch count | Risk |
|---|---|---:|---:|---|
| Full B | whole logic block each pass, every counter above scaled | 5 × 22 % = 110 % of a frame | ≥ 25 (every WORLD row needs a hand-made fraction; projectile/NPC tables have no spare per-entry state; type `$11` impossible) | high: RNG consumption changes, per-entry rounding, one-shot key events |
| **Partial B** | passes 1-4 = player-motion path only; pass 5 = whole block as in A | 4 × (0.4 % control dispatch, or 3.5 % if whole `$33bca`) + A | 7 (below) | medium, see below |
| Stay A | 5 Hz, frame cap | 0 | 3 (already shipped) | none, but the cap throws away every P4 gain above 5 fps |

Partial B patch list (all exist as ideas or scratch; the first four are validated):

1. `tick_head`: scheduler at 25 Hz (TICK = 2 VBL), pass counter PH 1..5, fast path for PH 1..4, world pass at PH 5 (`scratch_tick_gate` is the prototype of the fast path: `jsr $33bca` then `jmp $31486`).
2. `tick_render`: unchanged logic (skip when behind).
3. `pos` (`$344f8`): Q16 remainder, validated.
4. `hdg` (`$345dc`): Bresenham, validated.
5. `alt` (`$33f56`, `$764c`): new, validated.
6. `bank` (`$3461a`, `$6746`): not written; same Bresenham as `hdg`.
7. `save` (`$33be6-$33bf2`): save the pre-move position only at PH = 1 so the collision/arrival revert undoes the whole 5 Hz step (observed skew §5.7).

Plus a per-mode switch (one word, tested in `pos`/`hdg`/`alt`/`bank`): scale 1/5 only for modes whose control block uses the generic path and that have been tested; other modes use divisor 1 and the A schedule. About 600-700 bytes of blob, from `$B3000`+.

Risks, ranked:
1. **Per-type validity.** Only type 13 is tested; types `$f/$10/$11/$14` have private accumulators (`$7680` doubling). Mitigated by the mode switch.
2. **Order skew.** The world calls that precede the player sim (`$31512-$31568`) see the player at the end of pass 4, i.e. 0.8 of a tick **newer** than in A. Observed as ±1 on `$6888` (§5.7). An order-exact split, with passes 1 and 5 entering the loop at different points, removes it. The loop is flat code, so this is a different entry label, not an extra site per call.
3. **Collision revert semantics** (`$66ee`, `$34006`): needs patch 7.
4. **P5 interaction:** direct mouse control must write heading/pitch per 25 Hz pass; do it after this lands.
5. **Clamp boundaries** in `alt` and `bank` (see 2.1).

## 4. Recommendation

**Partial B (player motion at 25 Hz, everything else at 5 Hz), but only as part of P4, not before.**
* Today a frame is 12.2 VBL at 8 MHz on a 1 MB STE (`baseline.md`), and the A tick is 10 VBL, so A costs nothing yet. As soon as P4 brings a frame below 10 VBL, A caps the game at 5 fps and discards the gain. B lets the view run at the render rate (up to 25 fps) with 25 Hz motion.
* Reject full B (§3): cost plus many un-scalable counters.
* The 5 Hz world is consistent with the 25 Hz view by construction: every WORLD item is advanced exactly once per original tick, in the same pass as the group's last sub-step, so game clock, odometer, fatigue, AI, projectiles and event timing are the A values (validated for clock/odometer in §5.6).
* A mid-air slice that stays in the 5 Hz world: AI vehicles and bullets move at 5 Hz while the player glides at 25 Hz. This is the same as A, where the whole world moves at 5 Hz; only the player becomes smoother.

Estimated effort: 7 patch files (4 validated or nearly), one regression pass per player type. Added CPU at 25 Hz: about 1.6 % of a frame with a purpose-built fast path (4 extra 5.3 k passes per 5 Hz group), about 14 % if the fast path just calls `$33bca`.

## 5. Dynamic validation of the partial-B core

### 5.1 Setup

* Snapshot `work/snapshots/1mb_ingame_walking.sav`, restored in Hatari 2.6.1 via the harness (`Hatari(snapshot=...)`). The start frame is identical for control and patched runs: at the first `pc = $26e98` (flip) after `VBL > current+3` the live patch (`loadbin` + `w` site bytes from `mw2patch.py live`) is applied, the state is dumped, and then each hit of `pc = $3450c` (the instruction after the position integrator) dumps `m $66e6 8`, `m $6742 2`, `m $6294 2`, `m $764a 2`, `m $674e 2`, `m $6740 2`, `m $6772 2`, `m $f984 2`, `m $b41c0 2` (PH).
* Control: unpatched, one hit per tick (row *k* = state after tick *k*; row 0 = state at the apply instant).
* Patched: `scratch_tick_head` makes every pass of the loop one sub-tick. PH counts 1..5 and only PH = 5 renders. The patched row **5k** is the end of group *k*. The patch sets are `hr` (head+render), `pos` (+`pos`), `all` (+`hdg`), `end` (head+render+`pos_end`+`hdg_end`), `gate` (`scratch_tick_gate` replaces the head), `gatealt`, `gatealt_end`.
* Turn snapshots, built from the walking snapshot (`/tmp/ti2/turnA.sav`, `turnB.sav`, not committed):
  * `h.rel(-300,0)` as suggested gives `$6fb6 = $ff79 = −135`, which is inside the deadzone 150 of the type-13 block (`$12(a0) = $96`), so **no turn**: heading stayed `$0300`, `$6752 = 0`:
    ```
    > m $6fb6 8     00006FB6: ff 79 00 00 01 42 00 00
    > m $6742 2     00006742: 03 00
    > m $6752 2     00006752: 00 00
    ```
  * turnA: `h.rel(-390,0)`: `$6fb6 = $ff51` (−175), `$6752 = $ff38` (−200), `$6740 = −13`, effective `e = x&~1 = −14` per tick.
  * turnB: `w $6fb6 $ff $06 $00 $00` (−250): `$6752 = $fce0` (−800), `$6740 = −50` per tick.
* All three runs have `$f984 = 0` and `$efb4 = 0` (no fatigue drift); the walking one has bank `$6746 = 32`, so `$764c` moves +5/tick.

### 5.2 Straight walk (heading 768, speed 217, `P = −3 555 328`, not a multiple of 65536·5)

`scratch_tick_head + render + pos + hdg`:

```
=== walk: control rows (tick k = row k) vs patched group ends (row 5k)   [all_]
 k | ctl X,Y,H,lean | patched X,Y,H,lean | dX dY dH
 0 |  11210  25600  768     0 |  11210  25600  768     0 | +0 +0 +0  (PH=0)
 1 |  11155  25600  768     0 |  11155  25600  768     0 | +0 +0 +0  (PH=5)
 2 |  11100  25600  768     0 |  11100  25600  768     0 | +0 +0 +0  (PH=5)
 3 |  11045  25600  768     0 |  11045  25600  768     0 | +0 +0 +0  (PH=5)
 4 |  10990  25600  768     0 |  10990  25600  768     0 | +0 +0 +0  (PH=5)
 5 |  10935  25600  768     0 |  10935  25600  768     0 | +0 +0 +0  (PH=5)
 6 |  10880  25600  768     0 |  10880  25600  768     0 | +0 +0 +0  (PH=5)
 7 |  10825  25600  768     0 |  10825  25600  768     0 | +0 +0 +0  (PH=5)
 8 |  10770  25600  768     0 |  10770  25600  768     0 | +0 +0 +0  (PH=5)
 9 |  10715  25600  768     0 |  10715  25600  768     0 | +0 +0 +0  (PH=5)
10 |  10660  25600  768     0 |  10660  25600  768     0 | +0 +0 +0  (PH=5)
11 |  10605  25600  768     0 |  10605  25600  768     0 | +0 +0 +0  (PH=5)
12 |  10550  25600  768     0 |  10550  25600  768     0 | +0 +0 +0  (PH=5)
```

Passes within groups 1-2 (`$66e6` only moves by −11 per pass, 5 × −11 = −55 = the original step `floor(−54.25) = −55`):
`11199 11188 11177 11166 **11155** 11144 11133 11122 11111 **11100**`.

### 5.3 Banked turns, as-found scratch patches (`pos` uses the sub-tick heading `$6294`)

```
=== turnA (−14/tick): control rows vs patched group ends
 k | ctl X,Y,H,lean | patched X,Y,H,lean | dX dY dH
 0 |  11399  25561  794   -14 |  11399  25561  794   -14 | +0 +0 +0  (PH=0)
 1 |  11344  25564  780   -14 |  11345  25566  780   -14 | +1 +2 +0  (PH=5)
 2 |  11289  25563  766   -14 |  11290  25566  766   -14 | +1 +3 +0  (PH=5)
 3 |  11235  25557  752   -14 |  11235  25562  752   -14 | +0 +5 +0  (PH=5)
 4 |  11181  25547  738   -14 |  11181  25553  738   -14 | +0 +6 +0  (PH=5)
 5 |  11128  25532  724   -14 |  11128  25540  724   -14 | +0 +8 +0  (PH=5)
 6 |  11077  25513  710   -14 |  11076  25522  710   -14 | -1 +9 +0  (PH=5)
 7 |  11027  25489  696   -14 |  11026  25500  696   -14 | -1 +11 +0  (PH=5)
 8 |  10980  25461  682   -14 |  10978  25474  682   -14 | -2 +13 +0  (PH=5)
 9 |  10935  25429  668   -14 |  10932  25444  668   -14 | -3 +15 +0  (PH=5)
10 |  10893  25394  654   -14 |  10889  25410  654   -14 | -4 +16 +0  (PH=5)
11 |  10854  25355  640   -14 |  10849  25372  640   -14 | -5 +17 +0  (PH=5)
12 |  10819  25313  626   -14 |  10812  25331  626   -14 | -7 +18 +0  (PH=5)
=== turnB (−50/tick)
 k | ctl X,Y,H,lean | patched X,Y,H,lean | dX dY dH
 1 |  11481  25567  790   -50 |  11482  25573  790   -50 | +1 +6 +0
 2 |  11427  25557  740   -50 |  11428  25570  740   -50 | +1 +13 +0
 3 |  11378  25532  690   -50 |  11377  25551  690   -50 | -1 +19 +0
 4 |  11339  25493  640   -50 |  11334  25517  640   -50 | -5 +24 +0
 5 |  11314  25444  590   -50 |  11303  25472  590   -50 | -11 +28 +0
 6 |  11304  25390  540   -50 |  11287  25420  540   -50 | -17 +30 +0
 7 |  11311  25336  490   -50 |  11287  25365  490   -50 | -24 +29 +0
 8 |  11334  25286  440   -50 |  11303  25313  440   -50 | -31 +27 +0
 9 |  11370  25246  390   -50 |  11334  25269  390   -50 | -36 +23 +0
10 |  11417  25219  340   -50 |  11377  25236  340   -50 | -40 +17 +0
11 |  11470  25207  290   -50 |  11428  25218  290   -50 | -41 +11 +0
12 |  11523  25212  240   -50 |  11482  25216  240   -50 | -41 +4 +0
```

Results:
* **Heading (`H`) and lean are bit-identical** in every group of both snapshots: dH = 0 and lean equal for k = 0..12.
* **Position is not equal in turns:** max |dX|/|dY| over 12 groups is 7/18 (turnA) and 42/30 (turnB). Cause: the original takes one step per tick along the heading the tick **ends** on (`sub_0345c4` runs before `sub_0344ac`, `$33c2e` before `$33c36`); the sub-tick variant steps along the intermediate headings `H0 + e·j/5`, a path that lags the end heading by about 2/5 e per tick. Lateral offset per tick ≈ speed · sin(0.4 e) (turnB: 55 · sin(0.4·50·2π/1024 rad) ≈ 6.6 per tick; observed +6 in Y at k=1).
* Raw excerpt for turnA (control, then patched passes; PH in the last column):
```
CONTROL (unpatched) turnA, hit = pc $3450c, one row per tick (#00 = state at apply time)
#00 66E6:00 00 2c 87 00 00 63 d9  6742:03 1a  674E:ff f2  B41C0(PH):00 00
#01 66E6:00 00 2c 50 00 00 63 dc  6742:03 0c  674E:ff f2  B41C0(PH):00 00
#02 66E6:00 00 2c 19 00 00 63 db  6742:02 fe  674E:ff f2  B41C0(PH):00 00
#03 66E6:00 00 2b e3 00 00 63 d5  6742:02 f0  674E:ff f2  B41C0(PH):00 00
#04 66E6:00 00 2b ad 00 00 63 cb  6742:02 e2  674E:ff f2  B41C0(PH):00 00

PATCHED (head+render+pos+hdg) turnA, one row per pass; group ends = PH 05
#00 66E6:00 00 2c 87 00 00 63 d9  6742:03 1a  674E:ff f2  B41C0(PH):00 00
#01 66E6:00 00 2c 7c 00 00 63 da  6742:03 16  674E:ff f2  B41C0(PH):00 01
#02 66E6:00 00 2c 71 00 00 63 db  6742:03 14  674E:ff f2  B41C0(PH):00 02
#03 66E6:00 00 2c 66 00 00 63 dc  6742:03 10  674E:ff f2  B41C0(PH):00 03
#04 66E6:00 00 2c 5b 00 00 63 dd  6742:03 0e  674E:ff f2  B41C0(PH):00 04
#05 66E6:00 00 2c 51 00 00 63 de  6742:03 0c  674E:ff f2  B41C0(PH):00 05
#06 66E6:00 00 2c 46 00 00 63 de  6742:03 08  674E:ff f2  B41C0(PH):00 01
#07 66E6:00 00 2c 3b 00 00 63 de  6742:03 06  674E:ff f2  B41C0(PH):00 02
#08 66E6:00 00 2c 30 00 00 63 df  6742:03 02  674E:ff f2  B41C0(PH):00 03
#09 66E6:00 00 2c 25 00 00 63 df  6742:03 00  674E:ff f2  B41C0(PH):00 04
#10 66E6:00 00 2c 1a 00 00 63 de  6742:02 fe  674E:ff f2  B41C0(PH):00 05
```
  Heading steps per pass `$31a → $316 → $314 → $310 → $30e → $30c` = −4, −2, −4, −2, −2 = −14 (Bresenham on the grid of 2); group 2 ends at `$2fe` = control tick 2 (`$2fe`).

### 5.4 Exact variant: sub-ticks move along the heading the 5 Hz tick ends on

New scratch files `scratch_tick_hdg_end.s` (stores `HF = ($6742 + e)&$3fe` at PH = 1) and `scratch_tick_pos_end.s` (reloads sin/cos from `HF`, same remainder accumulator). Same snapshots and start frame:

```
=== turnA (variant scratch_tick_pos_end + scratch_tick_hdg_end)
 0 ctl  11399  25561 H 794 lean -14 | patched  11399  25561 H 794 lean -14 | d=(0, 0, 0, 0)
 1 ctl  11344  25564 H 780 lean -14 | patched  11344  25564 H 780 lean -14 | d=(0, 0, 0, 0)
 2 ctl  11289  25563 H 766 lean -14 | patched  11289  25563 H 766 lean -14 | d=(0, 0, 0, 0)
 3 ctl  11235  25557 H 752 lean -14 | patched  11235  25557 H 752 lean -14 | d=(0, 0, 0, 0)
 4 ctl  11181  25547 H 738 lean -14 | patched  11181  25547 H 738 lean -14 | d=(0, 0, 0, 0)
 5 ctl  11128  25532 H 724 lean -14 | patched  11128  25532 H 724 lean -14 | d=(0, 0, 0, 0)
 6 ctl  11077  25513 H 710 lean -14 | patched  11077  25513 H 710 lean -14 | d=(0, 0, 0, 0)
 7 ctl  11027  25489 H 696 lean -14 | patched  11027  25489 H 696 lean -14 | d=(0, 0, 0, 0)
 8 ctl  10980  25461 H 682 lean -14 | patched  10980  25461 H 682 lean -14 | d=(0, 0, 0, 0)
 9 ctl  10935  25429 H 668 lean -14 | patched  10935  25429 H 668 lean -14 | d=(0, 0, 0, 0)
10 ctl  10893  25394 H 654 lean -14 | patched  10893  25394 H 654 lean -14 | d=(0, 0, 0, 0)
11 ctl  10854  25355 H 640 lean -14 | patched  10854  25355 H 640 lean -14 | d=(0, 0, 0, 0)
12 ctl  10819  25313 H 626 lean -14 | patched  10819  25313 H 626 lean -14 | d=(0, 0, 0, 0)
ALL EQUAL
=== turnB (variant scratch_tick_pos_end + scratch_tick_hdg_end)
 0 ctl  11535  25560 H 840 lean -50 | patched  11535  25560 H 840 lean -50 | d=(0, 0, 0, 0)
 1 ctl  11481  25567 H 790 lean -50 | patched  11481  25567 H 790 lean -50 | d=(0, 0, 0, 0)
 2 ctl  11427  25557 H 740 lean -50 | patched  11427  25557 H 740 lean -50 | d=(0, 0, 0, 0)
 3 ctl  11378  25532 H 690 lean -50 | patched  11378  25532 H 690 lean -50 | d=(0, 0, 0, 0)
 4 ctl  11339  25493 H 640 lean -50 | patched  11339  25493 H 640 lean -50 | d=(0, 0, 0, 0)
 5 ctl  11314  25444 H 590 lean -50 | patched  11314  25444 H 590 lean -50 | d=(0, 0, 0, 0)
 6 ctl  11304  25390 H 540 lean -50 | patched  11304  25390 H 540 lean -50 | d=(0, 0, 0, 0)
 7 ctl  11311  25336 H 490 lean -50 | patched  11311  25336 H 490 lean -50 | d=(0, 0, 0, 0)
 8 ctl  11334  25286 H 440 lean -50 | patched  11334  25286 H 440 lean -50 | d=(0, 0, 0, 0)
 9 ctl  11370  25246 H 390 lean -50 | patched  11370  25246 H 390 lean -50 | d=(0, 0, 0, 0)
10 ctl  11417  25219 H 340 lean -50 | patched  11417  25219 H 340 lean -50 | d=(0, 0, 0, 0)
11 ctl  11470  25207 H 290 lean -50 | patched  11470  25207 H 290 lean -50 | d=(0, 0, 0, 0)
12 ctl  11523  25212 H 240 lean -50 | patched  11523  25212 H 240 lean -50 | d=(0, 0, 0, 0)
ALL EQUAL
```

Per-pass path inside groups 1-2 of turnB (control tick ends in the header line):
```
control tick ends: (11535,25560,840) (11481,25567,790) (11427,25557,740)
pass PH | smooth (pos, sub-tick heading)   X     Y   H | exact (pos_end)  X     Y   H
 1  1   | 11524 25564 830 | 11524 25561 830
 2  2   | 11514 25567 820 | 11513 25562 820
 3  3   | 11504 25570 810 | 11502 25564 810
 4  4   | 11493 25572 800 | 11491 25565 800
 5  5   | 11482 25573 790 | 11481 25567 790      <- control tick 1: 11481 25567 790
 6  1   | 11471 25573 780 | 11470 25565 780
 ...
10  5   | 11428 25570 740 | 11427 25557 740      <- control tick 2: 11427 25557 740
```
**Choice (open for you):** the smooth variant (`pos`) follows the arc of a continuous turn (25 Hz heading, 25 Hz displacement along the current heading) but gives positions that differ from the 5 Hz game by the offsets above; the exact variant (`pos_end`) reproduces the 5 Hz game bit-for-bit at every group boundary but, within a group, moves along the end heading (a crab-like slip of up to `e` degrees). I would ship `pos`/`hdg` (smooth) unless bit-exact replays are needed, but the exact pair is there and passes.

### 5.5 What happens without scaling (necessity of the patches)

`hr` (head + render only), straight walk: X per group −275 (5 × the original −55):
```
group  X(ends)      $6290 (clock countdown)
0      11210        26
1      10935        22      (control: 11155 / 26)
2      10660        17
3      10385        12
4      10110        7
5      9835         2
```
`pos` only (no `hdg`), turnA: heading −70 per group instead of −14 (5×); `H` = 794 → 724 → 654 → 584 → 514 → 444.

All-passes un-gated (`all`; the whole logic block runs each pass), straight walk, group ends vs control:
```
k   $6290 ctl/pat   odo/cnt ($f968/$f96c) ctl         ... pat          $764c ctl / pat
1   26 / 22          5985/105                          6213/109          3316 / 3336
2   25 / 17          6042/106                          6498/114          3321 / 3361
3   24 / 12          6099/107                          6783/119          3326 / 3386
```
The game-minute countdown, the odometer and `$764c` all run 5× faster, which is the argument for WORLD gating.

### 5.6 Gated partial-B prototype (`scratch_tick_gate`, +`pos`, `hdg`/`hdg_end`, `alt`)

PH 1..4 run only `jsr $33bca` and loop back; PH 5 runs the whole block and renders. Both runs are sampled at `pc = $31590` (end of the logic block; in the patched run it is reached only at PH 5). Straight walk with `gate + render + pos + hdg + alt`:

```
===== z_gatealt_walk vs z_ctl_walk   (end-of-logic sample at $31590; patched rows = pass 5 of group k)
k= 1 ctl X=11155 Y=25600 H=768 $6290=25 $eb8c=2178 odo=5985/105 $764c=3316 $66e2=585 $66e4=2731 $6888=586 $66ee=(11210, 25600)
     pat X=11155 Y=25600 H=768 $6290=25 $eb8c=2178 odo=5985/105 $764c=3316 $66e2=585 $66e4=2731 $6888=585 $66ee=(11166, 25600)  PH=5
k= 2 ctl X=11100 Y=25600 H=768 $6290=24 $eb8c=2178 odo=6042/106 $764c=3321 $66e2=584 $66e4=2737 $6888=585 $66ee=(11155, 25600)
     pat X=11100 Y=25600 H=768 $6290=24 $eb8c=2178 odo=6042/106 $764c=3321 $66e2=584 $66e4=2737 $6888=584 $66ee=(11111, 25600)  PH=5
k= 3 ctl X=11045 Y=25600 H=768 $6290=23 $eb8c=2178 odo=6099/107 $764c=3326 $66e2=583 $66e4=2743 $6888=584 $66ee=(11100, 25600)
     pat X=11045 Y=25600 H=768 $6290=23 $eb8c=2178 odo=6099/107 $764c=3326 $66e2=583 $66e4=2743 $6888=583 $66ee=(11056, 25600)  PH=5
k= 4 ctl X=10990 Y=25600 H=768 $6290=22 $eb8c=2178 odo=6156/108 $764c=3331 $66e2=582 $66e4=2749 $6888=583 $66ee=(11045, 25600)
     pat X=10990 Y=25600 H=768 $6290=22 $eb8c=2178 odo=6156/108 $764c=3331 $66e2=582 $66e4=2749 $6888=582 $66ee=(11001, 25600)  PH=5
k= 5 ctl X=10935 Y=25600 H=768 $6290=21 $eb8c=2178 odo=6213/109 $764c=3336 $66e2=581 $66e4=2755 $6888=582 $66ee=(10990, 25600)
     pat X=10935 Y=25600 H=768 $6290=21 $eb8c=2178 odo=6213/109 $764c=3336 $66e2=581 $66e4=2755 $6888=581 $66ee=(10946, 25600)  PH=5
k= 6 ctl X=10880 Y=25600 H=768 $6290=20 $eb8c=2178 odo=6270/110 $764c=3341 $66e2=579 $66e4=2762 $6888=581 $66ee=(10935, 25600)
     pat X=10880 Y=25600 H=768 $6290=20 $eb8c=2178 odo=6270/110 $764c=3341 $66e2=579 $66e4=2762 $6888=580 $66ee=(10891, 25600)  PH=5
k= 7 ctl X=10825 Y=25600 H=768 $6290=19 $eb8c=2178 odo=6327/111 $764c=3346 $66e2=578 $66e4=2768 $6888=579 $66ee=(10880, 25600)
     pat X=10825 Y=25600 H=768 $6290=19 $eb8c=2178 odo=6327/111 $764c=3346 $66e2=578 $66e4=2768 $6888=579 $66ee=(10836, 25600)  PH=5
k= 8 ctl X=10770 Y=25600 H=768 $6290=18 $eb8c=2178 odo=6384/112 $764c=3351 $66e2=577 $66e4=2774 $6888=578 $66ee=(10825, 25600)
     pat X=10770 Y=25600 H=768 $6290=18 $eb8c=2178 odo=6384/112 $764c=3351 $66e2=577 $66e4=2774 $6888=578 $66ee=(10781, 25600)  PH=5
```
and turnA with `gate + render + pos_end + hdg_end + alt` (k = 1..10, lean, `f984`, bank, throttle, speed also equal):
```
k= 1 ctl X=11344 Y=25564 H=780 $6290=22 $eb8c=2180 odo=513/9 $764c=3661 $66e2=945 $66e4=2716
     pat X=11344 Y=25564 H=780 $6290=22 $eb8c=2180 odo=513/9 $764c=3661 $66e2=945 $66e4=2716  PH=5
k= 5 ctl X=11128 Y=25532 H=724 $6290=18 $eb8c=2180 odo=741/13 $764c=3681 $66e2=945 $66e4=2736
     pat X=11128 Y=25532 H=724 $6290=18 $eb8c=2180 odo=741/13 $764c=3681 $66e2=945 $66e4=2736  PH=5
k=10 ctl X=10893 Y=25394 H=654 $6290=13 $eb8c=2180 odo=1026/18 $764c=3706 $66e2=939 $66e4=2767
     pat X=10893 Y=25394 H=654 $6290=13 $eb8c=2180 odo=1026/18 $764c=3706 $66e2=939 $66e4=2767  PH=5
```
So with the world block gated to PH 5 and `alt` added, **X, Y, H, lean, the game-minute countdown `$6290`, the clock `$eb8c`, the odometer `$f968/$f96c`, route `$764c`, `$66e2` and range `$66e4` are exactly the 5 Hz game's, for straight walking and for a −14/tick turn**. Without `alt` (first run, `gate`, sampled at `$3450c`) `$764c` ran 3336 / 3361 / 3386 / 3411 / 3436 against the control's 3316 / 3321 / 3326 / 3331 / 3336, and `$66e2/$6888` drifted 601 / 620 / 639 / 658 / 677 instead of 586 / 585 / 584 / 583 / 582: that is the 5× error the `alt` patch removes.

### 5.7 Residual differences, all explained

1. `$66ee/$66f2/$66fe` (pre-move copies, field `svalt` = `$66fe`) differ (e.g. k = 1: control `(11210,25600)`, patched `(11166,25600)`). The patched run saves at the start of pass 5, the control at the start of the tick. This is the collision/arrival revert baseline. Hence patch 7 (save only at PH = 1) is required. In the test it does not change the trajectory because nothing collided.
2. `$6888` (HUD copy of `$66e2`) is 1 lower in the patched run (586 vs 585 at k = 1, …). `$335ce → $336ea` writes it before the player sim in the loop, so it carries the end-of-previous-pass value: pass 4 (0.8 tick newer) instead of the previous tick. This is the order skew of §3, risk 2. At k = 7 and 8 it vanishes because the value is the same.

### 5.8 Limits of this validation

* Only type 13 (foot), bank 32, no fatigue drift, no collision, speed 217, throttle 222, on a 1 MB STE at 8 MHz. Types `$f/$10/$11/$14`, vehicle speeds, flying, `$efb4 > 1000` drift (the RNG consumption is gated to the world pass but not exercised), bank changes during a group, and clamp boundaries of `$764c` are untested.
* The scratch passes are deterministic (PH, no VBL); a real scheduler adds the clock and catch-up logic of `tick_head` with TICK = 2.
* `pos`'s range check uses an offset of 320 for `floor(S/65536)`, so it is exact only up to speed ≈ 1260 (`|v| ≤ 5 + speed/4`). The highest observed speed is 944 (`controls_joystick_check.md`).
* `$f984` (drift) enters `x` unchanged each pass, so a drift change at the world pass shows up in the next group's heading steps. In A it would have shown up in the same tick. At most a 1-tick (200 ms) lag of a ≤ 32/1024-turn drift. **[INFERENCE]** not exercised.

## 6. Scratch files and reproduction

Files touched (all `default: no`):
* existing: `patches/scratch_tick_{head,render,pos,hdg}.s`, unchanged;
* new: `scratch_tick_pos_end.s`, `scratch_tick_hdg_end.s` (exact variant, blobs at `$B4080` / `$B4110`, data `$B41C4`, `$B41CC`, `$B41D0`), `scratch_tick_gate.s` (fast-path head, `$B4000`), `scratch_tick_alt.s` (`$764c`, blob `$B4230`, data `$B41D4`). All of them sit in `$B4000-$B42FF`.

Live patch sets:
```
python3 tools/mw2patch.py live --only scratch_tick_head scratch_tick_render scratch_tick_pos scratch_tick_hdg --out /tmp/ti2/live/all
python3 tools/mw2patch.py live --only scratch_tick_head scratch_tick_render scratch_tick_pos_end scratch_tick_hdg_end --out /tmp/ti2/live/end
python3 tools/mw2patch.py live --only scratch_tick_gate scratch_tick_render scratch_tick_pos scratch_tick_hdg scratch_tick_alt --out /tmp/ti2/live/gatealt
python3 tools/mw2patch.py live --only scratch_tick_gate scratch_tick_render scratch_tick_pos_end scratch_tick_hdg_end scratch_tick_alt --out /tmp/ti2/live/gatealt_end
```
(`verify` passes for all of them; patch sets must not mix the plain and `_end` variants: they share sites.)

Harness core (the same in every run; `COND` = `pc = $3450c` or `pc = $31590`):
```python
h = Hatari(snapshot=SNAP)
apply = [f"loadbin {live}.img $b3000"] + [f"w ${a:x} " + " ".join(f"${b:02x}" for b in new) for a, new in sites] \
        + DUMPS + [f"b {COND} :trace :file {hit_file}"]          # hit_file = DUMPS
v = h.vbl(); h.cmd(f"hatari-debug b VBL > {v+3} && pc = $26e98 :trace :once :file {apply_file}")
# wait for N+1 occurrences of '^000066E6:' in the Hatari log, then 'b all'; h.close()
```
Hatari requires the debugger breakpoint flag `:trace`; `:once` removes the start breakpoint after it fires; all breakpoints are cleared with `b all`.
