# Hunter baseline (HunterBench)

Setup: Hatari 2.6.1, 1 MB STE, TOS 1.62, 8 MHz; "16 MHz" = `hatari-option --cpuclock 16` on the same STE (a real Mega STE/TOS 2.06 was not run, see boot.md section 1).
`fps()` counts changes of `$ff8203` over N VBL. Snapshots restore with the stick released, so walking/driving rows hold the cursor keys
(`Hunter.hold`) before measuring.

## 1. fps (600 VBL = 12 emulated seconds)
| snapshot (keys held) | 8 MHz fps | VBL/frame | 16 MHz fps (STE `--cpuclock 16`) | VBL/frame |
|---|---:|---:|---:|---:|
| foot_stand (none) | 4.50 | 11.1 | 8.33 | 6.0 |
| foot_walk (Up) | 7.42 | 6.7 | 16.75 | 3.0 |
| car_stand (none) | 5.58 | 9.0 | 10.00 | 5.0 |
| car_drive (Up) | 7.17 | 7.0 | 12.50 | 4.0 |
| car_turn (Up+Left) | 6.67 | 7.5 | 12.50 | 4.0 |
| hills_stand (none, 300 VBL) | 7.17 | 7.0 | - | - |
| 4mb_foot_stand (none, 200 VBL) | 4.75 | 10.5 | - | - |

(`car_drive` as saved sits against the shore: the car is blocked at 8 MHz, so its fps is the blocked-car view.)
Frames are always a whole number of VBLs: the flip is VBL-locked (`$aaa2`: `bset #3,$8f(a5)` spin released by the VBL handler `$c616`).
Frame cost at 8 MHz (cycles, `e CycleCounter` between loop-top hits, 20-35 frames each): stand 1,762,721; walk 1,015,560; car_stand 1,442,603; car_drive 1,121,753; car_turn 1,190,632 (split in hotpaths.md).
Flip and frame loop: flip routine `$5fd2` (writes `$ff8203`/`$ff8201` from the buffer pointers `$7f6c/$7f74`), loop `$253e..$2594`, see frameloop.md.

## 2. Is the world speed tied to the frame rate? (full check, same snapshot, 8 vs 16 MHz)
Method: breakpoint on the loop top `$253e`; at every frame log VBL, cycle counter and RAM words (player `$ab2` X/height/Z words, HUD = word/256; `$ae6` heading-like word; `$9ae..$9b9` clock block; NPC/bird triples `$c92`,`$d32`). Rates use the VBL counter as the time base. Key held from the same moment after restore (`Up`, or `Up+Left` in the car).
| run | frames | dVBL | player dX/s | dZ/s | heading word first->last | $9ae first->last (VBL counter) | $9b4 (game-clock tick) |
|---|---:|---:|---:|---:|---|---|---|
| foot_walk @8 MHz | 27 | 221 | 0.0 | 101.4 | 0 -> 0 | 4080 -> 4301 (+221) | 2 -> 3 |
| foot_walk @16 MHz | 51 | 223 | 0.0 | 100.4 | 0 -> 0 | 4128 -> 4351 (+223) | 1 -> 2 |
| car_stand @8 MHz | 26 | 217 | 90.3 | 53.9 | -25344 -> -15360 | 4030 -> 4247 (+217) | 2 -> 4 |
| car_stand @16 MHz | 51 | 220 | 100.2 | 65.7 | -23552 -> -14080 | 4074 -> 4294 (+220) | 2 -> 3 |
| foot_stand @8 MHz | 21 | 220 | 0.0 | 0.0 | -24576 -> -24576 | 3041 -> 3261 (+220) | 4 -> 0 |
| foot_stand @16 MHz | 41 | 240 | 0.0 | 0.0 | -24576 -> -24576 | 3095 -> 3335 (+240) | 3 -> 4 |

Findings:
- (a) Position change per real second: on foot (Up) **101.4 u/s at 8 MHz vs 100.4 u/s at 16 MHz** (-1 %), 6.1 vs 11.4 fps. 1 HUD unit = 256 world units, so about 0.4 units/s. In the car (Up+Left, starts from rest, accelerates) dX/s 90 vs 100 and dZ/s 54 vs 66: the car is in its acceleration phase, the two runs start ~0.3 host-seconds apart, so this row is not a clean steady-state comparison [inconclusive, within start offset]. A steady-state car number needs open ground; the island is ~20 cells wide.
- (b) Game clock: `$9ae` is a VBL counter: +221 over 221 VBL at 8 MHz, +223 over 223 VBL at 16 MHz, +220/+220 (car), +220/+240 (stand): exactly 1 per VBL at both speeds. The slow clock word `$9b4` advances about once per ~540 VBL (5 steps over 2160 VBL in a 5-sample dump series at 8 MHz) and in the runs above 1-2 steps per ~220 VBL at both clocks (same rate within sampling). The HUD clock ("00:00") only shows after the `C` key (manual).
- (c) Other entities: NPC soldier/birds (`$c92`, `$d32` triples) wander on random headings; the two runs show comparable displacement (< 100 units per 220 VBL) but no steady rate: inconclusive.
- (d) Turning in the car (Up+Left, heading word `$ae6`): 8 MHz -25344 -> -15360 = 9,984 units in 217 VBL = **2,300 units/s**; 16 MHz -23552 -> -14080 = 9,472 in 220 VBL = **2,153 units/s** (-6 %; runs start in different phases of the turn ramp). Same order, not frame-bound (frames differ 26 vs 51).

From the disassembly (no real-time source other than the VBL):
- No read of `$4ba` (hz_200), `$462` (_vbclock), `$466` (_frclock) or of MFP timer data registers anywhere in `$800-$22000` (grep of the full disassembly: 0 hits; only `$fa17` AEI bit toggles at `$11a5a/$11ac8`).
- The VBL handler `$c5f0`/`$c63a` (vector `$70`) increments two counters while the 3D loop runs: `addq.w #1,$1a8(a5)` (`$c644`, absolute) and `addq.w #1,$1aa(a5)` (`$c648`, since last frame); the frame loop copies it at `$5fa4` (`move.w $1aa(a5),$1ac(a5); clr.w $1aa(a5)`) = **elapsed VBLs of the last frame**, and the movement/physics code multiplies by it: `mulu.w $1ac(a5),d0` at `$2acc,$2af0,$2b52,$2b60,$2bd2`, `muls.w $1ac(a5),d3` at `$2bde`, plain reads at `$2738,$2770,$2a5c,$2bc2`.
- The VBL handler also runs per-VBL timers (`$699c`: countdowns `$232(a5)`, `$234`, `$186`, `$184`, `$188`), a per-VBL LFSR (`$c6a4`, `$1c6(a5)`), the IKBD joystick interrogate (`$c5fa`: `moveq #$16,d0 / bsr $afbe`) and the sound driver tick (`$c628: movea.l $7f44(pc),a0 / jmp $40(a0)`).
- A frame limiter exists (`$1a6` counter / `$1a7` reload, spin at `$aaa2`) but the reload word is 11 in the cold-boot dump and 0 in the snapshots: inactive there.

**Verdict: decoupled from CPU speed and frame rate (time-based on the 50 Hz VBL counter), with whole-VBL granularity.** What does depend on the frame rate is only smoothness: at 4.5-11 fps each frame moves the world by (elapsed VBLs) x (per-VBL step). Speeding up the renderer therefore needs no timing patch; the update rate will simply rise. [Car steady-state and NPC rates remain unmeasured.]

(Added later: the 50 Hz basis of this verdict means the world runs 20 % fast on a 60 Hz display; `hn_hz` fixes that, see timing.md.)
