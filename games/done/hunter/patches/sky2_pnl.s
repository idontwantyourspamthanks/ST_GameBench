; name: sky2_pnl
; default: yes
; site: $8142
; orig: 41ea258043eb2580
; requires: sky_vbl
; note: The Amiga's dashboard, part 7 of 7 (work/notes/panel.md): on machines with 2 MB or more the panel is drawn with the Amiga's bitmap and colours.
; note: This patch: (1) the art hook, `jsr` from $8142 inside the panel setup $8122, after the first of its two picture copies
; note: (`lea (a2),a0 / lea (a3),a1 / bsr $8162`: FILES/8 rows 0-59 -> the HUD master a3 = $3682c, 9,600 bytes).  When SKY_CFG bit 3 is set
; note: (sky_vbl sets it at the first VBL if memcntlr $424 says 2 MB or more) and the sky is on (V_ST = $7f), it unpacks the Amiga panel (the
; note: 'HPAN' block that snd_build.py appends to the sample bank, PANDATA = $AE4E0) over the master, checks the word sum and sets
; note: V_PAN; any failure puts the ST art back with the game's own copy loop.  (2) pnl_pal: the panel palette (the block's 16 Amiga
; note: colours scaled by the panel level, packed by the game's own $67fc) for sky_vbl's per-frame split.  The two original
; note: instructions are re-executed here (a0, a1 = the second copy's addresses); every register is preserved.
SKY     equ     $8f100
SKYV    equ     $8ecea
PANDATA equ     $ae4e0
ST_ON   equ     $7f
V_ST    equ     1
V_KEY   equ     6
V_PNEED equ     11
V_PAN   equ     15                      ; Amiga art is in the HUD master
V_PPAL  equ     112

        org     $8142
        jsr     $8ed80.l                ; pnl_art: replaces `lea $2580(a2),a0 / lea $2580(a3),a1`
        nop

        org     $8ed80
        bra.w   pnl_art                 ; PNL+0
        bra.w   pnl_pal                 ; PNL+4

; ---- the art hook: a2 = the picture buffer, a3 = the HUD master (the game's registers) --------------------------------
pnl_art:
        movem.l d0-d2/a0-a1/a4,-(sp)
        lea     SKYV.l,a0
        cmpi.b  #ST_ON,V_ST(a0)
        bne.s   .out
        btst    #3,SKY+28.l
        beq.s   .out
        lea     PANDATA.l,a1
        cmpi.l  #'HPAN',(a1)+
        bne.s   .out
        cmpi.w  #9600,(a1)+
        bne.s   .out
        move.w  (a1),d2                 ; expected word sum
        lea     34(a1),a0               ; the HLZ stream (4 + 2 + 2 + 32 bytes in)
        movea.l a3,a1
        lea     9600(a3),a4             ; the stream may not run past the master (the next copy overwrites a short overshoot)
        bsr.s   pnl_unpack
        lea     9600(a3),a0
        cmpa.l  a0,a1                   ; exactly 9,600 bytes out
        bne.s   .bad
        move.w  #4799,d0                ; word sum of the master
        moveq   #0,d1
        movea.l a3,a0
.sum:   add.w   (a0)+,d1
        dbra    d0,.sum
        cmp.w   d2,d1
        bne.s   .bad
        lea     SKYV.l,a0
        st      V_PAN(a0)
        move.w  #-1,V_KEY(a0)           ; the panel palette must be computed again
        bra.s   .out
.bad:   movea.l a2,a0                   ; put the ST art back: the game's own copy loop
        movea.l a3,a1
        jsr     $8162.l
.out:   movem.l (sp)+,d0-d2/a0-a1/a4
        lea     $2580(a2),a0            ; the two original instructions
        lea     $2580(a3),a1
        rts

; a0 = HLZ stream, a1 = destination, a4 = limit; returns a1 = end.  Uses d0-d2, a2.
pnl_unpack:
        movem.l d0-d2/a2,-(sp)
.next:  cmpa.l  a4,a1
        bhi.s   .end
        moveq   #0,d0
        move.b  (a0)+,d0
        beq.s   .end
        bmi.s   .match
        subq.w  #1,d0
.lit:   move.b  (a0)+,(a1)+
        dbra    d0,.lit
        bra.s   .next
.match: move.w  d0,d1
        andi.w  #$3f,d0
        moveq   #0,d2
        move.b  (a0)+,d2
        btst    #6,d1
        beq.s   .go
        lsl.w   #8,d2
        move.b  (a0)+,d2
        addq.w  #1,d0                   ; long: c + 3 bytes
.go:    addq.w  #1,d0                   ; short: c + 2 bytes (dbra counts one less)
        movea.l a1,a2
        suba.l  d2,a2
.cp:    move.b  (a2)+,(a1)+
        dbra    d0,.cp
        bra.s   .next
.end:   movem.l (sp)+,d0-d2/a2
        rts

; ---- pnl_pal: called by sky_vbl's sky_colours.  d3 = panel level 0..15, a4 = SKYV.  Sets V_PNEED and fills V_PPAL with the
; ---- Amiga colours at that level: gun * level / 15 rounded, so level 15 is exact; the game's $67fc packs them (STE or ST form).
pnl_pal:
        movem.l d0-d2/d4/d6/a0/a2,-(sp)
        st      V_PNEED(a4)
        lea     PANDATA+8.l,a0
        lea     V_PPAL(a4),a2
        move.w  d3,d4
        mulu.w  #17,d4                  ; level * 17: gun * level * 17 >> 8 = gun * level / 15
        moveq   #15,d6
.c:     move.w  (a0)+,d0
        moveq   #0,d2
        moveq   #2,d1
.g:     move.w  d0,-(sp)
        andi.w  #$f,d0
        mulu.w  d4,d0
        addi.w  #128,d0
        lsr.w   #4,d0
        andi.w  #$f0,d0
        ror.w   #4,d2
        or.b    d0,d2
        move.w  (sp)+,d0
        lsr.w   #4,d0
        dbra    d1,.g
        jsr     $67fc.l
        move.w  d2,(a2)+
        dbra    d6,.c
        movem.l (sp)+,d0-d2/d4/d6/a0/a2
        rts
