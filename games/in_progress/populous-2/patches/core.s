; core.s - Populous 2 patch delivery mechanism (always installed by pop2patch.py).
; Assembled at PB (the payload base, supplied by the tool as `PB equ ...`; see README.md).
;   PB+$0000 trampoline: entered by the `jmp` that replaces PP's patcher tail in RUNME's stack-phase
;            block (text $3da: `move.l #$1c42,$118.w` + `jmp $1770.w`, the game has just been
;            unpacked to $1770).  Replays the displaced `move.l #$1c42,$118.w`, then VERIFIES every site's
;            original bytes (pass 1), APPLIES all of them only if every site matched (pass 2) and
;            writes 'P2PO' (all applied) or 'P2PF' (a mismatch: nothing was applied) to MARKER.
;            It ends with the game entry `jmp $1770.w`, exactly as PP's tail did.
;   Site table PB+$7000..PB+$7FFF: entries {addr.l len.w rsv.w orig.l new.l}, addr 0 ends; then the
;            orig/new byte pool.
MARKER  equ PB-8
TABLE   equ PB+$7000

        org     PB
trampoline:
        move.l  #$1c42,$118.w           ; PP's displaced instruction
        movem.l d0-d7/a0-a6,-(a7)
        move.w  sr,-(a7)                ; keep flags/mode exactly as PP's tail left them
        move.l  #'P2PF',MARKER.l        ; preset failure marker
        lea     TABLE.l,a0
.v1:    move.l  (a0)+,d0                ; pass 1: verify; addr 0 = end of table
        beq.s   .apply
        move.w  (a0)+,d1                ; length
        addq.l  #2,a0                   ; reserved
        movea.l (a0)+,a1                ; orig bytes
        addq.l  #4,a0                   ; new bytes (pass 2)
        movea.l d0,a3
        subq.w  #1,d1
.vc:    cmpm.b  (a1)+,(a3)+
        dbne    d1,.vc
        beq.s   .v1                     ; whole site matched
        bra.s   .done                   ; mismatch: apply nothing, keep 'P2PF'
.apply: lea     TABLE.l,a0
.a1:    move.l  (a0)+,d0                ; pass 2: apply every site
        beq.s   .ok
        move.w  (a0)+,d1
        addq.l  #2,a0
        addq.l  #4,a0                   ; orig bytes
        movea.l (a0)+,a2                ; new bytes
        movea.l d0,a3
        subq.w  #1,d1
.aw:    move.b  (a2)+,(a3)+
        dbra    d1,.aw
        bra.s   .a1
.ok:    move.l  #'P2PO',MARKER.l
.done:  move.w  (a7)+,sr
        movem.l (a7)+,d0-d7/a0-a6
        jmp     $1770.w                 ; PP's game entry
