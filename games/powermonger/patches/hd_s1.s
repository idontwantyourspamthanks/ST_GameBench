; name: hd_s1
; default: no
; mandatory: yes
; stage: 1
; site: $1356
; orig: 4eb900057032
; note: HD build (see hd_core.s).  Stage 1 (the intro) loads DATA\SPRITE40.DAT, i.e. the game proper, with its copy of the
;       by-name FAT12 loader at $57032 (a0 = a1 = the file name at $13ba, which the load overwrites): the only call.
        org     $1356
        jsr     $bb008.l
