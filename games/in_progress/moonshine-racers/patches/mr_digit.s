; name: mr_digit
; default: yes
; site: $14d98
; orig: 5347284b1219
; doc: Faster HUD score-digit glyph kernel $14d98 (pixel-identical): the two colours the game uses ($cd, $c7) get straight-line row code instead of 8 btst/sne/or per row.
; note: Moonshine Racers render speed-up 3 (work/notes/render_patches.md).  $14d98 (called by the score/time text routine $11d42, ~15 rows x 5 characters a pass while the score changes) turns a glyph
; note: byte pair (d1 = shape, d2 = shadow) into the four plane bytes d3 = (bit n of d4 ? d1) | (bit n+4 of d4 ? d2) | (d1 & d2) with btst/sne/branch per plane (~270 cycles per row).
; note: The game only passes d4 = $cd (and $c7 when $11c6 is set): for these the per-plane choice is constant: $cd -> d1, d1&d2, d1|d2, d1|d2 ; $c7 -> d1, d1, d1|d2, d2 (each equals the stock formula
; note: because d1&d2 is contained in d1 and d2).  Any other d4 runs a verbatim copy of the stock loop.  Site: $14d98 `subq.w #1,d7 / movea.l a3,a4 / move.b (a1)+,d1` (6 B; the stock loop top $14d9c is
; note: inside the patched bytes, hence the copy) -> `jmp $B3C00.l`.  d0-d3 end with the stock low bytes (byte operations only), a3 gets the stock tail.
        org     $14d98
        jmp     $B3C00.l

        org     $B3C00
PL      macro
        btst    #\1,d4
        sne     d3
        and.b   d1,d3
        btst    #\2,d4
        beq.s   .n\@
        or.b    d2,d3
.n\@:   or.b    d0,d3
        move.b  d3,\3(a4)
        endm
digit:  subq.w  #1,d7
        movea.l a3,a4
        cmp.b   #$cd,d4
        beq.s   fcd
        cmp.b   #$c7,d4
        beq.w   fc7
.l:     move.b  (a1)+,d1                ; verbatim stock loop
        move.b  (a1)+,d2
        move.b  d1,d0
        and.b   d2,d0
        PL      0,4,0
        PL      1,5,2
        PL      2,6,4
        PL      3,7,6
        lea     $a0(a4),a4
        dbra    d7,.l
tail:   move.l  a3,d0
        addq.l  #7,d0
        andi.w  #$fff9,d0
        movea.l d0,a3
        rts
fcd:    move.b  (a1)+,d1
        move.b  (a1)+,d2
        move.b  d1,d0
        and.b   d2,d0
        move.b  d1,d3
        or.b    d2,d3
        move.b  d1,(a4)
        move.b  d0,2(a4)
        move.b  d3,4(a4)
        move.b  d3,6(a4)
        lea     $a0(a4),a4
        dbra    d7,fcd
        bra.s   tail
fc7:    move.b  (a1)+,d1
        move.b  (a1)+,d2
        move.b  d1,d0
        and.b   d2,d0
        move.b  d1,(a4)
        move.b  d1,2(a4)
        move.b  d1,d3
        or.b    d2,d3
        move.b  d3,4(a4)
        move.b  d2,d3
        move.b  d3,6(a4)
        lea     $a0(a4),a4
        dbra    d7,fc7
        bra.s   tail
