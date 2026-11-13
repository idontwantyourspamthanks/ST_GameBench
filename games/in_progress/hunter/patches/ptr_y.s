; name: ptr_y
; default: yes
; site: $b32c
; orig: 48806a02e240
; requires: ptr_vbl ptr_x
; note: Even mouse pointer, part 3 of 3 (see ptr_vbl.s).  The Y byte ends the packet: add both of its deltas to the pending motion (PX, PY) together,
; note: so a VBL boundary can never split one packet between two VBLs.  Both adds are single read-modify-write instructions on words that the VBL hook
; note: takes the same way, and the ACIA handler cannot be interrupted by the VBL (IPL 6 over 4).  TX is cleared so a stray Y byte cannot reuse it.
PTR     equ     $8dbc0
        org     $b32c
        jmp     $8da50.l                ; the blob's rts returns to the routine's caller

        org     $8da50
ptr_y:  ext.w   d0
        add.w   d0,PTR+8.l              ; PY
        move.w  PTR+16.l,d0
        add.w   d0,PTR.l                ; PX
        clr.w   PTR+16.l
        rts
