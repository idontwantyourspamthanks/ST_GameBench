; name: tb_cpu13
; default: yes
; site: $12c14
; orig: 4a4666000028
; conflicts: sb_bar sb_face sb_facestat
; doc: Faster 1-column shifted 3-plane (nibble 13: planes 0,2,3) CPU sprite kernel $12c14 (pixel-identical): eliminates self-modifying-code setup, skips empty rows/columns, and uses rol.l (16-d6) when shift > 8.
; note: Mirrors tb_cpu1 ($12b00, nibble 11) with plane 1 zeroed (and.w d0,(a3)+) and d2 written to plane 2. Pure 68000 (speeds up ST, STE, and Mega STE alike).
        org     $12c14
        jmp     $B6600.l

        org     $B6600
tb_cpu13:
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
        ; ---- Case A: 1 <= d6 <= 8 (left-column-only fall-through fast path)
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
        bne.s   .hasR
        not.w   d0
        lsr.w   d6,d1
        lsr.w   d6,d2
        lsr.w   d6,d3
        move.w  d0,d4
        and.w   (a3),d4
        or.w    d1,d4
        move.w  d4,(a3)+
        and.w   d0,(a3)+                ; plane 1 = 0
        move.w  d0,d4
        and.w   (a3),d4
        or.w    d2,d4
        move.w  d4,(a3)+                ; plane 2 = d2
        and.w   (a3),d0
        or.w    d3,d0
        move.w  d0,(a3)+                ; plane 3 = d3
        lea     $98(a3),a3
        dbra    d7,.lpA
        move.w  (a7)+,d5
        rts
.empA:  lea     160(a3),a3
        dbra    d7,.lpA
        move.w  (a7)+,d5
        rts
.hasR:  tst.w   d0
        beq.s   .rA
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
        and.w   d0,(a3)+
        move.w  d0,d4
        and.w   (a3),d4
        or.w    d2,d4
        move.w  d4,(a3)+
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
        and.w   d0,(a3)+
        move.w  d0,d4
        and.w   (a3),d4
        or.w    d2,d4
        move.w  d4,(a3)+
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
        and.w   d0,(a3)+
        move.w  d0,d4
        and.w   (a3),d4
        or.w    d2,d4
        move.w  d4,(a3)+
        and.w   (a3),d0
        or.w    d3,d0
        move.w  d0,(a3)+
        lea     $90(a3),a3
        dbra    d7,.lpA
        move.w  (a7)+,d5
        rts

        ; ---- Case B: 9 <= d6 <= 15 (rol.l d5 -> low = right col, high = left col)
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
        beq.w   .lB
        swap    d0
        tst.w   d0
        beq.w   .rB
        not.l   d0
        rol.l   d5,d1
        rol.l   d5,d2
        rol.l   d5,d3
        swap    d0
        addq.l  #8,a3
        move.w  d0,d4
        and.w   (a3),d4
        or.w    d1,d4
        move.w  d4,(a3)+
        and.w   d0,(a3)+
        move.w  d0,d4
        and.w   (a3),d4
        or.w    d2,d4
        move.w  d4,(a3)+
        and.w   (a3),d0
        or.w    d3,d0
        move.w  d0,(a3)+
        lea     -16(a3),a3
        swap    d0
        swap    d1
        swap    d2
        swap    d3
        move.w  d0,d4
        and.w   (a3),d4
        or.w    d1,d4
        move.w  d4,(a3)+
        and.w   d0,(a3)+
        move.w  d0,d4
        and.w   (a3),d4
        or.w    d2,d4
        move.w  d4,(a3)+
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
        and.w   d0,(a3)+
        move.w  d0,d4
        and.w   (a3),d4
        or.w    d2,d4
        move.w  d4,(a3)+
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
        and.w   d0,(a3)+
        move.w  d0,d4
        and.w   (a3),d4
        or.w    d2,d4
        move.w  d4,(a3)+
        and.w   (a3),d0
        or.w    d3,d0
        move.w  d0,(a3)+
        lea     $90(a3),a3
        dbra    d7,.lpB
        move.w  (a7)+,d5
        rts

.unsh:  jmp     $12c1a.l
.clip:  jmp     $12c40.l
