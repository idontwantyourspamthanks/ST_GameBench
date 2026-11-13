; name: test_pwalk
; default: no
; site: $0b6e2
; orig: 3039 0003b260
; data: $c6f40 16
; note: TEST ONLY (gate driver for tools/poptick.py; never in a build).  Makes the game's input a pure function of the world turn, so a patched run and an unpatched run see the same
;       pointer position and the same view in every turn, whatever their speed.  Site: `move.w $3b260.l,d0` at $b6e2, the water-phase toggle of the pass top (executed once per turn by the original and by the tick's
;       T, S and P passes, never by R passes, which jump over the top part to the render stage), BEFORE the pass renders.  The turn word is still the pass's own turn X.  MODE bit 0: the pointer words $24786/$24788 (ST pixels) from a 16-entry table, each
;       entry held two turns (edges, the x > 304 one-column case, the y > 184 clip, corners, panel areas, map); MODE bit 1: the view $37eb8/$249ec = (BX,BY) + a point on a 16-cell
;       square walked at one cell per turn (+x, +y, -x, -y, period 64 turns).  The host zeroes the IKBD packet handler's three position stores ($2003e, 30 bytes of nops) in both runs.
;       Data (zero in the live image): MODE.w BX.w BY.w SPINN.w at $c6f40 (the host pokes BX/BY = the snapshot's view - 8, clamped to 0..40).  SPINN = N: every turn
;       (T and S passes, i.e. the world logic) burns N `dbra` iterations (10 cycles each on a 68000, taken) before the walk - a world that costs more to compute, i.e. a slower machine
;       (the render passes are not slowed).  No interrupt is masked and no bus is held.
MODE    equ     $c6f40
BX      equ     $c6f42
BY      equ     $c6f44
SPINN   equ     $c6f46
        org     $0b6e2
        jmp     $c5800.l

        org     $c5800
        movem.l d0-d2/a0,-(a7)
        move.w  SPINN.l,d0
        beq.s   .nospin
        subq.w  #1,d0
.spin:  dbra    d0,.spin
.nospin: move.w $3c506.l,d0
        btst    #0,MODE+1.l
        beq.s   .view
        move.w  d0,d1
        lsr.w   #1,d1
        andi.w  #15,d1
        lsl.w   #2,d1
        lea     postab(pc),a0
        move.w  0(a0,d1.w),$24786.l
        move.w  2(a0,d1.w),$24788.l
.view:  btst    #1,MODE+1.l
        beq.s   .out
        move.w  d0,d2                   ; u = turn & 63, segment u >> 4 (+x, +y, -x, -y), r = u & 15
        andi.w  #63,d2
        move.w  d2,d1
        lsr.w   #4,d2
        andi.w  #15,d1
        tst.w   d2
        bne.s   .s1
        move.w  d1,d0                   ; x = r, y = 0
        moveq   #0,d2
        bra.s   .set
.s1:    cmpi.w  #1,d2
        bne.s   .s2
        moveq   #16,d0                  ; x = 16, y = r
        move.w  d1,d2
        bra.s   .set
.s2:    cmpi.w  #2,d2
        bne.s   .s3
        moveq   #16,d0                  ; x = 16 - r, y = 16
        sub.w   d1,d0
        moveq   #16,d2
        bra.s   .set
.s3:    moveq   #0,d0                   ; x = 0, y = 16 - r
        moveq   #16,d2
        sub.w   d1,d2
.set:   add.w   BX.l,d0
        add.w   BY.l,d2
        move.w  d0,$37eb8.l
        move.w  d2,$249ec.l
.out:   movem.l (a7)+,d0-d2/a0
        move.w  $3b260.l,d0             ; the displaced instruction
        jmp     $0b6e8.l
postab: dc.w    160,100
        dc.w    20,20
        dc.w    300,30
        dc.w    319,199
        dc.w    8,190
        dc.w    150,189
        dc.w    96,170
        dc.w    310,100
        dc.w    1,100
        dc.w    200,60
        dc.w    305,185
        dc.w    304,184
        dc.w    15,195
        dc.w    250,199
        dc.w    64,128
        dc.w    270,150
