; name: test_hznop
; default: no
; site: $c63c
; orig: 082d00070093
; note: Timing control for the hn_hz gate (tools/hunthz.py ab --control): the same site and the same instruction sequence as hn_hz.s at
; note: 50 Hz (identical cycles per VBL), but it never skips a world tick, at either refresh. A run with this patch and a run with hn_hz at
; note: 50 Hz therefore have identical timing, so every frame of the two must be bit-identical (a free-running comparison against the
; note: unpatched game is not: the ~140 extra cycles per VBL move a frame across a VBL boundary now and then). At 60 Hz it is the
; note: "unpatched speed" control with the same cost. Do not ship.
HZ_ACC  equ     $8dc60
        org     $c63c
        jmp     $8dc00.l

        org     $8dc00
nop_gate:
        moveq   #6,d0
        btst    #1,$ffff820a.w
        bne.s   .u
        moveq   #5,d0
.u:     lea     HZ_ACC.l,a0
        add.w   (a0),d0
        cmpi.w  #6,d0
        bcs.s   .tick                   ; 60 Hz, accumulator below 6: hn_hz would skip here, the control ticks anyway
        subq.w  #6,d0
        move.w  d0,(a0)
        clr.b   2(a0)
.tick:  btst    #7,$93(a5)
        jmp     $c642.l

        org     $8dc60
        dc.w    0
        dc.b    0,0
