# MW1: Atari Jaguar pad on the STE enhanced joystick ports (patches `jag_vbl` `jag_mrg` `jag_btn` `jag_rmp`, default: no)

Source study: `reports/jaguar_pad_study.md` (protocol, detection, the proposed MW1 map). Everything below is raw output of this session (Hatari 2.6.1,
`tools/m68dis.py` on `work/dumps/ram_ski_walk.bin`, the test scripts in `work/jagpad/`) or marked `[INFERENCE]`. **No real STE with a pad was available: Hatari's own
pad emulation (`joy.c`) is the only evidence for the electrical side.**

## 1. What changed (four 6-8 byte splices, one blob of 568 bytes)

All four are needed together; each stub is self-contained and harmless alone (it reads state bytes that are 0 without `jag_vbl`).

| patch | site | original | new | role |
|---|---|---|---|---|
| `jag_vbl` | `$61e2` (8 B) | `bsr.w $65c0` / `bsr.w $652e` (VBL: joystick re-read, key poll) | `jsr $b6900.l` / `nop` | poll the pad, then the two displaced calls (as `jsr`) |
| `jag_mrg` | `$65e2` (6 B) | `move.w $2c328.l,d2` | `jsr $b6c00.l` | the latched IKBD joystick byte `OR`ed with `PADJ` (pad directions) |
| `jag_btn` | `$665e` (6 B) | `move.b (a0),d2` / `andi.w #3,d2` | `jsr $b6c10.l` | button byte of the input funnel `OR`ed with `PADBTN` (pad fire) |
| `jag_rmp` | `$6696` (6 B) | `move.b $2c32e.l,d2` | `jsr $b6c20.l` | J-mode fire remap: `$f9` when `PADBTN` is set |

Blob map: code `$B6900-$B6B37`, data `$B6BF0-$B6BF7` (`PADST` byte, `PADJ` byte, `PADBTN` byte, `PADOLD` long at `$B6BF4`), stubs `$B6C00/$B6C10/$B6C20`.
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

### 1.3 Reading the pad (per VBL; `poll` in `jag_vbl.s`)
Select words `$FFEE/$FFDD/$FFBB/$FF77` = group 4/3/2/1 on **both** ports at once, then `$FFFF`; each read is `$FF9200` and `$FF9202` as **words** (a byte read of `$FF9200`
bus-errors on a real STE, study 1.3); the two ports are ANDed (low = pressed) so a pad in either port works. The settle time between a select write and its read is the
decode of the previous group plus a `dbra`: 23 us for the first group and about 23 us for the others at 8 MHz (study 1.2 plans for 20 us; a passive pad needs less).

### 1.4 Detection (first VBL with `$2c178 != 0`, cached in `PADST`: 0 unprobed / 1 pad ports / `$ff` none)
1. **68000 only**: the brief-extension scale trick of `p4_blit_sky` / `cpulib.s` (`dc.w $43f0,$0200` gives 1 on a 68000). A 68020+ (TT, Falcon, accelerators) is never touched:
   `PADST = $ff` at once. (The Falcon is study "phase 2": it has the same ports, but its detection (no SCU) could only be observed in Hatari.)
2. Guarded byte reads (vector `$8` swapped, `a7` restored by the handler, the pattern of `p4_blit_sky`): `$FF8901` (DMA sound: bus error on ST/Mega ST), `$FF8A3C` (blitter:
   bus error on a plain ST) must answer, `$FF8E21` (Mega STE cache register) must bus-error. That leaves the STE.
3. Guarded word write `$FFFF -> $FF9202` and word reads of `$FF9202`/`$FF9200`: no bus error, high byte of `$FF9202` = `$FF`, low nibble of `$FF9200` = `$F` (a Mega STE reads
   `$FFF9`, a TT `$3F03`: refused; study 1.3).
Without a pad port the VBL cost is `move.b PADST,d0 / bmi` plus the two `jsr` replacing the two `bsr.w`.

## 2. Cost

Hatari STE cold boot, `work/jagpad/prof_pad.py` (profile cycles over 100 VBL, 1mb_ski_stand_J + live set; pad emulated on host keys, nothing / B / Left held):
```
pad idle      :    977.2 cycles/VBL in $b6900-$b6c3f = 0.869 % of the profiled cycles (112483/VBL profiled; VBL = 160256 cycles = 0.610 %)
pad B held    :    980.0 cycles/VBL in $b6900-$b6c3f = 0.870 % of the profiled cycles (112680/VBL profiled; VBL = 160256 cycles = 0.612 %)
pad Left held :    977.2 cycles/VBL in $b6900-$b6c3f = 0.869 % of the profiled cycles (112440/VBL profiled; VBL = 160256 cycles = 0.610 %)
hot addresses (last run, address: cycles): [(747848, 13720), (747892, 4480), (747936, 4480), (747980, 4480), (747888, 1680), (747932, 1680), (747976, 1680), (748020, 1680)]
```
* **With pad ports (STE): about 977-980 cycles per VBL by Hatari's profiler = 0.61 % of the 160256 cycles of a PAL VBL**, constant while buttons are held (the state is polled every VBL; the
  key/direction handling only runs on a change). By 68000 instruction timing (tally of the idle path in `jag_vbl.s`: 164 + 3 x 54 cycles of `dbra` waits, 4 x 116 of decode, 4 select writes,
  8 register reads, the state compare and the call overhead) the same path is **about 1130 cycles = 0.70 %**; Hatari's profiler counts a taken `dbra` a little below 10 (13720 / 100 VBL / 16 iterations
  = 8.6), which is the difference [INFERENCE: not checked against the Hatari timing tables]. Either way it is below the 1 % target; most of it is the 4 x 23 us settle time.
* **Without pad ports** (profile of the blob in the ski view, cold boots, section 3): ST 134.4 cycles/VBL, Mega ST 134.4, Mega STE 181.0 (the figure includes the three stubs that
  replace three instructions of the game; the TT and Falcon were not profiled, they take the same `move.b PADST` + `bmi` path as the ST). That is 0.08-0.11 % of a VBL.
* `mw1ab.py` reports "cycles per frame" for the J snapshot +1.50 % (760744 -> 772157), and -1.25 % (busy) / -0.23 % (turn) for M snapshots where the pad code is not even entered: that
  figure is dominated by the phase of the 5 Hz world tick against the VBL (flips per 1000 VBL change 204 -> 201 and 299 -> 302), so it is not a measure of the poll cost; the profile above is.

## 3. Tests (all raw logs in `work/jagpad/`)
Hatari pad emulation: `work/jagpad/pad.cfg` maps pad A to host keys (w/s/a/d = directions, z = A, x = B, v = C, o = Option, p = Pause, 1/2/3 = keypad 1/2/3) and ST joystick 1 ("the
real stick", IKBD path) to the cursor keys + Right Ctrl, so the same run can drive the game with the stick and with the pad (`--joy1 keys --configfile pad.cfg`). A held host key is a held
pad button (study 2.1). Build under test: `build/jag` = every default patch + `jag_*` (`mw1patch.py build --only <default set> jag_vbl jag_mrg jag_btn jag_rmp`, 58 patches + 2 file patches), cold
boot of the HD build (`RUNME.TOS` from the GEMDOS drive), control mode J, `tools/mw1.py boot_to_game('J')` (Options -> J -> PLAY -> Team -> Stark -> Decisions -> Skiing).

### 3.1 No pad: pixel identity (`work/jagpad/ab_seq.py` = `mw1ab.py` with one Hatari at a time; base = default set, patched = default set + jag; Hatari STE, no key pressed)
```
stand --flips 8: IDENTICAL; flips/1000VBL 220 -> 220; cycles/frame 708338 -> 708389 (+51, +0.01 %)
stand --flips 40: IDENTICAL
walk --flips 8: IDENTICAL; flips/1000VBL 445 -> 445; cycles/frame 350592 -> 350535 (-57, -0.02 %)
walk --flips 40: IDENTICAL
turn --flips 8: IDENTICAL; flips/1000VBL 331 -> 331; cycles/frame 473747 -> 472661 (-1086, -0.23 %)
turn --flips 40: IDENTICAL
busy --flips 8: IDENTICAL; flips/1000VBL 299 -> 302; cycles/frame 523830 -> 517280 (-6550, -1.25 %)
busy --flips 40: IDENTICAL
1mb_ski_stand_J --flips 8: IDENTICAL; flips/1000VBL 204 -> 201; cycles/frame 760744 -> 772157 (+11414, +1.50 %)
1mb_ski_stand_J --flips 40: IDENTICAL
ALL IDENTICAL
```
`1mb_ski_stand_J` is a J-mode snapshot in which the pad poll runs every VBL (the probe runs in it right after the live patch is applied at a flip): all three screen buffers identical
after 8 and 40 flips. In the M-mode snapshots `jag_vbl` only executes `move.b PADST` / `tst.w $2c178`.

### 3.2 Cold boot, STE 1 MB TOS 1.62, J mode, pad on host keys (`coldpad.py ste`)
Stick and pad run the same input script in the same session, in the ski view, on the sniper view (pad key 2 = S), and with the buggy and glider step handlers forced
(`w $12d5e $1359a / $1373c`: no save reaches a vehicle, as in `p5_controls.md`). Columns: `L` = Left held 2.0 s: heading change, VBLs, `$15110` (turn of the last step),
vector X, `$24faa` hi word; `R` the same for Right; `U`/`D` = vector Y and `$24fae` hi word; `fire` = the set of `$24fba` values over 6 samples, speed at 0.8 s and 2.3 s, `$24fba` after release.
```
config ste {'machine': 'ste', 'memsize_kb': 1024} ['--joy1', 'keys', '--configfile', '/home/ryan/Code/AtariST/gamebench/games/in_progress/midwinter/work/jagpad/pad.cfg']
boot_to_game J ok in 114 s, control mode J
after boot   vbl=5803 PADST=01 PADJ=00 BTN=00 OLD=00000000 vec=(+0.0,+0.0) $24fba=0000 head=0 rate=0 speed=0 step=000131ae menu=0000 key24=00000000 acc=(0,0)
MWPO marker: b'MWPO'  sites: 4eb9000b69004e71 4eb9000b6c00 4eb9000b6c10 4eb9000b6c20
ski idle     vbl=5953 PADST=01 PADJ=00 BTN=00 OLD=00000000 vec=(+0.0,+0.0) $24fba=0000 head=0 rate=0 speed=0 step=000131ae menu=0000 key24=00000000 acc=(0,0)
  [ski     stick] L(dhead,dvbl,rate,vecx,accx)=(-230, 106, -2, -5.0, -35) R=(231, 106, 32, 5.0, 10) U(vecy,accy)=(-5.0, -245) D=(5.0, -15) fire($24fba set,speed,speed+1.5s,after release)=(['0002'], 225, 265, '0000')
  [ski     pad  ] L(dhead,dvbl,rate,vecx,accx)=(-221, 106, -22, -5.0, -20) R=(222, 106, 25, 5.0, 40) U(vecy,accy)=(-5.0, -767) D=(5.0, -542) fire($24fba set,speed,speed+1.5s,after release)=(['0002'], 184, 221, '0000')
hold A       vbl=7706 PADST=01 PADJ=00 BTN=00 OLD=00000020 vec=(+0.0,+0.0) $24fba=0001 head=5 rate=0 speed=0 step=000131ae menu=0000 key24=00000000 acc=(0,-512)
rel A        vbl=7762 PADST=01 PADJ=00 BTN=00 OLD=00000000 vec=(+0.0,+0.0) $24fba=0000 head=5 rate=0 speed=0 step=000131ae menu=0000 key24=00000000 acc=(0,-512)
  key C     : VBLs traced 126  makes {'0x39': 1}  breaks {'0x39': 1}
  key n3    : VBLs traced 127  makes {'0x23': 1}  breaks {'0x23': 1}
  key pause : VBLs traced 152  makes {'0x19': 1}  breaks {'0x19': 1}
  flips/50 VBL after the first pause press: 0
  key pause : VBLs traced 102  makes {'0x19': 1}  breaks {'0x19': 1}
  flips/50 VBL after the second pause press: 6
  key n2    : VBLs traced 152  makes {'0x1f': 1}  breaks {'0x1f': 1}
snipe?       vbl=8899 PADST=01 PADJ=00 BTN=00 OLD=00000000 vec=(+0.0,+0.0) $24fba=0000 head=10 rate=0 speed=0 step=00013f36 menu=0000 key24=00000000 acc=(20,0)
  [snipe   stick] L(dhead,dvbl,rate,vecx,accx)=(896, 106, 0, -5.0, -485) R=(120, 106, 0, 5.0, -10) U(vecy,accy)=(-5.0, -255) D=(5.0, -35) fire($24fba set,speed,speed+1.5s,after release)=(['0002'], 0, 0, '0000')
  [snipe   pad  ] L(dhead,dvbl,rate,vecx,accx)=(896, 106, 0, -5.0, -485) R=(118, 106, 0, 5.0, -10) U(vecy,accy)=(-5.0, -255) D=(5.0, -20) fire($24fba set,speed,speed+1.5s,after release)=(['0002'], 0, 0, '0000')
  key n2    : VBLs traced 151  makes {'0x1f': 1}  breaks {'0x1f': 1}
ski again?   vbl=10815 PADST=01 PADJ=00 BTN=00 OLD=00000000 vec=(+0.0,+0.0) $24fba=0000 head=6 rate=0 speed=0 step=000131ae menu=0000 key24=00000000 acc=(0,0)
  key n1    : VBLs traced 152  makes {'0x32': 1}  breaks {'0x32': 1}
map?         vbl=11077 PADST=01 PADJ=00 BTN=00 OLD=00000000 vec=(+0.0,+0.0) $24fba=0000 head=6 rate=0 speed=0 step=000131ae menu=0000 key24=00000000 acc=(0,0)
map closed?  vbl=11352 PADST=01 PADJ=00 BTN=00 OLD=00000000 vec=(+0.0,+0.0) $24fba=0000 head=6 rate=0 speed=0 step=000131ae menu=0000 key24=00000000 acc=(0,0)
map closed   vbl=11520 PADST=01 PADJ=00 BTN=00 OLD=00000000 vec=(+0.0,+0.0) $24fba=0000 head=6 rate=0 speed=0 step=000131ae menu=0000 key24=00000000 acc=(0,0)
  flips/50 VBL back in the ski view: 2
buggy idle   vbl=11742 PADST=01 PADJ=00 BTN=00 OLD=00000000 vec=(+0.0,+0.0) $24fba=0000 head=6 rate=0 speed=0 step=0001359a menu=0000 key24=00000000 acc=(0,0)
  [buggy   stick] L(dhead,dvbl,rate,vecx,accx)=(-252, 107, -25, -5.0, 0) R=(235, 106, 25, 5.0, 35) U(vecy,accy)=(-5.0, -255) D=(5.0, -5)
  [buggy   pad  ] L(dhead,dvbl,rate,vecx,accx)=(-245, 106, -25, -5.0, -15) R=(250, 106, 25, 5.0, 0) U(vecy,accy)=(-5.0, -250) D=(5.0, -5)
  [buggy   pad  ] L(dhead,dvbl,rate,vecx,accx)=(-235, 106, -25, -5.0, -30) R=(240, 106, 25, 5.0, 20) U(vecy,accy)=(-5.0, -255) D=(5.0, -5) fire($24fba set,speed,speed+1.5s,after release)=(['0002'], 0, 0, '0000')
buggy C      vbl=13675 PADST=01 PADJ=00 BTN=00 OLD=00200000 vec=(+0.0,+0.0) $24fba=0000 head=6 rate=0 speed=0 step=0001359a menu=0000 key24=00000000 acc=(0,0)
glider idle  vbl=13787 PADST=01 PADJ=00 BTN=00 OLD=00000000 vec=(+0.0,+0.0) $24fba=0000 head=6 rate=0 speed=0 step=0001373c menu=0000 key24=00000000 acc=(0,0)
  [glider  stick] L(dhead,dvbl,rate,vecx,accx)=(-242, 106, -25, -5.0, -20) R=(247, 106, 25, 5.0, 5) U(vecy,accy)=(-5.0, -250) D=(5.0, -30)
  [glider  pad  ] L(dhead,dvbl,rate,vecx,accx)=(-232, 107, -25, -5.0, -40) R=(240, 106, 25, 5.0, 25) U(vecy,accy)=(-5.0, -255) D=(5.0, -25)
  [glider  pad  ] L(dhead,dvbl,rate,vecx,accx)=(-247, 107, -25, -5.0, -10) R=(230, 106, 25, 5.0, 45) U(vecy,accy)=(-5.0, -250) D=(5.0, -20) fire($24fba set,speed,speed+1.5s,after release)=(['0002'], 50, 100, '0000')
glider C     vbl=15720 PADST=01 PADJ=00 BTN=00 OLD=00200000 vec=(+0.0,+0.0) $24fba=0000 head=6 rate=0 speed=0 step=0001373c menu=0000 key24=00000000 acc=(0,5)
  key opt   : VBLs traced 119  makes {'0x2d': 1}  breaks {'0x2d': 1}
after X      vbl=15984 PADST=01 PADJ=00 BTN=00 OLD=00000000 vec=(+0.0,+0.0) $24fba=0000 head=6 rate=0 speed=0 step=0001373c menu=0001 key24=00000000 acc=(0,5)
total 320 s
```
Reading it:
* **Directions**: the pad gives the stick's vector exactly (`vecx = -5.0 / +5.0`, `vecy = -5.0 / +5.0`), the turn per tick `$15110` is 25 (the p5 rate, 125 units/s) with both, and the heading
  change in 106 VBL is -230/-221 (stick/pad) and +231/+222 in the ski view, -252/-245 and +235/+250 for the buggy, -242/-232 and +247/+240 for the glider: the differences are the 1 VBL
  granularity of the xdotool key events and of the 5 Hz tick, not a different gain. (`$24fae`, the Y lever, is a persistent position: it differs by what the previous run left in it.)
* **Fire**: `$24fba` = 2 (left button) for the stick and for the pad in every view, speed rises from standing (walking starts), `$24fba` = 0 after release.
* **Keys** (`trace_keys`: a breakpoint at `$B6900` dumps the key table `$2c29a` and `$2c324/6` at every VBL): every pad key gives exactly **one make and one break** of its scancode
  (`C` `$39`, `3` `$23`, Pause `$19`, `2` `$1f`, `1` `$32`, Option `$2d`), held for 1-2 s. The game acts on them once: Pause: the first press stops the flips (0 per 50 VBL), the second resumes them;
  `2` toggles ski -> sniper (`$12d5e = $13f36`) and back (`$131ae`); `1` opens the main map (screenshot `/tmp/jag_cold_map.png`: the map and its buttons; the pad fire clicks its RELIEF
  button, `/tmp/jag_map_closed2.png`) and the original needs the mouse to close it; Option (X) leaves the action mode (`menu=0001`). A (`>`) shows `$24fba = 1` (right button) and stops walking.
* The same keys through the Hatari keyboard behave the same way (`map_probe.py real`: the keyboard `m` opens the same map).

### 3.3 Cold boots on machines without pad ports (`coldpad.py st|megast|megaste|tt|falcon`; pad key B held while skiing: nothing reaches the game)
```
== st
boot_to_game J ok in 113 s, control mode J
after boot   vbl=5796 PADST=ff PADJ=00 BTN=00 OLD=00000000 vec=(+0.0,+0.0) $24fba=0000 head=0 rate=0 speed=0 step=000131ae menu=0000 key24=00000000 acc=(0,0)
MWPO marker: b'MWPO'  sites: 4eb9000b69004e71 4eb9000b6c00 4eb9000b6c10 4eb9000b6c20
no pad ports on this machine: PADST must be $ff (the probe says no), nothing else to test
cost without pad ports: 134.4 cycles/VBL in the blob (incl. the displaced calls' jsr), 0.119 % of the profiled cycles
B held       vbl=6148 PADST=ff PADJ=00 BTN=00 OLD=00000000 vec=(+0.0,+0.0) $24fba=0000 head=0 rate=0 speed=0 step=000131ae menu=0000 key24=00000000 acc=(0,0)
total 123 s
== megast
boot_to_game J ok in 114 s, control mode J
after boot   vbl=5843 PADST=ff PADJ=00 BTN=00 OLD=00000000 vec=(+0.0,+0.0) $24fba=0000 head=0 rate=0 speed=0 step=000131ae menu=0000 key24=00000000 acc=(0,0)
MWPO marker: b'MWPO'  sites: 4eb9000b69004e71 4eb9000b6c00 4eb9000b6c10 4eb9000b6c20
no pad ports on this machine: PADST must be $ff (the probe says no), nothing else to test
cost without pad ports: 134.4 cycles/VBL in the blob (incl. the displaced calls' jsr), 0.119 % of the profiled cycles
B held       vbl=6196 PADST=ff PADJ=00 BTN=00 OLD=00000000 vec=(+0.0,+0.0) $24fba=0000 head=0 rate=0 speed=0 step=000131ae menu=0000 key24=00000000 acc=(0,0)
total 124 s
== megaste
boot_to_game J ok in 105 s, control mode J
after boot   vbl=6396 PADST=ff PADJ=00 BTN=00 OLD=00000000 vec=(+0.0,+0.0) $24fba=0000 head=0 rate=0 speed=0 step=000131ae menu=0000 key24=00000000 acc=(0,0)
MWPO marker: b'MWPO'  sites: 4eb9000b69004e71 4eb9000b6c00 4eb9000b6c10 4eb9000b6c20
no pad ports on this machine: PADST must be $ff (the probe says no), nothing else to test
cost without pad ports: 181.0 cycles/VBL in the blob (incl. the displaced calls' jsr), 0.115 % of the profiled cycles
B held       vbl=6818 PADST=ff PADJ=00 BTN=00 OLD=00000000 vec=(+0.0,+0.0) $24fba=0000 head=0 rate=0 speed=0 step=000131ae menu=0000 key24=00000000 acc=(0,0)
total 115 s
== tt
boot_to_game J ok in 95 s, control mode J
after boot   vbl=5803 PADST=ff PADJ=00 BTN=00 OLD=00000000 vec=(+0.0,+0.0) $24fba=0000 head=0 rate=0 speed=0 step=000131ae menu=0000 key24=00000000 acc=(0,0)
MWPO marker: b'MWPO'  sites: 4eb9000b69004e71 4eb9000b6c00 4eb9000b6c10 4eb9000b6c20
no pad ports on this machine: PADST must be $ff (the probe says no), nothing else to test
B held       vbl=6038 PADST=ff PADJ=00 BTN=00 OLD=00000000 vec=(+0.0,+0.0) $24fba=0000 head=0 rate=0 speed=0 step=000131ae menu=0000 key24=00000000 acc=(0,0)
total 102 s
== falcon
boot_to_game J ok in 99 s, control mode J
after boot   vbl=5055 PADST=ff PADJ=00 BTN=00 OLD=00000000 vec=(+0.0,+0.0) $24fba=0000 head=0 rate=0 speed=0 step=000131ae menu=0000 key24=00000000 acc=(0,0)
MWPO marker: b'MWPO'  sites: 4eb9000b69004e71 4eb9000b6c00 4eb9000b6c10 4eb9000b6c20
no pad ports on this machine: PADST must be $ff (the probe says no), nothing else to test
B held       vbl=5251 PADST=ff PADJ=00 BTN=00 OLD=00000000 vec=(+0.0,+0.0) $24fba=0000 head=0 rate=0 speed=0 step=000131ae menu=0000 key24=00000000 acc=(0,0)
total 106 s
```
`PADST = $ff` on all five: the probe says no, `MWPO`, no bus error (the machines reach the ski view; the TT with `--mmu true`, screenshot `/tmp/jag_cold_tt.png`), and the
pad key (B) changes nothing (`PADJ = BTN = 0`, `$24fba = 0`). Mega STE and TT are the machines whose `$FF9200` returns DIP-switch bits (study 1.3): the registers are never read there.

### 3.4 Floppy build (`build --floppy --only <default set> floppy_secbypass floppy_driveb jag_*`, MWA in A and MWB in B from power-on, STE 1 MB; `floppy_pad.py`)
```
options reached True 65 s; marker b'MWPO'
control mode J
after PLAY   vbl=6099 PADST=01 PADJ=00 BTN=00 OLD=00000000 vec=(+0.0,+0.0) $24fba=0000 head=0 rate=0 speed=0 step=00000000 menu=0001 key24=00b9ffff ptr=(150,155)
team right   vbl=6159 PADST=01 PADJ=08 BTN=00 OLD=00000008 vec=(+5.0,+0.0) $24fba=0000 head=0 rate=0 speed=0 step=00000000 menu=0001 key24=00b9ffff ptr=(310,155)
team down    vbl=6241 PADST=01 PADJ=02 BTN=00 OLD=00000002 vec=(+0.0,+5.0) $24fba=0000 head=0 rate=0 speed=0 step=00000000 menu=0001 key24=00b9ffff ptr=(310,198)
in_ski True 279 s
ski          vbl=13969 PADST=01 PADJ=00 BTN=00 OLD=00000000 vec=(+0.0,+0.0) $24fba=0000 head=0 rate=0 speed=0 step=000131ae menu=0000 key24=00000000 ptr=(135,170)
hold left    vbl=14050 PADST=01 PADJ=04 BTN=00 OLD=00000004 vec=(-5.0,+0.0) $24fba=0000 head=-185 rate=-2 speed=0 step=000131ae menu=0000 key24=00000000 ptr=(135,170)
rel left     vbl=14096 PADST=01 PADJ=00 BTN=00 OLD=00000000 vec=(+0.0,+0.0) $24fba=0000 head=-202 rate=0 speed=0 step=000131ae menu=0000 key24=00000000 ptr=(135,170)
hold right   vbl=14177 PADST=01 PADJ=08 BTN=00 OLD=00000008 vec=(+5.0,+0.0) $24fba=0000 head=-55 rate=35 speed=0 step=000131ae menu=0000 key24=00000000 ptr=(135,170)
rel right    vbl=14222 PADST=01 PADJ=00 BTN=00 OLD=00000000 vec=(+0.0,+0.0) $24fba=0000 head=0 rate=0 speed=0 step=000131ae menu=0000 key24=00000000 ptr=(135,170)
hold up      vbl=14303 PADST=01 PADJ=01 BTN=00 OLD=00000001 vec=(+0.0,-5.0) $24fba=0000 head=0 rate=0 speed=0 step=000131ae menu=0000 key24=00000000 ptr=(135,170)
rel up       vbl=14349 PADST=01 PADJ=00 BTN=00 OLD=00000000 vec=(+0.0,+0.0) $24fba=0000 head=0 rate=0 speed=0 step=000131ae menu=0000 key24=00000000 ptr=(135,170)
hold down    vbl=14430 PADST=01 PADJ=02 BTN=00 OLD=00000002 vec=(+0.0,+5.0) $24fba=0000 head=0 rate=0 speed=0 step=000131ae menu=0000 key24=00000000 ptr=(135,170)
rel down     vbl=14476 PADST=01 PADJ=00 BTN=00 OLD=00000000 vec=(+0.0,+0.0) $24fba=0000 head=0 rate=0 speed=0 step=000131ae menu=0000 key24=00000000 ptr=(135,170)
hold B       vbl=14632 PADST=01 PADJ=00 BTN=01 OLD=00002000 vec=(+0.0,+0.0) $24fba=0002 head=0 rate=0 speed=263 step=000131ae menu=0000 key24=00000000 ptr=(135,170)
hold A       vbl=14763 PADST=01 PADJ=00 BTN=00 OLD=00000020 vec=(+0.0,+0.0) $24fba=0001 head=0 rate=0 speed=0 step=000131ae menu=0000 key24=00000000 ptr=(135,170)
hold 2 (S)   vbl=14920 PADST=01 PADJ=00 BTN=00 OLD=00080000 vec=(+0.0,+0.0) $24fba=0000 head=4 rate=0 speed=0 step=00013f36 menu=0000 key24=00000000 ptr=(135,170)
snipe?       vbl=14976 PADST=01 PADJ=00 BTN=00 OLD=00000000 vec=(+0.0,+0.0) $24fba=0000 head=1022 rate=0 speed=0 step=00013f36 menu=0000 key24=00000000 ptr=(135,170)
ski again    vbl=15133 PADST=01 PADJ=00 BTN=00 OLD=00000000 vec=(+0.0,+0.0) $24fba=0000 head=1020 rate=0 speed=0 step=000131ae menu=0000 key24=00000000 ptr=(135,170)
after X      vbl=15314 PADST=01 PADJ=00 BTN=00 OLD=00000000 vec=(+0.0,+0.0) $24fba=0000 head=1020 rate=0 speed=0 step=000131ae menu=0001 key24=00000000 ptr=(135,170)
total 306 s
```
Same behaviour from the floppy: the probe finds the ports after PLAY, the pad drives the pointer on the menu screens (Team: `ptr` runs to the right/bottom limits `310,198`),
and in the ski view: directions, fire (`$24fba = 2`, speed 263), A (`$24fba = 1`, speed 0), 2 (S: sniper `$13f36` and back `$131ae`), Option (X: `menu = 1`).

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
* **No real STE, no real pad.** The electrical timing (23 us settle, study 1.2) and the pad matrix come from documents and from Hatari's `joy.c`; a real Jaguar pad on a real STE
  must be tried before shipping (study section 5). Third-party pads with a microcontroller may need longer than 23 us (study 1.2: up to 20 us typical, 100 us identification).
* **Falcon** (and any 68020+): `PADST = $ff` by design (phase 2 in the study: the Falcon has the same ports, the detection could only be seen in Hatari). The Falcon boots to the ski view with the set applied (3.3).
* **K and M mode**: untouched (the pad is read as released). With only a pad, choose J at the Game Options screen (that screen needs the mouse; the pad is live from PLAY on, `$2c178` is copied at PLAY).
* The default stays `no` (the lead decides): on a pad-less machine the cost is 134-181 cycles/VBL (0.08-0.11 %) and the no-pad gate is identical, on an STE with ports ~980 cycles/VBL (0.61 %).
* A and Option are mapped to game-state-changing keys (`>` stops, X leaves the action mode); `*`, `#`, `0`, `4`-`9` are free (`keymap` in `jag_vbl.s` takes `{bit, scancode}` pairs).
* Suggested user-doc line for `PATCHES.TXT`/`README` when `jag_*` become default (not edited: not my file): "Atari Jaguar pads in the STE/Falcon controller ports work as the joystick in
  Joystick mode (STE only): D-pad = stick, B = fire, A = right button, C = Space, Option = X, Pause = P, 1/2/3 = M/S/H; other machines are unchanged."
