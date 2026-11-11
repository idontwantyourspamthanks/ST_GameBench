; Test scaffolding (not a game patch): gate (b). The main loop's `jsr $db8a` ($b806)
; is redirected here. Before every world turn the stub hashes the game's whole
; data + bss area (RANGES below) and appends a 12-byte record {turn.w, RNG seed.w,
; sum.l, rox.l} to CKBUF, then runs the turn ($db8a) as a tail call.
;   sum = sum of all longs; rox = rol(rox,1) ^ long, over the same longs in order.
; CKV: +0 write pointer.l (the driver sets it to CKBUF).
CKBUF   equ     $60000
CKV     equ     $b2000

        org     $b2100
ck:     movem.l d0-d3/a0-a2,-(sp)
        moveq   #0,d0
        moveq   #0,d1
        lea     ranges(pc),a2
.rng:   move.l  (a2)+,d2
        beq.s   .end
        movea.l d2,a0
        move.l  (a2)+,d3
.l:     move.l  (a0)+,d2
        add.l   d2,d0
        rol.l   #1,d1
        eor.l   d2,d1
        subq.l  #1,d3
        bne.s   .l
        bra.s   .rng
.end:   movea.l CKV.l,a1
        move.w  $3c506.l,(a1)+
        move.w  $3d56c.l,(a1)+
        move.l  d0,(a1)+
        move.l  d1,(a1)+
        move.l  a1,CKV.l
        movem.l (sp)+,d0-d3/a0-a2
        jmp     $db8a.l
ranges:                                 ; {start.l, longs.l} pairs appended by the driver, 0 ends
