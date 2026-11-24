; name: hd_load
; default: no
; mandatory: yes
; site: $d962
; orig: 48e77ff82848
; note: HD build (see hd_core.s).  sub_00d962 is the game's by-name loader (a0 = "FX.PAK", a1 = destination; d0 = 0 and Z set when loaded, else an error code), called by the resource loader and the key-disk-free load paths.  The first two instructions (movem.l d1-d7/a0-a4,-(a7); movea.l a0,a4) become a jump to hd_load, which returns to the caller itself.
        org     $d962
        jmp     $77408.l
