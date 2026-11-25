; name: qol_type
; default: yes
; stage: 2
; site: $19c2
; orig: 700010390001c490
; data: $dcb00 68
; note: 32-key ring-buffer FIFO for text input (Enter Your Name, Save Game name, etc.).
;       The original ACIA handler overwrote $1c490 with 0 on every key release, so any key released before the slow
;       window-redraw loop polled $19c2 was dropped. qol_keys2 now pushes (scancode.b, shift.b) into TFIFO while
;       $d03e (typing active) is set, and this hook pops from TFIFO and translates via the game's own ASCII tables
;       ($19e8 unshifted, $1a7a shifted).
TF      equ     $dcb00                  ; +0 TH.w, +2 TT.w, +4 RING[64] (32 x {sc.b, sh.b})
TH      equ     TF+0
TT      equ     TF+2
RING    equ     TF+4

        org     $19c2
        jmp     $dcb50.l
        nop

        org     $dcb50
rdkey:  movem.l d1/a0,-(a7)             ; caller ($cfc8) keeps string ptr in a0 and cursor index in d1!
        clr.b   $1c490.l
        move.w  TH.l,d0
        cmp.w   TT.l,d0
        beq.s   .empty
        lea     RING.l,a0
        move.w  d0,d1
        addq.w  #2,d1
        andi.w  #62,d1
        move.w  d1,TH.l
        moveq   #0,d1
        move.b  1(a0,d0.w),d1           ; shift flag
        move.b  0(a0,d0.w),d0           ; scancode
        andi.w  #$7f,d0
        tst.b   d1
        bne.s   .sh
        lea     $19e8.l,a0              ; unshifted ASCII table
        bra.s   .lu
.sh:    lea     $1a7a.l,a0              ; shifted ASCII table
.lu:    move.b  (a0,d0.w),d0
        move.b  d0,$2df88.l
        movem.l (a7)+,d1/a0             ; movem preserves CCR (Z set from d0)
        rts
.empty: moveq   #0,d0
        movem.l (a7)+,d1/a0
        rts
