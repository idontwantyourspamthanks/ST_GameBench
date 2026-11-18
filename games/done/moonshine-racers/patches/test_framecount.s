; name: test_framecount
; default: no
; site: $d1ca
; orig: 2038100822381004
; data: $B2FF4 4
; note: Measurement instrument (README.md "Test patches"): increments the long at $B2FF4 once per presented frame (the flip routine $d1ca) and replays
; note: the two instructions it displaced, so the picture is untouched.  Compare its rate (one per frame = `tools/msrbench.py` flips) and use it for A/B
; note: work on a snapshot through `msrpatch.py live` (no boot needed: the site is in the frame loop).
; note: Site: $d1ca `move.l $1008.w,d0 / move.l $1004.w,d1` (8 B, rendering.md section 2: flip) -> 6-byte `jmp $B2900.l` + nop; the blob replays both
; note: moves and jumps to $d1d2.
        org     $d1ca
        jmp     $B2900.l
        nop

        org     $B2900
        addq.l  #1,$B2FF4.l
        move.l  $1008.w,d0
        move.l  $1004.w,d1
        jmp     $d1d2.l
