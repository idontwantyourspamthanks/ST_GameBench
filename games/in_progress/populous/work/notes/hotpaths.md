# Populous: hot paths

Profile `work/notes/baseline.md`, wait spin removed (7.65M cycles). Dump `work/dumps/genesis_start.bin`.

| share of non-wait | where | what |
|---|---|---|
| 33.3% + 10.6% + 9.6% + 6.8% | `$16ec0`, `$16e00`, `$16e80`, `$16f00` | one routine |
| 9.2% | `$1ffc0` | ACIA handler (`$118` = `$1ffc8`) |
| 5.1% | `$d1040` | TOS |
| 2.8% | `$20000` | follows the ACIA handler |
| 2.4% + 1.9% | `$d01c0`, `$d0200` | TOS VBL `$d018e` |

The routine at `$16eaa` (the 60% block) is a masked sprite blit. It rotates five words by `d5` and merges them into the screen:

```
16eac  move.w (a3)+, d0      ; five source words
16ebe  ror.l  d5, d0
16ec0  ror.l  d5, d1
16ec2  ror.l  d5, d2
16ec4  ror.l  d5, d3
16ec6  ror.l  d5, d4
16ec8  move.w (a4), (a6)+    ; save under
16eca  and.w  d0, (a4)
16ecc  or.w   d1, (a4)+
16f0c  dbra   d7, $16eaa
16f10  rts
```

No `$ff8a00` (blitter) literal in the dump. The blit is the blitter candidate, and it is the same shape as Powermonger's sprite blit (shift, mask, merge), not the same code. YM register `$ff8800` is written at `$16418` (`move.b #$e,$ff8800`; read back; `andi.b #$f8`; `or.b d0`; `move.b d1,$ff8802`). That is a port-A write, not a timer sample player, and it was not in the profile. No sample player was found.
