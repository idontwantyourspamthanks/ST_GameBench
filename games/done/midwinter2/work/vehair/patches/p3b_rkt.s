; name: p3b_rkt
; default: no
; site: $33d26
; orig: 3a390003493a
; note: SCRATCH (MW2VehAir). Type 16 (Rocket Pack) block of sub_033bde: alt = clamp($764c, ground+100, 12000),
;       ground = $3493a (wave-aware terrain under the position AFTER this tick's move, $348ec at $33c4e),
;       $66e2 = alt - ground; then the probe ($33e30). Movement and altitude come from the apply
;       selectors (Y sel 3 -> $764c += $6740, p3b_apply3; button sel 1 -> $344ac, thrust $6750 = $6740 =
;       $675a>>4 where $675a is an integrator, p3b_ctlb). The clamp is a function of the END position and
;       the END altitude of the tick: on passes 1..4 the position is not final and a partial clamp would
;       ratchet the altitude up over a hill the 5 Hz game never samples. Run the block only on pass 5.
D       equ     $b42e0
        org     $33d26
        jsr     $b8500.l

        org     $b8500
        tst.w   D+8.l                   ; SUB
        beq.s   .run
        cmpi.w  #5,D+6.l                ; PH
        beq.s   .run
        addq.l  #4,a7
        jmp     $33e30.l                ; passes 1..4: skip the clamp (the probe call there skips itself)
.run:   move.w  $3493a.l,d5             ; displaced
        rts
