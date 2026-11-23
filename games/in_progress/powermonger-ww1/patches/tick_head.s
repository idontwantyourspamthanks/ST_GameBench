; name: tick_head
; default: yes
; site: $13da0
; orig: 4a790005a856
; data: $72a80 64
; note: fixed-rate world tick, port of master's tick_head (games/done/powermonger/patches/tick_head.s, work/notes/timing.md).  Head of the world logic of the
;       main-loop pass: WW1 `$13da0 tst.w $5a856.l ; bne.b $13dcc ; addq.l #1,$2ed90.l ; addq.l #1,$50fd8.l ; jsr $1359a ; jsr $576a ; jsr $d712 ;
;       jsr $3276` (master $13020: lea $14e20,a2 ; tst.w $57ff2 ; bne ; addq.l #1,$2df70 ; addq.l #1,$4bb3e ; ... $127e6 $6522 $d322 $3e06).  The site is the
;       displaced `tst.w $5a856.l` (pause flag): the hook returns its flags, so the `bne.b $13dcc` that follows is the original one, and a render-only
;       pass returns NZ to take that branch (it skips exactly the world logic: the two counters and the four logic calls).
;       Real time = the game's VBL counter $71b7c (long, +1 per VBL in the VBL handler $774; the low word $71b7e is used, deltas mod 65536) times the length
;       of a VBL in 1/300 s units, read from the shifter sync mode at every look ($ff820a bit 1: 1 = 50 Hz = 6 units, 0 = 60 Hz = 5 units), so the world
;       runs at the same real-time rate on 50 and 60 Hz displays.  One TICK = TK = 75 units = 0.25 s = 4.00 world steps/s (12.5 VBL at 50 Hz, 15 VBL at 60 Hz).
;       ACC (D+2) = real time not yet simulated, in 1/300 s units.
;       Three kinds of pass (flags SKIP D+4, RON D+6, read by tick_pass / tick_wx / tick_men):
;         T  ACC >= TK: a world tick.  The pass is the ORIGINAL pass.
;         S  as T but another tick is owed after it (ACC still >= TK): tick_pass skips the render path (window copy, landscape, flip), exactly the game's own
;            `$5a854` skip.
;         R  ACC < TK: render-only pass.  The world clock $2ed90 (also stored as an event timestamp by the logic and compared by it), $50fd8 and the logic do
;            not run; tick_wx / tick_men skip the weather and men updates.  View limits, render, HUD, UI / click dispatch, camera keys and the flip run.
;       Catch-up is clamped to 3 ticks; a gap of more than 4 ticks (1 s: disk load, menus) resyncs (one tick, no burst).  While $5a856 (pause) is set the pass is
;       the original and the clock is kept.
;       Data D = $72a80 (zero): +0 LAST.w +2 ACC.w +4 SKIP.w +6 RON.w +8 TICKS.l +12 RPASS.l +16 SPASS.l +32 PASS.l
TK      equ     75
D       equ     $72a80
oLAST   equ     0
oACC    equ     2
oSKIP   equ     4
oRON    equ     6
oTICKS  equ     8
oRPASS  equ     12
oSPASS  equ     16
oPASS   equ     32
        org     $13da0
        jsr     $72900.l

        org     $72900
head:   movem.l d0-d2/a0,-(a7)
        lea     D.l,a0
        tst.w   $5a856.l
        bne.s   .pause
        addq.l  #1,oPASS(a0)            ; pass counter (click lifetime, tick_click)
        move.w  $71b7e.l,d0
        move.w  d0,d1
        sub.w   oLAST(a0),d1            ; VBLs since the previous pass (mod 65536)
        move.w  d0,oLAST(a0)
        moveq   #5,d2                   ; 60 Hz: 5 units per VBL
        btst    #1,$ffff820a.w          ; shifter sync mode: bit 1 set = 50 Hz
        beq.s   .rate
        moveq   #6,d2                   ; 50 Hz: 6 units per VBL
.rate:  mulu.w  d2,d1                   ; d1.l = real time since the previous pass, 1/300 s
        cmpi.l  #4*TK,d1
        bls.s   .acc
        move.w  #TK,oACC(a0)            ; first entry / back from a menu or disk load: resync, one tick
        bra.s   .tick
.acc:   add.w   d1,oACC(a0)
        cmpi.w  #TK,oACC(a0)
        blt.s   .ronly
.tick:  subi.w  #TK,oACC(a0)
        cmpi.w  #3*TK,oACC(a0)
        ble.s   .noclamp
        move.w  #3*TK,oACC(a0)          ; bound the catch-up
.noclamp:
        clr.w   oRON(a0)
        clr.w   oSKIP(a0)
        addq.l  #1,oTICKS(a0)
        cmpi.w  #TK,oACC(a0)
        blt.s   .out
        move.w  #1,oSKIP(a0)            ; another tick is owed: no render this pass
        addq.l  #1,oSPASS(a0)
.out:   movem.l (a7)+,d0-d2/a0
        tst.w   $5a856.l                ; the displaced instruction: Z = run the world logic
        rts
.pause: clr.w   oSKIP(a0)
        clr.w   oRON(a0)
        clr.w   oACC(a0)
        move.w  $71b7e.l,oLAST(a0)
        bra.s   .out
.ronly: move.w  #1,oRON(a0)
        clr.w   oSKIP(a0)
        addq.l  #1,oRPASS(a0)
        moveq   #1,d0                   ; NZ: the game's `bne.b $13dcc` skips the world logic (movem does not touch the flags)
        movem.l (a7)+,d0-d2/a0
        rts
