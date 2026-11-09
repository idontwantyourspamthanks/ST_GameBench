; name: p4_ptr_a
; default: no
; stage: 2
; site: $1390
; orig: 20390001c49a
; data: $bd200 288
; note: P4 item 2, software mouse pointer (work/notes/p4_raster.md section 3), part A of two (needs p4_ptr_b to ever skip;
;       either one alone is harmless: the original path runs every VBL).
;       The VBL handler $1270 restores the 16 saved lines of the pointer ($1c49e -> $1c49a) and redraws it into the displayed
;       buffer $2df78 at EVERY VBL: 11.7 k cycles per VBL (measured, 8 MHz), 12 of 13 VBLs of a pass redo the same thing.
;       This hook (at `move.l $1c49a.l,d0`, after the hide test) skips restore+draw when the result is provably the same:
;         [$1c49a] == the address we recorded after the last draw (nothing hid the pointer / cleared it since),
;         [$2df78] [$2df92] [$2df94] equal the inputs of that draw, [$2c1be] == 0 (no animation step to take),
;         the ROWS x (8|16 B) screen rectangle under the pointer equals the image the draw left there (compared with cmpm).
;       Then restore writes the saved pixels S over it and the draw saves S again and ORs the pointer back: identical bytes,
;       identical save area, so nothing is skipped that changes a pixel.  Any other state: the original code, and part B
;       (after the draw, at $14c4) records the new image and inputs.  A flip changes [$2df78], so the first VBL after a flip is
;       always the full path (restores into the old buffer, which is why the cache cannot outlive a flip).
;       Data block P ($bd200): +0 FLAG.w (the draw ran) +2 VALID.w +4 BUF.l +8 A4.l +12 X.w +14 Y.w +16 ROWS.w +18 STRIDE.w
;       +20 NBUF.l +24 NX.w +26 NY.w (inputs read before the draw) +32 IMG[256] (the drawn rectangle).
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
        org     $1390
        jmp     $bd000.l

        org     $bd000
ptr_a:  move.l  $1c49a.l,d0
        beq.s   .full                   ; nothing drawn yet / hidden: the original draws
        lea     P.l,a0
        cmp.l   pA4(a0),d0
        bne.s   .full
        tst.w   pVALID(a0)
        beq.s   .full
        tst.w   $2c1be.l
        bne.s   .full                   ; animated pointer: the original advances the frame counter
        move.l  $2df78.l,d1
        cmp.l   pBUF(a0),d1
        bne.s   .full
        move.w  $2df92.l,d1
        cmp.w   pX(a0),d1
        bne.s   .full
        move.w  $2df94.l,d1
        cmp.w   pY(a0),d1
        bne.s   .full
        movea.l d0,a1                   ; the rectangle on screen
        lea     pIMG(a0),a2             ; what we left there
        move.w  pROWS(a0),d7
        move.w  pSTR(a0),d6
        cmpi.w  #$90,d6
        bne.s   .one
.two:   cmpm.l  (a2)+,(a1)+
        bne.s   .full
        cmpm.l  (a2)+,(a1)+
        bne.s   .full
        cmpm.l  (a2)+,(a1)+
        bne.s   .full
        cmpm.l  (a2)+,(a1)+
        bne.s   .full
        adda.w  d6,a1
        dbra    d7,.two
        jmp     $14c4.l                 ; identical result: nothing to do
.one:   cmpm.l  (a2)+,(a1)+
        bne.s   .full
        cmpm.l  (a2)+,(a1)+
        bne.s   .full
        adda.w  d6,a1
        dbra    d7,.one
        jmp     $14c4.l
.full:  lea     P.l,a0
        move.w  #1,pFLAG(a0)            ; part B records this draw
        move.l  $2df78.l,pNBUF(a0)      ; the inputs, read before the original reads them
        move.w  $2df92.l,pNX(a0)
        move.w  $2df94.l,pNY(a0)
        move.l  $1c49a.l,d0             ; the displaced instruction (and its flags for the beq.w at $1396)
        jmp     $1396.l
