; name: p4_ptr_a
; default: yes
; site: $87e
; orig: 20390001d2ba
; data: $75e00 288
; note: software mouse pointer, part A of two (master p4_ptr_a / work/notes/p4_raster.md section 3, re-sited: master $1390 -> WW1 $87e; needs p4_ptr_b to ever skip, either one alone is harmless:
;       the original path runs every VBL).  The VBL handler $774 restores the 16 saved lines of the pointer ($1d2be -> [$1d2ba]) and redraws it into the displayed buffer [$2ed98]
;       at EVERY VBL (~11.7 k cycles in master), 12 of 13 VBLs of a pass redo the same thing.  This hook (at `move.l $1d2ba.l,d0`, after the hide test `tst.w $1d4d2 / bne.w $9b8`)
;       skips restore + draw when the result is provably the same:
;         [$1d2ba] == the address recorded after the last draw (nothing hid the pointer / cleared it since),
;         [$2ed98] [$2edb2] [$2edb4] equal the inputs of that draw, the frame word [$2cfde] equals the one the draw used and is a STATIC frame (0, or $320 = the WW1-only `cmp.w #$320,d0 / beq.b`
;         that skips the animation step; any other value animates: the original advances it every 8th VBL), the ROWS x (8|16 B) screen rectangle under the pointer equals the image the draw left (cmpm).
;       Then restore writes the saved pixels S over it and the draw saves S again and ORs the pointer back: identical bytes, identical save area.  Any other state: the original code, and part B
;       (after the draw, at $9b8) records the new image and inputs.  A flip changes [$2ed98], so the first VBL after a flip is always the full path.
;       WW1 differences from master: addresses ($1c49a -> $1d2ba, $2df78 -> $2ed98, $2df92/94 -> $2edb2/b4, $1c69e/$1c6a0 -> $1d4be/$1d4c0, animation word $2c1be -> $2cfde), and the frame word is
;       not always 0 here (WW1's pointer sprite has animated frames), so it is part of the recorded inputs.
;       Data block P ($75e00): +0 FLAG.w (the draw ran) +2 VALID.w +4 BUF.l +8 A4.l +12 X.w +14 Y.w +16 ROWS.w +18 STRIDE.w +20 NBUF.l +24 NX.w +26 NY.w (inputs read before the draw)
;       +28 FR.w (frame word the recorded draw used) +30 NFR.w (frame word read before the draw) +32 IMG[256] (the drawn rectangle).
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
        org     $87e
        jmp     $75c40.l

        org     $75c40
ptr_a:  move.l  $1d2ba.l,d0
        beq.w   .full                   ; nothing drawn yet / hidden: the original draws
        lea     P.l,a0
        cmp.l   pA4(a0),d0
        bne.w   .full
        tst.w   pVALID(a0)
        beq.w   .full
        move.w  $2cfde.l,d1
        cmp.w   pFR(a0),d1
        bne.w   .full                   ; another pointer frame
        move.l  $2ed98.l,d1
        cmp.l   pBUF(a0),d1
        bne.w   .full
        move.w  $2edb2.l,d1
        cmp.w   pX(a0),d1
        bne.w   .full
        move.w  $2edb4.l,d1
        cmp.w   pY(a0),d1
        bne.w   .full
        movea.l d0,a1                   ; the rectangle on screen
        lea     pIMG(a0),a2             ; what we left there
        move.w  pROWS(a0),d7
        move.w  pSTR(a0),d6
        cmpi.w  #$90,d6
        bne.s   .one
.two:   cmpm.l  (a2)+,(a1)+
        bne.w   .full
        cmpm.l  (a2)+,(a1)+
        bne.w   .full
        cmpm.l  (a2)+,(a1)+
        bne.w   .full
        cmpm.l  (a2)+,(a1)+
        bne.w   .full
        adda.w  d6,a1
        dbra    d7,.two
        jmp     $9b8.l                  ; identical result: nothing to do
.one:   cmpm.l  (a2)+,(a1)+
        bne.w   .full
        cmpm.l  (a2)+,(a1)+
        bne.w   .full
        adda.w  d6,a1
        dbra    d7,.one
        jmp     $9b8.l
.full:  lea     P.l,a0
        move.w  #1,pFLAG(a0)            ; part B records this draw
        move.l  $2ed98.l,pNBUF(a0)      ; the inputs, read before the original reads them
        move.w  $2edb2.l,pNX(a0)
        move.w  $2edb4.l,pNY(a0)
        move.w  $2cfde.l,pNFR(a0)
        move.l  $1d2ba.l,d0             ; the displaced instruction (and its flags for the beq.w at $884)
        jmp     $884.l
