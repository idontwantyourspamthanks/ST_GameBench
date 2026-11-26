; name: p4_hud_crop_clip
; default: no
; site: $38c86
; orig: 3e39000180ec
; note: VISUAL-TRADEOFF EXPERIMENT (work/notes/cockpit.md section 4), part 2/3.  The span-fill entry
;       $38c6e computes d7 = ymax - ymin (ymax = word $180ec) and fills rows ymin..ymin+d7; this clamps
;       ymax to line LIM so no fill variant writes below the cropped window (a polygon wholly below
;       gives d7 < 0 and is skipped by the original bmi at $38c8e).  Foot mode only ($6220 = 13).
;       The edge walker still walks the rows below LIM.
LIM     equ     181

        org     $38c86
        jmp     $b44c0.l

        org     $b44c0
        move.w  $180ec.l,d7             ; displaced
        cmpi.w  #13,$6220.w
        bne.s   .ok
        cmpi.w  #LIM,d7
        ble.s   .ok
        move.w  #LIM,d7
.ok:    jmp     $38c8c.l                ; sub.w d0,d7 ...
