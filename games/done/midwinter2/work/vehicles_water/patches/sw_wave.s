; name: sw_wave
; default: no
; site: $1dcae
; orig: 50790001877c
; note: ANALYST SCRATCH: wave phase advance (+8 mod $80 -> $1877c / $1dfba, end of sub_01dc90 = the renderer) only on
;       the render of PH 5 (or of an unmasked type). On a masked type's PH 1-4 render it is skipped, so the phase
;       advances exactly 8 per 5 Hz tick as in the unpatched game (1 render per tick).
        org     $1dcae
        jsr     $b4f00.l

        org     $b4f00
        tst.w   $b42e8.l                ; SUB
        beq.s   .orig
        cmpi.w  #5,$b42e6.l             ; PH
        beq.s   .orig
        addq.l  #4,a7                   ; skip the block: return from sub_01dc90
        rts
.orig:  addq.w  #8,$1877c.l             ; the replaced instruction
        rts
