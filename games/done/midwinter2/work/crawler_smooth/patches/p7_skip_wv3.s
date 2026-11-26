; name: p7_skip_wv3
; default: yes
; site: $1fd9a
; orig: 207ae21e0241007e
; phase: deferred
; note: P7 item 5(a), part 7/7 (work/notes/p7_static_skip.md).  The same read in the `$507a` variant of the
;       wave height probe ($1fd84).  Sets WAVE.
;       Displaces `movea.l $1dfba(pc),a0 ; andi.w #$7e,d1`; rejoins at $1fda2.
D       equ     $b6000
WAVE    equ     D+$10

        org     $1fd9a
        jmp     $b7d40.l
        nop

        org     $b7d40
        move.w  #1,WAVE.l
        movea.l $1dfba.l,a0             ; displaced (pc-relative read of the same long)
        andi.w  #$7e,d1
        jmp     $1fda2.l
