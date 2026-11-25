; name: test_nowait
; default: no
; site: $13e04
; orig: 4eb900000e04
; note: TEST ONLY (negative control of the tearing trace tools/wwtriple.py, never shipped; master test_nowait re-sited): the main loop's wait for the VBL handler's flag before the window copy is removed
;       (`jsr $e04` -> three nops) in the ORIGINAL double-buffer flip: the pass draws into the buffer that is still scanned and holds the pointer, so the trace must report violations.
        org     $13e04
        nop
        nop
        nop
