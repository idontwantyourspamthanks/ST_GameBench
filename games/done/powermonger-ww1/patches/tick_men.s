; name: tick_men
; default: yes
; site: $13e36
; orig: 4eb9000158b2
; note: (needs tick_head) `jsr $158b2`: the people (men) update (master `jsr $14b62` at $130c2).  World logic: once per tick, not on a render-only pass (RON).
D       equ     $72a80
        org     $13e36
        jsr     $72a60.l

        org     $72a60
men:    tst.w   D+6.l                   ; RON
        bne.s   .r
        jmp     $158b2.l
.r:     rts
