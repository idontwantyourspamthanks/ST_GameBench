; name: test_walk3
; default: no
; site: $1cda
; orig: 33f900002028000393fc
; note: TEST ONLY: the IKBD packet handler's y copy ($1cda `move.w $2028.l,$393fc.l`) takes PY (test_walk's data, PB+$6f02) instead; see test_walk.
        org     $1cda
        move.w  PB+$6f02.l,$393fc.l
