; name: asn_lv2
; default: yes
; site: $18ea0
; orig: 33fc000700019218
; phase: deferred
; note: Second level constant (see asn_lv1): `move.w #7,$19218.l` -> 9 with asn_core's DMA driver active.
        org     $18ea0
        jsr     $bf818.l
        nop
