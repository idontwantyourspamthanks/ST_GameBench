; name: test_walk2
; default: no
; stage: 2
; site: $194c
; orig: 33f90001c4920002df92
; note: test only, part 2 of 3 of test_walk: the IKBD packet handler's copy of the pointer x (`move.w $1c492.l,$2df92.l`)
;       becomes `move.w PX.l,$2df92.l` (PX = $ce402), so the IKBD's absolute position no longer reaches the draw variables.
        org     $194c
        move.w  $ce402.l,$2df92.l
