; name: p3c_sim
; default: no
; site: $31570
; orig: 4eb900033bca
; note: P3c second site (work/notes/vehicles_p3b.md; needs p3c_head, which carries the code).  The frame loop calls the player sim `jsr $33bca.l`
;       at $31570; the call becomes `jsr $b8000.l` (hook of p3c_head).  Plain pass (SUB = 0): the original call as a tail call.  PH 1 of an
;       interpolated group: pose before, the original tick, shadow of the end state, then straight to the render path ($3158c) instead of
;       the post-calls $31576.., which run at PH 5.
        org     $31570
        jsr     $b8000.l
