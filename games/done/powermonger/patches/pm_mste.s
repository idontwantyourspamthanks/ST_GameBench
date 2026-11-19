; name: pm_mste
; default: yes
; init: $dc200
; note: Mega STE 16 MHz + cache (v1.2, work/notes/mste16.md).  A Mega STE starts at 8 MHz: its speed / cache register $ff8e21 resets to 0 (bit 1 = 16 MHz,
;       bit 0 = the 16 KB cache) and nothing in TOS 2.06, HDDRIVER or the game writes it, so the patched game ran at 4.5 fps there.  `init`
;       (supervisor, before the game has run an instruction of its own; floppy and HD builds alike) writes MSTEVAL = $03 = 16 MHz + CACHE ON
;       (measured in Hatari 2.6.1: 16 MHz without the cache is only +12 %, 4.50 -> 5.04 fps, because RAM accesses wait for the 8 MHz bus;
;       with the cache 8.1 fps; the cache is unproven on real hardware: DMA-written code, self-modifying code), but only when ALL of this holds:
;         1. the _MCH cookie ($5a0 jar) says STE hardware family (high word 1: STE, Mega STE; ST 0, TT 2, Falcon 3, no jar = old TOS: nothing is written),
;         2. a bus-error-guarded byte read of $ff8e21 SUCCEEDS (an STE answers a bus error there: nothing written, `$8` restored),
;         3. the register still holds its reset value 0.  Non-zero = somebody (the user's control panel / AUTO program) already chose: left alone.
;       A user's explicit 8 MHz is the same 0 and cannot be told from "not set yet": it is raised to 16 MHz as well.
;       The core's init loop keeps its table pointer in a2 across the calls: this routine saves and restores every register it uses.  Nothing is stored in RAM.
MSTEVAL equ     3
        org     $dc200
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
