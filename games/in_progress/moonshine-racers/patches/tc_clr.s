; name: tc_clr
; default: yes
; conflicts: tc_clrx
; site: $17c24
; orig: 41f900004ff8
; data: $B6FF0 2
; doc: Span-buffer clear $17c24 (1136 bytes, 3.7 k cycles) done exactly but only where it can matter: it zeroes the previous pass's road record stream, the 16 bytes below it and the terminator, memory afterwards identical to stock.
; note: Moonshine Racers tighten-C (work/notes/tighten_c.md section 5).  Stock zeroes $4b88-$4ff7 (71 x `movem.l d0-d3,-(a0)` from $4ff8 = 1136 bytes) before the road geometry runs; the start pointer long at $4b84 and table $4aa4 below it are NOT cleared.  What the previous geometry run left in $4b88-$4ff7 is the stream (records of 8 bytes, written downwards from $4f78 by $100b4, start
; note: pointer = the long at $4b84, stored at the end of the geometry) and nothing else (the rest was zero after the previous clear and the geometry writes only the stream there).
; note: So when $4b84 holds a valid start pointer p ($4b88 <= p <= $4f78, multiple of 8) the blob zeroes p-$4f87 (the old stream and the terminator, descending `movem.l d0-d7`, 128/32/8 byte steps), and the region is zero exactly as after the stock clear.
; note: Otherwise, and on the first call after game start (flag byte $B6FF0, zero in the image), the whole stock range $4b88-$4ff7 is cleared exactly as stock does.  Registers: d0-d7 and a0 are clobbered (stock: d0-d3, d7, a0), a1 is preserved; the callers are `$7afe` and mx_sync, both followed by `$100b4`, which initialises its own registers.
        org     $17c24
        jmp     $B6D40.l

        org     $B6D40
tc_clr:
        tst.b   $B6FF0.l
        beq.s   .full
        move.l  $4b84.w,d0
        cmp.l   #$4b88,d0
        bcs.s   .full
        cmp.l   #$4f78,d0
        bhi.s   .full
        move.w  d0,d1
        and.w   #7,d1
        bne.s   .full
        movea.l d0,a0
        moveq   #0,d0
        moveq   #0,d1
        moveq   #0,d2
        moveq   #0,d3
        moveq   #0,d4
        moveq   #0,d5
        moveq   #0,d6
        moveq   #0,d7
        move.l  a1,-(a7)
        lea     $4f88.w,a1
        lea     $80(a0),a0
.b:     cmpa.l  a0,a1
        bcs.s   .c
        movem.l d0-d7,-(a1)
        movem.l d0-d7,-(a1)
        movem.l d0-d7,-(a1)
        movem.l d0-d7,-(a1)
        bra.s   .b
.c:     lea     -$60(a0),a0
.d:     cmpa.l  a0,a1
        bcs.s   .e
        movem.l d0-d7,-(a1)
        bra.s   .d
.e:     lea     -$18(a0),a0
.f:     cmpa.l  a0,a1
        bcs.s   .g
        movem.l d0-d1,-(a1)
        bra.s   .f
.g:     movea.l (a7)+,a1
        rts
.full:  lea     $4ff8.l,a0
        move.w  #$46,d7
        moveq   #0,d0
        move.l  d0,d1
        move.l  d0,d2
        move.l  d0,d3
.l:     movem.l d0-d3,-(a0)
        dbra    d7,.l
        move.b  #1,$B6FF0.l
        rts
