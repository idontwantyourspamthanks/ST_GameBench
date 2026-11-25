; name: p4_clamp
; default: yes
; site: $ed6
; orig: 13f90001d2b10001d2af
; note: safety net for the IKBD packet parser (master p4_clamp / work/notes/buserr.md, re-sited: master $1942 -> WW1 $ed6).  The game polls the IKBD every VBL (`$0D`, absolute
;       mouse positions, x 0..319, y 0..199) and the 6-byte reply is parsed byte by byte by the ACIA handler (state byte $1d2ae: header -> 5 data bytes into
;       $1d2b1..$1d2b5).  A lost byte (ACIA overrun) shifts the packet: the position words become garbage and the pointer code draws at `[$2ed98] + y * 160`: a bus
;       error.  $ed6 is the packet-complete branch (`move.b $1d2b1.l,$1d2af.l`, the button byte, 10 bytes; the two position copies $ee0 and $eea follow).  This hook runs
;       the displaced instruction, then checks the shadow position $1d2b2 (x) and $1d2b4 (y): if x > 319 or y > 199 (unsigned) the packet is dropped, i.e. the shadow
;       words are set back to the last committed position $2edb2 / $2edb4 and the copies that follow are no-ops.  Every position the IKBD can really send is in
;       range, so nothing changes in normal use.
        org     $ed6
        jsr     $75c00.l
        nop
        nop

        org     $75c00
clamp:  move.b  $1d2b1.l,$1d2af.l       ; the displaced instruction
        cmpi.w  #319,$1d2b2.l
        bhi.s   .bad
        cmpi.w  #199,$1d2b4.l
        bls.s   .ok
.bad:   move.w  $2edb2.l,$1d2b2.l       ; keep the last good position
        move.w  $2edb4.l,$1d2b4.l
.ok:    rts
