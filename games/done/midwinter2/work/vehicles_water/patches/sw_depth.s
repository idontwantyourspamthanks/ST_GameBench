; name: sw_depth
; default: no
; site: $345aa
; orig: 3038764cd0786740
; note: ANALYST SCRATCH: sub_034586 (button apply selector 3, Submarine $36 = 3; Balloon/Rocket/Parachute too) integrates
;       $764c += $6740 (route/depth, $6740 = $675a>>4, constant over a tick) then clamps to [$e0c0,$2ee0].
;       SUB = 1: five sub-steps with a Bresenham remainder (D2ACC, cleared at HOLD = 0): q = floor((ACC+e)/5), ACC = ACC+e-5q,
;       so the group adds exactly e; d0 = $764c + q, then the original clamp/store continues at $345b2.
D       equ     $b42e0
ACCD    equ     $b4e10
        org     $345aa
        jsr     $b4f40.l
        nop

        org     $b4f40
        tst.w   D+8.l                   ; SUB
        beq.s   .orig
        movem.l d1-d2/a0,-(a7)
        lea     ACCD.l,a0
        tst.w   D+10.l                  ; HOLD
        bne.s   .acc
        clr.w   (a0)
.acc:   move.w  $6740.w,d1
        add.w   (a0),d1                 ; S = ACC + e
        ext.l   d1
        move.l  d1,d0
        jsr     $b40c8.l                ; q = floor(S/5)
        move.w  d0,d2
        muls.w  #5,d2
        sub.w   d2,d1
        move.w  d1,(a0)                 ; ACC = S - 5q
        add.w   $764c.w,d0              ; $764c + q
        movem.l (a7)+,d1-d2/a0
        rts
.orig:  move.w  $764c.w,d0              ; the replaced instructions
        add.w   $6740.w,d0
        rts
