; name: p3b_pos
; default: yes
; site: $344f8
; orig: c1c2c3c24840
; note: P3 partial-B: sub_0344ac position integrator at 1/5 step. Original
;       ($344f8-$3450b), d0 = sin, d1 = cos (Q14), d2 = speed $6772:
;         Dx = floor(sin*speed/65536); X += Dx;  (same for Y)
;       The site is the first three instructions (muls d2,d0; muls d2,d1; swap d0).
;       Not foot (SUB = 0): they are replayed and the original continues at $344fe.
;       Foot (SUB = 1): one call = one of 5 sub-ticks; the rest of the original up to
;       $3450b is skipped (jmp $3450c).
;         P = sin(HF)*speed ; ACC += P ; q = floor(ACC/(5*65536)) ; X += q ;
;         ACC -= q*5*65536
;       ACC is cleared on the first pass of the group (HOLD = 0). HF (D+14, from
;       p3b_hdg) is the heading the 5 Hz tick would END on, so all 5 sub-ticks use the
;       same P and the group sum is exactly the original Dx, also while turning
;       (tick_inventory.md 5.4). sin/cos are reloaded from HF.
;       Clobbers d0, d1, a0, a1 (d3/d4 saved) (dead after the site; the original
;       reloads d0/d1 at $3450c).
D       equ     $b42e0
        org     $344f8
        jsr     $b413e.l

        org     $b413e
        tst.w   D+8.l                   ; SUB
        bne.s   .sub
        muls.w  d2,d0                   ; the replaced instructions
        muls.w  d2,d1
        swap    d0
        rts
.sub:   addq.l  #4,a7                   ; skip the rest of the original
        movem.l d3-d4,-(a7)
        lea     $44a4.w,a0
        move.w  D+14.l,d0               ; HF
        andi.w  #$3fe,d0
        lea     (a0,d0.w),a0
        move.w  (a0),d0                 ; sin(HF)
        move.w  $100(a0),d1             ; cos(HF)
        muls.w  d2,d0                   ; Px
        muls.w  d2,d1                   ; Py
        lea     D+20.l,a0
        tst.w   D+10.l                  ; HOLD
        bne.s   .acc
        clr.l   (a0)
        clr.l   4(a0)
.acc:   lea     $66e6.w,a1
        bsr.s   .axis
        move.l  d1,d0
        addq.l  #4,a0
        lea     $66ea.w,a1
        bsr.s   .axis
        movem.l (a7)+,d3-d4
        jmp     $3450c.l
.axis:  move.l  (a0),d3                 ; ACC += P
        add.l   d0,d3
        move.l  d3,d0
        swap    d0
        ext.l   d0                      ; floor(ACC/65536), |.| <= 3000
        jsr     $b40c8.l                ; q = floor(ACC/(5*65536))
        add.l   d0,(a1)
        muls.w  #5,d0
        swap    d0
        clr.w   d0                      ; q*5*65536
        sub.l   d0,d3
        move.l  d3,(a0)
        rts
