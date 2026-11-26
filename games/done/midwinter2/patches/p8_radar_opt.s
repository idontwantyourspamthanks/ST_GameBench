; name: p8_radar_opt
; default: yes
; site: $1b92a
; orig: 41f83cee4a50
; phase: deferred
; note: HUD radar loop ($1b92a..$1b964) calls sub_01b966 for each active object in $3cee..$3fbe (57 slots),
; note: and sub_01b966 recomputes sin/cos($6294) via `jsr $4f7e.w` on EVERY iteration.
; note: Hoist `move.w $6294.w,d0; jsr $4f7e.w` once before the loop and keep sin/cos in d6/d7,
; note: computing the identical rotation inline (100% pixel-identical, saves up to 56 sin/cos calls/frame).
        org     $1b92a
        jmp     $b9140.l

        org     $b9140
        movem.l d4-d7,-(a7)
        move.w  $6294.w,d0
        jsr     $4f7e.w                 ; d0 = sin(heading), d1 = cos(heading)
        move.w  d0,d6                   ; d6 = sin
        move.w  d1,d7                   ; d7 = cos
        lea     $3cee.w,a0
.loop:  tst.w   (a0)
        bmi.s   .next
        move.l  4(a0),d2
        move.l  10(a0),d3
        sub.l   $66e6.w,d2
        sub.l   $66ea.w,d3
        ; Inline sub_01b966 with d6=sin, d7=cos (exact same arithmetic)
        move.l  d2,d4
        muls.w  d7,d4                   ; dx * cos
        move.l  d3,d5
        muls.w  d6,d5                   ; dy * sin
        sub.l   d5,d4                   ; d4 = dx*cos - dy*sin
        muls.w  d6,d2                   ; dx * sin
        muls.w  d7,d3                   ; dy * cos
        add.l   d2,d3                   ; d3 = dx*sin + dy*cos
        move.l  d4,d0
        move.l  d3,d1
        swap    d0
        swap    d1
        asr.w   #6,d0
        asr.w   #6,d1
        neg.w   d1
        add.w   $535a.w,d0
        add.w   $535c.w,d1
        moveq   #8,d2
        jsr     $4f9c.w
.next:  lea     $18(a0),a0
        cmpa.l  #$3fbe,a0
        bcs.s   .loop
        movem.l (a7)+,d4-d7
        rts
