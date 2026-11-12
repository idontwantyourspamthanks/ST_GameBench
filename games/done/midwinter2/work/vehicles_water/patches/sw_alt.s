; name: sw_alt
; default: no
; site: $33f50
; orig: 303867503200
; note: ANALYST SCRATCH: p3b_alt with the group-start freeze. sub_033f40 (flags bit0/6: Minisub, Submarine, Frogman, air types):
;         P0 = thr*$7652 (vertical, $764c += floor(P0/131072)), speed $6772 = ((thr*$7654)<<2)>>16.
;       $7652/$7654 (sin/cos of the bank/pitch $6746) are written by $3467c at the END of every pass, so in the original tick they
;       are the previous tick's values. With a bank that changes (Minisub/Frogman/helicopter button) the sub-passes see a moving
;       $7652/$7654 and p3b_alt drifts by 1 unit per tick. Fix: compute P0 and the speed on the first pass of the group (HOLD = 0),
;       keep them in FRZ (long P0, word speed) and replay them on the other four. Everything else as p3b_alt.
D       equ     $b42e0
FRZ     equ     $b4e18
        org     $33f50
        jsr     $b4d00.l

        org     $b4d00
        move.w  $6750.w,d0              ; the replaced instructions: d0 = d1 = thr
        move.w  d0,d1
        tst.w   D+8.l                   ; SUB
        beq.s   .out                    ; not a masked type: the original continues at $33f56
        addq.l  #4,a7
        tst.w   D+10.l                  ; HOLD
        bne.s   .hold
        muls.w  $7652.w,d0              ; P0 = thr*sin(bank)
        muls.w  $7654.w,d1
        asl.l   #2,d1
        swap    d1
        move.l  d0,FRZ.l
        move.w  d1,FRZ+4.l
        bra.s   .use
.hold:  move.l  FRZ.l,d0
        move.w  FRZ+4.l,d1
.use:   move.w  d1,$6772.w              ; speed
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
