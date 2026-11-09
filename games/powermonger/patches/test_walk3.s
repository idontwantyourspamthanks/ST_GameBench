; name: test_walk3
; default: no
; stage: 2
; site: $1956
; orig: 33f90001c4940002df94
; note: test only, part 3 of 3 of test_walk: the pointer y copy (`move.w $1c494.l,$2df94.l`) becomes `move.w PY.l,$2df94.l` (PY = $ce404).
        org     $1956
        move.w  $ce404.l,$2df94.l
