; variant E: floor removed, stock post-flip wait replaced by a latch guard before the first back-buffer write;
; the raster-table copy stays where it is (at $7b7a, untouched)
PEND equ $b8f08
sync:   jsr     $d1ca.l
        move.b  #1,PEND.l
        clr.b   $611a.l
        rts
wait:   tst.b   PEND.l
        beq.s   .go
.w:     tst.b   PEND.l
        bne.s   .w
.go:    jmp     $17c42.l
vbl:    addq.b  #1,$611b.l
        clr.b   PEND.l
        rts
