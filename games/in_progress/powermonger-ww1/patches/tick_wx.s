; name: tick_wx
; default: no
; site: $13e24
; orig: 4eb90001b90a
; note: (needs tick_head) `jsr $1b90a`: the season/weather step (master `jsr $1abaa` at $130b0).  World logic: once per tick, not on a render-only pass (RON).
D       equ     $72a80
        org     $13e24
        jsr     $72a40.l

        org     $72a40
wx:     tst.w   D+6.l                   ; RON
        bne.s   .r
        jmp     $1b90a.l
.r:     rts
