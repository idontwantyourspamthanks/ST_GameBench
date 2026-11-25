; name: pop_cliff
; default: yes
; prog: populous
; site: $1457e
; orig: 3a3c000f381a
; note: Fast 32-bit longword cliff-face blit (replaces $1457e, 16x16 stacked cliff blocks).
;       Also checks pop_detail's Low Detail flag ($bd6c0.w): in Low Detail mode, skips cliff faces.
;       100% pixel-identical in High Detail mode (default).  Blob $b6400.

        org     $1457e
        jmp     $b6400.l

        org     $b6400
cliff:  tst.w   $bd6c0.l                ; Low Detail mode? (0 = High, 1 = Low)
        bne.s   .skipall
        moveq   #15,d5                  ; 16 rows
.row:   move.w  (a2)+,d4
        cmpi.w  #-1,d4
        beq.s   .rskip
        tst.w   d4
        beq.s   .rsolid
        move.w  d4,d6
        swap    d4
        move.w  d6,d4
        move.l  (a0),d6
        and.l   d4,d6
        or.l    (a2)+,d6
        move.l  d6,(a0)+
        move.l  (a0),d6
        and.l   d4,d6
        or.l    (a2)+,d6
        move.l  d6,(a0)+
        lea     $98(a0),a0
        dbra    d5,.row
        bra.s   .done
.rskip: addq.l  #8,a2
        lea     160(a0),a0
        dbra    d5,.row
        bra.s   .done
.rsolid:
        move.l  (a2)+,(a0)+
        move.l  (a2)+,(a0)+
        lea     $98(a0),a0
        dbra    d5,.row
.done:  suba.w  #$a00,a0
        suba.w  #$a0,a2
.skipall:
        rts
