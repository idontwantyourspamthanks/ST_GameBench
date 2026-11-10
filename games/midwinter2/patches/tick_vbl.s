; name: tick_vbl
; default: yes
; site: $262d0
; orig: 527870205278770c
; data: $b3400 4
; note: P3 fixed-tick, part 1. The game's VBL handler ($26298) bumps $7020 and
;       $770c every VBL, but the game clears $7020 per frame and in its own
;       wait loops, and $770c wraps at 6, so neither is a usable clock. This
;       routes both increments through the blob and adds a free-running REAL-TIME
;       clock (long at $B3400, never cleared) used by tick_head / p3cp_head, in units
;       of 1/300 s: every VBL adds the length of that frame, read from the shifter
;       sync mode ($ff820a bit 1: 1 = 50 Hz = 6 units, 0 = 60 Hz = 5 units), so the
;       world ticks at the same rate on 50 and 60 Hz displays (work/notes/timing.md).
;       Blob at $B3700 (30 bytes; the old $B40F2 slot had only 16 bytes before the render hook, now p3c_render).
        org     $262d0
        jsr     $b3700.l
        nop

        org     $b3700
        addq.w  #1,$7020.w              ; displaced
        addq.w  #1,$770c.w              ; displaced
        addq.l  #5,$b3400.l             ; 60 Hz frame = 5 units of 1/300 s
        btst    #1,$ffff820a.w          ; shifter sync mode: bit 1 set = 50 Hz
        beq.s   .done
        addq.l  #1,$b3400.l             ; 50 Hz frame = 6 units
.done:  rts
