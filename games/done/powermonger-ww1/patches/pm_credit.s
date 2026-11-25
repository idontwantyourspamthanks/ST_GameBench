; name: pm_credit
; default: yes
; site: $14baa
; orig: 4eb9000074e0
; note: release credit: a small version line "v<VERSION> enhanced by dad_prg" at the very bottom of the main menu screen
;       (Welcome to the World War I Scenario / START NEW CONQUEST / CONTINUE CONQUEST / PLAY RANDOM LAND), screen rows 194-199
;       (the 6 bottom rows), centred, in the game's 4x6 font ($8406) drawn in ONE palette colour (COLOUR below, colour 2 = $332, a dim
;       olive grey already in the screen's palette; the palette is untouched).  Port of master's pm_credit (games/done/powermonger).
;       THE VERSION LIVES HERE ONLY (the `TXT:` line at the end; tools/package.sh reads it for the zip names and the READMEs).
;       Site: `jsr $74e0` at $14baa = the window drawing call of the menu's own loop (master $13e24 -> WW1 $14baa, confirmed: a Hatari
;       breakpoint there is hit while the menu is up).  The hook runs the original `jsr $74e0`, then draws only if the window table $74c0
;       holds a window AND its text buffer ($7658, the instance copy the game makes of the window) starts with "Welc".
;       The menu is redrawn over itself every pass, so the credit is stored every pass into the back buffer [$2ed9c] (master $2df7c).
;       Font cells: block ch>>2 of 48 B (6 rows x 4 planes x 1 word) at $8406, column ch&3 of the 16-px word = the glyph; colour 1 is
;       the glyph background, colours >= 2 are ink, so ink = plane1|plane2|plane3.  The ink mask is output in COLOUR.
;       The text is padded to whole 16-px words and centred by whole words; the rows are blank in the menu, so the words are stored.
COLOUR  equ     2                       ; palette index of the ink (bit n of the index -> plane n)
FONT    equ     $8406
ROW0    equ     194                     ; first of the 6 bottom rows

        org     $14baa
        jsr     $72800.l

        org     $72800
pl      macro                           ; d3 = the 16 ink pixels: store as plane \1 of COLOUR
        ifne    (COLOUR>>\1)&1
        move.w  d3,(a3)+
        endc
        ifeq    (COLOUR>>\1)&1
        clr.w   (a3)+
        endc
        endm
NW      equ     (TXTE-TXT+3)/4          ; 16-px words (4 characters each)
COL0    equ     (20-NW)/2               ; first 16-px word column (centred)

hook:   jsr     $74e0.l
        tst.w   $74c0.l                 ; a window is open
        beq.s   .out
        cmpi.l  #$57656c63,$7658.l      ; "Welc": and it is the main menu ("Welcome to the World ...")
        bne.s   .out
        movem.l d0-d7/a0-a3,-(a7)
        movea.l $2ed9c.l,a1
        lea     ROW0*160+COL0*8(a1),a1
        moveq   #0,d6                   ; d6 = row * 8 (offset into a font block)
        moveq   #5,d7
.row:   lea     TXT(pc),a2
        movea.l a1,a3
        moveq   #NW-1,d5
.word:  moveq   #0,d3
        moveq   #3,d4
.cell:  moveq   #0,d0
        move.b  (a2)+,d0
        move.w  d0,d1
        lsr.w   #2,d1
        mulu.w  #48,d1
        lea     FONT.l,a0
        adda.w  d1,a0
        adda.w  d6,a0
        move.w  2(a0),d2
        or.w    4(a0),d2
        or.w    6(a0),d2                ; ink mask of the 4 columns
        and.w   #3,d0
        lsl.w   #2,d0
        addq.w  #4,d0
        rol.w   d0,d2                   ; this character's column -> bits 3..0
        and.w   #$f,d2
        rol.w   #4,d3
        or.w    d2,d3
        dbra    d4,.cell
        pl      0
        pl      1
        pl      2
        pl      3
        dbra    d5,.word
        lea     160(a1),a1
        addq.w  #8,d6
        dbra    d7,.row
        movem.l (a7)+,d0-d7/a0-a3
.out:   rts

; THE VERSION: the number in this one line (tools/package.sh reads it with `sed -n 's/^TXT:.*"v\([^ ]*\) enhanced by dad_prg".*/\1/p'`).
; The text is space padded to whole 16-px words (NW).
TXT:    dc.b    "v1.0 enhanced by dad_prg"
TXTE:   dcb.b   (4-((TXTE-TXT)&3))&3," "
