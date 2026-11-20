; Frame replay with interrupts ENABLED: the case table ($D0000: n.w + 16-byte records as kb.s) is drawn LOOPS times in a row onto $C8000.
; Timed by m_start / m_end; the game's own ISRs (Timer B raster, VBL, IKBD) run meanwhile: use bps on $d616 to log LineCycles.
        ifnd    LOOPS
LOOPS   equ     10
        endc
        org     $C0000
SCR     equ     $C8000
PTR     equ     $D9000
LCNT    equ     $D9004
start:  movem.l d0-d7/a0-a6,-(a7)
        move.w  sr,-(a7)
        move.w  #$2700,sr
        lea     SCR.l,a0
        move.w  #7999,d0
        move.l  #$2468ace1,d1
.fl:    move.l  d1,(a0)+
        add.l   #$01234567,d1
        rol.l   #3,d1
        dbra    d0,.fl
        move.w  #LOOPS,LCNT.l
        move.w  #$2300,sr               ; interrupts on
m_start: nop
loopl:  move.l  #$D0002,PTR.l
        move.w  $D0000.l,$D9008.l
nxt:    movea.l PTR.l,a6
        movea.l (a6)+,a4
        move.w  (a6)+,d0
        move.w  (a6)+,d1
        move.w  (a6)+,d7
        addq.l  #2,a6
        movea.l (a6)+,a1
        move.l  a6,PTR.l
        lea     SCR.l,a5
        jsr     (a4)
        subq.w  #1,$D9008.l
        bne.s   nxt
        subq.w  #1,LCNT.l
        bne.s   loopl
m_end:  nop
        move.w  #$2700,sr
        move.l  #'DONE',$C0FF0.l
        move.w  (a7)+,sr
        movem.l (a7)+,d0-d7/a0-a6
        move.l  #$4eb90000,$7b74.w
        move.w  #$d1e4,$7b78.w
        jmp     $d1e4.l
