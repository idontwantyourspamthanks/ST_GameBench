; name: pop2_ptr_a
; default: yes
; site: $1a1a
; orig: 20390000202e
; data: $88000 512
; note: Item 3 (work/notes/display.md): software mouse pointer, part A of two (pop2_ptr_b records; either alone is harmless: the original runs every VBL).
; note: The VBL handler $18fa restores the pointer's saved rectangle ($2032 -> [$202e], 16 rows) and redraws it into the shown buffer [$392dc] at
; note: EVERY VBL ($1a1a-$1b30, about 9,900 cycles, 6.9 % of a busy frame; a pass is 8 VBLs, the screen changes once per pass).  This hook (at
; note: `move.l $202e.l,d0`, after the hide test $1a10) skips restore + draw when the result is provably identical: the previous draw's inputs equal
; note: the current ones (buffer [$392dc], x [$393fa], y [$393fc], shape index [$11d50]), [$202e] is the address it drew at, the rectangle on screen
; note: still holds the image that draw left (cmpm) and the 16 x 8 shape bytes ([$682d0 + (short)[$11d50]]) are what it drew from.  Then restore writes the
; note: saved pixels S over the rectangle and the draw saves S again and ORs the pointer back: the same bytes, the same save area ($2032 is only
; note: referenced at $1a28, $1ac6, $1b68: restore, draw, hide), the same [$202e] / [$2232] / [$2234] (functions of x and y).  Any other state runs the original.
; note: Data block at $88000 (not in the payload image; no initial value is assumed: validity is the magic longs FLAG/VALID):
; note: +0 FLAG.l (the draw ran) +4 VALID.l +8 BUF.l +12 A4.l +16 X.w +18 Y.w +20 SHP.w +22 ROWS.w (dbra count) +24 STR.w +28 NBUF.l +32 NX.w +34 NY.w
; note: +36 NSHP.w +40 IMG[256] +296 SHAPE[128].
MAGIC   equ     $50545256               ; 'PTRV'
PD      equ     $88000
PTRA    equ     PB+$6000
        org     $1a1a
        jmp     PTRA.l

        org     PB+$6000
ptra:   cmpi.l  #MAGIC,PD+4.l
        bne.w   .full
        move.l  $202e.l,d0
        beq.w   .full                   ; nothing drawn / hidden: the original
        lea     PD.l,a0
        cmp.l   12(a0),d0
        bne.w   .full
        move.l  $392dc.l,d1
        cmp.l   8(a0),d1
        bne.w   .full
        move.w  $393fa.l,d1
        cmp.w   16(a0),d1
        bne.w   .full
        move.w  $393fc.l,d1
        cmp.w   18(a0),d1
        bne.w   .full
        move.w  $11d50.l,d1
        cmp.w   20(a0),d1
        bne.w   .full
        movea.l d0,a1                   ; the rectangle on screen
        lea     40(a0),a2               ; what the last draw left there
        move.w  22(a0),d7
        move.w  24(a0),d6
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
        bra.s   .shp
.one:   cmpm.l  (a2)+,(a1)+
        bne.w   .full
        cmpm.l  (a2)+,(a1)+
        bne.w   .full
        adda.w  d6,a1
        dbra    d7,.one
.shp:   lea     $682d0.l,a3             ; the shape rows the draw reads ($1ab6-$1ac2): 4 words per row
        adda.w  $11d50.l,a3
        lea     296(a0),a2
        move.w  22(a0),d7
.sl:    cmpm.l  (a2)+,(a3)+
        bne.w   .full
        cmpm.l  (a2)+,(a3)+
        bne.w   .full
        dbra    d7,.sl
        jmp     $1b34.l                 ; identical result: nothing to do (part B sees FLAG clear)
.full:  lea     PD.l,a0
        move.l  #MAGIC,(a0)             ; part B records this draw
        move.l  $392dc.l,28(a0)         ; the inputs, read before the original reads them
        move.w  $393fa.l,32(a0)
        move.w  $393fc.l,34(a0)
        move.w  $11d50.l,36(a0)
        move.l  $202e.l,d0              ; the displaced instruction (its flags feed the beq.w at $1a20)
        jmp     $1a20.l
