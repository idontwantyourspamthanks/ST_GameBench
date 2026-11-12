; name: test_cpyx
; default: no
; stage: 2
; site: $12ce0
; orig: 48e77f107220
; data: $cef00 16
; note: TEST ONLY (PMBusErr, work/notes/buserr.md): p6_cpy with the chunk size taken from memory so a run can sweep it.  ROWS.w ($cef00, default 10)
;       must divide 200; NCH.w ($cef02) = 200/ROWS; STRIDE.w ($cef04) = 160*ROWS.  Poke them at the apply flip.  Conflicts with p6_cpy (same site).
BLT     equ     $bdc04
ROWS    equ     $cef00
        org     $12ce0
        jmp     $ced00.l

        org     $ced00
cpy:    cmpi.l  #$b17e0001,BLT.l
        bne.s   orig
        movem.l d1-d3,-(a7)
        move.w  #2,$ffff8a20.w
        move.w  #2,$ffff8a22.w
        move.w  #2,$ffff8a2e.w
        move.w  #2,$ffff8a30.w
        move.w  #80,$ffff8a36.w
        move.b  #2,$ffff8a3a.w
        move.b  #3,$ffff8a3b.w
        clr.b   $ffff8a3d.w
        moveq   #-1,d1
        move.w  d1,$ffff8a28.w
        move.w  d1,$ffff8a2a.w
        move.w  d1,$ffff8a2c.w
        move.w  ROWS+2.l,d2
        subq.w  #1,d2
        move.w  ROWS+4.l,d3
.l:     move.l  a0,$ffff8a24.w
        move.l  a1,$ffff8a32.w
        move.w  ROWS.l,$ffff8a38.w
        move.b  #$c0,$ffff8a3c.w
        adda.w  d3,a0
        adda.w  d3,a1
        dbra    d2,.l
        movea.l -8(a0),a2
        movem.l (a7)+,d1-d3
        move.w  #-1,d0
        rts
orig:   movem.l d1-d7/a3,-(a7)
        moveq   #$20,d1
        jmp     $12ce6.l
