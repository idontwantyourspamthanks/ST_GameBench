; name: hd_load
; default: no
; mandatory: yes
; stage: 2
; site: $d574
; orig: 48e77ff82848
; note: HD build (see hd_core.s).  sub_00d574 is the game's by-name loader (a0 = "DATA\X.DAT", a1 = destination; d0 = 0
;       and Z set when loaded, else an error code), called by the resource loader $d4d2 and $1bd28/$1bd46.
;       The first two instructions (movem.l d1-d7/a0-a4,-(a7); movea.l a0,a4) become a jump to hd_load, which returns
;       to the caller itself.
        org     $d574
        jmp     $bb008.l
