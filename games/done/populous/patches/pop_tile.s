; name: pop_tile
; default: yes
; prog: populous
; site: $14314
; orig: 2079000228b8e748
; note: Fast 32-bit longword 32x24 terrain/object tile blit (replaces $14314, ~40% of a patched busy frame).
;       1) Eliminates all 4 mulu.w instructions per tile (3x mulu #$a0 + 1x mulu #$1e0 -> shifts).
;       2) Skips completely empty ($ffff) 16px halves (~25% of halves on busy maps).
;       3) Copies completely opaque ($0000) 16px halves with 2x move.l (~16% of halves).
;       4) Duplicates 16-bit mask with swap to merge 2 bitplanes per longword (and.l/or.l) on masked halves.
;       100% pixel-identical on both STE and plain ST.  Blob $b6200.

        org     $14314
        jmp     $b6200.l
        nop

        org     $b6200
tile:   movea.l $0228b8.l,a0
        lsl.w   #3,d0                   ; d0 = x * 8
        lsl.w   #3,d1                   ; d1 = y * 8
        ext.l   d0
        ext.l   d1
        adda.l  d0,a0                   ; + x * 8
        suba.l  d1,a0                   ; - y * 8
        add.w   d1,d0                   ; d0 = (x + y) * 8
        sub.w   d2,d0                   ; d0 = (x + y) * 8 - height
        ext.l   d0
        move.l  d0,d1
        lsl.l   #2,d0
        add.l   d1,d0                   ; * 5
        lsl.l   #5,d0                   ; * 160
        adda.l  d0,a0
        adda.l  $03c510.l,a0            ; + back buffer
        movea.l $03c55c.l,a6            ; tile sheet
        andi.l  #$ffff,d3
        move.l  d3,d4
        lsl.l   #4,d3
        sub.l   d4,d3                   ; * 15
        lsl.l   #5,d3                   ; * 480 ($1e0)
        adda.l  d3,a6
        move.l  d7,-(a7)
        moveq   #-1,d7                  ; d7.w = $ffff for fast 4-cycle empty-mask test
        moveq   #23,d5                  ; 24 rows
.row:   ; --- left 16px half ---
        move.w  (a6)+,d4                ; mask (sets Z for $0000!)
        beq.s   .lsolid
        cmp.w   d7,d4                   ; $ffff = empty?
        beq.s   .lskip
        move.w  d4,d6
        swap    d4
        move.w  d6,d4                   ; d4 = (mask << 16) | mask
        move.l  (a0),d6
        and.l   d4,d6
        or.l    (a6)+,d6
        move.l  d6,(a0)+
        move.l  (a0),d6
        and.l   d4,d6
        or.l    (a6)+,d6
        move.l  d6,(a0)+
        bra.s   .right
.lskip: addq.l  #8,a6
        addq.l  #8,a0
        bra.s   .right
.lsolid:
        move.l  (a6)+,(a0)+
        move.l  (a6)+,(a0)+
.right: ; --- right 16px half ---
        move.w  (a6)+,d4                ; mask (sets Z for $0000!)
        beq.s   .rsolid
        cmp.w   d7,d4                   ; $ffff = empty?
        beq.s   .rskip
        move.w  d4,d6
        swap    d4
        move.w  d6,d4
        move.l  (a0),d6
        and.l   d4,d6
        or.l    (a6)+,d6
        move.l  d6,(a0)+
        move.l  (a0),d6
        and.l   d4,d6
        or.l    (a6)+,d6
        move.l  d6,(a0)+
        lea     $90(a0),a0
        dbra    d5,.row
        move.l  (a7)+,d7
        rts
.rskip: addq.l  #8,a6
        lea     $98(a0),a0
        dbra    d5,.row
        move.l  (a7)+,d7
        rts
.rsolid:
        move.l  (a6)+,(a0)+
        move.l  (a6)+,(a0)+
        lea     $90(a0),a0
        dbra    d5,.row
        move.l  (a7)+,d7
        rts
