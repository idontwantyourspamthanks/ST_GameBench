; name: p3b_logic
; default: no
; site: $14e32
; orig: 4eb9000202c64eb9000200e84eb90001ffe04eb90001fa0a4eb900020d52
; note: P3 partial B (needs p3b_head). The loop body's five logic calls (spawn tests $202c6 $200e8
;       $1ffe0 $1fa0a and the object update $20d52, 30 bytes, sitting between render calls) run
;       once per 5 Hz tick, not on the view sub-step passes (NOLOGIC = 1).
D       equ     $b3700
        org     $14e32
        jsr     $b3640.l

        org     $b3640
logic:  tst.w   D+32.l                  ; NOLOGIC
        bne.s   .no
        jsr     $202c6.l
        jsr     $200e8.l
        jsr     $1ffe0.l
        jsr     $1fa0a.l
        jsr     $20d52.l
.no:    rts
