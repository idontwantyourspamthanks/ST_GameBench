; name: opt_xform
; default: yes
; site: $5452
; orig: 41ed15a44a2c0080
; note: Fast bit-exact 3D vertex rotation (sub_005452).
; note: Replaces slow 38-50 cycle `asr.l d3/d5` shifts with `add.l + swap` (12 cyc when sh==15)
; note: and `swap + asr.w #(sh-16)` (12-18 cyc when sh>=16), with exact `asr.l` fallback for sh<15.
; note: Bit-for-bit identical to the original for all 256 sin/cos table angles.
        org     $5452
        jmp     $8d860.l
        nop

        org     $8d860
opt_xform:
        lea     $15a4(a5),a0
        tst.b   $80(a4)                 ; Z rotation?
        beq.s   .x
        move.w  d2,-(sp)
        movem.w 16(a0),d3-d6
        bsr.s   rot2d                   ; (d0, d1) -> (d0', d1')
        move.w  (sp)+,d2
.x:     tst.b   $7c(a4)                 ; X rotation?
        beq.s   .y
        move.w  d0,-(sp)
        movem.w (a0),d3-d6
        move.w  d2,d0
        bsr.s   rot2d                   ; (d0=z, d1=y) -> (d0=z', d1=y')
        move.w  d0,d2
        move.w  (sp)+,d0
.y:     tst.b   $7e(a4)                 ; Y rotation? (hottest: inline d3==15 && d5==15 fast path)
        beq.s   .tr
        move.w  d1,-(sp)
        movem.w 8(a0),d3-d6
        moveq   #15,d1
        cmp.w   d1,d3
        bne.s   .ygen
        cmp.w   d1,d5
        bne.s   .ygen
        move.w  d0,-(sp)
        move.w  d2,d1
        muls.w  d4,d1
        add.l   d1,d1
        swap    d1
        muls.w  d6,d0
        add.l   d0,d0
        swap    d0
        add.w   d1,d0
        move.w  (sp)+,d1
        muls.w  d6,d2
        add.l   d2,d2
        swap    d2
        muls.w  d4,d1
        add.l   d1,d1
        swap    d1
        sub.w   d1,d2
        move.w  (sp)+,d1
.tr:    jmp     $54d2.l                 ; translate + min-y + store + rts
.ygen:  move.w  d2,d1
        bsr.s   rot2d                   ; (d0=x, d1=z) -> (d0=x', d1=z')
        move.w  d1,d2
        move.w  (sp)+,d1
        jmp     $54d2.l

; rot2d: A'=((A*d6)>>d5)+((B*d4)>>d3), B'=((B*d6)>>d5)-((A*d4)>>d3)
; In: d0=A, d1=B, d3=sh_s, d4=s, d5=sh_c, d6=c. Clobbers d2, d3, d5.
rot2d:  moveq   #15,d2
        cmp.w   d2,d3
        bne.s   .g1
        cmp.w   d2,d5
        bne.s   .g2
        ; Fast path: d3 == 15 AND d5 == 15
        move.w  d0,-(sp)
        move.w  d1,d2
        muls.w  d4,d2
        add.l   d2,d2
        swap    d2
        muls.w  d6,d0
        add.l   d0,d0
        swap    d0
        add.w   d2,d0
        move.w  (sp)+,d2
        muls.w  d6,d1
        add.l   d1,d1
        swap    d1
        muls.w  d4,d2
        add.l   d2,d2
        swap    d2
        sub.w   d2,d1
        rts
.g1:    ; d3 != 15: check if d5 == 15 and d3 >= 16
        cmp.w   d2,d5
        bne.s   .orig
        subi.w  #16,d3
        bmi.s   .fix3
        move.w  d0,-(sp)
        move.w  d1,d2
        muls.w  d4,d2
        swap    d2
        asr.w   d3,d2
        muls.w  d6,d0
        add.l   d0,d0
        swap    d0
        add.w   d2,d0
        move.w  (sp)+,d2
        muls.w  d6,d1
        add.l   d1,d1
        swap    d1
        muls.w  d4,d2
        swap    d2
        asr.w   d3,d2
        sub.w   d2,d1
        rts
.fix3:  addi.w  #16,d3
        bra.s   .orig
.g2:    ; d3 == 15 and d5 != 15: check if d5 >= 16
        subi.w  #16,d5
        bmi.s   .fix5
        move.w  d0,-(sp)
        move.w  d1,d2
        muls.w  d4,d2
        add.l   d2,d2
        swap    d2
        muls.w  d6,d0
        swap    d0
        asr.w   d5,d0
        add.w   d2,d0
        move.w  (sp)+,d2
        muls.w  d6,d1
        swap    d1
        asr.w   d5,d1
        muls.w  d4,d2
        add.l   d2,d2
        swap    d2
        sub.w   d2,d1
        rts
.fix5:  addi.w  #16,d5
.orig:  move.w  d0,-(sp)
        move.w  d1,d2
        muls.w  d4,d2
        muls.w  d6,d0
        asr.l   d3,d2
        asr.l   d5,d0
        add.w   d2,d0
        move.w  (sp)+,d2
        muls.w  d6,d1
        muls.w  d4,d2
        asr.l   d5,d1
        asr.l   d3,d2
        sub.w   d2,d1
        rts
