; name: p6_cpy
; default: yes
; stage: 2
; site: $12ce0
; orig: 48e77f107220
; note: PMPerf2, work/notes/hotpaths2.md.  The 3D window copy `$12ce0` (the 32000 B picture $78000 -> back buffer at the start of every
;       rendered pass, 163 k cycles = 10-11 % of a pass) on the STE blitter: 20 chunks of 10 rows (800 words, 6400 cycles each, HOG), so the
;       bus is held for 0.8 ms at most (a 7812 baud keyboard byte takes 1.28 ms: the ACIA cannot overrun; the VBL and MFP interrupts are taken
;       between chunks).  Whole copy 131 k cycles instead of 163 k.  The CPU path (ST, and whenever p4_spr did not choose the blitter) is the
;       original routine, entered after the displaced instructions.
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
        moveq   #19,d2
.l:     move.l  a0,$ffff8a24.w
        move.l  a1,$ffff8a32.w
        move.w  #10,$ffff8a38.w         ; 10 rows
        move.b  #$c0,$ffff8a3c.w        ; start, HOG
        lea     1600(a0),a0
        lea     1600(a1),a1
        dbra    d2,.l
        movea.l -8(a0),a2
        movem.l (a7)+,d1-d2
        move.w  #-1,d0
        rts
orig:   movem.l d1-d7/a3,-(a7)          ; the two replaced instructions
        moveq   #$20,d1
        jmp     $12ce6.l
