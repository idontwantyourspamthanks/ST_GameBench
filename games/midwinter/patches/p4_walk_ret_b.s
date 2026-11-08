; name: p4_walk_ret_b
; default: no
; site: $1a610
; note: item #4 part 3/3: epilogue of the edge walker (falling-x path), see p4_walk_save.
        org     $1a610
        movem.l (a7)+,a0-a1
