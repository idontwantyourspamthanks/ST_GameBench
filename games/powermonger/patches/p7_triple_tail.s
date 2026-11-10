; name: p7_triple_tail
; default: no
; stage: 2
; site: $1898
; orig: 33fc00000002df8c
; note: P7 triple buffering (work/notes/triple.md), part 3 of 3 (needs p7_triple_wait: data block T).
;       `move.w #0,$2df8c.l` = the last action of the plain flip $187a (clear the VBL flag), run by EVERY caller of the flip: the main loop
;       (through p7_triple_flip, IN = 1) and the dialog / menu / modal loops (plain, IN = 0).  The hook records who flipped last:
;       OURS := IN, IN := 0.  p7_triple_wait reads OURS.  (A plain flip anywhere leaves the three-buffer state: the first main-loop pass
;       after it waits as the original did.)
T       equ     $db000
tIN     equ     0
tOURS   equ     2
        org     $1898
        jsr     $db300.l                ; 6 bytes; pmpatch pads the remaining 2 with a nop, the rts at $18a0 stays

        org     $db300
ttail:  clr.w   $2df8c.l
        move.w  T+tIN.l,T+tOURS.l
        clr.w   T+tIN.l
        rts
