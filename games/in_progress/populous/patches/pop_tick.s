; name: pop_tick
; default: yes
; site: $0b632
; orig: 3039 0003b03c
; data: $c6000 3680
; note: Fixed-rate world tick, part 1 of 6 (the set: pop_tick pop_tick_render pop_tick_logic pop_tick_flip pop_tick_cmd pop_tick_dot; work/notes/timing.md).
;       User's choice: the world runs FIVE TURNS PER REAL SECOND on every machine and at 50 and 60 Hz (10 VBL at 50 Hz, 12 at 60 Hz).  The game is frame coupled:
;       one pass of the play loop ($b632-$bc06, called once from $b54e) is one turn ($3c506, `addq.w #1,$3c506` at $db96 inside the world $db8a), one flip ($16f16)
;       and one full redraw, as fast as the CPU goes (3.2 turns/s on a busy 8 MHz STE, 8-17 on an empty world, 25 on a TT, 42 on a Falcon).
;       This hook sits at the pass top (`move.w $3b03c.l,d0`, 6 bytes, displaced and executed at the end).  Time base: the game's own VBL counter $16d2a (long, `addq.l #1`
;       at the end of the VBL routine $16d70) in units of 1/300 s: 6 per VBL at 50 Hz, 5 at 60 Hz (shifter sync mode `btst #1,$ffff820a.w`: set = 50 Hz, read at every look).
;       Timer C is not used by the game for this (TOS $4ba/$462 are untouched by it and the VBL vector is PP's $d018e).  TK = 60 units = 0.2 s = 5 turns/s exactly.
;       ACC = real time not yet simulated (units, clamp 3 TK).  Every pass is one of four kinds (flags SKIP, RON, REC in the data block, read by the other hooks):
;         T  ACC >= TK: a world turn: the ORIGINAL pass (render, world, flip, keys, UI, commands).
;         S  as T, and another turn is still owed afterwards (catch-up on a machine too slow for the scene): water phase + the per-pass derivations of the pass top, the world
;            ($12fc2, $db8a), the shield countdown block ($b8ec), $d4c0, then the command executor $1e750 - no render, no flip, no keys, no UI (pop_tick_render, pop_tick_flip).
;         R  ACC < TK: ahead of real time.  Render + minimap dots (replayed) + $d4c0 + flip + keys + UI, but NO world: no water toggle, no $12fc2 / $db8a, no turn++, no
;            shield countdown, no $1000-turn event, no command execution (pop_tick_logic, pop_tick_cmd).  The pointer is drawn by the VBL routine, so it never waits.
;         P  paused ($3b2b2), paint mode ($3b2b4) or a link game ($3c524 <> 0): the original pass, the clock parked (the original keeps unpausing / link lock-step working).
;       Catch-up is bounded (ACC clamp 3 TK: at most four turns in a row without a frame); a gap of more than 40 VBL since the previous look (first look, a dialog, a load)
;       resyncs to one turn.  Everything per pass that the original counted is listed in work/notes/timing.md section 3.  Click latches ($3d566, $3c514) age at the end of
;       every UI pass in the original and still do (T and R passes; S passes run no UI, so a click waits for the next UI pass).
;       Data block D = $c6000: +0 MAGIC.l +4 LAST.l +12 ACC.w +14 SKIP.w +16 RON.w +18 REC.w +28 TICKS.l +32 RPASS.l +36 SPASS.l +40 PPASS.l +44 TPASS.l +48 WPTR.l
;       (write pointer of the minimap dot list, pop_tick_dot); the dot list is at D+$100 (560 entries of 6 bytes).  The block arms itself on the first look (magic 'PTIK').
TK      equ     60
MAGIC   equ     $5054494b
D       equ     $c6000
oMAGIC  equ     0
oLAST   equ     4
oACC    equ     12
oSKIP   equ     14
oRON    equ     16
oREC    equ     18
oTICKS  equ     28
oRPASS  equ     32
oSPASS  equ     36
oPPASS  equ     40
oTPASS  equ     44
oWPTR   equ     48
oDOTS   equ     $100
        org     $0b632
        jmp     $c5000.l

        org     $c5000
tick:   movem.l d0-d4/a0-a1,-(a7)
        lea     D.l,a0
        cmpi.l  #MAGIC,oMAGIC(a0)
        beq.s   .ready
        movea.l a0,a1                   ; first look: zero the control block, arm the dot list
        move.w  #63,d0
.zero:  clr.l   (a1)+
        dbra    d0,.zero
        move.l  #MAGIC,oMAGIC(a0)
        lea     oDOTS(a0),a1
        move.l  a1,oWPTR(a0)
.ready: moveq   #6,d4                   ; units per VBL: 6 at 50 Hz (sync bit 1 set), 5 at 60 Hz
        btst    #1,$ffff820a.w
        bne.s   .u
        moveq   #5,d4
.u:     move.l  $16d2a.l,d1             ; now, in VBL
        move.l  d1,d0
        sub.l   oLAST(a0),d0            ; VBL since the previous look
        tst.w   $3b2b2.l                ; paused
        bne.s   .paused
        tst.w   $3b2b4.l                ; paint mode (the game's debug mode: the world does not run)
        bne.s   .paused
        tst.w   $3c524.l                ; link game: the command exchange ($1ff14 / $1fe4c) is the lock-step, leave it alone
        bne.s   .paused
        moveq   #0,d2
        cmpi.l  #40,d0
        bhi.s   .resync
        mulu.w  d4,d0                   ; real time since the previous look, 1/300 s
        move.w  oACC(a0),d2
        add.w   d0,d2
        bra.s   .decide
.resync: moveq  #TK,d2                  ; first look / back from a dialog or a load: one turn, no burst
.decide: moveq  #2,d3                   ; kind R: ahead of real time
        cmpi.w  #TK,d2
        blt.s   .commit
        subi.w  #TK,d2                  ; a turn is due
        cmpi.w  #3*TK,d2
        ble.s   .noclamp
        move.w  #3*TK,d2                ; bound the catch-up
.noclamp: moveq #0,d3                   ; kind T
        cmpi.w  #TK,d2
        blt.s   .commit
        moveq   #1,d3                   ; kind S: another turn is owed, this pass draws nothing
        bra.s   .commit
.paused: moveq  #0,d2                   ; kind P: the game's own pass, clock parked
        moveq   #3,d3
.commit: move.l d1,oLAST(a0)
        move.w  d2,oACC(a0)
        clr.w   oSKIP(a0)
        clr.w   oRON(a0)
        clr.w   oREC(a0)
        tst.w   d3
        beq.s   .t
        cmpi.w  #1,d3
        beq.s   .s
        cmpi.w  #2,d3
        beq.s   .r
        addq.l  #1,oPPASS(a0)           ; P
        bra.s   .out
.t:     addq.l  #1,oTICKS(a0)
        addq.l  #1,oTPASS(a0)
        move.w  #1,oREC(a0)             ; the world of this pass records the minimap dots anew
        lea     oDOTS(a0),a1
        move.l  a1,oWPTR(a0)
        bra.s   .out
.s:     move.w  #1,oSKIP(a0)
        addq.l  #1,oTICKS(a0)
        addq.l  #1,oSPASS(a0)
        bra.s   .out
.r:     move.w  #1,oRON(a0)
        addq.l  #1,oRPASS(a0)
        movem.l (a7)+,d0-d4/a0-a1
        jmp     $0b6f4.l                ; straight to the render stage: no water toggle, no pass-top derivations
.out:   movem.l (a7)+,d0-d4/a0-a1
        move.w  $3b03c.l,d0             ; the displaced instruction
        jmp     $0b638.l
