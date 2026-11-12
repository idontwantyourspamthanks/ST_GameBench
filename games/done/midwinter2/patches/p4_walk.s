; name: p4_walk
; default: yes
; site: $3c5e2
; note: Edge walker $3c5e2 (draw-coord entry), part 1 of 4 (p4_walk, p4_walk_c4,
;       p4_walk_tab, p4_walk_ret: apply together).  The whole setup ($3c5c4-$3c689) is
;       re-implemented in the blob; the unrolled bodies $3c68a-$3d313 are reused
;       unchanged (entered by jmp (a1) with the identical register state).
;       Saves/restores only d2-d3/d5-d7/a0-a1/a3; d0,d1,d4 are dead after the call in
;       every caller; a2 is no longer touched (see work/notes/walker.md).
        org     $3c5e2
        jmp     $b3c00.l

        org     $b3c00
e2:     movem.l d2-d3/d5-d7/a0-a1/a3,-(a7)
        bra.s   e6
hz:     movem.l (a7)+,d2-d3/d5-d7/a0-a1/a3
        rts
c4:     movem.l d2-d3/d5-d7/a0-a1/a3,-(a7)      ; entry $b3c0c (from $501a / $3c5c4)
        neg.w   d1
        neg.w   d3
        neg.w   d0
        neg.w   d2
        add.w   #$a0,d0
        add.w   #$81,d1
        add.w   #$a0,d2
        add.w   #$81,d3
e6:     cmp.w   d1,d3
        beq.s   hz
        bpl.w   fwd

; TAIL tr,yb,adj : product (16.16 I-frac in tr.l) -> body register state, jmp into body
TAIL    macro
        move.w  \1,d0                   ; frac(I)
        swap    \1
        add.w   #320,\1                 ; int(I) = 320 + dx/dy
        moveq   #4,d4
        swap    d4                      ; $00040000
        move.w  d5,d4
        lsr.w   #1,d5
        add.w   d4,d4
        ifne    \3
        move.w  \1,d1
        move.w  \1,d2
        else
        move.w  \1,d2
        endc
        lsr.w   #1,d2
        add.w   d1,d1
        moveq   #$1e,d6
        moveq   #-8,d7
        or.b    #$e1,d1
        or.w    #7,d2
        move.w  #$8000,d3
        jmp     (a1)
        endm

; WALK xa,ya,xb,yb,adj,table : A = top endpoint (smaller y), B = bottom endpoint
WALK    macro
        lea     $17a66.l,a3             ; recip table; ymin=$688(a3), ymax=$686(a3)
        cmp.w   $688(a3),\2
        bpl.s   .m1\@
        move.w  \2,$688(a3)
.m1\@:  cmp.w   $686(a3),\4
        bmi.s   .m2\@
        move.w  \4,$686(a3)
.m2\@:  sub.w   \2,\4                   ; dy
        move.w  \2,d5
        add.w   \2,\2
        add.w   \2,\2                   ; 4*ya
        add.w   \2,d5                   ; 5*ya
        asl.w   #6,d5                   ; 320*ya
        add.w   \1,d5                   ; + xa
        ifne    \5
        addq.w  #1,d5
        endc
        lea     \6.l,a0
        adda.w  \2,a0
        add.w   \4,\4
        move.w  0(a3,\4.w),\2           ; T[dy]
        asl.w   #3,\4                   ; 16*dy
        lea     $3d30a.l,a1
        suba.w  \4,a1
        sub.w   \1,\3                   ; dx = xb-xa
        bmi.s   .ng\@
        mulu    \3,\2
        TAIL    \2,\4,\5
.ng\@:  neg.w   \3
        mulu    \3,\2
        neg.l   \2
        TAIL    \2,\4,\5
        endm

bwd:    WALK    d2,d3,d0,d1,1,$7b9d0
fwd:    WALK    d0,d1,d2,d3,0,$7b6b0
