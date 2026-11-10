; name: p3b_head
; default: yes
; site: $31486
; orig: 4df8770e4eb84f5a
; data: $b42e0 32
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
MASK    equ     $17f000          ; scratch: sub-tick types 12,13,14,15,16,18 (bit n = type n)
D       equ     $b42e0
        org     $31486
        jsr     $b4000.l
        nop

        org     $b4000
        movem.l d0-d2/a0,-(a7)
        lea     D.l,a0
        moveq   #GRP,d2                 ; d2 = clock units this pass consumes
        move.l  #MASK,d0
        move.w  $6220.w,d1
        btst    d1,d0
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

        org     $b4d00
fdiv5:  addi.w  #3000,d0
        mulu.w  #52429,d0
        swap    d0
        lsr.w   #2,d0
        subi.w  #600,d0
        ext.l   d0
        rts
        org     $b4d14
bres:   add.w   (a1),d1
        ext.l   d1
        move.l  d1,d0
        bsr.s   $b4d00
        move.w  d0,d2
        muls.w  #5,d2
        sub.w   d2,d1
        move.w  d1,(a1)
        add.w   d0,d0
        rts
