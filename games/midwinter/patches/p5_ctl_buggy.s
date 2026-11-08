; name: p5_ctl_buggy
; default: no
; site: $13618
; note: P5 direct controls, part 2 of 2 (needs p5_ctl_turn; work/notes/p5_controls.md).
;       Snow-buggy exertion test: `move.w $24faa.l,d0` compared the yoke accumulator with its
;       previous value ($1413a) and added $28 to the exertion $1354c whenever it changed.
;       p5_ctl_turn consumes $24faa inside the same step ($135d0 -> $12fe2), so it is always 0
;       here and the test would never fire. Read the turn of this step ($15110, written by
;       p5_ctl_turn) instead: same size, the exertion again follows changes of the steering.
        org     $13618
        move.w  $15110.l,d0
