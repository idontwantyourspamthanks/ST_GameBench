; name: qol_detail_rain
; default: yes
; site: $1b5b6
; orig: e74a20790002ed9c
; note: Alt+D detail level hook for rain/snow drawing ($1b5b6). When DET_LVL ($75300) != 0 (Medium or Low detail),
;       skips drawing the rain/snow overlay (~230k-248k cycles/pass saved when raining/snowing). Weather world logic
;       in $1b90a still runs identically. In High detail (DET_LVL == 0) runs the original routine unchanged.
DET_LVL equ     $75300

        org     $1b5b6
        jmp     $75310.l
        nop

        org     $75310
rain_d: tst.w   DET_LVL.l
        bne.s   .skip
        lsl.w   #3,d2                   ; displaced instructions
        movea.l $2ed9c.l,a0
        jmp     $1b5be.l
.skip:  rts
