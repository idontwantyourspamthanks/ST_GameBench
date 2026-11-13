; name: pop_tt_ptr2
; default: yes
; prog: populous
; machine: tt, falcon
; site: $16d66
; orig: 6c0642790001 6d26 4e75
; note: TT / Falcon only, part 2 of 2 of the pointer fix (pop_tt_ptr is the flip; work/notes/tt_pointer.md).  The routines that draw into the displayed buffer hide the pointer around their
;       drawing: `$16d2e` (hide: count $16d26 + 1; the outermost call restores the saved background and clears $16f12) ... `$16d5e` (show: count - 1, clamped at 0; it draws nothing, the next VBL
;       routine does).  The map's hover marker (`$11c9e` ... `$11cc6`, once per pass), the text printer `$180fc` / `$181c8`, the pause icon and the dialog code use them.  On an ST the next VBL routine
;       comes within a frame and the pass is several frames long, so the pointer is back at once (an STE: the arrow is drawn beside the cross over the map in 84 % of the VBLs, work/gates/ttptr_ste_map.txt).
;       A TT runs a pass per frame: the hide comes right after the flip, the VBL routine that would redraw the pointer comes after the NEXT flip, which has put the other buffer on the screen,
;       so over the map the arrow was never in the displayed buffer for more than a few scan lines (0 of 118 frames with pop_tt_ptr alone).
;       The blob (`jmp` over the clamp and the `rts` of `$16d5e`; CCR from the `subi.w` at `$16d5e` is still valid) finishes the show, and when the count is back at 0 runs the VBL routine's own
;       restore + draw (`$16dea` is a no-op after the outermost hide cleared `$16f12`; after an unbalanced show it removes the old image first, so there is never a second pointer) into the
;       displayed buffer at the VBL routine's interrupt level.  The next VBL routine and the flip (pop_tt_ptr) restore and redraw as usual.  A nested show (count still > 0) and a show while the
;       pointer is hidden by a dialog (name entry: count 1 for the whole entry) draw nothing.  Cost: one restore + draw per hide/show pair (about 12 k cycles: 0.4 ms at 32 MHz).
        org     $16d66
        jmp     $b8040.l

        org     $b8040
tts:    bge.s   .l                      ; flags of the `subi.w #1,$16d26.l` at $16d5e
        clr.w   $16d26.l                ; clamp at 0, as the original
.l:     tst.w   $16d26.l
        bne.s   .out                    ; still hidden (nested hide, or the game's own hide count)
        movem.l d0-d7/a0-a6,-(a7)
        move.w  sr,-(a7)
        ori.w   #$0400,sr
        jsr     $16dea.l
        jsr     $16e20.l
        move.w  (a7)+,sr
        movem.l (a7)+,d0-d7/a0-a6
.out:   rts
