; experiment: trap #1 from the game context, once, at the top of the frame loop
MB      equ $76f00          ; mailbox
        org $76c00
        tst.w   MB.l
        bne.w   .orig
        move.w  #1,MB.l
        movem.l d0-d7/a0-a6,-(a7)
        ; Fopen("README.TXT",0)
        clr.w   -(a7)
        pea     fn1(pc)
        move.w  #$3d,-(a7)
        trap    #1
        addq.l  #8,a7
        move.l  d0,MB+4.l
        tst.l   d0
        bmi.s   .nof
        move.w  d0,d7
        pea     MB+$10.l
        pea     16.l
        move.w  d7,-(a7)
        move.w  #$3f,-(a7)
        trap    #1
        lea     12(a7),a7
        move.l  d0,MB+8.l
        move.w  d7,-(a7)
        move.w  #$3e,-(a7)
        trap    #1
        addq.l  #4,a7
.nof:
        ; Fcreate("TESTOUT.DAT")
        clr.w   -(a7)
        pea     fn2(pc)
        move.w  #$3c,-(a7)
        trap    #1
        addq.l  #8,a7
        move.l  d0,MB+$20.l
        tst.l   d0
        bmi.s   .nc
        move.w  d0,d7
        pea     dat(pc)
        pea     16.l
        move.w  d7,-(a7)
        move.w  #$40,-(a7)
        trap    #1
        lea     12(a7),a7
        move.l  d0,MB+$24.l
        move.w  d7,-(a7)
        move.w  #$3e,-(a7)
        trap    #1
        addq.l  #4,a7
        move.l  d0,MB+$28.l
.nc:
        move.w  #2,MB.l
        movem.l (a7)+,d0-d7/a0-a6
.orig:  jmp     $3853a.l
fn1:    dc.b 'README.TXT',0
fn2:    dc.b 'TESTOUT.DAT',0
        even
dat:   dc.b 'NEBULUS-EDIT-OK!'
