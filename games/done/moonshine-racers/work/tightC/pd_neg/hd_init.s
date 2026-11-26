; name: hd_init
; default: yes
; site: $edea
; orig: 4eb90000dd18
; requires: hd_stage
; doc: Race start/restart of the new HUD: both screen buffers repaint the top strip and the sky on their next pass (the stock cloud initialisation $dd18 is gone with the clouds).
; note: New HUD (work/notes/hud_build.md).  Site $edea: `jsr $dd18.l` (cloud slot init, in the race init $edea-$ef2c that runs once for every race start/restart with $100e = 0) -> `jsr $BB700.l`.
; note: The blob clears the `painted` byte of both shadow sets (S0 for $70000, S1 for $78000 of hd_stage), so the first pass into each buffer repaints the strip bitmap and the sky rows 16-64 (the race restart does not clear the screens).
        org     $edea
        jsr     $BB700.l

        org     $BB700
hdinit: clr.b   $BCF00.l
        clr.b   $BCF40.l
        rts
