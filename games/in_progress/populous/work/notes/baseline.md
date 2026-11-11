# Populous: baseline, world speed, pacing

Second pass, 2026-11-11. 1 MB STE, TOS 1.62, Hatari 2.6.1, PP's HAGA build, no patches. It replaces the first draft, whose numbers were taken on the GAME LOST dialog (see "What the draft got wrong").

## The main loop and how it paces itself

`$b54e` is the game loop (compiled C); one pass, top `$b632`, bottom `$bc02`:

```
00b6f4  jsr $14a28        ; copy the clean background (32,000 bytes) to the back buffer
00b728  jsr $da90
00b73a  jsr $143a2        ; terrain + people, 8 x 8 cells
00b7e6  jsr $16954        ; view marker on the minimap
00b7f0  tst.w $3b2b2 / bne ; paused
00b7f8  tst.w $3b2b4 / bne ; paint mode
00b800  jsr $12fc2
00b806  jsr $db8a         ; the world: one turn (addq.w #1,$3c506 at $db96)
00b93a  jsr $d4c0
00b940  jsr $16f16        ; wait for the VBL flag, swap the two buffers, write $ff8201/03
00b946  jsr $200a6        ; key -> ASCII
00b94c  ...               ; keypad scroll, paint keys
00bb88  jsr $11a24 / $d42c ; pointer on the land / on a shield
00bbc4  jsr $c420         ; a fresh click: icons, minimap
00bbfa  jsr $1e750        ; execute both players' queued commands
00bc02  bra $b632
```

The flip (`$16f16`) is the only wait:

```
016f48  tst.w $16d28 / beq.b $16f48          ; flag set by the VBL routine $16d70
016f1a  move.l $3c510,d0 / move.l $3c50c,d1 / move.l d1,$3c510 / move.l d0,$3c50c
016f32  lsr.w #8,d0 / move.l d0,$ffff8200
016f3a  clr.w $16d28
```

So the loop runs as fast as it can, in whole VBLs, with one world turn and one full redraw per pass. There is no timer, no turn limiter and no speed setting. Two buffers: `$4f500` and `$57200` (`$3c510` back, `$3c50c` front); the clean background is a third, `$78000` (`$3b016`). A free-running VBL counter exists: `$16d2a` (long), next to the flag `$16d28`.

## World turns per real second

`world_rate($3c506)` = change of the turn word per emulated second; flips of `$ff8201` counted over the same window.

| Scene (snapshot) | People slots / buildings | 8 MHz: fps, turns/s | 16 MHz: fps, turns/s | ratio |
|---|---|---|---|---|
| start of Genesis (`genesis_start.sav`), 9 peeps | 9 / 2 | 7.5-8.8, 7.35-8.69 | 16.5, 16.45 | 1.9-2.2 |
| flat land, 76-83 buildings, castles in view (`busy_castles.sav`) | 106 / 77 | 3.3, 3.20; 3.2, 3.20 | 6.9, 6.78; 6.9, 6.86 | 2.1 |
| same world after an earthquake and a volcano in view (`busy_quake_volcano.sav`), hills | 130 / 90 | 3.0, 2.97 | 6.375, 6.38 | 2.1 |
| during the earthquake (300 VBL window) | | 3.17, 2.19 | | |
| during the volcano | | 2.33, 2.52 | | |
| after a flood (3 peeps left) | 108 / 1 | 7.33, 6.69 | | |

Raw lines (harness output):

```
start 16 {'vbls': 300, 'flips': 99, 'fps': 16.5, 'units_per_sec': 16.447}
start 8  {'vbls': 300, 'flips': 45, 'fps': 7.5, 'units_per_sec': 7.346}
8  {'vbls': 500, 'flips': 33, 'fps': 3.3, 'vbls_per_frame': 15.15, 'units_per_sec': 3.201}
16 {'vbls': 500, 'flips': 69, 'fps': 6.9, 'vbls_per_frame': 7.25, 'units_per_sec': 6.784}
8  {'vbls': 500, 'flips': 32, 'fps': 3.2, 'units_per_sec': 3.201}
16 {'vbls': 500, 'flips': 69, 'fps': 6.9, 'units_per_sec': 6.860}
hilly 8  {'vbls': 400, 'flips': 24, 'fps': 3.0, 'units_per_sec': 2.968}
hilly 16 {'vbls': 400, 'flips': 51, 'fps': 6.375, 'units_per_sec': 6.385}
```

**Verdict: coupled.** One turn per displayed frame; 2.1 times faster at 16 MHz; and on one machine the world slows from 8.7 to 3.0 turns per second as it fills up. TT and Falcon were not measured: a cold boot on Hatari's TT (EmuTOS and TOS 3.06, GEMDOS drive, 4 MB) passes PP's hardware screen and then loops on bus errors (`Bus Error reading at address $ffff8a00, PC=$3b3422` / `writing at $fffffc3b, PC=$3b4474`, white screen: `work/shots/boot_tt_*.png`). The ACSI-image route used for Powermonger was not tried.

## The copy-protection trap that PP's build leaves armed

Found while building the busy scene: every game ended within about 500 turns. Cause, in the peep loop of `$db8a`:

```
00edec  cmpi.w #$12,-$2(a6) / bne $ee6a      ; only when the loop reaches peep 18
00edf4  move.w -$2(a6),d0 / asl.w #1,d0      ; $24
00ee04  jsr $16020                           ; Supexec: d0 = long at address $24
00ee0c  move.l $21d92,d1 / asl.l #1,d1       ; $2a560421 * 2 = $54ac0842
00ee14  cmp.l d1,d0 / beq.b $ee6a
00ee18  ...  move.w #1,$6(player) for both players / move.w #1,$3d562
```

`$3d562` is the Armageddon flag (`$12e38` sets it too). The original expects `$54ac0842` at address `$24` ([INFERENCE] the key the disk protection leaves there). PP's crack returns that value from `$16042` (`bra $1604a` / `move.l #$54ac0842,d0`) but address `$24` holds `$090d0578` in his build. The text at `$1675a` reads "well bugger me you've found the Protection check ! whos a cleaver little hacker then".

Reproduced with the game's own paint mode and no code change: 31 walkers placed with F1, paint off, and the breakpoint `pc = $ee18` fired with `$3d562` going 0 -> 1 (raw log in this session: "CPU breakpoint condition(s) matched 1 times. pc = $ee18", `0003D562: 00 01`). With 18 or fewer peep slots the check is never reached, which is why the opening looks fine. With it armed, walkers stop settling (`$ef8a` takes the Armageddon branch), gather and fight, and the game ends (GAME WON at turn 750, no building ever founded: `work/shots/s2_scene2.png`). With `$ee16` changed from `beq` to `bra` (one byte, `w $ee16 $60`, applied live for the measurements above) 58 peeps were in buildings 70 turns after the same start.

**All busy-scene numbers in these notes were taken with that one byte changed.** It is the first patch the plan needs (`PLAN.md` item 0), and it is PP's bug, not ours.

## How the busy scene was made (reproducible)

`tools/populous.py`: `Populous.busy_scene()`. From `genesis_start.sav`: change `$ee16`; load a helper of about 500 bytes at `$70000` (free: `$5eefc-$77fc7` is zero in the dumps) and point the `jsr $da90` at `$b728` at it for one pass. The helper sets every non-zero vertex height to 1, calls the game's own `$c12c(0,0,63,63)` and `$c2b8`, places 36 and 42 walkers of the two sides with the game's own paint routine `$114c4`, gives every peep 300 life, restores the `jsr` and continues. Then the game runs untouched. Effects were issued as the game's own commands (`w $21e4a 03 2c 20` = earthquake at the view, `06` volcano, `0e 00 04` flood) after raising manna (`$3b270`).

## Per-frame invariants (evidence for `algorithms.md`)

Fourteen consecutive turns of `busy_castles` were captured at `$b728` (`savebin` of `$33c22`-`$3d621`, one breakpoint per turn value).

```
turn 1598: houses 83 results changed 0; map_blk cells changed 0, map_bk2 0, map_alt 0
turn 1599: houses 83 results changed 0; map_blk cells changed 4, map_bk2 0, map_alt 0
turn 1601: houses 83 results changed 1; map_blk cells changed 4, map_bk2 0, map_alt 0
turn 1610: houses 83 results changed 3; map_blk cells changed 5, map_bk2 0, map_alt 0
house-turn evaluations 1078 changed 5
1598 view cells changed: blk 0 alt 0 bk2 0 | cells with peeps 5 water cells 0 3b260 1
1599 view cells changed: blk 0 alt 0 bk2 0 | cells with peeps 5 water cells 0 3b260 0
... (13 lines, all "blk 0 alt 0 bk2 0"; cells with peeps 4-5; $3b260 alternates)
```

"results" are the three outputs of `$18244` computed by a Python model of `$181d6` + `$18244` on each capture [INFERENCE: the model was written from the listing and not yet checked against the routine's real outputs].

## What the draft got wrong

- Its "88% spin at `$1d02a`" and "0.5 passes per second at 8 and 16 MHz" were measured on the GAME LOST dialog: the snapshot's three walkers die around turn 1,064 and the dialog waits for a click. `$180f4`, which it called the loop head, is the text renderer.
- The screen is not one buffer at `$40000`: `$ff8201/03` = `$04`, `$f5` is `$4f500`, and it flips with `$57200` every pass (33 flips in 500 VBLs in the busy scene).
- "VBL is still TOS, so the pointer is not drawn in the VBL" was wrong: `$70` = `$d018e` runs the VBL queue, and the game puts its routine `$16d70` into a free slot of that queue (`$16c26`-`$16c4a`: `movea.l $456,a0` ... `move.l #$16d70,(a0)`). It runs every VBL (pointer, buttons, IKBD poll, flag, counter).
