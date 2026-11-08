# Simulation timing — how the game advances per frame

Snapshot set: `ingame_foot_walking`, `ingame_foot_banked_turn`, `ingame_lobos_foot` (on foot, mode `$6220 = 13`).
CPU profile: `work/prof/walking.txt` (`total_cycles=35321256`, 8 MHz ⇒ 4.415 s ⇒ 220.8 VBL).

## 1. Scope and cycle share

| Region (non-overlapping) | What | Cycles | % of profiled | /frame |
|---|---|---:|---:|---:|
| `$33bca`–`$348ff` | player sim: `sub_033bde`, mover, heading, speed, range, sub-step dispatch | 149224 | 0.42% | 412 |
| `$37a62`–`$37bb3` | view matrix (`sub_037a62`) + position→cell (`sub_037afa`) | 63096 | 0.18% | 175 |
| `$2f4b8`–`$2faff` | odometer, 5-game-minute settlement, `$6740` control scaling (`$2f784`–`$2f82f` = 12920) | 31768 | 0.09% | 88 |
| `$1a706`–`$1a92f` | HUD writer **and the game clock tick** | 30228 | 0.09% | 83 |
| `$31486`–`$315e7` | frame-loop body itself | 20520 | 0.06% | 56 |
| `$32ee0`–`$32f1f` | HUD numeric readouts | 3952 | 0.01% | 10 |
| **Total** | | **298788** | **0.85%** | **825** |

Of the player sim: `sub_0344ac` mover 8208 cyc = 432/frame, `$34006`–`$34105` dispatch 24376 = 1283/frame,
`sub_0345c4` heading+lean 6004 = 316/frame, `sub_033f40` throttle→speed 5244 = 276/frame.

232.4 ms/frame (19 frames in the profile window); sim scope = **1.97 ms/frame ≈ 0.85%**. The
simulation is *not* a speed target — its relevance to P4 is only that it must be replicable (P3).

## 2. Role

One call per presented frame integrates the player: throttle → speed → position, control rate →
heading/bank/pitch, position → range/bearing → HUD, and a frame-countdown → **game clock in minutes**.
Nothing in the chain reads a VBL counter: every increment is a fixed per-frame step.

Inputs: mode `$6220`; vehicle control block `$54dc0 + $6220*$3e` (mode 13 ⇒ `$550e2`); control rates
`$6752/$6756/$675a/$675e/$6762` (written by the IKBD path — see `Controls`); fatigue `$efb0–$efbe`.
Outputs: position `$66e6/$66ea`, heading `$6742/$6294/$764a`, bank `$6746`, lean `$674e`, pitch
`$674a`, cell coords `$670a–$6710`, view matrix `$7662–$767a`, HUD `$6888/$66b8/$180f6–$1813a`,
clock `$eb8c`.

## 3. Call graph

```
frame loop  $31486 … $315de  (bra.w $31486)              [19 execs in profile]
├─ $31512 jsr $2f4b8   odometer $f968/$f96c + 5-game-minute settlement sub_02f51a → stamina $efb2
├─ $31518 jsr $2fa0a   ┐
├─ $3151e jsr $2f968   │ 0.00% in the walking profile (early-out at $2f96e/$2f978,
├─ $31524 jsr $2f726   ┘ $efb0=1500/$efb2=250); $2f968 holds the only in-loop blocking VBL waits
├─ $31570 jsr $33bca ──► sub_033bde   PLAYER SIM  (tst.w $40b6; bne → jsr $37626 instead)
│            ├─ $33bf8 jsr $3489a       range/bearing → $66e4, $6774
│            ├─ $33c1e..$33c4a bsr $34142/$341cc/$34256/$34106/$343ee/$34112/$34414/$3411e/$3443a
│            │        $34106 = `$6740 = $6752>>4`  (the slot that reaches heading, proven below)
│            ├─ $33c42 bsr $3467c / $33c46 bsr $346a2   jmp (a1) via tables $349de / $349ea
│            │        └─► sub_0345c4  heading $6742/$6294/$764a, lean $674e
│            │        └─► sub_03461a  bank $6746 (clamped by table $7250)
│            │        └─► sub_034660  pitch $674a, and $6740 → $7656
│            ├─ $33ca2/$33d18 bsr $344ac  ► jsr $2f784, jsr $2f7f0 ($6740 fatigue scale)
│            │                            ► $344d8 bsr $33f40 → speed $6772 (+ $764c if flying)
│            │                            ► $34504/$34508 POSITION INTEGRATOR
│            │                            ► $34514 bsr $3451a  world bounds (5000,46200) → $6288
│            ├─ $33c4e jsr $348ec       recompute $34936/$34938/$3493a from position
│            ├─ $33dc6 bsr $34006, $33dd2 bsr $33e7a, $33df2 bsr $346c8/$34708
│            └─ $33e34 bsr $31dee, $33e38 bsr $37a62 (view matrix), $33e3c bsr $37afa (pos→cell)
├─ $31582 jsr $50b6 ──► $1a706   HUD writer + GAME CLOCK (`addq.l #$1,$eb8c.l` @ $1a716)
├─ $31586 jsr $32ee0             HUD numerics $66b8/$66ba from cell $670a/$670c
├─ $3159c clr.w $7020            ← the VBL counter is ZEROED EVERY FRAME
└─ $315a4 jsr $5056              renderer (single call; see FrameLoop)
```
Callees outside the loop: `$4f8a` (clamp), `$4f7e`/`$5062`/`$5068`/`$506e` (indirect trig/range via
the jump table built at `$33ba4` into `$5050`), `$2e6fe` (clock → date fields).

## 4. Per-frame cost (no inner loops — 1 iteration/frame each)

There are **no hot loops in the simulation**: every block below is straight-line and executes exactly
once per presented frame. `sub_0344ac` integrator core, profile cycles then `÷19` = per-frame (each
address divides by 19 exactly except the two data-dependent `muls`):

```
0344dc 152 ( 8) lea.l $44a4.w,a0        trig table     | 0344f8 950 (50) muls.w d2,d0
0344e0 228 (12) move.w $6294.w,d0       heading        | 0344fa 988 (52) muls.w d2,d1
0344e4 152 ( 8) andi.w #$3fe,d0                        | 0344fc 114 ( 6) swap d0 / 0344fe 76 (4) swap d1
0344e8 304 (16) lea.l (a0,d0.w),a0                     | 034500  76 ( 4) ext.l d0 / 034502 76 (4) ext.l d1
0344ec 152 ( 8) move.w (a0),d0     sin(h) Q14          | 034504 456 (24) add.l d0,$66e6.w   X +=
0344ee 152 ( 8) lea.l $100(a0),a0                      | 034508 456 (24) add.l d1,$66ea.w   Y +=
0344f2 152 ( 8) move.w (a0),d1     cos(h) Q14          | 03450c 304 (16) move.l $66e6.w,d0
0344f4 228 (12) move.w $6772.w,d2  speed               | 034510 304 (16) move.l $66ea.w,d1
03451a 266 (14) cmp.l #$1388,d0  world box (5000,46200)| 034514 380 (18) bsr $3451a
034520 190 (10) ble.b $3453c  -> clr.w $6288           | 034518 304 (16) rts
```

Exact sums: `$344dc`–`$3451a` = **6270 cyc ⇒ 330/frame**; whole `sub_0344ac` (`$344ac`–`$34519`) =
8208 ⇒ **432/frame**. `sub_0345c4` (heading+bank, `$345c4`–`$34619`) = 6004 ⇒ **316/frame**, all 19
instructions at 19 execs (`$345c4 movem.l d0-d1,-(a7)` 456/24, `$345ea andi.w #$3fe,d0` 152/8,
`$3460c lsl.w #$6,d0` 342/18, `$34610 move.w d0,$674e.w` 266/14, `$34614 movem.l (a7)+` 532/28).
`sub_033f40` (throttle→speed) = 5244 ⇒ **276/frame**. `sub_033bde`'s own bucket `$33bde`–`$33e45` =
21508 ⇒ **1132/frame**; `$1a706` HUD+clock = 30228 ⇒ **1591/frame**.

**19 executions over 220.8 VBL ⇒ 11.6 VBL/frame ⇒ 4.30 fps.** `$33bde movem.l d0-d7/a0-a6,-(a7)` =
2432/128 = 19; `$3159c clr.w $7020.w` = 304/16 = 19; and *every* instruction from `$31542` to
`$315d8` is exactly 380 = 19 × `jsr (abs.l)`(20). One sim step per presented frame.

## 5. Variables

World geometry: `$66e0.w = 512` = position units per map cell; map centre = `0x6400` = 25600 (cell 50);
playable box from `$3451a`: `(5000, 46200)` exclusive.

| Addr | Size | Meaning | Evidence |
|---|---|---|---|
| `$66e6`,`$66ea` | L,L | player world **X**, **Y** in 1/512-cell units; `$66ee`/`$66f2` = copies saved at frame start (`033be6`,`033bec`) | `034504 add.l d0,$66e6.w`, `034508 add.l d1,$66ea.w`; watchpoint `D0=FFFFFFE9`, `D1=0` |
| `$6288` | W | cleared when X or Y leaves the world box `(5000,46200)` | `03451a`–`03453c` |
| `$66e0` | W | 512 = position units per map cell | `037b06 move.w $66e0.w,d7` / `037b0a divs.w d7,d0` |
| `$670a`,`$670c` / `$670e`,`$6710` | W×4 | X,Y ÷ 512 = integer cell (walk 48/50, stand 50/50) / the remainders | `037b0e`,`037b12`,`037b1a`,`037b1e` |
| `$6742` | W | **heading (yaw) master**, 10-bit 0..1022 | `0345f2`; live −50/frame |
| `$6294`,`$764a` | W,W | heading copies: compass (`01a760 andi #$3fe; mulu #$6c; divu #$400`) and renderer view matrix (`037a6a`) | `0345ee`, `0345f6` |
| `$66fe` | W | `$764c` saved at frame start; restore `01ba6c/01bc5c/01bca8 move.w $66fe.w,$764c.w` | `033bf2 move.w $764c.w,$66fe.w` |
| `$674e` | W | signed 10-bit **lean/tilt**, `clr.w` every frame then recomputed from `$6740`; drives the HUD horizon tilt | `033bfe clr.w $674e.w`; `034610`; HUD `01a78c divs.w #$c` → `$18108` |
| `$6746` | W | **bank** from the mouse-button axis, clamped `[−192,192]` by table `$7250+4*mode`; the angle whose sin/cos is `$7652/$7654` | `034656`; `034762` (per `Controls`) |
| `$674a` | W | **pitch**, true accumulator (not cleared) | `034674 move.w d0,$674a.w`; `03466e $6740→$7656` |
| `$6740` | W | this frame's applied control delta = `rate>>4`; 1/1024-turn units on the `$345c4`/`$3461a` paths | `03410c/034118/034124/034130/03413c`; measured `0xffcf` |
| `$6750` | W | **throttle**; `clr.w` @`033c02` then `+= $6740` @`0344bc` each frame ⇒ constant 90 because `$6740 = $6756>>4 = 90` | RAM 90 in all 3 snapshots |
| `$6752` | W | **facing/yaw rate** (the yoke axis that turns you) — the slot that reaches heading, via `$34106` selected by `$33(a0)=4` | turn `0xfcf8`=−776 → −776>>4 = −49 = `$6740` |
| `$6756` | W | **throttle-axis rate** = 1440 constant on foot (its input accumulator is never cleared on the walking path), via `$34112` selected by `$30(a0)=1` | RAM `0x05a0` in walk *and* turn; chain per `Controls` |
| `$6772` | W | **speed** fed to the integrator `= ($6750*$7654*4)>>16` (flying) or `= $6750` (ground) | `033f66`/`033fac`; `0344f4` |
| `$7652`,`$7654` | W,W | **sin/cos of bank `$6746`**, Q14 (`$7654=0x4000`=1.0), table `$44a4`/`$45a4` via `$34762` | `033f56`,`033f5a`; written `033fd0`/`033fd4` |
| `$764c` | W | **vertical/route accumulator**: `+= (($6750*$7652)>>16)>>1`, clamped `[−8000,+12000]`; only moves while banked. **= 2000 constant here**, and the minuend of the HUD distance | `033f6a`–`033f7a`; `033dc2 move.w d6,$66e2.w`, `d6 = $764c − $3493a` |
| `$66e2` | W | route distance **remaining** (HUD); `$6888` is its HUD copy | `033dc2`; `0336ea move.w $66e2.w,$6888.w` |
| `$66e4` | W | distance-travelled term `= $3493a`; `$66e2 + $66e4 = 2000` at all 5 walk samples | `033db8` |
| `$34936/8/a` | W×3 | range/bearing recomputed from position each frame | `sub_0348ec` `03490e/03491c/03492a` |
| `$6220` | W | mode/vehicle id = 13 (on foot) | `033c06`; block `$54dc0+13*$3e = $550e2`, flags `$550e4 = 0x0101` |
| `$6290` | W | **frames until next game minute** (countdown) | `01a70a dbra`; reload `01a73a` |
| `$753a[]`,`$f970` | W[],W | per-mode tick reload table (`[13]` = `$7554` = **16**) and the shift (`$f970` = **1**) ⇒ reload `16<<1 = 32` | `01a72e`, `01a732 asl.w d1,d0`; RAM `00 10` / `00 01` |
| `$eb8c` | **L** | **GAME CLOCK, minutes since campaign start** = 2219 ⇒ 36 h 59 m ⇒ day 2 **12:59** | `01a716 addq.l #$1,$eb8c.l` |
| `$de92–$dea0` | W×8 | clock broken into fields; `$de9a` = minute-of-day (779 = 12:59) | `sub_02e756`: `move.l $eb8c.l,d0; bsr $2e6fe; move.w d4,$de9a.l` |
| `$f974` | L | `$eb8c` at the last settlement; advances in steps of 5 game minutes | `02f51a`; RAM 2215→2220 |
| `$f968`,`$f96c` | L,W | odometer `Σ(speed*(table+1))` and frame count since settlement | `02f4f8`, `02f4fe`; cleared `02f54e/02f554` |
| `$efb2` | W | **stamina** 0..250, settled every 5 game minutes from mean speed | `02f5ac`; HUD `01a884 lsl #3; divu #$64` → `$180f6` |
| `$efb0`,`$efb6/8/c` | W×4 | `$efb0` = 1500 gates `sub_02f968`; `$efb6/$efb8/$efbc > 1000` ⇒ `$6740` scaled ×0.75/×0.5 | `02f972`; `02f794`, `02f7c2`, `02f802` |
| `$770c` | W | VBL counter, +1/VBL, free-running, never read by game logic | `0262d4 addq.w #$1,$770c.w`; measured +580 over 580 VBL |
| `$7020` | W | VBL counter **cleared every frame** at `$3159c`; only read by `sub_02f968`'s blocking waits | measured 5..13 (= VBLs since last frame) |
| `$773e` | W | +1 per sim frame while in motion — an exact frame counter in the moving snapshots; no absolute-address xref (register-relative access) | measured +49/+110/+44/+89 = exact frame counts |
| `$66b8`,`$66ba` → `$7790`,`$7794` | W×2 | HUD numerics `= (cellX>>1)−1` and `49−(cellY>>1)`, copied into the HUD record (`a6=$770e`) | `032ef0`, `032f00`, `01a8c8 move.w $66b8.w,$82(a6)` |

**Correction to `work/baseline.md`:** the readout logged as "speed 23" is `$66b8`, and `sub_032ee0`
derives it from the *map cell*, not the throttle (`032ee8 move.w $670a.w,d2; asr #1; subq #1;
032ef0 move.w d2,$66b8.w` ⇒ cellX 48 → 23). It fell 23→20 only because X fell; `$6750`/`$6772` stayed
90 throughout. [INFERENCE] `$66b8/$66ba` are a map grid reference (50×50 over the 100×100 cell map).
Heading has no per-frame save/restore — it is a pure accumulator. Units (per `Controls`, consistent
with the observed `andi.w #$3fe`): `$6740`/`$6750` are 1/1024-turn on the `$345c4`/`$3461a` paths, so
−50/frame = −17.6°/frame; `$764c` is a different space, clamped `[−8000,12000]` at `$33f6e`.

**Cadence.** Sim steps and presented frames are ~1:1 but not identical — the loop free-runs with no
VBL wait (FrameLoop), so a frame can present twice or be skipped: my windows gave 49 steps/49 flips
(walk 8 MHz) and 110/113 (walk 16 MHz); `Controls` measured 33 `$33bde` + 2 `$37626` against 31 flips
in 403 VBLs. **P3's k must come from `$770c`, not the flip count.** `$33bca` picks `sub_033bde` when
`$40b6 == 0`, else `sub_037626` (`033bca tst.w $40b6.w; 033bce bne.b $33bd6`).

## 6. Per-frame vs per-VBL — the decisive statement

**Every simulated quantity is a fixed per-FRAME step. Nothing is scaled by elapsed VBLs.**

* No read of `$7020` or `$770c` anywhere in `$31486–$315de`, `$33bca–$348ff`, `$1a706–$1a92f`,
  `$37a62–$37bb3`. `--xref 770c` returns only `$262d4` (VBL handler `addq`), `$2646a`, `$26476`,
  `$26a1a` — all inside interrupt handlers. `--xref 466` returns only `01a3b5 addi.w #$466,$1a60(a3)`
  (an immediate) ⇒ `$466` is not a variable. The integrator has no dt term: `muls.w d2,d0` with
  `d2 = $6772` (speed) only.
* `$7020` **cannot** be a dt source as shipped: `$3159c clr.w $7020.w` runs once per frame (304/16 =
  19 execs). Its only in-loop readers are the *blocking* waits in `sub_02f968` (`$2f998 clr.w $7020.w;
  $2f99c cmpi.w #$a,$7020.w; bcs`, and `$2f9c0/$2f9c4 (#$19)`) — a cold path, 0.00% of the walking
  profile, skipped because `$efb0 = 1500 ≠ 0` at `$2f972`.
* `$770c` is the only free-running VBL counter and is never read by game logic ⇒ **natural dt source
  for P3 option B.**
* The clock is per-frame too: `$1a716 addq.l #$1,$eb8c.l` fires when frame countdown `$6290` expires,
  and `$6290` is decremented by `dbra` once per call of `$1a706` = once per frame.

## 7. Measured rates, 8 MHz vs 16 MHz

`python3 /tmp/simtiming/rates4.py <snapshot> <mhz> 500 'pc = $34504' <tag>`; both ends captured
atomically by a `:file` VBL breakpoint (`m $66e0 32 / m $6740 64 / m $6880 16 / m $7640 16 /
m $7700 64 / m $eb88 16 / e VBL`); window length taken from the `$770c` delta in the same capture.

**Walking (`ingame_foot_walking`, throttle 90, heading 768):**

| | 8 MHz | 16 MHz | ratio |
|---|---:|---:|---:|
| window (`$770c`) | 580 VBL = 11.60 s | 580 VBL = 11.60 s | 1.00 |
| sim frames (`$773e`) | **49** | **110** | 2.24 |
| fps | 4.22 | 9.48 | 2.24 |
| VBL per frame | 11.84 | 5.27 | 0.45 |
| ΔX per frame | **−23** (1127/49) | **−23** (2530/110) | **1.00** |
| X per second | −97.16 u/s | −218.10 u/s | 2.24 |
| X per second in map cells | −0.190 | −0.426 | 2.24 |
| route distance remaining `$66e2` (→ HUD `$6888`) per second | −17.67 | −46.47 | 2.63 |
| game clock `$eb8c` | +1 min | +3 min | 3.0 |
| s per game minute | 11.6 (phase-limited: only 1 tick in window) | 3.87 | 0.33 |

Longer clean 8 MHz run (`N=1500`, 1580 VBL = 31.60 s): `$773e` +144 frames (4.56 fps), X −3312 =
**144 × −23 exactly**, clock +4 min ⇒ **7.90 s per game minute**. Dedicated tick count
(`ticks.py … 8 2000`, 2098 VBL = 42.0 s): `pc = $34504` hit 208×, `pc = $1a716` hit 6× ⇒
**34.7 frames and 6.99 s per game minute, fps 4.957**. Theory: reload `$7554`(16) `<< $f970`(1) = 32,
plus the expiring frame ⇒ **33 frames per game minute**.

**Banked turn (`ingame_foot_banked_turn`, yaw rate `$6752 = −776`):**

| | 8 MHz | 16 MHz | ratio |
|---|---:|---:|---:|
| window | 580 VBL = 11.60 s | 580 VBL = 11.60 s | 1.00 |
| sim frames (`$773e`) | 44 | 89 | 2.02 |
| fps | 3.79 | 7.67 | 2.02 |
| Δheading per frame | **−50** (44×−50 = −2200 ≡ −152 mod 1024 ✓) | **−50** (89×−50 = −4450 ≡ −354 ✓) | **1.00** |
| heading per second | −190 u/s = **−66.8°/s** | −384 u/s = **−135.1°/s** | 2.02 |
| full circle | 5.4 s | 2.7 s | |
| game clock ticks | 1 | 2 | 2.0 |

A 16 MHz machine (and any P4 speed-up) turns the world **2.0–2.25× faster** and runs the campaign
clock **~2.2× faster**. Per-VBL scaling would have left both identical, since both windows are
exactly 580 VBL.

## 8. Optimisation / decoupling opportunities

| # | Idea | Saving | Risk |
|---|---|---|---|
| 1 | **P3 option B is clean.** Replicate `$31486..$315a4` *k* times (k from a `$770c` delta), call the renderer `$5056` once. | n/a (enables P4) | Low. Sim is 0.85%/frame ⇒ *k*=2.2 costs +1.0% of a frame. |
| 2 | Use **`$770c`**, not `$7020`, as the dt source. `$7020` is zeroed at `$3159c` every frame and is also the wait counter for `sub_02f968`. | n/a | Low, but `$3159c clr.w $7020.w` must stay or `sub_02f968`'s waits break. |
| 3 | `sub_037afa` does **8 `divs.w d7`** with `d7 = $66e0 = 512` (a power of two) purely to split position/matrix into cell+remainder: `swap`+`andi #$1ff` is exact. | ~800 cyc/frame = 0.002% | Very low; only valid while `$66e0 == 512` (guard it). |
| 4 | The 2 `muls` in the integrator (102 cyc/frame = 0.00003%) could become a lookup, but speed is 0..255 and heading 0..1022 ⇒ table too large. No visual tradeoff is available anywhere in the sim: removing sim work changes gameplay, not pixels. | ~0 | — |
| 5 | **Blitter: nothing here is blitter-addressable** — all scalar 16/32-bit integer work, 1.97 ms/frame. Blitter effort belongs in the renderer (`$1dbbe`), not the sim. | — | — |
| 6 | **Watch-out for option B:** `sub_037a62` decays `$7646`/`$7648` with `divs.w $6794.w` (`$37ae4/$37ae8`) once per sim step. If that decay is meant per *rendered* frame it will decay *k*× faster under option B. [INFERENCE] — `$7646/$7648` were 0 / `0x00a3` and constant over 25 s of walking, so I could not observe the decay rate. | — | Medium |
| 7 | Also under option B: `$31582 jsr $50b6` (HUD + clock) and `$31512 jsr $2f4b8` (odometer + 5-minute fatigue settlement) are inside the replicable block, which is what makes the campaign clock and fatigue real-time-correct for free. `$2f504` compares `$eb8c − $f974 >= 5`, so it is already game-time driven. | — | Low |

## 9. Verification (raw output)

**(a) Position integrator — watchpoint on `$66e6` while walking.**
`h.debug("b ($66e6).l ! ($66e6).l :trace :once :file /tmp/simtiming/hit/pos.txt")`, file = `r`:
```
  $66e6 = $6051
1. CPU breakpoint condition(s) matched 1 times.
	( $66e6 ) . l ! ( $66e6 ) . l :once :trace :file /tmp/simtiming/hit/pos.txt
  D0 FFFFFFE9   D1 00000000   D2 0000005A   D3 00000328
  D4 0000FFBA   D5 FFFF0369   D6 0000E0C0   D7 00002EE0
  A0 000048A4   A1 000344AC   A2 00079F42   A3 0007CF38
SR=2311 T=00 S=1 M=0 X=1 N=0 Z=0 V=0 C=1 IM=3 STP=0
00034508 d3b8 66ea                add.l d1,$000066ea.w [00006400]
Next PC: 0003450c
```
Stopped between `$34504 add.l d0,$66e6.w` and `$34508`. `D2 = $005A = 90` = speed `$6772`,
`D0 = −23` = the X increment, `D1 = 0` = the Y increment, `A1 = $344AC` = caller.
Second/third hits: `$66e6 = $5ff5`, `$5f99` (−92 each = 4 frames × −23).

**(b) Heading integrator — 11 consecutive frames, banked turn.**
`h.debug("b pc = $34610 :trace :file /tmp/simtiming/hit/bank.txt")`, file = `m $6740 16`,`m $f980 8`:
```
00006740: ff cf 01 4e 00 00 00 00 00 00 00 00 00 00 ff ce   0000F980: 00 00 3e 7d 00 00 00 01
00006740: ff cf 01 1c …  ff cf 00 ea …  ff cf 00 b8 …  ff cf 00 86 …  ff cf 00 54 …  ff cf 00 22 …
00006740: ff cf 03 f0 …  ff cf 03 be …  ff cf 03 8c …  ff cf 03 5a …
```
`$6740 = −49` constant, `$f984 = 0`; `$6742` = 334, 284, 234, 184, 134, 84, 34, 1008, 958, 908, 858
⇒ **exactly −50 per frame** (−49, then `andi.w #$3fe` at `$345ea` forces even). `$674e = 0xffce` (−50)
both before and after `$34610` because `$33bfe clr.w $674e.w` resets it each frame:
`0 + (−49) → &3fe = 974 → lsl 6 = 0xF380 → asr 6 = 0xFFCE = −50` — the lean term is stateless.
Reset confirmed by `b ($674e).w ! ($674e).w :once :file` → `Next PC: 00033c06`, `A6 0000770E`,
`00006740: 00 00 01 e4 00 00 00 00 00 00 00 00 00 00 00 00` (`$674e = 0` right after `$33bfe`).

**(c) Game clock — watchpoint on `$eb8c.l`.**
`h.debug("b ($eb8c).l ! ($eb8c).l :trace :once :file /tmp/simtiming/hit/clk.txt")`:
```
  $eb8c = $8ab
  D0 01BB0003   D1 00000000   D2 000C00FB   D3 0000000C
  A4 0007C718   A5 0007BE42   A6 0000770E   A7 0000802A
Prefetch 33fc (MOVE) 0002 (OR) Chip latch 00000000
Next PC: 0001a724
0000EB88: 00 00 00 00 00 00 08 ab 00 00 08 70 00 ab 00 00
```
`A6 = $770E` ⇒ inside `$1a706`; `Next PC = $1a724` = two instructions past
`$1a716 addq.l #$1,$eb8c.l`. `$eb8c.l = 0x08ab = 2219` min = 36 h 59 m = **day 2, 12:59**, matching
the HUD clock in PLAN.md; `$eb8e` before the hit was 2218 (12:58).

**(d) Clock ticks counted against sim frames** (`ticks.py`, 8 MHz, `b pc = $34504` + `b pc = $1a716`):
```
ingame_foot_walking.sav @8MHz window 417756->419854 VBL = 42.0s
  bp counters {1: (4, 212), 2: (1, 7), 3: (1, 1)}
  sim frames (bp $34504) = 208 ; clock ticks (bp $1a716) = 6
  fps = 4.957 ; frames per game-minute = 34.67 ; s per game-minute = 6.99
```

**(e) Rate windows (raw)** — `python3 /tmp/simtiming/rates4.py <snapshot> <mhz> 500 'pc = $34504' <tag>`.
WALK8 verbatim:
```
### WALK8 ingame_foot_walking.sav @8MHz cond='pc = $34504'
    bp counters: {2: (12, 60), 1: (13, 61), 3: (1, 1)}
    VBL 417796->418377 (e VBL) ; $770c delta=580 => 11.60s ; sim-step hits=49 ; flips=49
    X $66e8: 24519 -> 23392 d=-1127 /s=-97.155     distRem $66e2: 1104 -> 899 d=-205
    heading $6742: 768 -> 768 d=+0   throttle $6750: 90 -> 90   speed $6772: 90 -> 90
    w773e $773e: 243 -> 292 d=+49    CLOCK $eb8c.l 2219->2220 d=1
```
Same format, key lines from the other three:
```
WALK16  bp {1:(26,138)} $770c=580 =>11.60s hits=113 flips=113 | X 23622->21092 d=-2530 /s=-218.103
        distRem 949->410 d=-539 | heading 768->768 d=+0 | throttle/speed 90->90 | $773e 282->392 d=+110
        CLOCK $eb8c.l 2220->2223 d=3
TURN8   bp {1:(12,54)}  $770c=580 =>11.60s hits=43  flips=43  | X 23336->23330 d=-6, Y 25449->25490 d=+41
        heading $6742 134->1006 d=-152 | bank4e 65486->65486 d=+0 | $6756 1440->1440 | $773e 350->394 d=+44
        CLOCK 2222->2223 d=1
TURN16  bp {1:(24,110)} $770c=580 =>11.60s hits=87  flips=87  | heading $6742 482->128 d=-354
        $773e 384->473 d=+89 | CLOCK 2223->2225 d=2
```
Frame counts in §7 are the **`$773e` deltas (49 / 110 / 44 / 89)**, not the `pc = $34504` breakpoint
counters (49 / 113 / 43 / 87): that breakpoint is armed before capture A and cleared after capture B,
so its window is a few frames wider than the atomically-captured memory window. `$773e` is corroborated
exactly by the state itself — `1127 = 49×23`, `2530 = 110×23`, `44×(−50) = −2200 ≡ −152 (mod 1024)`,
`89×(−50) = −4450 ≡ −354 (mod 1024)` — four independent exact matches.
A 31.62 s / 16 MHz walk run was **discarded**: `$66e2` fell 949 → 50, i.e. the player arrived at the
objective mid-window (`$33c86 subi.w #$32,d0; bmi $33caa`), changing mode and the tick reload.

**(f) `$770c` is +1/VBL** — RAM dumps 6.4 s apart: `54259, 54580, 54900, 55220, 55541` for VBL
deltas `321, 320, 320, 321`. **`$7020` is VBLs-since-last-frame** — dumps `13, 6, 12, 11, 5`
(frame = 11.4–11.9 VBL), consistent with `clr.w $7020` at `$3159c`.
