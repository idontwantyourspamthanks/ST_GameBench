; name: p7_triple_wait
; default: yes
; site: $13e04
; orig: 4eb900000e04
; data: $77380 16
; scratch: $b0000 32000
; note: triple buffering (master p7_triple_* / work/notes/triple.md), part 1 of 3 (needs p7_triple_flip and p7_triple_tail; carries the data block T).  Re-sited: master $13090 -> WW1 $13e04.
;       `jsr $e04` at $13e04 = the main loop's wait for the VBL handler's flag $2edac before the window copy touches the back buffer (the buffer the previous pass's flip just stopped showing is still
;       scanned, and holds the software pointer, until the VBL).  With the 3-buffer flip (p7_triple_flip) the back buffer after a flip is the THIRD buffer, which neither the display nor the pointer uses,
;       so the pass starts at once and the wait moves to the flip (the next flip waits for one VBL since the previous one).  OURS (T+2) is set by p7_triple_tail iff the last flip of any kind was
;       p7_triple_flip's (a plain $e0e flip of a dialog / menu loop clears it): then no wait.  Otherwise the original wait, unchanged.  Data T ($77380, zeroed at boot): +0 IN.w +2 OURS.w.
;       The third buffer C = $b0000..$b7cff (32 000 B, 256-aligned; HIGH area of memory_plan.md 3.2, declared `; scratch:`: never initialised, overwritten by the 32 000 B window copy every pass).
T       equ     $77380
tIN     equ     0
tOURS   equ     2
        org     $13e04
        jsr     $77200.l

        org     $77200
twait:  tst.w   T+tOURS.l
        bne.s   .no
        jmp     $e04.l                  ; the original wait (its rts returns to the loop)
.no:    rts
