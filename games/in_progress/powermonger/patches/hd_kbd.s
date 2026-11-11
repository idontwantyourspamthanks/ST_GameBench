; name: hd_kbd
; default: no
; mandatory: yes
; stage: 2
; site: $18e4
; orig: 102900024a390001c48e
; note: HD build (see hd_core.s).  A verification-only site: the bytes are written back unchanged.  hd_core.s hands the
;       keyboard / mouse bytes that arrived during a GEMDOS call to the game's own byte processor at $18e8 (the game's ACIA
;       handler $18be reads the byte, `bsr $18e4` = `move.b 2(a1),d0` + the packet state machine from $18e8 on, which only
;       needs d0 = the byte).  If those bytes were different the build's mandatory group would refuse and the HD game would
;       not start, instead of jumping into the middle of something else.
        org     $18e4
        move.b  2(a1),d0
        tst.b   $1c48e.l
