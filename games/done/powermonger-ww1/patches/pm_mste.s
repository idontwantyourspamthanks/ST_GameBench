; name: pm_mste
; default: yes
; init: $75900
; note: Mega STE 16 MHz + cache (master v1.2, games/done/powermonger/work/notes/mste16.md; game independent, ported verbatim except the address).  A Mega STE starts
;       at 8 MHz: its speed / cache register $ff8e21 resets to 0 (bit 1 = 16 MHz, bit 0 = the 16 KB cache) and nothing in TOS 2.06 or the game writes it.  `init`
;       (supervisor, before the game has run an instruction of its own) writes MSTEVAL = $03 = 16 MHz + CACHE ON, but only when ALL of this holds:
;         1. the _MCH cookie ($5a0 jar) says STE hardware family (high word 1: STE, Mega STE; ST 0, TT 2, Falcon 3; no jar = old TOS: nothing is written),
;         2. a bus-error-guarded byte read of $ff8e21 SUCCEEDS (an STE answers a bus error there: nothing written, `$8` restored),
;         3. the register still holds its reset value 0.  Non-zero = somebody already chose: left alone.
;       The core's init loop keeps its table pointer in a2 across the calls: this routine saves and restores every register it uses.  Nothing is stored in RAM.
MSTEVAL equ     3
        org     $75900
init:   movem.l d0-d1/a0-a2,-(a7)
        move.l  $5a0.w,d0
        beq.s   .r                      ; no cookie jar: TOS 1.0x, not a Mega STE
        movea.l d0,a0
.l:     move.l  (a0)+,d0
        beq.s   .r
        move.l  (a0)+,d1
        cmpi.l  #'_MCH',d0
        bne.s   .l
        swap    d1
        cmpi.w  #1,d1                   ; STE hardware family only
        bne.s   .r
        movea.l a7,a2                   ; the bus error handler resets the stack here (the saved registers on top)
        movea.l $8.w,a1
        lea     .berr(pc),a0
        move.l  a0,$8.w
        move.b  $ffff8e21.w,d0          ; bus error on an STE
        move.l  a1,$8.w                 ; the read answered: restore the vector
        tst.b   d0
        bne.s   .r                      ; already set (speed and / or cache): keep it
        move.b  #MSTEVAL,$ffff8e21.w    ; 16 MHz + cache (one-byte constant: $02 = 16 MHz without cache)
.r:     movem.l (a7)+,d0-d1/a0-a2
        rts
.berr:  movea.l a2,a7
        move.l  a1,$8.w
        bra.s   .r
