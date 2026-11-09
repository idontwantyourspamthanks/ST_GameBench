; name: hd_sector
; default: no
; mandatory: yes
; stage: 2
; site: $d9fc
; orig: 48e778c04e56
; note: HD build (see hd_core.s).  sub_00d9fc is the game's sector driver (d1 = first sector, d2 = count, d3.b = mode
;       0 read / 1 write / 2 format, a0 = buffer; d0 = 0 / Z ok).  With $d574 replaced its only users are the save-game
;       disk routines $1ba72 $1bd52 $1bd70 $1bdfe.  The first 6 bytes (movem.l d1-d4/a0-a1,-(a7); the opcode of
;       link.w a6,#$ffe2) become a jump to hd_sector; its operand word is never reached.
        org     $d9fc
        jmp     $bb00c.l
