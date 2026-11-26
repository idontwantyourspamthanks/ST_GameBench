; name: p8_det_ring
; default: yes
; site: $16d72
; orig: be7c001067000014
; note: Dynamic terrain ring count in sub_016cf6: compares d7 against RING_LIM ($B7006)
; note: instead of immediate #$10. In HIGH detail RING_LIM=$10 (8 rings, exact original);
; note: MEDIUM=$0c (6 rings), LOW=$0a (5 rings). In-place 8 bytes, zero extra cycles.
        org     $16d72
        cmp.w   $b7006.l,d7
        beq.s   $16d8c
