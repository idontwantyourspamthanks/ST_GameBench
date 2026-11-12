; name: p7_skip_wv1
; default: yes
; site: $1dafc
; orig: 301032000240007e
; phase: deferred
; note: P7 item 5(a), part 5/7 (work/notes/p7_static_skip.md).  Terrain vertex transform for water cells
;       ($1dad0 -> $1dafc): `movea.l $1dfba(pc),a3` at $1db04 reads the wave table pointer, i.e. the sea
;       animation phase ($1877c) is an input of the picture.  Sets WAVE; p7_skip_render then compares the
;       phase for the buffers whose last render touched the wave table.
;       Displaces `move.w (a0),d0 ; move.w d0,d1 ; andi.w #$7e,d0`; rejoins at $1db04.
D       equ     $b6000
WAVE    equ     D+$10

        org     $1dafc
        jmp     $b7d00.l
        nop

        org     $b7d00
        move.w  #1,WAVE.l
        move.w  (a0),d0                 ; displaced
        move.w  d0,d1
        andi.w  #$7e,d0
        jmp     $1db04.l
