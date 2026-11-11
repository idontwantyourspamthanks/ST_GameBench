; name: qol_keys2
; default: yes
; stage: 2
; site: $199c
; orig: 13c00001c490
; note: the interrupt half of qol_keys (see there; harmless without it: it only writes PEND bytes).  $199c is the make-code path of the game's
;       ACIA keyboard handler $18be (`st.b (a0,d0.w)` just stored the key in the table $2de6c, d0 = the scan code, 0 for a break):
;       `move.b d0,$1c490` (the game's "last key" byte) becomes `jsr KH`; KH does that same move, and for a make code sets
;       PEND[scancode] = 1 (+ 2 when Shift is down, $2df8a) in qol_keys' data block.  qol_keys consumes PEND once per pass, so a tap shorter
;       than a pass is not lost.  The handler already saved d0-d2/a0-a1 ($18be) and pushed a0 again ($1962): d0, d1, a0 are free here.
PEND    equ     $cd4a4
ANY     equ     $cd4a2

        org     $199c
        jsr     $cd530.l

        org     $cd530
kh:     move.b  d0,$1c490.l             ; the displaced instruction
        tst.b   d0
        beq.s   .r                      ; a break code (d0 was cleared)
        lea     PEND.l,a0
        moveq   #1,d1
        tst.w   $2df8a.l                ; Shift down?
        beq.s   .s
        moveq   #3,d1
.s:     move.b  d1,(a0,d0.w)
        move.w  #1,ANY.l                ; after PEND: the pass hook scans only when this is set
.r:     rts
