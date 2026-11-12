; name: pop2_tick
; default: no
; site: $22f14
; orig: 3039000393fa d079000393fc
; data: PB+$2800 6144
; note: Fixed-rate world tick, part 1 of 8 (the set: pop2_tick pop2_tick_render pop2_tick_logic pop2_tick_flip pop2_tick_dot_a pop2_tick_dot_b pop2_tick_snd; work/notes/timing.md).
; note: User's choice: ONE WORLD TURN per 1/6.25 s of real time on every machine and at 50 and 60 Hz (8 VBL at 50 Hz, 9.6 at 60 Hz).  The game is frame-coupled: one pass of
; note: the play loop ($1252a-$13340) = one turn ($3979a, $22f9c) = one flip, as fast as the CPU goes (8.9 turns/s at the start of a battle, 6.0 when busy, 8 MHz STE).
; note: This patch replaces the pass-top function $22f14 (pacing + turn counter; one caller, `jsr $22f14` at $1254e).  Time base: the game's own VBL counter $392d8
; note: (long, +1 per VBL in the handler $18fa) in units of 1/300 s: 6 per VBL at 50 Hz, 5 at 60 Hz (shifter sync mode, `btst #1,$ffff820a.w`: set = 50 Hz, read at every
; note: look so a runtime switch is followed).  TK = 48 units = 0.16 s = 6.25 turns/s.  The timer C 200 Hz tick is NOT usable: the game points $114 at an rte ($1d60) and
; note: leaves timer C masked (IERB = $40 in play), $4ba does not move (measured: 0 in 3 s).  ACC = real time not yet simulated (units, clamp 3 TK).
; note: Every pass is one of four kinds, set by the look at the top (flags SKIP, RON in the data block, read by the other hooks):
; note:   T  ACC >= TK: a world turn, the ORIGINAL pass (render, logic, flip, keys).  Falls into the game's own code at $22f2e (turn++, the 3-turn palette fade, the
; note:      view clamp).
; note:   S  as T, and another turn is still owed after it: catch-up.  The pass runs the turn and the logic but not the render, the UI or the flip (pop2_tick_render,
; note:      pop2_tick_flip): no VBL wait is needed either (the flip clears the VBL flag, so without a flip the next pass starts at once).
; note:   R  ACC < TK: ahead of real time.  Render + UI + flip but NO world: no turn++, none of the logic calls ($2309a $25652 $26644 $27faa $1fcce $29c7e $2a0b2), no
; note:      command execution ($29226), none of the copies at $22fa8.  The minimap dots that the logic plots are replayed (pop2_tick_dot_a/b record them).
; note:   P  the game is paused ($39796): the original pass, throttle-free, ACC cleared.
; note: Catch-up is bounded (ACC clamp 3 TK: at most four turns in a row without a frame); a gap of more than 40 VBL (a load, a requester, the first look) resyncs to one turn.
; note: The click latches ($39402, $39404; stamp $3940a = the turn at the click, cleared at $22f84 once the turn has moved on) are aged HERE, by passes that run the UI (T and R),
; note: not by turns: with R passes (no turn++) the original test would keep an unhandled click for two whole turns, and with S passes (turns without UI) it would lose
; note: a click that no pass has seen.  The stamp is read and re-armed with a sentinel ($7fffffff: `cmp.l $3940a,d0 / ble` at $22f84 then never clears) every look; a
; note: stamp that changed since the last look = a fresh click (the VBL writes it only when it latches one): survives this pass, an unchanged stamp with a latch still
; note: set = seen by a whole pass: cleared.  Same lifetime as the original at any pass rate (a click made after the top of pass k is seen by passes k and k+1).
; note: The pointer-at-(0,0) hold of the original (`cmpi.l #8,$392d4` / `ble.b $22f14`: no pass shorter than 9 VBL while the pointer sits in the top-left corner)
; note: is kept but in real time (HOLD = 54 units = 0.18 s: 9 VBL at 50 Hz, 11 at 60 Hz) and never delays an S pass, so the world still gets its 6.25 turns/s.
; note: Data block D = PB+$2800 = $82800 (inside the zero-filled payload image, 6 KB; the control block is also armed lazily behind the magic 'P2TK' for the live images of the gates): +0 MAGIC.l +4 LAST.l +8 HREF.l +12 ACC.w +14 SKIP.w +16 RON.w
; note: +18 FRESH.w +20 SACC.w (pop2_tick_snd) +24 SLAST.l +28 TICKS.l +32 RPASS.l +36 SPASS.l +40 PPASS.l +44 TPASS.l +48 WPTR.l (minimap dot list write pointer);
; note: the dot list is at D+$100 (900 entries of 6 bytes, pop2_tick_dot_a).
TK      equ     48
HOLD    equ     54
MAGIC   equ     $5032544b               ; 'P2TK'
D       equ     PB+$2800
oMAGIC  equ     0
oLAST   equ     4
oHREF   equ     8
oACC    equ     12
oSKIP   equ     14
oRON    equ     16
oFRESH  equ     18
oTICKS  equ     28
oRPASS  equ     32
oSPASS  equ     36
oPPASS  equ     40
oTPASS  equ     44
oWPTR   equ     48
oDOTS   equ     $100
VBLCNT  equ     $392d8
STAMP   equ     $3940a
SENT    equ     $7fffffff
TICK    equ     PB+$2000
        org     $22f14
        jmp     TICK.l

        org     PB+$2000
tick:   movem.l d0-d4/a0-a1,-(a7)
        lea     D.l,a0
        cmpi.l  #MAGIC,oMAGIC(a0)
        beq.s   .ready
        movea.l a0,a1                   ; first call: zero the control block, arm the dot list
        moveq   #63,d0
.zero:  clr.l   (a1)+
        dbra    d0,.zero
        move.l  #MAGIC,oMAGIC(a0)
        lea     oDOTS(a0),a1
        move.l  a1,oWPTR(a0)
.ready:
.again: moveq   #6,d4                   ; units per VBL: 6 at 50 Hz (sync bit 1 set), 5 at 60 Hz
        btst    #1,$ffff820a.w
        bne.s   .u
        moveq   #5,d4
.u:     move.l  VBLCNT.l,d1             ; now, in VBL
        move.l  d1,d0
        sub.l   oLAST(a0),d0            ; VBL since the previous look
        tst.w   $39796.l
        bne.s   .paused
        moveq   #0,d2
        cmpi.l  #40,d0
        bhi.s   .resync
        mulu.w  d4,d0                   ; real time since the previous look, 1/300 s
        move.w  oACC(a0),d2
        add.w   d0,d2
        bra.s   .decide
.resync: moveq   #TK,d2                 ; first look / back from a load or a requester: one turn, no burst
.decide: moveq   #2,d3                  ; kind R: ahead of real time
        cmpi.w  #TK,d2
        blt.s   .kind
        subi.w  #TK,d2                  ; a turn is due
        cmpi.w  #3*TK,d2
        ble.s   .noclamp
        move.w  #3*TK,d2                ; bound the catch-up
.noclamp:
        moveq   #0,d3                   ; kind T
        cmpi.w  #TK,d2
        blt.s   .kind
        moveq   #1,d3                   ; kind S: another turn is owed, this pass draws nothing
        bra.s   .kind
.paused: moveq  #0,d2                   ; kind P: the game's own pass, clock parked
        moveq   #3,d3
.kind:  cmpi.w  #1,d3
        beq.s   .commit                 ; S: never held
        move.w  $393fa.l,d0             ; the original hold: pointer at (0,0) -> no pass shorter than 9 VBL
        add.w   $393fc.l,d0
        bne.s   .commit
        move.l  d1,d0
        sub.l   oHREF(a0),d0            ; VBL since the previous (non-S) pass
        cmpi.l  #20,d0
        bhi.s   .commit
        mulu.w  d4,d0
        cmpi.w  #HOLD,d0
        blo.w   .again                  ; spin like the original (the VBL keeps counting)
.commit: move.l d1,oLAST(a0)
        move.w  d2,oACC(a0)
        cmpi.w  #1,d3
        beq.s   .nohref
        move.l  d1,oHREF(a0)
.nohref: clr.w  oSKIP(a0)
        clr.w   oRON(a0)
        cmpi.w  #3,d3
        beq.s   .out                    ; P: the original from $22f2e
        cmpi.w  #1,d3
        beq.s   .skip
        cmpi.w  #2,d3
        beq.s   .rpass
        ; ---- T
        addq.l  #1,oTICKS(a0)
        addq.l  #1,oTPASS(a0)
        lea     oDOTS(a0),a1            ; the logic of this pass records the minimap dots anew
        move.l  a1,oWPTR(a0)
        bsr.w   .age
        bra.s   .out
.skip:  ; ---- S
        move.w  #1,oSKIP(a0)
        addq.l  #1,oTICKS(a0)
        addq.l  #1,oSPASS(a0)
        move.w  sr,-(a7)                ; keep a fresh click's mark, but hide the stamp from the original test at $22f84
        ori.w   #$700,sr
        move.l  STAMP.l,d0
        move.l  #SENT,STAMP.l
        move.w  (a7)+,sr
        cmpi.l  #SENT,d0
        beq.s   .out
        move.w  #1,oFRESH(a0)
        bra.s   .out
.rpass: ; ---- R
        move.w  #1,oRON(a0)
        addq.l  #1,oRPASS(a0)
        bsr.w   .age
        clr.l   $392d4.l                ; the original's `clr.l $392d4` ($22f2e)
        movem.l (a7)+,d0-d4/a0-a1
        jmp     $22fc8.l                ; the view clamp, then back to $1254e (it ends with rts)
.out:   movem.l (a7)+,d0-d4/a0-a1
        jmp     $22f2e.l                ; the original from `clr.l $392d4`: fade, pause test, turn++, copies, clamp
        ; the click latch aging, once per pass that runs the UI (T, R)
.age:   move.w  sr,-(a7)
        ori.w   #$700,sr
        move.l  STAMP.l,d0
        move.l  #SENT,STAMP.l
        move.w  (a7)+,sr
        cmpi.l  #SENT,d0
        bne.s   .fresh
        tst.w   oFRESH(a0)
        bne.s   .fresh
        clr.w   $39402.l
        clr.w   $39404.l
        rts
.fresh: clr.w   oFRESH(a0)
        rts
