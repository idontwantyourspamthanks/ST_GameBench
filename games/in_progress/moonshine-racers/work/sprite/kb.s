; Kernel benchmark / differential harness (see kb.py).  Case table at $D0000: n.w, then n records of 16 bytes:
;   +0 kernel entry (L)  +4 x (W)  +6 y (W)  +8 rows (W)  +10 reps (W)  +12 a1 (L)
; per case: refill scratch screen $C8000 (untimed), reps x { d0=x d1=y d7=rows a1 a5=$C8000 ; jsr kernel }, checksum of the screen -> $D8000+4*i
        org     $C0000
SCR     equ     $C8000
PTR     equ     $D9000
CNT     equ     $D9004
IDX     equ     $D9008
KRN     equ     $D9010
VX      equ     $D9014
VY      equ     $D9016
VR      equ     $D9018
VA      equ     $D901C
start:  movem.l d0-d7/a0-a6,-(a7)
        move.w  sr,-(a7)
        move.w  #$2700,sr
        move.l  #$D0002,PTR.l
        clr.l   IDX.l
casel:  lea     SCR.l,a0
        move.w  #7999,d0
        move.l  #$2468ace1,d1
.fl:    move.l  d1,(a0)+
        add.l   #$01234567,d1
        rol.l   #3,d1
        dbra    d0,.fl
        movea.l PTR.l,a6
        move.l  (a6)+,KRN.l            ; kernel
        move.w  (a6)+,VX.l              ; x
        move.w  (a6)+,VY.l              ; y
        move.w  (a6)+,VR.l              ; rows
        move.w  (a6)+,CNT.l             ; reps
        move.l  (a6)+,VA.l              ; a1 source
        move.l  a6,PTR.l
m_case: nop
.rep:   move.w  VX.l,d0
        move.w  VY.l,d1
        move.w  VR.l,d7
        movea.l VA.l,a1
        movea.l KRN.l,a4
        lea     SCR.l,a5
        jsr     (a4)
        subq.w  #1,CNT.l
        bne.s   .rep
m_end:  nop
        lea     SCR.l,a0
        move.w  #7999,d1
        moveq   #0,d0
.sm:    add.l   (a0)+,d0
        rol.l   #3,d0
        dbra    d1,.sm
        lea     $D8000.l,a0
        adda.l  IDX.l,a0
        move.l  d0,(a0)
        addq.l  #4,IDX.l
        move.w  $D0000.l,d0
        move.l  IDX.l,d1
        lsr.l   #2,d1
        cmp.w   d0,d1
        bne     casel
        move.l  #'DONE',$C0FF0.l
        move.w  (a7)+,sr
        movem.l (a7)+,d0-d7/a0-a6
        move.l  #$4eb90000,$7b74.w      ; restore jsr $d1e4
        move.w  #$d1e4,$7b78.w
        jmp     $d1e4.l
