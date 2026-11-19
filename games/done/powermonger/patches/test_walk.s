; name: test_walk
; default: no
; stage: 2
; site: $13034
; orig: 52b90004bb3e
; data: $ce400 8
; note: test only (tools/pmab.py, never shipped), part 1 of 3 (needs test_walk2, test_walk3): drives the mouse pointer
;       deterministically.  The game polls the IKBD (absolute mode, `$0D` every VBL, reply decoded in the ACIA interrupt) and
;       the packet handler copies the position `$1c492/$1c494` to the draw variables `$2df92/$2df94` (`$194c`, `$1956`: parts
;       2 and 3 copy PX/PY instead), so pokes of those words are overwritten within a VBL.  This part is the world tick
;       increment of the main loop (`addq.l #1,$4bb3e.l` at $13034, reached by T and S passes, never by R passes) and sets
;       PX/PY and the draw variables from a table indexed by the NEW world tick & 15 (MODE.w != 0, `w $ce400 $00 $01`) or
;       entry 0 (MODE = 0).  The pointer position is thereby a pure function of the world tick: every pass of a tick (the
;       logic, the UI/hover code that reads $2df92, the render, the pointer redraws) sees the same position, whatever the pass
;       mix (R/S) of the run - that was the flaw of the first version (a position latched at flips changed the logic's view of
;       the pointer between runs with different S passes, and the army icon blits into the background differ).
;       Table: the snapshot's own position, edges, the one-column x > 304 case, the y > 184 clip, corners.
;       Data: MODE.w PX.w PY.w.  pmab.py pokes PX/PY = (229,173) at the apply flip.
MODE    equ     $ce400
PX      equ     $ce402
TAB     equ     $ce0c0
        org     $13034
        jsr     $ce000.l

        org     $ce000
walk:   addq.l  #1,$4bb3e.l            ; the displaced instruction
        movem.l d1/a0,-(a7)
        moveq   #0,d1
        tst.w   MODE.l
        beq.s   .f
        move.l  $4bb3e.l,d1
        andi.w  #15,d1
.f:     lsl.w   #2,d1
        lea     TAB.l,a0
        move.l  (a0,d1.w),d1
        move.l  d1,PX.l
        move.l  d1,$2df92.l
        movem.l (a7)+,d1/a0
        rts

        org     $ce0c0
        dc.w    229,173, 100,100, 0,0, 310,20, 319,199, 160,190, 304,184, 305,185
        dc.w    15,1, 16,0, 250,60, 303,100, 64,120, 200,183, 8,197, 311,150
