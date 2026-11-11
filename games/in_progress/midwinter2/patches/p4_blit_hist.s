; name: p4_blit_hist
; default: no
; site: $38d14
; data: $b4b00 192
; note: MEASUREMENT ONLY, never default (work/notes/blitter.md): histogram of interior 16-px group counts per
;       scanline row of every fill call.  At $38d14 (after the code-table decode, before
;       `jmp (a2)`) a0/a1 still point at the {offset,mask} records of the d7+1 rows.  Per row:
;       k = (offR - offL)/8 (group distance); bin g = k-1 interior groups (cap 39) if k>0,
;       bin 40 = single-group / crossed row.  bin 41 = calls, bin 42 = rows.
HIST    equ     $b4b00
        org     $38d14
        jmp     $b4900.l

        org     $b4900
        movem.l d0-d1/d7/a0-a2,-(a7)
        lea     HIST.l,a2
        addq.l  #1,41*4(a2)
.row:   addq.l  #1,42*4(a2)
        move.w  (a0)+,d0
        addq.w  #2,a0
        move.w  (a1)+,d1
        addq.w  #2,a1
        sub.w   d0,d1
        bgt.s   .wide
        moveq   #40,d1
        bra.s   .cnt
.wide:  lsr.w   #3,d1
        subq.w  #1,d1
        cmp.w   #39,d1
        ble.s   .cnt
        moveq   #39,d1
.cnt:   lsl.w   #2,d1
        addq.l  #1,0(a2,d1.w)
        dbra    d7,.row
        movem.l (a7)+,d0-d1/d7/a0-a2
        andi.w  #1,d6
        beq.s   .p0
        movea.l d2,a2
        jmp     (a2)
.p0:    movea.l d3,a2
        jmp     (a2)
