; name: mr_credit
; default: yes
; phase: stage1
; site: $78524
; orig: 41f9000782ba
; doc: Release credit: the line `v@VERSION@ enhanced by dad_prg` in the game's own message font at the bottom of the "Moonshine Racers" / hotrod title picture (shown while the game loads); nothing else changes.
; note: Release credit (st-game-speedup skill): `v<VERSION> enhanced by dad_prg` at the BOTTOM of the title picture ("Moonshine Racers" over the
; note: brown hotrod, MILLENNIUM / PEAK STAR logos) that the stage-1 loader shows while it loads the game (floppy: ~VBL 340-900, HD: until the
; note: loading is done).  THE ONE PLACE FOR THE VERSION is patches/VERSION: the tool substitutes @VERSION@ in the string below (`msrpatch.py version
; note: [--credit]` prints it).  Details, hook disassembly, screenshots: work/notes/credit.md.
; note: Where: stage 1 (MSR_S1.FIC unpacked at $78000; the floppy's tracks 1-5) runs `$78518 jsr $790b2` (draw the picture into the screen buffer
; note: ($78004) = $70000) then `$78524 lea $782ba.l,a0 / jsr $7910e` (start the palette fade-in) and loads the game ($78558).  The site is the
; note: `lea` (6 B): the picture is complete, the fade-in has not started, so the text fades in with the picture and nothing is ever redrawn.
; note: The blob draws the text into the buffer and replays `lea $782ba.l,a0`.  It runs BEFORE the trampoline (the game is not even loaded yet):
; note: phase `stage1` = HD: RUNME's copy routine applies the site to the unpacked stage 1 right after the payload copy; floppy: the same 6 bytes
; note: as a disk A edit (the boot sector's stage-0 loader has already put the payload in RAM); never `live` (a snapshot is past stage 1).
; note: Font: the game's own 8x8 message font (the ticker's: glyph = 16 B, 8 x (edge byte, body byte), index = char - $20; the game draws it with
; note: `$14fd4`), the 25 glyphs the line can need (all digits for the version) copied from disk A $310be = RAM $190be by work/credit/gen_glyphs.py
; note: (the font is not in RAM yet at this point of the boot).  Same drawing rule as the game's: a glyph clears the covered pixels, edge pixels get
; note: colour EDGE, body pixels BODY (palette of the picture: 7 = $765 cream = the title lettering, 5 = $654 tan = the picture frame).
; note: Where on the screen: the picture's frame ends at row 192, rows 193-199 are black between the two logos (MILLENNIUM x 8-47, PEAK STAR
; note: x 289-311).  Only 6 rows (194-199, row 193 stays black as a gap to the frame) are available for a cell, so each glyph is stored as the
; note: font cell's rows 0,2,3,4,5,6 (row 1 repeats row 0 for every stem, row 7 only holds the tails of p and y: they lose their last row), and the
; note: game's `_` (a bar in cell row 0 = an overline) is drawn in the last row.  Centred on 8-pixel cells (40 columns minus the length; the 24
; note: characters span x 64-255): no logo or art is covered.
; note: Registers: all saved but a0, which is the displaced instruction's result.  No hardware access, no game state, 68000 only.
BODY    equ     7
EDGE    equ     5
CREDITY equ     194

        org     $78524
        jsr     $bfd00.l

        org     $bfd00
credit: movem.l d0-d7/a1-a4,-(sp)
        movea.l $78004.l,a1             ; the screen buffer the picture was just drawn into
        adda.l  #CREDITY*160,a1
        lea     text(pc),a2
        movea.l a2,a3
        moveq   #-1,d6
.len:   addq.w  #1,d6
        tst.b   (a3)+
        bne.s   .len                    ; d6 = string length
        moveq   #40,d7
        sub.w   d6,d7
        lsr.w   #1,d7                   ; d7 = first 8-pixel cell (centred)
.ch:    moveq   #0,d0
        move.b  (a2)+,d0
        beq.s   .end
        lea     chars(pc),a3
        moveq   #0,d1
.f:     move.b  (a3)+,d2
        beq.s   .next                   ; not in the table: leave the cell empty
        cmp.b   d0,d2
        beq.s   .found
        addq.w  #1,d1
        bra.s   .f
.found: move.w  d1,d2
        lsl.w   #2,d2
        lsl.w   #3,d1
        add.w   d2,d1                   ; index * 12 (6 rows x 2 bytes)
        lea     glyphs(pc),a3
        adda.w  d1,a3                   ; a3 = the glyph
        move.w  d7,d3
        lsr.w   #1,d3
        lsl.w   #3,d3                   ; 8 bytes per 16 pixels
        move.w  d7,d4
        andi.w  #1,d4
        add.w   d4,d3                   ; + 1 for the right half of the 16-pixel block
        lea     (a1,d3.w),a0
        moveq   #5,d5
.row:   move.b  (a3)+,d0                ; edge pixels
        move.b  (a3)+,d1                ; body pixels
        move.b  d0,d2
        or.b    d1,d2
        not.b   d2                      ; pixels the glyph leaves alone
        lea     masks(pc),a4
        moveq   #3,d4
.pl:    move.b  (a4)+,d3
        and.b   d0,d3
        move.b  (a4)+,d6
        and.b   d1,d6
        or.b    d6,d3
        and.b   d2,(a0)
        or.b    d3,(a0)
        lea     2(a0),a0
        dbra    d4,.pl
        lea     160-8(a0),a0
        dbra    d5,.row
.next:  addq.w  #1,d7
        bra.s   .ch
.end:   movem.l (sp)+,d0-d7/a1-a4
        lea     $782ba.l,a0             ; the displaced instruction
        rts
masks:  dc.b    -((EDGE>>0)&1),-((BODY>>0)&1),-((EDGE>>1)&1),-((BODY>>1)&1)
        dc.b    -((EDGE>>2)&1),-((BODY>>2)&1),-((EDGE>>3)&1),-((BODY>>3)&1)
text:   dc.b    "v@VERSION@ enhanced by dad_prg",0
chars:  dc.b    " .0123456789abcdeghnprvy_",0
        even
glyphs:
        dc.b    $00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00   ; ' '
        dc.b    $00,$00,$00,$00,$00,$00,$00,$00,$20,$c0,$20,$c0   ; '.'
        dc.b    $02,$7c,$11,$e6,$11,$e6,$11,$e6,$11,$e6,$02,$7c   ; '0'
        dc.b    $04,$38,$04,$38,$04,$38,$04,$38,$04,$38,$04,$38   ; '1'
        dc.b    $02,$7c,$01,$06,$02,$7c,$10,$e0,$10,$e6,$02,$fc   ; '2'
        dc.b    $02,$3c,$01,$06,$02,$3c,$01,$06,$11,$e6,$02,$7c   ; '3'
        dc.b    $12,$ec,$12,$ec,$01,$7e,$02,$0c,$02,$0c,$02,$0c   ; '4'
        dc.b    $02,$fc,$10,$e0,$02,$fc,$01,$06,$11,$e6,$02,$7c   ; '5'
        dc.b    $02,$7c,$10,$e0,$02,$fc,$11,$e6,$11,$e6,$02,$7c   ; '6'
        dc.b    $01,$fe,$01,$0e,$02,$1c,$04,$38,$08,$70,$10,$e0   ; '7'
        dc.b    $02,$7c,$11,$e6,$02,$7c,$11,$e6,$11,$e6,$02,$7c   ; '8'
        dc.b    $02,$7c,$11,$e6,$01,$7e,$01,$06,$11,$e6,$02,$7c   ; '9'
        dc.b    $00,$00,$02,$3c,$01,$06,$01,$7e,$11,$e6,$01,$7e   ; 'a'
        dc.b    $10,$e0,$02,$fc,$11,$e6,$11,$e6,$11,$e6,$02,$fc   ; 'b'
        dc.b    $00,$00,$04,$78,$10,$e0,$10,$e0,$10,$e0,$02,$7c   ; 'c'
        dc.b    $01,$06,$01,$7e,$11,$e6,$11,$e6,$11,$e6,$01,$7e   ; 'd'
        dc.b    $00,$00,$02,$7c,$11,$e6,$02,$fc,$10,$e0,$02,$7c   ; 'e'
        dc.b    $00,$00,$02,$3c,$09,$76,$01,$3e,$01,$0e,$02,$7c   ; 'g'
        dc.b    $10,$e0,$02,$fc,$11,$e6,$11,$e6,$11,$e6,$11,$e6   ; 'h'
        dc.b    $00,$00,$22,$dc,$01,$fe,$11,$e6,$11,$e6,$11,$e6   ; 'n'
        dc.b    $00,$00,$02,$fc,$11,$e6,$02,$fc,$10,$e0,$10,$e0   ; 'p'
        dc.b    $00,$00,$02,$fc,$11,$e6,$10,$e0,$10,$e0,$10,$e0   ; 'r'
        dc.b    $00,$00,$11,$e6,$11,$e6,$12,$6c,$04,$38,$08,$10   ; 'v'
        dc.b    $00,$00,$11,$e6,$11,$e6,$01,$7e,$01,$06,$11,$e6   ; 'y'
        dc.b    $00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$00,$ff   ; '_'
