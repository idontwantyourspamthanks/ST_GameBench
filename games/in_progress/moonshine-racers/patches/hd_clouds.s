; name: hd_clouds
; default: yes
; site: $7b3a
; orig: 4eb90000dd50
; doc: The clouds are gone: the cloud position update $dd50 (and, with hd_stage, the cloud erase/draw $de1c/$de6c) no longer runs; the sky stays plain.
; note: New HUD (work/notes/hud_build.md).  Site $7b3a `jsr $dd50.l` (cloud slot x/y update, writes only the 12 cloud slots $29c8-$2c67 and the counters $27de-$27e5) -> three nops.  Nothing reads those words once hd_stage no longer calls $de1c/$de6c.
        org     $7b3a
        nop
        nop
        nop
