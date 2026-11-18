; experiment: in-game GEMDOS via TOS-state swap
HOOKFLAG equ $76f00
GSP      equ $76f04      ; game a7
GSR      equ $76f08
RES      equ $76f10      ; results
MFPG     equ $76f40      ; 24 bytes game MFP
BUF      equ $77000
STK      equ $77e00
        org $76c00
        tst.w   HOOKFLAG.l
        bne.w   .orig
        move.w  #1,HOOKFLAG.l
        bsr.w   save_ovl
        move.w  #2,HOOKFLAG.l
.orig:  jmp     $3853a.l

save_ovl:
        move.w  sr,GSR.l
        ori.w   #$700,sr
        move.l  a7,GSP.l
        lea     STK.l,a7
        movem.l d0-d7/a0-a6,-(a7)
        bsr     mfp_save
        bsr     swap_tos
        bsr     mfp_tos
        move.w  #$2500,sr               ; MFP (level 6) on, VBL (level 4) masked
        move.w  #1,-(a7)
        pea     fname(pc)
        move.w  #$3d,-(a7)
        trap    #1
        addq.l  #8,a7
        move.l  d0,RES.l
        tst.l   d0
        bmi.s   .fail
        move.w  d0,d7
        pea     BUF.l
        pea     256.l
        move.w  d7,-(a7)
        move.w  #$40,-(a7)
        trap    #1
        lea     12(a7),a7
        move.l  d0,RES+4.l
        move.w  d7,-(a7)
        move.w  #$3e,-(a7)
        trap    #1
        addq.l  #4,a7
        move.l  d0,RES+8.l
.fail:  move.w  #$2700,sr
        bsr     swap_tos
        bsr     mfp_game
        movem.l (a7)+,d0-d7/a0-a6
        move.l  GSP.l,a7
        move.w  GSR.l,sr
        rts

swap_tos:
        lea     8.w,a0
        move.l  $ffd80.l,a1
        move.w  $ffd86.l,d0
        addq.w  #1,d0
        mulu.w  #48,d0
        lea     8(a0,d0.l),a6
.l:     movem.l (a0),d0-d5
        movem.l (a1),d6/d7/a2-a5
        movem.l d6/d7/a2-a5,(a0)
        movem.l d0-d5,(a1)
        lea     24(a0),a0
        lea     24(a1),a1
        cmpa.l  a6,a0
        blo.s   .l
        rts

mfp_save:
        lea     $fffffa01.w,a0
        lea     MFPG.l,a1
        moveq   #23,d0
.r:     move.b  (a0),(a1)+
        addq.l  #2,a0
        dbra    d0,.r
        moveq   #0,d2
        moveq   #0,d4
        moveq   #0,d6
        move.w  #4777,d7
.s:     move.b  $fffffa1f.w,d1
        cmp.b   d1,d2
        bcc.s   .a
        move.b  d1,d2
.a:     move.b  $fffffa23.w,d3
        cmp.b   d3,d4
        bcc.s   .b
        move.b  d3,d4
.b:     move.b  $fffffa25.w,d5
        cmp.b   d5,d6
        bcc.s   .c
        move.b  d5,d6
.c:     dbra    d7,.s
        move.b  d2,MFPG+15.l
        move.b  d4,MFPG+17.l
        move.b  d6,MFPG+18.l
        rts

mfp_tos:
        lea     $fffaa.l,a2
        bra.s   mfp_set
mfp_game:
        lea     MFPG.l,a2
mfp_set:
        clr.b   $fffffa07.w
        clr.b   $fffffa09.w
        clr.b   $fffffa0b.w
        clr.b   $fffffa0d.w
        clr.b   $fffffa0f.w
        clr.b   $fffffa11.w
        lea     $fffffa01.w,a1
        moveq   #23,d2
.l:     move.b  (a2)+,(a1)
        addq.l  #2,a1
        dbra    d2,.l
        rts
fname:  dc.b 'NEBLEVEL.OVL',0
        even
