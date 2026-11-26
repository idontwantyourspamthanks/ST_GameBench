; name: p4_hud_pfx_ymin
; default: yes
; site: $38cd0
; orig: 300242009440
; note: HUD "clean-prefix" set (work/notes/cockpit.md section 3, option C), part 1/4.  The span-fill
;       dispatcher $38cd0 (reached from $38c6e bsr and from $5020; every terrain/object polygon fill)
;       enters with d6.w = first row of the polygon (spanfill.md E6/E7: ymin).  Record the frame's
;       smallest first row in YMIN ($b4684; reset to 200 by p4_hud_pfx_fill).  Displaces
;       move.w d2,d0 / clr.b d0 / sub.w d0,d2 and rejoins at $38cd6.
YMIN    equ     $b4684

        org     $38cd0
        jmp     $b44c0.l

        org     $b44c0
        move.w  d2,d0                   ; displaced
        clr.b   d0
        sub.w   d0,d2
        cmp.w   YMIN.l,d6
        bge.s   .n
        move.w  d6,YMIN.l
.n:     jmp     $38cd6.l
