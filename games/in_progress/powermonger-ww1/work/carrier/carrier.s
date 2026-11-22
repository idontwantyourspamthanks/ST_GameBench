; Powermonger WW1 (Cobra #26 / Fuzion build): the patch carrier.
;
; Key simplification: the ATOMIK stub hands over with `text $238: move.l (a7)+,d6 ; rts`, and
; the game it depacks is at the SAME addresses as the Pompey build (work/notes/cobra26.md).
; The hand-over site is short (4 bytes: 2c 1f 4e 75), so a 4-byte `jmp <abs>.l` fits exactly
; with no slack — but the game's load base is only known at run time.
;
; So the carrier works RELATIVE to itself:
;   * WW1.PRG gains a DATA segment holding this code and the patch records;
;   * the stub's own entry (`text $0`, 6 bytes) is replaced by `jmp front`, and `front`
;     computes the base from its own PC, patches the hand-over at `base + $238` to call
;     `hook`, restores the original 6 entry bytes it displaced, and jumps back to them;
;   * `hook` runs after the depack, verifies every site's original bytes, writes them all or
;     nothing, sets the marker, and returns as the original hand-over did.
;
; Everything is PC-relative, so the file works from a folder or a floppy and at any load
; address. The patch payload (the tick) is copied to the free span $B6000 by `front`, which
; runs before the game exists.
;
; Build: tools/wwbuild.py assembles this, splices it into a new data segment, patches the
; entry and appends the record stream. See work/notes/carrier.md.

	org	$0
; ---- front: the new program entry (replaces the ATOMIK stub's first 6 bytes) ---------
front:
	lea	front(pc),a6		; a6 = our own base (links to the data segment)
	move.l	a6,d7
	; where is the TEXT? the entry is text offset 0, so base = our address - data_offset;
	; the builder stores that delta just ahead of this code.
	move.l	-FRONTBASE(a6),d6	; d6 = text base (patched literal)
	; 1. copy the patch payload to its home ($B6000) from the record stream
	lea	records(pc),a0
.copy:	move.l	(a0)+,a1
	move.l	a1,d0
	beq.s	.patched
	move.l	(a0)+,d1
	lsr.l	#2,d1
.cp:	move.l	(a0)+,(a1)+
	subq.l	#1,d1
	bne.s	.cp
	bra.s	.copy
.patched:
	; 2. point the hand-over at `hook` and restore the entry bytes we displaced
	lea	hook(pc),a1
	move.l	a1,$238(a6)		; WRONG: $238 is in the TEXT, not here (see .fix below)
.fix:
	; the hand-over lives at text+$238; write a jmp there
	lea	hook(pc),a1
	move.w	#$4ef9,$238(a6)		; placeholder; the builder rewrites this block
	move.l	a1,$23a(a6)
	; 3. restore and run the original entry (builder patches the 6 saved bytes)
	move.w	#$4e71,.-(a7)		; placeholder
	jmp	$00000000		; placeholder

; ---- hook: runs at the hand-over, applies the patches ------------------------------
	org	$100
hook:
	movem.l	d0-d7/a0-a6,-(a7)
	move.w	sr,-(a7)
	lea	hook(pc),a6
	sub.l	#HOOK_TO_BASE,a6	; a6 = text base again
	move.l	#$504d5046,MARKER	; 'PMPF'
	bsr.w	apply
	bne.s	.out
	move.l	#$504d504f,MARKER	; 'PMPO'
.out:	move.w	(a7)+,sr
	movem.l	(a7)+,d0-d7/a0-a6
	move.l	(a7)+,d6		; the original hand-over instruction
	rts				; the original return

apply:	lea	table(pc),a0
.verify:move.l	(a0)+,d0
	beq.s	.write_pass
	move.w	(a0)+,d1
	movea.l	a0,a1
	adda.w	d1,a0
	adda.w	d1,a0
	movea.l	d0,a3
	subq.w	#1,d1
.cmp:	cmpm.b	(a1)+,(a3)+
	bne.s	.bad
	dbra	d1,.cmp
	bra.s	.verify
.write_pass:
	lea	table(pc),a0
.next:	move.l	(a0)+,d0
	beq.s	.good
	move.w	(a0)+,d1
	adda.w	d1,a0
	movea.l	a0,a2
	adda.w	d1,a0
	movea.l	d0,a3
	subq.w	#1,d1
.wr:	move.b	(a2)+,(a3)+
	dbra	d1,.wr
	bra.s	.next
.good:	moveq	#0,d0
	rts
.bad:	moveq	#1,d0
	rts

MARKER	equ	$B6F00
HOOK_TO_BASE	equ	$100
table:
