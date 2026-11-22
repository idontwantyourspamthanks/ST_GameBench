; Powermonger WW1 (Cobra #26 / Fuzion build): fixed-rate world tick.
;
; The same design as work/tickproto/tick.s (the Pompey build), with every address shifted by
; the constant delta +$12686 that relates the two releases (work/notes/cobra26.md section 2).
; All seven hook sites were checked byte-identical at that offset before this file was made.
;
;   Pompey -> Cobra
;   $72000 -> $84686   the payload/code base (the free span shifts with the image)
;   $13da0 -> $26426   the pass head
;   $13e24 -> $264aa   the weather wrapper
;   $13e36 -> $264bc   the men wrapper
;   $13e42 -> $264c8   the terrain wrapper
;   $7e6   -> $12e6c   the right-latch click stamp
;   $842   -> $12ec8   the left-latch click stamp
;   $144b4 -> $26b3a   the click-expiry read
;   $13da8 -> $2642e   the world counter bump (logic entry)
;   $13dcc -> $26452   the render setup (skips the logic)
;   $2ed90 -> $41416   the world counter
;   $71b7e -> $84204   the VBL counter low word
;   $1b90a -> $2df90   the weather routine
;   $158b2 -> $27f38   the men walk
;   $74e0  -> $19b66   the render tail
;   $5a854/$5a856      the speed countdown / pause gate: same absolute addresses (they are in
;                      the same bss area in both builds)
;
; BUILD: vasmm68k_mot -Fbin -o tick26.bin tick26.s

BASE	equ	$b6000
PASS	equ	$b61e0
ACC	equ	$b61e4
LASTVBL	equ	$b61e8
KIND	equ	$b61ea

	org	BASE
	move.l	a0,-(a7)
	move.l	d0,-(a7)
	move.l	d1,-(a7)
	addq.l	#1,PASS
	move.w	$84204,d0		; the VBL counter low word
	move.w	d0,d1
	sub.w	LASTVBL,d1
	move.w	d0,LASTVBL
	bmi.s	.resync
	cmp.w	#60,d1
	bhi.s	.resync
	moveq	#6,d0			; 50 Hz
	btst.b	#1,$ff820a
	bne.s	.units
	moveq	#5,d0			; 60 Hz
.units	ext.l	d1
	mulu.w	d0,d1
	add.l	d1,ACC
	cmp.l	#225,ACC		; at most 3 ticks owed
	bls.s	.decide
	move.l	#75,ACC
	bra.s	.decide
.resync	clr.l	ACC
.decide	cmp.l	#75,ACC
	bcs.s	.rpass
	sub.l	#75,ACC
	clr.w	KIND
	cmp.l	#75,ACC
	bcs.s	.go
	move.w	#1,KIND		; S
	bra.s	.go
.rpass	move.w	#2,KIND		; R
.go	tst.w	KIND
	beq.s	.t
	cmp.w	#2,KIND
	bne.s	.t
	bra.s	.render
.t	tst.w	$5a856			; the original pause gate
	bne.s	.render
	cmp.w	#1,KIND
	bne.s	.logic
	move.w	#2,$5a854
.logic	move.l	(a7)+,d1
	move.l	(a7)+,d0
	movea.l	(a7)+,a0
	jmp	$2642e.l
.render	move.l	(a7)+,d1
	move.l	(a7)+,d0
	movea.l	(a7)+,a0
	jmp	$26452.l

; ---- wrappers --------------------------------------------------------------------
	org	$b6160
WX	tst.w	KIND
	beq.s	.wx
	cmp.w	#2,KIND
	beq.s	.wxrts
.wx	jmp	$2df90.l
.wxrts	rts

	org	$b6180
MEN	tst.w	KIND
	beq.s	.men
	cmp.w	#2,KIND
	beq.s	.menrts
.men	jmp	$27f38.l
.menrts	rts

	org	$b61a0
TER	cmp.w	#1,KIND
	beq.s	.terrts
	jmp	$19b66.l
.terrts	rts
