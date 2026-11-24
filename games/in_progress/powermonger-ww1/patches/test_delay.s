; name: test_delay
; default: no
; site: $87e
; orig: 20390001d2ba
; note: TEST ONLY (tools/wwab.py robustness control, never shipped; master test_delay re-sited): burns cycles in the VBL handler's pointer code (at `move.l $1d2ba.l,d0`) at every VBL, nothing else: a run with
;       different interrupt timing.  `wwab.py --only test_delay` shows which frames depend on the pass / VBL phase alone (they differ with no real change in the code).
        org     $87e
        jsr     $77d00.l

        org     $77d00
        move.w  #1500,d0
.l:     dbra    d0,.l
        move.l  $1d2ba.l,d0             ; the displaced instruction
        rts
