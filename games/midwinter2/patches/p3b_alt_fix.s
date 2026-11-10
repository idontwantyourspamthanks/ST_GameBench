; name: p3b_alt_fix
; default: no
; site: $33f50
; orig: 303867503200
; data: $b4c80 4
; note: FIX of p3b_alt (v1.2, found by MW2VehAir): the original uses the sin/cos of the PREVIOUS tick's bank ($7652/$7654, set by $3467c at the end of the previous tick) for the
;       altitude step and the speed; the 1/5 passes saw the sub-bank of their own pass (25/25 groups wrong with the mouse button held). FRZ captures them on the first pass of a group.
; note: P3 partial-B: sub_033f40 route/altitude branch ($764c accumulator, +5 per tick
;       on foot) at 1/5 step. Original ($33f50-$33f7a), thr = $6750:
;         d0 = ((thr*$7652)>>16)>>1 = floor(thr*$7652 / 131072)    (swap + asr.w #1)
;         d1 = ((thr*$7654)<<2)>>16 -> $6772 (speed)
;         $764c = clamp($764c + d0, $e0c0, $2ee0)                   (code after the site)
;       The site is the two moves at the entry $33f50 (d0 = d1 = thr). Not foot (SUB = 0):
;       they are replayed and the original continues at $33f56. Foot (SUB = 1): P0 = thr*$7652
;       is accumulated, d0 = floor(ACC/655360) with the remainder kept (ACC cleared on
;       the first pass of a group, HOLD = 0), so five passes with constant P0 add
;       exactly the original floor(P0/131072). The speed $6772 is written as the
;       original and the rest of the original up to $33f69 is skipped (jmp $33f6a with
;       d0.w = step).
D       equ     $b42e0
FRZ     equ     $b4c80
        org     $33f50
        jsr     $b4f00.l

        org     $b4f00
        move.w  $6750.w,d0              ; the replaced instructions: d0 = d1 = thr
        move.w  d0,d1
        tst.w   D+8.l                   ; SUB
        beq.s   .out                    ; not foot: the original continues at $33f56
        addq.l  #4,a7
        tst.w   D+10.l                  ; HOLD
        bne.s   .frz
        move.w  $7652.w,FRZ.l           ; group start: the coefficients the original uses
        move.w  $7654.w,FRZ+2.l
.frz:   muls.w  FRZ.l,d0                ; P0 = thr*sin(bank of the previous tick), frozen for the group
        muls.w  FRZ+2.l,d1
        asl.l   #2,d1
        swap    d1
        move.w  d1,$6772.w              ; speed, as the original
        movem.l d2-d3,-(a7)
        lea     D+28.l,a0
        tst.w   D+10.l                  ; HOLD
        bne.s   .acc
        clr.l   (a0)
.acc:   move.l  (a0),d2
        add.l   d0,d2                   ; S
        move.l  d2,d0
        swap    d0
        ext.l   d0                      ; floor(S/65536), |.| < 3000
        jsr     $b40c8.l                ; floor(./5)
        asr.l   #1,d0                   ; q = floor(S/655360), the step
        move.l  d0,d3
        muls.w  #10,d3
        swap    d3
        clr.w   d3                      ; q*655360
        sub.l   d3,d2
        move.l  d2,(a0)
        movem.l (a7)+,d2-d3
        jmp     $33f6a.l
.out:   rts
