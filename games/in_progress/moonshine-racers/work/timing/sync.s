; variant D: stock floor removed; the stock post-flip wait replaced by a latch guard before the first back-buffer write
PEND    equ     $b8f08
sync:   jsr     $d1ca.l
        move.b  #1,PEND.l
        clr.b   $611a.l
        rts
wait:   tst.b   PEND.l
        beq.s   .go
.w:     tst.b   PEND.l
        bne.s   .w
.go:    move.w  $1304.w,$1300.w
        move.w  $1302.w,$12fe.w
        jmp     $17c42.l
vbl:    addq.b  #1,$611b.l
        clr.b   PEND.l
        rts
