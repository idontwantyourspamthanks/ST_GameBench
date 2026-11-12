; name: test_delay
; default: no
; stage: 2
; site: $1390
; orig: 20390001c49a
; note: test only (tools/pmab.py robustness control, never shipped): burns cycles in the VBL handler's pointer code (at
;       `move.l $1c49a.l,d0`) at every VBL, nothing else: a run with different interrupt timing.
        org     $1390
        jsr     $ce200.l

        org     $ce200
        move.w  #60,d0
.l:     dbra    d0,.l
        move.l  $1c49a.l,d0             ; the displaced instruction
        rts
