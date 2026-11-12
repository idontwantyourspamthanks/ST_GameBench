; name: test_qolinv
; default: no
; stage: 2
; site: $130ce
; orig: 4eb900007a56
; data: $cec00 16
; note: TEST ONLY (tools/pmqol_inv.py): replays a table of scenarios on settlement 0 inside the emulator and, for each, runs qol_hover's `predict`
;       ($cfa84, the read-only replay of the invention chooser) and then the game's REAL order $5cde, exactly as the order handler $5fa0 calls it
;       (a0 = settlement, d1 = posture - 2), from the main loop (the `jsr $7a56` at $130ce, after the logic and the render of the pass).
;       TI: +0 go.w (the debugger pokes 1) +2 count.w +4 done.w.  The table at SC ($e0000, loaded with `loadbin`): per scenario 16 bytes
;       {posture-2.w, resident flags F.w, terrain H.w, forest cell word.w (0 = no forest), mine.w, parity.w, slot-free.w, -}; the results at RS
;       ($e8000), 8 bytes each: {W.w (predict), c.w (the settlement's item $c after the real order), 0.l}.  Each scenario first writes its inputs
;       into the game's own variables (captain posture word, the first resident's profession byte $7 = F and 0 for the others, the terrain byte
;       under the settlement, the forest list $57f68, the mine word $12(a2), the parity byte $57fed, the house slot counter $51536) and clears $c(a2).
TI      equ     $cec00
SC      equ     $e0000
RS      equ     $e8000

        org     $130ce
        jsr     $ce8c0.l

        org     $ce8c0
ti:     tst.w   TI.l
        beq     .o
        movem.l d0-d7/a0-a6,-(a7)
        clr.w   TI.l
        lea     $4e514.l,a2             ; settlement 0
        lea     SC.l,a3
        lea     RS.l,a4
        move.w  TI+2.l,d7
        subq.w  #1,d7
.s:     move.w  (a3),d0                 ; posture - 2
        addq.w  #2,d0
        move.w  $57fd2.l,d1
        lea     $51538.l,a0
        move.w  d0,$3c(a0,d1.w)
        move.w  2(a3),d2                ; F: first resident gets it, the rest 0
        move.w  2(a2),d0                ; first house
        moveq   #1,d3
.hs:    beq.s   .hd
        lea     $4f916.l,a0
        adda.w  d0,a0
        move.w  $a(a0),d1
.ps:    beq.s   .pd
        lea     $51b66.l,a1
        adda.w  d1,a1
        clr.b   7(a1)
        tst.w   d3
        beq.s   .pn
        move.b  d2,7(a1)
        moveq   #0,d3
.pn:    move.w  $18(a1),d1
        bra.s   .ps
.pd:    move.w  8(a0),d0
        bra.s   .hs
.hd:    move.w  4(a2),d0                ; terrain under the settlement
        lea     $3f86c.l,a0
        move.b  5(a3),(a0,d0.w)
        lea     $57f68.l,a0             ; forests
        moveq   #9,d0
.fz:    clr.w   (a0)
        addq.l  #8,a0
        dbra    d0,.fz
        move.w  6(a3),$57f68.l
        move.w  8(a3),$12(a2)           ; mine
        move.b  11(a3),$57fed.l         ; parity
        move.w  #$1000,$51536.l         ; slot free ...
        tst.w   12(a3)
        bne.s   .sf
        move.w  #$1c20,$51536.l         ; ... or not
.sf:    clr.w   $c(a2)
        movem.l d7/a3/a4,-(a7)          ; predict and $5cde clobber d7 / a4
        jsr     $cfa84.l                ; predict -> d3
        movem.l (a7),d7/a3/a4
        move.w  d3,(a4)
        move.w  (a3),d1
        movea.l a2,a0
        jsr     $5cde.l                 ; the game's real order
        movem.l (a7)+,d7/a3/a4
        move.w  $c(a2),2(a4)
        lea     16(a3),a3
        lea     8(a4),a4
        dbra    d7,.s
        move.w  #1,TI+4.l
        movem.l (a7)+,d0-d7/a0-a6
.o:     jmp     $7a56.l
