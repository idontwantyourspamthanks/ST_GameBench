; name: p7_cell_pre
; default: yes
; site: $18304
; data: $b5200 256
; data: $b5300 2
; note: P7 cell early-outs (work/notes/p7_cell.md), part 1/2 of the object-cell filter (needs p7_cell_obj; inert without it).
; note: Entry of the terrain scene build sub_018304 (sole caller `jsr $18304` at $14e56). Its first instruction `jsr $18362.l`
; note: (grid clear, 6 bytes) becomes `jsr $b5000.l`; the blob ends in `jmp $18362.l`, whose rts returns to $1830a.
; note: Per frame, after sub_01d0a0 has built the in-range object list ($1d288: $1d41a+1 words, the low word of the grid cell
; note: address of each object; $1d41a = -1 when the list is empty, see $1d13e subq / $1d0c2 bmi), the blob sets one byte in
; note: a 256-byte table per entry at index (word >> 6) & $ff (all other bytes cleared first) and sets the word VALID = 1.
; note: p7_cell_obj reads the table at $1748c: a cell whose index byte is 0 cannot be in the list (hash collisions only
; note: ever produce a 1, i.e. fall back to the original scan), so the scan of sub_01d41e can be skipped exactly.
; note: Registers: d0-d7/a0-a1 saved/restored (all dead here anyway).
TBL     equ     $b5200
VALID   equ     $b5300

        org     $18304
        jsr     $b5000.l

        org     $b5000
        movem.l d0-d7/a0-a1,-(a7)
        lea     TBL+256,a1
        moveq   #0,d0
        moveq   #0,d1
        moveq   #0,d2
        moveq   #0,d3
        moveq   #0,d4
        moveq   #0,d5
        moveq   #0,d6
        moveq   #0,d7
        movem.l d0-d7,-(a1)             ; 8 x 32 bytes = the 256-byte table
        movem.l d0-d7,-(a1)
        movem.l d0-d7,-(a1)
        movem.l d0-d7,-(a1)
        movem.l d0-d7,-(a1)
        movem.l d0-d7,-(a1)
        movem.l d0-d7,-(a1)
        movem.l d0-d7,-(a1)
        move.w  $1d41a.l,d1             ; as sub_01d41e: negative = no entries, else entries 0..d1
        bmi.s   .done
        lea     $1d288.l,a0
        moveq   #1,d2
.fill:  move.w  (a0)+,d0
        lsr.w   #6,d0
        and.w   #$ff,d0
        move.b  d2,(a1,d0.w)            ; a1 = TBL after the clears
        dbra    d1,.fill
.done:  move.w  #1,VALID.l
        movem.l (a7)+,d0-d7/a0-a1
        jmp     $18362.l
