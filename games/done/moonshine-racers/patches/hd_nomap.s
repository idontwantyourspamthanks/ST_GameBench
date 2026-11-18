; name: hd_nomap
; default: yes
; requires: hd_stage hd_clouds
; note: Occupancy-map writers of the speech path (work/notes/hud_build.md section 6): the map $6f000-$6ffff was only ever READ by the cloud passes $de1c/$de6c (static proof + sentinel test in hud_build.md), which hd_stage/hd_clouds remove, so these writes are dead work.
; site: $f9dc
; orig: 45f83a70
; doc: The talking face no longer writes the cloud occupancy map (nothing reads it without the clouds): about 5 k cycles less per speech pass.
        org     $f9dc
        rts
        nop
