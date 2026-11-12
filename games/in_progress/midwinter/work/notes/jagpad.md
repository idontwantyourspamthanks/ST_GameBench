# MW1: Atari Jaguar pad on the STE enhanced joystick ports (patches `jag_vbl` `jag_mrg` `jag_btn` `jag_rmp`, default: no)

Source study: `reports/jaguar_pad_study.md` (protocol, detection, the proposed MW1 map). Everything below is raw output of this session (Hatari 2.6.1,
`tools/m68dis.py` on `work/dumps/ram_ski_walk.bin`, the test scripts in `work/jagpad/`) or marked `[INFERENCE]`. **No real STE with a pad was available: Hatari's own
pad emulation (`joy.c`) is the only evidence for the electrical side.**

## 1. What changed (four 6-8 byte splices, one blob of 474 bytes)

All four are needed together; each stub is self-contained and harmless alone (it reads state bytes that are 0 without `jag_vbl`).

| patch | site | original | new | role |
|---|---|---|---|---|
| `jag_vbl` | `$61e2` (8 B) | `bsr.w $65c0` / `bsr.w $652e` (VBL: joystick re-read, key poll) | `jsr $b6900.l` / `nop` | poll the pad, then the two displaced calls (as `jsr`) |
| `jag_mrg` | `$65e2` (6 B) | `move.w $2c328.l,d2` | `jsr $b6c00.l` | the latched IKBD joystick byte `OR`ed with `PADJ` (pad directions) |
| `jag_btn` | `$665e` (6 B) | `move.b (a0),d2` / `andi.w #3,d2` | `jsr $b6c10.l` | button byte of the input funnel `OR`ed with `PADBTN` (pad fire) |
| `jag_rmp` | `$6696` (6 B) | `move.b $2c32e.l,d2` | `jsr $b6c20.l` | J-mode fire remap: `$f9` when `PADBTN` is set |

Blob map: code `$B6900-$B6AD9`, data `$B6BF0-$B6BF7` (`PADST` byte, `PADJ` byte, `PADBTN` byte, `PADG` byte, `PADOLD` long at `$B6BF4`), stubs `$B6C00/$B6C10/$B6C20`.
Registers: the VBL handler `$61a8` begins `movem.l d0-d7/a0-a6,-(a7)` (`0061a8: 48e7fffe`), so the poll uses d0-d7/a0-a2 freely.

### 1.1 How the pad reaches the game's own paths (disassembly of `ram_ski_walk.bin`)
```
0061e2: bsr.w $65c0 (joystick)   0061e6: bsr.w $652e (keys)          <- jag_vbl
0065c6: tst.w $2c32c / bne $65e2 ; no new byte: replay $24f98/$24f9c + header $2c31e -> $2c32e, bra $6646 -> $665e
0065e2: move.w $2c328.l,d2       (new byte: bit0 up, bit1 down, bit2 left, bit3 right, bit7 fire)   <- jag_mrg
0065f6..: d0 = -/+$24f44 (Y), d1 = -/+$24f40 (X), $24f98 = d1, $24f9c = d0, clr $2c32c
00665e: move.b (a0),d2 / andi.w #3,d2 / bne $666c / clr.w $24fa0 / move.w d2,$24fba (bit1 left, bit0 right)   <- jag_btn
00668e: tst.w $2c178 (J mode) / beq $66aa / move.b $2c32e.l,d2 / cmp.b #$f9,d2 / bne / move.w #2,$24fba    <- jag_rmp
0066aa: jmp ($62ac + 4*$62b8)  ->  $66c0: add.l d1,$24faa / add.l d0,$24fae   (the funnel p5_ctl_turn consumes)
```
* **Directions.** `jag_vbl` stores the pad directions in `PADJ` in the IKBD layout (1 up, 2 down, 4 left, 8 right). On a change it writes `$2c32c = $ffff`, the flag
  the IKBD ISR sets for a new joystick byte (`006524: move.w #$ffff,$2c32c`), so `$65c0` recomputes `$24f98/$24f9c` from `$2c328 | PADJ` (`jag_mrg`) and then replays
  the vector every VBL. The real byte `$2c328` is never written: stick and pad both work, and the result is exactly the stick's vector (`+-$50000` = 5.0 counts, step
  table `$24f40/44`). The funnel `$66c0` adds it to `$24faa/$24fae`; `p5_ctl_turn` (`$12fe2`) consumes those, so the pad is a stick for the direct-control path with nothing
  else changed (section 3.2 compares stick and pad in the same run).
* **Fire = B.** A joystick-1 fire reaches the game as the IKBD right-button bit of a mouse packet (`$f9`), which J mode turns into the left button
  (`$668e..$66a2`). `PADBTN = 1` is ORed into the button byte at `$665e` (so `$24fa0` is not cleared and the latches `$24fc0/$24fc2` behave as for the stick) and `jag_rmp`
  returns `$f9` at `$6696`, so the funnel writes `$24fba = 2` (left button) every VBL while B is held. `$2c31e/$2c32e` (the mouse header) are never touched, so a real mouse
  or stick packet cannot race with the pad.
* **Keys.** `jag_vbl` runs the game's own key bookkeeping, replicated from `$64b6..$64c2` (make: `$2c324 = sc`, `$2c29a[sc] = $ff`, `$2c326 = $ffff`) and
  `$64cc..$64e2` (break: `$2c324 = sc|$80`, `$2c29a[sc] = 0`, `if $2c326 == 0: clr.w $2c324`; the HAGA hook `$392` only special-cases the break codes `$e5/$e6`), with
  `ori #$700,sr` around the loop because the IKBD ISR (IPL 6) writes the same words. **One make per press and one break per release: nothing repeats.**
* **J mode only**: `$2c178` (read at `$668e` and `$677c`, written nowhere) gates the poll. In M and K mode the pad is read as "nothing pressed", so state and keys that were
  held when the mode changed are released and `PADJ` goes back to 0.

### 1.2 The button map (Jaguar pad -> game)
| pad | game | how |
|---|---|---|
| D-pad | the joystick (menu pointer, skiing, sniper sights, buggy, glider) | `PADJ` -> `$65e2` |
| B | the joystick fire = **left button** (walk / start the glider / fire missiles / zoom in when sniping) | `PADBTN` |
| A | `>` `$34` = **right button** (stop / zoom out) | key table |
| C | Space `$39` (grenade, bullets, torpedoes, missiles, glider 45 degree view) | key |
| Option | X `$2d` (leave the action mode to the Decisions display) | key |
| Pause | P `$19` (pause / resume) | key |
| 1 | M `$32` (main map) | key |
| 2 | S `$1f` (ski / sniper) | key |
| 3 | H `$23` (help, menu screens) | key |
| `*` `#` `0` `4`-`9` | unassigned | |

The pad bit layout (`S`, 1 = pressed): byte 0 = group 4 (bits 0-3 Up Down Left Right, bit 4 Pause, bit 5 A), byte 1 = group 3 (bits 8-11 `*` 7 4 1, bit 13 B), byte 2 =
group 2 (bits 16-19 `0` 8 5 2, bit 21 C), byte 3 = group 1 (bits 24-27 `#` 9 6 3, bit 29 Option); the table `keymap` at `$B6AA4` is `{bit, scancode}`.

### 1.3 Reading the pad (per VBL; `poll` in `jag_vbl.s`) - one group per VBL, adopted from Hunter's `jag_pad` (work/notes/jagpad.md section 9 there)
Select words `$FFEE/$FFDD/$FFBB/$FF77` = group 4/3/2/1 on **both** ports at once. Each VBL the poll **reads** the group that the previous poll selected (`$FF9200` and `$FF9202` as **words**: a byte read of
`$FF9200` bus-errors on a real STE), decodes that one group, replaces its byte in `S` (`PADOLD`), then **selects the next group** (round robin 4, 3, 2, 1; `PADG`) and returns, leaving it selected.
So the settle time is a whole VBL (20 ms): no `dbra` loop and no assumption about CPU speed (the Falcon needs no special case). The price: every switch is sampled at 12.5 Hz (a press shorter than
80 ms can be missed; the stick vector and `$15110` rates are unaffected, a held direction is a level). The ports are ANDed (low = pressed) so a pad in either port works. Never several groups at once
(Team Tap). The first version of this patch read all four groups every VBL with 23 us waits: 977 cycles/VBL (0.61 %) on the STE.

### 1.4 Detection (first VBL with `$2c178 != 0`, cached in `PADST`: 0 unprobed / 1 pad ports / `$ff` none)
Same layers as Hunter's `jag_pad` (`games/in_progress/hunter/patches/jag_pad.s`); the first version of this patch had a 68000-only gate, dropped at the lead's request so the Falcon gets the pad.
1. Guarded byte reads (vector `$8` swapped, `a7` restored by the handler, the pattern of `p4_blit_sky`): `$FF8901` (DMA sound) **must answer** (bus error on ST / Mega ST) and the SCU `$FF8E01`
   **must bus-error** (answers on a Mega STE and a TT, faults on an STE and a Falcon). A machine that fails either test never has a pad register read.
2. Guarded word write `$FFFF -> $FF9202` and word reads of `$FF9202`/`$FF9200`: no bus error.
3. Idle sanity: high byte of `$FF9202` = `$FF`, low nibble of `$FF9200` = `$F` (a Mega STE reads `$FFF9`, a TT `$3F03`: refused; study 1.3).
No blitter or `$FF8E21` test any more (the SCU test refuses the Mega STE and the TT). Without a pad port the VBL cost is `move.b PADST,d0 / bmi` plus the three stubs.
[INFERENCE] A real Falcon that answered at `$FF8E01` would be refused (fail closed).

## 2. Cost
`work/jagpad/prof_pad.py` (Hatari profile cycles over 100 VBL, 1mb_ski_stand_J + live set; pad emulated on host keys, nothing / B / Left held):
```
pad idle      :    457.0 cycles/VBL in $b6900-$b6c3f = 0.406 % of the profiled cycles (112586/VBL profiled; VBL = 160256 cycles = 0.285 %)
pad B held    :    459.2 cycles/VBL in $b6900-$b6c3f = 0.407 % of the profiled cycles (112783/VBL profiled; VBL = 160256 cycles = 0.287 %)
pad Left held :    456.4 cycles/VBL in $b6900-$b6c3f = 0.406 % of the profiled cycles (112536/VBL profiled; VBL = 160256 cycles = 0.285 %)
hot addresses (last run): [(747900, 2240), (747904, 2240), (747926, 1680), (747868, 1540), (747806, 1400), (747810, 1400), (747816, 1400), (747824, 1400)]
```
* **With pad ports (STE, and the Falcon runs the same code): about 457 cycles per VBL = 0.29 % of a 160256-cycle PAL VBL**, the same while buttons are held (a change only costs once). The first version
  (all four groups every VBL with 23 us `dbra` waits) was 977 cycles = 0.61 %.
* **Without pad ports** (profile of the blob in the ski view, cold boots): ST 134.4 cycles/VBL, Mega ST 134.4, Mega STE 181.1 (the figure includes the three stubs that replace three instructions
  of the game); the TT and the Falcon take the same `move.b PADST` + `bmi` path only when the probe says no (the Falcon says yes).
* `mw1ab.py` "cycles per frame" for the J snapshot: +0.60 % (760744 -> 765297); it follows the phase of the 5 Hz world tick against the VBL (flips per 1000 VBL 204 -> 203), not only the poll; the profile above is the cost.

## 3. Tests (all raw logs in `work/jagpad/`; the numbers below are from the FINAL code, one group per VBL, no CPU gate)
Hatari pad emulation: `work/jagpad/pad.cfg` maps pad A to host keys (w/s/a/d = directions, z = A, x = B, v = C, o = Option, p = Pause, 1/2/3 = keypad 1/2/3) and ST joystick 1 ("the
real stick", IKBD path) to the cursor keys + Right Ctrl, so the same run can drive the game with the stick and with the pad (`--joy1 keys --configfile pad.cfg`). A held host key is a held
pad button (study 2.1). Build under test: `build/jag` = every default patch + `jag_*` (`mw1patch.py build --only <default set> pp_nofade pp_bigram_cache jag_vbl jag_mrg jag_btn jag_rmp`), cold
boot of the HD build (`RUNME.TOS` from the GEMDOS drive), control mode J, `tools/mw1.py boot_to_game('J')` (Options -> J -> PLAY -> Team -> Stark -> Decisions -> Skiing).
A bug found by the first snapshot run of the one-group version (stale upper word of `d2` shifted into `S`: phantom keys, the game left the action mode) is fixed (`andi.l #$3f,d2`); all runs below are after the fix.

### 3.1 No pad: pixel identity (`work/jagpad/ab_seq.py` = `mw1ab.py` with one Hatari at a time; base = default set, patched = default set + jag; no key pressed)
```
stand --flips 8: IDENTICAL; flips/1000VBL 220 -> 220; cycles/frame 708338 -> 708389 (+51, +0.01 %)
stand --flips 40: IDENTICAL
1mb_ski_stand_J --flips 8: IDENTICAL; flips/1000VBL 204 -> 203; cycles/frame 760744 -> 765297 (+4553, +0.60 %)
1mb_ski_stand_J --flips 40: IDENTICAL
ALL IDENTICAL
```
(An earlier run of the first version covered `stand walk turn busy 1mb_ski_stand_J`, all IDENTICAL.) `1mb_ski_stand_J` is a J-mode snapshot in which the pad poll runs every VBL (the probe runs right after the live patch is applied at a flip).

### 3.2 Cold boot, STE 1 MB TOS 1.62, J mode (`coldpad.py ste`)
Stick and pad run the same input script in the same session, in the ski view, on the sniper view (pad key 2 = S), and with the buggy and glider step handlers forced
(`w $12d5e $1359a / $1373c`: no save reaches a vehicle, as in `p5_controls.md`). Columns: `L` = Left held 2.0 s: heading change, VBLs, `$15110` (turn of the last step),
vector X, `$24faa` hi word; `R` the same for Right; `U`/`D` = vector Y and `$24fae` hi word; `fire` = the set of `$24fba` values over 6 samples, speed at 0.8 s and 2.3 s, `$24fba` after release.
```
boot_to_game J ok in 114 s, control mode J
after boot   vbl=5809 PADST=01 PADJ=00 BTN=00 OLD=00000000 vec=(+0.0,+0.0) $24fba=0000 head=0 rate=0 speed=0 step=000131ae menu=0000 key24=00000000 acc=(0,0)
MWPO marker: b'MWPO'  sites: 4eb9000b69004e71 4eb9000b6c00 4eb9000b6c10 4eb9000b6c20
ski idle     vbl=5965 PADST=01 PADJ=00 BTN=00 OLD=00000000 vec=(+0.0,+0.0) $24fba=0000 head=0 rate=0 speed=0 step=000131ae menu=0000 key24=00000000 acc=(0,0)
  [ski     stick] L(dhead,dvbl,rate,vecx,accx)=(-235, 105, -30, -5.0, -30) R=(242, 106, 3, 5.0, 10) U(vecy,accy)=(-5.0, -255) D=(5.0, -25) fire($24fba set,speed,speed+1.5s,after release)=(['0002'], 225, 264, '0000')
  [ski     pad  ] L(dhead,dvbl,rate,vecx,accx)=(-217, 106, -25, -5.0, -35) R=(230, 106, 22, 5.0, 25) U(vecy,accy)=(-5.0, -747) D=(5.0, -552) fire($24fba set,speed,speed+1.5s,after release)=(['0002'], 169, 211, '0000')
hold A       vbl=7718 PADST=01 PADJ=00 BTN=00 OLD=00000020 vec=(+0.0,+0.0) $24fba=0001 head=7 rate=0 speed=0 step=000131ae menu=0000 key24=00000000 acc=(0,-512)
rel A        vbl=7774 PADST=01 PADJ=00 BTN=00 OLD=00000000 vec=(+0.0,+0.0) $24fba=0000 head=7 rate=0 speed=0 step=000131ae menu=0000 key24=00000000 acc=(0,-512)
  key C     : VBLs traced 127  makes {'0x39': 1}  breaks {'0x39': 1}
  key n3    : VBLs traced 126  makes {'0x23': 1}  breaks {'0x23': 1}
  key pause : VBLs traced 152  makes {'0x19': 1}  breaks {'0x19': 1}
  flips/50 VBL after the first pause press: 0
  key pause : VBLs traced 102  makes {'0x19': 1}  breaks {'0x19': 1}
  flips/50 VBL after the second pause press: 7
  key n2    : VBLs traced 152  makes {'0x1f': 1}  breaks {'0x1f': 1}
snipe?       vbl=8913 PADST=01 PADJ=00 BTN=00 OLD=00000000 vec=(+0.0,+0.0) $24fba=0000 head=12 rate=0 speed=0 step=00013f36 menu=0000 key24=00000000 acc=(28,0)
  [snipe   stick] L(dhead,dvbl,rate,vecx,accx)=(898, 106, 0, -5.0, -477) R=(-896, 107, 0, 5.0, 3) U(vecy,accy)=(-5.0, -250) D=(5.0, -20) fire($24fba set,speed,speed+1.5s,after release)=(['0002'], 0, 0, '0000')
  [snipe   pad  ] L(dhead,dvbl,rate,vecx,accx)=(904, 106, 0, -5.0, -462) R=(-902, 106, 0, 5.0, -2) U(vecy,accy)=(-5.0, -240) D=(5.0, -25) fire($24fba set,speed,speed+1.5s,after release)=(['0002'], 0, 0, '0000')
  key n2    : VBLs traced 152  makes {'0x1f': 1}  breaks {'0x1f': 1}
ski again?   vbl=10831 PADST=01 PADJ=00 BTN=00 OLD=00000000 vec=(+0.0,+0.0) $24fba=0000 head=10 rate=0 speed=0 step=000131ae menu=0000 key24=00000000 acc=(0,0)
  key n1    : VBLs traced 151  makes {'0x32': 1}  breaks {'0x32': 1}
map?         vbl=11094 PADST=01 PADJ=00 BTN=00 OLD=00000000 vec=(+0.0,+0.0) $24fba=0000 head=10 rate=0 speed=0 step=000131ae menu=0000 key24=00000000 acc=(0,0)
map closed?  vbl=11369 PADST=01 PADJ=00 BTN=00 OLD=00000000 vec=(+0.0,+0.0) $24fba=0000 head=10 rate=0 speed=0 step=000131ae menu=0000 key24=00000000 acc=(0,0)
map closed   vbl=11538 PADST=01 PADJ=00 BTN=00 OLD=00000000 vec=(+0.0,+0.0) $24fba=0000 head=10 rate=0 speed=0 step=000131ae menu=0000 key24=00000000 acc=(0,0)
  flips/50 VBL back in the ski view: 2
buggy idle   vbl=11760 PADST=01 PADJ=00 BTN=00 OLD=00000000 vec=(+0.0,+0.0) $24fba=0000 head=10 rate=0 speed=0 step=0001359a menu=0000 key24=00000000 acc=(0,0)
  [buggy   stick] L(dhead,dvbl,rate,vecx,accx)=(-244, 107, -25, -5.0, -15) R=(249, 106, 25, 5.0, 0) U(vecy,accy)=(-5.0, -255) D=(5.0, -5)
  [buggy   pad  ] L(dhead,dvbl,rate,vecx,accx)=(-237, 106, -25, -5.0, -30) R=(242, 106, 25, 5.0, 20) U(vecy,accy)=(-5.0, -240) D=(5.0, -20)
  [buggy   pad  ] L(dhead,dvbl,rate,vecx,accx)=(-252, 106, -25, -5.0, 0) R=(232, 106, 25, 5.0, 35) U(vecy,accy)=(-5.0, -235) D=(5.0, -20) fire($24fba set,speed,speed+1.5s,after release)=(['0002'], 0, 0, '0000')
buggy C      vbl=13692 PADST=01 PADJ=00 BTN=00 OLD=00200000 vec=(+0.0,+0.0) $24fba=0000 head=13 rate=0 speed=0 step=0001359a menu=0000 key24=00000000 acc=(0,0)
glider idle  vbl=13804 PADST=01 PADJ=00 BTN=00 OLD=00000000 vec=(+0.0,+0.0) $24fba=0000 head=13 rate=0 speed=0 step=0001373c menu=0000 key24=00000000 acc=(0,0)
  [glider  stick] L(dhead,dvbl,rate,vecx,accx)=(-235, 106, 0, -5.0, -35) R=(232, 106, 32, 5.0, 40) U(vecy,accy)=(-5.0, -255) D=(5.0, -25)
  [glider  pad  ] L(dhead,dvbl,rate,vecx,accx)=(-230, 106, -28, -5.0, -30) R=(235, 107, 30, 5.0, 20) U(vecy,accy)=(-5.0, -245) D=(5.0, -30)
  [glider  pad  ] L(dhead,dvbl,rate,vecx,accx)=(-227, 106, -25, -5.0, -35) R=(240, 106, 25, 5.0, 10) U(vecy,accy)=(-5.0, -245) D=(5.0, -30) fire($24fba set,speed,speed+1.5s,after release)=(['0002'], 43, 93, '0000')
glider C     vbl=15740 PADST=01 PADJ=00 BTN=00 OLD=00200000 vec=(+0.0,+0.0) $24fba=0000 head=13 rate=0 speed=0 step=0001373c menu=0000 key24=00000000 acc=(0,0)
  key opt   : VBLs traced 119  makes {'0x2d': 1}  breaks {'0x2d': 1}
after X      vbl=16004 PADST=01 PADJ=00 BTN=00 OLD=00000000 vec=(+0.0,+0.0) $24fba=0000 head=13 rate=0 speed=0 step=0001373c menu=0001 key24=00000000 acc=(0,0)
total 320 s
```
Reading it: the pad gives the stick's vector exactly (`vecx/vecy = -5.0/+5.0`), the turn per tick `$15110` is 25 with both, heading changes of about +-230 in 106 VBL for both (differences = the 1 VBL granularity
of the key events and the 5 Hz tick); fire = `$24fba` 2 (left button) in every view; every pad key = exactly one make and one break (`C` `$39`, `3` `$23`, Pause `$19`, `2` `$1f`, `1` `$32`, Option `$2d`) with the
game acting once: Pause 0 flips/50 VBL then resumed; `2` ski -> sniper `$13f36` -> ski `$131ae`; `1` opens the main map (the map is click-driven: closed with the mouse, as without the patch); Option leaves the action mode
(`menu=0001`); A = `$24fba 1` (right button) stops walking.

### 3.3 Cold boot, Falcon TOS 4.04 4 MB, HD build, J mode (`coldpad.py falcon`) - the same script
```
boot_to_game J ok in 99 s, control mode J
after boot   vbl=5060 PADST=01 PADJ=00 BTN=00 OLD=00000000 vec=(+0.0,+0.0) $24fba=0000 head=0 rate=0 speed=0 step=000131ae menu=0000 key24=00000000 acc=(0,0)
MWPO marker: b'MWPO'  sites: 4eb9000b69004e71 4eb9000b6c00 4eb9000b6c10 4eb9000b6c20
ski idle     vbl=5215 PADST=01 PADJ=00 BTN=00 OLD=00000000 vec=(+0.0,+0.0) $24fba=0000 head=0 rate=0 speed=0 step=000131ae menu=0000 key24=00000000 acc=(0,0)
  [ski     stick] L(dhead,dvbl,rate,vecx,accx)=(-220, 106, -27, -5.0, -20) R=(222, 106, 20, 5.0, 60) U(vecy,accy)=(-5.0, -250) D=(5.0, -25) fire($24fba set,speed,speed+1.5s,after release)=(['0002'], 225, 265, '0000')
  [ski     pad  ] L(dhead,dvbl,rate,vecx,accx)=(-232, 106, -30, -5.0, -40) R=(226, 106, 27, 5.0, 25) U(vecy,accy)=(-5.0, -767) D=(5.0, -557) fire($24fba set,speed,speed+1.5s,after release)=(['0002'], 176, 218, '0000')
hold A       vbl=6966 PADST=01 PADJ=00 BTN=00 OLD=00000020 vec=(+0.0,+0.0) $24fba=0001 head=0 rate=0 speed=0 step=000131ae menu=0000 key24=00000000 acc=(0,-512)
rel A        vbl=7022 PADST=01 PADJ=00 BTN=00 OLD=00000000 vec=(+0.0,+0.0) $24fba=0000 head=0 rate=0 speed=0 step=000131ae menu=0000 key24=00000000 acc=(0,-512)
  key C     : VBLs traced 127  makes {'0x39': 1}  breaks {'0x39': 1}
  key n3    : VBLs traced 127  makes {'0x23': 1}  breaks {'0x23': 1}
  key pause : VBLs traced 152  makes {'0x19': 1}  breaks {'0x19': 1}
  flips/50 VBL after the first pause press: 0
  key pause : VBLs traced 102  makes {'0x19': 1}  breaks {'0x19': 1}
  flips/50 VBL after the second pause press: 25
  key n2    : VBLs traced 152  makes {'0x1f': 1}  breaks {'0x1f': 1}
snipe?       vbl=8158 PADST=01 PADJ=00 BTN=00 OLD=00000000 vec=(+0.0,+0.0) $24fba=0000 head=1020 rate=0 speed=0 step=00013f36 menu=0000 key24=00000000 acc=(0,0)
  [snipe   stick] L(dhead,dvbl,rate,vecx,accx)=(-122, 106, 0, -5.0, -505) R=(122, 106, 0, 5.0, -30) U(vecy,accy)=(-5.0, -250) D=(5.0, -25) fire($24fba set,speed,speed+1.5s,after release)=(['0002'], 0, 0, '0000')
  [snipe   pad  ] L(dhead,dvbl,rate,vecx,accx)=(900, 106, 0, -5.0, -505) R=(116, 106, 0, 5.0, -40) U(vecy,accy)=(-5.0, -255) D=(5.0, -40) fire($24fba set,speed,speed+1.5s,after release)=(['0002'], 0, 0, '0000')
  key n2    : VBLs traced 152  makes {'0x1f': 1}  breaks {'0x1f': 1}
ski again?   vbl=10074 PADST=01 PADJ=00 BTN=00 OLD=00000000 vec=(+0.0,+0.0) $24fba=0000 head=1022 rate=0 speed=0 step=000131ae menu=0000 key24=00000000 acc=(0,0)
  key n1    : VBLs traced 152  makes {'0x32': 1}  breaks {'0x32': 1}
map?         vbl=10336 PADST=01 PADJ=00 BTN=00 OLD=00000000 vec=(+0.0,+0.0) $24fba=0000 head=1022 rate=0 speed=0 step=000131ae menu=0000 key24=00000000 acc=(0,0)
map closed?  vbl=10610 PADST=01 PADJ=00 BTN=00 OLD=00000000 vec=(+0.0,+0.0) $24fba=0000 head=1022 rate=0 speed=0 step=000131ae menu=0000 key24=00000000 acc=(0,0)
map closed   vbl=10778 PADST=01 PADJ=00 BTN=00 OLD=00000000 vec=(+0.0,+0.0) $24fba=0000 head=1022 rate=0 speed=53 step=000131ae menu=0000 key24=00000000 acc=(0,-212)
  flips/50 VBL back in the ski view: 25
buggy idle   vbl=11000 PADST=01 PADJ=00 BTN=00 OLD=00000000 vec=(+0.0,+0.0) $24fba=0000 head=1022 rate=0 speed=146 step=0001359a menu=0000 key24=00000000 acc=(0,-212)
  [buggy   stick] L(dhead,dvbl,rate,vecx,accx)=(-230, 107, -25, -5.0, -45) R=(235, 106, 25, 5.0, 30) U(vecy,accy)=(-5.0, -275) D=(5.0, -10)
  [buggy   pad  ] L(dhead,dvbl,rate,vecx,accx)=(-242, 106, -25, -5.0, -10) R=(247, 106, 25, 5.0, 0) U(vecy,accy)=(-5.0, -250) D=(5.0, -5)
  [buggy   pad  ] L(dhead,dvbl,rate,vecx,accx)=(-232, 107, -25, -5.0, -30) R=(237, 106, 25, 5.0, 20) U(vecy,accy)=(-5.0, -245) D=(5.0, 27) fire($24fba set,speed,speed+1.5s,after release)=(['0002'], 0, 0, '0000')
buggy C      vbl=12933 PADST=01 PADJ=00 BTN=00 OLD=00200000 vec=(+0.0,+0.0) $24fba=0000 head=1012 rate=0 speed=0 step=0001359a menu=0000 key24=00000000 acc=(0,0)
glider idle  vbl=13045 PADST=01 PADJ=00 BTN=00 OLD=00000000 vec=(+0.0,+0.0) $24fba=0000 head=1012 rate=0 speed=0 step=0001373c menu=0000 key24=00000000 acc=(0,0)
  [glider  stick] L(dhead,dvbl,rate,vecx,accx)=(-242, 106, -25, -5.0, -20) R=(247, 106, 25, 5.0, 5) U(vecy,accy)=(-5.0, -250) D=(5.0, -25)
  [glider  pad  ] L(dhead,dvbl,rate,vecx,accx)=(-232, 106, -25, -5.0, -35) R=(237, 106, 25, 5.0, 25) U(vecy,accy)=(-5.0, -255) D=(5.0, -40)
  [glider  pad  ] L(dhead,dvbl,rate,vecx,accx)=(-247, 106, -25, -5.0, -5) R=(227, 107, 25, 5.0, 45) U(vecy,accy)=(-5.0, -255) D=(5.0, -45) fire($24fba set,speed,speed+1.5s,after release)=(['0002'], 43, 93, '0000')
glider C     vbl=14978 PADST=01 PADJ=00 BTN=00 OLD=00200000 vec=(+0.0,+0.0) $24fba=0000 head=1012 rate=0 speed=0 step=0001373c menu=0000 key24=00000000 acc=(0,0)
  key opt   : VBLs traced 127  makes {'0x2d': 1}  breaks {'0x2d': 1}
after X      vbl=15241 PADST=01 PADJ=00 BTN=00 OLD=00000000 vec=(+0.0,+0.0) $24fba=0000 head=1012 rate=0 speed=0 step=0001373c menu=0001 key24=00000000 acc=(0,0)
total 305 s
```
`PADST = 1` on the Falcon (DMA sound answers, SCU `$FF8E01` bus-errors, pad registers answer and idle high); no bus error (the guarded reads are the only faults), directions, fire and every key work exactly as on the STE.
(MW1's floppy build was not run on the Falcon: a floppy Falcon boot did not reach the Game Options screen in 500 s of the test, which the notes (tt.md: "Falcon not examined") do not cover; the HD build is how MW1 runs there.)

### 3.4 Cold boots on machines without pad ports (`coldpad.py tt|megaste|st|megast`; pad key B held while skiing: nothing reaches the game)
```
== tt
boot_to_game J ok in 95 s, control mode J
after boot   vbl=5805 PADST=ff PADJ=00 BTN=00 OLD=00000000 vec=(+0.0,+0.0) $24fba=0000 head=0 rate=0 speed=0 step=000131ae menu=0000 key24=00000000 acc=(0,0)
MWPO marker: b'MWPO'  sites: 4eb9000b69004e71 4eb9000b6c00 4eb9000b6c10 4eb9000b6c20
no pad ports on this machine: PADST must be $ff (the probe says no), nothing else to test
B held       vbl=6040 PADST=ff PADJ=00 BTN=00 OLD=00000000 vec=(+0.0,+0.0) $24fba=0000 head=0 rate=0 speed=0 step=000131ae menu=0000 key24=00000000 acc=(0,0)
total 102 s
== megaste
boot_to_game J ok in 105 s, control mode J
after boot   vbl=6390 PADST=ff PADJ=00 BTN=00 OLD=00000000 vec=(+0.0,+0.0) $24fba=0000 head=0 rate=0 speed=0 step=000131ae menu=0000 key24=00000000 acc=(0,0)
MWPO marker: b'MWPO'  sites: 4eb9000b69004e71 4eb9000b6c00 4eb9000b6c10 4eb9000b6c20
no pad ports on this machine: PADST must be $ff (the probe says no), nothing else to test
cost without pad ports: 181.1 cycles/VBL in the blob (incl. the displaced calls' jsr), 0.114 % of the profiled cycles
B held       vbl=6812 PADST=ff PADJ=00 BTN=00 OLD=00000000 vec=(+0.0,+0.0) $24fba=0000 head=0 rate=0 speed=0 step=000131ae menu=0000 key24=00000000 acc=(0,0)
total 115 s
== st
boot_to_game J ok in 114 s, control mode J
after boot   vbl=5806 PADST=ff PADJ=00 BTN=00 OLD=00000000 vec=(+0.0,+0.0) $24fba=0000 head=0 rate=0 speed=0 step=000131ae menu=0000 key24=00000000 acc=(0,0)
MWPO marker: b'MWPO'  sites: 4eb9000b69004e71 4eb9000b6c00 4eb9000b6c10 4eb9000b6c20
no pad ports on this machine: PADST must be $ff (the probe says no), nothing else to test
cost without pad ports: 134.4 cycles/VBL in the blob (incl. the displaced calls' jsr), 0.118 % of the profiled cycles
B held       vbl=6158 PADST=ff PADJ=00 BTN=00 OLD=00000000 vec=(+0.0,+0.0) $24fba=0000 head=0 rate=0 speed=0 step=000131ae menu=0000 key24=00000000 acc=(0,0)
total 124 s
== megast
boot_to_game J ok in 114 s, control mode J
after boot   vbl=5805 PADST=ff PADJ=00 BTN=00 OLD=00000000 vec=(+0.0,+0.0) $24fba=0000 head=0 rate=0 speed=0 step=000131ae menu=0000 key24=00000000 acc=(0,0)
MWPO marker: b'MWPO'  sites: 4eb9000b69004e71 4eb9000b6c00 4eb9000b6c10 4eb9000b6c20
no pad ports on this machine: PADST must be $ff (the probe says no), nothing else to test
cost without pad ports: 134.4 cycles/VBL in the blob (incl. the displaced calls' jsr), 0.119 % of the profiled cycles
B held       vbl=6157 PADST=ff PADJ=00 BTN=00 OLD=00000000 vec=(+0.0,+0.0) $24fba=0000 head=0 rate=0 speed=0 step=000131ae menu=0000 key24=00000000 acc=(0,0)
total 124 s
```
`PADST = $ff` on all four (TT with `--mmu true`: the SCU answers, so the pad registers are never touched; Mega STE: SCU answers; ST/Mega ST: DMA sound bus-errors): the probe says no, `MWPO`, no bus error, the ski view runs, and the pad key changes nothing.

### 3.5 Floppy build (`build --floppy --only <default set> floppy_secbypass floppy_driveb jag_*`, MWA in A and MWB in B from power-on, STE 1 MB; `floppy_pad.py ste`)
```
options reached True 65 s; marker b'MWPO'
control mode J
after PLAY   vbl=6096 PADST=01 PADJ=00 BTN=00 OLD=00000000 vec=(+0.0,+0.0) $24fba=0000 head=0 rate=0 speed=0 step=00000000 menu=0001 key24=00b9ffff ptr=(150,155)
team right   vbl=6157 PADST=01 PADJ=08 BTN=00 OLD=00000008 vec=(+5.0,+0.0) $24fba=0000 head=0 rate=0 speed=0 step=00000000 menu=0001 key24=00b9ffff ptr=(310,155)
team down    vbl=6238 PADST=01 PADJ=02 BTN=00 OLD=00000002 vec=(+0.0,+5.0) $24fba=0000 head=0 rate=0 speed=0 step=00000000 menu=0001 key24=00b9ffff ptr=(310,198)
in_ski True 279 s
ski          vbl=13965 PADST=01 PADJ=00 BTN=00 OLD=00000000 vec=(+0.0,+0.0) $24fba=0000 head=0 rate=0 speed=0 step=000131ae menu=0000 key24=00000000 ptr=(135,170)
hold left    vbl=14046 PADST=01 PADJ=04 BTN=00 OLD=00000004 vec=(-5.0,+0.0) $24fba=0000 head=-162 rate=-3 speed=0 step=000131ae menu=0000 key24=00000000 ptr=(135,170)
rel left     vbl=14092 PADST=01 PADJ=00 BTN=00 OLD=00000000 vec=(+0.0,+0.0) $24fba=0000 head=-210 rate=0 speed=0 step=000131ae menu=0000 key24=00000000 ptr=(135,170)
hold right   vbl=14173 PADST=01 PADJ=08 BTN=00 OLD=00000008 vec=(+5.0,+0.0) $24fba=0000 head=-56 rate=37 speed=0 step=000131ae menu=0000 key24=00000000 ptr=(135,170)
rel right    vbl=14219 PADST=01 PADJ=00 BTN=00 OLD=00000000 vec=(+0.0,+0.0) $24fba=0000 head=-10 rate=0 speed=0 step=000131ae menu=0000 key24=00000000 ptr=(135,170)
hold up      vbl=14299 PADST=01 PADJ=01 BTN=00 OLD=00000001 vec=(+0.0,-5.0) $24fba=0000 head=-10 rate=0 speed=0 step=000131ae menu=0000 key24=00000000 ptr=(135,170)
rel up       vbl=14345 PADST=01 PADJ=00 BTN=00 OLD=00000000 vec=(+0.0,+0.0) $24fba=0000 head=-10 rate=0 speed=0 step=000131ae menu=0000 key24=00000000 ptr=(135,170)
hold down    vbl=14426 PADST=01 PADJ=02 BTN=00 OLD=00000002 vec=(+0.0,+5.0) $24fba=0000 head=-10 rate=0 speed=0 step=000131ae menu=0000 key24=00000000 ptr=(135,170)
rel down     vbl=14472 PADST=01 PADJ=00 BTN=00 OLD=00000000 vec=(+0.0,+0.0) $24fba=0000 head=-10 rate=0 speed=0 step=000131ae menu=0000 key24=00000000 ptr=(135,170)
hold B       vbl=14628 PADST=01 PADJ=00 BTN=01 OLD=00002000 vec=(+0.0,+0.0) $24fba=0002 head=-10 rate=0 speed=263 step=000131ae menu=0000 key24=00000000 ptr=(135,170)
hold A       vbl=14760 PADST=01 PADJ=00 BTN=00 OLD=00000020 vec=(+0.0,+0.0) $24fba=0001 head=-10 rate=0 speed=0 step=000131ae menu=0000 key24=00000000 ptr=(135,170)
hold 2 (S)   vbl=14917 PADST=01 PADJ=00 BTN=00 OLD=00080000 vec=(+0.0,+0.0) $24fba=0000 head=1018 rate=0 speed=0 step=00013f36 menu=0000 key24=00000000 ptr=(135,170)
snipe?       vbl=14973 PADST=01 PADJ=00 BTN=00 OLD=00000000 vec=(+0.0,+0.0) $24fba=0000 head=1008 rate=0 speed=0 step=00013f36 menu=0000 key24=00000000 ptr=(135,170)
ski again    vbl=15130 PADST=01 PADJ=00 BTN=00 OLD=00000000 vec=(+0.0,+0.0) $24fba=0000 head=1010 rate=0 speed=0 step=000131ae menu=0000 key24=00000000 ptr=(135,170)
after X      vbl=15312 PADST=01 PADJ=00 BTN=00 OLD=00000000 vec=(+0.0,+0.0) $24fba=0000 head=1010 rate=0 speed=0 step=000131ae menu=0001 key24=00000000 ptr=(135,170)
total 306 s
```
Same behaviour from the floppy: probe after PLAY, pad drives the menu pointer (Team screen), ski view: directions, fire, A, 2 (S) and back, Option (X: `menu = 1`).

## 4. Midwinter's IKBD handler and misframed packets (question from the lead)
Evidence: `m68dis ram_ski_walk.bin`. The game's ISR `$6400` is a byte state machine (`$2c31c`: <0 joystick byte follows, >0 bytes left, 0 idle) and **never range-checks dx/dy**, but
nothing that consumes them can walk through memory:
* mouse packet (`$f8-$fb` header): `$664a` sign-extends the two bytes (`ext.w`, `swap`) and `jmp ($62ac + 4*$62b8)`: menus (`$62b8 = 0`) `$66ce` and `$62b8 = 1` `$6712` **clamp the pointer**
  (`$66e0: cmp.w #$c6,d0 / bcs / move.w #$c6,d0`, `$66fe: cmp.w #$136,d1 ...`, `$6742-$6750` the same with a lower limit of 3); in game (`$62b8 = 2`) `$66c0` only does `add.l d1,$24faa / add.l d0,$24fae`,
  and the consumers are bounded (ski/buggy/glider `$12fe2`: clamp +-512, our `p5_ctl_turn`: +-200 counts; sniper `$14056..$14060`: `andi.w #$3fe,d0` on the heading and the Y clamp `$1445a` with `d1 = $200`).
  The pointer is drawn by the game's own loop from the clamped `$24fa2/$24fa6`, not from the ISR (the unclamped `sub_012b12`, `add.w d0,$24fa2`, has no caller or xref in the dump).
* joystick (`$ff` header, `$6510`): one byte to `$2c328`, only its low bits are decoded (`$65e2..`), nothing is an index or address.
* scancodes (bytes < `$f6`): `$64ac: tst.b d0 / bmi $64cc`, so the make path indexes `$2c29a + d0` with `d0 < $80` (128-byte table), and the break path masks to 7 bits (`$392: andi.w #$7f,d0`).
* a bad header (`$f6 $f7 $fc $fd $fe`) arms `$2c31c = 7 / $2c322 = $fa` (`$645c..`) and discards the next 7 bytes: it can swallow genuine bytes (a stall, not a crash).
* The one thing a misframed byte can do is **`$e5` / `$e6` in scancode position**: PP's HAGA hook `$392` treats them as the save-state keys (`cmp.b #$e5,d0 / beq $3cc`, `cmp.b #$e6,d0 / beq $3a6`) and runs PP's
  save/load-state code (movem + disk access) [INFERENCE: what that code does to a half-initialised game was not run]. Not a memory overrun.
So: no crash from a split mouse reply on the `[evidence]` paths above; garbage dx/dy turns/moves a little for one tick, and a stray `$e5/$e6` could trigger the save-state hook.
`jag_*` does not touch the IKBD path (it writes `$2c32c`, the new-byte flag, and the key words only, never a packet byte).

## 5. Limits / not done
* **No real STE, no real pad.** The pad matrix comes from documents and from Hatari's `joy.c`; a real Jaguar pad on a real STE or Falcon
  must be tried before shipping (study section 5). The 20 ms select-to-read gap is far above any settle time in the study (10-20 us, 100 us identification).
* **Falcon**: gets the pad since the second version (section 3.3). Real Falcon hardware is untested (the SCU assumption above); the round-robin read needs no timing assumption.
* **K and M mode**: untouched (the pad is read as released). With only a pad, choose J at the Game Options screen (that screen needs the mouse; the pad is live from PLAY on, `$2c178` is copied at PLAY).
* The default stays `no` (the lead decides): on a pad-less machine the cost is 134-181 cycles/VBL (0.08-0.11 %) and the no-pad gate is identical, on a machine with ports ~457 cycles/VBL (0.29 %); a press shorter than 80 ms can be missed (12.5 Hz sampling per switch).
* A and Option are mapped to game-state-changing keys (`>` stops, X leaves the action mode); `*`, `#`, `0`, `4`-`9` are free (`keymap` in `jag_vbl.s` takes `{bit, scancode}` pairs).
* Suggested user-doc line for `PATCHES.TXT`/`README` when `jag_*` become default (not edited: not my file): "Atari Jaguar pads in the STE/Falcon controller ports work as the joystick in
  Joystick mode (STE only): D-pad = stick, B = fire, A = right button, C = Space, Option = X, Pause = P, 1/2/3 = M/S/H; other machines are unchanged."
