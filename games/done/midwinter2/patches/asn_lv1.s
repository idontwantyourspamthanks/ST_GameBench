; name: asn_lv1
; default: no
; site: $18e72
; orig: 33fc000700019218
; phase: deferred
; note: Level constant of the ST code for the on-foot / low-route case (`move.w #7,$19218.l`; the Amiga's `$2f1f4` writes 9): with asn_core's DMA driver
; note: active (SV+0 = 2) the Amiga value 9, else the original 7.  See asn_lvc.
        org     $18e72
        jsr     $bf812.l
        nop
