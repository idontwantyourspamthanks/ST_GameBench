; name: pop2_ptr_b
; default: yes
; site: $1b34
; orig: 33fc0001000392cc
; note: Item 3, part B of two (needs pop2_ptr_a and its data block at $88000).  `move.w #1,$392cc.l` at $1b34: the end of the VBL pointer code (the
; note: target of the hide path, of the draw loop's fall-through and of part A's skip).  If part A flagged that the draw ran, record the drawn rectangle:
; note: the inputs it saw (re-checked now: if x, y, the shape index or the buffer changed during the draw (an IKBD packet, a flip) there is no entry), the
; note: address [$202e], ROWS = [$2232] (dbra count 0..15), STRIDE = [$2234] ($90 = two columns, $98 = one) and copies of the rows x (16|8) bytes now on
; note: screen and of the shape rows.  Then the displaced instruction and on to $1b3c.
MAGIC   equ     $50545256
PD      equ     $88000
PTRB    equ     PB+$6200
        org     $1b34
        jmp     PTRB.l
        nop

        org     PB+$6200
ptrb:   lea     PD.l,a0
        cmpi.l  #MAGIC,(a0)
        bne.w   .tx
        clr.l   (a0)
        clr.l   4(a0)                   ; invalid until recorded
        move.l  $392dc.l,d0
        cmp.l   28(a0),d0
        bne.w   .tx
        move.w  $393fa.l,d0
        cmp.w   32(a0),d0
        bne.w   .tx
        move.w  $393fc.l,d0
        cmp.w   34(a0),d0
        bne.w   .tx
        move.w  $11d50.l,d0
        cmp.w   36(a0),d0
        bne.w   .tx
        movea.l $202e.l,a1
        move.l  a1,d0
        beq.w   .tx
        move.w  $2232.l,d7
        cmpi.w  #15,d7
        bhi.w   .tx                     ; (unsigned) not 0..15: leave it to the original
        move.w  $2234.l,d6
        cmpi.w  #$90,d6
        beq.s   .ok
        cmpi.w  #$98,d6
        bne.w   .tx
.ok:    move.l  28(a0),8(a0)
        move.w  32(a0),16(a0)
        move.w  34(a0),18(a0)
        move.w  36(a0),20(a0)
        move.w  d7,22(a0)
        move.w  d6,24(a0)
        move.l  a1,12(a0)
        lea     40(a0),a2
        cmpi.w  #$90,d6
        bne.s   .c1
.c2:    move.l  (a1)+,(a2)+
        move.l  (a1)+,(a2)+
        move.l  (a1)+,(a2)+
        move.l  (a1)+,(a2)+
        adda.w  d6,a1
        dbra    d7,.c2
        bra.s   .sh
.c1:    move.l  (a1)+,(a2)+
        move.l  (a1)+,(a2)+
        adda.w  d6,a1
        dbra    d7,.c1
.sh:    lea     $682d0.l,a3
        adda.w  $11d50.l,a3
        lea     296(a0),a2
        move.w  22(a0),d7
.s1:    move.l  (a3)+,(a2)+
        move.l  (a3)+,(a2)+
        dbra    d7,.s1
        move.l  #MAGIC,4(a0)
.tx:    move.w  #1,$392cc.l             ; the displaced instruction
        jmp     $1b3c.l
