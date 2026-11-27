
        org     $014c
        moveq   #0,d3
        move.b  $424.w,d3
        move.l  d3,d2
        andi.b  #1,d2
        move.l  d3,d1
        andi.b  #4,d1
        lsr.b   #2,d1
        add.b   d1,d2
        move.l  d3,d4
        andi.b  #2,d4
        move.l  d3,d1
        andi.b  #8,d1
        lsr.b   #2,d1
        add.b   d1,d4
        lsr.b   #1,d4
        moveq   #0,d3
        tst.b   d2
        beq.s   .b1
        moveq   #1,d3
        subq.b  #1,d2
        lsl.b   d2,d3
.b1:    moveq   #0,d2
        tst.b   d4
        beq.s   .cl
        moveq   #2,d2
        lsl.b   d4,d2
        add.b   d2,d3
.cl:    cmp.b   -1(a2),d3
        bls.s   .ok
        move.b  -1(a2),d3
.ok:    move.b  d3,4(a2)
