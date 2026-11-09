; name: tick_click
; default: no
; site: $12f8
; orig: 0002df70
; note: P2 (needs tick_head). `$2df70` is the WORLD clock (the pass counter of the original; $3e06 stores its low
;       word as an event timestamp at $3720, $6522 compares it at $65a0), so a render-only pass must not bump it.
;       But the same counter dates mouse clicks: the VBL handler copies it to `$2df74` when a button event is
;       latched (`move.l $2df70.l,$2df74.l` at $12f6 and $1352), and the loop clears the latched click flags
;       `$2df96` at $1373c when `$2df70 != $2df74` (a click lives about one pass). That lifetime must stay one
;       PASS, so the three source operands are redirected to the pass counter PASS = D+32 that tick_head bumps in every
;       (non-paused) pass. Operand-only sites: $12f8, $1354, $1373e (this file carries them as one data-less patch each).
        org     $12f8
        dc.l    $b8a20
