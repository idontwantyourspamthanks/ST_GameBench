; name: p3b_head
; default: yes
; site: $14e00
; orig: 610000fa6100e096
; data: $b3700 64
; note: P3 partial B (work/notes/timing.md); replaces tick_head (option A). Needs p3b_hook, p3b_hud,
;       p3b_logic, p3b_msg, p3b_units. Head of the in-game frame loop sub_014e00. Real time = the game's VBL
;       counter $637e times the length of a VBL in 1/300 s units, read from the shifter sync mode at every look
;       ($ff820a bit 1: 1 = 50 Hz = 6 units, 0 = 60 Hz = 5 units), as tick_head (timing.md section 10). The 5 Hz game
;       step ("tick", GRP = 60 units = 0.2 s) is unchanged
;       (A); what is new is that the VIEW advances in 5 sub-steps of SUBT = 12 units = 0.04 s (25 Hz) per tick:
;       a GROUP of 5 passes of the loop, each pass 12 units, PH = 1..5.
;         PH 1  key poll $14efc, then the mode step $12d5e (= $131ae, ski/walk state machine) with
;               SPLIT = 1. The state machine runs to its common exit $13236, where p3b_hook takes
;               over: turn ($12fe2, once per tick, fresh input), group end heading HG = H0 + E,
;               the tick's position step (DX,DZ) from the speed $15112 the state machine just set,
;               then view sub-step 1/5.
;         PH 2-4 view sub-step k/5 only (substep).
;         PH 5  the rest of the A tick: heading = HG, position = (X0,Z0), then the chain
;               $13244..$1327c as the original ($14530 adds the full step DX,DZ, terrain $13078,
;               window recentre $152c0, cells, exits, energy), then the stamina $12f9e. Group end
;               state == A's state after the same tick.
;       View sub-step k (substep): heading = H0 + trunc(k*E/5), position = (X0,Z0) + trunc(k*(DX,DZ)/5),
;       then the pure geometry of the chain: $13078 (terrain tilt; its two state words $130d6/$130d8
;       are saved and restored, they are the previous tick's height), $144ca, $158f4, $159a4, $14684,
;       $14716. Nothing else of the world moves in a sub-step.
;       The body of the loop runs on a sub-step pass with NOLOGIC = 1: p3b_hud/logic/msg then run
;       the HUD feed WITHOUT the game clock, skip the spawn tests and the object update, and keep
;       the message timer; the render calls and the flip are the original ones.
;       A pass is a full A pass (poll + $12e9c + the whole loop body, PH = 0) when: the caller is
;       not the loop ($14a86 first frame, $d1de), the mode step is not $131ae (snipe, buggy,
;       glider), the window flag $14efa is 0 (first pass after a (re)build, recentre pending), or a
;       fall is in progress ($13c5a). A group in progress is dropped when $12d5e changes.
;       Scheduling is as tick_head, in units of the pass length (SUBT or GRP): ahead -> spin on
;       $637e; another pass owed -> SKIP = 1 (no render, no flip: after the sim of a sub pass the
;       head returns to the loop top; after a world pass it runs the logic calls of the body, see
;       wskip); catch-up clamped to 3*GRP units; gap > 4*GRP units resyncs (one pass, no burst).
;       Data block D = $B3700 (zero at boot):
;         D+0 LAST.w  D+2 ACC.w  D+4 PH.w  D+6 SKIP.w  D+8 SPLIT.w  D+10 H0.w  D+12 E.w
;         D+14 HG.w  D+16 X0.l  D+20 Z0.l  D+24 DX.w  D+26 DZ.w  D+28 MODE.l  D+32 NOLOGIC.w
GRP     equ     60                      ; 1/300 s units: 0.2 s
SUBT    equ     12                      ; 0.04 s
D       equ     $b3700
oLAST   equ     0
oACC    equ     2
oPH     equ     4
oSKIP   equ     6
oSPLIT  equ     8
oH0     equ     10
oE      equ     12
oHG     equ     14
oX0     equ     16
oZ0     equ     20
oDX     equ     24
oDZ     equ     26
oMODE   equ     28
oNOLOG  equ     32
        org     $14e00
        jsr     $b3100.l
        nop

        org     $b3100
tick:   movem.l d0-d2/a0,-(a7)
        lea     D.l,a0
        clr.w   oNOLOG(a0)
        moveq   #GRP,d2                 ; d2 = 1/300 s units this pass consumes (A pass)
        cmpi.l  #$14ac4,20(a7)          ; caller = the loop ($14ac0 bsr.w)?
        bne.s   .forceA
        move.w  oPH(a0),d0
        beq.s   .new
        cmpi.w  #5,d0
        bhs.s   .new
        move.l  $12d5e.l,d1             ; group in progress: still the same mode step?
        cmp.l   oMODE(a0),d1
        beq.s   .sub
        clr.w   oPH(a0)                 ; mode changed: drop the group
.new:   move.l  $12d5e.l,d1             ; start of a tick: is a view-split group possible?
        cmpi.l  #$131ae,d1
        bne.s   .wait
        tst.w   $14efa.l
        beq.s   .wait
        tst.w   $13c5a.l
        bne.s   .wait
        move.l  d1,oMODE(a0)
.sub:   moveq   #SUBT,d2
        bra.s   .wait
.forceA:
        clr.w   oPH(a0)
.wait:  move.w  $637e.l,d0
        move.w  d0,d1
        sub.w   oLAST(a0),d1            ; VBLs since the previous look (mod 65536)
        move.w  d0,oLAST(a0)
        moveq   #5,d0                   ; 60 Hz: 5 units per VBL
        btst    #1,$ffff820a.w          ; shifter sync mode: bit 1 set = 50 Hz
        beq.s   .rate
        moveq   #6,d0                   ; 50 Hz: 6 units per VBL
.rate:  mulu.w  d0,d1                   ; d1.l = real time since the previous look, 1/300 s
        cmpi.l  #4*GRP,d1
        bls.s   .acc
        moveq   #0,d1                   ; first entry / back from another screen / $637e cleared:
        move.b  d2,d1                   ; resync, one pass, no catch-up burst
        clr.w   oACC(a0)
.acc:   add.w   d1,oACC(a0)
        cmp.w   oACC(a0),d2
        bgt.s   .wait                   ; ahead of real time: wait for VBLs
        sub.w   d2,oACC(a0)             ; this pass consumes one unit
        move.w  #3*GRP,d0
        cmp.w   oACC(a0),d0
        bge.s   .noclamp
        move.w  d0,oACC(a0)             ; bound the catch-up
.noclamp:
        clr.w   oSKIP(a0)
        cmp.w   oACC(a0),d2
        bgt.s   .ontime
        addq.w  #1,oSKIP(a0)            ; another pass owed: no render now
.ontime:
        cmpi.w  #SUBT,d2
        bne.w   .passA
        move.w  oPH(a0),d0
        addq.w  #1,d0                   ; next phase of the group (0 or 5 -> 1)
        cmpi.w  #5,d0
        bls.s   .ph
        moveq   #1,d0
.ph:    move.w  d0,oPH(a0)
        movem.l (a7)+,d0-d2/a0
        cmpi.w  #1,D+oPH.l
        beq.s   .p1
        cmpi.w  #5,D+oPH.l
        beq.s   .p5
        jsr     $b3300.l                ; substep: PH 2..4: view sub-step only
        tst.w   D+oSKIP.l
        bne.w   pout
        move.w  #1,D+oNOLOG.l           ; on time: the loop body renders, logic calls inert
        rts
.p1:    jsr     $14efc.l                ; key poll
        move.w  #1,D+oSPLIT.l
        movea.l $12d5e.l,a0
        jsr     (a0)                    ; state machine; p3b_hook ends it (turn, step, sub-step 1)
        clr.w   D+oSPLIT.l
        tst.w   D+oSKIP.l
        bne.w   pout
        move.w  #1,D+oNOLOG.l
        rts
.p5:    move.w  D+oHG.l,d0
        move.w  d0,$12c98.l             ; the tick's final heading
        move.w  d0,$15114.l
        move.l  D+oX0.l,$12c60.l        ; $14530 adds the full tick step to the tick's start
        move.l  D+oZ0.l,$12c64.l
        jsr     $13244.l                ; the original chain after the turn
        jsr     $12f9e.l                ; stamina, as $12e9c
        bra.s   .world
.passA: clr.w   oPH(a0)
        movem.l (a7)+,d0-d2/a0
        jsr     $14efc.l                ; displaced: key poll
        jsr     $12e9c.l                ; displaced: simulation step
.world: tst.w   D+oSKIP.l
        bne.s   wskip
        rts                             ; -> $14e06 nop -> original loop body
wskip:  tst.w   $14dfc.l                ; exit flag: the loop body would rts here
        bne.w   pout
        jsr     $14fac.l                ; HUD feed + game clock
        cmpi.w  #1,$12d58.l             ; $129d2 (HUD redraw) also runs the map units: $c4f2 walkers, $ca7e
        beq.s   .nounit                 ; (sub_0129d2 ends with them; it rts at once when $12d58 = 1)
        jsr     $c4f2.l
        jsr     $ca7e.l
.nounit:
        jsr     $202c6.l
        jsr     $200e8.l
        jsr     $1ffe0.l
        jsr     $1fa0a.l
        jsr     $20d52.l
        move.w  $14ee4.l,d0             ; message timer ($14e98 counts it down once per tick)
        bmi.w   pout
        subq.w  #1,$14ee4.l
pout:   addq.l  #4,a7                   ; drop the return into $14e06: leave sub_014e00
        rts

; view sub-step k = D+4 (1..4), see the header (p3b_hook jumps to $B3300)
        org     $b3300
substep:
        lea     D.l,a0
        move.w  oPH(a0),d1
        move.w  oE(a0),d2
        muls.w  d1,d2
        divs.w  #5,d2
        add.w   oH0(a0),d2
        move.w  d2,$12c98.l
        move.w  d2,$15114.l
        move.w  oDX(a0),d2
        muls.w  d1,d2
        divs.w  #5,d2
        ext.l   d2
        add.l   oX0(a0),d2
        move.l  d2,$12c60.l
        move.w  oDZ(a0),d2
        muls.w  d1,d2
        divs.w  #5,d2
        ext.l   d2
        add.l   oZ0(a0),d2
        move.l  d2,$12c64.l
        move.w  $130d6.l,-(a7)          ; previous tick's height/tilt state: $13078 rewrites it
        move.w  $130d8.l,-(a7)
        jsr     $13078.l
        move.w  (a7)+,$130d8.l
        move.w  (a7)+,$130d6.l
        jsr     $144ca.l
        jsr     $158f4.l
        jsr     $159a4.l
        jsr     $14684.l
        jsr     $14716.l
        rts
