# Populous: hot paths in a busy scene

Second pass, 2026-11-11. Replaces the draft, which profiled the GAME LOST dialog. Scene `work/snapshots/busy_castles.sav` (77-83 buildings, 106 peep slots, castles in view, no input), 8 MHz, 1 MB STE. Profile `work/prof/busy_castles.txt` (500 VBLs, 75,408,164 cycles in the top 20,000 addresses, 30 frames). Buckets are call targets (`jsr`/`bsr`) of `work/dumps/busy.bin`. Algorithms and the fixes are in `algorithms.md`.

A frame is 2,513,605 cycles = 15.7 VBLs.

## Top 10 by exclusive cycles

| # | Routine | Cycles | Share | Calls per frame | Role |
|---|---|---:|---:|---:|---|
| 1 | `$14314` | 18,674,708 | 24.8% | 91.2 | terrain / object tile blit, 32 x 24, mask + 4 planes |
| 2 | `$181d6` | 14,416,512 | 19.1% | 1,389 | "may a walker step from this cell by this offset": off-map, rock, water |
| 3 | `$18244` | 10,492,536 | 13.9% | 77.2 | land score around a building (17 cells), once per building per turn |
| 4 | `$14a28` | 7,716,296 | 10.2% | 1 | copy the 32,000-byte clean background to the back buffer |
| 5 | `$db8a` | 6,508,632 | 8.6% | 1 | the peep loop (compiled C) |
| 6 | `$16e20` | 4,606,656 | 6.1% | 15.7 | draw the mouse pointer, in the VBL |
| 7 | `$20796` | 2,245,876 | 3.0% | 191 | 32-bit multiply helper of the C compiler |
| 8 | `$16954` | 1,342,056 | 1.8% | 6.2 | 16-wide masked sprite (people) |
| 9 | `$f332` | 1,179,076 | 1.6% | 2.0 | settle search of a walker |
| 10 | `$143a2` | 969,144 | 1.3% | 1 | the 8 x 8 cell loop that calls #1 |

Next: `$16dea` pointer restore 1.3% (15.8 per frame), `$1ff14` 0.9%, `$167b0` minimap dot 0.9% (50 per frame), PP's resident code at `$d0000`-`$d3fff` 2.0%, the IKBD handler `$1fff2` 0.6%.

Excerpts (the tile blit and the pointer are listed in `algorithms.md` sections 3 and 4):

```
; #2 $181d6: 346 cycles per call, most of it frame
0181d6  link.w a5,#0 / movem.l d1-d4/a0,-(a7) / clr.l d0
0181e0  move.w $8(a5),d2 / move.w $a(a5),d3 / beq.b $1823a
0181ea  move.w d2,d4 / add.w d3,d4 / blt.b $1822a / cmp.w #$1000,d4 / bge.b $1822a
0181f6  andi.w #$3f,d3 / cmp.w #3,d3 / ble.b + / ori.w #$ffc0,d3
018204  andi.w #$3f,d2 / add.w d2,d3 / blt.b $1822a / cmp.w #$3f,d3 / bgt.b $1822a
018212  lea $36eb6,a0 / ext.l d4 / adda.l d4,a0
01821c  cmpi.b #0,(a0) / beq (water: 3) / cmpi.b #$2f,(a0) / beq (rock: 2)
01823a  movem.l (a7)+,d1-d4/a0 / unlk a5 / tst.w d0 / rts

; #4 $14a28
014a3c  move.w #$1f3f,d0
014a40  move.l (a1)+,(a0)+
014a42  dbra d0,$14a40

; #7 $20796 (391 cycles per call for index * 22 or * 46)
020796  link.w a6,#0 / movem.l d0-d3/d7,-(a7) / clr.w d7
0207a0  move.l $8(a6),d1 / bge + / moveq #1,d7 / neg.l d1
0207b6  ... mulu.w d2,d3 / mulu.w d1,d0 / mulu.w d1,d2 ...
0207de  move.l d3,$c(a6) / movem.l (a7)+,d0-d3/d7 / unlk a6 / move.l (a7)+,(a7) / tst.l $4(a7) / rts
```

## Frame split

| Part | Routines | Share |
|---|---|---:|
| World logic | `$181d6`, `$18244`, `$db8a`, `$20796`, `$f332`, `$101de`, `$ef8a`, `$20724` | 46.7% |
| Terrain and people drawing | `$14314`, `$143a2`, `$14a28`, `$16954`, `$168e8`, `$1680e`, `$145bc` | 39.2% |
| Pointer in the VBL | `$16e20`, `$16dea` | 7.4% |
| Minimap dots, sound calls | `$167b0`, `$166f0` | 1.4% |
| IKBD handler, button routine, PP's resident code | `$1fff2`, `$16c96`, `$d0000`.. | 3.2% |
| Rest (`$1ff14` 0.9%, others) | | 2.1% |

At the start of a world (9 peeps, `work/prof/idle_start.txt`, 43.4M cycles in 325 VBLs) the same list reads: tiles 39.8%, background copy 22.5%, pointer 7.4%, `$181d6` 5.8%, `$18244` 4.3%, peep loop 3.5%.

A hilly view (`busy_quake_volcano.sav`, `work/prof/busy_hilly.txt`, 21 frames of 2,829,528 cycles): `$181d6` 19.4%, tiles 16.0% (66 per frame), `$18244` 14.5%, background 9.1%, peep loop 8.9%, pointer 6.2% + 1.3%, **`$17078`-`$171cc` 5.4%** (the timer-A sample interrupt while the volcano sound plays), cliff faces `$1457e` 3.7%, multiply 3.0%.

## Wasted work, table candidates, blitter candidates

- Wasted: the land score (33.0%), the unchanged tiles (24.8%), the pointer redraw (7.4%): `algorithms.md` section 8.
- Tables: `algorithms.md` section 7. None is worth more than 1% except the multiply helper's fast path (about 2%).
- Blitter:
  - background copy: no gain over `movem` ([INFERENCE] 16,000 words x 8 cycles = 128,000 cycles of bus time, against 152,700 measured for Populous 2's `movem` copy of the same 32,000 bytes; the present loop costs 257,000). If used, chunk it (4 rows per chunk in Powermonger) because the game sends `$0d` to the IKBD every VBL and reads a 6-byte reply through a one-byte ACIA, exactly the situation of `powermonger/work/notes/buserr.md`.
  - tiles: [INFERENCE] not a blitter candidate. A masked 4-plane tile needs two blitter operations per plane (AND with the mask, OR with the data), 8 blits of 2 words x 24 rows per tile, and the register set-up per blit is of the same order as the 24-row CPU loop. Midwinter 2 found the same for short spans. Not planned; change A in `algorithms.md` removes the tiles instead.
  - sprites and pointer: too few (6 + 16 per frame); the pointer goes away with `p4_ptr`.

## Sound

The game has the Bullfrog timer-A sample player (the draft said none was found):

```
016ffc  divu.w d0,d2                       ; timer data from the sample rate
017058  move.l #$1717e,$134                ; timer-A vector
01717e  ori.w #$700,sr / movem.l d0-d3/a0,-(a7)
017188  move.l $2499c,d3 / movea.l $24994,a0 / move.b (a0,d3.l),d0
01719c  lsl.w #3,d0 / move.l $171f8(pc,d0.w),d1 / move.w $171fc(pc,d0.w),d2
0171a8  movep.l d1,-$7800(a0) / movep.w d2,-$7800(a0)      ; three YM volumes
0171b0  addq.l #1,d3 / cmp.l $24998,d3 / bge (end or loop)
0171c4  bclr #5,$fffa0f / rte
```

It only runs while an effect sound plays (5.4% in the volcano window, 0 in the two quiet profiles).
