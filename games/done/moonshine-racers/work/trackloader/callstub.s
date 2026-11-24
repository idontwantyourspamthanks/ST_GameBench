; callstub.s -- scratch: debugger-driven call of trk_read ($100000) from a Hatari breakpoint.  The driver sets PC to `stub` at a breakpoint on the game's
; flip routine $d1ca (not yet executed), so the stub restores everything and jumps back to $d1ca.
; params at $100500: +0 dest.l  +4 max.l  +8 path (NUL);  results at $100600: d0.l d1.l, SR-at-entry.w at $100608, done marker $d0e5 at $10060a.
        org     $100400
stub:   movem.l d0-d7/a0-a6,-(a7)
        move.w  sr,-(a7)
        move.w  (a7),$100608.l
        clr.w   $10060a.l
        movea.l $100500.l,a1
        move.l  $100504.l,d1
        lea     $100508.l,a0
        jsr     $100000.l
        move.l  d0,$100600.l
        move.l  d1,$100604.l
done:   move.w  #$d0e5,$10060a.l
        move.w  (a7)+,sr
        movem.l (a7)+,d0-d7/a0-a6
        jmp     $d1ca.l
