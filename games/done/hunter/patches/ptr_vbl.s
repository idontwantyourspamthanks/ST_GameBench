; name: ptr_vbl
; default: yes
; site: $c69a
; orig: 4a2d01ce6b00dfbc
; requires: ptr_x ptr_y ptr_thr
; data: $8dbc0 18
; note: Responsive, even mouse pointer, part 1 of 4.  ptr_thr changes the game's IKBD mouse threshold ($af9a) from (3,3) to (1,1)
; note: so small movements are delivered immediately instead of being held back; ptr_x/ptr_y collect each packet's X and Y bytes
; note: together without halving negative deltas (left/up now match right/down).  This VBL hook commits the collected (PX, PY)
; note: directly 1:1 right before the pointer redraw ($a65c) with zero multi-frame lag or drift.
; note: STATE (18 bytes at $8dbc0, zero at the start): +0 PX.w, +8 PY.w, +16 TX.w (X byte of packet in flight).
PTR     equ     $8dbc0
        org     $c69a
        jsr     $8da70.l                ; replaces `tst.b $1ce(a5) / bmi.w $a65c`; returns to the original `rts` at $c6a2 through the nop
        nop

        org     $8da70
ptr_vbl:
        movem.l d0/a0,-(sp)
        lea     PTR.l,a0
        move.w  (a0),d0                 ; X: packets collected since the last VBL
        beq.s   .y
        sub.w   d0,(a0)                 ; atomic take (a packet landing here stays for the next VBL)
        add.w   $d8(a5),d0
        bpl.s   .x1
        clr.w   d0
.x1:    cmp.w   $e4(a5),d0
        blt.s   .x2
        move.w  $e4(a5),d0
.x2:    move.w  d0,$d8(a5)
.y:     move.w  8(a0),d0                ; Y: packets collected since the last VBL
        beq.s   .done
        sub.w   d0,8(a0)
        add.w   $da(a5),d0
        bpl.s   .y1
        clr.w   d0
.y1:    cmp.w   $e6(a5),d0
        blt.s   .y2
        move.w  $e6(a5),d0
.y2:    move.w  d0,$da(a5)
.done:  movem.l (sp)+,d0/a0
        tst.b   $1ce(a5)                ; the original two instructions
        bpl.s   .r
        jsr     $a65c.l                 ; (`bmi.w $a65c` was a tail jump; here it returns through the nop to the `rts` at $c6a2)
.r:     rts
