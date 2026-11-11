; name: pop_land_mul
; default: no
; site: $20796
; orig: 4e56000048e7f100
; note: The C compiler's 32 x 32 multiply helper $20796 (368 call sites; arguments
;       are two longs on the stack, the product replaces the second and the first
;       is popped; every register is preserved; CCR = tst.l of the product).
;       Fast path for two operands in 0..65535 (index * 22, index * 46): one mulu.
;       Any other operand runs the ORIGINAL code (displaced link/movem replayed,
;       then $2079e). Same product, same CCR (X = 0 as the original's `add.l d2,d3`
;       onto 0 leaves it), same registers. Evidence: work/notes/landscore.md.
;       Blob $C1000-$C103F. Uses no data of its own.

        org     $20796
        jmp     $c1000.l
        nop

        org     $c1000
lmul:   tst.w   4(sp)                   ; high word of the first operand
        bne.s   .slow
        tst.w   8(sp)                   ; high word of the second
        bne.s   .slow
        move.l  d0,-(sp)
        moveq   #0,d0
        add.w   10(sp),d0               ; first operand; X = 0
        mulu.w  14(sp),d0
        move.l  d0,12(sp)               ; product over the second operand
        move.l  (sp)+,d0
        move.l  (sp)+,(sp)              ; return address over the first operand
        tst.l   4(sp)
        rts
.slow:  link.w  a6,#0                   ; the two displaced instructions
        movem.l d0-d3/d7,-(sp)
        jmp     $2079e.l
