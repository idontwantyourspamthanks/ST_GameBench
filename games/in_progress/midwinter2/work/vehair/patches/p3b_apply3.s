; name: p3b_apply3
; default: no
; site: $34586
; orig: 30386220b07c0011
; note: SCRATCH (MW2VehAir). Apply selector 3, sub_034586 (types 9, 15, 16, 17), run once per tick in
;       the 5 Hz game with $6740 = rate>>4 (constant over a group, see p3b_ctl):
;         type 17 (Parachute): $7680 = clamp($7680 + $6740, -100, -10)   (fall speed state)
;         others:              $764c = clamp($764c + $6740, -8000, 12000)
;       Sub-pass (SUB = 1):
;         type 17: the state update is not integer-splittable (the fall speed is doubled once per tick in
;                  $33cc2, p3b_par) so it runs ONCE per group, on the first pass (HOLD = 0), unmodified;
;                  passes 2..5 skip it.
;         others:  the altitude gets 1/5 of $6740 per pass (Bresenham on units of 1, remainder AR, cleared
;                  on the first pass), so the group adds exactly $6740 (monotone partial sums: the
;                  clamp gives the same final value). On the first pass the group start altitude and the
;                  full step are saved (ALT0, BSTEP) for the Balloon block (p3b_bal).
D       equ     $b42e0
D2      equ     $b8f00                  ; scratch variable block (words)
AR      equ     D2+0
ALT0    equ     D2+2
BSTEP   equ     D2+4
        org     $34586
        jsr     $b8100.l
        nop

        org     $b8100
        tst.w   D+8.l                   ; SUB
        beq.s   .plain
        move.w  $6220.w,d0
        cmpi.w  #$11,d0
        bne.s   .alt
        tst.w   D+10.l                  ; Parachute: apply only on the first pass of a group
        bne.s   .skip
        addq.l  #4,a7
        jmp     $34590.l                ; the original
.skip:  addq.l  #4,a7
        rts
.alt:   tst.w   D+10.l
        bne.s   .step
        clr.w   AR.l
        move.w  $764c.w,ALT0.l
        move.w  $6740.w,BSTEP.l
.step:  move.w  $6740.w,d1
        lea     AR.l,a1
        jsr     $b4d14.l                ; d0.l = 2q
        asr.w   #1,d0
        add.w   $764c.w,d0
        move.w  #$e0c0,d6
        move.w  #$2ee0,d7
        jsr     $4f8a.w
        move.w  d0,$764c.w
        addq.l  #4,a7
        rts
.plain: move.w  $6220.w,d0              ; displaced
        cmpi.w  #$11,d0
        rts
