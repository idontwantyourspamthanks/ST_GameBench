; name: p3b_terr
; default: no
; site: $33c4e
; orig: 4eb9000348ec
; note: SCRATCH (MW2VehAir). sub_0348ec samples the terrain at the player's position into
;       $34936/$34938/$3493a at the END of every player pass; the NEXT pass reads them
;       ($33da4: $66e4 = $3493a, $66e2 = $764c - $66e4; $34034/$340a8 probes). So tick k
;       of the 5 Hz game sees the terrain of the position at the end of tick k-1. On a 25 Hz
;       sub-step pass the next pass would see the sub-step position instead (observed:
;       agl/gnd off by up to 100 at group end, Biplane). Run it only on the world pass
;       (PH 5, or any non-sub pass): sub-passes 1..5 then read the end-of-previous-group sample.
D       equ     $b42e0
        org     $33c4e
        jsr     $b4e80.l

        org     $b4e80
        tst.w   D+8.l                   ; SUB
        beq.s   .run
        cmpi.w  #5,D+6.l                ; PH
        bne.s   .skip
.run:   jmp     $348ec.l                ; tail call, returns to $33c54
.skip:  rts
