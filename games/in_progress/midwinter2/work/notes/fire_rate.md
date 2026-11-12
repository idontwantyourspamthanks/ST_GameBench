# Fire rate: one press threw up to 3-5 grenades (v1.4, fast machines)

Author: MW2Fire. Evidence = raw tool output (`work/fire/out/*.raw|json`, driver `work/fire/fire.py`, table `work/fire/tab.py`, gate logs `work/fire/{ab10,ab40,ab10k,ab40k,rate,rate_nokeys}.log`) or a disassembly line of `work/dumps/ram_ingame_lobos.bin`. Anything else is [INFERENCE].

## 1. Root cause

* Fire consumer (J mode): `$1ab70: tst.w $eb76.l / beq $1ab86`, `$1ab78: tst.w $6872.w / beq.w $1b31c`, `$1ab80: clr.w $6872.w`, `$1ab84: bra.b $1ab8e` -> weapon table `jmp (a0)`. It is `$1aaa4` (table stub `$50ce: jmp $1aaa4`), called from the frame loop tail `$315d4: jsr $50ce.w`.
* `$6872` is a LEVEL, not an event: `$26bea: move.b (a0),d2 / $26bec: andi.w #3,d2 / $26bf0: move.w d2,$6872.w` runs every VBL (`$262c8` site) while the stick button is held, so the consumer's `clr.w $6872` is re-armed within one VBL.
* Hand grenade (idx 4, `$1afb2`), grenade launcher (idx 5, `$1b00a`), flare (`$1ad12`) have NO cooldown: `$1afb2..$1affc: ... subq.b #1,d1 / move.b d1,(a0,d0.w) ... jsr $4f00.w` (ammo byte `$ef8a+idx` decremented, projectile spawned, once per call). Sniper rifle/pistol use cooldown words `$4072/$4074` decremented once per tick (`$32f06`).
* The original runs the loop tail `$315c6: jsr $4f36 / $315ca: jsr $32db6 / $315d0: jsr $4f66 / $315d4: jsr $50ce / $315d8: jsr $30f72 / $315de: bra.w $31486` once per tick. `p3cp_head`'s extra passes (PH 2-5, every 40 ms) enter `jmp $3158c` (HUD, renderer, flip) and so run the SAME tail: key fetch, fire consumer and F-key dispatcher up to 5 times per 5 Hz tick. Held/pressed fire therefore threw a grenade in every extra pass. Measured (TT, v1.4, hand grenade, J mode): `KEYC` (pc `$1aaa4` hits) = 14 per 10 ticks on foot, 24 per 10 ticks in a Jeep (2 s hold); a 200 ms press = 2 grenades on foot, 3 with Jeep missiles.
* Not the cause: jag (section 4), catch-up ticks (section 3), p5_ctl_* (no `$6872` access: `grep 6872 patches/*.s` only finds a comment in jag_btn), p7_skip_render (render only). M/K mode is unaffected because the key is a one-shot latch (`$7684`, cleared by the fetch) - exactly 1 per press in every build.

## 2. Fix: new patch `p3cp_keys` (+ one instruction in `p3cp_head`)

* `patches/p3cp_head.s`: `.cont` (extra pass) now does `move.w #1,10(a0)` (EXTRA = D+10 = `$B42EA`, the old HOLD word; cleared with SUB by `clr.l 8(a0)` at every head entry).
* `patches/p3cp_keys.s` (`default: yes`, site `$315d0`, orig `4eb84f664eb850ce`): `jmp $b7e00.l / nop`; blob `tst.w EXTRA / bne .skip / jsr $4f66.w / jsr $50ce.w / jmp $315d8.l`, `.skip: jmp $315de.l`. Extra passes run no key fetch, fire consumer or F-key handler; PH 1 and plain passes are the original tail (the blob is entered by `jmp`, so the stack depth at each `jsr` is the original's). Without p3cp_head the word is zero = original behaviour.
* Result: the consumer runs once per tick that renders (`KEYC` = `TICK` on a machine that keeps up). A held J fire = one throw per tick (5 Hz, stock's own auto-repeat, per tick not per frame); a tap between ticks is missed, as in stock.

## 3. Tables. Hand grenade (idx 4, on foot, type 5) and Jeep orca/missile (idx 16, type 1); mean launched per press (ammo byte delta over [down, next down)), n = 6/6/4 presses of 80/200/400 ms (VBL-exact, injected into the IKBD state at emulated VBLs: J = `$75a2` bit 0, M = ISR make/break replayed for Space), held = one 2 s press

(a) STOCK STE 8 MHz (1.62, 2 MB snapshots `raid_onfoot_dhafra`, `raid_jeep_dhafra`); (b) v1.4 STE 8 MHz cold boot (MW2Fire); (c) v1.4 TT cold boot (MW2Fire, TOS 3.06, 4 MB, --mmu true); (d) STOCK Mega STE 16 MHz cold boot (TOS 2.06, 4 MB, 60 Hz; MW2FireStock = 0 patches + pp_bigram_cache); (e) FIXED STE 8 MHz cold boot (MW2FireFix); (f) FIXED TT cold boot. 80/200/400 ms = 4/10/20 VBL at 50 Hz, 5/12/24 at 60 Hz (84/200/401 ms measured from CycleCounter).

| build x machine | mode | weapon | 80 ms | 200 ms | 400 ms | held 2 s |
|---|---|---|---|---|---|---|
| (a) stock STE | J | grenade | 0.33 | 0.33 | 1.00 | 5 |
| (b) v1.4 STE | J | grenade | 0.17 | 0.67 | 1.00 | 4 |
| (e) fixed STE | J | grenade | 0.17 | 0.50 | 1.25 | 4 |
| (d) stock Mega STE 16 | J | grenade | 0.67 | 1.50 | 2.00 | 9 |
| (c) v1.4 TT | J | grenade | 0.83 | **2.00** | **3.25** | **12** |
| (f) fixed TT | J | grenade | 0.33 | **1.00** | **2.00** | **10** |
| (a) stock STE | J | Jeep missile | 0.17 | 0.50 | 1.00 | 2 |
| (b) v1.4 STE | J | Jeep missile | 0.17 | 0.83 | 1.25 | 4 |
| (e) fixed STE | J | Jeep missile | 0.33 | 0.83 | 1.25 | 3 |
| (d) stock Mega STE 16 | J | Jeep missile | 0.33 | 1.00 | 1.50 | 5 |
| (c) v1.4 TT | J | Jeep missile | 1.17 | **3.00** | **4.75** | 9 (capped: `cmpi.w #6,$6820`, <=5 missiles in flight) |
| (f) fixed TT | J | Jeep missile | 0.17 | **1.00** | **1.50** | 3 |
| all six | M (Space) | grenade | 1 | 1 | 1 | 1 |
| all six | M (Space) | Jeep missile | 1 | 1 | 1 | 1 |

M-mode cells: every press launched exactly one projectile in every build and machine (the 80 ms row has a few 0 on the TT/Mega STE where the first press fell on the chain start; a_ste_jeep_M shows 0.5/0.75 at 200/400 ms for the stock snapshot: Jeep missile gate `$6820`). The mouse buttons are not fire in M mode (`$6fbe` = nose tilt, `controls.md`). Per-press lists: `python3 work/fire/tab.py <label>`.

Reading: stock fires once per world tick (frame-bound: `FIRE` = `TICK` in (a): 5 in 2 s hold = 2.5 Hz on foot at 8 MHz STE, 4.5 Hz stock Mega STE 16 MHz (d)), so stock itself is faster on a faster machine (d vs a) but still one per tick. v1.4 TT before the fix: 5 consumer runs per tick (`KEYC` 12-24 per 10 ticks). After the fix `KEYC` = `TICK` (TT: 10/10). On the STE the effect was already small (extra passes rarely run in time at 8 MHz) and the fix leaves it at the stock level. A press shorter than a tick period can be missed in stock J mode and still can (0.17-0.83 above): unchanged semantics.

### Jaguar path (Main's suspect 2): no effect
STE, jag active vs absent, J fire, live patch sets (`build/live/fire_{old,fix}_{jag,nojag}`, `work/fire/mklive.py`), snapshot `raid_onfoot_dhafra`, held 2 s: old_nojag 4, old_jag 4, fix_nojag 4, fix_jag 4; per-press means 80/200/400 ms: 0.33/0.67/1.00 (old_nojag), 0.33/0.67/1.00 (old_jag), 0.33/0.50/1.00 (fix_nojag), 0.33/0.67/1.00 (fix_jag). On the TT jag restores its sites (`np_cold2.log`), and the TT showed the bug, so jag cannot be the cause.

### Catch-up ticks (Main's suspect 1): no
`p3cp_head`: `.noclamp: clr.w 12(a0) / cmp.w 4(a0),d2 / bgt .ontime / addq.w #1,12(a0)` sets SKIP when another pass is owed; `p3c_render` ($3158c): `tst.w SKIP / beq .draw / ... addq.l #4,a7 / jmp $31486`, i.e. a catch-up tick returns to the head BEFORE the tail, so it runs no fire consumer. Measured (STE, v1.4/fixed, 2 s hold): `TICK` 9-10, `KEYC` 4 (FIRE 4): fewer consumer runs than ticks, never more. Stock under load (a, STE 8 MHz, slow frames) has `KEYC` = `TICK`, no bursts. Option A (`tick_head`, default no) was not run (not shipping). Predict-ahead extra frames: yes, that is the cause (section 1).

## 4. Gates (raw)

`mw2patch.py verify`: ALL OK. `build --out build/MW2FireFix`: `built ... with 39 patch(es) + 2 file patch(es)`, `$315d0  boot 8 4eb84f664eb850ce -> 4ef9000b7e004e71   [p3cp_keys]`.

abtest, display set (`work/mapptr/abset.txt`, 27 patches) and the same + p3cp_keys:
```
--flips 10 (display set):  1mb_ingame_walking: pixels IDENTICAL; fps base 3.1 (63 flips) -> patched 3.4 (68 flips)
--flips 10 (display set):  1mb_ingame_foot: pixels IDENTICAL; fps base 4.2 (84 flips) -> patched 27.4 (548 flips)
--flips 10 (display set):  exit=0
--flips 40 (display set):  1mb_ingame_walking: pixels IDENTICAL; fps base 2.8 (56 flips) -> patched 3.4 (68 flips)
--flips 40 (display set):  1mb_ingame_foot: pixels IDENTICAL; fps base 4.2 (84 flips) -> patched 27.4 (549 flips)
--flips 40 (display set):  exit=0
--flips 10 (+p3cp_keys):   1mb_ingame_walking: pixels IDENTICAL; fps base 3.2 (64 flips) -> patched 3.4 (68 flips)
--flips 10 (+p3cp_keys):   1mb_ingame_foot: pixels IDENTICAL; fps base 4.2 (85 flips) -> patched 27.4 (548 flips)
--flips 10 (+p3cp_keys):   exit=0
--flips 40 (+p3cp_keys):   1mb_ingame_walking: pixels IDENTICAL; fps base 2.8 (56 flips) -> patched 3.4 (68 flips)
--flips 40 (+p3cp_keys):   1mb_ingame_foot: pixels IDENTICAL; fps base 4.2 (85 flips) -> patched 27.4 (548 flips)
--flips 40 (+p3cp_keys):   exit=0
```
World rate, default set (39 patches incl. p3cp_keys), `mw2tick.py rate`, snapshot `1mb_ingame_walking`:
```
RESULT 1mb_ingame_walking 8 MHz 50 Hz: sync $fe, 160235 cycles/VBL, 93 ticks in 930 VBL = 18.60 s: 5.000 ticks/s; without stalls > 30 VBL []: 93 ticks in 930 VBL = 5.000 ticks/s
RESULT 1mb_ingame_walking 16 MHz 50 Hz: sync $fe, 320397 cycles/VBL, 120 ticks in 1480 VBL = 29.60 s: 4.054 ticks/s; without stalls > 30 VBL [(721, 288)]: 119 ticks in 1192 VBL = 4.992 ticks/s
```
(unchanged: the same two rows without p3cp_keys; the 16 MHz stall is the original game's map rebuild, `timing.md`.)

Cold boots (`work/fire/cold_fire.py`, MW2FireFix, J/M selection via M key, Raids -> Zafriya): STE 1 MB TOS 1.62 and TT 4 MB TOS 3.06 `--mmu true` both reach the 3D view (`type 5`, `view 2`), `MWPO`, site `$315d0 = 4ef9000b7e00`, blob `$b7e00 = 4a79000b42ea` (`t3.py`): 
```
fire_ste14fix_foot.sav MWPO b'MWPO' site $315d0 4ef9000b7e00 blob $b7e00 4a79000b42ea type 5 view 2
fire_tt14fix_foot.sav MWPO b'MWPO' site $315d0 4ef9000b7e00 blob $b7e00 4a79000b42ea type 5 view 2
```
Raw counter excerpt, TT v1.4 before (c_tt_J_g4, single presses): 200 ms -> `KEYC 2 FIRE 2`; 400 ms -> `KEYC 5 FIRE 5`.

## 5. Method notes / limits
* Presses are injected by Hatari breakpoint files at absolute VBLs (`b VBL > N :trace :once :file`), not by xdotool: press length is exact in emulated time. The real-key path (`--joy1 keys`, Right Ctrl) was not compared [not run].
* M-mode release replays `$76bf`, `$770a`, `$7708`; the ISR's `$7684 = $b9` for an unfetched make gives the same scancode `$39 & $7f` as the make latch and is omitted (conditional-breakpoint twins hung Hatari at 16 breakpoints and on TT/Mega STE). The STE M rows were taken with the conditional version, same results.
* `FIRE` breakpoint hit counts double in the conditional-twin M runs (breakpoint re-add artefact); the ammo byte is used as the count in `tab.py`. Jeep J: dispatch count (`FIRE`) can exceed launches (in-flight cap).
* Hatari 2.6.1; the stock STE snapshot is 2 MB (the 1 MB cold boots of the patched builds differ only in RAM size).
* The wording "exactly the stock STE count" holds per tick; stock's tick rate itself varies with frame cost (2.5-4.5 Hz), v1.4's is 5.00 Hz.
