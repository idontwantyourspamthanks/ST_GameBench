; name: pop_tt_ptr
; default: yes
; prog: populous
; machine: tt, falcon
; site: $16f32
; orig: e04823c0ffff8200
; note: TT / Falcon only: the mouse pointer is invisible on a TT (in play, every frame) and flickers on a Falcon (work/notes/tt_pointer.md has the evidence and the gates).
;       The pointer is drawn by the VBL routine $16d70 (restore $16dea, draw $16e20) into the DISPLAYED buffer $3c50c.  The flip $16f16 (`bsr.w $16f48` waits for the flag the
;       VBL routine sets at its end, so the flip runs right after the draw when a pass is short) swaps $3c50c / $3c510 (016f1a-016f2c) and writes the new base
;       (`016f32 lsr.w #8,d0` / `016f34 move.l d0,$ffff8200.l`).  An ST / STE latches the base at the next frame start, so the buffer the routine drew into is the one shown in
;       that frame.  Hatari's TT and Falcon video take the new base at once: every frame shows the buffer that has no pointer yet (the next VBL routine draws it there, after the
;       next flip has already gone back).  A game that flips on every VBL (a TT: always) never shows the pointer; a Falcon, with passes of about one frame, shows it in a third of the frames.
;       The site is the base write (8 bytes: `jsr` + `nop`; d0 = the buffer about to be shown, the swap is done).  Unless the pointer is hidden ($16d26, the VBL routine's own test
;       at 016d78) the blob runs the game's own routines at the VBL routine's interrupt level, kept up to and including the base write: restore the saved background into the buffer
;       being left ($16dea, via $16f12), draw the pointer into the new one ($16e20, via $3c50c; it records $16f12 / $2498c / $2498e / $2478c as the VBL routine would), then the
;       displaced `lsr.w #8,d0` / `move.l d0,$ffff8200.l`.  The pointer is in the buffer before the video is switched to it, and a VBL that falls due during the draw (a Falcon:
;       0.8 ms of a 16.7 ms frame) is served after the base write, not between the draw and the write (that left one frame without a pointer in 1 % of the frames).
;       The next VBL routine restores and redraws in the same buffer, as before.  The restore into the left buffer is the one the VBL routine used to do after the flip; it now
;       happens before the main loop re-renders that buffer.  Cost: one restore + draw per flip (about 12 k cycles: 0.4 ms at 32 MHz, 0.8 ms at 16 MHz).  pop_ptr is independent
;       (its skip compares $16f12, $3c50c, the rectangle and the shape against what its own last draw left; a draw by this blob never matches a record it did not write).
;       The site is skipped on an ST / STE / Mega STE (machine mask), whose game text stays byte-identical.
        org     $16f32
        jsr     $b8000.l
        nop

        org     $b8000
ttp:    tst.w   $16d26.l                ; pointer hidden: the VBL routine skips restore + draw
        bne.s   .base
        move.w  sr,-(a7)
        ori.w   #$0400,sr               ; the VBL routine's own level, kept up to and including the base write
        movem.l d0-d7/a0-a6,-(a7)
        jsr     $16dea.l                ; restore into the buffer being left
        jsr     $16e20.l                ; draw into the buffer about to be shown
        movem.l (a7)+,d0-d7/a0-a6
        lsr.w   #8,d0                   ; the displaced instructions: the new base
        move.l  d0,$ffff8200.l
        move.w  (a7)+,sr                ; a VBL that came due during the draw runs now, after the base write
        rts
.base:  lsr.w   #8,d0
        move.l  d0,$ffff8200.l
        rts
