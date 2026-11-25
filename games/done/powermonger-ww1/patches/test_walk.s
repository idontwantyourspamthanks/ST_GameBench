; name: test_walk
; default: no
; site: $13dae
; orig: 52b900050fd8
; data: $77c00 8
; note: TEST ONLY (tools/wwab.py, never shipped), part 1 of 3 (needs test_walk2, test_walk3): drives the mouse pointer deterministically (master test_walk, re-sited).  The game polls the IKBD
;       every VBL (absolute mode) and the packet handler $ee0/$eea copies the position $1d2b2/$1d2b4 to the draw variables $2edb2/$2edb4 (parts 2 and 3 copy PX/PY instead), so pokes of
;       those words are overwritten within a VBL.  This part is the world tick increment of the logic path (`addq.l #1,$50fd8.l` at $13dae, reached by T and S passes, never by R passes) and
;       sets PX/PY and the draw variables from a table indexed by the NEW tick & 15 (MODE.w != 0, `w $77c00 $00 $01`) or entry 0 (MODE = 0): the pointer position is a pure function of the
;       world tick.  Table: edges, the one-column x > 304 case, the y > 184 clip, corners.   Data: MODE.w PX.w PY.w ($77c00).  wwab.py pokes PX/PY = the snapshot's pointer at the apply flip.
MODE    equ     $77c00
PX      equ     $77c02
TAB     equ     $77c60
        org     $13dae
        jsr     $77c10.l

        org     $77c10
walk:   addq.l  #1,$50fd8.l            ; the displaced instruction
        movem.l d1/a0,-(a7)
        moveq   #0,d1
        tst.w   MODE.l
        beq.s   .f
        move.l  $50fd8.l,d1
        andi.w  #15,d1
.f:     lsl.w   #2,d1
        lea     TAB.l,a0
        move.l  (a0,d1.w),d1
        move.l  d1,PX.l
        move.l  d1,$2edb2.l
        movem.l (a7)+,d1/a0
        rts

        org     $77c60
        dc.w    229,173, 100,100, 0,0, 310,20, 319,199, 160,190, 304,184, 305,185
        dc.w    15,1, 16,0, 250,60, 303,100, 64,120, 200,183, 8,197, 311,150
