; name: test_delay
; default: no
; phase: stage1
; site: $78524
; orig: 41f9000782ba
; note: TEST ONLY (work/credit/, copied into patches/ only while building the control variants): the credit hook with NO drawing: the displaced lea plus a busy-wait of N dbra iterations (10 cycles each).
N       equ     3000
        org     $78524
        jsr     $bfd00.l
        org     $bfd00
        move.l  d0,-(sp)
        move.w  #N,d0
        subq.w  #1,d0
        bmi.s   .out
.l:     dbra    d0,.l
.out:   move.l  (sp)+,d0
        lea     $782ba.l,a0
        rts
