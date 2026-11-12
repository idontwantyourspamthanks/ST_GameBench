# Input pipeline: IKBD → steering (Midwinter 2, HAGA HD build)

Addresses = offsets in `work/dumps/ram_ingame_lobos.bin`. Disassembly: `python3 tools/m68dis.py
work/dumps/ram_ingame_lobos.bin <addr> [--end <e>] [--xref <a>] [--callers <a>]`. Dynamic evidence:
`work/snapshots/ingame_foot_walking.sav` on Hatari 2.6.1 (§9; full logs `/tmp/controls/{raw1,raw4}.txt`,
`add_X-60.txt`, `ramp6a.txt`, `step6a.txt`, `{D,E,F}.txt`). Snapshot: `$6220 = 13` (control type = on
foot), `$700a = 2` (input context = in game), `$eb76/$eb78/$eb7a = 0/0/$ffff` (mouse mode).
Hatari gotchas: the clear command is **`b all`** — the `bc all` in `tools/mw2harness.py` is not a command
and fails silently; `b … :trace :<n>` fires every n-th hit; `w <addr> <bytes>` writes memory; never
re-arm a `:once :file` breakpoint from its own commands file (Hatari re-fires at the same PC and stalls).

## 1. Scope and cost (`work/prof/walking.txt`, 35 321 256 cycles)

| Region | Role | cycles |
|---|---|---:|
| `$26882–$26a5e` | IKBD/ACIA IRQ (vector `$118`) | **0** — no input during the profile run; runs only on a packet |
| `$26a6c–$26dc4` | packet finishers, mode dispatch, keyboard poll | 15 840 = 0.045 % |
| `$33bca–$33e46` | per-frame control step | 22 800 = 0.065 % |
| `$34106–$348a0` | clamp/deadzone, rate handlers, apply handlers | 77 216 = 0.219 % |
| **total** | | **≈115 900 = 0.33 %** |

Per presented frame: `$33bde` 2432 ÷ 22 ≈ **110 cycles**; `$347f2`, `$3481e`, `$34142`, `$341cc`,
`$34256`, `$33f40` = 228 each; `$344ac` 380, `$345c4`/`$3461a` 456. Per VBL: `$26c1e` 3520 ÷ 250 ≈ 14
cycles/call and `$26b58` the same — both are `tst.w $eb78/$eb76 ; beq ; rts` (mouse mode).
**No fps win is available here.** The only per-VBL work is the keyboard ramp (§6), which is also the
term that makes steering fps-dependent.

## 2. Pipeline

```
ACIA $fffc02 ─► IRQ $26882 ─► packet state machine ($75a0 state, $759e bytes left)
  mouse $f8-$fb ─► $75a2 hdr, $75a4, $75a3 ─► $26a6c ─► dispatch on $700a (table $26a60)
      ├─ 0/1 UI pointer: $26b18 → $6fae (X 8..310), $6fb2 (Y 8..195), clicks $62e6/$62e8/$62ea/$62ec
      └─ 2   in game:    $26b0c → $6fb6 += dx<<16 ; $6fba += -dy<<16
  keys ─► key-down table $7686[scancode] = $ff/0 ; last scancode $7684
  joystick $ff ─► $26b58 (ramps $75b2..$75be — DEAD) → buttons only
VBL $26298 ─$262c8─► $26b58 (re-read joystick) ─$262cc─► $26c1e (keyboard poll, 50 Hz)
                                    └─► injects d0/d1 as SYNTHETIC MOUSE DELTAS at $26a8e
once per presented frame: $33bca ─► $33bde
  ─► $347f2/$3481e clamp+deadzone → $6766 (X), $6768 (Y)
  ─► $34142/$341cc/$34256 per-type rate → $6752, $6756, $675a
  ─► $34106/$34112/$3411e  $6740 = rate >> 4
  ─► $343ee/$34414/$3443a per-type apply → facing $6294/$6742/$764a · throttle $6750/$6772 · bank $6746
  ─► $3467c/$346a2  $7652/$7654 = sin/cos(bank) ; then $33d4c… type/flag heading fixups
```

## 3. IKBD handler `$26882` (vector `$118`, installed by `move.l #$26882,$118.w` at `$26602`)

```
26882: movem.l d0-d3/a0,-(a7) ; move.w #$2700,sr ; btst #7,$fffc00 ; beq $26a44 (exit)
26896: move.w $75a0.w,d1 ; bne $2692e  ; in packet → lea $2693e,a0 ; movea.l (a0,d1*4) ; jmp (a0)
268a0: move.b $fffc02.l,d0             ; header byte
26a44: movem.l (a7)+,d0-d3/a0 ; bclr #6,$fffa11 ; rte
```

| header | state `$75a0` | `$759e` | buffer | continuation | meaning |
|---|---|---|---|---|---|
| `< $f6` | – | – | – | `$269fe` | scancode (bit 7 = release) |
| `$f8–$fb` | 1 | 2 | `$75a2` hdr, then `$75a4`, `$75a3` | `$26956` → `bsr $26a6c` | mouse relative record; hdr bits 1:0 = right:left |
| `$fd` | 2 | 2 | `$75a8`,`$75aa`,`$75a9` | `$2697c` — stores, **no finisher** | unused |
| `$fe` | 3 | 1 | `$75a8`,`$75a9` | `$2699e` — stores, **no finisher** | unused |
| `$ff` | 4 | 1 | `$75a8`,`$75a9` | `$269c0` → `jsr $26b58` | joystick byte (bits 3/2/0/1) |
| else (`$f6,$f7,$fc`) | 5 | 7 | – | `$269e8` — reads and **discards** | time-of-day record |

Store order (`$26956`): `move.b d0,(a0,d1.w)` with `d1 = $759e` = 2 then 1 ⇒ **first data byte →
`$75a4`, second → `$75a3`**. Scancode path `$269fe`, press (bit 7 clear):
`$7684 = sc ; $7686[sc] = $ff ; $75ac = $ffff ; $770a = sc ; $770c = 0` (`$770c` is the VBL auto-repeat
counter: VBL increments it at `$262d4`, a key press zeroes it). Release (`$26a20`): `jmp $3ea.w` — a
low-memory hook that swallows the releases of `$65` (keypad `/`) and `$66` (keypad `*`), the HAGA
savestate keys, else re-enters at `$26a28`: `$7686[sc&$7f] = 0`; if `sc == $770a` → `$770a = 0`,
`$7708 = sc`; if `$75ac == 0` → `$7684 = 0`. Scancode identities come from the game's own
scancode→ASCII table `$662e` (§9.4). `$26676` swaps `$118` to the drain-only handler `$2668e` (input
off; caller `$24ec8`); `$2665e` restores `$26882` (caller `$24f48`).

## 4. Axis mapping (proofs in §9.3)

`$26a6c`: `d0 = (int8)$75a3 << 16`, `d1 = (int8)$75a4 << 16`; `$26b0c`: `add.l d1,$6fb6 ; neg.l d0 ;
add.l d0,$6fba`. The UI handler `$26b18` uses the same `d0`/`d1` but feeds `d0` into `$6fb2` clamped
`8..$c3` (195 = screen rows) and `d1` into `$6fae` clamped `8..$136` (310 = screen columns), so `d0` is
Y and `d1` is X. ⇒ **`$75a4` = delta-X = 1st data byte → `$6fb6` = Σ deltaX** (right positive);
**`$75a3` = delta-Y = 2nd byte → `$6fba` = −Σ deltaY** (up positive). Both are 16.16 longs; the
per-frame consumer reads, clamps and writes back only the **high word**.

## 5. Control mode (M/J/K) and input context

`$2fd60`: `jsr $4f66` (→ `$26e6c`, ASCII of the last scancode via `$662e`) until the key is M/J/K:
```
2fd86: d1=$ff d2=0 d3=0    ; 'M' $4d → $eb7a=$ff $eb76=0    $eb78=0    mouse
2fd92: d1=0 d2=$ff         ; 'J' $4a → $eb7a=0    $eb76=$ff  $eb78=0    joystick
2fd9c: d2=0 d3=$ff         ; 'K' $4b → $eb7a=0    $eb76=0    $eb78=$ff  keyboard
2fda6: $eb7a=d1 ; $eb76=d2 ; $eb78=d3   ; exactly one is $ffff
2fdb8: jsr $4f30 (→$2a474 block copy) ; jsr $4f36 (→$26e98 flip) ; $769a=0 ; $6870=0
```
Snapshot: `0000EB76: 00 00 00 00 ff ff`. **There is no mode jump table** — the flags are pure gates:
`$eb7a` gates `$26a6c` and the UI waits `$26ab0`/`$26e00`/`$270ba`; `$eb76` gates `$26b58` and the
map-select consumer `$1ab70`; `$eb78` gates `$26c1e` and the key waits `$2bd8a`/`$2ce88`. `$700a` is
orthogonal (input *context*): table `$26a60` = `[$26b18, $26b18, $26b0c]`, 2 = in game.

## 6. Keyboard path `$26c1e` — from the VBL handler (`$262cc`), 50 Hz

```
26c1e: tst.w $eb78 ; beq rts   ; 26c2c: tst.w $759e ; bne rts (never mid-packet)
26c38: if $7686[$39] (Space) → $6872 = 1                       ; map "select" event
26c46: d2 = 0 ; if $7686[$33](',') | $7686[$4b](Left)  → d2 |= 2
                elif $7686[$34]('.') | $7686[$4d](Right) → d2 |= 1   ; synthetic mouse buttons
26c64: d0 = 0 ; d1 = 0 ; the FIRST held direction key ramps a 16.16 velocity, then
       bra $26dc0 → jmp $26a8e, i.e. injected through the *mouse* dispatch
```

| key | d0 → `$6fba` (−Σ Y = throttle on foot) | d1 → `$6fb6` (Σ X = turn on foot) |
|---|---|---|
| KP7 `$67` | `$75c8 -= $4000` | `$75cc -= $4000` |
| KP8 `$68` | `$75d0 -= $4000` | – |
| KP9 `$69` | `$75d4 -= $4000` | `$75d8 += $4000` |
| KP4 `$6a` | – | `$75dc -= $4000` |
| KP6 `$6c` | – | `$75e0 += $4000` |
| KP1 `$6d` | `$75e4 += $4000` | `$75e8 -= $4000` |
| KP2 `$6e` | `$75ec += $4000` | – |
| KP3 `$6f` | `$75f0 += $4000` | `$75f4 += $4000` |
| released | `= $ffff0000` (−1.0) or `$10000` (+1.0), **never 0** | same |

A held key therefore *accelerates*: velocity starts at ±1.0 and grows ±0.25 **per VBL**, and the
accumulator integrates that again ⇒ quadratic response whose size depends on how many VBLs fall inside
one rendered frame (9–16 measured). Only the first held key in that order is processed per VBL.
Measured end to end in §9.6. Cost of one held-key VBL: `tst.b` 12, `beq` 10, `move.l $75dc.w,d1` 12,
`subi.l #$4000,d1` 8, `move.l d1,$75dc.w` 12, `bra` 10, dispatch `$26a8e` (`move.w d2,-(a7)` 8, `lea` 8,
`move.w $700a,d2` 12, `add.w`×2 8, `movea.l (a0,d2)` 14, `jsr (a0)` 12), `$26b0c` 12+8+12+16, `rts` 16
≈ **150 cycles/VBL** = 0.09 % of an 8 MHz frame.

## 7. Joystick path `$26b58` — direction data is dead code

From the `$ff` packet (`$269de`) and from the VBL (`$262c8`, re-read 50×/s):
```
26b58: tst.w $eb76 ; beq rts
26b6a: d2 = $75a9 ; bit3 → $75b2 += $4000 else $10000 ; bit2 → $75ba -= $4000 else $ffff0000
                  bit0 → $75b6 -= $4000 else $ffff0000 ; bit1 → $75be += $4000 else $10000
26be6: d2 = $75a2 & 3 → $6872 ; keys $33/$4b, $34/$4b → d2 ; bra $26a8e  WITH d0 = d1 = 0
```
`d0`/`d1` are zeroed at `$26b66`/`$26b68` and never reloaded, so only the button word survives;
`--xref` and a byte scan of `$4000–$3E000` for `75b2/75b6/75ba/75be` find **no readers** outside
`$26b58`. `$fd`/`$fe` packets are stored and dropped. The game never sends an IKBD command: the sender
`$26dc6`→`$26dd0`→`$26de2` (the only writer of `$fffc02`) has no caller — a scan for the absolute
targets `00026dc6/00026dd0/00026de2` over `$4000–$3E000` returns nothing, and all ten `$fffc02`
references are reads. [INFERENCE] joystick steering never worked in this build; P5 must implement it
(or repair `$26c18` to load `d0/d1` from the ramps), not tune it.

## 8. Per-frame consumer — clamp, deadzone, rate, apply

### 8.1 Driver
`$33bca` (callers `$31570` = the in-game frame routine, `$3243c`, `$325b2`):
`tst.w $40b6 ; bne → jsr $37626 ; else bsr $33bde`. Measured (§9.1): 33 hits of `$33bde` and 2 of
`$37626` against 31 flips in 403 VBLs ⇒ **once per presented frame**, while device ramps run at 50 Hz.
`$33bde`, with `a0 = $54dc0 + $6220*$3e` (per-type control block, §8.5):
```
33bfe: clr.w $674e ; clr.w $6750 ; $6776 = $2(a0) (flags)
33c1e: bsr $34142  ; $6fb6 (Σ X) → $6766 → rate $6752  (selector $34(a0), scale $35(a0))
33c22: bsr $341cc  ; $6fba (−Σ Y) → $6768 → rate $6756 (selector $31(a0), scale $32(a0))
33c26: bsr $34256  ; buttons $6fbe → $675a/$675c       (selector $37(a0), scale $38(a0))
33c2a/33c2e: bsr $34106 ($6740 = $6752>>4) ; bsr $343ee (apply, sel $33(a0) → $3499a; type 13 → $345c4)
33c32/33c36: bsr $34112 ($6740 = $6756>>4) ; bsr $34414 (apply, sel $30(a0); type 13 → $344ac)
33c3a/33c3e: bsr $3411e ($6740 = $675a>>4) ; bsr $3443a (apply, sel $36(a0); type 13 → $3461a)
33c42/33c46: bsr $3467c (coeffs, sel $3c(a0) → $349de; type 13 → $34762 = sin/cos of $6746)
             bsr $346a2 (view vector, sel $3d(a0) → $349ea; type 13 → $34708)
33c4a: bsr $33e46 ; jsr $348ec ; then type $f/$11/$10 special cases ($33c60/$33cc2/$33d26), else
       flag-driven $33d4c (bits 0/4/2/6 of $2(a0)) → heading fixups, $34006, $31dee, $37a62, $37afa
```

### 8.2 Clamp + deadzone — **this is the yoke** (`$347f2` X axis, `$3481e` Y axis)
```
347f2: d0 = (int16)$6fb6 ; d0 = clamp(d0, $14(a0)..$16(a0)) ; move.w d0,$6fb6  ← CLAMP WRITTEN BACK
34810: d1 = $12(a0) ; bsr $3484a ; $6766 = d0
3484a: d2 = sign(d0) ; d0 = |d0| − d1 ; if d0 < 0 → 0 ; d0 = d0·d2 ; rts       ← deadzone
3481e: same for $6fba, clamp $6(a0)/$8(a0), deadzone $4(a0) → $6768
```
Nothing clears `$6fb6`/`$6fba` on this path: the `clr.l` sites are `$310dc` (needs `$40b8 != 0` and
`not.w $40b6 == 0`), `$376ec` (inside `$37626`, only when `$12(a5) != 0` and the type is not 5/11/21)
and the full reset `$31776` (via trampoline `$4fae`). `$40b6 = 0` at every sampled step, so **the
accumulator persists indefinitely between input bursts**: it *is* the stored yoke position, the clamp is
its travel limit, the deadzone its centring band. Measured: byte-identical for 52–72 consecutive control
steps (≈6 s) with no input (`/tmp/controls/{D,E,F}.txt`), and still turning 10 s after a key release (§9.6).

### 8.3 Rate handlers (selector byte per type; tables `$3494a` X / `$3495a` Y / `$3496a` buttons)
| sel | X axis `$6766` → `$6752` | Y axis `$6768` → `$6756` | semantics |
|---|---|---|---|
| 0 | `$3166a` | `$3166a` | axis unused |
| 1 | `$34172`: `$6752 = ($6766 − $676a)·scale`; `$676a = $6766` | `$341fc` (same, `$676c`) | **derivative**: rate ∝ *change* of input |
| 2 | `$34188`: `$6752 = clamp($6766·scale, $18(a0)<<4 .. $1a(a0)<<4)` | `$34212`: `clamp($6768·scale, $a(a0)<<4 .. $c(a0)<<4)` | **direct**: rate ∝ input |
| 3 | `$341a0`: `$6754 = clamp($6766·scale, $1c<<4,$1e<<4)`; `$6752 = clamp($6752+$6754, $18<<4,$1a<<4)` | `$3422a` (same, `$e/$10`) | direct + integrator |

`scale` = byte `$35(a0)`/`$32(a0)`, sign-extended (`move.b …,d1 ; ext.w d1`). Clamp helper `$3485e`:
`d6 <<= 4; if d0 ≤ d6 → d0 = d6; else d7 <<= 4; if d0 ≥ d7 → d0 = d7` (table limits are stored ÷16).
Buttons `$34282`: `d0 = 0`; `$10` if any button; `$f0` if bit 1 (right);
`$675a = clamp(d0·$38(a0), $20(a0)<<4, $22(a0)<<4)`; `$342a8` also adds `$675c`.

### 8.4 Apply handlers (table `$3499a` = `[$3166a, $344ac, $34542, $34586, $345c4, $3461a, $34660, …]`)
| sel | routine | effect |
|---|---|---|
| 1 | `$344ac` | `$6740` scaled by `$2f784`/`$2f7f0` (×3/4 or ×1/2 when `$efb6`/`$efbc`/`$efbe` > 1000), `$6750 += $6740`; then `$33f40`: flags bit0/bit6 → `$764c = clamp($764c + ((($6750·$7652)>>16)>>1), −8000, 12000)` **and** `$6772 = ($6750·$7654·4)>>16`; else `$6772 = $6750` (types 1–3: `·($688e+8)>>4`). Then position `$66e6 += ($6772·sin)>>16`, `$66ea += ($6772·cos)>>16`, `sin/cos = $44a4[$6294&$3fe]`/`$45a4[…]` |
| 2 | `$34542` | view vector from `$6294 + $100`, scaled by `$6740` |
| 3 | `$34586` | type `$11`: `$7680 = clamp($7680+$6740, −100, −10)`; else `$764c = clamp($764c+$6740, −8000, 12000)` |
| 4 | `$345c4` | `$6294 = $6742 = $764a = ($6742 + $f984 + $6740) & $3fe` (`$f984` = 0), and `$674e = sext10($674e + $f984 + $6740)` = the view tilt that banks the horizon (`$674e` is `clr.w`'d every frame at `$33bfe`, so it is stateless) |
| 5 | `$3461a` | `$6746 = sext10($6746 + $6740)`, clamped to `$7250[type*4]..$7252[type*4]` = `[−192,+192]` for all 22 types **unless** flags bit0/bit6 (on foot: unclamped) |
| 6 | `$34660` | `$674a = ($674a + $6740) & $3fe`; `$7656 = $6740` (`$674a` is *not* cleared each frame — a true accumulator) |

Coefficients (`$3467c`, table `$349de` = `[$346c8, $34762, $34722, $34748, $347be, $34708]`): type 13 →
`$34762`: `$7652 = $44a4[$6746 & $3fe]`, `$7654 = $45a4[$6746 & $3fe]` = **(sin, cos) of the bank angle
`$6746`**, Q14 (`$4000` = 1.0), copied to `$7642/$7644`. Net on-foot mapping: **mouse X / KP4-KP6 →
facing** (`$6294`,`$6742`,`$764a`, tilt `$674e`); **mouse Y / KP8-KP2 → throttle** (`$6750` → speed
`$6772`, and heading `$764c` only via `sin(bank)`); **mouse buttons / `,` `.` Left Right → bank
`$6746`**, which splits the throttle into heading and speed. Angles are 10-bit (`& $3fe`, 1024 = full
circle) so `$6740 = −50` is −17.6°/frame; `$764c` lives in another space, clamped [−8000, 12000] at `$33f6e`.

### 8.5 Per-type control block `$54dc0 + $6220*$3e` (62 bytes; 22 types 0–21; type 13 = `$550e6`)
| off | meaning — type 13 value |
|---|---|
| `$02` | flags — `$0021` (bit0 = heading/speed split; bits 2/4/6 tested at `$33d4c`) |
| `$04`, `$06/$08`, `$0a/$0c` | Y deadzone **100**, clamp **−200/1200**, `$6756` limits (×16) **−200/944** |
| `$12`, `$14/$16`, `$18/$1a` | X deadzone **150**, clamp **−250/250**, `$6752` limits (×16) **−80/80** |
| `$20/$22`, `$24/$26` | button rate limits (×16) −300/300, 0/0 |
| `$30`, `$31/$32` | Y apply sel **1** (`$344ac`), Y rate sel **2** (direct), scale **$10** |
| `$33`, `$34/$35` | X apply sel **4** (`$345c4`), X rate sel **2** (direct), scale **8** |
| `$36/$37/$38` | bank apply sel 5, button rate sel 2, button scale $10 |
| `$39/$3c/$3d` | further apply/coeff selectors 5 / 1 / 1 |

Types **15 and 17** are the only ones with rate selector **1** (derivative) and negative scale `$f8`
(−8); all others use selector 2 (direct). Type 16 uses apply sels 3/1 and scales `$0a`/8. Types 5, 11,
21 are excluded from the `$37626` accumulator clear; types `$f`, `$10`, `$11` have their own branches in
`$33bde`; type `$14` halves `$6750` when `$764c < 0`. [INFERENCE] the yoke feel comes from the
persistent accumulator plus the 50 Hz ramp (§6, §8.2), not from the derivative handler.

## 9. Verification (raw Hatari output)

### 9.1 Cadence: control step = once per presented frame
```
$770c 54470 -> 54873 = 403 VBLs in the window
$33bde hits = 33   $37626 hits = 2   flips = 31
```
`hatari-debug b pc = $33bde :trace :file f_cnt.txt`, same for `$37626`, plus
`b ($ff8201).b ! ($ff8201).b :trace`. `$770c` = the VBL counter (`$262d4`).

### 9.2 Whole chain, no input, consecutive control steps (`b pc = $33c26 :trace :file …`)
```
> m $6fb6 12
00006FB6: ff e2 00 00 00 be 00 00 00 00 00 02   ; $6fb6=-30<<16 $6fba=+190<<16 $6fbe=0 $6fc0=2
> m $6740 52
00006740: 00 00 03 00 00 00 00 00 00 00 00 00 00 00 00 00   ; $6740=0 $6742=$300 $6746=0 $674e=0
00006750: 00 00 00 00 00 00 05 a0 00 00 00 00 00 00 00 00   ; $6750=0 $6752=0 $6756=$5a0=1440
00006760: 00 00 00 00 00 00 00 00 00 5a 00 00 00 00 00 00   ; $6766=0 $6768=$5a=90 $676a=0 $676c=0
00006770: 00 00 00 5a                                       ; $6772=90 (speed)
> m $7642 20
00007642: 00 00 40 00 00 00 00 a3 03 00 07 d0 00 a0 00 80   ; $7642=0 $7644=$4000 $764a=$300 $764c=$7d0
00007652: 00 00 40 00                                       ; sin(bank)=0 cos(bank)=$4000
> m $6294 4
00006294: 03 00 00 00        ; facing $300     > m $40b6 4 → 00 00 00 00 (→ $33bde branch)
```
Against §8: `$6fba` hi 190 → clamp[−200,1200] → 190; deadzone `$4(a0)`=100 → `$6768 = 90` ✓; scale
`$32(a0)`=$10 → `$6756 = 1440 = $5a0` ✓; `$6740 = 1440>>4 = 90` → `$6750 = 90` ✓ →
`$6772 = (90·$4000·4)>>16 = 90` ✓. `$6fb6` hi −30 with deadzone 150 → `$6766 = 0` ✓ → `$6752 = 0` ✓;
`sin(bank)=0` → `$764c` unchanged ✓. **Bit-identical in the next step and 10 further steps.**

### 9.3 Registers at the accumulator write, and per-axis packets
`hatari-debug b pc = $26b16 :trace :file f_add.txt` — `$26b16` is the `rts` of `$26b0c`, so D0/D1 are
the values just added. Two consecutive hits during one `rel(-60,0)` burst (`/tmp/controls/add_X-60.txt`):
```
1. CPU breakpoint condition(s) matched 1 times.   pc = $26b16
> r
  D0 00000000   D1 FFF90000   D2 00000008   D3 00031DDD
  A0 00026B0C   A1 0007BBDA   A2 00065172   A3 FFFF7777
SR=2700 T=00 S=1 M=0 X=0 N=0 Z=0 V=0 C=0 IM=7 STP=0
00026b16 4e75    rts  == $00026aa4          ; return addr = the jsr (a0) of the $700a dispatch
> m $75a2 4
000075A2: f8 00 f9 00                        ; hdr $f8 (buttons 0), $75a3=$00 (dY), $75a4=$f9 (dX=-7)
> m $6fb6 8
00006FB6: ff db 00 00 00 be 00 00            ; $6fb6 = -37, $6fba = 190
… matched 2 times.  D0 00000000  D1 FFF80000 ; dX = -8 ; 000075A2: f8 00 f8 00
00006FB6: ff d3 00 00 00 be 00 00            ; $6fb6 = -45 = -37 + (-8) ✓ ; $6fba unchanged (D0=0) ✓
```
`A0 = $26b0c`, `SR = $2700` (level-7 IRQ) ⇒ the real in-game path, and D1 (= `$75a4` = 1st data byte =
delta-X) is what lands in `$6fb6`. Separate pure bursts (`b pc = $26970 :trace :file …` → `m $75a2 4`):
```
X(-100,0): f8 00 f8 00  f8 00 f7 00 …    X(+100,0): f8 00 07 00  f8 00 08 00 …
Y(0,-100): f8 f8 00 00  f8 f7 00 00 …    Y(0,+100): f8 08 00 00 …
```
X bursts move `$6fb6` only (`ff e7 → ff d7 → ff b5`, ≈ −50 counts per 100 host px), Y bursts move
`$6fba` only (`00 c1 → 00 d2 → 00 f4` up, `00 f4 → 00 c4` down, ≈ ±50) — signs match §4 exactly.

### 9.4 Scancode→ASCII table `$662e` (dump of the running image)
```
0x00-0x7f: ..1234567890-=..QWERTYUIOP[]..ASDFGHJKL:@`.#ZXCVBNM,./... ................-...+.................\..()/*7894561230...............
$33 ','  $34 '.'  $39 ' '  $4a '-'  $4e '+'  $65 '/'  $66 '*'  $67 '7' $68 '8' $69 '9' $6a '4' $6b '5'
$6c '6'  $6d '1'  $6e '2'  $6f '3'  $70 '0'  $71 '.'
```

### 9.5 X-axis burst drives facing and view tilt (cumulative X = −500 host px)
```
00006FB6: ff 06 00 00 00 be 00 00 …   ; $6fb6 = -250 = the type-13 clamp $14(a0) = $ff06
00006750: 00 00 fc e0 00 00 05 a0 …   ; $6752 = $fce0 = -800 = (-100)·8
00006760: … 00 00 ff 9c 00 5a …       ; $6766 = $ff9c = -100 = -250 + 150 (deadzone)
00006294: 01 cc 00 00                 ; facing $1cc (was $300)
00007642: 00 00 40 00 ff a2 00 85 01 cc 07 d0 …  ; $674e = $ffa2 = -94 (tilt), $764a = $1cc
```
`$6766 = −100` → ×8 → `$6752 = −800` → `>>4` → `$6740 = −50`/frame → `$6294/$6742` walked
`$300 → $1cc` (−308 over 6 frames) as `$345c4` prescribes, tilt `$674e` following: the "hard mouse-left
banks the view and changes the heading arrow" of `work/baseline.md`.

### 9.6 Keyboard mode forced on: the 50 Hz ramp, and the rate that survives release
```
> w $eb76 0 0 255 255 0 0
Wrote 6 'b' values starting from 0xeb76.
> m $eb76 6
0000EB76: 00 00 ff ff 00 00     ; joystick off, keyboard ON, mouse off
> m $75c8 48                    ; all 12 ramps at the "released" values §6 predicts ($75dc = $ffff0000 = -1.0)
000075D8: 00 01 00 00 ff ff 00 00 00 01 00 00 00 01 00 00
```
Key "held" by writing the key-down byte directly (`w $76f0 255` = `$7686+$6a`, keypad 4 = left — exactly
what the IRQ does at `$26a0a`), sampled every VBL with `b pc = $26dc0 :trace :file …` (140 samples,
`/tmp/controls/ramp6a.txt`):
```
  VBL  $75dc(ramp)  $6fb6(accX)  Δ/VBL
54439     -1.00       -30.00     +0.00   ; not held: no motion
54440     -1.25       -30.00     +0.00   ; first VBL with $76f0 = $ff
54441     -1.50       -31.25     -1.25   ; accumulator integrates the previous VBL's ramp
54443     -2.00       -34.50     -1.75
54455     -5.00       -75.00     -4.75
54475    -10.00      -222.50     -9.75
54485    -12.50      -249.75    +71.75   ; control step clamped the hi word to -250 = $14(a0)
54494    -14.75      -371.25    -14.50
54495     -1.00      -386.00    -14.75   ; RELEASED: ramp snaps to -1.0, NOT 0
54499     -1.00      -250.00   +136.00   ; next control step clamps to -250 …
54559     -1.00      -250.00     +0.00   ; … and it stays: the turn never stops
```
The ramp steps by exactly `$4000` (0.25) per VBL; the breakpoint at `$26dc0` sits after the ramp update
and before the `jsr (a0)` that adds it, hence the one-VBL lag; the clamp write-back at `$3480c` replaces
only the high word (`$FEB2C000` → `$FF06C000` = −249.75). Control-step view of the same run
(`b pc = $33c26`, key released after ~2 s ≈ 10 steps; `/tmp/controls/step6a.txt`):
```
  VBL  accX  accY  $6752  $6756  $6766  $6768  $6772  $6742=$6294
54679  -250   190   -800   1440   -100     90     90      974
54722  -250   190   -800   1440   -100     90     90      824   ← key still held
54846  -250   190   -800   1440   -100     90     90      324   ← key long released
54901  -250   190   -800   1440   -100     90     90       74      still turning -50/frame
```
`$6766 = −250+150` (deadzone `$12(a0)`), `$6752 = −100×8` (scale `$35(a0)`), facing steps −50/frame =
`$6752>>4`. Step spacing 9–16 VBLs ⇒ once per presented frame (§9.1).

## 10. Where a direct-control patch hooks

The chain is 0.33 % of a frame, so nothing here buys fps; the win is feel plus fps-independence.
"Data" = bytes in `$54dc0`, no code touched.

| # | Change | Site | Risk |
|---|---|---|---|
| 1 | **Mouse: facing ∝ dx, stops when the mouse stops.** (a) consume-and-clear: the two 4-byte calls `034152: bsr.w $347f2` and `0341dc: bsr.w $3481e` → `bsr <new>`, where `<new>` = the original clamp/deadzone **plus** `clr.l $6fb6`/`clr.l $6fba` after the read (`--xref $6fb6`: the only other touches are `$1b328`/`$1b3a8` save/restore, `$26b0c` write and the four clear sites, so clearing here is safe). (b) **Data**: zero the deadzones `$54dc0+type*$3e+$4` and `+$12`; the clamps `+$6/+$8/+$14/+$16` then cap the per-frame turn and `+$32/+$35` are the tunable gains `k`. | `$34152`, `$341dc`, `$54dc0` | Low; per-frame clearing also removes the mouse axis's fps dependence |
| 2 | **Joystick/keyboard: fixed rate per second while held, zero on release.** Stop the 50 Hz acceleration: let `$26c1e` only record a *held direction* (reuse `$75c8…$75f4` as `0`/±`$10000` — replace each `subi.l #$4000`/`addi.l #$4000` + store with a constant store, and the release value `$ffff0000`/`$10000` with 0), and have patch #1's `<new>` add `held · K · ΔVBL` to `$6766/$6768`, `ΔVBL` = `$770c` (VBL counter, `$262d4`) minus the value latched at the previous control step. | the 8 branches `$26c6e`–`$26db8`; new code in free space; hook as in #1 | Medium (8 sites, one 3-instruction idiom). Without `ΔVBL` the rate stays fps-linked — the P3 gate |
| 3 | **Release = zero within one frame.** Free with #2 if the injected value is recomputed from the key table each step; #1a's clear also kills the residual mouse rate (§9.6 shows it lasting 10 s). | as #1/#2 | Low |
| 4 | **Repair the joystick axis.** `$26c18: bra.w $26a8e` (4 bytes) → `bsr <new>` loading `d0`/`d1` from the four ramps (or straight from the bits of `$75a9`) at a fixed magnitude, falling into `$26a8e`. Per §7 the game never enables joystick reporting, so packet arrival must be confirmed per machine first. | `$26c18`, `$26b58` | Medium-high; needs a joystick packet source to test |
| 5 | **Map screens: click = Space.** `$6872` is the select event, consumed at `$1ab78`/`$1ab80` but only when `$eb76` (joystick); otherwise the consumer wants scancode `$39` (`$1ab86: cmp.b #$39,d1`). Two-site patch: (a) `$1ab70: 4a79 0000eb76` (`tst.w $eb76.l`) → `4a79 0000eb7a` (`tst.w $eb7a.l`), a 2-byte data change so mouse mode takes the `$6872` path; (b) `$26aca: 31c26fbe` (`move.w d2,$6fbe`, 4 bytes) → `bsr <new>` = `move.w d2,$6fbe.w ; btst #0,d2 ; beq s ; move.w #1,$6872.w ; s: rts`. `$1ab70` is the only `$eb76` consumer. | `$1ab70`, `$26aca` | Low; check drags do not select (the consumer clears `$6872` on read) |
| 6 | **Per-vehicle tuning, data only:** rate scales `$32/$35/$38`, deadzones `$04/$12`, clamps `$06/$08/$14/$16`, rate limits `$0a/$0c`, `$18/$1a`, `$20…$26`, and the response *shape* (selectors `$31/$34/$37`: 1 derivative, 2 direct, 3 direct+integrator). Flipping types 15/17 from selector 1 to 2 removes their extra derivative. | `$54dc0`, 22 × 62 bytes | Low; each vehicle needs its own before/after feel check |
| 7 | **Feel-tradeoff candidate:** the ×3/4 and ×1/2 scalers `$2f784`/`$2f7b0`/`$2f7f0`, gated on `$efb6`/`$efb8`/`$efbc` > 1000, slow the turn rate in some conditions. SimTiming: those words track **fatigue** — `$efb2` (0..250), settled every 5 game-minutes by `$2f51a` from mean speed (`$f968`/`$f96c`). Neutralising the scalers makes the response constant; no fps change, feel only. | call sites `$344ac`/`$345c4` | Low; needs a feel sign-off (it is a game mechanic, not a hack) |

**Recommended shape:** one shared replacement for the `bsr`s at `$34152`/`$341dc` that (a) reads the
`$6fb6`/`$6fba` high words, (b) adds `held_device · K · ΔVBL`, (c) applies the existing per-type
deadzone/clamp from `$54dc0`, (d) writes `$6766`/`$6768`, (e) clears `$6fb6`/`$6fba`. Everything
downstream — rate selectors, scales, apply handlers, the vehicle table — then works unchanged, and P3
(ΔVBL) and P5 (tunable `k`) are both satisfied at one site.
