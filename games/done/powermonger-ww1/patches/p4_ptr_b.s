; name: p4_ptr_b
; default: yes
; site: $9b8
; orig: 08380001fc00
; note: software mouse pointer, part B of two (master p4_ptr_b, re-sited $14c4 -> $9b8; needs p4_ptr_a, data block P of that file).  `btst.b #1,$fc00.w` at $9b8: the end of the
;       pointer code (also the target of the hide path and of part A's skip).  If part A flagged that the draw ran, record the drawn rectangle: the inputs it saw (re-checked: if the mouse
;       words, the buffer or the frame word changed during the draw the entry is not valid), the address [$1d2ba], ROWS = [$1d4be] (dbra count), STRIDE = [$1d4c0] ($90 = 2 columns, $98 = 1)
;       and a copy of the ROWS x (16|8) bytes now on screen.  A frame word other than 0 / $320 (animated pointer) is never cached.  Then the ACIA transmit wait (its own loop, the original
;       is `btst / beq.b $9b8`) and on to `move.b #$16,$fc02.w` at $9c0.  Only the pointer is cached; the IKBD protocol is untouched.
P       equ     $75e00
pFLAG   equ     0
pVALID  equ     2
pBUF    equ     4
pA4     equ     8
pX      equ     12
pY      equ     14
pROWS   equ     16
pSTR    equ     18
pNBUF   equ     20
pNX     equ     24
pNY     equ     26
pFR     equ     28
pNFR    equ     30
pIMG    equ     32
        org     $9b8
        jmp     $75d20.l

        org     $75d20
ptr_b:  lea     P.l,a0
        tst.w   pFLAG(a0)
        beq.w   .tx
        clr.w   pFLAG(a0)
        clr.w   pVALID(a0)
        move.w  $2cfde.l,d0
        cmp.w   pNFR(a0),d0
        bne.w   .tx                      ; the frame moved during the draw (animation step): no entry
        tst.w   d0
        beq.s   .fok
        cmpi.w  #$320,d0
        bne.w   .tx                      ; animated: never cached
.fok:   move.w  d0,pFR(a0)
        move.l  $2ed98.l,d0
        cmp.l   pNBUF(a0),d0
        bne.w   .tx                      ; the inputs moved during the draw (flip / IKBD packet): no entry
        move.w  $2edb2.l,d0
        cmp.w   pNX(a0),d0
        bne.w   .tx
        move.w  $2edb4.l,d0
        cmp.w   pNY(a0),d0
        bne.w   .tx
        movea.l $1d2ba.l,a1
        move.l  a1,d0
        beq.w   .tx
        move.w  $1d4be.l,d7
        cmpi.w  #15,d7
        bhi.w   .tx                      ; (unsigned) not 0..15 rows-1: leave it to the original
        move.w  $1d4c0.l,d6
        cmpi.w  #$90,d6
        beq.s   .ok
        cmpi.w  #$98,d6
        bne.w   .tx
.ok:    move.l  pNBUF(a0),pBUF(a0)
        move.w  pNX(a0),pX(a0)
        move.w  pNY(a0),pY(a0)
        move.w  d7,pROWS(a0)
        move.w  d6,pSTR(a0)
        move.l  a1,pA4(a0)
        lea     pIMG(a0),a2
        cmpi.w  #$90,d6
        bne.s   .c1
.c2:    move.l  (a1)+,(a2)+
        move.l  (a1)+,(a2)+
        move.l  (a1)+,(a2)+
        move.l  (a1)+,(a2)+
        adda.w  d6,a1
        dbra    d7,.c2
        bra.s   .v
.c1:    move.l  (a1)+,(a2)+
        move.l  (a1)+,(a2)+
        adda.w  d6,a1
        dbra    d7,.c1
.v:     move.w  #1,pVALID(a0)
.tx:    btst.b  #1,$fffffc00.w
        beq.s   .tx
        jmp     $9c0.l
