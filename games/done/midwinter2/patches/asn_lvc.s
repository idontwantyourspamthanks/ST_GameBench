; name: asn_lvc
; default: yes
; site: $18ed8
; orig: 3c3c00013e3c00074eb84f8a
; phase: deferred
; note: Engine level clamp of the ST code `$18ed8-$18ee3` (`move.w #1,d6 / move.w #7,d7 / jsr $4f8a.w`): the ST clamps 7 - x to 1..7, the AMIGA code
; note: ($2f260 `move.w #2,d6 / move.w #9,d7 / jsr $5e208`) to 2..9.  asn_core's engine period is `base + scale * level` as on the Amiga, so with the
; note: DMA driver active (asn_core mode 2: SV+0) the clamp is 2..9; otherwise the original 1..7.  The tail `jmp $4f8a.w` returns to the site.
        org     $18ed8
        jsr     $bf80c.l
        nop
        nop
        nop
