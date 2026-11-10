; name: p4_walk_ret
; default: yes
; site: $3d316
; note: Shared tail of the unrolled body (`movem.l (a7)+,d0-d7/a0-a6; rts` at $3d314):
;       restore only the registers p4_walk saved (d2-d3/d5-d7/a0-a1/a3 = $0BEC).
        org     $3d316
        dc.w    $0bec
