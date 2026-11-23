; Probe: call the game's composer ($82c8) the way its own caller does, and see what appears.
;
; Known from the live caller at rt $74e0 (text $75f0):
;   a6 = the font base (rt $8406)
;   a4 = a descriptor: [width-1][height-1][width*4 character codes]
;   a5 = destination = screenbase + row*$a0 + col*8
;   [$82c4] = the clip limit (screenbase + $7d00)
;   d0/d1/d2/d3/d4 = the loop counters the composer manages itself
;
; This probe draws "ABCDEFGH" at screen (200, 2) into the BACK buffer and returns, so a
; screenshot taken straight after shows whether the contract above is right.
;
; BUILD: vasmm68k_mot -Fbin -o ttprobe.bin ttprobe.s
	org	$72C00

FONT	equ	$8406

PROBE	movem.l	d0-d7/a0-a6,-(a7)

	movea.l	$2ED9C.l,a5		; the back buffer
	move.l	a5,d0
	adda.l	#$7D00,a5		; ... its end
	move.l	a5,$82C4		; the clip limit the composer tests

	movea.l	$2ED9C.l,a5		; back to the start
	adda.w	#(2*160)+100,a5		; ST row 2, byte column 100 (= px 200)

	lea	FONT.l,a6
	lea	DESC(pc),a4
	jsr	$82C8.l

	movem.l	(a7)+,d0-d7/a0-a6
	rts

	even
; width-1 = 1 (so 2 groups of 4 = 8 characters), height-1 = 0 (one row)
DESC	dc.b	1,0
	dc.b	"ABCDEFGH"
	even
