; name: test_copy
; default: no
; stage: 2
; site: $1305e
; orig: 22790002df7c
; data: $ce700 16
; note: test only (never shipped): cycle cost of a 32000-byte screen copy (the 3D-window background copy `$12ce0` is one) on the CPU and
;       on the STE blitter, for work/notes/p4_raster.md section 4.  Runs once from the main loop (`movea.l $2df7c.l,a1` at $1305e) when
;       TESTGO.w != 0 (`w $ce700 $00 $01`): copies $78000 -> $e0000 five ways, each bracketed by calls of the empty stubs at $ceb00 + 16*k
;       (k = 0..9: start/end markers; the tool arms breakpoints there and reads the cycle counter): 0/1 the original `jsr $12ce0`
;       (8-register movem pairs), 2/3 a 12-register movem loop, 4/5 blitter HOG mode, 6/7 blitter shared mode with the CPU polling BUSY,
;       8/9 blitter shared mode, the CPU runs a 2000-iteration `dbra` loop meanwhile and then polls (overlap test).  DONE marker
;       $600d at $ce702 when finished.  Interrupts are masked (SR $2700) for the whole test.
TESTGO  equ     $ce700
DONE    equ     $ce702
        org     $1305e
        jsr     $ce800.l

        org     $ce800
tst:    tst.w   TESTGO.l
        beq.w   .out
        clr.w   TESTGO.l
        movem.l d0-d7/a0-a6,-(a7)
        move.w  sr,-(a7)
        ori.w   #$0700,sr               ; no interrupt inside a window
        lea     $78000.l,a0             ; 0/1: the original routine
        lea     $e0000.l,a1
        jsr     $ceb00.l
        jsr     $12ce0.l
        jsr     $ceb10.l
        lea     $78000.l,a0             ; 2/3: 12 registers per movem, 666 blocks of 48 bytes + 32 bytes
        lea     $e0000.l,a1
        jsr     $ceb20.l
        move.w  #665,d0
.m12:   movem.l (a0)+,d1-d7/a2-a6
        movem.l d1-d7/a2-a6,(a1)
        lea     48(a1),a1
        dbra    d0,.m12
        movem.l (a0)+,d1-d7/a2
        movem.l d1-d7/a2,(a1)
        jsr     $ceb30.l
        move.w  #16000,d6               ; blitter: source 2 inc, dest 2 inc, one line of 16000 words, HOP source, LOP S
        move.w  #2,$ffff8a20.w
        move.w  #2,$ffff8a2e.w
        move.w  #$ffff,$ffff8a28.w
        move.w  #$ffff,$ffff8a2a.w
        move.w  #$ffff,$ffff8a2c.w
        move.b  #2,$ffff8a3a.w
        move.b  #3,$ffff8a3b.w
        move.b  #0,$ffff8a3d.w
        move.w  d6,$ffff8a36.w
        move.l  #$78000,$ffff8a24.w     ; 4/5: HOG
        move.l  #$e0000,$ffff8a32.w
        move.w  #1,$ffff8a38.w
        jsr     $ceb40.l
        move.b  #$c0,$ffff8a3c.w
        jsr     $ceb50.l
        move.l  #$78000,$ffff8a24.w     ; 6/7: shared, polling
        move.l  #$e0000,$ffff8a32.w
        move.w  #1,$ffff8a38.w
        jsr     $ceb60.l
        move.b  #$80,$ffff8a3c.w
.p1:    btst    #7,$ffff8a3c.w
        bne.s   .p1
        jsr     $ceb70.l
        move.l  #$78000,$ffff8a24.w     ; 8/9: shared, CPU busy meanwhile (overlap)
        move.l  #$e0000,$ffff8a32.w
        move.w  #1,$ffff8a38.w
        jsr     $ceb80.l
        move.b  #$80,$ffff8a3c.w
        move.w  #1999,d0
.w:     dbra    d0,.w
.p2:    btst    #7,$ffff8a3c.w
        bne.s   .p2
        jsr     $ceb90.l
        move.w  #$600d,DONE.l
        move.w  (a7)+,sr
        movem.l (a7)+,d0-d7/a0-a6
.out:   movea.l $2df7c.l,a1             ; the displaced instruction
        rts

        org     $ceb00
        rts
        org     $ceb10
        rts
        org     $ceb20
        rts
        org     $ceb30
        rts
        org     $ceb40
        rts
        org     $ceb50
        rts
        org     $ceb60
        rts
        org     $ceb70
        rts
        org     $ceb80
        rts
        org     $ceb90
        rts
