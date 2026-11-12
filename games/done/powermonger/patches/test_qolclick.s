; name: test_qolclick
; default: no
; stage: 2
; site: $130fc
; orig: 4eb900007202
; data: $ce900 16
; note: TEST ONLY (tools/pmqol_state.py): the mouse-click side of the key-vs-click equality gate.  Same site as qol_keys ($130fc, right before the
;       click dispatch), but written independently: when the debugger has poked TQ (flag.w, x.w, y.w, right.w) it latches a click exactly as the
;       VBL handler does ($12ec-$1300 / $1348-$135c): position words $2df8e/$2df90, button latch $2df96 (or $2df98 + the held word $2df9e for the
;       right button), click stamp $2df74 = the value `move.l $2df70,d0` at $1373c reads (operand $1373e: $2df70 or the tick patches' pass counter).
;       A right-button hold is dropped again in the next pass (the release).
TQ      equ     $ce900                  ; +0 flag.w +2 x.w +4 y.w +6 right.w +8 release-pending.w

        org     $130fc
        jsr     $ce880.l

        org     $ce880
tc:     move.l  a0,-(a7)
        tst.w   TQ+8.l
        beq.s   .n
        clr.w   TQ+8.l
        clr.w   $2df9e.l
.n:     tst.w   TQ.l
        beq.s   .o
        clr.w   TQ.l
        move.w  TQ+2.l,$2df8e.l
        move.w  TQ+4.l,$2df90.l
        tst.w   TQ+6.l
        bne.s   .r
        move.w  #1,$2df96.l
        bra.s   .s
.r:     move.w  #1,$2df98.l
        move.w  #1,$2df9e.l
        move.w  #1,TQ+8.l
.s:     movea.l $1373e.l,a0
        move.l  (a0),$2df74.l
.o:     move.l  (a7)+,a0
        jmp     $7202.l
