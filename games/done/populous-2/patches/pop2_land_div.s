; name: pop2_land_div
; default: yes
; site: $25172
; orig: 200804800003ff1a80fc0034
; note: Exact algebraic replacement for `divu.w #$34,d0` at $2517a (111 calls/frame, ~1.3% of busy1).
;       The caller immediately masks `andi.w #$3,d0` ($2517e) to stagger land-score scans across 4 turns.
;       Because every people record is at offset 52*k = 4*13*k and 13 === 1 (mod 4),
;       ((52*k) >> 2) & 3 === (13*k) & 3 === k & 3 for every record k = 0..399!
;       Replaces a 140-cycle divu.w with an 8-cycle lsr.w #2,d0 in place (zero blob needed).

        org     $25172
        move.l  a0,d0
        subi.l  #$3ff1a,d0
        lsr.w   #2,d0
        nop
