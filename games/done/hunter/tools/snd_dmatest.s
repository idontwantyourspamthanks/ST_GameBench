; DMA sound smoke test: the payload's register sequence, a 391 Hz tone for ~4 s, on any STE-class machine
RL      equ     1024
        move.l  #sup,-(sp)
        move.w  #38,-(sp)
        trap    #14
        addq.l  #6,sp
        clr.w   -(sp)
        trap    #1
sup:    ; ring of 16-sample square-ish sine
        lea     ring(pc),a0
        move.l  a0,d4
        addq.l  #1,d4
        bclr    #0,d4                  ; even
        movea.l d4,a0
        move.w  #RL/16-1,d0
.f:     lea     wave(pc),a1
        moveq   #15,d1
.c:     move.b  (a1)+,(a0)+
        dbra    d1,.c
        dbra    d0,.f
        ; microwire, bus error safe (as snd_microwire)
        movea.l sp,a2
        movea.l $8.w,a1
        lea     .berr(pc),a0
        move.l  a0,$8.w
        lea     .cmds(pc),a0
        moveq   #5,d3
.nx:    move.w  #$07ff,$ff8924.l
        move.w  (a0)+,$ff8922.l
        move.w  #1000,d0
.w:     cmpi.w  #$07ff,$ff8924.l
        beq.s   .d
        dbra    d0,.w
.d:     dbra    d3,.nx
.out:   move.l  a1,$8.w
        bra.s   .go
.berr:  movea.l a2,sp
        bra.s   .out
.cmds:  dc.w    $04e8,$0554,$0514,$0401,$0486,$0446
.go:    lea     $ff8900.l,a0
        moveq   #0,d0
        move.b  d0,1(a0)
        move.l  d4,d0
        move.b  d0,7(a0)
        lsr.l   #8,d0
        move.b  d0,5(a0)
        lsr.l   #8,d0
        move.b  d0,3(a0)
        move.l  d4,d0
        add.l   #RL,d0
        move.b  d0,$13(a0)
        lsr.l   #8,d0
        move.b  d0,$11(a0)
        lsr.l   #8,d0
        move.b  d0,$f(a0)
        move.b  #$80,$21(a0)
        move.b  #3,1(a0)
        ; wait ~4 s and print the DMA counter movement via the exit code (unused)
        move.l  $4ba.w,d5
        add.l   #20,d5
.v0:    cmp.l   $4ba.w,d5
        bhi.s   .v0
        lea     $ff8909.l,a0            ; the payload's position read: stable twice
.rd:    movep.l 0(a0),d0
        movep.l 0(a0),d1
        cmp.l   d0,d1
        bne.s   .rd
        lsr.l   #8,d0
        sub.l   d4,d0                   ; offset inside the ring
        cmp.l   #RL,d0
        bhs.s   .bad
        tst.l   d0
        beq.s   .bad
        move.l  $4ba.w,d5
        add.l   #800,d5
.v:     cmp.l   $4ba.w,d5
        bhi.s   .v
.bad:   clr.b   $ff8901.l
        rts
wave:   dc.b    0,49,90,117,127,117,90,49,0,-49,-90,-117,-127,-117,-90,-49
        even
ring:   ds.b    RL+2
