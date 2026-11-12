; name: test_tickspin
; default: no
; site: $12548
; orig: 4eb900001bf4
; data: PB+$2700 2
; note: TEST ONLY (gate driver for tools/p2tick.py ab --spin N; never in a build).  Makes every pass slower by N loop iterations of `dbra` (10 cycles each on a 68000, taken):
; note: at the top of the pass, before the VBL wait `jsr $1bf4`, it burns the count in the word SPINN (PB+$2700, set by the host; 0 = none).  No interrupt is masked, no
; note: bus is held (unlike test_hog, whose blitter burst makes the IKBD lose bytes), so it slows a pass without disturbing anything else; the unpatched game and the tick
; note: are slowed by the same amount.  N = 12800 is about 128,000 cycles = 0.8 VBL at 8 MHz / 50 Hz: busy1 then needs about 8.9 VBL per turn pass against the 8 VBL of
; note: the tick, so catch-up (S) passes must carry the difference.
SPINN   equ     PB+$2700
        org     $12548
        jsr     PB+$2680.l

        org     PB+$2680
        move.w  SPINN.l,d0
        beq.s   .out
        subq.w  #1,d0
.l:     dbra    d0,.l
.out:   jmp     $1bf4.l
