; name: tick_click
; default: yes
; site: $7e6
; orig: 0002ed90
; note: (needs tick_head) click lifetime: `$2ed90` is the WORLD clock (the pass counter of the original; the logic stores its low word as an event
;       timestamp and compares it), so a render-only pass must not bump it.  The same counter dates mouse clicks: the VBL handler copies it to `$2ed94`
;       when a button event is latched (`move.l $2ed90.l,$2ed94.l` at $7e4 and $840) and the loop clears the latched click flag $2edb6 at $144b2 when
;       $2ed90 != $2ed94 (a click lives about one pass).  That lifetime must stay one PASS, so the three source operands are redirected to the pass counter
;       PASS = D+32 = $72aa0 that tick_head bumps in every (non-paused) pass.  Operand-only sites: $7e6, $842, $144b4 (master $12f8, $1354, $1373e).
        org     $7e6
        dc.l    $72aa0
