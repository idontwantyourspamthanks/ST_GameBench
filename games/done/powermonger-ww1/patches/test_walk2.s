; name: test_walk2
; default: no
; site: $ee0
; orig: 33f90001d2b20002edb2
; note: TEST ONLY, part 2 of 3 of test_walk: the IKBD packet handler's copy of the pointer x (`move.w $1d2b2.l,$2edb2.l`) becomes `move.w PX.l,$2edb2.l` (PX = $77c02).
        org     $ee0
        move.w  $77c02.l,$2edb2.l
