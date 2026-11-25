; name: pop_spr16
; default: yes
; prog: populous
; site: $169c4
; orig: 223cffffffff4282
; note: Fast 16x16 masked sprite row loop for people/flags/markers ($16954, site $169c4).
;       1) Skips completely empty rows (mask == $ffff) in 12 cycles without shifting.
;       2) Fast shift-0 path when (x & 15) == 0 (no ror.l, no right-column write, 32-bit swap mask).
;       100% pixel-identical on STE and plain ST.  Blob $b6600.

        org     $169c4
        jmp     $b6600.l
        nop

        org     $b6600
spr16:  tst.w   d0                      ; shift == 0?
        beq.s   .s0
.sh:    cmpi.w  #-1,(a1)                ; empty row?
        beq.s   .sh_sk
        moveq   #-1,d1
        moveq   #0,d2
        moveq   #0,d4
        moveq   #0,d5
        moveq   #0,d6
        move.w  (a1)+,d1
        move.w  (a1)+,d2
        move.w  (a1)+,d4
        move.w  (a1)+,d5
        move.w  (a1)+,d6
        ror.l   d0,d1
        ror.l   d0,d2
        ror.l   d0,d4
        ror.l   d0,d5
        ror.l   d0,d6
        and.w   d1,(a0)
        or.w    d2,(a0)+
        and.w   d1,(a0)
        or.w    d4,(a0)+
        and.w   d1,(a0)
        or.w    d5,(a0)+
        and.w   d1,(a0)
        or.w    d6,(a0)+
        cmp.w   #$98,d7
        beq.s   .sh_nx
        swap    d1
        swap    d2
        swap    d4
        swap    d5
        swap    d6
        and.w   d1,(a0)
        or.w    d2,(a0)+
        and.w   d1,(a0)
        or.w    d4,(a0)+
        and.w   d1,(a0)
        or.w    d5,(a0)+
        and.w   d1,(a0)
        or.w    d6,(a0)+
.sh_nx: adda.l  d7,a0
        dbra    d3,.sh
        jmp     $16a1e.l
.sh_sk: lea     10(a1),a1
        lea     160(a0),a0
        dbra    d3,.sh
        jmp     $16a1e.l

.s0:    move.w  (a1)+,d1                ; shift == 0: 16px aligned, 32-bit mask
        cmpi.w  #-1,d1
        beq.s   .s0_sk
        tst.w   d1
        beq.s   .s0_sol
        move.w  d1,d2
        swap    d1
        move.w  d2,d1
        move.l  (a0),d2
        and.l   d1,d2
        or.l    (a1)+,d2
        move.l  d2,(a0)+
        move.l  (a0),d2
        and.l   d1,d2
        or.l    (a1)+,d2
        move.l  d2,(a0)+
        lea     152(a0),a0
        dbra    d3,.s0
        jmp     $16a1e.l
.s0_sol:
        move.l  (a1)+,(a0)+
        move.l  (a1)+,(a0)+
        lea     152(a0),a0
        dbra    d3,.s0
        jmp     $16a1e.l
.s0_sk: addq.l  #8,a1
        lea     160(a0),a0
        dbra    d3,.s0
        jmp     $16a1e.l
