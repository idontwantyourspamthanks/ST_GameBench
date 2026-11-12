; name: p4_fill_save_b
; default: yes
; site: $1b27a
; note: item #9 part 2/2: matching restore of p4_fill_save_a (all exits of $1b1bc, including the early `beq.w $1b27a`).
        org     $1b27a
        movem.l (a7)+,a0/a2-a3/a6
