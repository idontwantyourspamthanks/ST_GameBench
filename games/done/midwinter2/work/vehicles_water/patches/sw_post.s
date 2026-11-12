; name: sw_post
; default: no
; site: $31576
; orig: 4eb9000359c2
; note: ANALYST SCRATCH: the post-world block starts at $31576 (NPC table). On a masked type's PH 1-4 pass
;       that reaches it (PH 1) it is skipped: back to the loop head, no render. PH 5 (entered by sw_head with
;       jmp $31576) and unmasked types (PH = 5) run it as the original.
        org     $31576
        jsr     $b4e20.l

        org     $b4e20
        cmpi.w  #5,$b42e6.l
        beq.s   .run
        addq.l  #4,a7
        clr.w   $7020.w
        jmp     $31486.l
.run:   jmp     $359c2.l
