; name: sw_ramp
; default: no
; site: $33e46
; orig: 303876466a02
; note: ANALYST SCRATCH: speed ramp $688e/$6892 (+-1 per call) runs only on PH 5 of a masked type (once per tick).
        org     $33e46
        jsr     $b4e40.l

        org     $b4e40
        tst.w   $b42e8.l                ; SUB
        beq.s   .orig
        cmpi.w  #5,$b42e6.l             ; PH
        bne.s   .skip
.orig:  move.w  $7646.w,d0              ; the replaced instructions
        bmi.s   .neg
        addq.l  #4,a7
        jmp     $33e4e.l
.neg:   rts                             ; continues at $33e4c: neg.w d0
.skip:  addq.l  #4,a7
        rts
