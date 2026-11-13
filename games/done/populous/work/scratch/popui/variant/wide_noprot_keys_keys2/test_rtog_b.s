; name: test_rtog_b
; default: no
; site: $0b7f0
; orig: 4a79 0003b2b2
; note: TEST ONLY (see test_rtog_a): toggles the water phase back at the end of the render stage of a render-only pass.  Any other pass: the displaced `tst.w $3b2b2.l`.
RON     equ     $c6010
        org     $0b7f0
        jmp     $c5940.l

        org     $c5940
        tst.w   RON.l
        beq.s   .n
        eori.w  #1,$3b260.l
.n:     tst.w   $3b2b2.l
        jmp     $0b7f6.l
