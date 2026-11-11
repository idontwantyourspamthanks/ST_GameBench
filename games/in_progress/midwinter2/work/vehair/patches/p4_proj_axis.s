; name: p4_proj_axis
; default: yes
; site: $3bfa2
; orig: 3015322d0006
; note: $3bfa2 (coord x matrix column >>14). If exactly one of the 3 column multipliers
;       is +/-$4000 (=+/-1.0 in 2.14) and the other two are 0, then per coord c:
;       (c*$4000)<<2 swap = c; (c*$c000)<<2 swap = -c (mod 2^16, neg.w identical incl.
;       $8000); 0*c = 0. So the muls/asl/swap triple becomes a copy/neg/clr.
;       Otherwise, if one multiplier is 0, a 2-muls loop (0*c=0 exact); else the original at $3bfac. Dead on exit (callers reload):
;       d3-d5. Kept: a2,a3 advanced, d7=$ffff, d0-d2 = column.
        org     $3bfa2
        jmp     $b3900.l

        org     $b3900
        move.w  (a5),d0                 ; displaced
        move.w  6(a5),d1                ; displaced
        move.w  $c(a5),d2
        tst.w   d0
        bne.s   n0
        tst.w   d1
        bne.s   z1
        cmp.w   #$4000,d2               ; (0,0,m)
        beq.w   k2p
        cmp.w   #$c000,d2
        beq.w   k2m
fb:     tst.w   d0                      ; not +/-1-axis: skip muls by a zero multiplier
        beq.w   zA
        tst.w   d1
        beq.w   zB
        tst.w   d2
        beq.w   zC
        jmp     $3bfac.l                ; original loop
z1:     tst.w   d2                      ; (0,m,?)
        bne.w   fb
        cmp.w   #$4000,d1
        beq.w   k1p
        cmp.w   #$c000,d1
        beq.w   k1m
        bra.w   fb
n0:     tst.w   d1                      ; (m,?,?)
        bne.w   fb
        tst.w   d2
        bne.w   fb
        cmp.w   #$4000,d0
        beq.w   k0p
        cmp.w   #$c000,d0
        bne.w   fb
k0m:    bra.s   e0m
l0m:    move.w  (a2)+,d3
        neg.w   d3
        move.w  d3,(a3)+
        clr.w   (a3)+
        clr.w   (a3)+
e0m:    dbra    d7,l0m
        rts
k0p:    bra.s   e0p
l0p:    move.w  (a2)+,(a3)+
        clr.w   (a3)+
        clr.w   (a3)+
e0p:    dbra    d7,l0p
        rts
k1m:    bra.s   e1m
l1m:    move.w  (a2)+,d3
        neg.w   d3
        clr.w   (a3)+
        move.w  d3,(a3)+
        clr.w   (a3)+
e1m:    dbra    d7,l1m
        rts
k1p:    bra.s   e1p
l1p:    clr.w   (a3)+
        move.w  (a2)+,(a3)+
        clr.w   (a3)+
e1p:    dbra    d7,l1p
        rts
k2m:    bra.s   e2m
l2m:    move.w  (a2)+,d3
        neg.w   d3
        clr.w   (a3)+
        clr.w   (a3)+
        move.w  d3,(a3)+
e2m:    dbra    d7,l2m
        rts
k2p:    bra.s   e2p
l2p:    clr.w   (a3)+
        clr.w   (a3)+
        move.w  (a2)+,(a3)+
e2p:    dbra    d7,l2p
        rts
zA:     bra.s   eA                      ; d0 == 0
lA:     move.w  (a2)+,d3
        move.w  d3,d4
        muls.w  d1,d3
        muls.w  d2,d4
        asl.l   #2,d3
        asl.l   #2,d4
        swap    d3
        swap    d4
        clr.w   (a3)+
        move.w  d3,(a3)+
        move.w  d4,(a3)+
eA:     dbra    d7,lA
        rts
zB:     bra.s   eB                      ; d1 == 0
lB:     move.w  (a2)+,d3
        move.w  d3,d4
        muls.w  d0,d3
        muls.w  d2,d4
        asl.l   #2,d3
        asl.l   #2,d4
        swap    d3
        swap    d4
        move.w  d3,(a3)+
        clr.w   (a3)+
        move.w  d4,(a3)+
eB:     dbra    d7,lB
        rts
zC:     bra.s   eC                      ; d2 == 0
lC:     move.w  (a2)+,d3
        move.w  d3,d4
        muls.w  d0,d3
        muls.w  d1,d4
        asl.l   #2,d3
        asl.l   #2,d4
        swap    d3
        swap    d4
        move.w  d3,(a3)+
        move.w  d4,(a3)+
        clr.w   (a3)+
eC:     dbra    d7,lC
        rts
