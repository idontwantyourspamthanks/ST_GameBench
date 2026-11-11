; name: test_walk2
; default: no
; site: $1cd0
; orig: 33f900002026000393fa
; note: TEST ONLY: the IKBD packet handler's x copy ($1cd0 `move.w $2026.l,$393fa.l`) takes PX (test_walk's data, PB+$6f00) instead; see test_walk.
        org     $1cd0
        move.w  PB+$6f00.l,$393fa.l
