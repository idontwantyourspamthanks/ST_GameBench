; name: test_tblock
; default: no
; site: $5fa4
; orig: 3b6d01aa01ac
; note: GATE ONLY, not for the release.  The frame's elapsed-VBL latch `move.w $1aa(a5),$1ac(a5)` becomes a constant 15, so
;       BOTH runs of an A/B test advance the world by the same number of VBLs per frame.  Without it, triple buffering makes
;       frames a different number of VBLs long (the movement and NPC code multiply by $1ac), so the two runs legitimately
;       diverge after the first frame and no per-frame pixel comparison is possible (the same reason huntab needs --lock).
;       The three tb_ sites are the only code difference between the runs.
        org     $5fa4
        move.w  #$000f,$1ac(a5)
