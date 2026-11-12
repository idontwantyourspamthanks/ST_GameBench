; name: p7_cell_pre
; default: yes
; site: $1d8d4
; orig: 48e7fffe3e3867c4
; phase: deferred
; data: $b5c00 288
; note: P7 item 4 (work/notes/p7_cell_cull.md), part 1/2.  Entry of the terrain classify pass $1d8d4
;       (sole caller `bsr.w $1d8d4` at $1dc7c).  Replays the displaced `movem.l d0-d7/a0-a6,-(a7)`
;       and `move.w $67c4.w,d7`, then builds the per-frame constants that p7_cell_cull ($1d974) uses
;       to prove, before any slot lookup, that a land cell can emit no triangle.  Inert without
;       p7_cell_cull (it only writes blob data).  Data block D = $b5c00:
;         +2 KC.w  ceil((9*mY+4*mW)/64), mY=$1856a, mW=$1856c (view Y and W multipliers of height)
;         +4 HI.w  largest cell height for which the no-wrap guard holds; -1 = culling disabled
;         +$20 TC  16 x 8 B: upper bound of 9*Y+4*W over the 2 corner columns of a cell, by
;                  column entry i = -7..6 (offset (c+64), c = $c(cell) = 8*i; other entries poisoned)
;         +$a0 TR  16 x 8 B: the same for the rows (offset (e+64), e = $e(cell)); +1 folded in
;       Disabled (HI = -1) when: $67be != 0 ($1dcd2 would shift W), |mY| or |mW| > 16384, K < 0,
;       zc = $1878c < 0, a table word of T1/T2 entry 0 beyond +-12000, a table step beyond +-512, or
;       the no-wrap bound leaves no room (HLIM < 0 or zc > HLIM).
;       T1 = $188f8 (columns), T2 = $18a40 (rows): 8-byte entries X,Y,W,dist built by $1d5fe as
;       entry0 + k*step (16-bit adds), so Y1[i] = Y1[0]+i*D1y etc.; BY = |Ay|+7(|D1y|+|D2y|),
;       BW = |Aw|+7(|D1w|+|D2w|) with Ay = T1y0+T2y0-VY, VY = floor(-zc*mY/2^14), same for W;
;       HLIM = min(7998-BY, 13998-BW) bounds |h-zc|, HI = min(zc+HLIM, 32767).  Proof: the note.
D       equ     $b5c00
TC      equ     $b5c20
TR      equ     $b5ca0
S1      equ     $b5d00
S2      equ     $b5d04
C1      equ     $b5d08
C2      equ     $b5d0c
AY      equ     $b5d10
AW      equ     $b5d14
BB      equ     $b5d18
W1B     equ     $b5d1c

        org     $1d8d4
        jmp     $b5800.l
        nop

        org     $b5800
        movem.l d0-d7/a0-a6,-(a7)       ; displaced
        move.w  $67c4.w,d7              ; displaced
        move.l  d7,-(a7)                ; d7 is scratch below; restored at out
        move.w  #-1,D+4.l               ; disabled until everything below has passed
        tst.w   $67be.w
        bne.w   out
        move.w  $1856a.l,d0             ; mY
        move.w  $1856c.l,d1             ; mW
        cmp.w   #16384,d0
        bgt.w   out
        cmp.w   #-16384,d0
        blt.w   out
        cmp.w   #16384,d1
        bgt.w   out
        cmp.w   #-16384,d1
        blt.w   out
        ; K = 9*mY + 4*mW
        move.w  d0,d2
        ext.l   d2
        move.l  d2,d3
        asl.l   #3,d2
        add.l   d3,d2
        move.w  d1,d3
        ext.l   d3
        asl.l   #2,d3
        add.l   d3,d2
        bmi.w   out                     ; K < 0: not supported
        add.l   #63,d2
        asr.l   #6,d2                   ; KC = ceil(K/64) <= 3328
        move.w  d2,D+2.l
        ; zc
        move.w  $1878c.l,d3
        bmi.w   out
        move.w  d3,d6                   ; d6 = zc
        move.w  d3,d4
        neg.w   d4                      ; -zc
        move.w  d4,d5
        muls.w  d0,d4
        asr.l   #7,d4
        asr.l   #7,d4                   ; d4 = VY = floor(-zc*mY/2^14)
        muls.w  d1,d5
        asr.l   #7,d5
        asr.l   #7,d5                   ; d5 = VW
        ; ---- columns: T1 entry 0 and 1 (Y at +2, W at +4)
        move.w  $188fa.l,d2             ; t1y0
        cmp.w   #12000,d2
        bgt.w   out
        cmp.w   #-12000,d2
        blt.w   out
        move.w  $188fc.l,d3             ; t1w0
        cmp.w   #12000,d3
        bgt.w   out
        cmp.w   #-12000,d3
        blt.w   out
        move.w  $18902.l,d0
        sub.w   d2,d0                   ; D1y
        cmp.w   #512,d0
        bgt.w   out
        cmp.w   #-512,d0
        blt.w   out
        move.w  $18904.l,d1
        sub.w   d3,d1                   ; D1w
        cmp.w   #512,d1
        bgt.w   out
        cmp.w   #-512,d1
        blt.w   out
        ext.l   d2
        ext.l   d3
        ext.l   d0
        ext.l   d1
        ; C1 = 9*t1y0 + 4*t1w0
        move.l  d2,d7
        asl.l   #3,d7
        add.l   d2,d7
        move.l  d3,-(a7)
        asl.l   #2,d3
        add.l   d3,d7
        move.l  (a7)+,d3
        move.l  d7,C1.l
        ; S1 = 9*D1y + 4*D1w
        move.l  d0,d7
        asl.l   #3,d7
        add.l   d0,d7
        move.l  d1,-(a7)
        asl.l   #2,d1
        add.l   d1,d7
        move.l  (a7)+,d1
        move.l  d7,S1.l
        ; AY = t1y0 - VY, AW = t1w0 - VW ; partials 7|D1y|, 7|D1w|
        sub.l   d4,d2
        move.l  d2,AY.l
        sub.l   d5,d3
        move.l  d3,AW.l
        tst.l   d0
        bpl.s   .p1
        neg.l   d0
.p1:    tst.l   d1
        bpl.s   .p2
        neg.l   d1
.p2:    move.l  d0,d2
        asl.l   #3,d0
        sub.l   d2,d0                   ; 7|D1y|
        move.l  d1,d2
        asl.l   #3,d1
        sub.l   d2,d1                   ; 7|D1w|
        move.l  d0,BB.l
        move.l  d1,W1B.l
        ; ---- rows: T2 entry 0 and 1
        move.w  $18a42.l,d2             ; t2y0
        cmp.w   #12000,d2
        bgt.w   out
        cmp.w   #-12000,d2
        blt.w   out
        move.w  $18a44.l,d3             ; t2w0
        cmp.w   #12000,d3
        bgt.w   out
        cmp.w   #-12000,d3
        blt.w   out
        move.w  $18a4a.l,d0
        sub.w   d2,d0                   ; D2y
        cmp.w   #512,d0
        bgt.w   out
        cmp.w   #-512,d0
        blt.w   out
        move.w  $18a4c.l,d1
        sub.w   d3,d1                   ; D2w
        cmp.w   #512,d1
        bgt.w   out
        cmp.w   #-512,d1
        blt.w   out
        ext.l   d2
        ext.l   d3
        ext.l   d0
        ext.l   d1
        ; C2 = 9*t2y0 + 4*t2w0
        move.l  d2,d7
        asl.l   #3,d7
        add.l   d2,d7
        move.l  d3,-(a7)
        asl.l   #2,d3
        add.l   d3,d7
        move.l  (a7)+,d3
        move.l  d7,C2.l
        ; S2 = 9*D2y + 4*D2w
        move.l  d0,d7
        asl.l   #3,d7
        add.l   d0,d7
        move.l  d1,-(a7)
        asl.l   #2,d1
        add.l   d1,d7
        move.l  (a7)+,d1
        move.l  d7,S2.l
        ; BY = |t2y0 + AY| + 7|D1y| + 7|D2y| ; BW likewise (d2 = BY, d3 = BW)
        add.l   AY.l,d2
        bpl.s   .q1
        neg.l   d2
.q1:    add.l   AW.l,d3
        bpl.s   .q2
        neg.l   d3
.q2:    tst.l   d0
        bpl.s   .q3
        neg.l   d0
.q3:    tst.l   d1
        bpl.s   .q4
        neg.l   d1
.q4:    move.l  d0,d7
        asl.l   #3,d0
        sub.l   d7,d0                   ; 7|D2y|
        move.l  d1,d7
        asl.l   #3,d1
        sub.l   d7,d1                   ; 7|D2w|
        add.l   BB.l,d0
        add.l   d0,d2                   ; BY
        add.l   W1B.l,d1
        add.l   d1,d3                   ; BW
        move.l  #7998,d0
        sub.l   d2,d0                   ; 7998 - BY
        move.l  #13998,d1
        sub.l   d3,d1                   ; 13998 - BW
        cmp.l   d0,d1
        bge.s   .q5
        move.l  d1,d0                   ; HLIM = min
.q5:    tst.l   d0
        bmi.w   out
        moveq   #0,d1
        move.w  d6,d1                   ; zc (>= 0)
        cmp.l   d0,d1
        bgt.w   out                     ; zc > HLIM: the lower side of |h-zc| is not covered
        add.l   d1,d0                   ; zc + HLIM
        cmp.l   #32767,d0
        ble.s   .q6
        move.l  #32767,d0
.q6:    move.w  d0,D+4.l                ; HI: enabled
        ; ---- tables: entry k (i = k-8): C + (k-8)*S + max(0,S) (+1 for rows)
        lea     TC.l,a0
        move.l  C1.l,d0
        move.l  S1.l,d1
        bsr.s   build
        lea     TR.l,a0
        move.l  C2.l,d0
        move.l  S2.l,d1
        addq.l  #1,d0                   ; floor slack of the K term, folded here
        bsr.s   build
out:    move.l  (a7)+,d7
        jmp     $1d8dc.l

; a0 = table, d0 = C, d1 = S -> 16 entries of 8 bytes, entries 0 and 15 poisoned. Clobbers d0-d2.
build:  move.l  a0,-(a7)
        move.l  d1,d2
        asl.l   #3,d2
        sub.l   d2,d0                   ; C - 8*S
        tst.l   d1
        bmi.s   .b1
        add.l   d1,d0                   ; + max(0,S)
.b1:    moveq   #15,d2
.b2:    move.l  d0,(a0)
        addq.l  #8,a0
        add.l   d1,d0
        dbra    d2,.b2
        movea.l (a7)+,a0
        move.l  #$3fffffff,(a0)         ; i = -8
        move.l  #$3fffffff,120(a0)      ; i = 7
        rts
