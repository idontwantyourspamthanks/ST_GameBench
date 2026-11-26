; name: p3c_head
; default: no
; site: $31486
; orig: 4df8770e4eb84f5a
; data: $b42e0 32
; data: $b8700 1984
; data: $b8f00 256
; note: P3c = the type-independent 25 Hz player step, INTERPOLATED alternative to p3cp_head (work/notes/vehicles_p3b.md; not shipping).  It does NOT have the later p3cp fixes
;       (wave pointer restore, deadline-aware extra passes) and was not re-gated: do not ship it as is.  Do not combine with p3cp_head.  Needs p3c_sim ($31570) and p3c_render ($3158c).
;       Idea: the 5 Hz tick runs ONCE per group of five 40 ms passes, completely unmodified (PH 1), so the world state at the end of every
;       group is the original game's by construction, for every vehicle type, including the ones that cannot be split exactly (the
;       exponential parachute fall, the speed ramp, probes, derivative/integrator controls, fatigue).  The passes in between only
;       DISPLAY the pose a fraction j/5 of the way from the start to the end of the tick:
;         PH 1    pre-calls, player sim ($33bca, hook p3c_sim) = the original tick; then the pose is set to j = 1 and the view refreshed.
;         PH 2-4  pose j = PH, view refresh ($3467c $346a2 $37a62 $37afa), HUD gauge draw + render + flip ($3158c).
;         PH 5    the end-of-tick state is restored (pose AND the view words the refresh wrote), then the post-calls ($31576: NPC table,
;                 HUD, clock, ...) and the render, i.e. option A's tail.
;       Interpolated: X, Y, heading ($6742 $6294 $764a), bank, pitch, altitude $764c, lean.  Not interpolated (display = end-of-tick):
;       everything else.  A tick whose pose jumps (type change, recentre of the map, |dX|,|dY|,|dAlt| > $1000) or does not move is shown unchanged.
;       Real time = the tick_vbl clock ($B3400, units of 1/300 s): GRP = 60 units = 5 Hz, SUBT = 12 units = 40 ms.
;       TAB[type] = 0 keeps a type on the plain 5 Hz pass (option A) (also when $40b6 <> 0).
;       Shared word block D = $b42e0 (LAST.l +0, ACC.w +4, PH.w +6, SUB.w +8 (1 = PH 1 of an interpolated group), +10 unused, SKIP.w +12 (read by p3c_render)).
;       Own data S = $b8f00: P0 (pose before the tick) +0, INT +$20, GV (a group is open: shadow valid) +$22, shadow of the end-of-tick state +$30.
;       Code: one segment at $b8000 (hook first: p3c_sim jumps to it), hook / head / helpers / tables.
GRP     equ     60
SUBT    equ     12
CLOCK   equ     $b3400
D       equ     $b42e0
S       equ     $b8f00
SV676   equ     S+$26                   ; $676e (probe/arrival result) of the tick, withheld from the post-flip handler until PH 5
JP      equ     S+$28                   ; the previous group's pose jumped
PLIVE   equ     S+$2a                   ; the live pose is the predicted one of PH 5
RD      equ     S+$a0                   ; a render happened since the NPC table snapshot was last applied
NS      equ     $b8700                  ; snapshot of the NPC table $3532-$3cee (30 x $42) after the pre-calls and the sim of the tick
P0      equ     S+0
INT     equ     S+$20
GV      equ     S+$22
WV      equ     S+$24
WVV     equ     S+$2c
SH      equ     S+$30
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
hook:   tst.w   D+8.l                   ; SUB: PH 1 of an interpolated group?
        bne.s   .sub
        jmp     $33bca.l                ; plain pass: the original call
.sub:   bsr     cap0                    ; pose before the tick
        jsr     $33bca.l                ; the original tick
        bsr     cap1                    ; shadow = end of tick, INT
        bsr     npcsave
        move.w  $676e.w,SV676.l         ; the post-flip handler ($32db6) acts on it after the first rendered pass: it must see the end-of-tick pose
        clr.w   $676e.w                 ; (eject, crash...), i.e. run at PH 5
        addq.l  #4,a7                   ; drop the return into $31576: the post-calls run at PH 5
        bsr     subpass                 ; pose 1/5 + view refresh (if a render is due)
        clr.w   $7020.w
        tst.w   D+12.l
        bne.s   .loop
        move.w  #1,RD.l
        lea     $770e.w,a6
        jmp     $3158c.l                ; HUD gauges, view setup, renderer, flip
.loop:  jmp     $31486.l

        cnop    0,256                   ; head at $b8100
; ---- head of the in-game frame loop ($31486) --------------------------------------------------------------------------------------------
head:   movem.l d0-d2/a0-a1,-(a7)
        lea     D.l,a0
        moveq   #GRP,d2                 ; d2 = clock units this pass consumes
        move.w  $6220.w,d0
        cmpi.w  #21,d0
        bhi.s   .wait
        lea     TAB(pc),a1
        tst.b   (a1,d0.w)
        beq.s   .wait
        tst.w   $40b6.w
        bne.s   .wait
        moveq   #SUBT,d2                ; interpolated type: 25 Hz pass
.wait:  move.l  CLOCK.l,d0
        move.l  d0,d1
        sub.l   (a0),d1
        move.l  d0,(a0)
        cmpi.l  #4*GRP,d1
        bls.s   .acc
        moveq   #0,d1                   ; first entry or back from another screen: resync, one pass, no burst
        move.b  d2,d1
        clr.w   4(a0)
        clr.w   6(a0)                   ; PH = 0: the next interpolated pass is PH 1
        clr.w   WVV.l                   ; wave phase: take the live one again
        clr.w   RD.l
        bsr     restore                 ; a group cut short: the live pose back to the end of its tick
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
        bne     .cont
        moveq   #1,d0                   ; no group is open (never started, or the loop was left): start one
.first: bsr     restore                 ; (predict: the live pose is the predicted one of PH 5; no-op when no group is open)
        move.w  d0,6(a0)
        move.w  #1,8(a0)                ; SUB = 1: the hook at $31570 runs this tick and shows 1/5 of it
        movem.l (a7)+,d0-d2/a0-a1
        lea     $770e.w,a6              ; displaced
        jmp     $4f5a.w                 ; displaced jsr, as a tail call: the pre-calls follow
.cont:  move.w  d0,6(a0)
        cmpi.w  #5,d0
        beq     .last
        movem.l (a7)+,d0-d2/a0-a1       ; PH 2-4
        addq.l  #4,a7                   ; drop the return into $3148e
        bsr     npcfix
        bsr     rewave
        bsr     subpass
        clr.w   $7020.w
        tst.w   D+12.l
        bne.s   .loop
        move.w  #1,RD.l
        lea     $770e.w,a6
        jmp     $3158c.l
.loop:  jmp     $31486.l
.last:  clr.w   12(a0)                  ; PH 5 renders the pose the original shows, so the next tick's pre-calls read the render data (visibility lists)
        cmpi.w  #GRP,4(a0)              ; of the end of this tick: skipped only when a whole tick is owed (option A's rule)
        blt.s   .l5
        move.w  #1,12(a0)
.l5:
        bsr     npcfix                  ; the extra renders of PH 1-4 write NPC records (+$36.., wave-aware heights) that the AI reads: undo them
        bsr     restore                 ; PH 5: end-of-tick state back (also from a predicted pose), then the post-calls
        move.w  SV676.l,$676e.w         ; the probe result of the tick, for the post-flip handler of this pass
        bsr     rewave
        movem.l (a7)+,d0-d2/a0-a1
        addq.l  #4,a7
        lea     $770e.w,a6
        jmp     $31576.l
.full:  move.w  d0,6(a0)                ; plain type: PH 5, option A
        bsr     restore
        movem.l (a7)+,d0-d2/a0-a1
        lea     $770e.w,a6
        jmp     $4f5a.w

; ---- pose before the tick ---------------------------------------------------------------------------------------------------------------
cap0:   lea     P0.l,a0
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
        tst.w   WVV.l                   ; sea wave phase: the original advances it (+8, $1dcae) after every render; here it advances once per tick
        bne.s   .wv
        move.w  $1877c.l,WV.l           ; first group: the live phase
        move.w  #1,WVV.l
        bra     rewave
.wv:    move.w  WV.l,d0
        addq.w  #8,d0
        andi.w  #$7e,d0
        move.w  d0,WV.l
        bra     rewave                  ; the sim of this tick sees the phase of this tick

; ---- shadow = end-of-tick state; INT = 1 if the pose moved smoothly (else the tick is shown unchanged) -------------------------------------
cap1:   movem.l d0-d2/d4-d6/a0-a3,-(a7)
        lea     RTAB(pc),a2
        lea     SH.l,a1
.reg:   move.w  (a2)+,d1
        beq.s   .done
        movea.w (a2)+,a0
.cp:    move.w  (a0)+,(a1)+
        subq.w  #1,d1
        bne.s   .cp
        bra.s   .reg
.done:  move.w  #1,GV.l
        lea     P0.l,a2
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
.fin:
        move.w  d4,JP.l
        move.w  d6,INT.l
        movem.l (a7)+,d0-d2/d4-d6/a0-a3
        rts

; ---- NPC table: the renders write into it (the AI of the post-calls reads it): only the render of PH 5 (= option A's) may leave a trace -------------
npcsave:
        movem.l d0/a0-a1,-(a7)
        lea     $3532.w,a0
        lea     NS.l,a1
        move.w  #494,d0
.l:     move.l  (a0)+,(a1)+
        dbra    d0,.l
        movem.l (a7)+,d0/a0-a1
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

; ---- the wave phase back to its value at the start of the tick (each render advances it; the original advances it once per tick) ---------------
rewave: move.l  a0,-(a7)
        move.w  WV.l,$1877c.l
        moveq   #0,d0
        move.w  WV.l,d0
        lea     $18574.l,a0
        adda.w  d0,a0
        move.l  a0,$1dfba.l
        movea.l (a7)+,a0
        rts

; ---- the live state back to the end of the tick ------------------------------------------------------------------------------------------
restore:
        tst.w   GV.l
        bne.s   .go
        tst.w   PLIVE.l
        beq.s   .r
.go:    movem.l d0-d1/a0-a2,-(a7)
        lea     RTAB(pc),a2
        lea     SH.l,a1
.reg:   move.w  (a2)+,d1
        beq.s   .done
        movea.w (a2)+,a0
.cp:    move.w  (a1)+,(a0)+
        subq.w  #1,d1
        bne.s   .cp
        bra.s   .reg
.done:  clr.w   GV.l
        clr.w   PLIVE.l
        movem.l (a7)+,d0-d1/a0-a2
.r:     rts

; ---- pose j = PH (1..4) of the open group and the view words derived from it ---------------------------------------------------------------
subpass:
        movem.l d0-d7/a0-a6,-(a7)
        tst.w   INT.l
        beq     .x
        tst.w   D+12.l                  ; SKIP: no render this pass, nothing to show
        bne     .x
        move.w  D+6.l,d7                ; j
        bsr     posej
        move.w  #1,PLIVE.l
.x:     movem.l (a7)+,d0-d7/a0-a6
        rts
posej:  lea     P0.l,a2
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
        cmpi.w  #5,d7
        bls.s   .up
        moveq   #5,d7                   ; descending: no prediction past the end of the tick (the camera could end up below the terrain)
.up:    bsr     lin
        move.w  d6,d7
        move.w  d0,$764c.w
        move.w  20(a2),d0
        ext.l   d0
        move.w  20(a3),d1
        ext.l   d1
        cmpi.w  #5,d7
        bls.s   .ln
        moveq   #5,d7                   ; lean (view tilt, a level): never predicted
.ln:    bsr     lin
        move.w  d6,d7
        move.w  d0,$674e.w
        jsr     $3467c.l                ; the coefficient / view vector / view matrix / cell setup of the tail of the tick
        jsr     $346a2.l
        jsr     $37a62.l
        jsr     $37afa.l
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
; TAB[$6220]: 1 = 25 Hz interpolated pass, 0 = plain 5 Hz pass.  Types 0..21.
TAB:    dc.b    1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1
        dc.b    0,0
