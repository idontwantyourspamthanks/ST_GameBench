; name: p3b_head_fix
; default: no
; site: $31486
; orig: 4df8770e4eb84f5a
; data: $b42e0 32
; data: $b4c40 8
; note: FIX of p3b_head (v1.2): (1) the sea wave phase ($1877c/$1dfba, +8 per RENDER at $1dcae, read by the player sim through $506e/$5062) advances once per 5 Hz group,
;       the head writes it back before every pass (a render-only pass no longer advances it), (2) a per-type table TAB replaces `cmpi.w #13,$6220` (13 only here),
;       (3) the head moved to $b4d80 (it was full). Use with p3b_alt_fix instead of p3b_alt. Original text follows.
; note: P3 partial-B scheduler (work/notes/tick_inventory.md sections 4-6); replaces
;       tick_head (option A). It runs at the head of the in-game frame loop ($31486).
;       Real time comes from the tick_vbl clock ($B3400): a long in units of 1/300 s,
;       every VBL adds 6 (50 Hz) or 5 (60 Hz), so the tick rate is the same on both.
;       FOOT pass (type $6220 = 13 and $40b6 = 0, the only type validated for the
;       25 Hz player step): one pass = one SUBT = 12 units (0.04 s) sub-tick, PH walks 1..5.
;         PH 1-4  sub-tick: only the player sim (jsr $33bca), then render if on
;                 time (jump into the loop at $3158c) or straight back to the head.
;         PH 5    world tick: the whole logic block, exactly as option A (5 Hz).
;       Any other type: one pass = one GRP = 60 units (0.2 s, 5 Hz) tick, PH = 5, i.e. option A.
;       Real time not yet simulated is ACC (1/300 s units). Ahead (ACC < the pass length):
;       spin on the VBL clock (frame limiter). Another pass owed after this one:
;       SKIP = 1, so no render this pass (p3b_render handles PH 5; PH 1-4 never
;       reach the render). Catch-up is clamped to 3*GRP units; a gap longer than
;       4*GRP units resyncs (one pass, no burst), as tick_head.
;       Data block D = $B42E0 (zero at boot), used by every p3b_* hook and p5_ctl_x:
;         D+0  LAST.l  clock at the previous look      D+4  ACC.w  1/300 s owed
;         D+6  PH.w    1..5                            D+8  SUB.w  1 = 1/5 foot step
;         D+10 HOLD.w  1 = foot pass 2..5 of a group   D+12 SKIP.w 1 = no render now
;         D+14 HF.w, D+16 SACC.w (p3b_hdg)  D+18 BACC.w (p3b_bank)
;         D+20 ACCX.l, D+24 ACCY.l (p3b_pos)  D+28 ALT.l (p3b_alt)
;       Second blob, shared helpers for p3b_pos/hdg/alt/bank:
;         fdiv5 ($B40C8): d0.l := floor(d0.l/5) for -3000 <= d0 <= 62000 (word domain:
;           ((x+3000)*52429 >> 18) - 600, exact for 16-bit operands); touches nothing else.
;         bres ($B40DC): Bresenham step. In: d1.w = e2, a1 -> remainder word. Out:
;           d0.l = 2*q with q = floor((rem+e2)/5), remainder updated. Clobbers d1, d2.
;       Preserves d0-d2/a0; a6 and the displaced jsr as tick_head.
GRP     equ     60                      ; 1/300 s units: 0.2 s
SUBT    equ     12                      ; 0.04 s
CLOCK   equ     $b3400
D       equ     $b42e0
        org     $31486
        jsr     $b4d80.l
        nop

        org     $b4d80
        movem.l d0-d2/a0-a1,-(a7)
        lea     D.l,a0
        moveq   #GRP,d2                 ; d2 = clock units this pass consumes
        move.w  $6220.w,d0
        cmpi.w  #21,d0
        bhi.s   .wait
        lea     TAB(pc),a1
        tst.b   (a1,d0.w)
        beq.s   .wait
        tst.w   $40b6.w
        bne.s   .wait
        moveq   #SUBT,d2                ; foot: 25 Hz sub-tick
.wait:  move.l  CLOCK.l,d0
        move.l  d0,d1
        sub.l   (a0),d1                 ; 1/300 s since the previous look
        move.l  d0,(a0)
        cmpi.l  #4*GRP,d1
        bls.s   .acc
        moveq   #0,d1                   ; first entry or back from another screen:
        move.b  d2,d1                   ; resync, one pass, no catch-up burst
        clr.w   4(a0)
.acc:   add.w   d1,4(a0)
        cmp.w   4(a0),d2
        bgt.s   .wait                   ; ahead of real time: wait for VBLs
        sub.w   d2,4(a0)                ; this pass simulates one unit
        move.w  #3*GRP,d0
        cmp.w   4(a0),d0
        bge.s   .noclamp
        move.w  d0,4(a0)                ; bound the catch-up
.noclamp:
        clr.w   12(a0)
        cmp.w   4(a0),d2
        bgt.s   .ontime
        addq.w  #1,12(a0)               ; another pass owed: no render now
.ontime:
        moveq   #5,d0                   ; PH of a full (option A) pass
        clr.l   8(a0)                   ; SUB (8) and HOLD (10), adjacent words
        cmpi.w  #SUBT,d2
        bne.s   .set
        move.w  6(a0),d0
        addq.w  #1,d0                   ; foot: next sub-tick
        cmpi.w  #5,d0
        bls.s   .ph
        moveq   #1,d0
.ph:    addq.w  #1,8(a0)                ; SUB = 1
        subq.w  #1,d0
        beq.s   .first                  ; PH 1: first pass of a group
        addq.w  #1,10(a0)               ; HOLD = 1 on passes 2..5
.first: addq.w  #1,d0
        bsr     wave                    ; wave phase: one step per group, restored before every pass
.set:   move.w  d0,6(a0)
        cmpi.w  #5,d0
        beq.s   .world
        movem.l (a7)+,d0-d2/a0          ; sub-tick: player sim only
        addq.l  #4,a7                   ; drop the return into $3148e
        jsr     $33bca.l
        clr.w   $7020.w                 ; as option A's skip path
        tst.w   D+12.l
        bne.s   .loop
        lea     $770e.w,a6              ; on time: render this sub-tick
        jmp     $3158c.l                ; HUD gauges, view setup, renderer, flip
.loop:  jmp     $31486.l
.world: movem.l (a7)+,d0-d2/a0
        lea     $770e.w,a6              ; displaced
        jmp     $4f5a.w                 ; displaced jsr, as a tail call

; d0 = PH (1..5) of a foot pass; the wave phase of this group goes to the game's words
wave:   movem.l d0-d1/a1-a2,-(a7)
        lea     $b4c40.l,a1             ; WV.w +0, WVV.w +2
        tst.w   2(a1)
        bne.s   .a
        move.w  $1877c.l,(a1)           ; first group: the live phase
        move.w  #1,2(a1)
        bra.s   .set
.a:     cmpi.w  #1,d0
        bne.s   .set
        move.w  (a1),d1                 ; PH 1: next group
        addq.w  #8,d1
        andi.w  #$7e,d1
        move.w  d1,(a1)
.set:   move.w  (a1),d1
        move.w  d1,$1877c.l
        lea     $18574.l,a2
        adda.w  d1,a2
        move.l  a2,$1dfba.l
        movem.l (a7)+,d0-d1/a1-a2
        rts
TAB:    dc.b    0,0,0,0,0,0,0,0,0,0,0,0,0,1,0,0,0,0,0,0,0,0
        dc.b    0,0

        org     $b40c8
fdiv5:  addi.w  #3000,d0
        mulu.w  #52429,d0
        swap    d0
        lsr.w   #2,d0
        subi.w  #600,d0
        ext.l   d0
        rts
        org     $b40dc
bres:   add.w   (a1),d1
        ext.l   d1
        move.l  d1,d0
        bsr.s   $b40c8
        move.w  d0,d2
        muls.w  #5,d2
        sub.w   d2,d1
        move.w  d1,(a1)
        add.w   d0,d0
        rts
