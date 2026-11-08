# MW1 ski view: navigation, state variables, frame mechanism, why the game drops back to Decisions

All of this is from a 1 MB STE, TOS 1.62, Hatari 2.6.1 run of the HAGA build, with RAM dumps in `work/dumps/`
(`ram_ski_stand.bin` = first frame of the ski view, `x_exit.bin` = taken just after a forced exit).
Addresses are RAM addresses of the running game. Disassembly is `tools/m68dis.py <dump> <addr> --end <addr>`.

## Navigation (what `MW1.boot_to_game` does)

Screenshot coordinates (832x588 frame; `h.goto` homes the pointer, then moves):

| step | action | evidence |
|---|---|---|
| cold boot | wait 25 s, then SPACE every 4 s until `work/ref/options_play.png` matches in box (250,325,580,450) | Game Options screen |
| control mode | click icon MOUSE (160,258) / JOYSTICK (264,258) / KEYBOARD (368,258) | label under the icon changes MOUSE / STICK / KEYS; RAM: `$24b7e`,`$24b80`,`$24b82` = $ffff for the selected one (M: ffff,0000,0000; J: 0000,ffff,0000; K: 0000,0000,ffff). Handlers `$10960` (mouse: `clr.w $24b82 / clr.w $24b7e`...) and `$10970` (keyboard: `move.w #$ffff,$24b82.l`, `clr.w $24b7e`, `clr.w $24b80`) |
| toggles | MORTARS (470,258), BOMBERS (572,258), TRAINING (673,258) | `$10986: not.w $2c17e.l`, `$1098e: not.w $2c17c.l`, `$10996: not.w $2c180.l`. `$10a7a/$10a9a` draw the label when the word is non-zero, so $ffff = ON. Defaults: mortars ON, bombers ON, training OFF |
| PLAY | click (415,385), wait 12 s | The Team screen |
| Stark | click (178,170), wait 6 s | personality display |
| Decisions | click (450,425), wait 6 s | Decisions screen (skier picture) |
| Skiing | click (384,424), wait 10 s | ski view, HUD clock 06:00 |

`boot_to_game('M')` raised no exception in 2 consecutive cold boots (113 s each) and a third (116 s) that wrote the
stand snapshot; the arrival check is `MW1.in_ski()` (see below).

## Frame / flip mechanism

`$bd9a` is the flip routine used by the ski loop (and every screen):
```
00bd9a: movem.l d0-d2/a0/a6,-(a7)
00bd9e: lea.l   $2c376.l, a6
00bda4: move.l  $0(a6), d0
00bda8: lea.l   $ff8201.l, a0
00bdae: lsr.l   #$8, d0
00bdb0: movep.w d0, $0(a0)          ; writes $ff8201/$ff8203 from the buffer address
...
00bdc0: move.l  d2, $0(a6) ; move.l d0, $4(a6) ; move.l d1, $8(a6)   ; rotates three buffer addresses
00bdcc: move.w  $8c(a6), d0 ; addq.w #1,d0 ; cmp.w #3,d0 ; ... move.w d0,$8c(a6)
00bdde: move.l  $0(a6), $12d0a.l    ; $12d0a = current draw buffer
```
It is a TRIPLE buffer: `m $2c376 16` read `00 06 80 00 | 00 07 80 00 | 00 05 80 00`, so the buffers are
`$068000/$078000/$058000` (`$ff8201` takes the values 5,6,7, `$ff8203` stays $80).
`b ($ff8201).b ! ($ff8201).b` logged `$ff8201 = $5, $7, $6, $5, $7, $6 ...` (raw log, standing in the ski view),
so the default `flip_reg` `($ff8201).b` counts presented frames correctly (it changes at every flip because the
three values differ). A `b pc = $bd9a :trace` counter agreed (9 hits per 100 VBL vs 9 $ff8201 changes).
Two other flip routines exist (`$bdec` double buffer, `$12a80` triple buffer with `$12cfe..`), not used in the ski view
(0 hits over 100 VBL).

## The ski action mode loop

* Entry: `$125f6: jsr $1498a.l` inside `sub_0125a0` (`$125de: move.w #$0,$1efde.l` before it, `$12602: move.w #$1,$1efde.l`
  after it). So **`$1efde` is 0 while an action mode runs and 1 on all menu screens** (dumps: ski 0, Decisions 1, options 1).
* Main loop `$14ac0` (`bsr.w $14e00` = one frame) leaves on: `$14dfc` != 0 (dead/forced, exit at `$14b08`), `$12d76` != 0,
  `$14dfe` != 0 (M key), `$14ef6` != 0 (X key: `$14f12 cmp.b #$58,d0` then `$14f1a: move.w #$1,$14ef6.l`;
  `$12afc` holds the last key as ASCII).
* Per-frame simulation `sub_013236` (`$13236..$1327c`): `$13236 bsr $12fe2` (turn), `$1323a move.w $12c98.l,$15114.l`,
  `$13244 bsr $141ce`, `$13248 bsr $14530` (move), `$1324c bsr $13078`, ... Everything is once per loop pass, so the
  motion is per frame (confirmed by the flip trace in `baseline.md`: distance per frame is the same at 8 and 16 MHz).

## State variables (1 MB TOS 1.62 image)

| var | meaning | evidence |
|---|---|---|
| `$12c60` long | X world position (window centred on $6400; bounds $1388..$b478) | `$14562: add.l d0,$12c60.l` (d0 = sin(heading)*speed>>16), bounds check `$1457a cmp.l #$1388,d0 / $14584 cmp.l #$b478,d0`; moved in all walk dumps: `66fc -> 68c3 -> 6c5d` |
| `$12c64` long | Z world position | `$14568: add.l d1,$12c64.l`; heading 0 moves +Z (observed: z 25600 -> 29868 at heading 0) |
| `$12c68`/`$12c6a` word | cell indices X/Z (position / $200) | `$15336: move.w d3,$12c68.l` after `divu.w d0,d3` with `d0=$12c5a` ($200) |
| `$12c6c`/`$12c6e` word | position within the cell | `$15346..` (remainder) |
| `$15112` word | speed (0 standing; ~$f8..$180 walking; HUD mph shown as 47 at $f8) | `$14550: move.w $15112.l,d2` then `muls.w d2,d0 / muls.w d2,d1` at `$14556/$14558`; read 0 standing, $f8/$eb walking |
| `$12c98` word | master heading (0..1023 used) | `$13014..$1301a: add.w d1,$12c98.l` in the turn routine `sub_012fe2` |
| `$15114` word | per-frame copy of the heading read by the move routine | `$1323a: move.w $12c98.l,$15114.l`, `$1453a: move.w $15114.l,d0 / andi.w #$3fe,d0` (table `$1c6bc`, sin at +0, cos at +$100) |
| `$24faa` word | mouse X accumulator, clamped +-$200 | `$12fe2..$13004` |
| `$24fae` word | mouse Y accumulator (speed command) | `$13022` |
| `$12c5e` word | terrain height at the player (changes with the ground), NOT muscle power | read 0x323, 0x2de, 0x2db while walking over ground |
| `$19cd4`/`$19cd6` word | global map position, adjusted when the window is recentred | `$15300: add.w d1,$19cd4.l`, `$15306: sub.w d2,$19cd6.l`, read `02ac 027c` after a walk |
| `$1efde` | 0 in an action mode, 1 on menus | above |
| `$14dfc` | "action mode over" flag (1 = forced exit) | `$14ac4: tst.w $14dfc.l` in the loop |

Turning: `sub_012fe2` makes the turn rate a cubic function of the mouse accumulator
(`$13004: move.w d0,$24faa.l; $1300c: muls.w d0,d1; $1300e: asr.l #$6,d1; $13010: muls.w d0,d1; $13012: swap d1;
$13014: move.w d1,$15110.l; $1301a: add.w d1,$12c98.l`) and adds it to the heading **once per frame**. The accumulator keeps its value until the mouse comes
back, so turning is a persistent rate per frame (the "yoke" model MW2 had): at 150 px of offset the heading moved about
6-14 units per second at 8 MHz, i.e. about 1-3 units per frame. Heading 0 = +Z, 256 = +X, 512 = -Z, 768 = -X (observed
from the sign of the position change).

Speed: the walk command (left click) ramps `$15112` up; the ground slope then changes it every frame (read 53, 311, 386,
270, 160, 36, 0 along a run). A walk that meets an uphill stops by itself (speed 0, seen at z = 20510, 31960, 27661).

## Why `ski -> Decisions` happened in the first try (clock 06:02 -> 06:22)

Not the X key (`$12afc` stayed 0; the `X` path sets `$14ef6`, which stayed 0) and not the time. A change watch on
`$14dfc` caught the write:
```
$14dfc = $1
1. CPU breakpoint condition(s) matched 1 times.
  ... PC after the write: 00020622 4e75 rts      (so the write is `$2061a: move.w #$1,$14dfc.l` in sub_0205f0)
  m $12afc 2 -> 00 00 ; m $14dfc 2 -> 00 01
  A5 0001CE02  A6 00020594
```
`$2061a` is the end of the routine whose entry is `$20594`: it is the per-frame routine of an *enemy object* in slot
`$1ce02`. The routine counts `$200e4` down, shrinks `$200e2` by `$7b7` per frame (the range to the player),
tests the distance to the player with `sub_01f884` (`|dx|,|dy| < $1f8bc`: `$205aa move.w #$c8,$1f8bc.l`,
`$205ee move.w #$5a,$1f8bc.l`, `$205f6 jsr $1f884.l`, `$205fc bne $20622`, `$20600 tst.w $13f28.l`, `$2061a
move.w #$1,$14dfc.l`) and when the object reaches Stark ends the action mode.
The slot is armed by `sub_0201e0`:
```
0201e0: move.l a4,-(a7)
0201e2: tst.w  $2c180.l            ; TRAINING flag
0201e8: bne.w  $202c2              ; training ON -> never spawn
0201ec: btst.b #$2,$1fa08.l        ; $1fa08 = $7 set at ski entry ($13eb4 / $1314c)
...
020284: move.l #$20594,$28(a4)     ; the routine seen above
```
So with the Game Options defaults (Training OFF) an enemy attack object periodically spawns, approaches, and on
contact throws Stark out of the action mode into the Decisions screen. The same screen also had `sub_0200e8`
(mortar shells, gated by `$2c17e`) and `$1ffe2` (bombers, gated by `$2c17c`). Switch MORTARS and BOMBERS off
and TRAINING on (`boot_to_game` does, and checks the three words in RAM) and the ski view stays up (in one such session the HUD clock
ran 06:00 -> 07:18 with standing, walking and turning, and no exit, `/tmp` screenshots in the session log; see `baseline.md`).
[INFERENCE] which in-game object `$20594` is (an enemy sniper/aircraft shot) is not established; what is established is
the flag that gates it and the exit it triggers. Other forced exits exist (building proximity `$13bb0`, a fall `$13bba`,
loop in `$12f3e` for `$12c5e == 0`) but none of them fired in the captured run.

## Quirks worth knowing

* The turn "yoke" persists: with the pointer displaced the heading keeps changing; undo the offset to stop.
  `xdotool` moves of +150 px were ignored once by the game (pointer at 662, no accumulator change) and worked later;
  `MW1.turn_to` verifies the heading actually changes and retries.
* A walk stops on its own at the next rise (`speed` 0), so `1mb_ski_walk` is a ~5000-unit downhill run:
  the world position stops changing after it (about 200 VBL at 8 MHz).
* `Hatari.state` (the memstate path) clashes with a method called `state`, hence `MW1.gstate()`.
