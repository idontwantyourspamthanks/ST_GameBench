# Populous: baseline

Scene: the opening map, 1 MB STE. Profile of 450 VBL: 64,212,560 cycles, of which 88.1% is the spin at `$1d02a`.

```
1d020  move.w  #$2, $3d566
1d02a  move.w  $3d566, d0
1d030  bne.b   $1d02a
```

`$3d566` is cleared by the ACIA handler at `$16cc4` (`move.w #0,$3d566`) when bit 2 of the packet byte at `$2478a` is set. With no mouse motion the game sits in that spin. Calls of the loop head `$180f4`: **2 per 200 VBL at 8 MHz and 2 per 200 VBL at 16 MHz** (0.5 Hz). Same rate at both clocks, so this scene does not speed up with the CPU; it is waiting, not computing. That is not a world-speed measurement: no walker or population word was tracked. Treat "coupled or not" as not yet measured. The non-wait work in that window was 7,653,216 cycles.

`$ff8201` flips in 250 VBL: 0. There is no double buffer on this screen.
