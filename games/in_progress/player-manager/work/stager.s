
        org $eed2
stager:
        lea     $f000(pc),a0
        lea     $b3000.l,a2
        move.w  #3503,d2
.cp:
        move.l  (a0)+,(a2)+
        dbra    d2,.cp
        suba.l  #($eed2-$00a2),a1
        lea     ($0090-$00a2)(a1),a0
        jmp     (a0)
