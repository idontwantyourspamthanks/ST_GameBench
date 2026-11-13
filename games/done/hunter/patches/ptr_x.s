; name: ptr_x
; default: yes
; site: $b30e
; orig: 48806a02e240
; requires: ptr_vbl ptr_y
; note: Even mouse pointer, part 2 of 3 (see ptr_vbl.s).  The game's X step `ext.w d0 / bpl.b +2 / asr.w #1,d0 / add.w $d8(a5),d0 / clamp / store` (the asr
; note: halves only negative deltas) is replaced by: remember the packet's X byte (sign extended, not halved) until its Y byte arrives (ptr_y).
PTR     equ     $8dbc0
        org     $b30e
        jmp     $8da40.l                ; 6 bytes; the rest of the old routine is never reached; the blob's rts returns to its caller

        org     $8da40
ptr_x:  ext.w   d0
        move.w  d0,PTR+16.l             ; TX
        rts
