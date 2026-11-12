; name: test_sky
; default: no
; site: $1b9a8
; orig: 70ff
; phase: deferred
; note: sky/background fill of sub $1b996 (work/notes/clears_blits.md). d0 seeds
;       d1-d5/a0-a5 (all = $ffffffff = colour 15), and only d0/d1 are reloaded
;       afterwards (at $1b9c0, which feeds just the first 8 bytes of every
;       line). Patching that seed therefore recolours the WHOLE fill (lines
;       58-199, everything not overdrawn by terrain/HUD): moveq #0 -> colour 0
;       instead of colour 15. The fill routine is NOT boot-resident: it arrives
;       with FFB file 1 -> $18d96 during the campaign flow, so the site is
;       applied by the load hook (phase deferred) right after that load.
        org     $1b9a8
        moveq   #0,d0                   ; was moveq #$ff,d0: solid colour 0 sky
