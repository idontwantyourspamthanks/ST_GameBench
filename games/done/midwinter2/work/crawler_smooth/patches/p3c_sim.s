; name: p3c_sim
; default: yes
; site: $31570
; orig: 4eb900033bca
; note: Second site of p3cp_head (and of the p3c_head alternative; work/notes/vehicles_p3b.md; needs one of them, which carries the code).  The frame loop calls the player sim
;       `jsr $33bca.l` at $31570; the call becomes `jsr $b8000.l` (the hook, first in both heads).  Plain pass or an extra pass: the original call as a tail call.  PH 1 of a
;       predicted group (p3cp_head): it records the pose before the tick, then the original sim and the rest of the original tick follow unchanged.
        org     $31570
        jsr     $b8000.l
