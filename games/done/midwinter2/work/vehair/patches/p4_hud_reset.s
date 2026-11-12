; name: p4_hud_reset
; default: yes
; site: $28cc0
; orig: 6100fd9e41f8732c
; data: $b4680 20
; note: Shared by the HUD "clean-prefix" set (p4_hud_pfx_*) and the "crop" experiment (p4_hud_crop_*),
;       work/notes/cockpit.md sections 3C/4.  $28cc0 is the 3D-view (re)entry that (re)builds the HUD
;       overlay list ($28cee jsr $30e30; callers $31632/$32ebc/$33016).  The screen buffers can hold
;       anything after a screen change, so forget the per-buffer state: HUD data block at $b4680 =
;       KB0.w KB1.w (clean-prefix blocks / dashboard-drawn flags), YMIN.w, CK.w (skip cache key),
;       CD7.w, pad.w, CA1.l, CA0.l.  Clears KB0/KB1 and CK.
;       Displaces bsr.w $28a60 / lea.l $732c.w,a0 and rejoins at $28cc8.
KB      equ     $b4680
CK      equ     $b4686

        org     $28cc0
        jmp     $b44e0.l
        nop

        org     $b44e0
        clr.l   KB.l
        clr.w   CK.l
        jsr     $28a60.l                ; was bsr.w $28a60
        lea     $732c.w,a0              ; displaced
        jmp     $28cc8.l
