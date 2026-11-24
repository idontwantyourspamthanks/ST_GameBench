; name: hd_kbd
; default: no
; mandatory: yes
; site: $e78
; orig: 102900024a390001d2ae
; note: HD build (see hd_core.s).  A verification-only site: the bytes are written back unchanged.  hd_core.s hands the keyboard / mouse bytes that arrived during a GEMDOS call to the game's own byte processor at $e7c (the game's ACIA handler $e52 reads the byte, `bsr $e78` = `move.b 2(a1),d0` + the packet state machine from $e7c on, which only needs d0 = the byte).  If those bytes were different the build's mandatory group would refuse and the HD game would not start, instead of jumping into the middle of something else.
        org     $e78
        move.b  2(a1),d0
        tst.b   $1d2ae.l
