; name: pop_ptr
; default: no
; site: $16d80
; orig: 61000068 6100009a
; data: $c2400 448
; note: The software mouse pointer.  The game's VBL routine $16d70 restores the saved background of the pointer ($16dea) and
;       redraws the pointer ($16e20) into the displayed buffer at EVERY VBL (about 11.5 k cycles, 7.4 % of a busy frame at
;       8 MHz, whether or not anything moved): `016d80 bsr.w $16dea` / `016d84 bsr.w $16e20`, reached only when the hide count
;       $16d26 is 0.  Both are replaced by one call into this blob, which skips them when the result is provably the same
;       bytes, and otherwise runs the two original routines unchanged and records what the draw left.
;       The skip needs ALL of:
;         $16f12 (where the last draw put the pointer, 0 after a hide) == the address recorded after that draw,
;         the displayed buffer $3c50c, the pointer words $24786/$24788, the shape index $2169a, the sprite sheet $3d572,
;         and the draw's row count / stride words $2498c/$2498e equal to what that draw saw,
;         the ROWS x (16|8) screen bytes under the pointer == the image the draw left there (cmpm),
;         the 160 bytes of the shape the draw reads (sheet + table $22b06[shape] * 160) == the copy taken at that draw.
;       Then restore writes the saved pixels S over the rectangle and the draw saves S again and merges the shape back: the
;       same bytes, the same save area $2478c, the same $2498c/e/$16f12.  Nothing that changes a pixel or a variable is
;       skipped.  A flip changes $3c50c, so the first VBL after a flip is always the full path (it restores into the old
;       buffer, exactly as the original); a hide ($16d2e) clears $16f12; anything the game draws under a still pointer fails
;       the rectangle compare and is restored/redrawn as before.  Same design as Powermonger's p4_ptr (work/notes/display.md).
;       The images (rectangle, shape rows: ~2.5 k cycles to copy) are recorded only when a full draw finds the SAME inputs as
;       the draw before it (KEYV set): a pointer that moves every VBL pays the compare of the first few words and nothing
;       else, a pointer that stands still pays one extra full draw per frame.
;       Data block P ($c2400): +0 KEYV.w +2 VALID.w +4 BUF.l +8 A4.l +12 X.w +14 Y.w +16 SHP.w +18 ROWS.w +20 STR.w +24 SHEET.l
;       +32 IMG[256] (the drawn rectangle) +288 SHI[160] (the shape rows read by the draw).  Blob $c2000-$c23ff.
P       equ     $c2400
pKEYV   equ     0
pVALID  equ     2
pBUF    equ     4
pA4     equ     8
pX      equ     12
pY      equ     14
pSHP    equ     16
pROWS   equ     18
pSTR    equ     20
pSHEET  equ     24
pIMG    equ     32
pSHI    equ     288

        org     $16d80
        jsr     $c2000.l
        nop

        org     $c2000
ptr:    move.l  $16f12.l,d0
        beq.w   full                    ; nothing drawn / hidden: the original draws
        lea     P.l,a0
        tst.w   pKEYV(a0)
        beq.w   full
        cmp.l   pA4(a0),d0
        bne.w   full
        move.l  $3c50c.l,d1
        cmp.l   pBUF(a0),d1
        bne.w   full
        move.w  $24786.l,d1
        cmp.w   pX(a0),d1
        bne.w   full
        move.w  $24788.l,d1
        cmp.w   pY(a0),d1
        bne.w   full
        move.w  $2169a.l,d1
        cmp.w   pSHP(a0),d1
        bne.w   full
        move.l  $3d572.l,d1
        cmp.l   pSHEET(a0),d1
        bne.w   full
        move.w  $2498c.l,d7
        cmp.w   pROWS(a0),d7
        bne.w   full
        move.w  $2498e.l,d6
        cmp.w   pSTR(a0),d6
        bne.w   full
        tst.w   pVALID(a0)
        beq.w   fullrec                 ; same inputs as the last draw, images not recorded yet: record them now
        movea.l d0,a1                   ; the rectangle on screen ...
        lea     pIMG(a0),a2             ; ... against the image the draw left there
        cmpi.w  #$90,d6
        bne.s   .one
.two:   cmpm.l  (a2)+,(a1)+
        bne.s   .nf
        cmpm.l  (a2)+,(a1)+
        bne.s   .nf
        cmpm.l  (a2)+,(a1)+
        bne.s   .nf
        cmpm.l  (a2)+,(a1)+
        bne.s   .nf
        adda.w  d6,a1
        dbra    d7,.two
        bra.s   .shape
.one:   cmpm.l  (a2)+,(a1)+
        bne.s   .nf
        cmpm.l  (a2)+,(a1)+
        bne.s   .nf
        adda.w  d6,a1
        dbra    d7,.one
.shape: move.w  $2169a.l,d2             ; the shape rows, addressed as $16e84-$16ea2 do
        add.w   d2,d2
        lea     $22b06.l,a2
        move.w  (a2,d2.w),d2
        ext.l   d2
        movea.l $3d572.l,a3
        mulu.w  #$a0,d2
        adda.l  d2,a3
        lea     pSHI(a0),a2
        moveq   #9,d2
.sh:    cmpm.l  (a2)+,(a3)+
        bne.s   .nf
        cmpm.l  (a2)+,(a3)+
        bne.s   .nf
        cmpm.l  (a2)+,(a3)+
        bne.s   .nf
        cmpm.l  (a2)+,(a3)+
        bne.s   .nf
        dbra    d2,.sh
        rts                             ; identical result: nothing to do
.nf:    bra.w   fullrec                 ; the game drew under the pointer: draw again and re-record

full:   moveq   #0,d3                   ; keys only
        bra.s   draw
fullrec:moveq   #1,d3                   ; keys and images
draw:   lea     P.l,a0
        clr.w   pKEYV(a0)
        move.w  d3,pVALID(a0)           ; until the draw is done: 1 = record the images as well
        move.l  $3c50c.l,pBUF(a0)       ; the inputs, read before the draw reads them
        move.w  $24786.l,pX(a0)
        move.w  $24788.l,pY(a0)
        move.w  $2169a.l,pSHP(a0)
        move.l  $3d572.l,pSHEET(a0)
        jsr     $16dea.l                ; the original restore
        jsr     $16e20.l                ; the original draw
        lea     P.l,a0
        move.l  $3c50c.l,d0
        cmp.l   pBUF(a0),d0
        bne.w   .abort
        move.w  $24786.l,d0             ; an IKBD packet during the draw: no entry
        cmp.w   pX(a0),d0
        bne.w   .abort
        move.w  $24788.l,d0
        cmp.w   pY(a0),d0
        bne.w   .abort
        move.l  $16f12.l,d0
        beq.w   .abort
        movea.l d0,a1
        move.w  $2498c.l,d7
        cmpi.w  #15,d7
        bhi.w   .abort                    ; not 0..15 (dbra count): leave it to the original
        move.w  $2498e.l,d6
        cmpi.w  #$90,d6
        beq.s   .ok
        cmpi.w  #$98,d6
        bne.w   .abort
.ok:    move.l  d0,pA4(a0)
        move.w  d7,pROWS(a0)
        move.w  d6,pSTR(a0)
        move.w  #1,pKEYV(a0)            ; the inputs of this draw are recorded
        tst.w   pVALID(a0)
        beq.s   .out                    ; keys only: the images are taken when the next draw finds the same inputs
        lea     pIMG(a0),a2             ; copy what the draw left on screen
        cmpi.w  #$90,d6
        bne.s   .c1
.c2:    move.l  (a1)+,(a2)+
        move.l  (a1)+,(a2)+
        move.l  (a1)+,(a2)+
        move.l  (a1)+,(a2)+
        adda.w  d6,a1
        dbra    d7,.c2
        bra.s   .shp
.c1:    move.l  (a1)+,(a2)+
        move.l  (a1)+,(a2)+
        adda.w  d6,a1
        dbra    d7,.c1
.shp:   move.w  $2169a.l,d2             ; and the 160 shape bytes it read
        add.w   d2,d2
        lea     $22b06.l,a2
        move.w  (a2,d2.w),d2
        ext.l   d2
        movea.l $3d572.l,a3
        mulu.w  #$a0,d2
        adda.l  d2,a3
        lea     pSHI(a0),a2
        moveq   #9,d2
.s2:    move.l  (a3)+,(a2)+
        move.l  (a3)+,(a2)+
        move.l  (a3)+,(a2)+
        move.l  (a3)+,(a2)+
        dbra    d2,.s2
.out:   rts                             ; (pVALID is still 1: the images are recorded)
.abort: clr.w   pVALID(a0)
        rts
