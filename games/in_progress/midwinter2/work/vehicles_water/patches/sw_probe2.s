; name: sw_probe2
; default: no
; site: $33e30
; orig: 610001d46100dfb8
; note: ANALYST SCRATCH: the tail probe `bsr $34006` + `bsr $31dee` at $33e30 (every type except flags bit0, which has
;       its own at $33dc6, p3b_probe) runs only on PH 5 of a masked type (and always for unmasked). On PH 1-4 it
;       clears $676e (the probe would have) and leaves $6288/page window handling to PH 5.
        org     $33e30
        jsr     $b4ea0.l
        nop

        org     $b4ea0
        tst.w   $b42e8.l                ; SUB
        beq.s   .full
        cmpi.w  #5,$b42e6.l             ; PH
        beq.s   .full
        clr.w   $676e.w
        rts
.full:  jsr     $34006.l
        jmp     $31dee.l
