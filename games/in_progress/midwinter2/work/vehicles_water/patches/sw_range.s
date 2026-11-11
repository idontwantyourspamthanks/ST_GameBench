; name: sw_range
; default: no
; site: $33bf8
; orig: 4eb90003489a
; note: ANALYST SCRATCH: sub_03489a (terrain/range probe of the position at the START of the pass: $66e4, $6774)
;       runs only on the first pass of a masked type's group (HOLD = 0), so the group end carries the value of the
;       original tick (computed from the tick-start position).
        org     $33bf8
        jsr     $b4e80.l

        org     $b4e80
        tst.w   $b42ea.l                ; HOLD
        bne.s   .skip
        jmp     $3489a.l
.skip:  rts
