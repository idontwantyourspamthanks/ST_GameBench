; name: hd_nomap2
; default: yes
; requires: hd_stage hd_clouds hd_nomap
; site: $120d6
; orig: 47f90006f000
; doc: The message ticker's glyph draw no longer writes the cloud occupancy map (dead work without the clouds).
; note: Second occupancy-map writer bypass (see hd_nomap): $120d6 `lea $6f000.l,a3` (the map pointer for the mask kernel $1237c that glyph draw $120a4 tail-jumps to) -> `rts / nop / nop`.  The box erase $12086 -> $1242c (35 k per message end) writes the map inside its shared loop and is NOT touched.
        org     $120d6
        rts
        nop
        nop
