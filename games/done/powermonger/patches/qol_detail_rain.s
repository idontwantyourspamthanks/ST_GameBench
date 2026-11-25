; name: qol_detail_rain
; default: yes
; stage: 2
; site: $1a856
; orig: e74a20790002df7c
; note: Alt+D detail level hook for rain/snow drawing ($1a856). When DET_LVL ($dc300) != 0 (Medium or Low detail),
;       skips drawing the rain/snow overlay (~230k-248k cycles/pass saved when raining/snowing). Weather world logic
;       in $1abaa still runs identically. In High detail (DET_LVL == 0) runs the original routine unchanged.
DET_LVL equ     $dc300

        org     $1a856
        jmp     $dc310.l
        nop

        org     $dc310
rain_d: tst.w   DET_LVL.l
        bne.s   .skip
        lsl.w   #3,d2                   ; displaced instructions
        movea.l $2df7c.l,a0
        jmp     $1a85e.l
.skip:  rts
