; name: test_rtog_a
; default: no
; site: $0b6fa
; orig: 4279 00037ef0
; note: TEST ONLY (gate for tools/poptick.py ab --render; never in a build; needs test_rtog_b).  The original toggles the water phase $3b260 once per pass at $b6e2-$b6ee, BEFORE the
;       render, so the frame k+1 that the original renders from the world after turn k shows phase(k+1); a render-only pass of the tick (no toggle) shows phase(k).  To compare the
;       render of a render-only pass with the original's render of the next pass, this hook (after the background copy, before the terrain) toggles the phase in a render-only pass
;       (flag RON) and test_rtog_b toggles it back at the end of the render stage ($b7f0).  Any other pass: the displaced `clr.w $37ef0.l`.
RON     equ     $c6010
        org     $0b6fa
        jmp     $c5900.l

        org     $c5900
        tst.w   RON.l
        beq.s   .n
        eori.w  #1,$3b260.l
.n:     clr.w   $37ef0.l
        jmp     $0b700.l
