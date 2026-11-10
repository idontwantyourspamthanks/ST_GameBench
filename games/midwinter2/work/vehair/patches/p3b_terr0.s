; name: p3b_terr0
; default: no
; site: $33bf8
; orig: 4eb90003489a
; note: SCRATCH (MW2VehAir). sub_03489a (called at the top of every sub_033bde pass) samples the terrain
;       height under the player into $66e4 (and the water flag $6774). The Parachute block ($33ce2)
;       reads $66e4 as the ground height of the TICK START position. On a sub-pass the position has
;       moved, so run it only on the first pass of a group (HOLD = 0) or on a non-sub pass.
D       equ     $b42e0
        org     $33bf8
        jsr     $b8200.l

        org     $b8200
        tst.w   D+8.l                   ; SUB
        beq.s   .run
        tst.w   D+10.l                  ; HOLD
        beq.s   .run
        rts
.run:   jmp     $3489a.l                ; tail call
