# MW1 input pipeline: IKBD, control modes, per-vehicle consumption, direct-control hooks

Addresses are RAM addresses of the running game (`work/dumps/ram_ski_walk.bin`, address = file offset); disassembly with
`python3 tools/m68dis.py <dump> <addr> [--end e] [--xref a] [--callers a]`. Dynamic evidence is from 1 MB STE / TOS 1.62 /
Hatari 2.6.1 snapshots `1mb_ski_stand`(M), `1mb_ski_stand_J`, `1mb_ski_stand_K`, `1mb_ski_walk`, a debugger breakpoint at
the per-frame ski step `$13236` logging VBL + words (scripts `/tmp/ctl/e*.py`, not kept). Compare with MW2's note
(`games/in_progress/midwinter2/work/notes/controls.md`): MW1 is the same idea (IKBD IRQ -> accumulators -> per-frame consumer) but simpler.

## 0. Summary

* All three devices end in ONE funnel: `$665e` -> `jmp ($62ac + 4*$62b8)` -> in-game `$66c0`:
  `add.l d1,$24faa` (X) and `add.l d0,$24fae` (Y). Accumulators are 16.16 longs; the game only reads/clamps the **high word**.
* Mouse: the IKBD IRQ `$6400` adds dx/dy **per packet**. Joystick and cursor/keypad keys: the VBL handler (`$61a8`)
  injects +-5.0 counts **per VBL** (50 Hz) while held, through the same funnel. Release leaves the accumulator where it is.
* The per-frame consumer `sub_012fe2` makes the turn rate a cubic of `$24faa` (clamped +-512) and **never decays it**:
  a deflection is a persistent rate (a "yoke"), for mouse and for keys. A held key reaches the clamp in about 100 VBL and
  keeps turning at 32 units/frame **after release**. This is what the direct-control patch must change.
* Best hook: **replace `sub_012fe2` (`$12fe2..$13021`, 64 bytes, called from ski `$13236`, buggy `$135d0`, glider `$13754`)
  by a 46-byte consume-and-scale routine (section 8, tested live)**. It gives constant turn rate while a key/stick is held,
  zero on release, and "motion only" for the mouse, with one routine for every vehicle and all three control modes.
* Mode flags `$24b7e/80/82` only select a step table at PLAY time; `$2c17a` (keys) is never read. J and K differ only in
  the step table and a fire-button remap. The three modes are NOT separate code paths (section 3).

## 1. Cost

`work/prof/walk.txt` (35.27 M cycles/250 VBL): IKBD IRQ `$6400-$652d` 0 cycles (no packets during the profile);
`sub_00652e` + `sub_0065c0` (`$652e-$6649`, VBL, keys+joystick) 108 240 = 433 cycles/VBL; funnel/dispatch `$664a-$671f`
58 080 = 232 cycles/VBL; `$61a8-$6271` 69 520; turn `$12fe2-$13021` 5208. Total about 0.5 % of the frame budget, so there is
**no fps win here**; the value of the patch is behaviour (direct, fps independent), not speed.

## 2. IKBD handler `$6400` (vector `$118`)

Installed by `$67a8`: `move.l #$6400,$118.l` (`$67e8`; the old vector saved to `$2c294`), `$61a8` as VBL (`$70`),
`$64f4`/`$64f6` as dummy `$14/$68/$114` handlers, `move.w #$2,$62b8` (input context = in game; `$62b8` is 0 or 2 elsewhere:
`$1089c clr.w $62b8` on the options screen, `move.w #$2,$62b8` at `$4118,$5192,...` and restored from the stack).

```
6400: movem.l d0-d2/a0,-(a7)
6404: btst.b #7,$fffc00 ; beq $64e8                       ; no IRQ data -> exit
6410: tst.w $2c31c ; bmi $6510 ; bne $6480                ; state: <0 joystick byte, >0 in packet, 0 idle
641e: move.b $fffc02,d0                                   ; header / scancode
6424: cmp.b #$f6,d0 ; bcs $64ac                           ; < $f6 -> scancode
6430: cmp.b #$ff,d0 ; beq $6506                           ; $ff -> $2c31c = $ffff (joystick byte follows)
6434: cmp.b #$f8,d0 ; blt $645c ; cmp.b #$fb,d0 ; bgt $645c
6440: lea $2c31e,a0 ; move.b d0,(a0) ; move.w #2,$2c31c ; clr.w $2c322   ; mouse header $f8-$fb
645c: $2c31c = 7 ; $2c322 = $fa  ; else ($f6,$f7,$fc,$fd,$fe) -> discard 7 bytes ($6470/$6480 loop)
6480: data byte: if $2c322 != 0 -> discard ; else move.b d0,(a0,d1.w) ; subq.w #1,$2c31c ; bne $64e8
64a6: bsr $664a                                           ; packet complete
6510: (joystick) $2c31c = 0 ; move.b $fffc02 -> $2c328 ; $2c32c = $ffff   ; joystick byte latched + flag
64ac: scancode: press (bit7 clear): $2c324 = sc ; move.b #$ff,($2c29a,sc) ; $2c326 = $ffff
64cc: release: $2c324 = sc|$80 ; jmp $392.w -> (HAGA hook, falls to $64d6) clr.b ($2c29a,sc&$7f) ; if $2c326==0 : clr $2c324
64e8: movem.l (a7)+ ; bclr #6,$fffa11 ; rte
```

* Store order: byte 1 after the header goes to `$2c31e+2`, byte 2 to `$2c31e+1`, so `$664a` reads `d0 = (a0+1)` = **dy**,
  `d1 = (a0+2)` = **dx** (`$664e move.b $1(a0),d0 ; ext.w ; $6654 move.b $2(a0),d1 ; ... swap d0 ; swap d1`).
* Key-down table `$2c29a[scancode]` = `$ff`/0 (byte per scancode); `$2c324` = last scancode, `$2c326` = "key pending" flag
  (cleared by the consumers `$bd44`, `$12ad0`, ...). `$12ac6` converts `$2c324` to ASCII through `$24846` (scancode->ASCII
  table; `$33` -> `<`, `$34` -> `.`, `$39` -> space) into `$12afc`, the key the action loop sees (`X`=`$58`, `M`=`$4d`, `P`=`$50`,
  `S`=`$53`, space=`$20`, `$14f12..$14f3c`, `$131de`, `$13216`).
* Joystick: the IKBD (Hatari `--joy1 keys`) sends `$ff <byte>` for joystick 1 (bits 0 up, 1 down, 2 left, 3 right, 7 fire);
  `$fd/$fe` (joystick 0 / other) are discarded. **Joystick 1 fire also arrives as a mouse right-button packet `$f9`**
  (measured: `$2c31e = f9 00 00` and `$24fba` toggling 1/2 per VBL with Ctrl_R held; see section 3).
* `$664a` -> `$665e`: `d2 = (a0)&3` (buttons: bit1 = left, bit0 = right) -> `$24fba` (**button state, level**, not an event);
  `$6678/$6686` also latch `$24fc2/$24fc0 = $ffff` on right/left presses [INFERENCE: for menu click polling; the only
  writers are those two instructions]; `$666c: clr $24fa0` when no button is down.

## 3. Control modes `$24b7e/$24b80/$24b82`

Set on the Game Options screen: `$10944` (mouse icon): `$24b7e=$ffff`, others 0; `$1095a` (stick): `$24b80=$ffff`; `$10970`
(keys): `$24b82=$ffff` (init at `$10852..$10866` = mouse). At PLAY (`$1091a..$1092e`) they are **copied** to `$2c176/$2c178/$2c17a`
and then `jsr $675e` (`$10938`, only caller):

```
675e: clr.l $24f40 ; clr.l $24f44                          ; X step, Y step = 0
676e: tst.w $2c176 ; bne $67a2                             ; MOUSE: steps stay 0 -> keys/joystick never steer
6776: lea $24f48,a0 ; tst.w $2c178 ; bne.b $678a          ; STICK: table $24f48
6784: lea $24f70,a0                                        ; KEYS : table $24f70
678a: move.w $24f3c,d0 ; lsl.w #3,d0
6792: move.l (a0,d0.w),$24f40 ; move.l 4(a0,d0.w),$24f44
```

`--xref` of the flags: `$2c176` read at `$676e` only; `$2c178` at `$668e` and `$677c`; **`$2c17a` has no reader**.
Tables (identical in this build): five (X,Y) pairs of 16.16 longs `(5,5) (8,6) (8,8) (6,4) (10,4)`; the live values in the J and K
snapshots are `$24f40 = $00050000`, `$24f44 = $00050000` (= 5.0 counts per VBL), mouse snapshot 0. `$24f3c` reads 4 in the dump
(entry 4 would be (10,4)), so [INFERENCE] it was 0 when PLAY was clicked; nothing writes it by absolute address.
Key configuration words `$24f30..$24f3a` = `$33 $34 $68 $6e $6a $6c` = `,` `.` KP8 KP2 KP4 KP6 (left button, right button, up, down, left,
right); the cursor keys are not in it.

Consequences, all measured:

| mode | joystick (Hatari `--joy1 keys`) | keypad keys | buttons |
|---|---|---|---|
| M | ignored for motion (steps 0): Left/KP4 held, `$24faa` stayed 0, `$24f98` 0 | same (`KP4 held acc 0`, `KP8 held yacc 0`) | `,` -> `$24fba=2`, walk started (speed 207) |
| J | cursor keys: `$24f98 = +-$50000`, `$24f9c = +-$50000` while held, 0 on release | KP4/KP6/KP8/KP2 also steer (`$652e` is ungated) | fire (Ctrl_R) = packet `$f9`, remapped by `$668e..$66a2` (`tst.w $2c178 ; $2c32e == $f9 -> $24fba = 2`) to **left button**: starts walking; `.` still = right (stop) |
| K | identical to J (same code, table `$24f70`) | KP keys | fire = `$f9` = right button (stop); `,` = left |

Mouse mode needs the mouse only; there is no run-time check of the flags anywhere in the steering code, so the direct patch
does not need them.

## 4. Where keys/joystick are turned into counts (VBL, `$61a8`)

```
61de: bsr $69b8
61e2: bsr $65c0          ; joystick (and replay of the held vector), every VBL
61e6: bsr $652e          ; keyboard keys, every VBL
```
`sub_0065c0`:
```
65c6: tst.w $2c32c ; bne $65e2            ; new joystick byte?
65ce: move.l $24f98,d1 ; move.l $24f9c,d0 ; move.b $2c31e,($2c32e) ; bra $6646     ; no -> REPLAY the held vector + last mouse header
65e2: d2 = $2c328 ; byte at $2c32e = $fb if bit7 (fire) ; bit0 -> d0 = -$24f44 ; bit1 -> d0 = +$24f44
65f6..662a: bit2 -> d1 = -$24f40 ; bit3 -> d1 = +$24f40
662e: move.l d1,$24f98 ; move.l d0,$24f9c ; clr.w $2c32a ; clr.w $2c32c ; $6646 bra $665e
```
So the joystick direction is **latched** (`$24f98/$24f9c` = +-5.0 while held, 0 on release, measured) and re-injected every VBL.
`sub_00652e` (keys): `$2c332` = button bits from the keys `$24f30/$24f32`, `d0 = -/+ $24f44` from `$24f34/$24f36`,
`d1 = -/+ $24f40` from `$24f38/$24f3a` (up/left negative; right/down positive, the later test wins), then `bra $665e` only if a
direction or button is active.

Direction convention: X right = +, Y **down = +** (dy of the mouse packet); `$24fae` becomes **negative when pushing forward**.

## 5. The per-frame consumers of `$24faa` (X) and `$24fae` (Y)

Per-vehicle step function pointers live in 58-byte mode records in `$12d3e..$12f00` (table copied into `$12d5e` (step) and `$12d62`
(init); the loop `sub_014e00 -> $14fac / $12e9c` jumps through `$12d5e`). Step pointers in the table: `$12d9e = $131ae` (ski),
`$12dd8 = $1359a`, `$12e12 = $1373c`, `$12e4c = $13f36`, `$12e86 = $13d78`; the live copy in the snapshot is `$131ae/$1314c`.
Names for the second and third by their controls and by `work/manual-proper.md` (buggy: throttle+steer; glider: pitch+steer):
`$1359a` = snow-buggy, `$1373c` = hang-glider, `$13f36` = snipe (S key); `$13d78` reads neither accumulator [INFERENCE: not a
steering mode]. `$4d66/$4d68/$4d6a` are per-vehicle skill values read by the init routines (ski `$13154`, buggy `$13566`, glider `$13700`).

### 5.1 Turn: `sub_012fe2` (all three vehicles)
```
12fe2: move.w $24faa,d0 ; cmp.w #$200 / #$fe00 -> clamp ; move.w d0,$24faa      ; clamp +-512, WRITTEN BACK (yoke persists)
13004: move.w d0,d1 ; muls.w d0,d1 ; asr.l #6,d1 ; muls.w d0,d1 ; swap d1       ; d1 = acc^3/64/65536
13014: move.w d1,$15110 ; add.w d1,$12c98 ; rts                                  ; rate -> heading, once per frame
```
Callers: `$13236` (ski, every state, standing included), `$135d0` (buggy; skipped when `$14774 < 0`), `$13754` (glider).
Glider also uses the returned d1 (`$1377a add.w d1,d1 ; move.w d1,$12c9c` = bank angle = 2 x turn rate).
Measured (J snapshot, Left held ~100 VBL then released): `$24faa` ramped -40 -105 -175 ... -512, heading step grows 1,2,4,8,15,28,50...
and settles at **-32 per frame** (= 512^3/64/65536); after release `$24faa` stays -512 and the heading kept falling 32/frame
(rows to VBL 6823: -818). Keys (K): the same (`-505`, step -31).
Quirk: `swap d1` floors, so any small negative accumulator gives -1 per frame and a small positive one 0: the mouse run left
`$24faa = -10` after +-100 px moves and the heading drifted -1/frame for 700 VBL (`e9` trace rows 6871..8277).
Mouse scaling observed: 100 host px = 40 to 50 counts (`$24faa` +40, then -50).

### 5.2 Lever: `$24fae` through `sub_013022` (ski) and in-line (buggy, glider)
`$13022: d0 = -$24fae ; d1 = $13544 ($00000200) ; bsr $14474 (clamp d0 to 0..$200) ; $24fae = -d0`. So `$24fae` is a lever in
`[-512, 0]`, forward = negative, written back each frame, persistent. Ski callers: `$1331e` (walking state) and `$1342e`
(skiing state) only; the standing path (`$1327e..$132f8`) never touches it.

* Walking state (`$13316..`): `$13548 = lever_magnitude + $200` (`$13322 addi.w #$200,d0`), speed `$15112 = $152a8 * $13548 >> 16`
  (`$133a0 mulu.w $13548,d1 ; asr.l #8 ; asr.l #8`). Measured: lever -512 -> factor 1.0 (`$152a8 24847 -> speed 388`), lever -482
  -> speed 324 with `$152a8 21408` (21408*994/65536 = 324.7). So the lever scales speed between 50 % (0) and 100 % (-512); it never
  reverses. K mode: KP2/Down raised the lever -512 -> -62 at 5 per VBL (rows 6354-6421) and the speed followed to about 26;
  KP8 pushes it back at the same rate.
* Skiing state (`$13426..`): `$1342e ... asl.w #4,d0 ; move.w d0,$152a8` -> the lever IS the speed command (x16) [INFERENCE from
  the disassembly; the walk snapshots never entered this state]. Entry sets the lever (`$133fe`, `$13420`: `-($13540>>5)`).
* Walk start (`$133dc/$13408/$132fc`) resets the lever: after the left button the trace shows `$24fae = -512` at once
  (M: row 7346, K: row 6179) whatever it was.
* Buggy `$1367a`: `d0 = $24fae` clamped by `$1445a` to +-`$13598`, `tst.w d0 ; bmi keep ; else clr` -> `$24fae`; `$136f6 = -d0`
  -> speed (`$136be`). **The Y lever is a throttle position and persists** [INFERENCE: not run].
* Glider `$13796..$137d0`: `d0 = $24fae - $13b5e` clamped to +-`$200` by `$1445a`, stored back, `$12c9a = (d0>>2)&$3fe` = pitch;
  also a position, persistent.
* Snipe `$13f36`: **position semantics**: `$13f08 move.w d0,$24faa` seeds it from the heading `$12c98<<2` on entry; `$1403c..$14060`
  `$12c98 = ($24faa>>2 + sway)&$3fe`; `$14066..$140a0` pitch = `-$24fae>>2` (+sway), lever clamped +-`$200`. Aim already
  stops when the input stops; the 5-counts-per-VBL step is time based. No change needed for snipe.
* Exertion: `$13618` (buggy) compares `$24faa` with `$1413a` and adds `$28` to `$1354c`; glider `$137ac` does the same with `$24fae`/
  `$1413c`; `$1354c` is summed by `sub_012f9e` into `$2c422` (a byte drained per frame) [INFERENCE: stamina]. See section 8 for the fix
  that the new `$12fe2` forces on `$13618`.

### 5.3 Buttons (`$24fba`, level)
`sub_0130da`: `btst #1,$24fba` (left); `sub_0130e6`: `btst #0,$24fba` (right). Ski: stand -> left button = start walking
(`$132cc`: `bsr $130da ; bne $133dc`); walking/skiing: right button = stop (`$13316: bsr $130e6 ; bne $1327e`; at `$1327e` the speed
word is divided by 3 per frame: `$152a8` 3146 -> 1048 -> 349 -> 116 -> 38 measured). Left button alone while walking does nothing more
(measured: trace column btn=2 then speed ramps 120 -> 273 by itself). Keys: `S` (`$131de`, only at speed 0) -> snipe, space `$20`
-> `$1fc6e` (grenade), `X` `$14f12` -> exit, `M` `$14f22` -> map. Buggy: space -> `$1fbbe`, right -> `$1fe56`, left -> `$1fd96`
(`$135a0..$135c2`); glider: left -> `$1ff16` (`$13788`). Mouse Y moves while standing do nothing.

## 6. Dynamic runs (summary of raw rows)

| run | action | result |
|---|---|---|
| J stand | Left held ~100 VBL (13 VBL/frame at 8 MHz) | acc `-40 -105 -175 -240 -305 -375 -450 -520 -587 -577 -582 ... -512`, heading step `-1 -2 -4 -8 -15 -28 -50 -82 -114 -146 ...` (+-32/frame), unchanged after release; the clamp only happens at frame time (-587 > 512 seen) |
| J | Ctrl_R (fire) | `$24fba` 2 (left) while held; walk starts: lever -512 at once, speed 120->273 |
| J | Down / Up held | `$24f9c = +327680 / -327680`, lever -512 -> -62 over 80 VBL, then back to -512 |
| J | Right / Left held | `$24f98 = +/-327680`, acc 65 170 270 355 (+5/VBL), then constant after release |
| K stand | KP4 / KP6 (`hatari-event keydown 106/108`, `$2c29a[$6a/$6c]=$ff`) | `$24faa` 65111 (= -425) / 65449; KP8 (`$68`) `$24fae` -580, KP2 `$6e` +425 |
| K | `,` (`$33`) / `.` (`$34`) | btn 2 -> walk, lever -512; btn 1 -> stop, speed decays 27 -> 16 -> 5 -> 1 -> 0 |
| M stand | Move +100 px | `$24faa` +40; -100 px: -10 (yoke persists, heading -1/frame for 1000+ VBL, cubic of -60 = -1) |
| M walk | RMB / LMB | btn 1 / 2 as expected; down 60 px moved the lever -512 -> -482 |
| M | KP4/KP8/Left held | `$24faa/$24fae` stay 0 (steps 0) |

Harness notes: `xdotool keydown KP_4` was seen to reach the game as `$4b` (cursor-left, = joystick left under `--joy1 keys`) in one run
(key table `$2c29a[$4b]`) and as `$6c` for KP_6 in another, so it is unreliable for the key table; use `h.cmd('hatari-event keydown 106')` / `keyup` (ST scancodes decimal: KP4 106, KP6 108, KP8 104, KP2 110,
`,` 51, `.` 52) for the key table. The cursor keys must go through xdotool (`Left/Right/Up/Down`, `Control_R` = fire) with
`extra=['--joy1','keys']`. `peekw`/`peek` after `e VBL` costs ~0.6 s each; the VBL counter (`e VBL`) and ~13 VBL/frame at 8 MHz
(27 under host load) vary between runs, so measure counts, not wall time.

## 7. Why the current behaviour is fps dependent

Injection is per **VBL** (5 counts per VBL, frame-rate independent) but the application is per **frame** (rate = cubic of the persistent
acc): at 13 VBL/frame a held key gives 32 units/frame = 123 units/s; at 16 MHz (about 6 VBL/frame) the same hold gives 32 units/frame
= 260 units/s. Mouse: persistent deflection x frames. The ramp to the clamp also depends on VBLs per frame (quadratic-looking
because `$24faa` grows linearly and the rate is cubic).

## 8. Hook sites and the direct-control patch

**H1 (required): replace `sub_012fe2`.** Consume all counts since the last call, scale, no persistence, keep `d1 = rate` and `$15110`:

```
12fe2: 2039 0002 4faa   move.l $24faa.l,d0       ; high word = signed sum of counts, low word always 0
12fe8: 91b9 0002 4faa   sub.l  d0,$24faa.l       ; race-free consume (one RMW instr; IKBD IRQ adds are not lost)
12fee: 4840             swap   d0                ; d0.w = counts (signed)
12ff0: 3200             move.w d0,d1
12ff2: 4a40             tst.w  d0
12ff4: 6a02             bpl.s  +2                ; skip the neg
12ff6: 4440             neg.w  d0                ; |counts|
12ff8: e240             asr.w  #1,d0             ; magnitude / 2  (K = 0.5 unit per count; tune)
12ffa: 4a41             tst.w  d1                ; original sign
12ffc: 6a02             bpl.s  +2
12ffe: 4440             neg.w  d0                ; restore sign (symmetric, no floor bias)
13000: 3200             move.w d0,d1
13002: 33c1 0001 5110   move.w d1,$15110.l
13008: d379 0001 2c98   add.w  d1,$12c98.l
1300e: 4e75             rts                      ; 46 bytes; the rest up to $13021 may stay (never reached) or be 4e71
```
(Exact byte stream that was loaded live: `20 39 00 02 4f aa 91 b9 00 02 4f aa 48 40 32 00 4a 40 6a 02 44 40 e2 40 4a 41 6a 02 44 40 32 00
33 c1 00 01 51 10 d3 79 00 01 2c 98 4e 75`, `loadbin` at `$12fe2`, 0x2e bytes.)

Tested live on the snapshots (patch applied with the debugger, not stored):

| snapshot | input | rows (`acc` seen at `$13236`, heading, rate) |
|---|---|---|
| K stand | KP4 held ~95 VBL | acc -20 -70 -70 -65 0 0; rate -35 -32 -32 -12 0 0; heading -223 then **constant**; release -> rate 0 at once |
| K stand | KP6 held | acc 65 70 70 30 0; rate +5 32 32 37 0; heading back to 0, then constant |
| M stand | +100 px | acc 40 -> heading +20 once, rate 20 then 0; -100 px: acc -50 -> heading -25, then constant (no drift) |

Properties: joystick/keys give `5 counts x VBLs held x 0.5` = 2.5 units per VBL = 125 units/s (as fast as the old maximum at 8 MHz) while held and
0 after release, independent of frames per second (time based because the injection is per VBL); mouse = `0.5 x counts`, motion only.
Tune only the constant `e240` (replace by `muls.w #K,d0 ; asr.l #n,d0` for another gain) and, separately for the keyboard/stick, the **step
tables** `$24f48/$24f70` (data, first long of each pair, 5.0 now) so the stick and the mouse can have different gains without touching code.
Under a later fixed-tick conversion `$12fe2` stays correct: it consumes whatever accumulated since the previous call, so the per-tick turn
is proportional to elapsed time. For hang-glider banking (`$12c9c = 2 x rate`) [INFERENCE] the bank angle would scale with frame length;
normalise there if the frame rate changes.

**H2 (needed with H1): `$13618 move.w $24faa.l,d0` (buggy exertion test).** After H1 `$24faa` is 0 when `$13618` runs (the same frame's
`$135d0` already consumed it), so the "turn changed" compare never fires. Change the operand to `$15110`: bytes `30 39 00 01 51 10`
(same size, 6 bytes) -> the buggy keeps its exertion `+$28` on turn-rate changes. Ski has no equivalent; the glider compares `$24fae`
which H1 does not touch.

**Not needed:** the Y axis. The lever is a position in `[-512,0]` (`$13022`, `$1445a`) and the stick/keys move it at 5 counts per VBL,
time based; this is also what the original mouse does. If the user wants "held up = full effort, release = ?" that is a gameplay change,
not a fix. Snipe needs nothing (section 5.2).

**Alternatives considered:**
* Patching the funnel `$66c0` (`add.l d1,$24faa`): cannot tell mouse packets from injected steps (both are `n<<16`), so the clamp/zero
  logic would end up per device anyway; the frame-time consume in H1 is simpler.
* Patching the injectors (`$665e` callers `$6646` and `$65ba`) to store the held vector and consume it at `$12fe2`: needs 3 sites and a
  new variable, samples the key state at frame time (a tap shorter than a frame is lost); the accumulate-then-consume form keeps taps.
* The cubic is only for the mouse feel of the original; the patched routine is linear. If a mouse acceleration curve is wanted, apply it
  to the counts before the sign restore.

## 9. Open items

* The buggy and glider paths were read, not run: no snapshot reaches them (garage / glider are not reachable from the Devils Valley start,
  `work/baseline.md`). The claims in sections 5.2 for them are from disassembly and marked [INFERENCE] where behaviour is inferred.
* `$24f3c` (step table index, 4 in the dump, evidently 0 at PLAY) has no other reference.
* `$24fc0/$24fc2` click latches: the writers are `$6678/$6686` only; the readers (menus) were not located [INFERENCE: base-relative reads].
