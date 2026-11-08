; name: tick_vbl
; default: yes
; site: $262d0
; orig: 527870205278770c
; data: $b3400 4
; note: P3 fixed-tick, part 1. The game's VBL handler ($26298) bumps $7020 and
;       $770c every VBL, but the game clears $7020 per frame and in its own
;       wait loops, and $770c wraps at 6, so neither is a usable clock. This
;       routes both increments through the blob and adds a free-running VBL
;       counter (long at $B3400) used by tick_frame.
        org     $262d0
        jsr     $b40f2.l
        nop

        org     $b40f2
        addq.w  #1,$7020.w              ; displaced
        addq.w  #1,$770c.w              ; displaced
        addq.l  #1,$b3400.l             ; free-running VBL clock (never cleared)
        rts
