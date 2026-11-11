# Populous 2: baseline

Scene: map, query panel open, 2 MB STE, TOS 1.62.

Profile of 200 VBL, 27,310,956 cycles:

| share | bucket | what |
|---|---|---|
| 50.0% | `$2e980` | the spin `tst.b $345bb; beq` at `$2e9aa` |
| 35.9% + 6.0% | `$2f500`, `$2f580` | unrolled copy, see hotpaths |
| 4.1% | `$2f480` | the loop that calls it |

VBL handler, installed at `$2e948` (`move.l #$2e9b4,$70`):

```
2e9b4  st.b    $345bb
2e9ba  addq.w  #1, $345bc
2e9c0  rte
```

Passes of `$2f438` per 200 VBL: **193 at 8 MHz, 192 at 16 MHz**. One pass per VBL at both clocks. The world rate was not measured (no walker or population address yet). What was measured is the frame loop: it waits for the VBL flag, so it does not run faster at 16 MHz while a pass fits in one VBL. At 8 MHz the pass already costs about half the frame (the spin is 50%), so a busier view can miss VBLs and then 16 MHz would pull ahead. That case was not set up.
