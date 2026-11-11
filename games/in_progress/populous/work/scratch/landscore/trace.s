; Test scaffolding (not a game patch): log every call of the ORIGINAL land score.
; $18244 is redirected here (jmp); the stub calls the original body and appends a
; 14-byte record {return address.l, turn.w, cell.w, d0.w, owner.b, $3b040.b,
; $37ef4.b, 0} to TBUF. TVARS: +0 write pointer.l, +4 records.l, +8 dropped.l.
TBUF    equ     $5f000
TEND    equ     $77f00
TVARS   equ     $b2000

        org     $b2100
trace:  move.w  6(sp),-(sp)             ; cell
        move.w  6(sp),-(sp)             ; owner
        bsr.s   call_o
        addq.l  #4,sp
        move.l  a0,-(sp)                ; return 4(sp), owner 8(sp), cell 10(sp)
        movea.l TVARS.l,a0
        cmpa.l  #TEND,a0
        bhs.s   .full
        move.l  4(sp),(a0)+
        move.w  $3c506.l,(a0)+
        move.w  10(sp),(a0)+
        move.w  d0,(a0)+
        move.b  9(sp),(a0)+
        move.b  $3b041.l,(a0)+
        move.b  $37ef5.l,(a0)+
        clr.b   (a0)+
        move.l  a0,TVARS.l
        addq.l  #1,TVARS+4.l
        bra.s   .out
.full:  addq.l  #1,TVARS+8.l
.out:   movea.l (sp)+,a0
        tst.w   d0                      ; N, Z as the original leaves them
        rts
call_o: link.w  a5,#0
        movem.l d1-d6/a0-a2,-(sp)
        jmp     $1824c.l
