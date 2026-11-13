; name: pop_land_score
; default: yes
; site: $18244
; orig: 4e55000048e77ee0
; note: The land score $18244(owner, cell) with the 17 calls of $181d6 inlined.
;       Same d0.l, same CCR (X included), same $3b040 and $37ef4, on every exit.
;       Paths, chosen from the arguments and map_bk2[cell] alone:
;         owner > 1, or cell outside 0..4095  -> the ORIGINAL routine (displaced
;                                                link/movem replayed, then $1824c);
;         cell 2 or more from every map edge  -> unrolled over the 17 offsets of the
;                                                table $22b8c (no edge test can fail);
;         cell within 2 of an edge            -> the same unrolled code, each offset
;                                                guarded by one bit of a 16-bit mask
;                                                (which offsets $181d6 keeps on the map);
;         castle centre ($2a) within 2 of an edge (never seen in play)
;                                             -> the original loop, $181d6 inlined.
;       Evidence, proof and gates: work/notes/landscore.md.
;       Blob $C0000-$C0FFF: code, then two 64-word constant tables. No variables.
BLK     equ     $36eb6                  ; map_blk, 64 x 64 bytes
BK      equ     $56aa                   ; map_bk2 ($3c560) - map_blk
CNT     equ     $3b040                  ; output: castle pieces in the 3 x 3
FLAT    equ     $37ef4                  ; output: 1 = a flat ($f) cell was counted

        org     $18244
        jmp     $c0000.l
        nop

        org     $c0000
; ---- one cell of the unrolled path -------------------------------------------
; d0 scratch, d1 flat flag, d2 = $f (flat tile, and 15 = the score step),
; d3 score, d4 = own field tile ($1f + owner), a0 = &map_blk[cell].
; \1 = offset, \2 = exit when a building stands on a cell that is not good
;      (X as the original leaves it: carry of cell + offset).
; The four tile values 0, $2f, $f, $1f/$20 are distinct, so testing the two common
; ones first gives the original's result (it tests 0 and $2f first, in $181d6).
CELL    macro
        move.b  (\1,a0),d0
        cmp.b   d4,d0
        beq.s   .g\@                    ; own field
        cmp.b   d2,d0
        bne.s   .o\@
        moveq   #1,d1                   ; flat
.g\@:   add.w   d2,d3                   ; +15 (the score is never 0 here: it is 65 + 15k)
        tst.b   (BK+\1,a0)
        beq.s   .n\@
        move.b  (BK+\1,a0),d0           ; something stands on a good cell
        cmp.b   #$20,d0
        ble.s   .n\@
        cmp.b   #$2c,d0
        bgt.s   .n\@
        bra.w   exb_keep                ; a building: 0, X from the add above
.o\@:   tst.b   d0
        beq.s   .n\@                    ; water ($181d6 = 3): nothing
        cmp.b   #$2f,d0
        bne.s   .b\@
        sub.w   d2,d3                   ; rock ($181d6 = 2): -15
        bra.s   .n\@
.b\@:   move.b  (BK+\1,a0),d0           ; other land: only the building test
        cmp.b   #$20,d0
        ble.s   .n\@
        cmp.b   #$2c,d0
        ble.w   \2
.n\@:
        endm

; The same for the 8 neighbours of a cell that holds $2a (castle centre):
; pieces $29..$2c are counted in $3b040 instead of ending the scan.
CCELL   macro
        move.b  (\1,a0),d0
        cmp.b   d4,d0
        beq.s   .g\@
        cmp.b   d2,d0
        bne.s   .o\@
        moveq   #1,d1
.g\@:   add.w   d2,d3
        move.b  (BK+\1,a0),d0
        beq.s   .n\@
        cmp.b   #$29,d0
        blt.s   .l\@
        cmp.b   #$2c,d0
        bgt.s   .n\@
        addq.w  #1,CNT.l
        bra.s   .n\@
.l\@:   cmp.b   #$20,d0
        ble.s   .n\@
        bra.w   exb_keep                ; $21..$28
.o\@:   tst.b   d0
        beq.s   .n\@
        cmp.b   #$2f,d0
        bne.s   .b\@
        sub.w   d2,d3
        bra.s   .n\@
.b\@:   move.b  (BK+\1,a0),d0
        cmp.b   #$29,d0
        blt.s   .m\@
        cmp.b   #$2c,d0
        bgt.s   .n\@
        addq.w  #1,CNT.l
        bra.s   .n\@
.m\@:   cmp.b   #$20,d0
        bgt.w   \2                      ; $21..$28
.n\@:
        endm

; A cell near an edge: bit 15 of d5 says whether this offset stays on the map
; ($181d6 would return 1 = off the map, and the original then skips the cell).
ECELL   macro
        add.w   d5,d5
        bcc.s   .e\@
        CELL    \1,\2
.e\@:
        endm

; ---- entry: stack = return, owner.w, cell.w ------------------------------------
lscore: cmpi.w  #1,4(sp)
        bhi.w   orig                    ; not a player number: the original code
        move.w  6(sp),d0
        subi.w  #$80,d0
        cmpi.w  #$f00,d0
        bhs.w   edge                    ; row 0, 1, 62, 63, or not a cell at all
        andi.w  #$3f,d0
        subq.w  #2,d0
        cmpi.w  #59,d0
        bhi.w   edge                    ; column 0, 1, 62, 63
        movem.l d1-d5/a0,-(sp)          ; 24 bytes: owner 28(sp), cell 30(sp) (d5 is used by `edge`)
        moveq   #$1f,d4
        add.w   28(sp),d4               ; own field tile
        lea     BLK.l,a0
        adda.w  30(sp),a0
        moveq   #$f,d2
        moveq   #0,d1
        clr.w   CNT.l
        move.b  (a0),d0                 ; the cell itself: $181d6 is not asked (offset 0)
        cmp.b   d4,d0
        beq.s   .g0
        cmp.b   d2,d0
        bne.w   exb_x0                  ; neither field nor flat: 0 (original X = 0)
        moveq   #1,d1
.g0:    moveq   #65,d3                  ; 50 + 15
        cmpi.b  #$2a,BK(a0)
        beq.w   castle
        CELL    -64,exb_x1
        CELL    1,exb_x0
        CELL    64,exb_x0
        CELL    -1,exb_x1
        CELL    -63,exb_x1
        CELL    65,exb_x0
        CELL    63,exb_x0
        CELL    -65,exb_x1
ring2:  CELL    -128,exb_x1
        CELL    2,exb_x0
        CELL    128,exb_x0
        CELL    -2,exb_x1
        CELL    -126,exb_x1
        CELL    130,exb_x0
        CELL    126,exb_x0
        CELL    -130,exb_x1
tail:   move.w  d1,FLAT.l
        cmpi.w  #$23,d3
        bge.s   .a
        moveq   #0,d3
.a:     cmpi.w  #$131,d3
        bne.s   .b
        move.w  #$bea,d3
.b:     moveq   #0,d0
        add.w   d3,d0                   ; d0.l = score; N, Z from it; V = C = X = 0
        movem.l (sp)+,d1-d5/a0
        rts

castle: addq.w  #1,CNT.l                ; the centre itself ($2a is in $29..$2c)
        CCELL   -64,exb_x1
        CCELL   1,exb_x0
        CCELL   64,exb_x0
        CCELL   -1,exb_x1
        CCELL   -63,exb_x1
        CCELL   65,exb_x0
        CCELL   63,exb_x0
        CCELL   -65,exb_x1
        bra.w   ring2

; ---- the three "return 0" exits of the unrolled path ---------------------------
exb_keep:                               ; X = carry of the last `add.w d2,d3`
        move.w  d1,FLAT.l
        movem.l (sp)+,d1-d5/a0
        moveq   #0,d0
        rts
exb_x1: move.w  d1,FLAT.l               ; X = 1 (cell + negative offset carries)
        movem.l (sp)+,d1-d5/a0
        moveq   #0,d0
        move.w  #$14,ccr                ; X, Z
        rts
exb_x0: move.w  d1,FLAT.l               ; X = 0
        movem.l (sp)+,d1-d5/a0
        sub.l   d0,d0                   ; d0 = 0, Z, X = N = V = C = 0
        rts

; ---- cells within 2 of an edge -----------------------------------------------------
; d5 = mask of the offsets 1..16 that stay on the map (bit 15 = offset 1): $181d6
; accepts cell + offset when 0 <= x + dx <= 63 and 0 <= y + dy <= 63 (dx = -2..2 is
; what it derives from offset & $3f), so the mask is mx[x] & my[y].
edge:   cmpi.w  #$1000,6(sp)
        bhs.w   orig                    ; not a cell: the original code
        movem.l d1-d5/a0,-(sp)          ; 24 bytes: owner 28(sp), cell 30(sp)
        move.w  30(sp),d0
        moveq   #$3f,d1
        and.w   d0,d1
        add.w   d1,d1
        lea     mx(pc),a0
        move.w  (a0,d1.w),d5
        lsr.w   #5,d0
        andi.w  #$7e,d0
        lea     my(pc),a0
        and.w   (a0,d0.w),d5
        lea     BLK.l,a0
        adda.w  30(sp),a0
        cmpi.b  #$2a,BK(a0)
        beq.w   ecastle
        moveq   #$1f,d4
        add.w   28(sp),d4
        moveq   #$f,d2
        moveq   #0,d1
        clr.w   CNT.l
        move.b  (a0),d0
        cmp.b   d4,d0
        beq.s   .g0
        cmp.b   d2,d0
        bne.w   exb_x0
        moveq   #1,d1
.g0:    moveq   #65,d3
        ECELL   -64,exb_x1
        ECELL   1,exb_x0
        ECELL   64,exb_x0
        ECELL   -1,exb_x1
        ECELL   -63,exb_x1
        ECELL   65,exb_x0
        ECELL   63,exb_x0
        ECELL   -65,exb_x1
        ECELL   -128,exb_x1
        ECELL   2,exb_x0
        ECELL   128,exb_x0
        ECELL   -2,exb_x1
        ECELL   -126,exb_x1
        ECELL   130,exb_x0
        ECELL   126,exb_x0
        ECELL   -130,exb_x1
        bra.w   tail

; ---- castle centre near an edge: the original loop, $181d6 inlined -----------------
ecastle:
        movem.l (sp)+,d1-d5/a0
        movem.l d1-d6/a0-a2,-(sp)       ; 36 bytes: owner 40(sp), cell 42(sp)
        move.w  40(sp),d6
        addi.w  #$1f,d6
        move.w  42(sp),d2
        clr.w   d4
        clr.w   CNT.l
        lea     $22b8c.l,a2
        lea     BLK.l,a0
        lea     $3c560.l,a1
        clr.w   d5
        clr.w   FLAT.l
.loop:  move.w  (a2)+,d3
        beq.s   .idx                    ; offset 0: $181d6 = 0
        move.w  d2,d1
        add.w   d3,d1
        blt.w   .next                   ; off the map
        cmpi.w  #$1000,d1
        bge.w   .next
        move.w  d3,d0
        andi.w  #$3f,d0
        cmpi.w  #3,d0
        ble.s   .p
        ori.w   #$ffc0,d0
.p:     move.w  d2,d1
        andi.w  #$3f,d1
        add.w   d1,d0
        blt.w   .next                   ; wrapped round a side
        cmpi.w  #$3f,d0
        bgt.w   .next
        add.w   d2,d3                   ; cell index
        move.b  (a0,d3.w),d0
        beq.w   .next                   ; water
        cmpi.b  #$2f,d0
        bne.s   .land
        addi.w  #$fff1,d4               ; rock
        bra.w   .next
.idx:   add.w   d2,d3
.land:  cmp.b   (a0,d3.w),d6
        beq.s   .good
        cmpi.b  #$f,(a0,d3.w)
        bne.s   .nflat
        move.w  #1,FLAT.l
.good:  tst.w   d4
        bne.s   .g2
        move.w  #$32,d4
.g2:    addi.w  #$f,d4
        bra.s   .obj
.nflat: tst.w   d5
        beq.s   .zero
.obj:   move.b  (a1,d3.w),d1
        cmpi.w  #9,d5
        bge.s   .bld
        cmpi.b  #$2a,(a1,d2.w)
        bne.s   .bld
        cmpi.b  #$29,d1
        blt.s   .bld
        cmpi.b  #$2c,d1
        bgt.s   .bld
        addq.w  #1,CNT.l
        bra.s   .next
.bld:   tst.w   d5
        beq.s   .next
        cmpi.b  #$20,d1
        ble.s   .next
        cmpi.b  #$2c,d1
        bgt.s   .next
.zero:  movem.l (sp)+,d1-d6/a0-a2
        moveq   #0,d0
        rts
.next:  addq.w  #1,d5
        cmpi.w  #$11,d5
        bne.w   .loop
        cmpi.w  #$23,d4
        bge.s   .t1
        clr.w   d4
.t1:    cmpi.w  #$131,d4
        bne.s   .t2
        move.w  #$bea,d4
.t2:    moveq   #0,d0
        move.w  d4,d0
        movem.l (sp)+,d1-d6/a0-a2
        rts

; ---- anything else: the original routine, untouched ----------------------------
orig:   link.w  a5,#0                   ; the two displaced instructions
        movem.l d1-d6/a0-a2,-(sp)
        jmp     $1824c.l

; ---- which offsets 1..16 stay on the map, by column and by row (bit 15 = offset 1) ----
mx:     dc.w    $ecec,$ffec
        dcb.w   60,$ffff
        dc.w    $ffb3,$b3b3
my:     dc.w    $7676,$ff76
        dcb.w   60,$ffff
        dc.w    $ffd9,$d9d9
