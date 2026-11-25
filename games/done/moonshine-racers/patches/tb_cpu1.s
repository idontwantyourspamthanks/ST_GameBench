; name: tb_cpu1
; default: yes
; site: $12b00
; orig: 4a4666000028
; conflicts: sb_bar
; doc: Faster 1-column shifted 3-plane (nibble 11: planes 0,1,3) CPU sprite kernel $12b00 (pixel-identical): eliminates 150-cycle self-modifying-code setup, skips empty rows/columns, and uses rol.l (16-d6) when shift > 8.
; note: Handles all unclipped shifted 1-col n11c1 calls (both $12a98 fallthrough and $38c4/$37c0/$37c4 inner entries that stay on CPU below tb_blit's minr=14). Pure 68000 (speeds up ST, STE, and Mega STE alike).
        org     $12b00
        jmp     $B6400.l

        org     $B6400
tb_cpu1:
        tst.w   d6
        beq.w   .unsh
        tst.w   d0
        bmi.w   .clip
        cmpi.w  #$130,d0
        bge.w   .clip
        move.w  d5,-(a7)
        moveq   #16,d5
        sub.w   d6,d5                   ; d5 = 16 - d6
        subq.w  #1,d7                   ; dbra counter
        cmpi.w  #8,d6
        bgt.w   .hi
        ; ---- Case A: 1 <= d6 <= 8 (82% of rows are left-column only -> make left-only the fall-through path!)
.lpA:   move.w  (a1)+,d1
        move.w  (a1)+,d2
        move.w  (a1)+,d3
        moveq   #0,d0
        move.w  d1,d0
        or.w    d2,d0
        or.w    d3,d0
        beq.s   .empA
        ror.l   d6,d0                   ; d0.w = mask_L, d0.hi = mask_R
        move.l  d0,d4
        swap    d4
        tst.w   d4
        bne.s   .hasR                   ; right col non-empty (18% of Case A)
        ; ---- left col ONLY (82% of Case A: no moveq #0 d1-d3, no swap d0, no taken branch!)
        not.w   d0
        lsr.w   d6,d1
        lsr.w   d6,d2
        lsr.w   d6,d3
        move.w  d0,d4
        and.w   (a3),d4
        or.w    d1,d4
        move.w  d4,(a3)+
        move.w  d0,d4
        and.w   (a3),d4
        or.w    d2,d4
        move.w  d4,(a3)+
        and.w   d0,(a3)+
        and.w   (a3),d0
        or.w    d3,d0
        move.w  d0,(a3)+
        lea     $98(a3),a3
        dbra    d7,.lpA
        move.w  (a7)+,d5
        rts
.empA:  lea     160(a3),a3
        dbra    d7,.lpA
        move.w  (a7)+,d5
        rts
.hasR:  tst.w   d0
        beq.s   .rA                     ; left col empty -> right col only
        ; both columns non-empty: clear high words of d1-d3 before ror.l
        andi.l  #$ffff,d1
        andi.l  #$ffff,d2
        andi.l  #$ffff,d3
        not.l   d0
        ror.l   d6,d1
        ror.l   d6,d2
        ror.l   d6,d3
        move.w  d0,d4
        and.w   (a3),d4
        or.w    d1,d4
        move.w  d4,(a3)+
        move.w  d0,d4
        and.w   (a3),d4
        or.w    d2,d4
        move.w  d4,(a3)+
        and.w   d0,(a3)+
        and.w   (a3),d0
        or.w    d3,d0
        move.w  d0,(a3)+
        swap    d0
        swap    d1
        swap    d2
        swap    d3
        move.w  d0,d4
        and.w   (a3),d4
        or.w    d1,d4
        move.w  d4,(a3)+
        move.w  d0,d4
        and.w   (a3),d4
        or.w    d2,d4
        move.w  d4,(a3)+
        and.w   d0,(a3)+
        and.w   (a3),d0
        or.w    d3,d0
        move.w  d0,(a3)+
        lea     $90(a3),a3
        dbra    d7,.lpA
        move.w  (a7)+,d5
        rts
.rA:    move.w  d4,d0
        not.w   d0
        lsl.w   d5,d1
        lsl.w   d5,d2
        lsl.w   d5,d3
        addq.l  #8,a3
        move.w  d0,d4
        and.w   (a3),d4
        or.w    d1,d4
        move.w  d4,(a3)+
        move.w  d0,d4
        and.w   (a3),d4
        or.w    d2,d4
        move.w  d4,(a3)+
        and.w   d0,(a3)+
        and.w   (a3),d0
        or.w    d3,d0
        move.w  d0,(a3)+
        lea     $90(a3),a3
        dbra    d7,.lpA
        move.w  (a7)+,d5
        rts

        ; ---- Case B: 9 <= d6 <= 15 (rol.l d5 -> low = right col, high = left col; d5 = 1..7)
.hi:
.lpB:   moveq   #0,d1
        moveq   #0,d2
        moveq   #0,d3
        move.w  (a1)+,d1
        move.w  (a1)+,d2
        move.w  (a1)+,d3
        moveq   #0,d0
        move.w  d1,d0
        or.w    d2,d0
        or.w    d3,d0
        beq.s   .empB
        rol.l   d5,d0                   ; d0.w = mask_R, d0.hi = mask_L
        tst.w   d0
        beq.w   .lB                     ; right col empty -> left col only (lsr.w d6)
        swap    d0
        tst.w   d0
        beq.w   .rB                     ; left col empty -> right col only (lsl.w d5)
        ; both columns non-empty (d0.w = mask_L, d0.hi = mask_R)
        not.l   d0
        rol.l   d5,d1                   ; d1.w = p0_R, d1.hi = p0_L
        rol.l   d5,d2
        rol.l   d5,d3
        swap    d0                      ; d0.w = ~mask_R, d0.hi = ~mask_L
        addq.l  #8,a3                   ; write right col first
        move.w  d0,d4
        and.w   (a3),d4
        or.w    d1,d4
        move.w  d4,(a3)+
        move.w  d0,d4
        and.w   (a3),d4
        or.w    d2,d4
        move.w  d4,(a3)+
        and.w   d0,(a3)+
        and.w   (a3),d0
        or.w    d3,d0
        move.w  d0,(a3)+
        lea     -16(a3),a3              ; back to left col
        swap    d0
        swap    d1
        swap    d2
        swap    d3
        move.w  d0,d4
        and.w   (a3),d4
        or.w    d1,d4
        move.w  d4,(a3)+
        move.w  d0,d4
        and.w   (a3),d4
        or.w    d2,d4
        move.w  d4,(a3)+
        and.w   d0,(a3)+
        and.w   (a3),d0
        or.w    d3,d0
        move.w  d0,(a3)+
        lea     $98(a3),a3
        dbra    d7,.lpB
        move.w  (a7)+,d5
        rts
.empB:  lea     160(a3),a3
        dbra    d7,.lpB
        move.w  (a7)+,d5
        rts
.lB:    swap    d0
        not.w   d0
        lsr.w   d6,d1
        lsr.w   d6,d2
        lsr.w   d6,d3
        move.w  d0,d4
        and.w   (a3),d4
        or.w    d1,d4
        move.w  d4,(a3)+
        move.w  d0,d4
        and.w   (a3),d4
        or.w    d2,d4
        move.w  d4,(a3)+
        and.w   d0,(a3)+
        and.w   (a3),d0
        or.w    d3,d0
        move.w  d0,(a3)+
        lea     $98(a3),a3
        dbra    d7,.lpB
        move.w  (a7)+,d5
        rts
.rB:    swap    d0
        not.w   d0
        lsl.w   d5,d1
        lsl.w   d5,d2
        lsl.w   d5,d3
        addq.l  #8,a3
        move.w  d0,d4
        and.w   (a3),d4
        or.w    d1,d4
        move.w  d4,(a3)+
        move.w  d0,d4
        and.w   (a3),d4
        or.w    d2,d4
        move.w  d4,(a3)+
        and.w   d0,(a3)+
        and.w   (a3),d0
        or.w    d3,d0
        move.w  d0,(a3)+
        lea     $90(a3),a3
        dbra    d7,.lpB
        move.w  (a7)+,d5
        rts

.unsh:  jmp     $12b06.l
.clip:  jmp     $12b2c.l
