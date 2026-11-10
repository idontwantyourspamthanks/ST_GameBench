; name: p7_triple_wait
; default: yes
; stage: 2
; site: $13090
; orig: 4eb900001870
; data: $db000 16
; note: P7 triple buffering (work/notes/triple.md), part 1 of 3 (needs p7_triple_flip and p7_triple_tail; carries the data block T).
;       `jsr $1870` at $13090 = the main loop's wait for the VBL handler's flag $2df8c before the window copy touches the back buffer
;       (the buffer the previous pass's flip just stopped showing is still scanned, and holds the software pointer, until the VBL).
;       With the 3-buffer flip (p7_triple_flip) the back buffer after a flip is the THIRD buffer, which neither the display nor the
;       pointer uses, so the pass starts at once and the wait moves to the flip (the next flip waits for one VBL since the previous one).
;       OURS (T+2) is set by p7_triple_tail iff the last flip of any kind was p7_triple_flip's (a plain $187a flip of a dialog / menu
;       loop clears it): then no wait.  Otherwise the original wait, unchanged.  Data T ($db000, zeroed at boot): +0 IN.w +2 OURS.w.
T       equ     $db000
tIN     equ     0
tOURS   equ     2
        org     $13090
        jsr     $db200.l

        org     $db200
twait:  tst.w   T+tOURS.l
        bne.s   .no
        jmp     $1870.l                 ; the original wait (its rts returns to the loop)
.no:    rts
