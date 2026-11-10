; name: test_nowait
; default: no
; stage: 2
; site: $13090
; orig: 4eb900001870
; note: NEGATIVE CONTROL for tools/pmtriple.py trace (work/notes/triple.md): the main loop's VBL wait removed on the plain double buffer
;       (3 nops).  The next pass then draws into the buffer that is still scanned and holds the pointer: the trace must report violations.
;       Conflicts with p7_triple_wait (same site).  Never part of a build.
        org     $13090
        nop
        nop
        nop
