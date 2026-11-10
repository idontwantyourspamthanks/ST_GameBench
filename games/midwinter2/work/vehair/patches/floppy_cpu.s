; floppy_cpu.s — floppy build only, NOT a patch (no `; site:`): the code mw2patch.py writes into the free zero bytes of FFA's BOOT SECTOR
; (offset $CA..$1FD, 308 bytes) and reaches by replacing the boot sector's final `jmp $4d9a6.l` (6 bytes at $B4) with `bra.w bs_entry` + nop.
; By then the boot sector has loaded the stub (FFA file 1) to $4D9A6; this block runs from TOS's boot-sector buffer (position independent, no
; absolute addresses but the stub's) and then jumps to the stub.  The stub has no room for it (18 free bytes) and runs the FDC with fixed loop
; counts tuned for an 8 MHz 68000 (work/notes/tt.md): its time-out in sub_04ddea ($50000 loops of btst/beq, ~1.5 s at 8 MHz) is ~0.1-0.2 s on a
; 32 MHz 68030 and its "force interrupt" on time-out aborts the read, so the stub loads title pictures / the game from the wrong place.
; On a 68000/68010 this block only runs cl_detect and restores the registers: ST/STE/Mega STE behave as before.  On a 68020+ (TT, Falcon, ...):
; caches off, TT -> ST low resolution, and the stub's FDC waits widened.  The game's own copy of the driver is widened by core.s cpufix.
        org     0
bs_entry:
        movem.l d0-d2/a0-a1,-(a7)
        bsr.w   cl_detect
        tst.b   d0
        beq.s   .go
        bsr.w   cl_cacheoff
        bsr.w   cl_ttres
        lea     st_tab(pc),a0
        bsr.w   cl_patch
.go:    movem.l (a7)+,d0-d2/a0-a1
        jmp     $4d9a6.l

;@CPULIB

; cl_ttres: on a TT (_MCH cookie $0002xxxx) select ST low resolution.  The game never sets the resolution itself (an ST boots in low res); TOS 3.06
; boots a TT in its NVRAM mode (TT medium, 640x480x4, on VGA), where the game's 320-pixel pictures come out as tiled garbage.  $ff8262 is the TT
; shifter mode byte TOS itself writes (Setscreen); 0 = ST low.  No jar / no _MCH / other machine (Falcon = $0003xxxx): nothing.  Trashes d1,d2,a0.
cl_ttres:
        move.l  $5a0.w,d1
        beq.s   .r
        movea.l d1,a0
.k:     move.l  (a0)+,d1
        beq.s   .r
        move.l  (a0)+,d2
        cmp.l   #'_MCH',d1
        bne.s   .k
        swap    d2
        cmp.w   #2,d2
        bne.s   .r
        clr.b   $ffff8262.w
.r:     rts

; {addr.l, size.w, value.l}: the stub's time-out long (was $50000) and its two dbra delays (were $60 in sub_04de26, $100 in sub_04dcf4)
st_tab: dc.l    $4ddf0
        dc.w    4
        dc.l    $00800000
        dc.l    $4de2a
        dc.w    2
        dc.l    $0180
        dc.l    $4dcfe
        dc.w    2
        dc.l    $0400
        dc.l    0
