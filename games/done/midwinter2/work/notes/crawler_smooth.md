# Crawler smoothing (bug B1): what the 25 Hz player smoothing covers, why the Crawler looks different, and a general fix

Author: CrawlerSmooth, 2026-11-15. Investigation only: nothing under `patches/` or `tools/` was changed, nothing committed.
Scratch: `work/crawler_smooth/` (scripts `cs.py pf.py gate.py gates.sh hgt.py cold_tt.py tt_enter.py`, per-flip tables `runs/*.txt`, gate output `logs/gate*.txt`,
experimental patch `patches/p3cp_head.s` = the shipped file + `p3cp_head_level.diff`, snapshots `snap/`).
Tags: **[obs]** measured in Hatari here, **[disasm]** read from `work/dumps/ram_ingame_lobos.bin` / the patch sources, **[model]** offline integer copy of game code checked against [obs], **[INFERENCE]** not run.

## 0. Result

1. **The Crawler is not excluded from the smoothing.** The shipped mechanism (`p3cp_head` + `p3c_sim` + `p3c_render` + `p3cp_keys`) has no per-vehicle code: it hooks the frame loop around the ONE call that moves the player for every vehicle (`$31570 jsr $33bca`), and its type table `TAB[$6220]` is 1 for all 22 types [disasm]. Measured, the Crawler gets a new position, heading and picture on every presented frame at 25 Hz, on the sea floor and on land, on an STE at 32 MHz and on a TT (Hatari 2.6.1 and the patched 2.6.1-devel of `dist/hatari.local`) [obs, section 2].
2. **The user's hypothesis is right about the game and is already how the smoothing works.** All 22 vehicle types go through one routine, `sub_033bde`, driven by a per-type parameter block and small jump tables (section 3). The per-vehicle notes (`vehicles_air.md`, `vehicles_water.md`) are analyses for the retired p3b design (exact sub-stepping, hooks inside the integrators); p3cp replaced it on 2026-11-11 with the common-call design.
3. **What IS different for the Crawler, measured: its height.** The extra frames (4 of 5) show a pose extrapolated linearly from the last tick, and "altitude is never extrapolated downwards". For a vehicle whose altitude is not an integrator but a *level* (`terrain(X,Y) + eye height`, recomputed every tick), this is wrong in two ways [obs, section 4]:
   - going **down** a slope the camera height stays frozen for the four extra frames while X/Y advance, then drops at the tick: a 5 Hz sawtooth. Crawler at full throttle downhill on Panao: the shown height is 5/11/16/22(/26) units too high in the extra frames 2/3/4/5, then 0 at the tick; maximum 29 units = **58 % of the Crawler's 50-unit eye height**;
   - going up, or over changing slopes, the linear guess is off by −9..+18 units.
   On the sea floor the depth is literally updated at 5 Hz when descending (`alt` per frame: −1294 ×5, −1297 ×5, −1298 ×5 ...), and the featureless seabed leaves the horizon/ground distance as the only motion cue. Every ground or surface follower has the defect (Jeep-type 44 %, on foot 44 % in the same run); the Crawler is the worst case: lowest eye height (50), highest ground speed on a slope (466; the Jeep/Truck/Bus lose half their speed on slopes through the gear word `$688e`), and it is the only one that also drives the steep shore and seabed.
4. **General fix, tested as a throwaway patch: take the level from the game's own function at the predicted position**, chosen by the same flags word the game's tail uses (`$33d4c`), not by vehicle: ground types `$764c = $5068(X,Y) + $66e2`, surface types `$764c = $5062(X,Y) + $66e2`, air and submarine types unchanged. The game's own auto-drive path does exactly this (`$37892-$378ae`) [disasm]. Result: shown height − (terrain at the shown position + eye) = **0 in 114 of 114 extra frames** (was up to +26), same frame count; **group-end state identical to option A in 18 of 18 gate runs** (Crawler sea/shore/land/standing, Jeep, Truck, Tank, on foot, Ship, Hovercraft, Swimming, Helicopter, Submarine; 16 and 32 MHz), negative control fails as it must (section 5).
5. Two more cases where a vehicle is not smoothed, for any type, by design of the shipped scheduler: **auto-drive** (`$40b6 <> 0`, the map's travel mode; the head keeps the plain 5 Hz pass) [disasm], and **8 MHz machines**, where an extra frame rarely fits before the next tick is due (Crawler at full throttle: 30 flips in 300 VBL at 8 MHz, 29 of them PH 1; 73 in 300 at 16 MHz; 95 in 200 at 32 MHz) [obs].
6. Not reproduced: a Crawler-only frame-rate or tick-rate loss on the TT. What the user saw on the TT is, by these measurements, the height sawtooth of item 3 **[INFERENCE: the report was not re-checked with the user; the level build should be shown to them]**.

## 1. How the shipped smoothing decides what it covers [disasm, `patches/p3cp_head.s`]

| Gate | Where | Effect |
|---|---|---|
| `TAB[$6220]` (22 bytes, all 1) and `$6220 <= 21` | head `$b8100`, `.nm` | 1 = 25 Hz passes (five 40 ms passes per 5 Hz tick). Every type is on. |
| `tst.w $40b6 / bne .wait` | head | auto-drive: plain 5 Hz pass for every type |
| `INT` (computed at PH 2 by `cap1`) | `subpass` | 0 = the four extra frames show the end-of-tick pose unchanged: type changed in the tick, `$676e <> 0` (collision revert/arrival), `$767e <> 0` (landing), a jump (`|dX|,|dY|,|dAlt| > $1000`, `|dHeading| > 256`, `|dBank|,|dPitch| > 128`), the first group after a jump, or nothing changed |
| deadline rule (`REST`, `SLACK`) | head `.cont` | an extra pass renders only if it should end before the next tick is due (+1 VBL); otherwise `SKIP` |
| altitude rule | `subpass` | `$764c` linear, and held at the end-of-tick value when the tick's delta is negative; lean `$674e` never predicted |

None of these looks at the vehicle type. For the Crawler none of the `INT = 0` conditions is a standing condition: `$767e` is only written for flags bit 0 types; `$676e` needs flags bit 3/bit 5 or `$66e2 < 0`, the Crawler has flags `$0004` and `$66e2 = $750c[7] = 50` [disasm `$34034`, `$340a8`]; in every run below `INT = 1`, `JP = 0`, `$676e = 0` in every flip [obs].

Pose words predicted in an extra frame: X `$66e6`, Y `$66ea` (long), heading `$6742/$6294/$764a`, bank `$6746`, pitch `$674a`, altitude `$764c`; then the game's own view set-up `$3467c $346a2 $37a62 $37afa` runs on that pose (so the terrain-slope tilt of the ground types IS recomputed from the terrain at the predicted position). Everything is put back from the shadow before the next tick (`fixup`), which is why group ends equal the unpatched tick.

## 2. Measurement: is the Crawler stepped at 25 Hz? [obs]

`pf.py`: one row per presented flip (`pc = $26e98`): VBL, scheduler phase `PH`, `INT`, `SKIP`, X, Y, heading, altitude, speed, terrain probe, view words, static-skip counters; `--frames` adds a hash of every 4th row of the 3D window (rows 58-198) of the buffer just drawn.

| Run (`runs/<name>.txt`) | Machine | Input | Flips / VBL | Flips with a new pose | New picture |
|---|---|---|---|---|---|
| `crawler32` | STE 2 MB, 32 MHz, default set live on `raid_crawler_panao.sav` | forward 150 (poke), sea floor | 95 / 200 (50 Hz) = 23.8 fps | 94 / 94 | - |
| `jeep32` | same, `raid_jeep_dhafra.sav` | forward | 79 / 200 | 78 / 78 | - |
| `ste_crawler_land` | STE 32 MHz, Crawler poked onto Panao's land (X 11008) | forward | 61 / 160 = 19 fps | 60 / 60 | 61 / 61 |
| `tt_crawler_fwd` | TT 4 MB TOS 3.06 `--mmu true`, Hatari 2.6.1, v1.4 code from a cold boot (`snap/tt_crawler.sav`, made from `fire_tt14fix_map.sav`) | forward 150 | 95 / 240 (60 Hz) = 23.8 fps | 94 / 94 | - |
| `tt_jeep_fwd` | same, `fire_tt14fix_jeep.sav` | forward | 76 / 240 | 75 / 75 | - |
| `tt_crawler_mouse` | same | real mouse (xdotool): throttle, then left/right sweeps | 124 / 300 = 24.8 fps | 123 / 123 | 124 / 124 |
| `tt_jeep_mouse` | same | same | 120 / 300 | 119 / 119 | 120 / 120 |
| `tt_crawler_full` | same | full throttle (speed 466) | 87 / 200 = 26 fps | 86 / 86 | - |
| `ttp_crawler_full` | TT, **patched Hatari 2.6.1-devel** (`dist/hatari.local`), own cold boot of `build/game` (= v1.4, md5 of `RUNME.TOS`/`HAGA` equal to `dist/_stage/MIDWINT2`) to Panao: `snap/ttp_crawler.sav` | full throttle, sea floor | 97 / 240 = 24.3 fps | 96 / 96 | 97 / 97 |
| `ttp_crawler_shore` | same, poked onto land, driving inland | full throttle | 191 / 540 = 21 fps | 190 / 190 | 170 / 191 (*) |
| `ste16_crawler` / `ste16_jeep` | STE 16 MHz | full throttle | 73 / 300, 60 / 300 | all | - |
| `ste8_crawler` / `ste8_jeep` | STE 8 MHz | full throttle | 30 / 300 (29 of them PH 1), 24 / 300 (all PH 1) | all | - |

(*) 21 flips in a row (0.7 s) with a new pose and a render (`nrend` +1 each) but the same sampled picture: the view was pitched up a steep climb and showed one colour. Not a skipped frame.

Within a group the Crawler's X/Y advance evenly (e.g. `crawler32`: X −4, −3, −3, −3, −3 per frame), the heading turns in every frame (`tt_crawler_mouse`: 648, 648, 650, 652, 654, 656 ...), the slope tilt words `$7642/$763e` change every frame. Only the altitude does not behave (section 4).

World rate: the tick is 5 Hz for every type (`vehicles_p3b.md` section 12). The unpatched Crawler standing on the sea floor at 8 MHz presents a frame every 8-9 VBL (5.6-6.3 fps; flips of the unpatched `raid_crawler_panao.sav` at VBL 153819, 827, 836, 844, 852; throwaway trace, output not kept), so there the 5 Hz lock makes the Crawler about 15 % slower than the original on a plain ST, while the Jeep (4.2 fps unpatched, `vehicles_p3b.md` section 1) and the heavy scenes get faster. This is a property of the fixed tick, not of the smoothing.

## 3. The common vehicle update: call tree and data layout [disasm]

```
frame loop $31486-$315de
  $31486  lea $770e,a6 / jsr $4f5a            <- p3cp_head (scheduler)
  ... pre-world calls ($50d4 Esc, fatigue, AI ...)
  $31570  jsr $33bca                           <- p3c_sim (records the pose before the tick, then tail-calls $33bca)
            $33bca: tst.w $40b6 ; beq -> bsr $33bde (manual) ; else jsr $37626 (auto-drive along a route)
  $31576  post-world calls, $31586 HUD numerics
  $3158c  jsr $50b0 (gauges) / tst $6298       <- p3c_render (render gate, SKIP)
  $315a4  jsr $5056 -> $1dbbe renderer, $315c6 flip
  $315d0  jsr $4f66 / jsr $50ce (keys, fire)   <- p3cp_keys (not in extra passes)

sub_033bde, one call per tick, ALL 22 types; a0 = $54dc0 + $6220*$3e (type block), flags = 2(a0) -> $6776
  $33be6  pre-move copies $66ee/$66f2/$66fe ; $33bf8 jsr $3489a (terrain under the start position -> $66e4, $6774)
  $33c1e  bsr $34142  X input: clamp/deadzone ($347f2; p5_ctl_x site $34152), rate selector $34(a0) via table $3494a -> $6752
  $33c22  bsr $341cc  Y input: $3481e, selector $31(a0) via $3495a -> $6756
  $33c26  bsr $34256  button axis: selector $37(a0) via $3496a -> $675a
  $33c2a  $6740 = $6752>>4 ; $33c2e bsr $343ee  apply selector $33(a0) via table $3499a   (every type: 4 = $345c4 heading)
  $33c32  $6740 = $6756>>4 ; $33c36 bsr $34414  apply selector $30(a0)                    (1 = $344ac throttle+move; 5 = bank; 3 = depth)
  $33c3a  $6740 = $675a>>4 ; $33c3e bsr $3443a  apply selector $36(a0)                    (5 = $3461a bank, 3 = $34586 depth, 0 = none)
  $33c42  bsr $3467c  view selector $3c(a0) via $349de: 0 = $346c8 terrain slope, 1 = $34762 sin/cos(bank), 2 = $34722
  $33c46  bsr $346a2  view selector $3d(a0) via $349ea: $34748 / $347be / $34708 / $34790
  $33c4a  bsr $33e46  gear $688e (+-1 per tick by slope; used by types 1-3 only, $33f86)
  $33c4e  jsr $348ec  probes at the NEW position: $34936 = $5068 terrain, $34938 = $506e wave, $3493a = $5062 max(terrain, sea)
  $33c54  tail, by type / flags:
            type $f Balloon, $11 Parachute, $10 Rocket Pack: own code $33c60-$33d48
            bit0 (air)                      -> $33da4: $66e4, $66e2 = $764c - level ; probe $34006 ; landing test $33e7a
            bit4 (surface)                  -> $33e06: $66e2 = $750c[type] ; $764c = $3493a + $66e2
            bit2, or neither bit2 nor bit6  -> $33e1a: $66e2 = $750c[type] ; $66e4 = $34936 ; $764c = $34936 + $66e2
            bit6 (submarine types)          -> $33d70: $66e2 = $764c - $66e4 ; < $32 -> $33e1a ; else clamp to [$34936, $34938 + $1e]
  $33e30  bsr $34006 (probe: $50c2 objects, $34034 shore for bit5, $340a8 for bit3 -> revert to $66ee.. or $676e = 2/3)
  $33e34  bsr $31dee (map window re-centre) ; $33e38 bsr $37a62 (view matrix) ; $33e3c bsr $37afa (position -> cell)

$344ac (throttle + move, all types): fatigue scalers $2f784/$2f7f0 ; $6750 += $6740 ; $33f40 speed
            bit0 or bit6: $6772 = $6750*$7654*4>>16 ; $764c += $6750*$7652>>17 (clamped)     <- altitude is an INTEGRATOR
            else ($33f86): $6772 = $6750 (types 1-3: * ($688e+8)/16)                         <- altitude is a LEVEL (tail)
          X += sin($6294)*$6772>>16 ; Y += cos($6294)*$6772>>16 ($344f8-$34508) ; bounds $3451a
$345c4 (heading, all types): $6742 = $6294 = $764a = ($6742 + $f984 + $6740) & $3fe ; lean $674e
```

Type block (`$54dc0 + type*$3e`): `+2` flags; `+4/+6/+8` Y deadzone/min/max; `+$a/+$c` Y rate clamp; `+$12/+$14/+$16` X deadzone/min/max; `+$18/+$1a` X rate clamp; `+$20..+$2e` button clamps; `+$30..+$3d` selector/scale bytes (Y apply, Y rate, Y scale, X apply, X rate, X scale, button apply, button rate, button scale, ..., view 1, view 2). Per-type words: eye height `$750c[type]`, `$7300`, `$753a`, bank clamp `$7250[type*4]`.

| type | flags | altitude source (tail) | view sel `$3c/$3d` | eye `$750c` | max speed word |
|---|---|---|---|---|---|
| 0 Tank, 1 Jeep, 2 Truck, 3 Bus, 4 Train | `$24` | ground level (`$33e1a`) | 0 / 2 terrain slope | 100, 70, 90, 80, 100 | 437, 727, 557, 567, 718 (1-3: x(gear+8)/16) |
| 5 on foot | `$04` | ground level | 0 / 0 | 50 | 341 |
| **7 Crawler** | **`$04`** | **ground level, also below sea level (no bit3/bit5: no shore test)** | 0 / 2 | **50** | **466, no gear** |
| 6 Speedboat, 10 Ship | `$18` | surface level `$5062` (`$33e06`) | 0 / 1, 0 / 2 | 50 | 557, 332 |
| 19 Hovercraft, 21 Swimming | `$14`, `$10` | surface level | 0 / 2 | 70, 50 | 557, 287 |
| 8 Minisub, 9 Submarine, 11 Frogman | `$48`, `$48`, `$40` | integrator + clamp (`$33d70`) | 1 / x | 50, 50, 70 | 437, 396, 351 |
| 12 Biplane, 13 Helicopter, 14 Zeppelin, 16 Rocket, 18 Flying Boat, 20 Flying Sub | bit0 | integrator | 1 / x | - | 987, 944, ... |
| 15 Balloon, 17 Parachute | `$01`, `$00` | own tails | 1 / x | - | - |

So the Crawler is not a special case in the sim: it is "on foot with a cockpit" (same flags `$04`), the plain ground-level tail, and because it has neither bit3 nor bit5 nothing stops it at the waterline. Land and sea floor are the same code path [disasm]; the terrain model below reproduces `$34936` in every tick of every run on both [model: `hgt.py`, 24/24 ... 45/45].

Auto-drive (`$37626`, `$40b6 <> 0`): the player is moved by the NPC route follower (`$36ff6`, record `$34f0`), heading from the direction vector, and the altitude by `a0 = $5068 or $5062 by flags ; jsr (a0) ; add.w $66e2,d5 ; move.w d5,$764c` (`$377f0-$378ae`), then the same `$348ec $34006 $31dee $37a62 $37afa`.

### What p3c / p3cp hook today (site, original bytes)

| Patch | Site | Original bytes | Role |
|---|---|---|---|
| `p3cp_head` (shipped) / `p3c_head` (interpolating alternative, off) | `$31486` | `4df8770e 4eb84f5a` | scheduler: PH 1 = the unmodified tick, PH 2-5 = predicted pose + view refresh + render |
| `p3c_sim` | `$31570` | `4eb900033bca` | the common player call: record the pose before the tick |
| `p3c_render` | `$3158c` | `4eb850b0 4a786298` | gauge draw once per presented frame, `SKIP` |
| `p3cp_keys` | `$315d0` | `4eb84f66 4eb850ce` | no key/fire consumers in extra passes |
| `tick_vbl` | `$262d0` | `52787020 5278770c` | 1/300 s clock |

No hook is inside a per-type handler. (The retired p3b set hooked `$344f8`, `$345e0`, `$3461e`, `$33f50`, `$33dc6`, `$33be6`: that is the per-vehicle look of the old notes.)

## 4. The defect: level altitudes are extrapolated as if they were integrators [obs + model]

`hgt.py` is an integer copy of `$5068` (`$1fcf4 -> $1fbec, $1fc24`: cell lookup in the 100 x 100 grid `$40040`, two triangles per cell) on a RAM dump of the Panao window (`snap/crawler_ram.bin`). Check: model == `$34936` at every PH 1 flip of every run (17/17, 18/18, 24/24, 19/19, 45/45, 34/34, 36/36).
Error = shown `$764c` − (model terrain at the shown X,Y + eye height), extra frames only:

| Run | Speed | Extra frames | min / max | mean abs | Note |
|---|---|---|---|---|---|
| `crawler32` (sea floor, gentle) | 150 | 76 | −1 / +2 | 0.4 | depth constant in each group, steps at the tick |
| `tt_crawler_full` (sea floor) | 466 | 69 | −5 / +8 | 1.2 | |
| `ttp_crawler_shore` (uphill, land) | 466 | 146 | −9 / +18 | 1.4 | linear guess across slope changes |
| `ttp_crawler_downhill` (land, heading east from X 7168) | 466 | 124 | −2 / **+29** | 7.8 | sawtooth 7, 14, 21, 28, then 0 |
| `ttp_jeeptype_downhill` (`$6220 = 1` poked, same place) | 363 (gear) | - | −1 / +31 | 7.3 | 44 % of eye height 70 |
| `ttp_foottype_downhill` (`$6220 = 5`) | 341 | - | −2 / +22 | 6.8 | 44 % of 50 |
| `ste_crawler_dh_lin` (scratch build, level rule switched off) | 466 | 112 | 0 / +26 | 8.6 | per frame `1:0 2:5 3:11 4:16 5:22 1:0 ...` |
| `ste_crawler_dh_lvl` (scratch build, level rule on) | 466 | 114 | **0 / 0** | 0.0 | |

Cause [disasm]: `subpass` sets `$764c = lin(P0.alt, SH.alt, j)` with `j` forced to 5 when the tick's delta is negative (the rule protects air vehicles from dipping under the terrain) and otherwise `T_end + delta*(PH-1)/5`. For flags bit0/bit6 types `$764c` really is integrated per tick, so a linear guess is the natural extension. For the ground and surface types the tick throws the old value away and writes `level(X,Y) + $66e2`; the right value in an extra frame is the same expression at the predicted X,Y. The slope tilt of these types is already obtained that way (`$346c8` on the predicted position), so today tilt and position move at 25 Hz while the height moves at 5 Hz.

## 5. Proposed general mechanism and the experiment

### 5.1 Design
Keep p3cp's structure (it is the common-call design: one unmodified tick per group, extra frames display only, state restored before the next tick). Change one rule inside `subpass`, selected by the type block's flags exactly as the game's tail does, no vehicle list:

```
after the predicted X/Y are written and the linear $764c is stored:
  type $f, $10, $11                -> keep (own tails)
  flags bit0                       -> keep (air: integrator, "never downwards" stays)
  flags bit4                       -> $764c = $5062(X-$6400, -(Y-$6400)) + $66e2      (surface: max(terrain, wave-aware sea))
  flags bit2, or not bit6          -> $764c = $5068(X-$6400, -(Y-$6400)) + $66e2      (ground / sea floor)
  flags bit6 only                  -> keep (submarine types: integrator + clamp)
```
`$66e2` after a tick of these types is `$750c[type]` (written by `$34880` in the tail) and no extra pass writes it. `$5068`/`$5062` (jump slots to `$1fcf4`/`$1fd44`) read only the height grid and, for `$5062`, the wave table through `$1dfba` (which `rewave` has set to the tick's phase); they write no memory and clobber d0-d7/a0 [disasm `$1fbec-$1fd68`].

**Sites: none new.** The change is inside the `p3cp_head` blob: `subpass` (one `jsr level` after `move.w d0,$764c.w`) and a 118-byte routine; the experiment placed it in the unused gap between the hook (`$b8000-$b8011`) and the head (`$b8100`), so the code still ends below `$b8700` (`$b86ab`). `p3cp_head`'s site `$31486` (`4df8770e4eb84f5a`) and the three sister sites keep their bytes. A release version drops the experiment's switch word `LVLX` (`$b8fb4`) and counter `LVLN` (`$b8fb8`) and the `movem` (d0-d6 are dead after the altitude block of `subpass`, d7 is reloaded by `moveq #5,d7`, a2/a3 survive the calls): about 80 bytes.

Group-end state: unchanged by construction. `$764c` is in the restore table (`RTAB: dc.w 1,$764c`), the height functions are pure, and the tick itself never reads the previous `$764c` of a level type except to copy it to `$66fe` (pre-move copy) - which is exactly the word the negative control breaks.

### 5.2 Experiment (scratch patch `work/crawler_smooth/patches/p3cp_head.s`, built with `cs.build_scratch`, applied live to snapshots)
- Display [obs]: `ste_crawler_dh_lvl` vs `ste_crawler_dh_lin` (same build, `LVLX` poked): error 0/0 in 114 extra frames vs 0/+26; 150 vs 148 flips in 350 VBL; a new picture in every flip in both; screenshot `logs/ste_crawler_dh_lvl.png` is a normal view.
- Group-end equality [obs]: `gate.py` restores a 2 MB STE snapshot, applies the set and the input pokes at the first flip after the same absolute VBL, dumps 18 regions (`$6600-$77ff`, NPC table, effects, projectiles, HUD, fatigue, odometer, probes, wave phase and pointer) at every `pc = $31586` for 41 ticks and compares option A (`tick_vbl tick_head tick_render`) with P (shipped `p3cp_head p3c_sim p3c_render`) and L (the level build), with the mask list of `vehicles_p3b.md` section 4. `logs/gate_crawler_downhill.txt`, `logs/gates_all.txt`, `logs/gates_more.txt`:

| Scenario (41 ticks) | A vs P | A vs L | level calls in L |
|---|---|---|---|
| Crawler downhill on land, full throttle, 32 MHz | identical | identical | 140 |
| **negative control N** (L with the restore table cut before `$764c`) | - | **40 of 41 ticks differ** (`$66fe`) | 133 |
| Crawler sea floor, full throttle + turn, 32 MHz | identical | identical | 171 |
| same, 16 MHz | identical | identical | 51 |
| Crawler across the shore (sea -113 -> land +505), 32 MHz | identical | identical | 160 |
| Crawler standing | identical | identical | 0 |
| Jeep move+turn | identical | identical | 136 |
| Truck move+turn | identical | identical | 94 |
| Tank (type poked) move+turn | identical | identical | 148 |
| on foot move+turn (second run; in the first run P differed in the effects table `$40e4-$4104` in all 41 ticks while L was identical: the start-one-flip-apart harness flake described in `vehicles_p3b.md` section 4) | identical | identical | 116 |
| Ship move+turn (surface path `$5062`) | identical | identical | 165 |
| Hovercraft move+turn | identical | identical | 93 |
| Swimming move+turn | identical | identical | 170 |
| Speedboat snapshot, stand and move+turn, two start VBLs (the player is Swimming, type 21, from tick 1 in all of them) | identical x4 | identical x4 | 107-154 |
| Helicopter move+turn (air: rule not used) | identical | identical | 0 |
| Submarine move+turn (bit6: rule not used) | identical | identical | 0 |

### 5.3 Verification plan for a real patch
1. `mw2patch.py verify` and `build` (blob still below `$b8700`; no new site).
2. `gate.py` matrix as above for all 22 types (15 snapshots + forced types 0, 4, 8, 11, 14, 16, 20) x stand / move+turn / move+turn+button at 16 and 32 MHz, with the negative control in every batch; the Esc batch of `vehicles_p3b.md` section 5 (type changes); a Speedboat run that stays type 6.
3. Display: `pf.py` + `hgt.py` on Crawler (sea floor, shore, land up and down), Jeep, on foot: error 0 in every extra frame; rows 0-57 (HUD) of `lin` vs `lvl` compared per flip (the height read-out is written by the tick's HUD writer `$50b6`; that the gauge draw `$50b0` of an extra frame does not read live `$764c` is **[INFERENCE]**).
4. Snapshot A/B for the user: `runs`-style side by side of `LVLX = 1` / `0` on the TT, downhill at full throttle, and a TT cold boot of the built image (`cold_tt.py`) into the Crawler.
5. The release matrix of `vehicles_p3b.md` section 12 (HD STE / ST / Mega STE / TT, floppy), since `p3cp_head` is in every build.

### 5.4 Cost and risks
- Cost: one height lookup per rendered extra frame of a level type: `$5068` is a cell lookup plus two `muls` (about 400-500 cycles on a 68000), `$5062` twice that; a frame is 200 k-1.6 M cycles. No measurable fps change (150 vs 148 flips).
- Surface types read the wave table at the phase `rewave` restored (the phase the tick saw). After a map-window rebuild the tick's sim can see the pointer at the table base instead (`vehicles_p3b.md` section 2), so for that one group the extra frames may show a height that differs from PH 1 by up to the wave amplitude. Display only **[INFERENCE, not provoked]**.
- With `p7_skip_wv2` in the build, `$5062` passes through its hook at `$1fd1c` and sets the static skip's `WAVE` flag: the skip then also requires an unchanged wave phase. It can only make the skip more conservative, and the level rule only runs when the pose changed (`INT = 1`), when the skip does not fire anyway [disasm]; the gates above ran without the p7 set, the display runs with the full default set.
- Submarine types resting on the sea floor (`$66e2 < $32` -> ground tail) keep the linear rule; Balloon / Rocket Pack / Parachute keep it too. They could get their own level forms later; not needed for B1.
- Predicted X/Y stay inside the grid: the jump limit is `$1000` per tick, so at most 3277 units beyond the window bounds `[$1388,$b478]`, cells 3..96 of 100 [model].
- Not tested here: 8 MHz (same code, few extra frames), cold boots of a build with the change, floppy, real mouse on the level build.

### 5.5 Further options (not tested)
- **Auto-drive smoothing**: drop the `tst.w $40b6 / bne.s .wait` test in the head. The pose words `$37626` writes are the ones p3cp already records and restores, and its tail is the same view code; `$37a0a` reads `$7662/$7664` only from the key dispatcher, which runs at PH 1 after `fixup`. Needs a snapshot with a route set (map screen) and its own gate. **[INFERENCE]**
- **8 MHz**: no extra frame fits (Crawler 5.0 fps, 29 of 30 flips are PH 1). Smoothness there is a render-cost question, not a scheduler one.

## 6. Reproduce
```
cd work/crawler_smooth
python3 pf.py --snap raid_crawler_panao.sav --mach ste --mhz 32 --scen fwd --frames --tag x            # default set live, per-flip table
python3 tt_enter.py 126 159 crawler                                                                    # TT snapshot (Hatari 2.6.1) from fire_tt14fix_map.sav
python3 cold_tt.py                                                                                     # TT cold boot with the patched Hatari -> snap/ttp_crawler.sav
HATARI=<patched hatari> python3 pf.py --snap snap/ttp_crawler.sav --mach tt --scen stand --poke 6fba=02580000 --frames --tag y
python3 pf.py --snap raid_crawler_panao.sav --mach ste --mhz 32 --live lvl --scen stand \
        --poke 6fba=02580000 66e6=00001c00 6742=0100 6294=0100 764a=0100 [b8fb4=0001] --frames --tag z # level build; b8fb4=0001 = shipped rule
python3 hgt.py runs/z.txt -v                                                                           # shown height vs terrain model
python3 gate.py NAME SNAP MHZ 41 --poke ... --sets A P L N ; ./gates.sh                                # group-end equality
```
Harness traps met: a chain of `:once :file` breakpoints re-armed at the same pc stalls Hatari after 15 hits (use one persistent breakpoint); the TT snapshots of `work/snapshots` load only in Hatari 2.6.1 (`HATARI=hatari`), the patched 2.6.1-devel needs its own (`snap/ttp_*.sav`); `mw2raids.enter_raid` reports `vehicle: 0` on the TT although `$6220 = 7`; the Speedboat snapshot turns into Swimming at the first tick when the set is applied at VBL 153960 or 154400.


## CrawlerApply (2026-11-16): the level fix shipped in `patches/p3cp_head.s`

Applied by CrawlerApply on the user's go-ahead ("the crawler is good"). **What changed:** `patches/p3cp_head.s` only (+34 lines): routine `level` ($B8012, between the hook and the head) and one `jsr level` in `subpass` after the linear `move.w d0,$764c.w`; the experiment's switch `LVLX` / counter `LVLN` and the `movem` are gone (d0-d6/a0 are dead after the altitude block, d7 is reloaded, a2/a3 survive `$5068`/`$5062`: [disasm] of `$1fbec-$1fd68` uses only d0-d7/a0). No new site, no other patch changed. Blob code now ends at `$B86AC` (was `$B86A8`; limit `$B8700`); `mw2patch.py verify`: ALL OK. Before copy for A/B: `work/crawler_smooth/before/p3cp_head_before.s` (= git HEAD version), experiment copy `before/p3cp_head_experiment.s`.

Harness changes (scratch only): `gate.py` P = the scratch patch dir (now holding the BEFORE `p3cp_head.s`), L / N = the real `patches/` tree (the new file); sequential (one Hatari at a time); direct `P vs L` comparison added; the LVLN counter read is dropped (no debug state any more, so "level calls" shows n/a). `gates.sh` / `gates2.sh .. gates4.sh`, `shots.py`, `shots_png.py`.

### Verification [obs]
1. `python3 tools/mw2patch.py verify` -> `verify: ALL OK` (also run by `tools/package.sh`). **[done]**
2. **Group-end state gates** (`gate.py`: 41 ticks, 18 regions, `A` = unmodified tick at 5 Hz, `P` = shipped-before p3cp, `L` = new p3cp; STE 2 MB snapshots). Raw: `logs/gates_apply.txt` (first batch), `gates_apply2/3/4.txt` (reruns). Every scenario of the §5.2 list was run: Crawler sea / shore / land downhill / standing, Jeep, Truck, Tank (type poked), on foot, Ship, Hovercraft, Swimming, Speedboat (stand and move), Helicopter, Submarine; 32 MHz all, 16 MHz Crawler sea, 8 MHz Crawler sea and Jeep. Negative control `N` (L with the restore table cut before `$764c`): 40 of 41 ticks differ (`66fe-66ff`, `66ff`).
   The harness flake of §5.2 (NPC table `35bf-35df` / effects table, one run of the A/P/L triple starts one flip apart) hit single runs again (crawler_shore L, crawler_stand P, speedboat_stand P, crawler_downhill P and L in other runs); each affected scenario was rerun (other start VBL `--at 154500/154700` where the same flake repeated) until a run with A, P and L all equal: every scenario has at least one run with `A vs L` IDENTICAL and `P vs L` IDENTICAL or `A vs P` IDENTICAL. **Not clean: Jeep at 8 MHz**: `A vs P` and `A vs L` both differ in 10 / 10 / 18 ticks (`1877d`, `1dfbd` wave phase, `34939` probe) in three runs, with `P vs L` IDENTICAL (41/41): at 8 MHz the shipped-before scheduler already differs from the 5 Hz game there; the new code adds no difference to it. The Crawler at 8 MHz (sea) is A-identical for both.
```
### logs/gates_apply.txt
GATE crawler_sea_movturn_32_N A vs L: ticks compared 41, ticks with any difference 0 IDENTICAL (level-rule calls in the run: n/a)
GATE crawler_sea_movturn_32_N A vs N: ticks compared 41, ticks with any difference 40 (level-rule calls in the run: n/a)
GATE crawler_sea_movturn_32 A vs P: ticks compared 41, ticks with any difference 0 IDENTICAL (level-rule calls in the run: n/a)
GATE crawler_sea_movturn_32 A vs L: ticks compared 41, ticks with any difference 0 IDENTICAL (level-rule calls in the run: n/a)
GATE crawler_sea_movturn_16 A vs P: ticks compared 41, ticks with any difference 0 IDENTICAL (level-rule calls in the run: n/a)
GATE crawler_sea_movturn_16 A vs L: ticks compared 41, ticks with any difference 0 IDENTICAL (level-rule calls in the run: n/a)
GATE crawler_shore_32 A vs P: ticks compared 41, ticks with any difference 0 IDENTICAL (level-rule calls in the run: n/a)
GATE crawler_shore_32 A vs L: ticks compared 41, ticks with any difference 41 (level-rule calls in the run: n/a)
GATE crawler_land_downhill_32 A vs P: ticks compared 41, ticks with any difference 41 (level-rule calls in the run: n/a)
GATE crawler_land_downhill_32 A vs L: ticks compared 41, ticks with any difference 41 (level-rule calls in the run: n/a)
GATE crawler_sea_movturn_8 A vs P: ticks compared 41, ticks with any difference 0 IDENTICAL (level-rule calls in the run: n/a)
GATE crawler_sea_movturn_8 A vs L: ticks compared 41, ticks with any difference 0 IDENTICAL (level-rule calls in the run: n/a)
GATE jeep_movturn_8 A vs P: ticks compared 41, ticks with any difference 10 (level-rule calls in the run: n/a)
GATE jeep_movturn_8 A vs L: ticks compared 41, ticks with any difference 10 (level-rule calls in the run: n/a)
GATE crawler_stand_32 A vs P: ticks compared 41, ticks with any difference 41 (level-rule calls in the run: n/a)
GATE crawler_stand_32 A vs L: ticks compared 41, ticks with any difference 0 IDENTICAL (level-rule calls in the run: n/a)
GATE jeep_movturn_32 A vs P: ticks compared 41, ticks with any difference 0 IDENTICAL (level-rule calls in the run: n/a)
GATE jeep_movturn_32 A vs L: ticks compared 41, ticks with any difference 0 IDENTICAL (level-rule calls in the run: n/a)
GATE speedboat_movturn_32 A vs P: ticks compared 41, ticks with any difference 0 IDENTICAL (level-rule calls in the run: n/a)
GATE speedboat_movturn_32 A vs L: ticks compared 41, ticks with any difference 0 IDENTICAL (level-rule calls in the run: n/a)
GATE speedboat_stand_32 A vs P: ticks compared 41, ticks with any difference 41 (level-rule calls in the run: n/a)
GATE speedboat_stand_32 A vs L: ticks compared 41, ticks with any difference 0 IDENTICAL (level-rule calls in the run: n/a)
GATE hovercraft_movturn_32 A vs P: ticks compared 41, ticks with any difference 0 IDENTICAL (level-rule calls in the run: n/a)
GATE hovercraft_movturn_32 A vs L: ticks compared 41, ticks with any difference 0 IDENTICAL (level-rule calls in the run: n/a)
GATE swimming_movturn_32 A vs P: ticks compared 41, ticks with any difference 0 IDENTICAL (level-rule calls in the run: n/a)
GATE swimming_movturn_32 A vs L: ticks compared 41, ticks with any difference 0 IDENTICAL (level-rule calls in the run: n/a)
GATE ship_movturn_32 A vs P: ticks compared 41, ticks with any difference 0 IDENTICAL (level-rule calls in the run: n/a)
GATE ship_movturn_32 A vs L: ticks compared 41, ticks with any difference 0 IDENTICAL (level-rule calls in the run: n/a)
GATE truck_movturn_32 A vs P: ticks compared 41, ticks with any difference 0 IDENTICAL (level-rule calls in the run: n/a)
GATE truck_movturn_32 A vs L: ticks compared 41, ticks with any difference 0 IDENTICAL (level-rule calls in the run: n/a)
GATE tanktype_movturn_32 A vs P: ticks compared 41, ticks with any difference 0 IDENTICAL (level-rule calls in the run: n/a)
GATE tanktype_movturn_32 A vs L: ticks compared 41, ticks with any difference 0 IDENTICAL (level-rule calls in the run: n/a)
GATE heli_movturn_32 A vs P: ticks compared 41, ticks with any difference 0 IDENTICAL (level-rule calls in the run: n/a)
GATE heli_movturn_32 A vs L: ticks compared 41, ticks with any difference 0 IDENTICAL (level-rule calls in the run: n/a)
GATE submarine_movturn_32 A vs P: ticks compared 41, ticks with any difference 0 IDENTICAL (level-rule calls in the run: n/a)
GATE submarine_movturn_32 A vs L: ticks compared 41, ticks with any difference 0 IDENTICAL (level-rule calls in the run: n/a)
### logs/gates_apply2.txt
GATE crawler_shore_32_rerun A vs P: ticks compared 41, ticks with any difference 0 IDENTICAL (level-rule calls in the run: n/a)
GATE crawler_shore_32_rerun A vs L: ticks compared 41, ticks with any difference 0 IDENTICAL (level-rule calls in the run: n/a)
GATE crawler_downhill_32 A vs P: ticks compared 41, ticks with any difference 41 (level-rule calls in the run: n/a)
GATE crawler_downhill_32 A vs L: ticks compared 41, ticks with any difference 0 IDENTICAL (level-rule calls in the run: n/a)
GATE speedboat_stand_32_rerun A vs P: ticks compared 41, ticks with any difference 41 (level-rule calls in the run: n/a)
GATE speedboat_stand_32_rerun A vs L: ticks compared 41, ticks with any difference 41 (level-rule calls in the run: n/a)
GATE jeep_movturn_8_rerun A vs P: ticks compared 41, ticks with any difference 10 (level-rule calls in the run: n/a)
GATE jeep_movturn_8_rerun A vs L: ticks compared 41, ticks with any difference 10 (level-rule calls in the run: n/a)
### logs/gates_apply3.txt
GATE crawler_downhill_32_b A vs P: ticks compared 41, ticks with any difference 0 IDENTICAL (level-rule calls in the run: n/a)
GATE crawler_downhill_32_b A vs L: ticks compared 41, ticks with any difference 41 (level-rule calls in the run: n/a)
GATE crawler_downhill_32_b P vs L: ticks compared 41, ticks with any difference 41 (level-rule calls in the run: n/a)
GATE speedboat_stand_32_b A vs P: ticks compared 41, ticks with any difference 0 IDENTICAL (level-rule calls in the run: n/a)
GATE speedboat_stand_32_b A vs L: ticks compared 41, ticks with any difference 0 IDENTICAL (level-rule calls in the run: n/a)
GATE speedboat_stand_32_b P vs L: ticks compared 41, ticks with any difference 0 IDENTICAL (level-rule calls in the run: n/a)
GATE jeep_movturn_8_b A vs P: ticks compared 41, ticks with any difference 18 (level-rule calls in the run: n/a)
GATE jeep_movturn_8_b A vs L: ticks compared 41, ticks with any difference 18 (level-rule calls in the run: n/a)
GATE jeep_movturn_8_b P vs L: ticks compared 41, ticks with any difference 0 IDENTICAL (level-rule calls in the run: n/a)
GATE crawler_stand_32_b A vs P: ticks compared 41, ticks with any difference 0 IDENTICAL (level-rule calls in the run: n/a)
GATE crawler_stand_32_b A vs L: ticks compared 41, ticks with any difference 0 IDENTICAL (level-rule calls in the run: n/a)
GATE crawler_stand_32_b P vs L: ticks compared 41, ticks with any difference 0 IDENTICAL (level-rule calls in the run: n/a)
### logs/gates_apply4.txt
GATE foot_movturn_32 A vs P: ticks compared 41, ticks with any difference 0 IDENTICAL (level-rule calls in the run: n/a)
GATE foot_movturn_32 A vs L: ticks compared 41, ticks with any difference 0 IDENTICAL (level-rule calls in the run: n/a)
GATE foot_movturn_32 P vs L: ticks compared 41, ticks with any difference 0 IDENTICAL (level-rule calls in the run: n/a)
GATE crawler_downhill_32_c A vs P: ticks compared 41, ticks with any difference 0 IDENTICAL (level-rule calls in the run: n/a)
GATE crawler_downhill_32_c A vs L: ticks compared 41, ticks with any difference 0 IDENTICAL (level-rule calls in the run: n/a)
GATE crawler_downhill_32_c P vs L: ticks compared 41, ticks with any difference 0 IDENTICAL (level-rule calls in the run: n/a)
GATE crawler_shore_32_b A vs P: ticks compared 41, ticks with any difference 0 IDENTICAL (level-rule calls in the run: n/a)
GATE crawler_shore_32_b A vs L: ticks compared 41, ticks with any difference 0 IDENTICAL (level-rule calls in the run: n/a)
GATE crawler_shore_32_b P vs L: ticks compared 41, ticks with any difference 0 IDENTICAL (level-rule calls in the run: n/a)
GATE foot_movturn_32 A vs P: ticks compared 41, ticks with any difference 0 IDENTICAL (level-rule calls in the run: n/a)

GATE foot_movturn_32 A vs L: ticks compared 41, ticks with any difference 0 IDENTICAL (level-rule calls in the run: n/a)

GATE foot_movturn_32 P vs L: ticks compared 41, ticks with any difference 0 IDENTICAL (level-rule calls in the run: n/a)

GATE crawler_downhill_32_c A vs P: ticks compared 41, ticks with any difference 0 IDENTICAL (level-rule calls in the run: n/a)

GATE crawler_downhill_32_c A vs L: ticks compared 41, ticks with any difference 0 IDENTICAL (level-rule calls in the run: n/a)

GATE crawler_downhill_32_c P vs L: ticks compared 41, ticks with any difference 0 IDENTICAL (level-rule calls in the run: n/a)

GATE crawler_shore_32_b A vs P: ticks compared 41, ticks with any difference 0 IDENTICAL (level-rule calls in the run: n/a)

GATE crawler_shore_32_b A vs L: ticks compared 41, ticks with any difference 0 IDENTICAL (level-rule calls in the run: n/a)

GATE crawler_shore_32_b P vs L: ticks compared 41, ticks with any difference 0 IDENTICAL (level-rule calls in the run: n/a)

```
3. **Display check, Crawler downhill on land** (`pf.py` on `raid_crawler_panao.sav`, STE 32 MHz, full default set, speed 466, east from X 7168; builds `build/dh_old` = BEFORE p3cp_head from the scratch dir, `build/dh_new` = the real tree; `hgt.py` = offline copy of `$5068`; shown `$764c` minus (terrain at the shown X/Y + 50), extra frames only):
```
runs/apply_dh_old.txt PH1 rows: model==$34936 35/35; extra frames 102: min 1 max 16 mean|e| 6.1; |e|>10: 20
runs/apply_dh_new.txt PH1 rows: model==$34936 35/35; extra frames 101: min 0 max 0 mean|e| 0.0; |e|>10: 0
```
   Old, steep stretch (X 10996-11204), per frame error: `0 4 8 12 16 | 0 4 8 12 16` (shown height frozen, 282 then 262 at the ticks); new: 0 in every extra frame. Flips 137 vs 136 in 350 VBL (no fps cost visible). **What is compared** (the pixel A/B gate does not apply: the picture of an extra frame differs by design): the shown height of every extra frame against the game's own terrain function at that frame's X/Y; the group-end state against the unpatched game (item 2). That the *picture* of the new frames is "right" is shown only by the screenshots below and by `hgt.py`'s 0 error; not by a pixel reference.
4. **Screenshots** (TT 4 MB, TOS 3.06, `--mmu true`, patched Hatari, cold-boot snapshot `snap/ttp_crawler.sav` = v1.4 code, i.e. the BEFORE blob; AFTER = the same snapshot with the new blob bytes `$B8000-$B86FF` poked in; same pokes: Crawler east at full throttle from X 10900; 14 consecutive flips each, `shots.py`): `ab/before_{1..4}.png`, `ab/after_{1..4}.png`, `ab/montage.png`; all 14 flips + raw buffers in `ab/*_flipNN.png`, `ab/raw_*`; per-flip PH/X/height `logs/shots_before.txt`, `logs/shots_after.txt`. BEFORE 1-4 = flips 8-11 (shown height 267, 251, 251, 251 at X 11136, 11173, 11191, 11209: tick drop of 16 then frozen); AFTER 1-4 = flips 10-13 (258, 251, 248, 245 at the same X: 3 units per frame). The images use one fixed palette (that of before flip 08; the game fades its palette from frame to frame). The first group after the pose poke is an artifact of the poke in BEFORE (alt 593/904/1215 from the stale shadow) and not part of the comparison.
5. **Cold boot, HD build** (`build/game` = the default set, STE, TOS 1.62, 1 MB): `python3 tools/asn_mus_cold.py run crawler_hd_ste162 ste 162 1024 hd build/game --no-profile --intro 8 --to 3d` (the tool has no stage `boss`; `3d` is its last stage short of F5) ran through logo, M/J/K, hall, personnel, map, island, objectives, boss screen and reached the 3D view (`work/asn_cold/mus_crawler_hd_ste162_3d.png`: cockpit, sky, ground). Its asn music checks print FAIL / 0 of 10 because this build has no asn_* patches (expected, nothing to do with this change). The cold boot was not run with a Crawler or on a TT / ST / Mega STE.
6. **Floppy build:** `python3 tools/mw2patch.py build --floppy --out build/crawler_fl` built clean (3 images of 737280 B + the blank disk, no error); `tools/package.sh` rebuilt both zips (floppy zip included): `dist/Midwinter2_v1.5_patched_2026-11-16.zip` md5 `40f5e59636a3870d259d14d40a0dd225`, `dist/Midwinter2_v1.5_patched_floppies_2026-11-16.zip` md5 `e4fcd7d1ebc8a5c774083304d342b9e6`; `build/game/RUNME.TOS` `c022bb63b4c76677252d813ee6b2421a`, `HAGA` `1074342dd4a917bafdc7d2a031e9b088`. The floppy build was not booted.

### §5.3 plan status
1. verify + build: **done**. 2. gate matrix: **partly**: the §5.2 scenario list at 32 MHz + Crawler 16 MHz + Crawler/Jeep 8 MHz with the negative control; NOT the 22-type matrix with forced types 0 4 8 11 14 16 20, the Esc (type change) batch, or the move+turn+button variants. 3. display `pf.py` + `hgt.py`: **Crawler downhill land only** (error 0 in 101 of 101 extra frames); NOT sea floor / shore / up-hill / Jeep / on foot, and the HUD rows 0-57 `lin` vs `lvl` comparison was not done. 4. TT screenshots: **done** (item 4 above); not the TT cold boot of the built image into the Crawler. 5. release matrix (HD STE / ST / Mega STE / TT, floppy): **only HD STE 1 MB cold boot** (item 5), floppy builds only.
Unproven: the surface path (`$5062`: Ship / Hovercraft / Swimming) has a group-end gate but no display check of its shown height [INFERENCE: correct by the same code and the game's own tail]; Jeep at 8 MHz is not A-equal (also before this change).
