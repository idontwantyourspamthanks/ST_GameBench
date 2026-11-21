; Powermonger WW1: keyboard shortcuts — LIVE PROTOTYPE
;
; The 1990 qol_keys design (../../done/powermonger/patches/qol_keys.s, work/notes/qol.md)
; transposed to the WW1 engine: a letter key does exactly what the click on its command
; icon does. The keys are captured in the IKBD interrupt into a pending slot; the pass
; consumes it just before the game's own click dispatch and writes the same words a real
; click writes (the click position inside the icon's cell + the left latch + the pass
; stamp), so the game handles it identically.
;
; Sites (live original bytes, from work/dumps/mapview_live.bin):
;   $f30   `move.b d0,$1d2b0` (13c0 0001d2b0) -> jsr KEYHOOK   the IKBD key path store
;   $13e6a `jsr $d62a` (4eb9 0000d62a)       -> jsr CELLHOOK  just before the input section
; The click words (frameloop.md/input.md): $2edae/$2edb0 = the click x/y, $2edb6 = the left
; latch, $2ed94 = the stamp copied from the world counter $2ed90 (tick_click redirects those
; to PASS in the tick build; reading $2ed90 here works in both builds).
;
; The command cells: the 1990 game's icon rectangles (../../done/powermonger work/notes/
; tooltip.md section 1.1; the user's manual: the WW1 has the same icons in the same places).
; Verified live on the WW1: Option opens its window, Get Men starts the men, Attack + a
; village target fights.
;
; BUILD: vasmm68k_mot -Fbin -o keys.bin keys.s   (org $72400, above the tick prototype)

	org	$72400

; ---- IKBD key path: remember a command key ----------------------------------------
KEYHOOK	move.l	d1,-(a7)
	tst.b	d0			; bit 7 set = a key release: ignore
	bmi.s	.store
	andi.w	#$ff,d0
	lea	KEYTAB(pc),a0
.loop	move.b	(a0)+,d1		; the scancode
	beq.s	.store			; end of table
	addq.w	#1,a0			; skip the pad
	cmp.b	d1,d0
	beq.s	.found
	addq.w	#4,a0			; skip x/y -> the next entry (6-byte stride)
	bra.s	.loop
.found	move.w	(a0)+,PENDX		; the cell x
	move.w	(a0)+,PENDY		; the cell y
.store	move.l	(a7)+,d1
	move.b	d0,$1d2b0.l		; the original store
	rts

; ---- just before the input section: turn a pending key into a click ---------------
	org	$72480
CELLHOOK	move.l	d0,-(a7)
	move.l	d1,-(a7)
	move.l	a0,-(a7)
	tst.w	RELEASE		; a synthetic click from the last pass: release it
	beq.s	.click
	clr.w	RELEASE
	clr.w	$2edbc.l		; the down-seen, as the IKBD release does
.click	move.w	PENDX,d0
	beq.s	.done			; nothing pending
	clr.w	PENDX
	move.w	d0,$2edae.l		; the click x
	move.w	d0,$2edb2.l		; and the tracked pointer x (the hover words)
	move.w	PENDY,$2edb0.l		; the click y
	move.w	PENDY,d1
	move.w	d1,$2edb4.l		; the tracked pointer y
	move.w	#1,$2edb6.l		; the left latch
	move.w	#1,$2edbc.l		; the down-seen (a real button event sets it)
	move.w	#1,RELEASE
	move.l	$2ed90.l,d1		; the stamp (works with or without tick_click)
	move.l	d1,$2ed94.l
.done	movea.l	(a7)+,a0
	move.l	(a7)+,d1
	move.l	(a7)+,d0
	jmp	$d62a.l			; the original call (its clobbers pass through)

; ---- the key table: {scancode, pad, x, y} x N, 0 ends ----------------------------
; letters: A attack, D drop food, E equip, F get food, G send captain, H go home,
; I invent, L alliance, M get men, N drop items, O option, Q query, R derank,
; S supply food, T trade, X transfer men, Y spy; 1/2/3 the postures.
	org	$72500
KEYTAB	dc.b	$1e,0
	dc.w	299,182			; A  Attack
	dc.b	$20,0
	dc.w	142,193			; D  Drop Food
	dc.b	$12,0
	dc.w	297,156			; E  Equip
	dc.b	$21,0
	dc.w	201,181			; F  Get Food
	dc.b	$22,0
	dc.w	299,182			; G  Send Captain
	dc.b	$23,0
	dc.w	100,170			; H  Go Home
	dc.b	$17,0
	dc.w	274,187			; I  Invent
	dc.b	$26,0
	dc.w	73,161			; L  Alliance
	dc.b	$32,0
	dc.w	275,162			; M  Get Men (verified live)
	dc.b	$31,0
	dc.w	173,188			; N  Drop Items
	dc.b	$18,0
	dc.w	71,138			; O  Option (verified live)
	dc.b	$10,0
	dc.w	75,191			; Q  Query
	dc.b	$13,0
	dc.w	252,168			; R  Derank
	dc.b	$1f,0
	dc.w	227,174			; S  Supply Food
	dc.b	$14,0
	dc.w	74,175			; T  Trade
	dc.b	$2d,0
	dc.w	103,186			; X  Transfer Men
	dc.b	$15,0
	dc.w	72,149			; Y  Spy
	dc.b	$02,0
	dc.w	92,135			; 1  Passive posture
	dc.b	$03,0
	dc.w	94,145			; 2  Neutral posture
	dc.b	$04,0
	dc.w	97,156			; 3  Aggressive posture
	dc.b	0

; ---- variables (clear of the code and the table) ---------------------------------
PENDX	equ	$72800
PENDY	equ	$72802
RELEASE	equ	$72804
