; name: test_hog
; default: no
; site: $12548
; orig: 4eb900001bf4
; data: PB+$6f20 4
; note: TEST ONLY (item 4 proof, work/notes/display.md): holds the bus the way a too-long blitter burst would.  At the top of every pass (before the VBL wait `jsr $1bf4`)
; note: it runs HOGN blits (word at PB+$6f20, set by the host; 0 = none) of 32,000 bytes ($2300 -> $90000, HOG mode, about 128,000 cycles = 12 IKBD byte times,
; note: Powermonger buserr.md section 3.2) with interrupts masked by the blitter's bus hold, so the ACIA loses bytes (OVRN) and the packet parser builds garbage positions.
HOGN    equ     PB+$6f20
HOG     equ     PB+$6900
        org     $12548
        jsr     HOG.l

        org     PB+$6900
hog:    move.w  HOGN.l,d0
        beq.s   .out
        subq.w  #1,d0
.b:     move.w  #2,$ffff8a20.w
        move.w  #2,$ffff8a22.w
        move.w  #2,$ffff8a2e.w
        move.w  #2,$ffff8a30.w
        move.w  #$ffff,$ffff8a28.w
        move.w  #$ffff,$ffff8a2a.w
        move.w  #$ffff,$ffff8a2c.w
        move.l  #$2300,$ffff8a24.w
        move.l  #$90000,$ffff8a32.w
        move.w  #100,$ffff8a36.w
        move.w  #160,$ffff8a38.w
        move.b  #2,$ffff8a3a.w
        move.b  #3,$ffff8a3b.w
        move.b  #0,$ffff8a3d.w
        move.b  #$c0,$ffff8a3c.w
        dbra    d0,.b
.out:   jmp     $1bf4.l
