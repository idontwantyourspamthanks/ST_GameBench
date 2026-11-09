; name: p4_ptr_b
; default: yes
; stage: 2
; site: $14c4
; orig: 08380001fc00
; note: P4 item 2, part B of two (needs p4_ptr_a, data block P of that file).  `btst.b #1,$fc00.w` at $14c4: the end of the
;       pointer code (also the target of the hide path and of part A's skip).  If part A flagged that the draw ran, record the
;       drawn rectangle: the inputs it saw (re-checked: if the mouse words changed during the draw the entry is not valid),
;       the address [$1c49a], ROWS = [$1c69e] (dbra count), STRIDE = [$1c6a0] ($90 = 2 columns, $98 = 1) and a copy of the
;       ROWS x (16|8) bytes now on screen.  Then the ACIA transmit wait (its own loop, the original is `btst / beq.b $14c4`)
;       and on to `move.b #$16,$fc02.w` at $14cc.  Only the pointer is cached; the IKBD protocol is untouched.
P       equ     $bd200
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
pIMG    equ     32
        org     $14c4
        jmp     $bd100.l

        org     $bd100
ptr_b:  lea     P.l,a0
        tst.w   pFLAG(a0)
        beq.w   .tx
        clr.w   pFLAG(a0)
        clr.w   pVALID(a0)
        tst.w   $2c1be.l
        bne.w   .tx                      ; animated: never cached
        move.l  $2df78.l,d0
        cmp.l   pNBUF(a0),d0
        bne.w   .tx                      ; the inputs moved during the draw (flip / IKBD packet): no entry
        move.w  $2df92.l,d0
        cmp.w   pNX(a0),d0
        bne.w   .tx
        move.w  $2df94.l,d0
        cmp.w   pNY(a0),d0
        bne.w   .tx
        movea.l $1c49a.l,a1
        move.l  a1,d0
        beq.w   .tx
        move.w  $1c69e.l,d7
        cmpi.w  #15,d7
        bhi.w   .tx                      ; (unsigned) not 0..15 rows-1: leave it to the original
        move.w  $1c6a0.l,d6
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
        jmp     $14cc.l
