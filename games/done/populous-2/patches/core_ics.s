; core_ics.s - the trampoline of the ICS floppy build (`pop2patch.py build --base ics`), the counterpart of core.s.
; Assembled at CORE; MARKER, CORE and TABLE are supplied by the tool (`full` layout: CORE = PB = $80000, TABLE = PB+$7000;
; `lowram` layout: inside $7b400-$7fff7, work/notes/ics.md).
;   The floppy's POP2.TOS (the crack's loader, our prefix in front of it) has unpacked the game to $1770 and ends `jmp $140.w`.
;   The ICS crack installed there `move.l #$4e714e71,$14a88.l` + `jmp $1770.w` (its AUTO\ICS.PRG did): the manual question's
;   `cmp.w d1,d2` is followed by two nops, so any answer passes.  Our prefix installs `jmp CORE.l` at $140 instead (AUTO\ICS.PRG is
;   not on our disk), and this trampoline does the crack's own store, then VERIFIES every site's original bytes (pass 1), APPLIES all
;   of them only if every site matched (pass 2) and writes 'P2PO' (all applied) or 'P2PF' (a mismatch: nothing applied) to MARKER,
;   then `jmp $1770.w`, the game entry, exactly as the crack's stub did.
;   Site table: entries {addr.l len.w rsv.w orig.l new.l}, addr 0 ends; then the orig/new byte pool (the same format as core.s).
        org     CORE
trampoline:
        move.l  #$4e714e71,$14a88.l     ; the crack's stub: two nops after `cmp.w d1,d2` at $14a86
        movem.l d0-d7/a0-a6,-(a7)
        move.w  sr,-(a7)                ; keep flags/mode exactly as the unpacker left them
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
        jmp     $1770.w                 ; the game entry
