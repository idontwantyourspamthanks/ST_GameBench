# Air vehicles: can the p3b 1/5-step player split be applied?

Author: MW2VehAir (analyst, no edits to `patches/`). Evidence = disassembly of `work/dumps/ram_ingame_lobos.bin` (`tools/m68dis.py`) and Hatari traces (harness `work/vehair/vh.py`, snapshots `work/snapshots/raid_*.sav`, `raids.md`). Anything not run is marked **[INFERENCE]**. Types: 12 Biplane, 13 Helicopter (reference, shipped), 14 Zeppelin, 15 Balloon, 16 Rocket Pack, 17 Parachute, 18 Flying Boat, 20 Flying Sub. Raw logs: `work/vehair/out/*.pkl` (control = unpatched snapshot, one row per `pc = $3158c` hit; B = same snapshot + live patch set, rows with `PH = 5` are group ends).

## 0. Summary

| type | code path | verdict (p3b 5 x 1/5 steps) | hooks beyond the shipped p3b set | evidence (group-end equality vs unpatched, groups) |
|---|---|---|---|---|
| 12 Biplane | generic flags bit0 (`$33da4`) | **yes** | frozen coefficients (F), type mask | moving snapshot, button + throttle + turn: 22 EQ; landing 24 EQ; ground crash 23 EQ |
| 13 Helicopter | same | shipped p3b **is not exact when the bank changes** (found); exact with F | **F** | 25 / 25 groups MISMATCH shipped, 25 / 25 EQ with F |
| 14 Zeppelin | same (view sel 0: no roll) | **yes** | F, mask | 23 EQ (heli snapshot + `$6220 = 14`) |
| 18 Flying Boat | same (flags `$09`) | **yes** | F, mask | 26 EQ (own snapshot) |
| 20 Flying Sub | same (flags `$41`) | **yes**, one caveat (water-surface crossing halves `$6750`) | F, mask | 24 EQ (heli snapshot + `$6220 = 20`) |
| 16 Rocket Pack | generic + own block `$33d26`, integrator rate selectors | **yes** | F, mask, `p3b_ctl*` (rate routines once per group), `p3b_apply3`, `p3b_probe2` (+ `p3b_rkt` defensive) | 24 EQ; **without `p3b_ctl*`: 12 / 12 MISMATCH** (integrator runs 5x) |
| 17 Parachute | own block `$33cc2`, apply sel 3, derivative rate sel 1 | **yes** (the "doubling cannot be split" is only true if you split the doubling) | `p3b_par`, `p3b_apply3`, `p3b_terr0`, `p3b_probe2`, `p3b_ctl*` | 26 EQ (turning + button), 23 EQ (full ramp, Swimming transition group EQ) |
| 15 Balloon | own block `$33c60`, integrator apply, derivative rate | **yes by design, not implemented** **[INFERENCE]** (section 6) | `p3b_bal` + the set above | control traced only (no split run) |

After the p3c design change (`MW2VehImpl`: run the original tick once per group, show the pose j/5 of the way), none of the per-type hooks is needed; sections 7-9 are the facts p3c needs (renderer inputs, pose jumps, clean test states, the wave-phase dependence). Sections 1-6 stay as the exact p3b step functions and as the proof that the old per-type "keep on 5 Hz" list is obsolete.

## 1. Tick order of `sub_033bde` (flags bit0 types) and what each step reads

Disassembly `$33bde-$33e44`, rate/apply handlers `$34142-$34880`. Per pass:

1. `$33be6-$33bf2` save pre-move pose `$66ee/$66f2/$66fe`; `$3489a` terrain sample (`$66e4`, water flag `$6774`, unused afterwards); `clr $674e`, `clr $6750`; `$6776 = flags` (`$54dc0 + type*$3e + 2`).
2. `$34142` X rate -> `$6752`; `$341cc` Y rate -> `$6756`; `$34256` button rate -> `$675a` (selectors `+$34/$31/$37`: 1 derivative `$676a/$676c`, 2 direct, 3 direct + integrator `$6754/$6758/$675c`). Not cleared per pass: `$6752/$6756/$675a` persist.
3. `$34106` `$6740 = $6752>>4`; `$343ee` apply sel `+$33` (all types 4 = `$345c4`: heading `$6742 = ($6742 + $f984 + $6740) & $3fe` -> `$6294/$764a`, lean `$674e`).
4. `$34112` `$6740 = $6756>>4`; `$34414` apply sel `+$30` (1 = `$344ac`: `$6750 += $6740`; `$33f40`: alt `$764c = clamp($764c + floor(thr*$7652/131072), -8000, 12000)`, speed `$6772 = (thr*$7654*4)>>16`; position `+= floor(sin($6294)*speed/65536)`).
5. `$3411e` `$6740 = $675a>>4`; `$3443a` apply sel `+$36` (5 = `$3461a`: bank `$6746 = sext10($6746 + $6740)`, clamp via `$7250` table only for flags without bit0/bit6).
6. `$3467c` coefficients (sel `+$3c`): 1 -> `$34762`: `$7652 = sin(bank)`, `$7654 = cos(bank)` Q14 (copies `$7642/$7644`); `$346a2` view vector (sel `+$3d`): 1 -> `$347be` roll from lean -> `$7646/$7648`, 0 -> `$34748` constant, 3 -> `$34790` from pitch `$674a`.
7. `$33e46` speed ramp `$688e/$6892` (types 1-3 only use it), `$348ec` terrain samples `$34936/$34938/$3493a` (`$5068`, `$506e`, `$5062`), then the type dispatch (`$33c54`): 15 -> `$33c60`, 17 -> `$33cc2`, 16 -> `$33d26`, flags bit0 -> `$33da4` (generic), else `$33d4c`.
8. Generic `$33da4`: `$66e4 = $3493a` (type 20: `$34936`), `$66e2 = $764c - $66e4` (AGL), probe `$34006` (`$34034`/`$340a8`: terrain/crash, collision revert to `$66ee`), landing test `$33e7a` (AGL <= 200 and `$18102 * ($753a[type]+1) >> 6 <= $7300[type]`; sets `$767e`, bank := 0, alt := ground + `$750c[type]`), throttle floor `$33f00` (`$a(a0) = $c8`, Biplane/Flying Boat/Flying Sub airborne) / `$33f20` (0 when landed), second probe `$33e30`, `$31dee` (map-window re-centre), `$37a62`, `$37afa`.

**Important ordering fact:** step 4 (position/altitude/speed) runs BEFORE steps 5-6, so tick k uses the coefficients `$7652/$7654` left by tick k-1 (the bank of tick k-1). This is why the shipped helicopter split is not exact when the bank changes (section 2).

There is no aerodynamic stall model. Lift is `thr * sin(bank)` (`bank` is the nose pitch, driven by the buttons); `bank > 256` (inverted) makes `cos < 0` so the speed goes negative (flies backwards, seen: bank 304 -> speed -59). The "stall" is the throttle floor of `$33f00` (200 for Biplane, Flying Boat, Flying Sub while airborne, 0 after landing) which is data written at the world pass of the probe branch, i.e. PH 5.

## 2. Types 12, 13, 14, 18, 20 (generic path)

**Verdict: yes.** All five run the code of section 1 with different table values (`$54dc0` blocks: flags 12/13/14 `$21`, 18 `$09`, 20 `$41`; apply selectors 1/4/5; rate selectors 2 = direct). The shipped p3b hooks (`p3b_pos/hdg/alt/bank/save/probe/render/head`) hook only generic code, so they apply to all five once `p3b_head`'s `cmpi.w #13,$6220` becomes a type mask.

### 2.1 Bug in the shipped p3b (Helicopter too): bank changes break the group-end state

Original tick k: `alt += floor(thr*sin(bank_{k-1})/131072)`, `speed = thr*cos(bank_{k-1})*4>>16`. Shipped `p3b_alt/pos` run `$33f40` on each of the 5 passes with the CURRENT `$7652/$7654`, i.e. the coefficients of the sub-bank (`$3467c` runs every pass). With the button held (bank +16 per tick) every group differs:

```
heliB  (raid_helicopter_lobos_moving, pokes w $6fba $01 $90 $00 $00; w $6fb6 $01 $40 $00 $00; w $6fbe $00 $01), shipped p3b
 k | alt ctl/patched | spd ctl/patched
 1 | 2000/2001 | 300/299     2 | 2003/2005 | 298/295     4 | 2020/2025 | 287/279     8 | 2094/2103 | 231/217     25 | 2651/2661 | -213/-228
 -> 25 of 25 groups mismatch (X, Y, alt, spd, agl)
```
Python model (`work/vehair/model.py`) reproduces both the control (22 ticks alt/spd/bank EQ) and the shipped deviation (alt 2001, 2005, 2013, 2025, 2040, 2058; spd 299, 295, 289, 279, 267, 253 = the patched values above).

**Fix F** (verified): in `p3b_alt` capture `$7652/$7654` into two words at HOLD = 0 (before they are used) and use the captured pair for `P0 = thr*sin` and the speed on all five passes. `$7652/$7654` themselves stay live (the renderer reads them). Result with F (heliB2): 25 / 25 groups EQ for X, Y, H, `$6294`, `$764a`, lean, bank, thr, spd, alt, `$7652/$7654`, type, `$676e`, `$6290`, clock, `$7680`, `$675a`, button. Scratch: `work/vehair/patches/p3b_alt.s` (diff to `patches/p3b_alt.s`: `FRZ` words).

Step function (per group, Q16 accumulators as shipped):
```
PH1: SIN0 = $7652; COS0 = $7654; ACC = 0
every pass: ACC += thr*SIN0 ; q = floor(ACC/655360) ; alt += q ; ACC -= q*655360 ; $6772 = (thr*COS0*4)>>16
            heading += Bresenham(e/2) steps (shipped p3b_hdg, HF frozen on PH1) ; bank += Bresenham(e) (p3b_bank)
            position += Q16 accumulator of sin(HF)*$6772 (shipped p3b_pos)
```

### 2.2 Evidence (all with p3b_head mask, F, `p3b_save`, `p3b_probe`)
```
bipM3  raid_biplane_maracay_moving, no pokes: 23 groups, 0 mismatches (keys: X Y H $6294 $764a lean bank thr spd alt $7652/54 type $676e $6290 clock $7680 $675a btn)
bipB3  same + throttle/turn/button pokes: 22 groups, 0 mismatches
fbA    raid_flyingboat_vicenza + pokes: 26 groups, 0 mismatches; bank runs to 384, speed to -228 (inverted flight)
zepA   heli_moving + w $6220 $00 $0e + pokes: 23 groups, 0 mismatches (bank step 4/tick: Zeppelin button scale 4)
fsA    heli_moving + w $6220 $00 $14 + pokes: 24 groups, 0 mismatches
bipL3  heli_moving + type 12, alt 1000 (AGL 122 -> landing at tick 1: alt 1000 -> 955, AGL 70, $767e = 1, flags $21): 24 groups, 0 mismatches
bipC   heli_moving + type 12, alt 860 (below ground), fast: crash (blk = 3) at tick 1, type 5 from tick 2 (X +256): 23 groups EQ including the crash and the type change
```
Group-end rows with PH 1..4 are present in all runs (counts e.g. zepA PH1..5 = 9/23/9/20/57), so the runs really are in sub-tick mode.

### 2.3 Caveats
* **Water:** over sea `$66e2/$66e4/$34938/$3493a` come from `$5062/$506e`, which index the sea wave table through `$1dfba`; the phase advances `+8` after every RENDER (`$1dcae-$1dcca`). The patched game renders more often, so agl/gnd and everything derived (landing at AGL <= 200, crash probes, Balloon heading) is not comparable over water (section 9). Terrain `$34936` (`$5068`) is equal (-405/-402/-402 in both runs at the same position). On land there is no dependence (heliB2, bipL3 above are on Lobos).
* `$348ec` samples the terrain AFTER the move for the generic path (positions equal at group end, so equal values), BEFORE the move for 15/17. Skipping it on passes 1-4 (`p3b_terr`, scratch) is possible (saves ~2.5 k cycles x 4) but changes nothing observable; not recommended.
* **Crash/landing events** set `$676e`; the type change itself is made by the post-flip handler `$32db6` on the next RENDERED pass. In the heli crash run (heliC: heli_moving, alt 960, throttle 492) both runs set `blk = 3` at tick 5 (EQ), but the control is type 5 at tick 6 while the patched run is still type 13 (one more group of motion, X 24288 vs 23909 then 24165 after its own relocation). Pre-existing p3b/A behaviour (the handler runs after a RENDERED pass, the patched run skips renders while "behind"), a timing latency, not a physics difference.
* **Flying Sub (20) [INFERENCE]:** `$344c0-$344d6` halves `$6750` when `$764c < 0`. The original tests the altitude of the tick start; a 1/5 pass tests the partial altitude, so a group that crosses 0 differs once. A frozen sign captured at HOLD = 0 (hook `$344c8`, 6 bytes `4a78764c 6a0a`) removes it; not run.

## 3. Type 16 Rocket Pack

Flags `$21`, apply sels: Y 3 (`$34586`: `$764c = clamp($764c + $6740, -8000, 12000)`, `$6740 = $6756>>4`, rate direct scale 10), X 4, button 1 (`$344ac` thrust), button RATE sel 3 (`$342a8`: integrator `$675c = clamp(d0*100, -1600, 1600)`, `$675a = clamp($675a + $675c, 0, 16000)`; left button +1600/tick = +100 thrust/tick, right button -1600). Own block `$33d26`: `alt = clamp($764c, $3493a + 100, 12000)`, `$66e2 = alt - $3493a`, then the probe at `$33e30`.

Not exact with the shipped set because:
1. `$342a8` integrates on every pass (5x ramp). Fix: `p3b_ctl/ctly/ctlb` skip the three rate routines (`$34142`, `$341cc`, `$34256`, 6 B each: `lea $54dc0.l,a0`) when SUB = 1 and HOLD = 1. They are not cleared per pass, so passes 2-5 reuse `$6752/$6756/$675a`.
2. `$34586` adds `$6740` on every pass (5x). Fix `p3b_apply3`: Bresenham on units of 1 (remainder cleared at HOLD = 0): `q = floor((rem + $6740)/5)`, `alt += q`, clamp each pass; the sum over 5 passes is exactly `$6740` and the partial sums are monotone, so the clamp gives the same final value.
3. The ground clamp (block `$33d26`) and the probe `$33e30` should act only on the END pose. `p3b_rkt` skips the block on passes 1-4; `p3b_probe2` (`$34006` entry: skip with `$676e := 0` unless PH = 5) skips the probe. **`p3b_rkt` was not needed in the test scenario** (without it 25 groups EQ too; the terrain was smooth); it protects against ratcheting the altitude over a hill crossed in the middle of a tick **[INFERENCE]**.

Evidence (heli_moving + `$6220 = 16`, alt 1200, throttle ramp, descending onto the ground, turn):
```
rktB  all hooks: 24 groups 0 mismatches; thr 100,200,...,1000 = original ramp, r5a 1600..16000, alt rides ground+100 from group 3
rktN  no p3b_ctl*: 12 of 12 groups mismatch (X off by 650, thr 1000 instead of 900 at group 9, r5a 16000 vs 14400)
rktK  without p3b_rkt: 25 groups 0 mismatches
```

## 4. Type 17 Parachute

Flags `$0000`; X sel 4 (direct, scale 16), Y rate sel 1 (DERIVATIVE, scale -8, `$6756 = (in - $676c)*-8`) with apply 5 (bank), button rate 2 direct scale 16 with apply sel 3 (`$34586`: `$7680 = clamp($7680 + $6740, -100, -10)`, `$6740 = $675a>>4` = 0 or +-16), coef 1 (bank sin/cos), view 1 (roll). Block `$33cc2`:
```
alt += $7680 ; $7680 *= 2  (add.w d6,d6 -> $7680)        ; fall speed state v_k = clamp(2 v_{k-1} + b, -100, -10) (the doubling ramp -10, -20, -40, -80, -100)
alt < 0                  -> type 21 (Swimming), $33e06
AGL = alt - $66e4        ($66e4 = ground at the tick START, $3489a)  ; AGL < 50 -> type 5, bank := 0, $33e1a
speed $6740 = clamp(AGL/10, 0, 100) -> $344ac (flags 0: $33f86, $6772 = $6750) -> position
```
**Verdict: exactly splittable.** The doubling is a per-tick STATE update; do not split it, keep it once per group and spread only its effect:
```
PH1 (HOLD = 0):  apply sel 3 runs once (original code)         ; v = $7680 after the apply
                 VK = v ; FA = alt + v ; $7680 = 2*v ; REM = 0
                 TR = (FA < 0) or (FA - $66e4 - 50 < 0)         ; the tick ends in a transition: the original does NOT move in that tick
every pass:      alt += floor((REM + VK)/5) (Bresenham, sum over 5 passes = VK)
passes 1..4:     $66e2 = FA - $66e4 ; speed code at $33d00 (position along the frozen heading HF) unless TR, then straight to $33e30 (no move); no transition test
pass 5:          alt == FA: original code from $33cd2 (type 21 / type 5 / speed / transitions)
```
Required companion hooks: `$34586` hook (apply once per group), `$3489a` only at HOLD = 0 (so `$66e4` is the ground of the group start, as the original), `$34006` entry (probe only at PH 5), rate routines once per group (the derivative needs input difference per TICK, see section 3).
Python check (`work/vehair/model_par.py`): 200000 random ticks (alt, `$7680`, button step, ground) give identical (alt, `$7680`, speed/transition) for original and split; the logged control run (alt 1000, `$7680 = -10`) is reproduced for 12 / 12 ticks, tick 13 -> swim (type 21 observed).
Live:
```
parC  raid_parachute_calabar + w $764c $27 $10; w $7680 $ff $f6; mouse X turn (+116/tick); Y derivative kick (bank -104); button held (v stays -10): 26 groups, 0 mismatches
parD  alt 1000, no button: $7680 -20,-40,-80,-160,-200 (v -10,-20,-40,-80,-100), alt 990,970,930,850,750,...,50 then type 21: 23 groups; 0 mismatches except alt AFTER the Swimming transition (-62 vs -57): that is wave phase, section 9
parA  first version without the TR (transition) rule: the transition tick moved 4/5 of a step (X 26654 vs 26668): rule added, parB EQ
```

## 5. Type 14 Zeppelin, 18 Flying Boat, 20 Flying Sub specifics
* 14: view sel 0 (`$34748`): constant view, no roll from lean; coef 1. No other differences (heading/bank/alt as section 2). Button scale 4: bank +4 per tick, speed floor not used.
* 18: flags `$09` (bit3: `$340a8` compares the terrain `$34936` with the water surface `$34938`; over water it skips, over land with AGL < `$64` it sets `$676e = 3`) and `$33f00` throttle floor 200; landing speed `$7300[18] = 100`, landing alt `$750c = 50`.
* 20: flags `$41` (bit6 in `$33f40`, `$34034`), uses `$34936` instead of `$3493a` at `$33db2`, throttle halved below sea level (caveat in 2.3), landing speed 120, landing alt 100.

## 6. Type 15 Balloon (design, not run)

Flags `$01`, apply: Y 5 (bank; Y rate sel 1 derivative scale -8), X 4, button apply sel 3 (`$34586`: `$764c = clamp($764c + $6740, -8000, 12000)`, `$6740 = $675a>>4` = +-32 with the left/right button, rate sel 2 scale 32), coef sel 3 (`$34748`: `$7652/$7654` NOT updated, stale), view sel 3 (pitch). Block `$33c60`:
```
G = $3493a (wave-aware ground at the tick-start position: $348ec runs before the move)
$6294 = ((alt + G) >> 1) & $3fe         ; movement/compass heading, changes with altitude AND the wave
AGL = alt - G -> $66e2 ; AGL - 50 < 0 -> landed: alt := G + $750c[15] (70), NO move ($33caa)
else speed $6740 = clamp((AGL-50)/10, 0, 800) -> $344ac (flags 1: $33f40: alt += floor(thr*$7652/131072), $6772 = thr*$7654*4>>16) -> position along $6294
```
Observed (raid_balloon_corozal, button held): alt 12000 (ceiling), speed 800, `$6294` 852, 850, 848, 850, 856, 862, 874, ... (moves with the sea height `g3a` -54, -58, -63, ...), 200 units/tick; at tick 10 the player leaves the map window and sub_031dee re-centres: X 5017 -> 25339, Y 37739 -> 26086.
Exact split design **[INFERENCE, not implemented or run]**: PH1 computes A1 = clamp(alt0 + b), `$6294 = H` from A1 and G, thr from AGL, TR/landed flag; all five passes use H (write it to `HF` so p3b_pos steps along it), the frozen thr/speed, alt += Bresenham(b/5) + `p3b_alt` Q16 term (the coefficient is the stale constant), landed ticks skip the move and set alt := G + 70 at PH 5 only. Edge: at the 12000 ceiling the original clamps twice (`clamp(clamp(alt0 + b) + step)`) while 5 partial clamps differ when `b` and `step` have opposite signs. Over water the heading depends on the wave phase (section 9). Under p3c (original tick once) none of this is needed.

## 7. What the renderer and HUD read (for p3c)
Renderer ranges `$1d000-$20500`, `$37a62-$3d500`, `$1b996`, `$30f2c`; scan `work/vehair/xref_scan.py` (xref of every word `$6700-$76ff`):
* pose: `$66e6/$66ea`, `$6742` (`$20308`), `$6746` (`$20318`), `$674a` (`$20324`), `$764c` (`$20282`, `$1dbd8`), `$764a` (`$37a6a`, `$38a5a`, `$38be2`, `$389fc`);
* bank/roll words: `$7652/$7654` (`$37a86`, `$38a1c`, `$38c2a`), `$7642/$7644`, `$7646/$7648` (`$37ad0`, rewritten `/ $6794` at `$37aec`), `$763e/$7640` (`$1dd3a`);
* view/cell: `$670a-$6710`, `$6780-$6796` from `$37afa`.
No other sim-written word is read by the render. Per type only the filler of `$7646/$7648/$7652/$7654` differs (coef sel `+$3c`, view sel `+$3d`): Zeppelin 14 has no roll (sel 0), Balloon 15 never updates `$7652/$7654` and its view comes from pitch `$674a` (constant), all others use bank sin/cos + lean roll. Balloon `$6294` (movement/compass) differs from the view heading `$764a`/`$6742`. HUD (`$1a706`, world pass): `$18102 = $6772`, `$1810e = $764c - $5062` (wave-aware), `$18108` lean, `$6748/$674c` bank/pitch copies. Weapon-fire handlers (`$1b19c`, `$1b236`, `$1b2d0`) copy `$6742`, `$764c`, `$6750`, `$7642/$7644` into projectile slots: world key events.

## 8. Pose jumps inside one player tick
* Map-window re-centre `sub_031dee` (end of every `$33bde` pass, via `$33e34`): when X/Y leave `[$1388, $b478)` (`$3451a` clears `$6288`) X/Y shift by multiples of `$200`, sector registers `$66bc/$66be` change, map reload follows. Observed in 1 tick: dX 20322, dY -11653 (Balloon). Any vehicle.
* Landing (generic types, `$33dd8`): bank := 0 (up to |192|), alt := ground + `$750c[type]` (observed 1000 -> 955), view reload `$346c8/$34708`, type unchanged.
* Crash / collision: pose reverts to the tick start (`$34056`, `$340d4`, `$1ba60`, `$1bc50`, `$1bc9c`: start == end); type change by `$32db6` later (X +256 observed at that change).
* Parachute: alt < 0 -> type 21, alt := wave + 50..; AGL < 50 -> type 5, bank 0; no motion that tick. Balloon AGL < 50: alt := ground + 70, no motion. Rocket: alt := ground + 100 clamp.
* Eject/Esc from a flyer (`$1b574`, `$32e9c`, `$3308a`, world key events): type := 17, `$7680 := -5`, bank := `$ff04`, X += `$100`.

## 9. The world reads render output: sea wave phase
`$1dcae-$1dcca`: after every render `addq.w #8,$1877c; andi.w #$7e; $1dfba = $18574 + $1877c` (16 phases). `$5062/$506e` (`$1fd44`, `$1fd0a`) add the wave table through `$1dfba`. The sim uses them in `$348ec` (`$34938/$3493a`), `$33da4` (AGL), `$33e7a` (landing), `$34034/$340a8` (crash), Balloon heading `$33c66`, HUD altitude `$1a7fc`. Evidence (bipM2, Biplane over sea, same X/Y/alt at the group end):
```
k | control gnd (g38) | patched gnd | terrain $34936 control/patched
1 | -116 | -78 | -405/-405      2 | -95 | -46 | -402/-402      3 | -71 | -8 | -402/-402
```
and a Biplane poked to alt 100 over sea (bipL, p3b set with F) had its landing/crash event (`blk = 2`, `$767e`) one group earlier than the control (control: AGL 216 > 200 at tick 1, event at tick 2 with AGL 70). Over land (terrain >= 0) no dependence. To keep A-vs-B equality over water, advance the phase once per 5 Hz group (gate the addq at `$1dcae`), which also keeps the sea animation at the original rate.

## 10. Clean moving states and reproduction
```
cd /home/ryan/Code/AtariST/gamebench/games/in_progress/midwinter2/work/vehair
python3 run1.py <snapshot.sav> <groups> <tag> '<pokes ;-separated>' <liveset>     # runs control + patched in parallel, pickles out/<tag>.pkl
python3 cmp.py <tag>          # group-end comparison; show.py <tag> <n> <keys> prints the control rows; model.py / model_par.py = Python models
```
Live sets are built from `work/vehair/patches` (scratch copy of `patches/`, `p3b_head` with `MASK` = bit n for type n, relocated blobs; `vh.mklive(name, [patch names])`, `vh.setmask(mask)`). Pokes (`w` debugger lines applied at a flip): throttle `w $6fba $01 $90 $00 $00`, turn `w $6fb6 $01 $40 $00 $00`, held button (bank +16 per tick) `w $6fbe $00 $01`, type `w $6220 $00 $0e` (14) / `$14` (20) / `$10` (16) / `$0c` (12), altitude `w $764c <hi> <lo>`.
| type | snapshot | pokes |
|---|---|---|
| 13 | `raid_helicopter_lobos_moving` | throttle, turn, button |
| 12 | `raid_biplane_maracay_moving` | throttle, turn, button (sea) |
| 18 | `raid_flyingboat_vicenza` | throttle, turn, button |
| 14 / 20 | `raid_helicopter_lobos_moving` | type poke + `w $6fba $01 $90 $00 $00; w $6fb6 $00 $c8 $00 $00; w $6fbe $00 $01` |
| 16 | `raid_helicopter_lobos_moving` | `w $6220 $00 $10; w $764c $04 $b0; w $6fba $ff $6a $00 $00; w $6fb6 $00 $d0 $00 $00; w $6fbe $00 $01` |
| 17 | `raid_parachute_calabar` | `w $764c $27 $10; w $7680 $ff $f6; w $6fb6 $00 $d8 $00 $00; w $6fba $01 $00 $00 $00` (long fall) or alt `$03e8` (sea in 13 ticks) |
| 15 | `raid_balloon_corozal` | `w $6fbe $00 $01` (control only) |
Limits: the pokes change only the player state; the island start screens of types 14, 16, 20 do not exist on any raid island (`raids.md`), their cockpit/overlays were not loaded, so only the physics was exercised. Flying Boat and Biplane runs are over sea (wave-dependent agl).
