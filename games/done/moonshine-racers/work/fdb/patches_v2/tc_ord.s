; name: tc_ord
; default: yes
; site: $e406
; orig: 2a78100841f829c8
; doc: Object stage $e406 (depth sort + dispatch loop): inactive slots no longer pay a subroutine call, the type-0 front end is entered directly, the per-slot stack frame is halved (state identical).
; note: Moonshine Racers tighten-C (work/notes/tighten_c.md).  Site $e406 (`movea.l $1008.w,a5 / lea.l $29c8.w,a0`) -> `jmp $B6820.l` + nop; callers: $7b46 (via mx_pre when present) and mx_sync's `jsr $e406.l`.
; note: The sort network and the merge into the order list $36e8 are the stock code (same list, same memory).  The dispatch loop (stock $e4dc-$e4fa: push d7+a0, bsr $e598 per entry, 124 cycles of
; note: overhead + 164 for an inactive slot) tests bit 0 of the slot flags inline and skips inactive slots; for type 0 with frame != $21 it loads a0 = $34(a2) and calls the stock front end $ecc8 directly
; note: (what $e598 -> $ec98 does), every other slot goes through the stock $e598.  The kernels, $ecc8 and $e568 are not touched or copied.  The special entry $2a0 (player) runs the stock block
; note: $e4fe-$e566 in place: a stock-shaped frame (d7 = 0, list pointer) is pushed under a return address so that its `bra.b $e4f4` epilogue pops them and falls into $e4fc `rts` back here.
        org     $e406
        jmp     $B6820.l
        nop

        org     $B6820
tc_ord:
        movea.l $1008.w,a5
        lea     $29c8.w,a0
        move.w  #$2a0,d1
        move.w  #$2d8,d2
        move.w  #$310,d3
        move.w  #$348,d4
        move.w  #$380,d5
        swap    d1
        swap    d2
        swap    d3
        swap    d4
        swap    d5
        move.w  $2c0(a0),d1
        move.w  $2f8(a0),d2
        move.w  $330(a0),d3
        move.w  $368(a0),d4
        move.w  $3a0(a0),d5
        cmp.w   d2,d5
        blt.s   .a1
        exg     d2,d5
.a1:    cmp.w   d1,d4
        blt.s   .a2
        exg     d1,d4
.a2:    cmp.w   d3,d5
        blt.s   .a3
        exg     d3,d5
.a3:    cmp.w   d2,d4
        blt.s   .a4
        exg     d2,d4
.a4:    cmp.w   d1,d3
        blt.s   .a5
        exg     d1,d3
.a5:    cmp.w   d4,d5
        blt.s   .a6
        exg     d4,d5
.a6:    cmp.w   d3,d4
        blt.s   .a7
        exg     d3,d4
.a7:    cmp.w   d2,d3
        blt.s   .a8
        exg     d2,d3
.a8:    cmp.w   d1,d2
        blt.s   .a9
        exg     d1,d2
.a9:    lea     $3732.w,a0
        movem.l d1-d5,(a0)
        lea     $29c8.w,a1
        lea     $36e8.w,a2
        move.w  $3746.w,d0
        lsl.w   #3,d0
        move.w  d0,d1
        lsl.w   #3,d0
        sub.w   d1,d0
        addi.w  #$3b8,d0
        moveq   #$1f,d7
        moveq   #4,d2
        move.l  (a0)+,d1
.m:     tst.w   d2
        bmi.s   .s
        cmp.w   $20(a1,d0.w),d1
        ble.s   .s
        subq.w  #1,d2
        swap    d1
        move.w  d1,(a2)+
        move.l  (a0)+,d1
        bra.s   .m
.s:     move.w  d0,(a2)+
        addi.w  #$38,d0
        cmpi.w  #$ab8,d0
        dbcc    d7,.m
        bcs.s   .tl
        move.w  #$3b8,d0
        dbra    d7,.m
.tl:    tst.w   d2
        bmi.s   .d
.t:     swap    d1
        move.w  d1,(a2)+
        move.l  (a0)+,d1
        dbra    d2,.t
.d:     lea     $36e8.w,a0
.l:     move.w  (a0)+,d0
        cmpi.w  #$2a0,d0
        beq.w   .sp
        lea     $29c8.w,a6
        lea     (a6,d0.w),a2
        move.b  4(a2),d1
        btst    #0,d1
        beq.w   .n
        move.l  a0,-(a7)
        movea.l $34(a2),a0
        move.w  $c(a2),d0
        bne.w   .o
        move.w  $6(a2),d0
        add.w   $8(a2),d0
        cmpi.w  #$21,d0
        beq.w   .o
        btst    #7,d1                   ; --- the stock $ecc8 for type 0, flags tested in d1, no bsr/rts, no d6 push ---
        beq.s   .a
        lsl.w   #3,d0
        add.w   $12(a2),d0
.a:     add.w   d0,d0
        move.w  d0,d3
        lsl.w   #3,d0
        sub.w   d3,d0
        adda.w  d0,a0
        move.w  6(a0),d7
        move.w  $a(a2),d0
        ble.s   .b
        sub.w   d0,d7
        sub.w   d0,2(a2)
.b:     movea.l (a0),a1
        move.w  4(a0),d3
        move.w  d3,d6
        ble.s   .r
        addi.w  #$f,d3
        andi.w  #$fff0,d3
        move.w  d3,d4
        lsr.w   #2,d3
        move.w  $c(a0),d0
        lea     $399c.w,a4
        cmpi.w  #7,d0
        beq.s   .k
        lea     $39b0.w,a4
        cmpi.w  #$b,d0
        beq.s   .k
        lea     $39c4.w,a4
        cmpi.w  #$d,d0
        beq.s   .k
        lea     $3a14.w,a4
        cmpi.w  #$f,d0
        bne.s   .r
.k:     movea.l (a4,d3.w),a4
        moveq   #0,d0
        btst    #2,d1
        beq.s   .e
        move.w  d4,d0
        asr.w   #1,d0
        neg.w   d0
        bra.s   .g
.e:     btst    #7,d1
        beq.s   .g
        move.w  4(a0),d0
        asr.w   #1,d0
        neg.w   d0
        bra.s   .h
.g:     add.w   8(a0),d0
.h:     add.w   (a2),d0
        move.w  2(a2),d1
        sub.w   d7,d1
        jsr     (a4)
.r:     movea.l (a7)+,a0
.n:     cmpa.w  #$3732,a0
        bne.w   .l
        rts
.o:     jsr     $e598.l
        bra.s   .r
.sp:    pea     .cn(pc)
        clr.w   -(a7)
        move.l  a0,-(a7)
        jmp     $e4fe.l
.cn:    bra.w   .n
