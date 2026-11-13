; name: pop2_fdc_delay
; default: yes
; base: ics
; site: $37a96
; orig: 538066fc4e75
; data: PB+$6fb0 1
; note: ICS floppy build only (`pop2patch.py build --base ics`; PP's build has no use for the game's own FDC driver).  The game's raw WD1772 driver ($375e0-$37aa3, the crack family's floppy layer) spaces every FDC
; note: register access with ONE delay routine, $37a96: `subq.l #1,d0 / bne.b $37a96 / rts`; $37a88 calls it with d0 = $18 (24 iterations = 432 cycles = 54 us on a 68000 at 8 MHz) behind every write
; note: and read of $ff8604/$ff8606, the motor-off wait uses $c3500, and the seek/verify code waits ~1 ms with it.  Written for an 8 MHz ST: on a 68030 at 32 MHz (the TT) the same loop is about
; note: 20-40 times shorter than the WD1772 needs, the driver reads garbage and the game shows its own "INSERT POPULOUS-II DISK" requester forever (Hatari TT 32 MHz: work/notes/ics.md; the same machine at
; note: --cpuclock 8 plays, the Falcon at 16 MHz plays, the Mega STE plays).  Fix: on a 68020+ the loop's time must not depend on the CPU clock or on the instruction cache, so each iteration does a
; note: dummy read of the MFP's GPIP (a bus cycle on the ST I/O bus: its length is the same on a TT/Falcon as on an ST) and the count is multiplied by 6; on a 68000/68010 the original loop runs unchanged.
; note: CPU class: the index-register scale test (68020+ honours `(d0.w*2)`), once, kept in a byte at PB+$6fb0 (0 unprobed, 1 = 68000/68010, 2 = 68020+), as pop2_tt_ptr does.
; note: Registers: the original touches only d0 and leaves it 0 with Z set; so does this.
FD_F    equ     PB+$6fb0
FDD     equ     PB+$6c00
        org     $37a96
        jmp     FDD.l

        org     PB+$6c00
fdd:    tst.b   FD_F.l
        bne.s   .k
        movem.l d0-d2/a0-a1,-(a7)
        moveq   #1,d0
        dc.w    $41fb,$0200                     ; lea     (0,pc,d0.w*2),a0
        dc.w    $43fb,$0000                     ; lea     (0,pc,d0.w),a1  (4 bytes behind the first: a1-a0 = 4 when the scale is ignored, 3 with scale 2)
        suba.l  a0,a1
        move.l  a1,d1
        moveq   #1,d2                           ; 1 = 68000 / 68010
        cmp.l   #4,d1
        beq.s   .set
        moveq   #2,d2                           ; 2 = 68020+
.set:   move.b  d2,FD_F.l
        movem.l (a7)+,d0-d2/a0-a1
.k:     cmpi.b  #2,FD_F.l
        beq.s   .fast
.l:     subq.l  #1,d0
        bne.s   .l
        rts
.fast:  move.l  d1,-(a7)
        move.l  d0,d1
        lsl.l   #7,d0
        move.l  d0,d1
        move.l  (a7)+,d1
.f:     tst.b   $fffffa01.w                     ; one I/O bus cycle per iteration (the clock-independent part of the delay)
        subq.l  #1,d0
        bne.s   .f
        rts
