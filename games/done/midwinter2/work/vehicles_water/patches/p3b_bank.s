; name: p3b_bank
; default: yes
; site: $3461e
; orig: 30386746d0786740
; note: P3 partial-B: sub_03461a bank integrator ($6746, button rate $6740 = $675a>>4) at
;       1/5 step. Original ($3461e-$3462d): d0 = sext10(($6746 + $6740) & $3fe), then
;       the clamp table for non-foot types and `move.w d0,$6746.w` at $34656.
;       The site is the first two instructions (move.w $6746.w,d0; add.w $6740.w,d0).
;       Not foot (SUB = 0): they are replayed, the original continues at $34626. Foot
;       (SUB = 1): Bresenham as p3b_hdg, e = $6740 & ~1, BACC (D+18) = remainder:
;       $6746 += 2*floor((BACC + e/2)/5) per pass, so a group with a constant button
;       state adds exactly e; leaves d0 = sext10 result and jumps to $3462e.
;       Free regs here: d0, d1, a1 (the routine saved d0/d1 and reloads d1 at $3462e).
D       equ     $b42e0
        org     $3461e
        jsr     $b4294.l
        nop

        org     $b4294
        tst.w   D+8.l                   ; SUB
        bne.s   .sub
        move.w  $6746.w,d0              ; the replaced instructions
        add.w   $6740.w,d0
        rts
.sub:   addq.l  #4,a7
        move.l  d2,-(a7)
        move.w  $6740.w,d1
        andi.w  #$fffe,d1               ; e
        asr.w   #1,d1                   ; e2
        lea     D+18.l,a1               ; BACC
        jsr     $b40dc.l                ; d0 = 2q
        add.w   $6746.w,d0
        andi.w  #$3fe,d0
        lsl.w   #6,d0
        asr.w   #6,d0
        move.l  (a7)+,d2
        jmp     $3462e.l
