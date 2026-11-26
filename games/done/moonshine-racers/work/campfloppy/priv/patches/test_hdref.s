; name: test_hdref
; default: no
; site: $ef7a
; orig: 2a7810084eb9
; conflicts: hd_stage hd_init
; note: GATE REFERENCE for the new HUD (work/notes/hud_build.md, tools/msrmask.py): the stock HUD stage reduced to the message ticker $11ef0 and the face $f90c (no thermometer, minimap, score, dial, cup, gear, speedometer, clouds).  Together with hd_clouds
; note: (no cloud position update) it draws what the new HUD must leave untouched: rows 65-199 of the reference are the stock game minus its HUD and clouds.  Never part of a release.
        org     $ef7a
        jmp     $BB100.l

        org     $BB100
        movea.l $1008.w,a5
        jsr     $11ef0.l
        jsr     $f90c.l
        movea.l $1008.w,a5
        rts
