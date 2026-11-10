; name: p7_skip_gate
; default: yes
; site: $1b6be
; orig: 48e7fffe4eb84f90
; phase: deferred
; note: P7 item 5(a), part 3/7 (work/notes/p7_static_skip.md).  Render-gate path $1b6be (stub $5098, called at
;       $31596 when $6298 <> 0 and at $325ce): it paints the 3D window area instead of rendering, so what the
;       back buffer holds is no longer the last render: clear VAL[] (p7_skip_render).
;       Displaces `movem.l d0-d7/a0-a6,-(a7)` and `jsr $4f90.w`; rejoins at $1b6c6.
D       equ     $b6000
VAL     equ     D+$00
NINV    equ     D+$1c

        org     $1b6be
        jmp     $b7c80.l
        nop

        org     $b7c80
        clr.l   VAL.l
        addq.l  #1,NINV.l
        movem.l d0-d7/a0-a6,-(a7)       ; displaced
        jsr     $4f90.w                 ; displaced
        jmp     $1b6c6.l
