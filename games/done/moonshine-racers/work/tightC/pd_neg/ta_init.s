; name: ta_init
; default: no
; site: $edea
; orig: 4eb90000dd18
; requires: hd_stage ta_erase
; conflicts: hd_init
; doc: hd_init plus: forget what the face shadows hold at every race start/restart (the HUD's sky repaint wipes the face).  Replaces hd_init when ta_face is used.
; note: Tighten wave A.  Same site as hd_init (`jsr $dd18.l` of the race init, once per race start/restart): runs the hd_init blob $BB700 (clears the `painted` bytes of both shadow sets: the next pass into each buffer repaints
; note: strip and sky, which wipes the face) and then writes $ffff into FV0/FV1.  Needs ta_erase (owner of the FV words).  conflicts hd_init (same site): select ta_init INSTEAD of hd_init.
FV0     equ     $BEF00
FV1     equ     $BEF02
        org     $edea
        jsr     $BE200.l

        org     $BE200
tainit: jsr     $BB700.l
        move.w  #$ffff,FV0.l
        move.w  #$ffff,FV1.l
        rts
