; name: p3cp_head
; default: yes
; site: $31486
; orig: 4df8770e4eb84f5a
; data: $b42e0 32
; data: $b8700 1984
; data: $b8f00 256
; note: P3cp = the PREDICT-AHEAD 25 Hz player step, type independent (work/notes/vehicles_p3b.md).  It is the game's scheduler (replaces v1.2's p3b_head and the p3b_pos/hdg/alt/bank/save/probe
;       integrators, which are gone) and needs p3c_sim ($31570, the hook; it only records the pose before the tick here) and p3c_render ($3158c, unchanged).
;       Per group of five 40 ms passes:
;         PH 1    the ORIGINAL tick, completely unmodified and complete (pre-calls, player sim, post-calls, render at the pose the original shows, flip,
;                 post-flip handler), so the world, the player and the picture at PH 1 are the unpatched game's by construction, for every vehicle type
;                 (exponential parachute fall, speed ramp, probes, derivative/integrator controls, fatigue, render->logic channels included).
;         PH 2-5  extra frames at the PREDICTED pose: T_end + (T_end - T_start) * (PH - 1) / 5, where T_start/T_end are the pose before/after the tick that
;                 just ran (the next tick is assumed to repeat it), then the view refresh ($3467c $346a2 $37a62 $37afa) and HUD gauge draw + render + flip
;                 ($3158c).  They run no game logic.  The live state is put back to the end of the tick (pose, view words, NPC table, wave phase) before the
;                 next PH 1, so every group end is the unpatched game's.
;       Overshoot limits: no prediction in a tick that changed the type, that jumped (|dX|,|dY|,|dAlt| > $1000, |dHeading| > 256, |dBank|,|dPitch| > 128: recentre of the
;       map, landing, eject), that ended with a collision/arrival result ($676e) or a landing ($767e), nor in the FIRST group after such a jump.  Altitude is never extrapolated downwards
;       (the camera could end up below the terrain) and the lean (view tilt) never.  Stopping after a move shows the extra frames' pose snap back by up to 4/5 of a tick step.
;       Not a game input: the extra frames' renders write the NPC records (+$36.., visibility counters) and advance the sea wave phase ($1dcae-$1dcca: $1877c and the pointer
;       $1dfba); the NPC table is restored from a snapshot taken after PH 1, and the wave phase AND pointer are restored from the values the PH 1 render left (the pointer is
;       not always base + phase: the map window rebuild $1dd7e resets it to the table base, and the next tick's sim reads it).
;       Real time: the tick_vbl clock ($B3400, 1/300 s): GRP = 60 units = 5 Hz, SUBT = 12 units = 40 ms.  PH 1 renders unless a whole tick (GRP) is owed (option A's
;       rule), PH 2-5 unless one more pass is owed or the render would not end before the next PH 1 is due (12 * (6 - PH) - lateness < the measured duration of the last two
;       extra passes): a PH 1 that starts late reads the keys (Esc) and the mouse later than the original's tick does, so a pass may end at most SLACK = 1 VBL after the next PH 1 is due (by the measured duration, VBL-quantised); the due times stay on the clock grid (ACC), so a late PH 1 does not push later ticks back.
;       TAB[type] = 0 keeps a type on the plain 5 Hz pass (also when $40b6 <> 0).
;       Shared word block D = $b42e0 (LAST.l +0, ACC.w +4, PH.w +6, SUB.w +8 (1 = PH 1 of a predicted group), +10 unused, SKIP.w +12 (read by p3c_render)).
;       Own data S = $b8f00.  Code: one segment at $b8000.
GRP     equ     60
SUBT    equ     12
CLOCK   equ     $b3400
D       equ     $b42e0
S       equ     $b8f00
P0      equ     S+0                     ; pose before the tick: X.l Y.l $6742 $6294 $764a $6746 $674a $764c $674e $6220 (24 bytes)
INT     equ     S+$20                   ; the group shows predicted poses
GV      equ     S+$22                   ; the hook ran in this group (P0 valid)
WV      equ     S+$24                   ; sea wave phase the tick's sim and PH 1 render saw
JP      equ     S+$28                   ; the previous tick's pose jumped
PLIVE   equ     S+$2a                   ; the live pose is a predicted one (restore it)
WX      equ     S+$2c                   ; an extra render altered the live wave phase / pointer (EPH/EPT hold the end-of-tick values)
EPH     equ     S+$2e                   ; $1877c after PH 1
EPT     equ     S+$a4                   ; $1dfba after PH 1 (long; the original's $1dd7e, the window rebuild, resets it to the table base without touching the phase)
TS      equ     S+$a8                   ; clock at the start of the last extra pass (long)
RF      equ     S+$ac                   ; the last pass rendered: measure it
REST    equ     S+$ae                   ; estimated duration of an extra pass (units)
RPV     equ     S+$b0                   ; the previous measure
SLKX    equ     S+$b2                   ; tuning word (zero-initialised): added to SLACK, only the gates set it (-SLACK = strict rule, +1000 = no rule)
SLACK   equ     6                       ; an extra pass may end up to one 50 Hz VBL (6 clock units) after the next PH 1 is due
SH      equ     S+$30                   ; shadow of the end-of-tick state (51 words)
RD      equ     S+$a0                   ; an extra render happened since the NPC table was restored
NS      equ     $b8700                  ; NPC table $3532-$3cee after PH 1
        org     $31486
        jsr     $b8100.l
        nop

        org     $b8000
CHG     macro                           ; \1 = P0 offset, \2 = shadow offset: d6 = 1 if the word differs
        move.w  \1(a2),d0
        cmp.w   \2(a3),d0
        beq.s   .c\@
        moveq   #1,d6
.c\@:
        endm
DLT     macro                           ; long delta d1 = (shadow - P0): d6 = 1 if <> 0, jump to .no if |d1| > $1000
        beq.s   .z\@
        moveq   #1,d6
        tst.l   d1
        bpl.s   .p\@
        neg.l   d1
.p\@:   cmpi.l  #$1000,d1
        bgt     .no
.z\@:
        endm
AJ      macro                           ; \1 = P0 offset, \2 = shadow offset, \3 = limit: |sext10 delta| > limit is a pose jump
        move.w  \2(a3),d1
        sub.w   \1(a2),d1
        lsl.w   #6,d1
        asr.w   #6,d1
        bpl.s   .a\@
        neg.w   d1
.a\@:   cmpi.w  #\3,d1
        bgt     .no
        endm
; ---- hook at $31570: replaces `jsr $33bca.l` (the player sim); (a7) = $31576 -------------------------------------------------------
hook:   tst.w   D+8.l                   ; SUB: PH 1 of a predicted group?
        beq.s   .plain
        bsr     cap0                    ; pose before the tick, wave phase of the tick
.plain: jmp     $33bca.l                ; the original call (tail call): the post-calls and the render follow as in option A

        cnop    0,256                   ; head at $b8100
; ---- head of the in-game frame loop ($31486) --------------------------------------------------------------------------------------------
head:   movem.l d0-d2/a0-a1,-(a7)
        lea     D.l,a0
        tst.w   RF.l
        beq.s   .nm
        clr.w   RF.l
        move.l  CLOCK.l,d0
        sub.l   TS.l,d0                 ; clock units the last extra pass took (VBL granularity)
        cmpi.l  #GRP,d0
        bls.s   .m1
        moveq   #GRP,d0
.m1:    move.w  RPV.l,d1
        move.w  d0,RPV.l
        cmp.w   d1,d0
        bge.s   .m2
        move.w  d1,d0
.m2:    move.w  d0,REST.l               ; REST = the longer of the last two
.nm:
        moveq   #GRP,d2                 ; d2 = clock units this pass consumes
        move.w  $6220.w,d0
        cmpi.w  #21,d0
        bhi.s   .wait
        lea     TAB(pc),a1
        tst.b   (a1,d0.w)
        beq.s   .wait
        tst.w   $40b6.w
        bne.s   .wait
        moveq   #SUBT,d2                ; predicted type: 25 Hz pass
.wait:  move.l  CLOCK.l,d0
        move.l  d0,d1
        sub.l   (a0),d1
        move.l  d0,(a0)
        cmpi.l  #4*GRP,d1
        bls.s   .acc
        moveq   #0,d1                   ; first entry or back from another screen: resync, one pass, no burst
        move.b  d2,d1
        clr.w   4(a0)
        clr.w   6(a0)                   ; PH = 0: the next predicted pass is PH 1
        clr.w   REST.l                  ; no extra-pass duration known yet
        clr.w   RPV.l
        clr.w   RF.l
        bsr     fixup                   ; a group cut short: live pose, NPC table and wave state back to the end of their tick
.acc:   add.w   d1,4(a0)
        cmp.w   4(a0),d2
        bgt.s   .wait                   ; ahead of real time: wait for VBLs
        sub.w   d2,4(a0)
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
        moveq   #5,d0
        clr.l   8(a0)                   ; SUB, HOLD
        cmpi.w  #SUBT,d2
        bne     .full
        move.w  6(a0),d0
        addq.w  #1,d0
        cmpi.w  #5,d0
        bls.s   .ph
        moveq   #1,d0
.ph:    cmpi.w  #1,d0
        beq.s   .first
        tst.w   GV.l
        bne.s   .cont
        moveq   #1,d0                   ; no group is open (never started, or the loop was left): start one
.first: tst.w   REST.l                 ; the estimate only grows when an extra pass renders: let it shrink by one unit per group, so a
        beq.s   .rd                     ; stale long measure (a map rebuild inside a pass) is probed again after a while
        subq.w  #1,REST.l
.rd:    bsr     fixup                   ; live pose and NPC table back to the end of the previous tick
        clr.w   GV.l
        move.w  d0,6(a0)
        move.w  #1,8(a0)                ; SUB = 1: the hook at $31570 records the pose before this tick
        clr.w   12(a0)                  ; PH 1 is the original tick: its render is skipped only when a whole tick is owed (option A's rule)
        cmpi.w  #GRP,4(a0)
        blt.s   .f1
        move.w  #1,12(a0)
.f1:    movem.l (a7)+,d0-d2/a0-a1
        lea     $770e.w,a6              ; displaced
        jmp     $4f5a.w                 ; displaced jsr, as a tail call: the pre-calls follow
.cont:  move.w  d0,6(a0)                ; PH 2-5: extra frame
        moveq   #6,d1                   ; render only if it ends before the next PH 1 is due: 12 * (6 - PH) - lateness >= the duration of the last extra passes
        sub.w   d0,d1                   ; (a late PH 1 would consume the input, e.g. Esc, a tick after the original does)
        mulu.w  #SUBT,d1
        sub.w   4(a0),d1
        addi.w  #SLACK,d1               ; middle ground: PH 1 may start up to 1 VBL late (the grid is kept: ACC is not touched, the next due times do not move)
        add.w   SLKX.l,d1
        cmp.w   REST.l,d1
        bge.s   .fits
        move.w  #1,12(a0)
.fits:
        move.l  CLOCK.l,TS.l            ; start of this extra pass (its duration is measured at the next head entry)
        movem.l (a7)+,d0-d2/a0-a1
        addq.l  #4,a7                   ; drop the return into $3148e
        cmpi.w  #2,D+6.l
        bne.s   .c3
        bsr     cap1                    ; PH 2: the end-of-tick state, after the whole of PH 1 (post-calls, render, post-flip handler)
        bsr     npcsave
        clr.w   $676e.w                 ; the post-flip handler has acted on the tick's result once (PH 1): not again
        bra.s   .c4
.c3:    bsr     npcfix                  ; the extra renders write NPC records that the AI reads: undo them
.c4:    bsr     rewave
        bsr     subpass
        clr.w   $7020.w
        tst.w   D+12.l
        bne.s   .loop
        move.w  #1,RD.l
        move.w  #1,RF.l
        lea     $770e.w,a6
        jmp     $3158c.l                ; HUD gauges, view setup, renderer, flip
.loop:  jmp     $31486.l
.full:  move.w  d0,6(a0)                ; plain type: PH 5, option A
        bsr     fixup
        movem.l (a7)+,d0-d2/a0-a1
        lea     $770e.w,a6
        jmp     $4f5a.w

; ---- pose before the tick; wave phase of the tick ------------------------------------------------------------------------------------------
cap0:   movem.l d0/a0,-(a7)
        lea     P0.l,a0
        move.l  $66e6.w,(a0)+           ; +0
        move.l  $66ea.w,(a0)+           ; +4
        move.w  $6742.w,(a0)+           ; +8
        move.w  $6294.w,(a0)+           ; +10
        move.w  $764a.w,(a0)+           ; +12
        move.w  $6746.w,(a0)+           ; +14
        move.w  $674a.w,(a0)+           ; +16
        move.w  $764c.w,(a0)+           ; +18
        move.w  $674e.w,(a0)+           ; +20
        move.w  $6220.w,(a0)+           ; +22
        move.w  $1877c.l,WV.l           ; wave phase of the tick (a render advances it)
        move.w  #1,GV.l
        movem.l (a7)+,d0/a0
        rts

; ---- wave state: PH 2 takes the live end-of-tick phase and pointer (the original's); the extra renders run at WV; the next tick restores them ----
wavesave:
        move.w  $1877c.l,EPH.l
        move.l  $1dfba.l,EPT.l
        rts
wavefix:
        tst.w   WX.l
        beq.s   .r
        clr.w   WX.l
        move.w  EPH.l,$1877c.l
        move.l  EPT.l,$1dfba.l
.r:     rts

; ---- shadow = end-of-tick state; INT = 1 if the next frames may show predicted poses ----------------------------------------------------------
cap1:   bsr     wavesave
        movem.l d0-d2/d4-d6/a0-a3,-(a7)
        lea     RTAB(pc),a2
        lea     SH.l,a1
.reg:   move.w  (a2)+,d1
        beq.s   .done
        movea.w (a2)+,a0
.cp:    move.w  (a0)+,(a1)+
        subq.w  #1,d1
        bne.s   .cp
        bra.s   .reg
.done:  lea     P0.l,a2
        lea     SH.l,a3
        moveq   #0,d6                   ; d6 = the pose changed
        moveq   #0,d4                   ; d4 = the pose jumped
        move.w  22(a2),d0
        cmp.w   $6220.w,d0
        bne     .no                     ; type changed in the tick
        tst.w   $676e.w
        bne     .no                     ; collision revert / arrival: the step went back
        tst.w   $767e.w
        bne     .no                     ; landing: bank and altitude are reset
        move.l  (a3),d1
        sub.l   (a2),d1
        DLT
        move.l  4(a3),d1
        sub.l   4(a2),d1
        DLT
        move.w  26(a3),d1
        ext.l   d1
        move.w  18(a2),d0
        ext.l   d0
        sub.l   d0,d1
        DLT
        AJ      8,8,256
        AJ      14,12,128
        AJ      16,16,128
        CHG     8,8
        CHG     10,22
        CHG     12,24
        CHG     14,12
        CHG     16,16
        CHG     20,20
        bra     .fin
.no:    moveq   #0,d6
        moveq   #1,d4
.fin:   tst.w   JP.l                    ; no prediction in the first group after a jump
        beq.s   .jp
        moveq   #0,d6
.jp:    move.w  d4,JP.l
        move.w  d6,INT.l
        movem.l (a7)+,d0-d2/d4-d6/a0-a3
        rts

; ---- NPC table: the extra renders write into it (the AI reads it); only the render of PH 1 (= option A's) may leave a trace ----------------------
npcsave:
        movem.l d0/a0-a1,-(a7)
        lea     $3532.w,a0
        lea     NS.l,a1
        move.w  #494,d0
.l:     move.l  (a0)+,(a1)+
        dbra    d0,.l
        movem.l (a7)+,d0/a0-a1
        clr.w   RD.l
        rts
npcfix: tst.w   RD.l
        beq.s   .r
        clr.w   RD.l
        movem.l d0/a0-a1,-(a7)
        lea     NS.l,a0
        lea     $3532.w,a1
        move.w  #494,d0
.l:     move.l  (a0)+,(a1)+
        dbra    d0,.l
        movem.l (a7)+,d0/a0-a1
.r:     rts

; ---- the wave phase of the tick (each render advances it) ------------------------------------------------------------------------------------
rewave: move.w  #1,WX.l
        move.l  a0,-(a7)
        move.w  WV.l,$1877c.l
        moveq   #0,d0
        move.w  WV.l,d0
        lea     $18574.l,a0
        adda.w  d0,a0
        move.l  a0,$1dfba.l
        movea.l (a7)+,a0
        rts

; ---- live pose, view words and NPC table back to the end of the tick ----------------------------------------------------------------------------
fixup:  bsr     npcfix
        bsr     wavefix
restore:
        tst.w   PLIVE.l
        beq.s   .r
        movem.l d0-d1/a0-a2,-(a7)
        lea     RTAB(pc),a2
        lea     SH.l,a1
.reg:   move.w  (a2)+,d1
        beq.s   .done
        movea.w (a2)+,a0
.cp:    move.w  (a1)+,(a0)+
        subq.w  #1,d1
        bne.s   .cp
        bra.s   .reg
.done:  clr.w   PLIVE.l
        movem.l (a7)+,d0-d1/a0-a2
.r:     rts

; ---- predicted pose of PH (2..5) and the view words derived from it -------------------------------------------------------------------------
subpass:
        movem.l d0-d7/a0-a6,-(a7)
        tst.w   INT.l
        beq     .x
        tst.w   D+12.l                  ; SKIP: no render this pass, nothing to show
        bne     .x
        move.w  D+6.l,d7
        addq.w  #4,d7                   ; j = PH + 4: T_end + (T_end - T_start) * (PH - 1) / 5
        lea     P0.l,a2
        lea     SH.l,a3
        move.l  (a2),d0
        move.l  (a3),d1
        bsr     lin
        move.l  d0,$66e6.w
        move.l  4(a2),d0
        move.l  4(a3),d1
        bsr     lin
        move.l  d0,$66ea.w
        move.w  8(a2),d0
        move.w  8(a3),d1
        bsr     ang
        move.w  d0,$6742.w
        move.w  10(a2),d0
        move.w  22(a3),d1
        bsr     ang
        move.w  d0,$6294.w
        move.w  12(a2),d0
        move.w  24(a3),d1
        bsr     ang
        move.w  d0,$764a.w
        move.w  14(a2),d0
        move.w  12(a3),d1
        bsr     ang
        lsl.w   #6,d0
        asr.w   #6,d0
        move.w  d0,$6746.w              ; bank: signed 10 bit
        move.w  16(a2),d0
        move.w  16(a3),d1
        bsr     ang
        move.w  d0,$674a.w
        move.w  18(a2),d0
        ext.l   d0
        move.w  26(a3),d1
        ext.l   d1
        move.w  d7,d6
        cmp.l   d0,d1
        bge.s   .up
        moveq   #5,d7                   ; descending: no prediction past the end of the tick (the camera could end up below the terrain)
.up:    bsr     lin
        move.w  d6,d7
        move.w  d0,$764c.w
        move.w  20(a2),d0
        ext.l   d0
        move.w  20(a3),d1
        ext.l   d1
        moveq   #5,d7                   ; lean (view tilt, a level): never predicted
        bsr     lin
        move.w  d0,$674e.w
        jsr     $3467c.l                ; the coefficient / view vector / view matrix / cell setup of the tail of the tick
        jsr     $346a2.l
        jsr     $37a62.l
        jsr     $37afa.l
        move.w  #1,PLIVE.l              ; the live pose is predicted: fixup puts it back before the next tick
.x:     movem.l (a7)+,d0-d7/a0-a6
        rts
lin:    sub.l   d0,d1                   ; d0 + (d1 - d0) * j / 5  (|d1 - d0| <= $1000)
        muls.w  d7,d1
        divs.w  #5,d1
        ext.l   d1
        add.l   d1,d0
        rts
ang:    sub.w   d0,d1                   ; (d0 + sext10(d1 - d0) * j / 5) & $3fe
        lsl.w   #6,d1
        asr.w   #6,d1
        muls.w  d7,d1
        divs.w  #5,d1
        add.w   d1,d0
        andi.w  #$3fe,d0
        rts

; Region table: (word count, address): the pose and every word $3467c $346a2 $37a62 $37afa write.  Shadow offsets: X.l +0, Y.l +4,
; $6742 +8, $6746 +12, $674a +16, $674e +20, $6294 +22, $764a +24, $764c +26.
RTAB:   dc.w    4,$66e6
        dc.w    7,$6742
        dc.w    1,$6294
        dc.w    1,$764a
        dc.w    1,$764c
        dc.w    6,$763e
        dc.w    2,$7652
        dc.w    14,$7662
        dc.w    2,$53ac
        dc.w    4,$670a
        dc.w    9,$6780
        dc.w    0
; TAB[$6220]: 1 = 25 Hz predicted pass, 0 = plain 5 Hz pass.  Types 0..21.
TAB:    dc.b    1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1
        dc.b    0,0
