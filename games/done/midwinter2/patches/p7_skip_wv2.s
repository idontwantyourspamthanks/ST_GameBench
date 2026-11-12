; name: p7_skip_wv2
; default: yes
; site: $1fd1c
; orig: 207ae29c0241007e
; phase: deferred
; note: P7 item 5(a), part 6/7 (work/notes/p7_static_skip.md).  Height probe with the wave table ($506e ->
;       $1fd0a, callers inside the render: $1c59a): `movea.l $1dfba(pc),a0` reads the wave phase.  Sets WAVE.
;       Displaces `movea.l $1dfba(pc),a0 ; andi.w #$7e,d1`; rejoins at $1fd24.
D       equ     $b6000
WAVE    equ     D+$10

        org     $1fd1c
        jmp     $b7d20.l
        nop

        org     $b7d20
        move.w  #1,WAVE.l
        movea.l $1dfba.l,a0             ; displaced (pc-relative read of the same long)
        andi.w  #$7e,d1
        jmp     $1fd24.l
