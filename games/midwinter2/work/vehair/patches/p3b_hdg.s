; name: p3b_hdg
; default: yes
; site: $345e0
; orig: d0790000f984
; note: P3 partial-B: sub_0345c4 heading and lean at 1/5 step. Original
;       ($345dc-$34613), x = $f984 + $6740 (fatigue drift + this tick's yaw delta):
;         heading ($6294 = $6742 = $764a) = ($6742 + x) & $3fe
;         lean    ($674e)                 = sext10(($674e + x) & $3fe)
;                                           ($674e is cleared at $33bfe: a level)
;       The & $3fe makes the effective step e = x & ~1 (even).
;       The site is the second instruction (add.w $f984.l,d0, after move.w $6742.w,d0).
;       Not foot (SUB = 0): it is replayed and the original continues at $345e6.
;       Foot (SUB = 1): the rest of the original up to $34613 is replaced (jmp $34614):
;       lean as the original (level); heading advances by e/5 per call in units of 2
;       (Bresenham): e2 = e/2 ; S = SACC + e2 ; q = floor(S/5) ; SACC = S - 5q ;
;       heading += 2q. Over a group with constant e this moves it exactly e. On the
;       first pass of a group (HOLD = 0) HF (D+14) = the heading the 5 Hz tick ends on
;       = ($6742 + e) & $3fe, used by p3b_pos for all 5 steps.
;       Free regs here: d0, d1, a1; d2 saved.
D       equ     $b42e0
        org     $345e0
        jsr     $b41be.l

        org     $b41be
        tst.w   D+8.l                   ; SUB
        bne.s   .sub
        add.w   $f984.l,d0              ; the replaced instruction
        rts
.sub:   addq.l  #4,a7                   ; skip the rest of the original
        move.l  d2,-(a7)
        move.w  $f984.l,d1
        add.w   $6740.w,d1              ; x
        move.w  $674e.w,d0
        add.w   d1,d0
        andi.w  #$3fe,d0
        lsl.w   #6,d0
        asr.w   #6,d0
        move.w  d0,$674e.w              ; lean level, unchanged
        andi.w  #$fffe,d1               ; e = x & ~1
        tst.w   D+10.l                  ; HOLD
        bne.s   .nostart
        move.w  $6742.w,d0
        add.w   d1,d0
        andi.w  #$3fe,d0
        move.w  d0,D+14.l               ; HF: heading at the end of the original tick
.nostart:
        asr.w   #1,d1                   ; e2
        lea     D+16.l,a1               ; SACC
        jsr     $b4d14.l                ; d0 = 2q
        add.w   $6742.w,d0
        andi.w  #$3fe,d0
        move.w  d0,$6294.w
        move.w  d0,$6742.w
        move.w  d0,$764a.w
        move.l  (a7)+,d2
        jmp     $34614.l
