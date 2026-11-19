; name: tick_wx
; default: no
; site: $130b0
; orig: 4eb90001abaa
; note: P2 (needs tick_head). `jsr $1abaa`: season/weather dissolve (steps the LCG $57ff6, advances the
;       season picture dissolve, `addq.w #1,$57fec`). World logic: once per tick, not on a render-only pass (RON).
D       equ     $b8a00
        org     $130b0
        jsr     $b8940.l

        org     $b8940
wx:     tst.w   D+6.l                   ; RON
        bne.s   .r
        jmp     $1abaa.l
.r:     rts
