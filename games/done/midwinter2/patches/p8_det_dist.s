; name: p8_det_dist
; default: yes
; site: $2029e
; orig: 33fc0a9000018772
; phase: deferred
; note: Dynamic terrain draw distance cutoff in sub_02029a: loads DIST_CUT ($B9106) into $18772.l
; note: ($0a90 HIGH exact, $0900 MEDIUM drops band 3, $0790 LOW drops bands 2+3).
        org     $2029e
        jsr     $b9940.l
        nop

        org     $b9940
        move.w  $b9106.l,$18772.l
        rts
