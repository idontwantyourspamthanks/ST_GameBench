; Powermonger WW1: hover tooltips — a one-line description of the command icon under the
; pointer, drawn into the top bar.
;
; The 1990 `pm_tooltip` design (../../done/powermonger/patches/pm_tooltip.s), with the two
; things that moved in this build corrected:
;
;   FONT      1990 $8976  ->  here runtime $8406  (text $8516)
;   composer  1990 $8838  ->  here runtime $82c8  (text $83d8)
;
; Both verified against the shipped image, not assumed:
;   * `rt $74e0` does `lea $8516(pc),a6` -> a6 = $8406, and `bsr $83d8` -> the composer.
;   * the composer is 4-phase rotate/mask/or, unrolled four times, and leaves a5 advanced by
;     exactly 8 bytes: it paints a 16-px (4 glyph) x 6-row strip per call.
;     `lea $98(a5),a5` after 8 bytes = one 160-byte screen line; at the end
;     `lea -$3b8(a5),a5` returns a5 to start+8, ready for the next four glyphs.
;   * the rotate-phases are the 8 bytes immediately before the font: `04 08 0c 00 04 08 0c 00`
;     at text $850e, read as `-$8(a6,d4.w)` .. `-$5(a6,d4.w)` with d4 = char & 3.
;   * the font decodes: 48-byte blocks, block = FONT + 48*(ch>>2), column ch & 3, six rows of
;     four plane words, colour 1 = the cell background. Rendering A-Z 0-9 gives legible
;     letterforms (work/notes/input.md section 7.4).
;   * the top bar (rows 0..5) is free from ST x=104 to 319 at the map view: measured from a
;     live screenshot, 24% occupied left of 104 (the small status icons), 0% right of it.
;
; WHY THERE IS NO CLEANUP: the site is the map pass's 32K window copy (`jsr $13a94` at
; runtime $13e0a). The hook performs that copy first, so the back buffer holds the clean
; frame, then paints into the same back buffer. The next pass's copy overwrites the text, so
; it disappears when the pointer leaves the icon. Nothing is ever erased explicitly.
;
; BUILD: vasmm68k_mot -Fbin -o tooltip.bin tooltip.s
	org	$72C00

FONT	equ	$8406
COMPOSER equ	$82c8
WCOPY	equ	$13a94			; the 32K window copy: fills the back buffer [$2ed9c]
CLIPVAR	equ	$82c4			; the composer's clip limit
BACKBUF	equ	$2ed9c
PTRX	equ	$2edb2
PTRY	equ	$2edb4

TIPCOLS	equ	24			; characters shown (6 composer calls of 4)
TIPBYTE	equ	104/2			; ST x 104 -> byte column 52
TIPROW	equ	0			; the first screen line

HOOK	movem.l	d0-d7/a0-a6,-(a7)

	jsr	WCOPY.l			; the original copy first: the back buffer is now the clean frame

	move.w	PTRX,d0
	move.w	PTRY,d1
	bsr	hit			; -> d2 = the icon id (0 = none)
	tst.w	d2
	beq	.out

	bsr	compose			; build the padded line in LINE

	movea.l	BACKBUF.l,a5
	adda.w	#TIPROW*160+TIPBYTE,a5
	lea	CLIPVAR.l,a0
	move.l	(a0),-(a7)		; SAVE the game's clip limit: the terrain renderer
	move.l	BACKBUF.l,d0		; depends on it, and clobbering it corrupts the map
	addi.l	#$7d00,d0
	lea	CLIPVAR.l,a0
	move.l	d0,(a0)		; ours, just for the composer
	lea	FONT.l,a6
	lea	LINE.l,a4
	moveq	#(TIPCOLS/4)-1,d7
.draw	bsr	COMPOSER.l		; paints 4 glyphs, leaves a5 at the next ones
	dbra	d7,.draw

	move.l	(a7)+,d0		; restore the game's clip limit
	lea	CLIPVAR.l,a0
	move.l	d0,(a0)
.out	movem.l	(a7)+,d0-d7/a0-a6
	rts

; ---------------------------------------------------------------------------------
; d0 = x, d1 = y  ->  d2 = the icon id (0 = none).
;
; Exact port of the game's perspective-grid hit test (tables $13bde/$13c58, action table
; $1a89a); the reference implementation is tools/pwwgrid.py, which is oracle-checked
; against the game.  Registers: d0=x d1=y, d2=cell, d3/d4=scratch, d5=q, d6=count,
; d7=y0 of the current line, a0=table cursor, a1=line base.
; ---------------------------------------------------------------------------------
hit	movem.l	d3-d7/a0/a1,-(a7)
	moveq	#0,d2
	lea	VG(pc),a0
	moveq	#14,d6		; 15 lines: dbra runs 15 times
.col	move.l	a0,a1			; a1 -> this line
	move.w	2(a1),d7		; y0
	addq.w	#1,d2			; col++
	bsr	lineq			; d5 = q
	move.w	d1,d3
	sub.w	d7,d3			; y - y0
	cmp.w	d5,d3
	bge.s	.rowstart		; NOT left of this line: the column is settled
	addq.l	#8,a0			; still left: try the next line
	dbra	d6,.col

.rowstart
	lea	HG(pc),a0
	moveq	#13,d6		; 14 lines: dbra runs 14 times
.row	move.l	a0,a1
	move.w	2(a1),d7
	addi.w	#$10,d2			; row += 16
	bsr	lineq
	move.w	d1,d3
	sub.w	d7,d3
	cmp.w	d5,d3
	ble.s	.lookup			; not below the line: stop
	addq.l	#8,a0
	dbra	d6,.row

.lookup	andi.w	#$ff,d2
	lea	ACT(pc),a0
	moveq	#0,d3			; the icon id
.lk	cmp.b	(a0)+,d2
	beq.s	.got
	addq.w	#1,d3
	cmp.w	#24,d3
	bge.s	.none
	bra.s	.lk
.got	move.w	d3,d2
	movem.l	(a7)+,d3-d7/a0/a1
	rts
.none	moveq	#0,d2
	movem.l	(a7)+,d3-d7/a0/a1
	rts

; a1 -> a line {x0,y0,x1,y1}; d0 = x  ->  d5 = (x-x0)*(y1-y0)/(x1-x0), a 16-bit word result
lineq	move.w	(a1),d3			; x0
	move.w	d0,d5
	sub.w	d3,d5			; x - x0
	move.w	6(a1),d3		; y1
	sub.w	2(a1),d3		; y1 - y0
	muls.w	d3,d5
	move.w	4(a1),d3		; x1
	sub.w	(a1),d3			; x1 - x0
	beq.s	.zero
	ext.l	d5
	divs.w	d3,d5
	rts
.zero	moveq	#0,d5
	rts

; ---------------------------------------------------------------------------------
; d2 = the icon id -> LINE holds TIPCOLS characters, space padded.  Clobbers d0-d3/a0/a1.
; ---------------------------------------------------------------------------------
compose	lea	TEXTS.l,a0
	move.w	d2,d0
	lsl.w	#2,d0			; 4-byte pointer per id
	adda.w	d0,a0
	move.l	(a0),a0
	lea	LINE.l,a1
	moveq	#0,d3
.cp	tst.b	(a0)
	beq	.pad
	move.b	(a0)+,(a1)+
	addq.w	#1,d3
	cmp.w	#TIPCOLS,d3
	beq	.done
	bra	.cp
.pad	move.b	#32,(a1)+
	addq.w	#1,d3
	cmp.w	#TIPCOLS,d3
	bne	.pad
.done	rts

; ---------------------------------------------------------------------------------
	even
	org	$73100			; a fixed data page: no drift, no pc-relative guessing
VG	dc.w	23,95,24,199
	dc.w	63,93,64,199
	dc.w	74,91,88,199
	dc.w	91,89,125,199
	dc.w	107,88,160,199
	dc.w	122,86,198,199
	dc.w	138,85,231,199
	dc.w	151,83,268,199
	dc.w	164,82,302,199
	dc.w	177,80,319,184
	dc.w	189,79,319,162
	dc.w	204,77,319,145
	dc.w	216,77,319,131
	dc.w	230,76,319,122
	dc.w	238,74,319,113
HG	dc.w	237,74,1,99
	dc.w	244,77,1,106
	dc.w	252,82,1,114
	dc.w	260,85,1,122
	dc.w	270,90,1,128
	dc.w	280,93,1,136
	dc.w	290,98,1,145
	dc.w	300,104,1,156
	dc.w	315,111,1,168
	dc.w	319,119,1,182
	dc.w	319,131,1,199
	dc.w	319,143,90,199
	dc.w	319,160,170,199
	dc.w	319,182,258,199
ACT		dc.b	0,234,196,215,218,180,232,233,219,213,217,0,214,216,179,163,147,0,0,164,148,132,195,131

; one pointer per icon id: id 0 is "no icon" and ids 11, 17, 18 have no cell
TEXTS	dc.l	T0,T1,T2,T3,T4,T5,T6,T7,T8,T9,T10,T0
	dc.l	T12,T13,T14,T15,T16,T0,T0,T19,T20,T21,T22,T23
T0	dc.b	"",0
T1	dc.b	"Send Captain",0
T2	dc.b	"Transfer Men",0
T3	dc.b	"Get Food",0
T4	dc.b	"Get Men",0
T5	dc.b	"Go Home",0
T6	dc.b	"Attack",0
T7	dc.b	"Invent",0
T8	dc.b	"Equip",0
T9	dc.b	"Drop Food",0
T10	dc.b	"Derank",0
T12	dc.b	"Drop Items",0
T13	dc.b	"Supply Food",0
T14	dc.b	"Trade",0
T15	dc.b	"Alliance",0
T16	dc.b	"Spy",0
T19	dc.b	"Aggressive",0
T20	dc.b	"Neutral",0
T21	dc.b	"Passive",0
T22	dc.b	"Query",0
T23	dc.b	"Option",0

	even
	org	$73600			; the composed line: its own page, 52 bytes used
LINE	ds.b	TIPCOLS+4
