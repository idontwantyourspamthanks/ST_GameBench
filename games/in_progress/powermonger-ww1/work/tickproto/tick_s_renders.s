; Powermonger WW1: fixed-rate world tick — LIVE PROTOTYPE (not a delivered patch yet)
;
; The 1990 Powermonger tick design (../../done/powermonger/patches/tick_*.s) transposed to
; the WW1 engine. Evidence and the site map: work/notes/frameloop.md section 3.
;
; Main loop (map view): $13d58..$145fe, back edge `bra.w $13d58`.
;   $13da0  tst.w $5a856        ; the pause gate (the pass head hook site)
;   $13da8  addq.l #1,$2ed90    ; the world/pass counter
;   $13db4..$13dc6              ; the four world-logic calls
;   $13dcc  clr.w $13ccc        ; the render flag
;   $13de8  subi.w #1,$5a854    ; the speed countdown ($5a852 = the period)
;   $13e04  jsr $e04            ; the VBL wait (inside the render branch)
;   $13e24  jsr $1b90a          ; the weather/season animation (world)
;   $13e36  jsr $158b2          ; the men/entity walk (world)
;   $13e42  jsr $74e0           ; the terrain/pattern render (render)
;   $145da  tst.w $13ccc / jsr $e0e   ; the flip, gated by the render flag
;   $145fe  bra.w $13d58        ; the pass end
;
; Pass kinds:  T (a world tick due) = the original pass;
;              S (another tick owed) = the tick logic + the men, no render (no wait/copy/
;                  HUD/terrain, no flip: park the countdown at 2 so $13de8 skips);
;              R (ahead of real time) = render only: the head jumps to $13dcc, the weather
;                  and the men wrappers skip themselves.
; VBL counter $71b7c (low word $71b7e), the VBL flag $2edac. Real time in 1/300 s units:
; a 50 Hz VBL = 6, 60 Hz = 5 (the shifter sync bit $ff820a bit 1; verify live).
; TICK = 75 = 0.25 s = 4.00 world steps/s.
; The click lifetime: the latch copies the world counter $2ed90 to $2ed94 at $7e4/$840 and
; the tail clears the latch when $2ed90 != $2ed94 at $144b2. Those three source operands
; are redirected to PASS (bumped every pass), so a click lives one pass, not one tick.
;
; BUILD: vasmm68k_mot -Fbin -o tick.bin tick.s   (org $72000: the free-RAM span
; $72000-$c1cff at the map view, work/notes/frameloop.md section 4).

	org	$72000
CODE	equ	$72000

; ---- entry from the pass head ($13da0) -------------------------------------------
HEAD	equ	$72000
	move.l	a0,-(a7)
	move.l	d0,-(a7)		; d1 is live at $13da0 (the scroll value); keep everything
	move.l	d1,-(a7)

; the pass counter PASS, bumped on every pass (T, S and R)
	addq.l	#1,PASS

; ---- real time: delta VBLs * (6 or 5) units, 1/300 s -----------------------------
	move.w	$71b7e,d0		; the VBL counter low word
	move.w	d0,d1
	sub.w	LASTVBL,d1
	move.w	d0,LASTVBL
	bmi.s	.resync			; a backwards counter
	cmp.w	#60,d1			; a gap of > 60 VBL (1.2 s) re-syncs
	bhi.s	.resync
	moveq	#6,d0			; 50 Hz
	btst.b	#1,$ff820a
	bne.s	.units
	moveq	#5,d0			; 60 Hz
.units	ext.l	d1
	mulu.w	d0,d1
	add.l	d1,ACC
; at most 3 ticks owed (the 1990 tick_head rule): a backlog beyond 3 ticks means the
; machine cannot keep up; drop it (keep exactly one owed tick) instead of starving the
; render forever
	cmp.l	#225,ACC
	bls.s	.decide
	move.l	#75,ACC
	bra.s	.decide
.resync	clr.l	ACC

; ---- decide the pass kind ---------------------------------------------------------
.decide	cmp.l	#75,ACC
	bcs.s	.rpass			; ACC < TICK: render only
	sub.l	#75,ACC
	clr.w	KIND			; T
	cmp.l	#75,ACC
	bcs.s	.go
	move.w	#1,KIND		; S: another tick owed
	bra.s	.go
.rpass	move.w	#2,KIND		; R

.go	tst.w	KIND			; R: skip the world logic (the head -> the render setup)
	beq.s	.t
	cmp.w	#2,KIND
	bne.s	.t
	bra.s	.render
.t	tst.w	$5a856			; the original pause gate
	bne.s	.render
.logic	move.l	(a7)+,d1
	move.l	(a7)+,d0
	movea.l	(a7)+,a0
	jmp	$13da8.l		; the world counter + the logic calls
.render	move.l	(a7)+,d1
	move.l	(a7)+,d0
	movea.l	(a7)+,a0
	jmp	$13dcc.l		; the render setup (skips the logic)

; ---- wrappers at the three world/render call sites --------------------------------
; weather $13e24: world -> skip on R
	org	$720e0
WX	tst.w	KIND
	beq.s	.wx
	cmp.w	#2,KIND
	beq.s	.wxrts
.wx	jmp	$1b90a.l
.wxrts	rts

; men $13e36: world -> skip on R
	org	$72110
MEN	tst.w	KIND
	beq.s	.men
	cmp.w	#2,KIND
	beq.s	.menrts
.men	jmp	$158b2.l
.menrts	rts

; terrain $13e42: always rendered (S renders like T in this variant)
	org	$72140
TER	jmp	$74e0.l

; ---- variables -------------------------------------------------------------------
PASS	equ	$72180
ACC	equ	$72184
LASTVBL	equ	$72188
KIND	equ	$7218a
