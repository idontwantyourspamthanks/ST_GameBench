; name: p4_edge
; default: yes
; site: $7450
; note: item (d) edge set-up (work/notes/p4_raster.md section 5). Replaces sub_007450 (called per object by $39ea/$4986/$4f5a/$4f84/$4fb8):
; note: per edge {x0.l, y0.w, dy.w, slope.l = (dx<<5)/dy, slope>>1} into the table $6af0. Same records, same registers preserved
; note: (a1, a3, a4, a5, a6; the original clobbers a0, a2, d0-d7). The slope: `divs.w d5,d2` is only executed for dy that is not
; note: 0 / 1 / 2 / 4 / 8 / 16 / 32 and dx != 0; there the quotient is an exact left shift (dx*32 is a multiple of 32), `asl.w`
; note: reports a 16-bit overflow in V, and the overflow result of divs (dividend unchanged, then ext.l = sext16(n)) is reproduced.
; note: dx == 0 -> 0 (divs would give 0). dy == 0: dx<<5 as long, no divide (as the original). Exhaustive proof: p4_raster.md section 5.
        org     $7450
        jmp     $8c100.l

        org     $8c100
        move.w  (a0)+,d0
        move.w  d0,d7
        lsl.w   #4,d0
        move.w  d0,$1604(a5)            ; the original's final value (it clears it first)
        lea     $6af0.l,a2
        subq.w  #1,d7
.e:     moveq   #0,d0
        move.b  (a0)+,d0
        lsl.w   #2,d0
        moveq   #0,d2
        move.b  (a0)+,d2
        lsl.w   #2,d2
        movem.w (a1,d0.w),d0-d1         ; x0,y0 (sign-extended)
        movem.w (a1,d2.w),d2-d3         ; x1,y1
        cmp.w   d1,d3
        bgt.s   .k
        blt.s   .sw
        cmp.w   d0,d2
        bge.s   .k
.sw:    exg     d0,d2
        exg     d1,d3
.k:     move.w  d2,d4
        sub.w   d0,d4                   ; dx
        move.w  d3,d5
        sub.w   d1,d5                   ; dy
        beq.s   .flat
        tst.w   d4
        beq.s   .zero
        cmp.w   #32,d5
        bhi.s   .gen
        move.b  .shift(pc,d5.w),d3
        bmi.s   .gen
        move.w  d4,d2
        asl.w   d3,d2                   ; dx << (5 - log2 dy); V = does not fit 16 bits
        bvs.s   .ovf
        ext.l   d2
        bra.s   .rec
.ovf:   move.w  d4,d2                   ; divs overflow: dividend stays dx<<5, ext.l keeps its low word
        lsl.w   #5,d2
        ext.l   d2
        bra.s   .rec
.gen:   move.w  d4,d2
        ext.l   d2
        lsl.l   #5,d2
        divs.w  d5,d2
        ext.l   d2
        bra.s   .rec
.zero:  moveq   #0,d2
        bra.s   .rec
.flat:  move.w  d4,d2
        ext.l   d2
        lsl.l   #5,d2                   ; no divide, no ext (as the original)
.rec:   swap    d1
        move.w  d5,d1                   ; y0:dy
        move.l  d2,d3
        asr.l   #1,d3
        movem.l d0-d3,(a2)
        lea     16(a2),a2
        dbra    d7,.e
        rts
.shift: dc.b    255, 5, 4, 255, 3, 255, 255, 255, 2, 255, 255, 255, 255, 255, 255, 255, 1, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 0
