# Hunter: Atari Jaguar pad (`patches/jag_pad.s` + `patches/jag_stick.s`, tool `tools/huntjag.py`)

Study: `reports/jaguar_pad_study.md` (protocol, Hatari pad emulation, proof of concept). Hatari 2.6.1, 1 MB unless noted; real TOS per machine.
Tags: **[obs]** observed (raw tool output pasted below), **[disasm]** read from `tools/m68dis.py` on `work/dumps/boot/ram_game.bin`, **[INFERENCE]** not proven.
Both patches are `; default: no` (the lead flips defaults); no version was changed.

**Revision 2 (sections 8 and 9 at the end) supersedes sections 1 (sizes, state), 3 (poll, detection) and 4 (cost) below**: the poll is now one row group per VBL (212 cycles per VBL net, was 748), the probe restores the original site bytes where it says no, and `core.s` got a TT fix for `FLAGS` bit3. Sections 2, 5 and 6 (button map, gates, findings) still stand; the button tables were re-run on the new code (section 9).

## 1. What was built

| file | site | size | job |
|---|---|---|---|
| `patches/jag_pad.s` | `$c616` (6 B) | blob `$8D600-$8D7C9` (458 B), state `$8D9F0-$8D9FF` | VBL hook: replays the displaced `bclr`, lazy probe, poll, key injection |
| `patches/jag_stick.s` | `$c64c` (8 B) | blob `$8D9D0-$8D9DF` (16 B) | OR of the pad's stick byte into `$d0` |

Both sites are original code that no other patch touches [disasm]:
```
00c616:  08ad0003008f   bclr.b #$3, $8f(a5)        ; end of the VBL handler (after `bsr.b $c628` = snd_core's tick) -> jsr JAG_VBL.l
00c64c:  102d00d1       move.b $d1(a5), d0         ; world block of the handler (runs while $93 bit 7 and, with hn_hz, on world ticks)
00c650:  1b4000d0       move.b d0, $d0(a5)         ; -> jsr JAG_MERGE.l / nop (blob: the same two instructions with `or.b JAG_DIR.l,d0` between)
00c654:  e808           lsr.b #$4, d0              ; fire level = bit 4 of the merged value
00c656:  02000001       andi.b #$1, d0
00c65a:  1b4000cf       move.b d0, $cf(a5)
00c664:  4eb90000355a   jsr $355a.l                ; camera / turn / accelerate ramps read $d0 / $cf
```
Why two sites: the merge must happen before `$cf` and `$355a` read `$d0` (so on foot and in vehicles the pad steers like the stick) and `$d1` can not be
written (the IKBD packet decoder overwrites it every VBL); the poll must run even when the 3D-loop gate at `$c63c` is closed, otherwise Pause could never un-pause
(`$2ef0 bclr.b #7,$93(a5)` while paused, `$c63c btst.b #7,$93(a5)` skips the whole block). `huntpatch.py` gained `; requires: <patch>` (selection without the partner is
refused) and the blob prefix `jag_` (`$8D600-$8D9FF`, inside the `hn_` window).

**State** (`$8D9F0`): `JAG_ST` b (0 not probed, 1 pad ports present, `$ff` no), `JAG_TOG` b (poll every second VBL), `JAG_W` w (extra settle loop), `JAG_DIR` b (stick byte in the `$d0`
format S=1 N=2 E=4 W=8 fire=`$10`), `JAG_OLD` l and `JAG_OLD2` w (previous poll).

## 2. Button map

| Pad | Hunter | Pad | Hunter |
|---|---|---|---|
| D-pad | stick (OR-ed with the real joystick) | `1` | R `$13` radar |
| A or B | fire (`$cf`, `$d0` bit 4) | `2` | Help `$62` overlay map ("?") |
| C | Return `$1c` next weapon | `3` | L `$26` log book |
| Option | Space `$39` leave vehicle | `4` | A `$1e` observation drone |
| Pause | P `$19` pause (and un-pause) | `5` | F `$21` flare |
| `*` | Esc `$01` game options | `6` | C `$2e` clock |
| `#`, `0`, `8` | unassigned | `7` / `9` | cursor Up `$48` / Down `$50` zoom, held while pressed |

Port A and port B are both read, with the same map, and OR-ed. The map is the study's proposal (section 4.2) with A, B = fire. Every action is one the game already
has on the keyboard (`work/manual.txt` section 4/5): the pad only calls the game's key decoder. Key makes are injected only while `$93` bit 7 (3D loop) or bit 5 (paused) is set, breaks
always. The menus, the drone map and the game options are mouse driven in the original and stay so: the pad has no pointer.

## 3. How it works

**Poll** (every second VBL, `JAG_TOG`; about 1330 cycles per poll). Word accesses only (`move.b $ff9200` bus-errors on a real STE, study 1.3). Four selects `$ffee/$ffdd/$ffbb/$ff77` (group 4/3/2/1 of port A and B
together; never several groups at once, so a Team Tap stays transparent), then `$ffff`. Software pipeline: the next select is written first, the previous group's data (raw `$ff9200`, `$ff9202`) is decoded while the new group settles, then the new group is read.
Decode: invert, `lsr.w #8`, shift one byte into `d3`; low nibble of `$ff9200` into `d5`. At the end port A | port B in one `lsr.l #4 / or.l / andi.l`; S1 (long) = directions and keypad columns, S2 (word) = A, B, C, Option, Pause (layout in the `jag_pad.s` note).
The first pass decodes a dummy idle group: that is the settle time of group 4, not a wait loop.
Select-to-read gap on an 8 MHz 68000: decode 88 cycles (profile lines `08d6b4..08d6c4`: 4+22+26+4+4+8+14+6) + `move.w d6,d0` 4 + the `dbra` loop with `JAG_W=2` 34 (10+10+14) = 126 cycles = 15.8 us [INFERENCE: 68000 timing arithmetic from the profile's per-instruction cycles; a passive Jaguar
pad needs far less, the FAQ's own example reads straight after the write; the Jaguar reference gives 10 us typical / 20 us worst case for microcontroller pads]. On the Falcon `JAG_W` is 56 (a 16 MHz 030 runs the dbra from its cache several times faster) [INFERENCE: not measured].
**Stick**: `JAG_DIR` from the group-4 nibble through a 16-byte table, fire from A (S2 bit 13) or B (S2 bit 9).
**Keys**: changed bits of S1/S2 against `JAG_OLD`/`JAG_OLD2`, masked to bits that have a key, then a 12-entry table (S bit, scancode); each change calls `jsr $b048.l` with `d0` = scancode (bit 7 = break),
the game's decoder after its IKBD packet-state test [disasm]:
```
00b01e:  122d01d0   move.b $1d0(a5), d1     ; packet state ... bne.w $b290   (skipped by entering at $b048)
00b048:  4a2d0095   tst.b  $95(a5)          ; scripted/demo mode: bmi -> jsr $2640 (any key leaves the demo, as on the keyboard)
00b04e:  49fa00a0   lea.l  $b0f0(pc), a4    ; held-key table, make = $ff, break = 0 (seq.b)
00b062 ... 00b0b6:  btst.b #7,$93(a5) / bne.w $a526      ; command dispatch (R, L, A, F, C, Help; Esc/Return/Space through $2686)
```
Registers: the VBL handler saved d0-d7/a0-a4 (`00c5f4 movem.l d0-d7/a0-a4,-(a7)`), the blob uses only those and saves d3-d6/a2 around `$b048`; `a5` is never touched; `a6` = `$ff8000` as in the real ISR (`00afde movem.l d0-d7/a0-a4,-(a7)` ... `$7c00(a6)`).

**Detection** (first VBL, once; any failing layer = no pad for the session, `JAG_ST=$ff`):
1. `FLAGS` bit0 (core.s probe: STE DMA sound answers; cookie-free) and a bus error on `tst.b $ff8e01.w` (the SCU: Mega STE and TT have it, STE and Falcon do not) [study 1.4: Hatari ST/Mega ST bus-error on DMA, Mega STE and TT answer at the SCU, STE and Falcon fault];
2. guarded word accesses `move.w #$ffff,$ff9202 / move.w $ff9202 / move.w $ff9200` (vector `$8` swapped, `a7` restored: `core.s probe`'s pattern);
3. idle sanity with every group deselected: `$ff9202` high byte `$ff`, `$ff9200` low nibble `$f` (study: Mega STE reads `$fff9`, TT `$3f03`, a stuck line 0).
`FLAGS` bit3 (Falcon) is **not** used to decide: on the TT HD build it reads 1 (section 6, finding 1). It only selects `JAG_W`. A pad button held while the probe runs does not matter (every group deselected reads high): tested, section 5.5.

## 4. Cost (Hatari cycle profile, 1 MB STE 8 MHz, snapshot `1mb_foot_stand`, 250 VBL, `tools/huntjag.py prof`) [obs]
```
pad A configured: jag_pad blob 152240 cycles over 220 VBL hook calls -> 692.0 cycles per VBL (0.432 % of a 160256-cycle VBL); jag_stick merge 56.0 per VBL
no pad          : jag_pad blob 151704 cycles over 219 VBL hook calls -> 692.7 cycles per VBL (0.432 % of a 160256-cycle VBL); jag_stick merge 56.0 per VBL
plain ST (probe = no), pad configured : 68.0 cycles per VBL (0.042 %), merge 56.0 per VBL
plain ST (probe = no), no pad         : 68.0 cycles per VBL (0.042 %), merge 56.0 per VBL
```
So 748 cycles per VBL = **0.47 %** of the CPU on an STE (a pad costs no more than none: the poll is data independent), 124 cycles per VBL = 0.08 % where the probe says no. The first all-VBL, 4-pad-group version measured 1304 cycles per VBL (0.81 %); polling every second VBL halves it (a press must last two VBL = 40 ms).
Key injection adds, inside the VBL handler, per make (cycles of `jsr $b048` to return; `tools/huntjag.py inject`) [obs]: C 780, Option 804, Pause 792/488, `1` 580, `2` 1272, `3` 608, `5` 664, `6` 552, `7`/`9` 776, `*` 824, `4` (drone map) 15632; breaks 108.
Frames are quantised to whole VBL: Hunter standing at the HQ needs about 1,602,020 of the 1,602,560 cycles of a 10-VBL frame (`REPORT.md` section 3: 1,602,020 cycles, 10.64 VBL/frame on average), so a per-VBL cost of a few tens of cycles already pushes some of those frames to 11 VBL: the gate below shows it
(`foot_stand` 10.76 -> 10.92 VBL/frame, `car_stand` 8.78 -> 8.95, `hills_stand` 6.69 -> 6.91, `4mb_foot_stand` 10.01 -> 10.48; walking and driving scenes 9.00/7.00 -> unchanged). This is the same effect `REPORT.md` describes for every cost change; it is why the patch is not default.

## 5. Gates [obs]

### 5.1 No pad, jag on: the existing pixel gate `tools/huntab.py` (live patch set on the snapshots, base = the six default patches; run through `tools/huntab_serial.py`, which only swaps huntab's thread pool for a serial executor so one Hatari runs at a time)
```
$ DEF="p4_ikbd p4_edge p4_poly snd_core hn_credit hn_hz"; huntab_serial.py --base $DEF --only $DEF jag_pad jag_stick --points 1 --flips 1 6 --vbls 400
foot_stand: IDENTICAL | work(first patched frame) 1588728 -> 1604820 (+16092, +1.01 %) | VBL/frame 10.76 -> 10.92 | fps 4.65 -> 4.58
    p0 flips=6 DIVERGED-TIME frames base=[10, 10, 10, 10, 10, 11] patched=[10, 11, 11, 11, 11, 11] (differs)
foot_walk: IDENTICAL | work(first patched frame) 1374120 -> 1380024 (+5904, +0.43 %) | VBL/frame 9.00 -> 9.00 | fps 5.55 -> 5.55
car_stand: IDENTICAL | work(first patched frame) 1272972 -> 1287636 (+14664, +1.15 %) | VBL/frame 8.78 -> 8.95 | fps 5.70 -> 5.58
car_drive: IDENTICAL | work(first patched frame) 991788 -> 996936 (+5148, +0.52 %) | VBL/frame 7.00 -> 7.00 | fps 7.14 -> 7.14
car_turn: IDENTICAL | work(first patched frame) 1038844 -> 1043284 (+4440, +0.43 %) | VBL/frame 7.00 -> 7.00 | fps 7.14 -> 7.14
hills_stand: IDENTICAL | work(first patched frame) 968932 -> 973372 (+4440, +0.46 %) | VBL/frame 6.69 -> 6.91 | fps 7.47 -> 7.23
4mb_foot_stand: IDENTICAL | work(first patched frame) 1531368 -> 1537388 (+6020, +0.39 %) | VBL/frame 10.01 -> 10.48 | fps 5.00 -> 4.77
ALL IDENTICAL
```
(`DIVERGED-TIME` rows are the legitimate divergence of a frame that crossed a VBL boundary because of the extra cycles, `huntab.py` docstring; the hard comparison is the first patched frame, flips = 1, 7 of 7 identical.)
With `--lock` (every flip a hard comparison, 15-VBL frames), `--flips 1 6`:
```
foot_stand: IDENTICAL   foot_walk: IDENTICAL   car_drive: IDENTICAL   car_turn: IDENTICAL   ALL IDENTICAL
```
**Negative control**: a throwaway patch with the same site as `jag_stick` that ORs a stuck North (`ori.b #2,d0`) instead of the pad byte (`org $c64c / jsr $8dc00.l / nop`; blob `move.b $d1(a5),d0 / ori.b #2,d0 / move.b d0,$d0(a5) / rts`; file removed afterwards), same `--lock --flips 1 6`:
```
foot_stand: DIFFER   p0 flips=6 DIFFER {'b23000': 2688, 'b2ad00': 2934}
foot_walk: DIFFER    p0 flips=6 DIFFER {'b23000': 4144, 'b2ad00': 3786}      MISMATCH
```
The default build is untouched: `huntpatch.py build --samples build/hunter_snd.bin` gives `START.TOS 28c613b4...` and `FILES/P a0b9a610...`, the same md5s as the existing `build/game`; `verify` and `verify --floppy` ALL OK.

### 5.2 The real joystick next to the pad (cold boot, `cfg none --stick`, default build against default+jag) [obs]
```
default (no jag): real stick Up d0=02 d1=02 | Left d0=08 d1=08 | Control_R (fire) ce=01 cf=01 d0=10 d1=10      fps {'flips': 24, 'fps': 4.8, 'vbls_per_frame': 10.416}
default + jag   : real stick Up d0=02 d1=02 | Left d0=08 d1=08 | Control_R (fire) ce=01 cf=01 d0=10 d1=10      fps {'flips': 24, 'fps': 4.8, 'vbls_per_frame': 10.416}   (JAG_ST=01, JAG_DIR=00, S1=0)
```
OR with a real stick (snapshot, pad B only, `live --cfg b --pad b --stick`):
```
real stick Up        + pad B Left   d0=0a d1=02  JAG_DIR=08
real stick Left      + pad B Up     d0=0a d1=08  JAG_DIR=02
real stick Control_R + pad B Right  ce=01 cf=01 d0=14 d1=10  JAG_DIR=04
real stick Up        + pad B A      cf=01 d0=12 d1=02  JAG_DIR=10
```

### 5.3 Pad against keyboard (same patched snapshot, pad A on one run, the same keys typed on the host keyboard, no pad, on the other; `huntjag.py kbd`) [obs]
```
button   | pad: $93 lastkey sc/asc $24a/$252/$92        | keyboard
C        | 80 1c/00 00060201/0000/6080                   | 80 1c/00 00060201/0000/6080     same
Option   | 80 39/20 ...                                  | 80 39/20 ...                    same
Pause    | 20 19/70 ... /6020                            | 20 19/70 ... /6020              same
Pause    | 80 19/70 ... /6080                            | 80 19/70 ... /6080              same
1 / 3 / 5 / 6 : 13/72, 26/6c, 21/66, 2e/63 on both       pad == keyboard
```

### 5.4 Cold boot, HD build, default set + jag, pads A and B (`huntjag.py cold --game build/jag_hd --cfg ab --pad a,b --buttons`, STE TOS 1.62, ACSI + HDDRIVER) [obs]
```
BOOT OK machine=ste mem=1024K in_game=True MARKER=b'HNPO' FLAGS=00000003 ... JAG_ST=01 fps 4.8 (10.4 VBL/frame)
pad A Up     N          d0=02 JAG_DIR=02 S1=01000000     pad B Up     N          d0=02 JAG_DIR=02 S1=01000000
pad A Down   S          d0=01                            pad B Down   S          d0=01
pad A Left   W          d0=08                            pad B Left   W          d0=08
pad A Right  E          d0=04                            pad B Right  E          d0=04
pad A A      fire       cf=01 d0=10 S2=2000              pad B A      fire       cf=01 d0=10
pad A B      fire       cf=01 d0=10 S2=0200              pad B B      fire       cf=01 d0=10
pad A C      Return     lastkey 1c/00                    pad B C      lastkey 1c/00
pad A Option Space      lastkey 39/20                    pad B Option lastkey 39/20
pad A Pause  $93=20, again $93=80 (un-pause)             pad B Pause  $93=20, again $93=80
pad A 1 R 13/72, 2 Help 62/7e, 3 L 26/6c, 5 F 21/66, 6 C 2e/63, 7 48/00, 9 50/00   (same for pad B)
pad A #, 0, 8: last key unchanged (unassigned)           (same for pad B)
```
The first cold boot (pad A only, `--cfg a`) gave the same table. The two buttons that leave the 3D loop were tested on the snapshot (`live --keys 4`, `--keys F5`): `4` opens the drone map (screenshot `work/shots/jag/live_4.png`, `$93=00`), `*` opens the game options (`$93=00`); after either the gate is closed and later makes are not injected (`1` ... `9` showed `lastkey` unchanged), as designed.
Floppy build, STE TOS 1.62 (real FDC timing, `huntjag.py floppy --cfg a --buttons`): `in 3D view: True after 91 s`, `MARKER=HNPO FLAGS=3 JAG_W=0002 JAG_ST=01`, the same full table (every direction, fire, C, Option, Pause/Pause, 1 2 3 5 6 7 9).

### 5.5 Layer 3 and held buttons: `live --hold-at-start A` (pad A button held while the patch goes live) [obs]
```
idle (patched)  ... JAG_ST=01 ...      pad A Up N d0=02 | pad A Right E d0=04     (the pad works after the release)
```

### 5.6 Machines (cold boots, default set + jag, HD build unless noted, pad A configured in Hatari) [obs]
```
ST      TOS 1.04 1 MB  BOOT OK in_game=True MARKER=HNPO FLAGS=00000006 JAG_ST=ff  fps 5.0 (10.0 VBL/frame)   (FLAGS bit0 clear: no pad register touched)
Mega ST TOS 1.04 1 MB  BOOT OK in_game=True MARKER=HNPO FLAGS=00000006 JAG_ST=ff  fps 5.0
Mega STE TOS 2.06 1 MB BOOT OK in_game=True MARKER=HNPO FLAGS=00000003 JAG_ST=ff  fps 8.4 (5.95 VBL/frame)   (SCU read answered: refused before any pad register)
TT TOS 3.06 4 MB --mmu true (hunt_ttf.py)   BOOT OK in_game=True MARKER=HNPO FLAGS=0000000b fps=50.00 (53 s)  $8d9f0: ff 00 00 ...  JAG_ST=ff
STE TOS 1.62 1 MB      BOOT OK ... FLAGS=00000003 JAG_ST=01 (pad found, table above)
Falcon TOS 4.04 4 MB, floppy (real FDC timing; `huntjag.py floppy --machine falcon --pb-at 35`, navigation by screen crops):
   BOOT OK MARKER=HNPO FLAGS=0000000b JAG_W=0038 JAG_ST=01
   Up d0=02 JAG_DIR=02 S1=01000000 | Down d0=01 | Left d0=08 | Right d0=04 | A cf=01 d0=10 S2=2000 | B cf=01 d0=10 S2=0200      (every direction and both fire buttons)
   C 1c/00 | Option 39/20 | Pause $93=20 then $93=80 | 1 13/72 | 2 62/7e | 3 26/6c | 5 21/66 | 6 2e/63 | 7 48/00 | 9 50/00       (every key through the game's decoder)
```
No machine showed a bus error or a HALT dialog. The plain ST, Mega ST, Mega STE and TT cold boots ran with a pad configured in Hatari on those machines (Hatari answers on none of them), and the probe said no on all four.
An earlier revision of the probe let `FLAGS` bit3 skip the SCU test; the TT HD run with it went on to layer 2, `$ff9202` bus-errored, the guard caught it and the pad stayed off (`JAG_ST=ff`, in_game True): the guarded read was exercised for real once. The final code never reaches it on a TT.
**Harness note (Falcon)**: the blind navigation of `boot_floppy` (fixed waits) does not reach a real game on the Falcon: the game sits in its demo (attract) mode, where any key, pad or keyboard, returns to the title (`$b048 tst.b $95 / bmi -> jsr $2640`), and the stick/keys change on their own (the unpatched default floppy build shows the same: `$93=88`, `d0=01/08`, last key 13/72, 39/20 with no input). Use the non-blind boot on the Falcon.

## 6. Findings, limits, open items
1. **`FLAGS` bit3 is wrong on the TT HD build** (not caused by this work): the default build (`build/game`, no jag) and the jag build both end with `FLAGS=0000000b` on a TT 3.06 `--mmu true` (`hunt_ttf.py ... --peek 8bff0:8` -> `0000000b`; `ttfalcon.md` recorded 3). The probe reads `_MCH` at `$5a0` at payload entry, where D15R_F5's own jar (`_MCH=$00030000`) is already installed on a TT HD boot. Effect: `snd_core` takes its Falcon branch (12517 Hz, samples doubled) on a TT HD build [INFERENCE: not listened]. The Falcon floppy value 0b is right. `jag_pad` does not depend on it.
2. **Real hardware is untested.** Everything electrical comes from documents and Hatari: the select-to-read gap (15.8 us), word-only access, SCU absence on an STE/Falcon, `$ff9200` low nibble `$f` idle. If a real Falcon answered at `$ff8e01` the pad would be refused there (fail closed); the SCU test is the one assumption that could cost a Falcon user the pad [INFERENCE].
3. A press must last about 40 ms (poll every second VBL). A press shorter than one poll interval is missed.
4. Menus, name entry, the drone map and the game options are mouse driven and have no pad support; the pad's keys are not injected there. After `4` (drone map) or `*` (game options) the player returns with the mouse.
5. The drone key `4` runs 15,632 cycles inside the VBL handler (interrupts masked), longer than one IKBD byte at 7812 baud (10,240 cycles); the first reply byte to the handler's `$16` poll arrives later than that in Hatari's IKBD model [INFERENCE], and the original keyboard path runs the same dispatch inside the IPL 6 ISR with the same masking. Nothing odd was seen after the key in the runs above, but an ACIA overrun was not instrumented (not proven either way). If one shows up on real hardware, move `$b048` to the next ACIA interrupt (a queue drained at `$afde`).
6. Cost 0.47 % of the CPU; it flips some 10-VBL standing frames to 11 (section 4). The pad polling can not be skipped when no pad is plugged in (no way to tell an idle pad from none), so the patch should stay opt-in or be enabled per user.
7. `hn_hz` at 60 Hz: the merge sits in the world block (gated like the real stick); the poll and the keys run on every VBL. Not run at 60 Hz here.
8. Not done: `#`, `0`, `8` are unassigned; Team Tap pads other than AA/BA are not read.

## 7. Reproduce
```
cd games/in_progress/hunter
DEF="p4_ikbd p4_edge p4_poly snd_core hn_credit hn_hz"
python3 tools/huntpatch.py build --only $DEF jag_pad jag_stick --samples build/hunter_snd.bin --out build/jag_hd          # HD
python3 tools/huntpatch.py build --floppy --only $DEF jag_pad jag_stick --samples build/hunter_snd.bin --out build/jag_fl # floppy
python3 tools/huntjag.py live|kbd|prof|inject [--cfg a|b|ab|none] [--pad a,b] [--keys ..] [--stick]
python3 tools/huntjag.py cold --game build/jag_hd --machine st|megast|ste|megaste --cfg ab --pad a,b --buttons
python3 tools/hunt_ttf.py jagtt --machine tt --tos 3.06 --mem 4096 --game build/jag_hd --bus acsi --hatari-opt="--mmu true --configfile $PWD/tools/jag_pad_a.cfg --joy1 none" --peek 8d9f0:16
python3 tools/huntjag.py floppy --machine falcon --pb-at 35 --mem 4096 --cfg a --buttons
```
`tools/jag_pad_{a,b,ab}.cfg`: Hatari pad configs (host keys = pad buttons, listed in the `huntjag.py` docstring); the study's originals are in `reports/jaguar_pad_study_files/`.

## 8. `FLAGS` bit 3 on a TT (follow-up 1) [obs unless marked]

**Users of bit 3.** Only `snd_core.s` reads it (`grep FLAGS patches/*.s`: `btst #3,FLAGS+3.l` at `snd_init0`; `core_floppy.s` and the other patches read bit 0 only). With bit 3 set it takes the "Falcon" branch: mix ring of 512 samples, a second DMA ring `DRING` `$8FC00` with every sample written twice (`snd_expand`), and `move.b #$81,$21(a0)` (`$ff8921`, 12517 Hz) instead of `$80` (6258 Hz).
**Registers touched on that branch**: the STE DMA registers `$ff8900-$ff8921`, `$ff8909` (`movep`), and the Microwire `$ff8922/$ff8924` behind a bus-error guard (`snd_microwire`). **No Falcon-only register** (`$ff8930+`, codec, crossbar) is read or written anywhere in `snd_core.s` (`grep ff89` above). `$ff8921 = $81` is a rate the TT's STE-compatible DMA also has.
**Where bit 3 is set**: `core.s probe`: bit0 set and `_MCH` = `$0003xxxx` in the jar at `$5a0`. On a TT HD boot START has already loaded `D15R_F5.FIC`, whose jar says Falcon (`ttfalcon.md` section 2), so at payload entry the jar is the game's, not TOS's. Observed on a TT (TOS 3.06, `--mmu true`, 4 MB, ACSI + HDDRIVER), default HD build (`tools/huntflags.py tt_before --kind hd --machine tt --game build/game`):
```
[tt_before] hd tt 4096K in_game=True MARKER=b'HNPO' FLAGS=0000000b  $5a0 -> $d0edc jar_MCH=00030000        ($d0edc = D15R_F5's jar in game RAM)
[tt_before]   payload SV: mode=2 ...   $ff8901=03 (DMA control) $ff8921=81 (mode: 80 = 6258 Hz, 81 = 12517 Hz)  SV mode=2
[tt_before]   WAV flags_tt_before.wav: 6.0 s, rms 887, peak 5161
[tt_before]   Hatari trace log (--trace cpu_exception): 10 bus error(s): $f00039/79/b9/f9 at PC=$11384 and $188c88 (game RAM), $fffa40 at $e00486 and $ff8a00 at $e0161e (TOS ROM)
```
**Why `ttfalcon.md` says 3**: those TT cells (and the sentence "TT reports `_MCH` = `$00020000` and stays `FLAGS=3`", section 8) were written when the TT result was read from TOS's jar (the floppy path probes in stage 2, while TOS's jar exists, and bit 3 is sticky) or before the HD payload's probe read F5's jar; the HD value today is `0b`. The floppy TT build still gives 3 (below).
**Effect on a TT (HD, v1.0 as released)** [obs]: sound plays (WAV rms 887 vs 889 after the fix), the DMA runs at 12517 Hz with doubled samples; the 10 bus errors are the game's and TOS's own hardware probes (none from the payload: `snd_core` touches no register that faults on a TT). The cost is the Falcon branch's extra work (`snd_expand`, 512-sample ring topped up more often) [INFERENCE: not measured]. So **no crash, no silence, audibly the same: the released v1.0 HD does not need an emergency re-release for this**; it should simply carry the fix in the next build.

**Fix (in `patches/core.s`, the delivery core, the `probe` routine shared by the HD payload entry and the floppy stage 2)**: after the cookie says Falcon, bit 3 is set only if `tst.b $ffff8e01.w` bus-errors (the TT and the Mega STE have the SCU there, the Falcon has none; same test as `jag_pad`, bus-error guarded the same way as the DMA probe). It needed 34 more bytes in the entry segment, so the load-hook segment moved from `$8BB40` to `$8BB60` (`CORE_ORGS["hook"]` in `huntpatch.py`; its end `$8BBEA` is below the site table `$8BC00`). No other patch is involved.
**Before and after** (`huntflags.py`; default HD set `build/game` vs `build/game_fix`, default floppy `build/floppy` vs `build/floppy_fix`):
| machine / build | FLAGS before | FLAGS after | `$ff8921` | WAV rms / peak (before -> after) | bus errors from the payload |
|---|---|---|---|---|---|
| STE 1.62, 1 MB, HD | `03` | `03` | `80` both | 882 / 5207 -> 881 / 5233 | none |
| TT 3.06 `--mmu true`, 4 MB, HD | **`0b`** | **`03`** | **`81` -> `80`** | 887 / 5161 -> 889 / 5477 | none (10 game/TOS probes both) |
| TT 3.06 `--mmu true`, 4 MB, floppy | `03` (`ttfalcon.md`) | `03` | `80` | - -> 885 / 5871 | none |
| Falcon 4.04, 4 MB, floppy | `0b` | `0b` | `81` both | 566 / 3711 -> 563 / 3711 | the guarded SCU read at `$8bb3a` (`reading $ffff8e01`): the Falcon bus-errors there, bit 3 stays set |
Raw lines of the runs: `[tt_after] ... FLAGS=00000003 ... $ff8921=80 ... rms 889, peak 5477`, `[falcon_after] ... FLAGS=0000000b ... reading $ffff8e01 at PC=$8bb3a (payload $8ba00-$aefff) x1`, `[tt_floppy_after] ... FLAGS=00000003 ... $ff8921=80 ... rms 885, peak 5871`.
**Re-release?** The bug is real (wrong sound branch on a TT HD) but harmless in Hatari's TT; a fixed `FILES/P` is needed to correct it, and `core.s` changed the payload bytes for every build (HD and floppy), so the next release carries it. Whether a real TT is happy with `$81` is untested [INFERENCE: it is a standard STE-DMA rate].

## 9. Cost rework (follow-up 2) [obs]

**New poll** (`jag_pad.s`): one row group per VBL, round robin 4, 3, 2, 1; the select written at the end of a VBL settles for the whole VBL and is read at the start of the next (no wait loop, no pipeline, `JAG_W` gone); both registers are read as one long (`move.l ($ff9200)`), masked and compared with the group's last value: a changed value (a press or a release) takes the slow path that rebuilds S1/S2, the stick byte and the key events. Splices are `jmp` out / `jmp` back (24 cycles instead of 36), and after the first VBL the probe re-points the `$c616` jump to the poll (skipping the state test). Where the probe says no it writes the original bytes back to `$c616` and `$c64c`: the unpatched code, 0 cycles. The state block is `$8D9E0-$8D9FF`, `jag_stick`'s blob `$8D9C0`.
Latency: every group is read every 4th VBL (80 ms at 50 Hz, 67 ms at 60 Hz): a press shorter than that can be missed; directions and fire also have 80 ms latency (they sit in groups 4 and 3). The old design polled everything every second VBL (40 ms). Keys are as before: one make per press.
```
$ tools/huntjag.py prof                       (1 MB STE, 1mb_foot_stand, 250 VBL)
pad A configured: 220 VBL hook calls, 220 merge calls: blob 180.0 + merge 52.0 cycles per VBL; net added by the two splices 212.0 cycles per VBL = 0.132 %
no pad          : 220 VBL hook calls, 220 merge calls: blob 180.0 + merge 52.0 cycles per VBL; net added by the two splices 212.0 cycles per VBL = 0.132 %
$ tools/huntjag.py prof --plain-st            (FLAGS as a plain ST: the probe says no)
no pad          : 0 VBL hook calls, 0 merge calls: ... net added by the two splices 0.0 cycles per VBL = 0.000 %
```
(net = blob + merge + 12 per splice jump - 20 for the replaced `bclr` - 24 for the replaced two `move.b`.) Before: 748 cycles per VBL (0.47 %). Detail of the 212: hook jump 12 + `jag_poll` 168 (bclr 20, lea 12, lea 8, `move.l` 12, `move.w J_G` 12, mask 16, next select 50, compare 18, branch 8, exit jump 12) - 20, merge 40.

**Pixel gate, free running** (`huntab_serial.py --base $DEF --only $DEF jag_pad jag_stick --points 1 --flips 1 6 --vbls 400`; the first patched frame is hard-compared; base = the six default patches):
```
                 first-frame work     VBL/frame (window mean)          fps
                 +cycles   %          before -> 748-cycle poll -> now   before -> now
foot_stand:      IDENTICAL +1904  +0.12 %   10.76 -> 10.92 -> 10.80    4.65 -> 4.63
foot_walk:       IDENTICAL +1704  +0.12 %    9.00 ->  9.00 ->  9.00    5.55 -> 5.55
car_stand:       IDENTICAL +10436 +0.82 %    8.78 ->  8.95 ->  8.84    5.70 -> 5.66
car_drive:       IDENTICAL +1268  +0.13 %    7.00 ->  7.00 ->  7.00    7.14 -> 7.14
car_turn:        IDENTICAL +1248  +0.12 %    7.00 ->  7.00 ->  7.00    7.14 -> 7.14
hills_stand:     IDENTICAL +1280  +0.13 %    6.69 ->  6.91 ->  6.79    7.47 -> 7.36
4mb_foot_stand:  IDENTICAL +1904  +0.12 %   10.01 -> 10.48 -> 10.12    5.00 -> 4.94        ALL IDENTICAL
```
Three points per scene for the four that changed (`--points 3`): `foot_stand 10.78 -> 10.86`, `car_stand 8.82 -> 8.86`, `hills_stand 6.70 -> 6.80`, `4mb_foot_stand 10.01 -> 10.13` VBL/frame, all IDENTICAL on the hard comparison; `--lock --flips 1 6` on foot_stand, foot_walk, car_drive, car_turn: IDENTICAL.
**Result: not zero, but 3 of 7 scenes are exactly unchanged and the others move by 0.04-0.13 VBL per frame (was 0.00-0.47).** Strictly zero is not reachable with any per-VBL cost: the standing frames sit within a few hundred cycles of a VBL boundary (`REPORT.md`: 1,602,020 of 1,602,560), so even the unavoidable floor of the two splices (hook jump 12 + merge 40 = 52 cycles per VBL, before any pad work) moves some frames. What is left to cut: the 40-cycle merge could be installed only while a direction is held (self-modifying code, needs an instruction-cache clear on the Falcon: not done), and the poll core (168) is read + advance + compare. Idle pad skipping (poll less when idle) would add 320 ms detection latency or need the all-groups-at-once read that a Team Tap decodes differently: not done.

**Button tables re-run on the new code** [obs]: live snapshot (pad A, every button: directions, A/B fire, C, Option, Pause/Pause, 1 2 3 5 6 7 9, unassigned `#` `0` `8`); cold boot HD STE 1 MB with pads A and B (`cold --cfg ab --pad a,b --buttons`: every row of both pads, e.g. `pad B Up (w) d0=02 JAG_DIR=02 S1=01000000`, `pad A Pause $93=20` then `$93=80`); cold boot floppy STE (real FDC timing, 88 s to the 3D view) and Falcon floppy (102 s, non-blind navigation): the same full table, `sites $c616=4ef90008d620 $c64c=4ef90008d9c04e71` (jump re-pointed to `jag_poll`).
Machines (HD, pad A configured in Hatari): `ST FLAGS=6 JAG_ST=ff sites $c616=08ad0003008f $c64c=102d00d11b4000d0 fps 5.0`; `Mega ST` the same; `Mega STE FLAGS=3 JAG_ST=ff` original bytes restored, fps 8.4; `TT 3.06 --mmu true 4 MB FLAGS=00000003 (fixed core) JAG_ST=ff`, `$c616: 08ad0003008f`, `$c64c: 102d00d11b4000d0`, fps 50.20: the sites are restored on all four, the game runs the unpatched code there.
`huntpatch.py verify` ALL OK, `build` and `build --floppy` of the default set and with jag succeed.
