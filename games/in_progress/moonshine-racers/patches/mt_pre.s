; name: mt_pre
; default: yes
; site: $7b0a
; orig: 4eb900017c42
; requires: mt_clock                              ; the guard waits on PEND (set by the pacer mg_sync/mg_pace, mx_sync or mt_sync, cleared by mt_clock's VBL code); alone it never waits
; doc: Fixed real-time game tick, part 3 of 3: a latch guard before the first write into the back buffer (the flipped buffer must be on screen first).
; note: Fixed tick, part 3 of 3.  Site: $7b0a `jsr $17c42.l` (first write into the new back buffer, 0.78 VBL after the flip) -> `jsr $B8200.l`.
; note: If a flip is still pending (PEND, cleared by the VBL in mt_clock) wait for it, then continue into $17c42 (a tail jump: it returns to $7b10).
PEND    equ     $B8F08
        org     $7b0a
        jsr     $B8200.l

        org     $B8200
pre17c42:
        tst.b   PEND.l
        beq.s   .go                     ; the flipped buffer is already on screen
.w:     tst.b   PEND.l                  ; else wait for the VBL that latches it
        bne.s   .w
.go:    jmp     $17c42.l
