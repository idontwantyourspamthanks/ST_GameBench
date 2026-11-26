; name: p4_hud_crop_clip_t
; default: no
; site: $38c86
; orig: 3e39000180ec
; note: TYPE-TABLE variant (work/notes/vehicles_p3b.md): TYP[$6220] replaces `$6220 = 13` (same table in p4_hud_crop_fill_t / _replay_t: the types whose cockpit hides at least 67 % of rows 182-199, like the Helicopter's, i.e. 1 3 6 7 9 10 12 13 15 19; 5/17/21 skip the cockpit replay and are never cropped; 2/18 hide 60/62 %; the rest have no measured list).  Use the three _t files together INSTEAD of the originals.
; note: VISUAL-TRADEOFF EXPERIMENT (work/notes/cockpit.md section 4), part 2/3.  The span-fill entry
;       $38c6e computes d7 = ymax - ymin (ymax = word $180ec) and fills rows ymin..ymin+d7; this clamps
;       ymax to line LIM so no fill variant writes below the cropped window (a polygon wholly below
;       gives d7 < 0 and is skipped by the original bmi at $38c8e).  Foot mode only ($6220 = 13).
;       The edge walker still walks the rows below LIM.
LIM     equ     181

        org     $38c86
        jmp     $b4d00.l

        org     $b4d00
        move.w  $180ec.l,d7             ; displaced
        movem.l d0/a0,-(a7)
        move.w  $6220.w,d0
        andi.w  #$1f,d0
        lea     TYP(pc),a0
        tst.b   (a0,d0.w)
        movem.l (a7)+,d0/a0             ; (movem does not change the flags)
        beq.s   .ok
        cmpi.w  #LIM,d7
        ble.s   .ok
        move.w  #LIM,d7
.ok:    jmp     $38c8c.l                ; sub.w d0,d7 ...
TYP:    dc.b    0,1,0,1,0,0,1,1,0,1,1,0,1,1,0,1,0,0,0,1,0,0
        dc.b    0,0,0,0,0,0,0,0,0,0
