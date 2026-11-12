; name: sw_head
; default: no
; site: $31486
; orig: 4df8770e4eb84f5a
; data: $b42e0 32
; note: ANALYST SCRATCH (work/vehicles_water): deterministic p3b head, no clock. Types selected by the
;       mask long at MASK ($b4e00, poked by the test): bit n = type n runs 5 sub-passes per tick.
;       PH walks 1..5 on masked types (PH 1-4: player sim only, no render; PH 5: world pass, exactly the
;       option A pass); other types: PH = 5, SUB = 0. Same D layout as p3b_head.
D       equ     $b42e0
MASK    equ     $b4e00
        org     $31486
        jsr     $b4000.l
        nop

        org     $b4000
        movem.l d0-d2/a0,-(a7)
        lea     D.l,a0
        clr.l   8(a0)                   ; SUB, HOLD
        clr.w   12(a0)                  ; SKIP
        moveq   #5,d0                   ; PH of a full pass
        tst.w   $40b6.w
        bne.s   .set
        move.l  MASK.l,d1
        move.w  $6220.w,d2
        btst    d2,d1
        beq.s   .set
        move.w  6(a0),d0
        addq.w  #1,d0
        cmpi.w  #5,d0
        bls.s   .ph
        moveq   #1,d0
.ph:    addq.w  #1,8(a0)                ; SUB = 1
        cmpi.w  #1,d0
        beq.s   .set                    ; PH 1: first pass of a group
        addq.w  #1,10(a0)               ; HOLD = 1 on passes 2..5
.set:   move.w  d0,6(a0)
        tst.w   D+8.l
        beq.s   .world                  ; unmasked type: the whole pass
        cmpi.w  #1,d0
        beq.s   .world                  ; PH 1: pre-world block then sub-step 1 through the loop body
        movem.l (a7)+,d0-d2/a0          ; PH 2-5: player sub-step only
        addq.l  #4,a7                   ; drop the return into $3148e
        jsr     $33bca.l
        clr.w   $7020.w
        cmpi.w  #5,D+6.l
        bne.s   .loop
        jmp     $31576.l                ; PH 5: post-world block, render
.loop:  tst.w   MASK+4.l                ; test option: render the sub-passes too (HUD gauges, view, renderer, flip)
        beq.s   .noren
        lea     $770e.w,a6
        jmp     $3158c.l
.noren: jmp     $31486.l
.world: movem.l (a7)+,d0-d2/a0
        lea     $770e.w,a6              ; displaced
        jmp     $4f5a.w                 ; displaced jsr, as a tail call

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
