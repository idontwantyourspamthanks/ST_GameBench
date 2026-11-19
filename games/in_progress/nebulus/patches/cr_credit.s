; Nebulus release credit line (cr_credit), shown on the frog-on-a-plinth title page only.
; Hook site $3d698 (8 bytes `move.w #$fffe,$38212.l`, reached after the title page is drawn, before the first flip) = jsr CR / nop.
; Page word $3d5b6: 0 = this title page, 1 = High Scorers, 2 = options list: the credit is printed only for page 0.
; Text goes through the game's own centred printer sub_03b360 (a0 = string, d0 = line 0..5; line 3 = screen row 144, the empty
; line between "(c)1987,8 Hewson" and "Mission #n"), i.e. the title font and the game's own per-line colour.
; Generated into patches/cr_credit.nep by tools/nebrelease.py (version text from patches/VERSION); `org` is the blob address.
	move.w #$fffe,$38212.l
	tst.w $3d5b6.l
	bne.s out
	movem.l d0-d2/a0,-(a7)
	lea str(pc),a0
	moveq #3,d0
	jsr $3b360.l
	movem.l (a7)+,d0-d2/a0
out:
	rts
str:
	dc.b '@TEXT@',0
	even
