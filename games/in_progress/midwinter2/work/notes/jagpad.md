# Jaguar pad support for Midwinter 2 (`jag_poll`, `jag_dir`, `jag_btn`; `default: no`)

Author: JagMW2. Study: `gamebench/reports/jaguar_pad_study.md` (protocol, detection, PoC). Evidence = raw tool output from this session
(Hatari 2.6.1, pad A emulation, `work/jagpad/*.py`, logs quoted below) or a disassembly line of `work/dumps/ram_ingame_lobos.bin`
(`tools/m68dis.py`); anything else is marked **[INFERENCE]**. Real STE hardware with a real pad is **untested** (Hatari is the only evidence).

## 1. What was added

| file | site | orig -> new | blob |
|---|---|---|---|
| `patches/jag_poll.s` | `$262c2` (6 B) | `4eb900027228` (`jsr $27228`) -> `4eb9000b9500` | `$B9500-$B9867` (872 B incl. 272 B decode tables), data `$B9EE0-$B9EEF` |
| `patches/jag_dir.s` | `$26b66` (8 B) | `7000 7200 14280001` -> `jsr $b9e00.l / nop` | `$B9E00` (16 B) |
| `patches/jag_btn.s` | `$26bea` (6 B) | `141002420003` -> `jsr $b9e20.l` | `$B9E20` (14 B) |
| `patches/p5_ctl_vbl.s` | (existing) | one added instruction `or.b PADJ.l,d1` after `move.b $75a9.w,d1` | - |

All sites are in FFA file 9 (`mw2patch.py list`: `src FFA f9`), none overlaps a `PP_PATCHES` address or another patch.
`PADJ` = `$B9EE1` is read by `p5_ctl_vbl` (zero payload RAM without `jag_poll`). Blob map row added to the `mw2-patching` skill and `patches/README.md`.

* **Poll placement.** `$262c2` is the VBL handler's `jsr $27228` (`$262c2: 4eb900027228 jsr $27228.l`, `$262c8: bsr.w $26b58`, `$262cc: bsr.w $26c1e`): straight-line code,
  every register saved by the handler (`$26298: movem.l d0-d7/a0-a6,-(a7)`). The blob polls, restores what it used, and tail-jumps to `$27228`. So the poll runs once per VBL
  *before* `p5_ctl_vbl`'s `jsr $26b58` (site `$262c8`) and its sampler. It cannot live in `jag_dir`: `$26b58` is also called from the IKBD ISR (`$269de: jsr $26b58.l`), which saves
  only d0-d3/a0 (`$26882: movem.l d0-d3/a0,-(a7)`).
* **Merge.** `$26b58: tst.w $eb76.l / beq.w $26c1c` (J mode gate). Inside: `$26b6a: move.b $1(a0),d2` = the IKBD joystick byte `$75a9` (bit0 up, 1 down, 2 left, 3 right). `jag_dir` ORs `PADJ`
  into d2; `$26b74-$26bde` turn it into the ramps `$75b2..$75be` (d0/d1 live at `$26a8e`), `$26b0c: add.l d1,$6fb6 / neg d0 / add.l d0,$6fba`. The pad therefore behaves exactly like the stick
  in every consumer (original yoke, `p5_ctl_x`, throttle). `$26bea: move.b (a0),d2 / andi.w #3,d2` + `$26bf0: move.w d2,$6872.w` is the select/fire event; `jag_btn` ORs `PADBTN` (pad B).
* **`p5_ctl_vbl`.** Its sampler counts left/right VBLs from `$75a9` (`move.b $75a9.w,d1 / btst #2 / btst #3`); without the OR the pad would turn through the old ramps while `p5_ctl_x` saw nothing.
  Measured (cold boot STE, Lobos helicopter): pad Left -> `$6766` = -50, Right = +50, Up -> `$6750` = 944; same values as the stick path (`p5_controls.md`: YAW_PCT 50).
* **`p3cp_head`, `p3c_*`.** They read no input register themselves (`grep -n '75a9\|eb76\|6872\|7686\|7684\|6fb6\|6fba\|6fbe' patches/p3c*.s` finds nothing); the pad reaches them through
  `$6fb6`/`$6fba`/`$6fbe`/the key table exactly like the stick, at the same once-per-tick sampling points. Nothing to change there.
* **No pad, no change.** Idle pad = all lines high = S = 0 = `PADJ`/`PADBTN` 0 -> OR of zero, no key event (Section 5 below: pixel-identical, J mode and M mode).

## 2. Hardware protocol as implemented (details: study section 1)

Row select word to `$ff9202`, read the word registers `$ff9200` (bit 1/3 = A,B,C,Option for groups 4,3,2,1 on port A/B, bit 0/2 = Pause on group 4) and `$ff9202` (bits 8-11 port A / 12-15 port B rows
Up,Down,Left,Right; keypad rows for groups 3/2/1); low = pressed. Selects `$ffee $ffdd $ffbb $ff77` = that group on both ports in one write; `$ffff` afterwards. Words only (a byte read of `$ff9200` bus-errors on a real STE).
Port A and B are OR-ed by two lookup tables (T1 256 B, T2A/T2B 16 B each, built by `rept` in the blob). One scan per VBL reads **group 4 plus one of groups 3/2/1 in turn**, so every button is seen at least
every 3rd VBL; the select-to-read gap is 172 / 178 cycles (>= 20 us at 8 MHz), the second select is written before the first group is decoded.
State `GB` (one byte per group, g4 first): `24 Up 25 Down 26 Left 27 Right 28 A 29 Pause | 16 * 17 7 18 4 19 1 20 B | 8 0 9 8 10 5 11 2 12 C | 0 # 1 9 2 6 3 3 4 Option`.

## 3. Detection and the machines (fail closed, one probe, cached in FLAG)

1. 68000 only (brief-extension trick `lea (0,a0,d0.w*2),a1`: `$b9544: 43f00200`). TT (68030) and Falcon: no hardware access at all, `FLAG = 2`. **Falcon is not supported** (a Falcon-specific
   branch needs the study's open item, a real Falcon, and a bus-error probe on 68030 under HAGA's low-RAM remap, which I did not want to run blind: `core.s:121`).
2. Guarded reads, vector `$8` swapped, `a7` restored by the handler, interrupts masked: `$ff8901.b` (DMA sound) must answer, `$ff8a3c.b` (blitter) must answer, `$ff8e21.b` (Mega STE cache) must bus-error.
3. Guarded word write `$ffff` -> `$ff9202`, reads of `$ff9202` / `$ff9200`: high byte `$ff` and low nibble `$f` (a Mega STE reads `$xxx9`, a TT `$xx03`).
The probe runs on the first poll in J mode (M/K mode never touch it). Results, cold boots of the HD build (`work/jagpad/cold.py`, `raid_from_map.py`, Hatari 2.6.1, pad A configured on every machine, keys held):

| machine | TOS / RAM | `FLAG` | pad keys effect | bus-error log lines (Hatari `WARN`) |
|---|---|---|---|---|
| STE | 1.62, 1 MB | 1 | all buttons work (Section 4) | `$ff8e21` reported at PC `$b9578` = just after my guarded `tst.b $ff8e21` at `$b9574`; `$1ba9c` is the game's own probe of the same register |
| ST | 1.04, 1 MB | 2 | none: `PADJ=00 GB=00000000 keys=[]` over 8 held pad keys, game kept running | `$ff8e21` PC `$1babc`, `$ff8924` PC `$1baea` (the game's own), `$ff8901` PC `$b956c` (mine, guarded) |
| Mega ST | 1.04, 1 MB | 2 | none | same three lines as ST |
| Mega STE | 2.06, 1 MB | 2 | none | none (`$ff8901`, `$ff8a3c`, `$ff8e21` all answer; `$ff9200/2` never touched) |
| TT (`--mmu true`) | 3.06, 4 MB | 2 | none | none (no hardware access) |

No crash, no stuck state, `MWPO` set on all five.

**Falcon (TOS 4.04, 4 MB, `falcon_min.py`):** the HD build does not reach the game in this harness at all, with or without the jag set (default build `build/jag_def` behaves the same): after the M/J/K key the screen stays black (1 colour in the screenshot), `$b2ff8` reads zero, the sites are untouched, no bus error logged. So the Falcon could not be tested; the jag code on a 68020+ executes only `cmpi.b #2,FLAG / tst.w $eb76 / movem / probe: lea (0,a0,d0.w*2),a1 / cmpa.w #1,a1 / bne` and touches no hardware register. (`$b9578` / `$b956c` are the guarded probe reads, reported one instruction late: the handler discards the frame, `a7` and `$8` are restored.)

## 4. Mapping, and what actually reaches the game

J mode only. The M/J/K flags are pure gates (`controls.md` section 5): `$26b58` (joystick) needs `$eb76`, `$26c1e` (keyboard ramp) needs `$eb78`, the mouse `$26a6c` needs `$eb7a`.

**Climb / dive.** MaskTT found `,` / `.` dead while swimming; that run was in **M mode** (`$eb78 = 0`): in M mode neither key is read anywhere (`$26c1e: tst.w $eb78.l / beq.w $26dc4`, `$26b58` returns at `$26b5e`),
so there is nothing to map there. In **J mode** the keys are read at `$26bf4` (`lea $7686.w,a0 / move.b $33(a0),d3 / or.b $4b(a0),d3 / beq / ori.b #2,d2` and `$34` -> `ori.b #1,d2`, then `bra.w $26a8e`) and stored as the
two "mouse buttons" `$26aca: move.w d2,$6fbe.w`; the button axis `$34282: move.w $6fbe.w,d2 / beq / moveq #$10,d0 / btst #1,d2 / beq / moveq #$f0,d0` makes bit 1 (`,` = `<`) negative, bit 0 (`.` = `>`) positive, and `$3461a`
integrates it into `$6746` (bank / pitch; air types derive the vertical speed from it, `vehicles_air.md` section 1; Swimming/Frogman use the same axis for the dive switch). (J mode uses `$4b` (Left) for BOTH tests at
`$26bfe` / `$26c0e`, the original's quirk; irrelevant here.) The pad's A and C therefore make `,` and `.`; **they work** (raw outputs):

* Helicopter (snapshot `raid_helicopter_lobos_moving`, live patches, J mode): hold C: `$6fbe=0001 bank$6746=416 alt$764c=2217` (from 2000), hold A: `$6fbe=0002 bank=-128 alt=1281`, then the helicopter lands (type 13 -> 5).
* Swimming (`raid_swimming_vitoria`): hold A: `type=11 (Frogman) bank=-48 -> -400 alt=-64 -> -98` (dive), hold C: `type=21 bank=192 alt=4` (surface).
* Cold boot STE HD, Speedboat Iquitos, Option tap 150 ms -> on foot -> Swimming: hold A `type=11 head=640 bank=-448 alt=-19` (dive), hold C `type=21 bank=192` (surface) (log in Section 6).
* Jeep, on foot: A `bank=-184/-192`, C `bank=-8 -> 160`: the same axis is read.

**Map** (`; default: no`; `GB` bit -> key / event):

| pad | game input | consumer (evidence) |
|---|---|---|
| D-pad | stick | `$75a9` merge (Section 1); Hatari: Left `yaw=-50`, Right `+50`, Up `thr$6750=944` (helicopter), Jeep `thr 727`, `yaw=+-200` |
| B | fire / select event | `$6872` = 1 (`$1ab70: tst.w $eb76 / beq / tst.w $6872 / beq.w $1b31c / clr.w $6872`); breakpoint `$1ab8e` hit on every press (2 and 1 hits for two taps) |
| A | `,` `$33` | `$6fbe` = 2, nose down / dive (above) |
| C | `.` `$34` | `$6fbe` = 1, nose up / climb (above) |
| Option | Esc `$01` | `$1b43a: tst.b $1(a0) / beq / clr.b $1(a0)` ... leaves the vehicle; Jeep -> on foot (type 1 -> 5), Speedboat -> Swimming (6 -> 5 -> 21), helicopter -> parachute (13 -> 17); breakpoint `$1b446` hit |
| Pause | P `$19` | `$1b31c` pause loop: breakpoint `$1b384` hit; second tap resumes |
| 1 .. 9, 0 | F1 .. F9 `$3b-$43`, F10 `$44` | `$30f72` dispatcher: breakpoint `$30f92` hit once per pad key, all ten (fresh restore per key, Section 6) |
| `*` | keypad `-` `$4a` | `$1ab26: cmp.b #$4a,d1` -> `$18112 = ($18112-1)&$1f` icon bar (previous weapon): breakpoint `$1ab2c` hit |
| `#` | keypad `+` `$4e` | `$1ab4e: cmp.b #$4e,d1` -> `$18112 + 1` (next weapon): breakpoint `$1ab54` hit |

Not mapped: Space, Return, the cursor keys, Help (`$62`), letters: all 21 switches are used. The cursor Up/Down keys are polled from the table (`$1b5ec: tst.b $48(a0)`, `$1b60c: tst.w $50(a0)`: rifle-sight zoom on foot);
the keyboard still works alongside the pad.

**Keys.** The injection mirrors the IKBD ISR: make (`$269fe`): `$7684 = sc; $7686[sc] = $ff; $75ac = $ffff; $770a = sc; $770c = 0`; break (`$26a20` -> HAGA `$3ea` -> `$26a28`): `$7684 = sc|$80; $7686[sc] = 0; if sc == $770a { $770a = 0; $7708 = sc }; if $75ac == 0 { $7684 = 0 }`.
One make per press, no auto-repeat; run with `sr |= $700` (the ISR saves only d0-d3/a0).

**Esc hold (found by measurement).** The game reads Esc from the key *table*, once per logic iteration (`$31568: jsr $50d4` = `jmp $1b43a`, every 10 VBL = 5 Hz: `t_iter.py`: 65 polls in 641 VBL), while the other keys go through the
latched `$7684`/`$75ac`. A pad tap shorter than a tick would be lost half the time (as it is on the real keyboard). Experiment (`t_tap.py`, game's Esc handler replaced by `rts`, breakpoint `pc=$31568 && ($7687).b ! 0`, 10 taps each):

| tap | polls seeing Esc down, ESCMIN = 0 | ESCMIN = 16 |
|---|---|---|
| 30 ms | 2 | 12 |
| 60 ms | 4 | 17 |
| 100 ms | 3 | 16 |
| 150 ms | 8 | 17 |
| 250 ms | 13 | 19 |

So Option's break is held back until 16 VBL after the press (`ESCMIN`, 320 ms at 50 Hz / 267 ms at 60 Hz; every tap is then seen by at least one poll). A and C are not stretched (a held button is the normal use; same as the keyboard).
Make events per tap (`t_tap.py`, breakpoint at `.make`, 10 taps each): A 10/10 at 40 ms; C 8/10 (first run) and 10/10 (second) at 40 ms, 10/10 from 70 ms; Option 9/10 at 40 ms, 10/10 from 60 ms; `*` 9/10 at 40 ms:
a tap shorter than 60 ms on groups 3/2/1 can be missed (rotation period 3 VBL).

## 5. Gates

* `mw2patch.py verify`: ALL OK (`jag_poll` `$262c2 4eb900027228`, `jag_dir` `$26b66 7000720014280001`, `jag_btn` `$26bea 141002420003` match FFA f9 and the RAM dump).
* `abtest.py --only <26 display patches> jag_poll jag_dir jag_btn --flips 10` and `--flips 40`, snapshots `1mb_ingame_walking` / `1mb_ingame_foot`: **IDENTICAL**, exit 0 both times (fps 3.1 -> 3.4, 4.2 -> 27.4, unchanged from the display set alone).
* J mode forced (`w $eb76 ff ff 0 0 0 0` at the capture point in both runs), no pad pressed, `--joy1 none`: display set vs display set + jag: **IDENTICAL**, flips 10 and 40, both snapshots
  (`work/jagpad/t_abj.py`, exit 0). **Harness trap:** Hatari's default joystick port 1 ("real") reads as a *stuck down* stick without a joystick (`$75a9 = 02` in `t_dbg.py`); in J mode
  that makes the ramps (and so the game state) depend on the VBL count, and the same A/B pair then DIFFERS (md5 `b1ad4c9b` vs `5de046fb`, RAM diff `$66e9`, `$6fbb`, `$770d` ...). Always run J-mode tests with `--joy1 none`.
* Cold boots: Section 3 (ST, Mega ST, Mega STE, TT) and Section 6 (STE HD, floppy).

## 6. Cycles per VBL (STE 8 MHz, Hatari CPU profile over 220 VBL, snapshot `1mb_ingame_foot`, `work/jagpad/t_cycles.py`)

```
M mode (jag idle path)       jag_poll=14960  (68/VBL)                          jag_dir+btn=0        p5_ctl_vbl=174/VBL
J mode, pad idle             jag_poll=232320 (1056/VBL = 0.659 % of 160256)   jag_dir+btn=100/VBL  p5_ctl_vbl=244/VBL
J mode, hold Up+z+o          jag_poll=232320 (1056/VBL)                       jag_dir+btn=100/VBL  p5_ctl_vbl=245/VBL
J mode, hold 1+5+9+0         jag_poll=93984 over 89 polls (1056/VBL)          jag_dir+btn=100/VBL  p5_ctl_vbl=246/VBL
```
Pad cost with and without a pad is the same (1056 cycles per VBL: the key bookkeeping runs only when a button changes). Total in J mode = 1056 + 100 + 16 (the added `or.b`) = 1172 cycles/VBL = **0.73 % of the CPU at 50 Hz, 0.88 % at 60 Hz**
(1172 x 60 / 8e6). M/K mode: 68 cycles; J mode on a machine without pad ports: `cmpi.b + beq + jmp` = 42. (First version, 4 groups every VBL, was 1692 = 1.06 % + 116 and was reworked.)

## 7. Cold-boot acceptance with the pad (STE HD build = default set + jag, 1 MB, TOS 1.62, J mode forced with `w $eb76 $ff $ff 0 0 0 0` after the 3D view is up; the M/J/K screen takes the mouse for the menus)

`MWPO` set on every boot. Lobos (helicopter), Dhafra (Jeep), Iquitos (Speedboat) were reached by `mw2raids` from the cold-booted map; each state was held in J mode with pad keys via xdotool (`work/jagpad/pad.cfg`).

```
ste_lobos (Helicopter, type 13):  Left  head 332  yaw=-50 PADJ=04 | Right head 924 yaw=+50 PADJ=08 | Up thr$6750=944 PADJ=01 | (then it landed: 13 -> 17 -> 5)
                                  C $6fbe=0001 keys=['34'] bank=192 | A $6fbe=0002 keys=['33'] bank=-192 | B $6872=0001 | * keys=['4a'] | # keys=['4e'] | P keys=['19'] x2 | 1 keys=['3b']
ste_jeep (Jeep, type 1):          Up thr=727 spd=363 | Left yaw=-200 head 1022 | Right yaw=+200 head 276 | A $6fbe=0002 bank=-184 | C $6fbe=0001 | B $6872=0001 |
                                  Option tap 150 ms: type 1 -> 5 (on foot) | on foot: Up thr=287 | Left yaw=-50 | B $6872=0001 | 1 keys=['3b']
ste_boat2 (Speedboat, type 6):    Option tap 150 ms: 6 -> 5 -> 21 Swimming | A: type=11 bank=-448 | C: type=21 bank=192   (dive and surface through the pad)
```
Per-button consumers on the cold-booted Lobos state (`t_consumers.py`, `t_consumers2.py`, fresh restore per key): B -> `$1ab8e` 2/1, `*` -> `$1ab2c` x2, `#` -> `$1ab54` x2, F1..F10 -> `$30f92` once each, P -> `$1b384` once (two taps),
Option -> `$1b446` once (helicopter -> type 17).

FLOPPY: see Section 8.

## 8. Floppy build

`mw2patch.py build --floppy --only <defaults without pp_*> floppy_copybuf jag_poll jag_dir jag_btn --out build/jag_fl` -> 37 patches, payload 32768 B = FFA file 10 (the three sites are the same on floppy:
`build --floppy` checks `floppy_conflicts`). Cold boot from the floppy images (`work/jagpad/jag_floppy.py`, adapted from `work/floppy_tests/run_cell.py`, STE TOS 1.62, 1 MB; drive A boots FFA, swapped to FFB at the prompt,
no security-check bypass written by the test) reached the Lobos 3D view (`type 13`, `MWPO`; sites `4eb9000b9500 / 4eb9000b9e00 / 4eb9000b9e20` in RAM), then J mode and the pad:

```
Left  head 394 yaw=-50 PADJ=04 | Right head 940 yaw=+50 PADJ=08 | C $6fbe=0001 bank=400 keys=['34'] | A $6fbe=0002 bank=364 keys=['33'] | B $6872=0001 |
* keys=['4a'] | # keys=['4e'] | P keys=['19'] (x2) | Option tap 150 ms: type 13 -> 17 (parachute) -> 5 | floppy FLAG 1 PASS
bus-error log lines: Bus Error reading at address $ffff8e21, PC=$b9578 (the guarded probe)
```

## 9. Limits / not done

* Real STE / real Jaguar pad: untested (Hatari only). The 20 us select-to-read gap is from the Jaguar developer reference (microcontroller pads); the passive pad needs less. On a 16 MHz accelerated STE the gap would halve.
* Falcon: not supported (68020+ = no pad access); TT: no ports. Mega STE: no ports (DIP bits at `$ff9200`).
* K and M mode: untouched. A user who picks M or K with only a pad connected gets nothing; choose J.
* A/C: a tap shorter than one logic tick can fall between two samples, as for the keyboard `,` `.` (the game samples `$6fbe` once per tick). B: sampled every 3rd VBL (group 3).
* Two taps of Option inside 320 ms count as one press.
* A user with only a pad still needs the keyboard once, to pick `J` on the M/J/K screen.

## 9b. Menu navigation with the pad (J mode, `work/jagpad/t_menu2.py`, snapshot `corridor_agent`, live patches, `--joy1 none`)

In J mode the stick moves the menu pointer (`$26b18`: `$6fae` = X clamped 8..$136, `$6fb2` = Y clamped 8..$c3) and `,` / `.` set the two mouse-button bits (`$26af0-$26b04`: `$62e6 = $ffff` + click position `$6faa/$6fac`), so the pad's A is the left button.
Raw: pad Right 0.5 s moved X 144 -> 257 (113 px; the ramp is +0.25 px per VBL per VBL), Down 0.5 s moved Y 38 -> 151. Closed loop with short taps to the CONTROL door label:

```
at (144,38) target (159,63) / at (164,73) / at (157,62) arrived
during A: $6fbe 0x2  $62e6 0xffff  click pos 157 62   ->  $700a 0 -> 2, the map screen loads (menu_after_click.png)
```

## 9c. Proposed release text (PATCHES.TXT; not edited, the patches are `default: no`)

"- Atari Jaguar pad (STE, Falcon-style enhanced joystick ports) in joystick mode: D-pad = stick, B = fire, A / C = `<` / `>` (nose down / up, dive / climb), Option = Esc (leave vehicle), Pause = P,
keypad 1-9 / 0 = F1-F10, `*` / `#` = previous / next weapon. Detected at run time; other machines are unchanged (cost 0.7 % of the CPU on an STE)."
(The Falcon is not supported by the code as written: see Section 3.)

## 10. Side note for the lead: IKBD packet handling (asked via Main, MW2 handler `$26882`)

The handler does not range-check mouse/joystick *values*, but it also never uses them as an index, so a misframed packet cannot walk through memory. Evidence: the packet states store at fixed small offsets chosen by
the header, `$268c0: move.w #2,$759e.w` (`$f8-$fb`), `$2691e: move.w #7,$759e.w / move.w #5,$75a0.w` (any other header >= `$f6`, bytes dropped at `$269e8`), `$268dc`/`$2690a` for `$fe`/`$fd`, then
`$26956: lea $75a2.w,a0 / move.w $759e.w,d1 / move.b d0,(a0,d1.w) / subq.w #1,$759e.w / bne.w $26a44 / bsr.w $26a6c` (index 1..2, `$75a0` only ever takes 1..5 so `$2693e` indexes six words); the joystick states
index `$75a8 + $759e` (<= 2). Mouse deltas are signed bytes (`$26a7a: move.b $1(a0),d0 / ext.w d0`) added to accumulators (`$26b0c: add.l d1,$6fb6.w`, `neg d0 / add.l d0,$6fba.w`) with no bound there; they are clamped at the
consumer (`$347f2`, and `p5_ctl_x` caps `MOUSE_CAP`), and the menu pointer is clamped (`$26b1e: cmp.w #$8,d0 ... cmp.w #$c3,d0`, `$26b3e ... cmp.w #$136,d1`). The scancode path masks to 7 bits (`$269fe: tst.b d0 / bmi.b $26a20`,
make index `d0 <= $7f` into the 128-byte table `$7686`; break: HAGA `$3f6: andi.w #$7f,d0 / jmp $26a28.l`). So a split packet can give wrong deltas / buttons, a data byte below `$f6` arriving at idle is taken as a scancode
(a make without a break = a stuck key until the break arrives, e.g. `$7687` Esc), and a data byte of `$e5`/`$e6` at idle reaches HAGA's `$3ec` compare (`$3ea: cmp.b #$e5,d0 / beq.b $426`, `$3f0: cmp.b #$e6,d0 / beq.b $400`, `$400: movem.l d0-d7/a0-a6,-(a7) / moveq #$37,d0 / bra.b $43c`), which I did not trace
(**[INFERENCE]**: PP's save-state / hot-key code). No crash path found; I did not run a misframing experiment.
