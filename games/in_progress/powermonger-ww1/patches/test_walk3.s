; name: test_walk3
; default: no
; site: $eea
; orig: 33f90001d2b40002edb4
; note: TEST ONLY, part 3 of 3 of test_walk: the pointer y copy (`move.w $1d2b4.l,$2edb4.l`) becomes `move.w PY.l,$2edb4.l` (PY = $77c04).
        org     $eea
        move.w  $77c04.l,$2edb4.l
