
HB      equ     0
        org     HB+$1460
        move.b  HB+$1f8a(pc),d0
        beq.s   HB+$14a6
        move.l  $70.w,-(a7)
        lea     HB+$12a2(pc),a2
        move.l  a2,$70.w
        move.w  HB+$14ac(pc),d1
        move.w  d1,d0
        lsl.w   #5,d0
        lea     HB+$14d8(pc,d0.w),a1
        move    #$2300,sr
        nop
