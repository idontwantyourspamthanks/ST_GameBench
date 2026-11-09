; name: tick_head
; default: no
; site: $14e00
; orig: 610000fa6100e096
; data: $b3700 64
; note: P3 fixed logic tick, OPTION A (work/notes/timing.md). Replaces the head of the in-game
;       frame loop sub_014e00 (`bsr.w $14efc` key poll + `bsr.w $12e9c` simulation step) with a
;       scheduler that makes the simulation advance at a fixed real-time rate of one step per
;       GRP = 10 VBL (5 steps/s) whatever the frame rate.
;       Real time = the game's own free-running VBL counter $637e (word, +1 per VBL in the
;       action mode, `$61ac addq.w #1,$637e`; frameloop.md/simtiming.md section 5); no VBL patch.
;         ACC (D+2) = real time not yet simulated, in VBLs (word).
;         Ahead (ACC < GRP after adding the VBLs since the last look): spin on $637e. This is
;           the frame limiter for fast machines.
;         Behind by at least another whole step after this one: SKIP (D+6) = 1. The pass then
;           runs the simulation and the logic calls of the loop body ($14fac HUD feed + game
;           clock, $c4f2 + $ca7e = the map units, which live at the tail of the HUD redraw
;           $129d2 (timing.md section 4), $202c6 $200e8 $1ffe0 $1fa0a spawn tests, $20d52
;           object update) but NOT the render calls and NOT the flip, and returns straight to the loop top, which tests
;           the exit flags ($14dfc, $12d76, $14dfe, $14ef6) after every step. The six render
;           calls ($129d2 $1580e $1d0a0 $18304 $19ce2 $1bbe6) and the flip are skipped
;           together (frameloop.md section 5: otherwise the draw buffer keeps the picture of
;           three flips ago). The key word $12afc is rewritten by every $14efc poll.
;         Catch-up is clamped to 3 steps; a gap of more than 4 steps (or a counter that went
;           backwards because menu code cleared $637e) resyncs: one pass, no burst.
;       Data block D = $B3700 (zero at boot), same layout as p3b_head:
;         D+0 LAST.w  D+2 ACC.w  D+4 PH.w  D+6 SKIP.w ...
GRP     equ     10
D       equ     $b3700
oLAST   equ     0
oACC    equ     2
oSKIP   equ     6
        org     $14e00
        jsr     $b3100.l
        nop

        org     $b3100
tick:   movem.l d0-d2/a0,-(a7)
        lea     D.l,a0
        moveq   #GRP,d2                 ; d2 = VBLs this pass consumes
.wait:  move.w  $637e.l,d0
        move.w  d0,d1
        sub.w   oLAST(a0),d1            ; VBLs since the previous look (mod 65536)
        move.w  d0,oLAST(a0)
        cmpi.w  #4*GRP,d1
        bls.s   .acc
        moveq   #0,d1                   ; first entry, back from another screen, or $637e
        move.b  d2,d1                   ; cleared/wrapped: resync, one pass, no burst
        clr.w   oACC(a0)
.acc:   add.w   d1,oACC(a0)
        cmp.w   oACC(a0),d2
        bgt.s   .wait                   ; ahead of real time: wait for VBLs
        sub.w   d2,oACC(a0)             ; this pass simulates one step
        moveq   #3*GRP,d0
        cmp.w   oACC(a0),d0
        bge.s   .noclamp
        move.w  d0,oACC(a0)             ; bound the catch-up
.noclamp:
        clr.w   oSKIP(a0)
        cmp.w   oACC(a0),d2
        bgt.s   .ontime
        addq.w  #1,oSKIP(a0)            ; another step owed: no render this pass
.ontime:
        movem.l (a7)+,d0-d2/a0
        jsr     $14efc.l                ; displaced: key poll
        jsr     $12e9c.l                ; displaced: simulation step
        tst.w   D+oSKIP.l
        bne.s   wskip
        rts                             ; -> $14e06 nop -> original loop body
wskip:  tst.w   $14dfc.l                ; exit flag set by the step: the loop body would rts
        bne.s   .out
        jsr     $14fac.l                ; HUD feed + game clock
        cmpi.w  #1,$12d58.l             ; $129d2 (HUD redraw) also runs the map units: $c4f2 walkers, $ca7e
        beq.s   .nounit                 ; (sub_0129d2 ends with them; it rts at once when $12d58 = 1)
        jsr     $c4f2.l
        jsr     $ca7e.l
.nounit:
        jsr     $202c6.l                ; spawn tests, object update (the loop body's logic calls)
        jsr     $200e8.l
        jsr     $1ffe0.l
        jsr     $1fa0a.l
        jsr     $20d52.l
        move.w  $14ee4.l,d0             ; message timer ($14e98 counts it down once per pass)
        bmi.s   .out
        subq.w  #1,$14ee4.l
.out:   addq.l  #4,a7                   ; drop the return into $14e06: leave sub_014e00
        rts
