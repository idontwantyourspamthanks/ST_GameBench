; name: p3b_hud
; default: yes
; site: $14e14
; orig: 4eb900014fac
; note: P3 partial B (needs p3b_head). The loop body's HUD feed + game clock call `jsr $14fac`.
;       On a view sub-step pass (NOLOGIC = 1) the HUD values (compass, turn indicator, gauges) are
;       still fed but the game clock must not tick: $15118 (frames to the next game minute) is
;       forced to 1 around the call, so `dbra` takes the no-tick path ($14fc6), and restored
;       (the call stores d0 = 0 there).
D       equ     $b3700
        org     $14e14
        jsr     $b3600.l

        org     $b3600
hud:    tst.w   D+32.l                  ; NOLOGIC
        bne.s   .sub
        jmp     $14fac.l
.sub:   move.w  $15118.l,-(a7)
        move.w  #1,$15118.l
        jsr     $14fac.l
        move.w  (a7)+,$15118.l
        rts
