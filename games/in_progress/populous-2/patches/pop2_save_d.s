; name: pop2_save_d
; default: yes
; base: pp
; site: $2cb0e
; orig: 4eb900036efc
; note: Part 3 of 3 of the in-game SAVE/LOAD fix (see pop2_save): the directory call of the requester's list routine $2cae0 (d0 = 3, a0 = drawer, a1 = record buffer) goes to the
; note: GEMDOS blob instead of PP's disk-layer stub.  Ships with pop2_save and pop2_save_w.
SAVE    equ     PB+$300

        org     $2cb0e
        jsr     SAVE.l
