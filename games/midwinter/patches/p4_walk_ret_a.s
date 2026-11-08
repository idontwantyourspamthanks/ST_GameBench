; name: p4_walk_ret_a
; default: no
; site: $1a2c4
; note: item #4 part 2/3: epilogue of the edge walker (rising-x/exit-by-test/horizontal path), see p4_walk_save.
        org     $1a2c4
        movem.l (a7)+,a0-a1
