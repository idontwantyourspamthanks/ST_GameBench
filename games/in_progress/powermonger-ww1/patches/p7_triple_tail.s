; name: p7_triple_tail
; default: yes
; site: $e2c
; orig: 33fc00000002edac
; note: triple buffering (master p7_triple_tail / triple.md), part 3 of 3 (needs p7_triple_wait: data block T).  Re-sited: master $1898 -> WW1 $e2c.
;       `move.w #0,$2edac.l` = the last action of the plain flip $e0e (clear the VBL flag), run by EVERY caller of the flip: the main loop (through p7_triple_flip, IN = 1) and the dialog / menu / modal
;       loops (plain, IN = 0).  The hook records who flipped last: OURS := IN, IN := 0.  p7_triple_wait reads OURS.  (A plain flip anywhere leaves the three-buffer state: the first main-loop pass after
;       it waits as the original did.)
T       equ     $77380
tIN     equ     0
tOURS   equ     2
        org     $e2c
        jsr     $77300.l                ; 6 bytes; wwpatch pads the remaining 2 with a nop, the rts at $e34 stays

        org     $77300
ttail:  clr.w   $2edac.l
        move.w  T+tIN.l,T+tOURS.l
        clr.w   T+tIN.l
        rts
