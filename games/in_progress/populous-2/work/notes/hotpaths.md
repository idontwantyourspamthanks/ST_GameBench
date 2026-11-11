# Populous 2: hot paths in a busy scene

Second pass, 2026-11-11; replaces the draft (which profiled the title credits). Scene `work/snapshots/busy1.sav` (147 people objects, enemy town in view, no input), 8 MHz, 2 MB STE. Profile `work/prof/busy1.txt`: 525 VBLs, 75,374,172 cycles, 58 frames of 1,299,555 cycles (8.1 VBLs). Ranges are address ranges of `work/dumps/busy1.bin`.

## Top 10 by exclusive cycles

| # | Code | Cycles | Share | Per frame | Role |
|---|---|---:|---:|---|---|
| 1 | `$1e15e`-`$1e22e` | 14,923,024 | 19.8% | 191 calls, 933 rows | terrain strip blit: 2 x 16 pixels x 8 rows, mask + 4 planes |
| 2 | `$25168`-`$25652` | 10,534,748 | 14.0% | 111 checks, 28 full scans, 457 ring scans | land score around each building (`$25168`, `$251d8`, `$252d8`) |
| 3 | `$2309a`-`$24a92` | 9,956,440 | 13.2% | 1 | people state machine |
| 4 | `$1e7b2` | 8,856,832 | 11.8% | 1 | copy the 32,000-byte clean background (`movem.l`, 48 bytes per step) |
| 5 | `$2122e`-`$2218a` | 7,533,328 | 10.0% | 5.9 sprites | masked sprite blit with `ror.l` per word |
| 6 | `$18fa`-`$1b4e` | 5,222,880 | 6.9% | 12.2 (one per VBL) | VBL: button state machine, pointer restore + draw, IKBD poll |
| 7 | `$1bf4` | 2,968,476 | 3.9% | | waiting for the VBL flag |
| 8 | `$20058` | 2,086,084 | 2.8% | 159 | one-pixel plot (`movep.l`) for minimap dots and manna marks |
| 9 | `$24a92`-`$25168` | 1,574,980 | 2.1% | | people helpers |
| 10 | `$1df44`-`$1e15e` | 1,374,364 | 1.8% | 1 | terrain driver |

Next: IKBD handler `$1c42` 1.5%, `$25652`-`$26644` 1.2%, effects objects `$26644` 1.1%, `$27faa` 0.9%, manna marks `$136ba` 0.7%. The timer-A sample player `$2aa4e` took 0 cycles in this window.

Split: drawing 47% (#1, #4, #5, #8, #10, marks), world logic 32.5% (#2, #3, #9 and the three smaller ones), interrupts 8.4%, waiting 3.9%.

Excerpts:

```
; #1 strip rows (compare Populous $14352)
01e172  move.w (a0)+,d0                       ; mask
01e174  move.w (a6),d1 / and.w d0,d1 / or.w (a0)+,d1 / move.w d1,(a6)+     ; x 4 planes
01e194  move.w (a1)+,d0 ... same for the right half from a second strip
01e1b6  lea $90(a6),a6 / dbra d2,$1e172

; #4
01e7c6  movem.l (a0)+,d1-d7/a2-a6 / movem.l d1-d7/a2-a6,(a1) / lea $30(a1),a1 / dbra d0,$1e7c6

; #5 (the same bytes as Powermonger's sprite routine at $123b2..$125bc)
0213b0  moveq #$78,d1 / neg.b d1 / subq.w #1,d2
0213b6  moveq #-1,d3 / move.w (a1)+,d3 / ror.l d0,d3            ; mask
0213bc  moveq #0,d4 / move.w (a1)+,d4 / ror.l d0,d4 / move.w (a0)+,d5 / and.w d3,d5 / or.w d5,d4
0213ea  movem.w d4-d7,-$8(a0) / swap d3 / swap d4 ...

; #2 once per building: is it this building's turn?
025172  move.l a0,d0 / subi.l #$3ff1a,d0 / divu.w #$34,d0 / andi.w #3,d0     ; 872,544 cycles in the window
025182  move.w $3979c,d1 / andi.w #3,d1 / cmp.w d0,d1 / beq (full scan $251d8)
```

## Wasted work

- **Pointer**: restored and redrawn every VBL whether it moved or not (6.9%). Same code and same fix as Powermonger's `p4_ptr`.
- **Terrain**: 191 strips and the full background copy every pass (31.6% with the driver) while 62-64 of the 64 view cells are unchanged from turn to turn (`baseline.md`).
- **Land score**: already spread over 4 turns by the game (`index & 3 == turn & 3`), unlike Populous 1; still 14%.
- **`divu #$34`** to turn an object address into an index, 111 times per frame, 1.2% on its own.

## Table and blitter candidates

- `divu #$34` at `$2517a`: exact table of 5,200 bytes indexed by offset / 4, or the index kept in a spare register by the caller. 1.2%.
- `$136ba` computes manna / cost with `divu d5,d4` per effect and plots up to 4 marks each, every pass (0.7% + part of #8): cache on (manna >> 2, category).
- Sprite shifts (#5): pre-shifted cache or the STE blitter, i.e. Powermonger's `p4_spr`, whose site bytes `7278 4401 5342` are at `$213b0` here. Powermonger gained 8-12% of render cycles with it.
- Background copy: already `movem`; a blitter copy is not faster ([INFERENCE] 128,000 against 152,700 cycles) and would need 4-row chunks (`powermonger/work/notes/buserr.md`: this game polls the IKBD every VBL too, `$1a0a`).
- Strips (#1): 8 rows of 2 words; no blitter case ([INFERENCE] set-up per blit exceeds the loop).
