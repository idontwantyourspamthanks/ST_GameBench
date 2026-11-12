; name: p4_hud_crop_fill_t
; default: no
; site: $1b99e
; orig: 203c00002440ddc0
; phase: deferred
; note: TYPE-TABLE variant, see p4_hud_crop_clip_t.
; note: VISUAL-TRADEOFF EXPERIMENT (work/notes/cockpit.md section 4), part 1/3: the 3D window ends at
;       line 181 instead of 199 (foot mode only, $6220 = 13).  Sky fill $1b996: after
;       move.l #$2440,d0 / adda.l d0,a6 (a6 = line 58) the original sets moveq #$46,d7 (71 passes x 2
;       lines = lines 58-199); here 62 passes = lines 58-181.  Rejoins at $1b9a8 (moveq #-1,d0).
        org     $1b99e
        jmp     $b4e00.l
        nop

        org     $b4e00
        move.l  #$2440,d0               ; displaced
        adda.l  d0,a6
        moveq   #$46,d7
        move.l  a0,-(a7)
        move.w  $6220.w,d0
        andi.w  #$1f,d0
        lea     TYP(pc),a0
        tst.b   (a0,d0.w)
        movea.l (a7)+,a0                ; (no flag change)
        beq.s   .f
        moveq   #$3d,d7
.f:     jmp     $1b9a8.l
TYP:    dc.b    0,1,0,1,0,0,1,1,0,1,1,0,1,1,0,1,0,0,0,1,0,0
        dc.b    0,0,0,0,0,0,0,0,0,0
