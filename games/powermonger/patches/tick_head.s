; name: tick_head
; default: no
; site: $13020
; orig: 45f900014e20
; data: $b8a00 64
; note: P2 fixed-rate world tick (work/notes/timing.md). Head of the world logic of the main loop pass
;       (sub_012fd8, `lea.l $14e20.l,a2` at $13020 just before `tst.w $57ff2` / `addq.l #1,$2df70`).
;       Real time = the game's VBL counter $6f304 (long, +1 per VBL in the VBL handler; the low word
;       $6f306 is used, deltas mod 65536). One TICK = 12.5 VBL = 4.00 world steps/s (TK = 25 half-VBL).
;       ACC (D+2) = real time not yet simulated, in half-VBL.
;       Three kinds of pass (flags SKIP D+4, RON D+6, read by tick_pass / tick_wx / tick_men):
;         T  ACC >= TK: a world tick. The pass is the ORIGINAL pass (logic1 $127e6 $6522 $d322 $3e06,
;            render, $1abaa weather+season, HUD, $14b62 men, UI/keys, flip).
;         S  as T but another tick is owed after it (ACC still >= TK): the render path is skipped by
;            tick_pass (window copy, landscape, flip), exactly the game's own `$57ff0` skip.
;         R  ACC < TK: render-only pass. Skips the world: the code jumps straight to $13058, so the world
;            clock `$2df70` (also stored as a timestamp by $3e06, compared by $6522) and `$4bb3e`, and logic1, do not run;
;            tick_wx / tick_men skip `$1abaa` and `$14b62`. View limits, render, HUD, UI/click
;            dispatch, camera keys and the flip run as in any pass.
;       Catch-up is clamped to 3 ticks; a gap of more than 4 ticks (disk load, menus) resyncs (one tick,
;       no burst). While `$57ff2` (pause) is set the pass is the original and the clock is kept.
;       Data D = $B8A00 (zero): +0 LAST.w +2 ACC.w +4 SKIP.w +6 RON.w +8 TICKS.l +12 RPASS.l +16 SPASS.l +32 PASS.l
TK      equ     25
D       equ     $b8a00
oLAST   equ     0
oACC    equ     2
oSKIP   equ     4
oRON    equ     6
oTICKS  equ     8
oRPASS  equ     12
oSPASS  equ     16
oPASS   equ     32
        org     $13020
        jsr     $b8800.l

        org     $b8800
head:   movem.l d0-d2/a0,-(a7)
        lea     D.l,a0
        tst.w   $57ff2.l
        bne.s   .pause
        addq.l  #1,oPASS(a0)            ; pass counter (click lifetime, tick_click)
        move.w  $6f306.l,d0
        move.w  d0,d1
        sub.w   oLAST(a0),d1            ; VBLs since the previous pass (mod 65536)
        move.w  d0,oLAST(a0)
        cmpi.w  #50,d1
        bls.s   .acc
        move.w  #TK,oACC(a0)            ; first entry / back from a menu or disk load: resync, one tick
        bra.s   .tick
.acc:   add.w   d1,d1                   ; half-VBL
        add.w   d1,oACC(a0)
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
        move.w  #1,oSKIP(a0)            ; another tick owed: no render this pass
        addq.l  #1,oSPASS(a0)
.out:   movem.l (a7)+,d0-d2/a0
        lea.l   $14e20.l,a2             ; displaced
        rts
.pause: clr.w   oSKIP(a0)
        clr.w   oRON(a0)
        clr.w   oACC(a0)
        move.w  $6f306.l,oLAST(a0)
        bra.s   .out
.ronly: move.w  #1,oRON(a0)
        clr.w   oSKIP(a0)
        addq.l  #1,oRPASS(a0)
        movem.l (a7)+,d0-d2/a0
        addq.l  #4,a7                   ; drop the return into $13026
        jmp     $13058.l
