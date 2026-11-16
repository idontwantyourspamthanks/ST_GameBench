; Option prototypes for the harness (kb.s contract: d0 = x, d1 = y, d7 = rows, a1 = data, a5 = screen; interior only, nibble 7 = 3 planes + masked 4th).
;  pa_al : (a) pre-masked rows [p0 p1 p2 ~M], aligned, 1 column
;  pa_sh : (a) pre-masked rows [p0 p1 p2 M], shifted by x & 15, 1 column (the mask is shifted too)
;  pc_c1 : (c) generated shifted 1-column kernel, shift as an immediate (jump table), zero-mask words skipped; data = stock rows
;  pb_n3 / pb_n5 : (b) pre-shifted data: per row N dest columns of [mask long (M,M)][p0:p1 long][p2:0 long], N = 3 / 5
        org     $C3000
DEST    macro   ; a3 = a5 + y*160 + (x >> 4) * 8 ; uses d2,d3
        move.w  d1,d3
        lsl.w   #5,d3
        move.w  d3,d2
        add.w   d3,d3
        add.w   d3,d3
        add.w   d2,d3
        move.w  d0,d2
        lsr.w   #4,d2
        lsl.w   #3,d2
        add.w   d2,d3
        lea     (a5,d3.w),a3
        endm
pa_al:  DEST
        subq.w  #1,d7
.l:     movem.w (a1)+,d1-d4
        and.w   d4,(a3)
        or.w    d1,(a3)+
        and.w   d4,(a3)
        or.w    d2,(a3)+
        and.w   d4,(a3)
        or.w    d3,(a3)+
        and.w   d4,(a3)+
        lea     $98(a3),a3
        dbra    d7,.l
        rts
pa_sh:  DEST
        moveq   #15,d6
        and.w   d0,d6
        subq.w  #1,d7
.l:     moveq   #0,d1
        move.w  (a1)+,d1
        ror.l   d6,d1
        moveq   #0,d2
        move.w  (a1)+,d2
        ror.l   d6,d2
        moveq   #0,d3
        move.w  (a1)+,d3
        ror.l   d6,d3
        moveq   #0,d0
        move.w  (a1)+,d0
        ror.l   d6,d0
        not.l   d0
        move.l  d0,d4
        swap    d4
        and.w   d0,(a3)
        or.w    d1,(a3)+
        and.w   d0,(a3)
        or.w    d2,(a3)+
        and.w   d0,(a3)
        or.w    d3,(a3)+
        and.w   d0,(a3)+
        swap    d1
        swap    d2
        swap    d3
        and.w   d4,(a3)
        or.w    d1,(a3)+
        and.w   d4,(a3)
        or.w    d2,(a3)+
        and.w   d4,(a3)
        or.w    d3,(a3)+
        and.w   d4,(a3)+
        lea     $90(a3),a3
        dbra    d7,.l
        rts
; ---- (c) generated 1-column shifted, shift immediate, zero-mask skip
SHF     macro   ; \1 = reg ; \2 = shift
        ifle    8-\2
        swap    \1
        rol.l   #(16-\2),\1
        else
        ror.l   #\2,\1
        endc
        endm
GEN     macro
pc\1:   subq.w  #1,d7
.l:     moveq   #0,d1
        move.w  (a1)+,d1
        SHF     d1,\1
        moveq   #0,d2
        move.w  (a1)+,d2
        SHF     d2,\1
        moveq   #0,d3
        move.w  (a1)+,d3
        SHF     d3,\1
        move.w  d1,d0
        or.w    d2,d0
        or.w    d3,d0
        beq.s   .z0
        not.w   d0
        and.w   d0,(a3)
        or.w    d1,(a3)+
        and.w   d0,(a3)
        or.w    d2,(a3)+
        and.w   d0,(a3)
        or.w    d3,(a3)+
        and.w   d0,(a3)+
        bra.s   .c1
.z0:    addq.l  #8,a3
.c1:    swap    d1
        swap    d2
        swap    d3
        move.w  d1,d0
        or.w    d2,d0
        or.w    d3,d0
        beq.s   .z1
        not.w   d0
        and.w   d0,(a3)
        or.w    d1,(a3)+
        and.w   d0,(a3)
        or.w    d2,(a3)+
        and.w   d0,(a3)
        or.w    d3,(a3)+
        and.w   d0,(a3)+
        lea     $90(a3),a3
        dbra    d7,.l
        rts
.z1:    lea     $98(a3),a3
        dbra    d7,.l
        rts
        endm
pc_c1:  DEST
        moveq   #15,d2
        and.w   d0,d2
        add.w   d2,d2
        move.w  jt(pc,d2.w),d2
        jmp     jt(pc,d2.w)
jt:     dc.w    0,pc1-jt,pc2-jt,pc3-jt,pc4-jt,pc5-jt,pc6-jt,pc7-jt,pc8-jt,pc9-jt,pc10-jt,pc11-jt,pc12-jt,pc13-jt,pc14-jt,pc15-jt
        GEN     1
        GEN     2
        GEN     3
        GEN     4
        GEN     5
        GEN     6
        GEN     7
        GEN     8
        GEN     9
        GEN     10
        GEN     11
        GEN     12
        GEN     13
        GEN     14
        GEN     15
; ---- (b) pre-shifted rows
COL     macro
        move.l  (a0)+,d0
        move.l  (a3),d1
        move.l  4(a3),d2
        and.l   d0,d1
        and.l   d0,d2
        or.l    (a1)+,d1
        or.l    (a1)+,d2
        move.l  d1,(a3)+
        move.l  d2,(a3)+
        endm
pb_n3:  DEST
        movea.l a1,a0                   ; masks and data interleaved: per column [mask][p01][p2]: use a1 as the data stream, a0 as the mask stream
        subq.w  #1,d7
.l:     move.l  (a1)+,d0
        move.l  (a3),d4
        move.l  4(a3),d5
        and.l   d0,d4
        and.l   d0,d5
        or.l    (a1)+,d4
        or.l    (a1)+,d5
        move.l  d4,(a3)+
        move.l  d5,(a3)+
        move.l  (a1)+,d0
        move.l  (a3),d4
        move.l  4(a3),d5
        and.l   d0,d4
        and.l   d0,d5
        or.l    (a1)+,d4
        or.l    (a1)+,d5
        move.l  d4,(a3)+
        move.l  d5,(a3)+
        move.l  (a1)+,d0
        move.l  (a3),d4
        move.l  4(a3),d5
        and.l   d0,d4
        and.l   d0,d5
        or.l    (a1)+,d4
        or.l    (a1)+,d5
        move.l  d4,(a3)+
        move.l  d5,(a3)+
        lea     $88(a3),a3
        dbra    d7,.l
        rts
pb_n5:  DEST
        subq.w  #1,d7
.l:     rept    5
        move.l  (a1)+,d0
        move.l  (a3),d4
        move.l  4(a3),d5
        and.l   d0,d4
        and.l   d0,d5
        or.l    (a1)+,d4
        or.l    (a1)+,d5
        move.l  d4,(a3)+
        move.l  d5,(a3)+
        endr
        lea     $78(a3),a3
        dbra    d7,.l
        rts
