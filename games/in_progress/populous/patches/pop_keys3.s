; name: pop_keys3
; default: no
; prog: populous
; site: $200a6
; orig: 2f08428010390002005f
; note: Typed-text guard for pop_keys (PopUI).  `$200a6` converts the last key press ($2005f) to ASCII ($37ef8); the main loop calls it at
; note: $b946 (return address $b94c), and every text input of the game polls it in its own loop: the name / file entry `$18a20`, the dialog
; note: `$1f3f6`, the line editors `$1fe96` / `$1ff62`.  A poll from anywhere but the main loop means text is being typed, so the hook
; note: empties pop_keys' ring (head := tail) and drops the Armageddon arm: letters typed into a dialog or the save requester can never
; note: become icon clicks later (the key recorder pop_keys2 records them in the interrupt, before anybody knows who will read them).
; note: Change: the first three instructions (`move.l a0,-(a7)` / `clr.l d0` / `move.b $2005f.l,d0`, 10 bytes) are replaced by a jmp to this
; note: blob, which runs them after its check and continues at $200b0.  Does nothing unless pop_keys' hook is in place.
KD      equ     $c8000
        org     $200a6
        jmp     $c7380.l
        nop
        nop

        org     $c7380
th:     cmpi.w  #$4eb9,$0bb7c.l         ; pop_keys installed?
        bne.s   .go
        cmpi.l  #$0b94c,(sp)            ; the main loop's own poll: not text
        beq.s   .go
        move.b  KD+11.l,KD+10.l         ; head := tail
        clr.l   KD+4.l
.go:    move.l  a0,-(a7)                ; the displaced instructions
        clr.l   d0
        move.b  $2005f.l,d0
        jmp     $0200b0.l
