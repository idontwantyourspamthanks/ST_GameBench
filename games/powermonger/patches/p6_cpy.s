; name: p6_cpy
; default: yes
; stage: 2
; site: $12ce0
; orig: 48e77f107220
; note: PMPerf2, work/notes/hotpaths2.md.  The 3D window copy `$12ce0` (the 32000 B picture $78000 -> back buffer at the start of every
;       rendered pass, 163 k cycles = 10-11 % of a pass) on the STE blitter: 50 chunks of 4 rows (320 words, 2560 cycles each, HOG).  The chunk size
;       is the keyboard's: the IKBD ACIA holds ONE received byte and a 7812 baud byte takes 1.28 ms (10 240 cycles at 8 MHz); the game polls the
;       IKBD every VBL and the reply is 9 bytes back to back (6 mouse + 3 joystick), so an ACIA interrupt that waits longer than a byte time
;       loses a byte and the mouse packet desyncs (work/notes/buserr.md).  Measured in Hatari 2.6.1: an interrupt raised during a chunk is
;       taken after up to TWO chunks (not at the first gap), so 10-row chunks (6400 cycles) gave 21 HBL = 10 750 cycles > 1.28 ms: overruns, a
;       garbage pointer position and a bus error in the VBL pointer code within a second; 8 rows still overran (21 HBL), 5 rows peak 14 HBL, 4 rows
;       peak 11 HBL (5 600 cycles, 55 % of the byte time), 2 rows 4 HBL.  The VBL and MFP interrupts are taken between chunks.  Whole copy ~134 k
;       cycles instead of 163 k.  The CPU path (ST, and whenever p4_spr did not choose the blitter) is the original routine, entered after the
;       displaced instructions.
;       Uses p4_spr's blitter decision ($bdc04 = $b17e0001: FLAGS bit0 AND the bus-error safe probe of the blitter's endmask registers, so TT / Falcon
;       and a patch set without p4_spr take the original path).  Registers as the original leaves them: a0 += 32000, a1 += 32000, d0.w = $ffff, a2 = the
;       last long of the last 8-register block read (a0 - 8), everything else restored.
BLT     equ     $bdc04
        org     $12ce0
        jmp     $da000.l

        org     $da000
cpy:    cmpi.l  #$b17e0001,BLT.l
        bne.s   orig
        movem.l d1-d2,-(a7)
        move.w  #2,$ffff8a20.w          ; source X inc
        move.w  #2,$ffff8a22.w          ; source Y inc
        move.w  #2,$ffff8a2e.w          ; dest X inc
        move.w  #2,$ffff8a30.w          ; dest Y inc
        move.w  #80,$ffff8a36.w         ; X count: one 160 byte row
        move.b  #2,$ffff8a3a.w          ; HOP = source
        move.b  #3,$ffff8a3b.w          ; LOP = S
        clr.b   $ffff8a3d.w             ; skew 0, no FXSR / NFSR
        moveq   #-1,d1
        move.w  d1,$ffff8a28.w          ; endmasks
        move.w  d1,$ffff8a2a.w
        move.w  d1,$ffff8a2c.w
        moveq   #49,d2
.l:     move.l  a0,$ffff8a24.w
        move.l  a1,$ffff8a32.w
        move.w  #4,$ffff8a38.w          ; 4 rows
        move.b  #$c0,$ffff8a3c.w        ; start, HOG
        lea     640(a0),a0
        lea     640(a1),a1
        dbra    d2,.l
        movea.l -8(a0),a2
        movem.l (a7)+,d1-d2
        move.w  #-1,d0
        rts
orig:   movem.l d1-d7/a3,-(a7)          ; the two replaced instructions
        moveq   #$20,d1
        jmp     $12ce6.l
