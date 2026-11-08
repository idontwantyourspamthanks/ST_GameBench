; name: p3b_msg
; default: no
; site: $14e8a
; orig: 4eb900014e98
; note: P3 partial B (needs p3b_head). `jsr $14e98` counts the message timer $14ee4 down once per
;       pass and draws the message ("ENEMY IN RANGE") into the buffer. The timer counts 5 Hz ticks,
;       so on a view sub-step pass (NOLOGIC = 1) the value is restored after the call; the message
;       is still drawn into every presented frame.
D       equ     $b3700
        org     $14e8a
        jsr     $b3680.l

        org     $b3680
msg:    tst.w   D+32.l                  ; NOLOGIC
        bne.s   .sub
        jmp     $14e98.l
.sub:   move.w  $14ee4.l,-(a7)
        jsr     $14e98.l
        move.w  (a7)+,$14ee4.l
        rts
