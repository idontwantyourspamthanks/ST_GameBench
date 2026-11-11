; name: test_hdsav
; default: no
; data: $ce800 2048
; note: HD build self-test of hd_sector (hd_core.s), called through the debugger (`pmpatch.py boot --hd .. --call $ce000`:
;       breakpoint at the main loop's `lea.l $14e20.l,a2` ($13020), `r pc=$ce000`).  Writes sectors 5-6 of SAVEDISK.DAT with a
;       pattern, reads them back, compares, reads sector 0 (must start with 'POWE'), formats (no-op) and returns to $13020.
;       Results (longs): $cfff0 write d0, $cfff4 read d0, $cfff8 compare (0 = equal), $cfffc sector-0 check (0 = ok), $cfffe is
;       unused; $cffe8 = format d0, $cffec = 'DONE'.
        org     $ce000
t_hd:   movem.l d0-d7/a0-a6,-(a7)
        move.w  sr,-(a7)
        lea     $ce800.l,a0             ; pattern: 1024 bytes
        move.w  #255,d0
        move.l  #$50414c31,d1
.f:     move.l  d1,(a0)+
        addq.l  #1,d1
        dbra    d0,.f
        moveq   #5,d1                   ; write sectors 5..6
        moveq   #2,d2
        moveq   #1,d3
        lea     $ce800.l,a0
        jsr     $bb00c.l
        move.l  d0,$cfff0.l
        lea     $cec00.l,a0             ; clear the read buffer
        move.w  #255,d0
.c:     clr.l   (a0)+
        dbra    d0,.c
        moveq   #5,d1                   ; read them back
        moveq   #2,d2
        moveq   #0,d3
        lea     $cec00.l,a0
        jsr     $bb00c.l
        move.l  d0,$cfff4.l
        lea     $ce800.l,a0
        lea     $cec00.l,a1
        moveq   #0,d2
        move.w  #255,d0
.m:     cmpm.l  (a0)+,(a1)+
        beq.s   .n
        moveq   #1,d2
.n:     dbra    d0,.m
        move.l  d2,$cfff8.l
        moveq   #0,d1                   ; sector 0
        moveq   #1,d2
        moveq   #0,d3
        lea     $cec00.l,a0
        jsr     $bb00c.l
        moveq   #1,d1
        cmpi.l  #'POWE',$cec00.l
        bne.s   .z
        moveq   #0,d1
.z:     or.l    d0,d1
        move.l  d1,$cfffc.l
        moveq   #0,d1                   ; format: must succeed and change nothing
        move.w  #$320,d2
        moveq   #2,d3
        jsr     $bb00c.l
        move.l  d0,$cffe8.l
        move.l  #'DONE',$cffec.l
        move.w  (a7)+,sr
        movem.l (a7)+,d0-d7/a0-a6
        jmp     $13020.l
