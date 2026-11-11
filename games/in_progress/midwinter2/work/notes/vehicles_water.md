# Water vehicles: can the p3b 5-sub-step player step be applied?

Author: MW2VehWater (analyst; no patch under `patches/` was touched). Types: Speedboat 6, Crawler 7, Minisub 8, Submarine 9, Ship 10, Frogman 11, Hovercraft 19, Swimming 21. All numbers below were observed in Hatari runs of the unpatched game vs a scratch-patched game (scripts and raw logs in `work/vehicles_water/`), or read from disassembly of `work/dumps/ram_ingame_lobos.bin` (`tools/m68dis.py`). Anything else is marked **[INFERENCE]**.

## 0. Verdicts

| type | verdict | extra hooks beyond the shipped `p3b_*` (§3) | evidence (group ends, full RAM compare, §2) |
|---|---|---|---|
| 6 Speedboat | **exact** | order-exact split, tail probe, wave gate | `fin_speedboat` 29 groups EQ; `rec2` (window re-centre inside the run) 12 EQ; `shore1` (boat hits the shore, ejected to type 21 at group 11) 16 EQ |
| 10 Ship | **exact** | same | `fin_ship` 28 groups EQ |
| 19 Hovercraft | **exact** | same | `fin_hover` 28 groups EQ |
| 7 Crawler | **exact** | same | `crw2` 24 groups EQ, turning 34/tick |
| 21 Swimming | **exact with variant** | same + the bank `$3461a` clamp is already in `p3b_bank`; **types 21 and 11 must both be 5-sub-step types** (Swimming<->Frogman dive switch happens inside a group) | `swim3` 32 groups EQ (bank runs into the +-192 clamp at group 24); `swim4` 16 EQ across the 21->11->21 switch; `swim2` (11 not masked) breaks at group 9 |
| 9 Submarine | **exact with variant** | + `$34586` depth integrator (Bresenham) + bit6 tail skip | `sub1` 24 groups EQ (no depth input), `sub3` 16 EQ (depth button, `$764c` -16/tick); `sub2` (no depth hook) wrong x5 from group 1 |
| 8 Minisub | **exact with variant** (type is never an island start: tested by poking `$6220 = 8` into the Submarine snapshot) | + `p3b_alt` **group-start freeze** (`sw_alt`) | `mini3` 17 groups EQ, bank -24/tick; `mini1` (shipped `p3b_alt`) off by 1-2 units per group from group 1 |
| 11 Frogman | **exact with variant** (poked `$6220 = 11` into the Submarine snapshot) | same as Minisub | `frog2` 16 groups EQ, turning 64/tick, bank -24/tick |

"EQ" = about 960-980 bytes per group end identical between control and patched: player state (`$66e0-$66ff`, `$6740-$677f`, `$7640-$767f`), HUD/objective words (`$6880-$689f`), clock/fatigue (`$eb8c`, `$efb0-$efbf`, `$f984`), RNG `$6904/$6906`, wave phase `$1877c`, collision/page-window state (`$6280-$629f`, `$66b8-$66c7`), 9 NPC records (`$3532-$378b`), input accumulators, `$34936-$3493f` (terrain/sea probes) and the p3b data block. Differences are listed per run in `logs/<tag>.txt` (one line per group).

**The one thing every water type needs and the shipped p3b does not do: the wave phase `$1877c/$1dfba` must advance exactly +8 per 5 Hz tick** (§5). With one render per group the result above is byte-exact; with five renders per group and the unmodified `$1dcae` it is wrong in every group (`ren6`).

**The shipped `p3b_alt` is wrong whenever the bank/pitch changes inside a group** (helicopter too: same code, bit0). Offline model: unfrozen `$7652` = 8 of 16 ticks equal, frozen = 16/16 (§4, `logs/model_out.txt`).

## 1. What moves the player (disassembly)

`$31570 jsr $33bca` -> `$33bde` (one 5 Hz tick; call list `$33c1e-$33c4a`). Per tick, in this order, for every type (`$54dc0 + type*$3e`, a0):

1. `$34142` X input: clamp/deadzone/`$6fb6` write-back (`$347f2`), selector `$34(a0)` into `$3494a` (**all 22 types: 2 = direct**), `$6752`.
2. `$341cc` Y (throttle lever) the same way, `$6756`; `$34256` button axis `$6fbe`, `$675a`.
3. `$34106`: `$6740 = $6752>>4`; `$343ee` heading apply `$33(a0)` (**all types 4 = `$345c4`**): `$6742 = $6294 = $764a = ($6742 + $f984 + $6740) & $3fe`; lean `$674e = sext10(.. + same x)`.
4. `$34112`: `$6740 = $6756>>4`; `$34414` throttle apply `$30(a0)` (**all 1 = `$344ac`**): `$6750 += $6740`, then `$33f40` (speed), then position.
5. `$3411e`: `$6740 = $675a>>4`; `$3443a` button apply `$36(a0)`.
6. `$3467c`/`$346a2` view (levels), `$33e46` speed ramp, `$348ec` (terrain/sea probes `$34936/$34938/$3493a` at the NEW position), then the type tail (`$33d4c`...), probe `$34006`, window `$31dee`, `$37a62`, `$37afa`.

Per type (generated from the dump; thr = Y, turn = X, rates are `$6756/$6752` clamp in 1/16 units, so the largest speed is the rate max):

| type | flags | Y dz / clamp / rate | X dz / clamp / rate | button apply (`$36`) | view sel `$3c` / `$3d` |
|---|---|---|---|---|---|
| 6 Speedboat | $18 | 100 / -490..700 / -180..557 | 100 / +-300 / +-60 | none | `$346c8` terrain-slope / `$347be` lean |
| 7 Crawler | $04 | 100 / -400..600 / -250..466 | 200 / +-300 / +-60 | none | `$346c8` / `$34708` |
| 8 Minisub | $48 | 50 / -400..500 / -150..437 | 100 / +-300 / +-200 | `$3461a` bank (x24) | `$34762` sin/cos(bank) / `$347be` |
| 9 Submarine | $48 | 100 / -400..500 / -300..396 | 100 / +-250 / +-100 | `$34586` depth `$764c += $6740` (x16) | `$34762` / `$34748` const |
| 10 Ship | $18 | 100 / -400..500 / -240..332 | 100 / +-200 / +-40 | none | `$346c8` / `$34708` |
| 11 Frogman | $40 | 140 / -250..500 / -120..351 | 150 / +-300 / +-120 | `$3461a` bank (x24) | `$34762` / `$347be` |
| 19 Hovercraft | $14 | 100 / -300..700 / -200..557 | 100 / +-500 / +-100 | none | `$346c8` / `$34708` |
| 21 Swimming | $10 | 100 / 0..400 / 0..287 | 100 / +-200 / +-80 | `$3461a` bank (x8), clamp `$7250` = +-192 | `$346c8` / `$34708` |

Flags decide the code path (`$33f40`, `$33d4c`, `$34630`): bit0 or bit6 -> `$33f50` branch (speed = `thr*$7654*4>>16`, vertical `$764c += floor(thr*$7652/131072)`, `$7652/$7654` = sin/cos of the bank/pitch `$6746`, **written by `$3467c` at the end of the previous pass**); otherwise `$33f86` (**speed = `$6750`**, plain level). Position `$344f8-$34508`: `X += floor(sin(H)*v/65536)`, `Y += floor(cos(H)*v/65536)` with `H = $6294`, `v = $6772`.

Tail `$33d4c` by flags: bit4 (Speedboat, Ship, Hovercraft, Swimming) -> `$33e06`: `$66e2 = $750c[type]`, **`$764c = $3493a + $66e2`** (`$3493a = $5062 = max(terrain, wave-aware sea height)` at the current position, written by `$348ec`); bit2 (Crawler) -> `$33e1a`: `$66e4 = $34936`, `$764c = $34936 + $66e2` (sea-floor following); bit6-only (Minisub, Submarine, Frogman) -> `$33d70`: `$66e2 = $764c - $66e4`; `< $32` -> `$33e1a` reset, else `$764c` clamped to `[$34936, $34938+$1e]`. All end at `$33e30`: probe `$34006` (`$1ba24` player-vs-NPC/marker test + `$34034/$340a8` terrain/shore test; both revert X,Y,`$764c` to `$66ee/$66f2/$66fe`, or set `$676e` = 2/3 which makes `$32db6 -> $32e2c` eject the player: type 11, or 5 / 17 ..., with `addi.l #$100,$66e6`) and `$31dee` (window re-centre).

Water-specific state:
* **Sea height / wave:** `$764c` of Speedboat/Ship/Hovercraft/Swimming is a level of (position, wave phase). `$1877c` (+8 mod `$80`) and the pointer `$1dfba` are advanced at the end of the **renderer** (`$1dcae-$1dcca`), i.e. once per RENDER, and read by `$506e/$5062/$507a` from `$348ec`, `$3489a`, `$335ce -> $336ea`, `$20272` and the unit draw `$1c59a`.
* **Buoyancy / depth:** none beyond `$764c`: no separate buoyancy integrator exists. Submarine depth is the button integrator `$34586`; Minisub/Frogman depth is `thr*sin(bank)`.
* **Collision / arrival:** `$340a8` (flags bit3: Speedboat, Ship, Submarine, Minisub) compares terrain `$34936` with the wave-aware `$34938`: terrain below the surface = free; between -128 and +32 -> revert; above -> `$676e = 3` (eject). `$33e7a` arrival test only for flags bit0 (not these types). Frogman/Swimming/foot switches: `$335ce` pre-world (types 5/`$15`/`$b`: `$6888+$6884 >= $6886` -> foot; Swimming with `$6746 <= -64` -> Frogman).

## 2. Method (reproduce)

* `work/vehicles_water/vw.py` (Hatari helpers), `cmp.py` (control vs patched, group-end comparison), `report.py`, `model.py`, `tr.py` + `cover2.py` (render-read tracing), `patches/sw_*.s` (scratch patch set, built with `mw2patch.py`'s `cmd_live` against a private `PATCHDIR`; `p3b_pos/hdg/bank/save/probe` copied unchanged).
* A run restores `raid_<vehicle>.sav` (2 MB STE), applies the live patch image and the input pokes at the first flip (`pc = $26e98`) after an **absolute** VBL (`> 154250`; a relative VBL start differs by 1-5 ticks between runs: the first version of this study was misaligned by one tick because of that), then logs 14 memory blocks at every `pc = $3158c` hit. The patched run is only sampled where `$b42e6` (PH) = 5 = the group end. Held input: `w $6fba <y>.l`, `w $6fb6 <x>.l` (mouse accumulators; clamp write-back keeps them), button `w $6fbe $00 $02` (`$34282`: 1 = +16, 2 = -16).
* `python3 cmp.py <tag> <snap> <groups> <y> <x> <typemask-hex> [patchlist] [pokes ';'-separated]` and `./run_type.sh` (same). Example: `./run_type.sh fin_ship raid_ship_bourem.sav 28 150 -160 0x400`.
* Scratch head `sw_head.s` has no clock: PH 1..5 on masked types, a long at `$b4e00` selects the types (bit n = type n), `$b4e04 != 0` renders the sub-passes too.
* Snapshots: Speedboat `raid_speedboat_iquitos`, Ship `raid_ship_bourem`, Hovercraft `raid_hovercraft_thar`, Crawler `raid_crawler_panao`, Submarine `raid_submarine_jebba`, Swimming `raid_swimming_vitoria`. Minisub/Frogman (not on any island): poke `$6220` into the Submarine snapshot (`w $6220 $00 $08` / `$0b`). Inputs used: Y 150, X -160 (Crawler -290: its X deadzone is 200; Frogman 250/-250: Y deadzone 140).
* Raw: `logs/<tag>.txt` per group; `logs/model_out.txt`; `logs/cover_<type>.txt`.

## 3. The split, exactly (what has to run when)

Exactness needs the group to look like the unpatched tick, so the loop body is split at the player call: **PH 1 = pre-world block + sub-step 1 (through `$31570` as normal); PH 2-4 = `jsr $33bca` only; PH 5 = `jsr $33bca` + post-world `$31576...`.** (The shipped p3b runs the pre-world block at PH 5, after four sub-steps: `$6884/$6886/$6888`, `$688a` and every pre-world reader of the player position see a position 0.8 tick newer. Measured: `$6886`/`$6888` differ by 1-2 in 9 of 12 groups; harmless for water vehicles except the Swimming/Frogman `$335ce` switch.)

Hooks (scratch files in `work/vehicles_water/patches/`; `D = $b42e0` is the p3b data block: PH `D+6`, SUB `D+8`, HOLD `D+10`):

| hook | site (orig) | what it does | needed for |
|---|---|---|---|
| `sw_post` | `$31576` (`4eb9000359c2`) | on a masked PH 1-4 pass skip the post-world block (back to `$31486`) | order-exact |
| `p3b_save` | `$33be6` | pre-move position saved only at HOLD 0 | probe revert = the whole 5 Hz step |
| `p3b_hdg` | `$345e0` | heading Bresenham on `e = x & ~1`, HF = end heading | all |
| `p3b_pos` | `$344f8` | Q16 accumulators, `floor(ACC/(5*65536))`, all five sub-steps along HF | all |
| `p3b_bank` | `$3461e` | Bresenham `$6746 += $6740`; **clamp +-192 for non-bit0/6 (Swimming) is applied after each step: monotone, so equal to one clamp at the end** | 21, 8, 11 |
| `sw_alt` | `$33f50` | `p3b_alt` with **P0 = thr*$7652 and the speed `$6772` computed at HOLD 0 and replayed** (see §4) | 8, 11 (bit6; also helicopter/air, bit0) |
| `sw_depth` | `$345aa` (`3038764cd0786740`) | `$764c += q`, `q = floor((ACC+e)/5)`, ACC kept (own word), then the original clamp | 9 |
| `sw_tail` | `$33d4c` (`3028000208000000`) | bit6-only types: on PH 1-4 skip to `$33e30` (the sea-floor clamp/reset `$33d70-$33d9c` runs once, on PH 5, with the group's `$34936` bounds) | 8, 9, 11 |
| `sw_probe2` | `$33e30` (`610001d46100dfb8`) | on PH 1-4: `clr.w $676e`, skip `$34006` + `$31dee` (re-centre and probes act on the group-end position) | all non-bit0 |
| `p3b_probe` | `$33dc6` | same for the bit0 (air) path | air only |
| `sw_range` | `$33bf8` (`4eb90003489a`) | `$3489a` (`$66e4`, `$6774`) only at HOLD 0 | in principle all; **not observable** in the Speedboat runs (ablation `ablr` 16 EQ), needed for bit6 types because `$66e2 = $764c - $66e4` feeds their clamp **[INFERENCE for the bit6 case, not ablated]** |
| `sw_ramp` | `$33e46` (`303876466a02`) | speed ramp `$688e/$6892` (+-1 per call) only on PH 5 | only types 1-3 consume `$688e`; state equality only |
| `sw_wave` | `$1dcae` (`50790001877c`) | wave phase advance only on the PH 5 render (or unmasked type) | §5, all water types |

Ablation notes: dropping `sw_probe2` (`ablp`) or `sw_range` (`ablr`) from the Speedboat run still gives 16 EQ groups: the shore hit in that run is an eject (`$676e = 3`), re-evaluated at the final sub-pass. A shallow revert case (terrain between -128 and +32) was not found/tested: the claim that the probe must run on PH 5 only is derived from the revert semantics (`$340d4` restores `$66ee`; a mid-group revert would be followed by two more sub-steps) **[INFERENCE]**.

## 4. Per type

State legend: **LEVEL** recomputed from other state every pass (nothing to scale), **ACC** needs a remainder accumulator, **WORLD** once per group (PH 1 pre-world or PH 5), **GATE** input to a clamp/probe.

### 4.1 Common to 6, 7, 10, 19, 21 (generic `$33f86` path)

Motion = `$345c4` heading + `$344ac` position. Offline check on 24-31 logged ticks per type (`model.py`, integer-exact copies of `bres`/`fdiv5`/Q16): the game's own formulas reproduce every tick (`ORIG-formula==game` 28/28 Speedboat, 28/28 Ship, 28/28 Hovercraft, 25/25 Crawler, 31/31 Swimming) and the five-sub-step arithmetic lands on the same X, Y, H every time (`SPLIT==game` the same counts).

| variable | per-pass update | 1/5 exact? | method |
|---|---|---|---|
| X, Y `$66e6/$66ea` | `+= floor(sin/cos(H)*v/65536)` | yes while `|v| <= ~1260` (largest water speed 557) | Q16 ACC per axis, all five sub-steps along HF = the heading the tick ends on (`p3b_pos`) |
| H `$6742/$6294/$764a` | `+= x & ~1`, `x = $f984 + $6752>>4` | yes | Bresenham on e/2 (`p3b_hdg`) |
| lean `$674e` | cleared each pass, `= sext10(x)` | LEVEL | - |
| `$6752/$6756/$675a`, `$6740`, `$6750`, `$6772` | direct selectors: clamp of the (held) input | LEVEL | - |
| `$f984` fatigue (RNG) | pre-world `$2f726` | not splittable | WORLD (PH 1 only by construction) |
| `$764c` (6, 10, 19, 21) | `= $3493a + $750c[t]`: wave + terrain at the new position | LEVEL, **but depends on the wave phase** | §5 |
| `$764c` (7) | `= $34936 + $750c[7]`: terrain | LEVEL | - |
| `$66e2` | `= $750c[t]` | LEVEL | - |
| `$66e4/$6774` | `$3489a` from the pass-start position | HOLD (computed on the group-start position) | `sw_range` |
| `$66ee/$66f2/$66fe` | pre-move copies | save at HOLD 0 | `p3b_save` |
| `$34936/$34938/$3493a`, `$7646-$7648`, `$7652/$7654`, `$7662-$767d`, `$670a-$6711`, `$53ac/ae` | levels of the final position/heading | LEVEL | - |
| `$688e/$6892` | +-1 | WORLD | `sw_ramp` (no consumer in these types) |
| `$6290`, `$eb8c`, odometer, HUD `$6884-$688a` | clock / world | WORLD | by construction |
| `$676e`, `$6282`, `$6288` (+ `$31dee`) | probe / window | event at the group end | `sw_probe2` |

* **Speedboat 6** (flags $18, bit3/bit4): as above; `$764c` bobs 20-25 units per tick (`alt` -71..+44, max 25 per tick, in `fin_speedboat`). Step function: `H1 = (H + (x&~1)) & $3fe` (Bresenham), `X += floor(sin(H1)*v/65536)` (Q16/5), `Y` likewise, `$764c = $3493a + $750c[6]` (level). Evidence: `logs/fin_speedboat.txt`, `shore1.txt`, `rec2.txt`:
```
fin_speedboat:  1 T=6 X=25592 Y=25845 H=610 ... SUB=1 EQ   (29 groups, all EQ; X 25592..25709, H 610..944..794)
shore1:        10 T=6 X=25600 Y=25726 H=512 ... EQ ; 11 T=21 X=25856 Y=25726 H=0 SUB=0 EQ   (eject at the shore, +$100 in X, type 21)
rec2:           2 X=46194 ... EQ ; 3 X=25726 Y=25856 ... EQ        (re-centre jump -20468 = 40*512, 12 groups all EQ)
```
* **Ship 10** (flags $18) and **Hovercraft 19** (flags $14): identical code path (Ship/Hovercraft view `$346c8`/`$34708`; the terrain-slope helper `$5116/$5110` is the renderer's `$1c6fe/$1c718`: it writes the scratch `$5392-$53a7/$691c-$694d`, always before reading in the same call). `fin_ship` 28, `fin_hover` 28 groups EQ.
* **Crawler 7** (flags $04): `$764c = $34936 + $750c[7]`, the sea-floor height; no wave. `crw2` 24 groups EQ, heading -34/tick (H 606 -> 848 over 24 groups, `alt` -1282..-1273).
* **Swimming 21** (flags $10): adds the button bank `$6746` (`$3461a`, not bit0/6, so clamped by `$7250[21*4]` = +-192: `swim3` runs 9 groups ON the clamp, 32 groups EQ). Bank per tick `$6740 = $675a>>4`: Bresenham; model: `bank ORIG 31/31 SPLIT 31/31`. **Type switch inside the group:** `$335ce` (pre-world) turns Swimming into Frogman when `$6746 <= -64` (`swim2`: control tick 9 = type 11, tick 10 = back to 21). With only type 21 in the mask the head ran the rest of that group as an unmasked full pass (a second tick): groups 9-16 shifted by one tick (`swim2.txt`). With 21 **and** 11 masked `swim4` is EQ in all 16 groups including both switches. Under p3c (tick executed once, interpolation display only) none of this applies, but PH 2-4 interpolation must be off when `$6220` changed during the group (type flip-flops on consecutive ticks).

### 4.2 Submarine 9 (flags $48: bit6)

Horizontal: generic. Speed = `$6772` from `$33f50` branch with `$7654 = cos(0)` (the Submarine has no pitch control: `$36 = 3`), vertical part `thr*$7652 = 0`. Depth: `$34586` button integrator `$764c = clamp($764c + $6740, $e0c0, $2ee0)`, `$6740 = $675a>>4` = +-16 for the button. Then the bit6 tail: `$66e2 = $764c - $66e4`; `< $32` -> reset to `$34936 + $750c[9]`; else clamp to `[$34936, $34938 + $1e]`.

| variable | per pass | exact? | method |
|---|---|---|---|
| X, Y, H | as 4.1 | yes | as 4.1 |
| `$764c` | `+= $6740` (clamp) | **yes, exact with a remainder accumulator**: `q = floor((ACC + e)/5)`, five steps add exactly e; clamp constants -> clamp each step == clamp once | `sw_depth` |
| `$764c` tail clamp/reset `$33d70-$33d9c` | non-idempotent, bounds from the new position | only once per group, on the group sum | `sw_tail` (GATE) |
| `$66e2`, `$66e4`, `$6774` | from `$764c` and the pass-start terrain | HOLD / PH 5 | `sw_range` / by the tail |
| `$7652/$7654/$763e-$7648` | views of `$6746`(= 0) | LEVEL | - |

Evidence: `sub1` (24 groups, no depth input) EQ; `sub3` (button -16 per tick, `alt` -216 .. -456) 16 groups EQ; `sub2` (`$764c` hook absent) shows `alt` 65320/65256 after group 1 (the original moves 16, the sub-steps 80), `$66e2` 548/484 and growing. Model: `depth ORIG 16/16 SPLIT 16/16`.

### 4.3 Minisub 8 and Frogman 11 (flags $48 / $40: bit6, with a button-controlled bank = pitch)

Same as helicopter in structure: Y rate -> thr, button -> `$3461a` bank (not clamped for bit6), `$7652/$7654 = sin/cos(bank)` by `$34762`, `$764c += floor(thr*$7652/131072)`, `v = thr*$7654*4>>16`; plus the bit6 tail of 4.2.

* **The `$7652/$7654` seen by `$33f50` are the previous pass's** (`$3467c` runs at the END of the pass, `$33c42`). Original tick k uses `$7652(end of k-1)`. The shipped `p3b_alt` re-reads them in every sub-pass, after `$3467c` has moved them with the bank, so the five P0 terms drift: model says 8 of 16 ticks equal (bank -24/tick), live `mini1`: `spd` 100/99, `$764c` 65336/65335 after group 1, `$66e2` 564/563, growing to 17 units. Fix `sw_alt`: compute P0 and `$6772` on HOLD 0, store (long + word at `$b4e18`), replay on HOLD 1; the group sum is then exactly `floor(P0/131072)` and the speed is the original's.
* Bank `$6746`: Bresenham (`p3b_bank`), unclamped (flags bit6).
* Frogman events (`$335ce`: `$6884 <= $ffc0 ...` -> `$15`/`$b`) are pre-world, see 4.1 on type switches.

Evidence (`logs/mini3.txt`, `frog2.txt`; type forced by poke): Minisub 17 groups EQ with bank -24 -> -408, `$764c` -200 -> -357, H 346 -> 762; Frogman 16 groups EQ, heading step 64/tick (H 320 -> 384 after full turns), bank -24/tick, `$764c` -200 -> -361. Model: `bank ORIG 16/16 SPLIT 16/16`, `alt/speed ORIG 16/16 SPLIT 16/16`, `shipped-p3b_alt 8/16`.

## 5. The wave phase and the other render -> logic channels

* `$1877c/$1dfba` advance by one step **per render** (`$1dcae`); the logic reads it (list in §1). One render per 5 Hz tick gives the unpatched value. With every sub-pass rendering and `$1dcae` untouched, **all 12 groups differ** (`ren6`: `$764c`, view words, `$6886/$688a`, and NPC-table words `$3642-$37xx` - the units' wave-aware height `$1c59a -> $506e` is stored into the record, and the render writes `+$36` of visible NPCs at `$1ce38`, read back at `$33a08`). With the advance executed only on the render of PH 5 (`sw_wave`), **10 of 12 groups are byte-identical** and the other two differ only in `$7682` (`ren7`; `$7682` is render-prep scratch: set `$2009c`, written `$20254`, read `$20118/$20194/$20208` inside the same `$20088` call, no logic reader). So A (1 render/tick) and B (5 renders/tick) are bit-equal for water vehicles if and only if the phase moves 8 per tick. `p7_ck_exit` already patches `$1dcae` and `p7_skip_render` replays the block: the gate has to live in that chain. A smoother alternative (Bresenham 8/5 per sub-render, group sum 8) is possible in principle but would make the sea height of PH 1-4 differ from the unpatched game at no benefit **[INFERENCE, not tested]**.
* Render-read words that the logic writes (traces of one full loop iteration of an unpatched, moving Speedboat/Ship/Hovercraft/Crawler/Submarine/Swimming; `cover2.py`, raw `logs/cover_*.txt`): `$66e6-ed`, `$670a-d`, `$763e-45`, `$764a-d` (Crawler/Swimming: only `$764c`), `$7652-55` (not Crawler/Swimming), `$53ac-af` (not Crawler/Swimming), `$17fc4`/`$181fa` (constants from `$67ba<<$67be`), `$67a6` (draw buffer), `$20272` outputs `$18768`, `$18772-79`, `$18784-89`, `$18796-97`, plus NPC/effect/marker records. **Nothing else, for all six types**; no periscope/propeller/depth cue is a separate word.
* Render-written words that the logic reads: `$1dfba` (above), NPC `+$36/$38/$3a` (above), `$6fc8` (`$1c312` -> `$38036`, height smoothing), and the scratch ranges `$5392-$53a7`, `$691c-$694d`, `$6776` that `$346c8` (called by the sim) shares with the renderer (always written before read inside the sim call: harmless).

## 6. Jumps inside a tick (for any interpolating display, p3c)

1. Collision reverts `$1ba60/$1bc50/$1bc9c/$34056/$340d4`: X, Y, `$764c` back to `$66ee/$66f2/$66fe` (<= one step; start == end of the tick, so interpolation start -> end is correct).
2. Window re-centre `$31dee` (`$3451a` clears `$6288` when X or Y leaves `[$1388,$b478]`): X/Y shift by whole 512-cell multiples (observed -20468 = 40 cells in `rec2`), also `$31e52` revert to `$66f6/$66fa`. |dX| is far above `$1000`: no interpolation.
3. Type changes: `$32e2c` eject (type 11 or 5/17, X += `$100`, `$6742/$6746/$674a/$6294` cleared; seen in `shore1`: Speedboat -> 21), `$335ce` Swimming <-> Frogman <-> foot, `$33cd8` type `$11` fall -> `$15`. The Swimming/Frogman pair flip-flops on consecutive ticks while the bank button is held.
4. bit6 types at the sea floor: `$33e1a` resets `$764c` to `$34936 + $750c[t]` (bounded by the clamp overshoot).

## 7. Open points

* A shallow-shore revert (terrain between -128 and +32, `$340d4`) and a `$1ba24` NPC-contact revert were not reproduced; `sw_probe2`/`p3b_probe` rely on the revert semantics (§3 [INFERENCE]).
* Input that changes inside a group (mouse/joystick): the hooks reread the input in every sub-pass; `p5_ctl_x`'s HOLD mechanism is the existing answer; not exercised here (inputs were held).
* Fatigue drift `$f984` with `$efb4 > 1000` (RNG per pass) was not active in these runs; by construction it is a PH 1 pre-world call (`$2f726`), so the group's x is constant. **[INFERENCE]**
* Speeds above 1260 would break `p3b_pos`'s `floor(S/65536)` domain; the largest water speed is 557.
