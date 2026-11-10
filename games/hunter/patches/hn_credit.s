; name: hn_credit
; default: yes
; version: 1.0
; site: $d61c
; orig: 4eb900010ea2
; note: Release credit (st-game-speedup skill): a small, dim version line `v<VERSION> enhanced by dad_prg` on the title screen.
; note: THE ONE PLACE FOR THE RELEASE VERSION is the `; version:` header above. huntpatch.py replaces @VERSION@ in this file, and
; note: `huntpatch.py version` prints it for tools/package.sh (zip names, PATCHES.TXT / README.TXT).
; note: Where: the game's file loader ($d53a, shared by the HD loader hook $150 and the Paper Bag floppy loader) ends with
; note: `cmpi.l #'FORM',(a0) / bne / jsr $10ea2.l` ($d614..): $10ea2 decodes an IFF ILBM picture in place at its load address
; note: ($1648(a5)).  The title picture is FILES/6 (Paper Bag file 06) loaded at $23000; it is the screen the player sees while the
; note: rest of the game loads and until SPACE.  This site is that `jsr $10ea2.l`: the hook runs it, and when the picture that
; note: was just decoded is the title (destination $23000 AND the CMAP just converted at $612a is the title's: colours 0..5)
; note: it draws the text into the bitmap and returns.  Both loaders run the same resident code ($d60a..$d624), so one
; note: boot-phase site serves HD and floppy; nothing else is touched.
; note: Text: own 4x6 font (glyphs for digits, '.', '_' and the letters of the credit), advance 5, centred (x = (321 - 5*len)/2),
; note: rows 194..199 of the 320x200 picture.  Colour index 10 (planes 1 and 3; $444 in the title palette: dim grey), plotted
; note: with OR onto pixels that are colour 0 in the picture: rows 196..199 are black everywhere, 193..195 between the side
; note: icon boxes (x 45..274) are black except the tip of the V of ACTIVISION (x 154..155, rows <= 194), where no glyph has a pixel.
; note: Font rows: bit 3 = leftmost column; lower case uses rows 1..4, ascenders (b d h) and digits row 0, descenders (g p y) row 5.
SCR     equ     $23000+194*160          ; first text row of the title bitmap (160 bytes per row, 4 interleaved planes)

        org     $d61c
        jsr     $8d400.l

        org     $8d400
credit: jsr     $10ea2.l                ; the original call: decode the IFF picture in place
        cmpi.l  #$23000,$1648(a5)       ; $1648(a5) = destination of the file just loaded
        bne.w   .done
        lea     $612a.l,a0              ; CMAP of that picture, converted to 12-bit words
        cmpi.l  #$00000006,(a0)+        ; title palette: 000 006 028 04a 26c 48e
        bne.w   .done
        cmpi.l  #$0028004a,(a0)+
        bne.w   .done
        cmpi.l  #$026c048e,(a0)+
        bne.w   .done
        movem.l d0-d7/a0-a2,-(sp)
        lea     text(pc),a0
        movea.l a0,a1
.len:   tst.b   (a1)+
        bne.s   .len
        move.l  a1,d4
        sub.l   a0,d4
        subq.w  #1,d4                   ; len
        mulu    #5,d4
        neg.w   d4
        add.w   #321,d4
        lsr.w   #1,d4                   ; d4 = x of the first glyph = (321 - 5*len) / 2
.char:  moveq   #0,d0
        move.b  (a0)+,d0
        beq.s   .end
        lea     chars(pc),a1
        moveq   #0,d1
.find:  move.b  (a1)+,d2
        beq.s   .next                   ; not in the font: blank cell
        cmp.b   d2,d0
        beq.s   .got
        addq.w  #1,d1
        bra.s   .find
.got:   mulu    #6,d1
        lea     font(pc),a1
        adda.w  d1,a1                   ; 6 rows of this glyph
        lea     SCR.l,a2
        moveq   #5,d3
.row:   move.b  (a1)+,d0
        move.w  d4,d5                   ; x of column 0
        moveq   #3,d6                   ; bit 3 = leftmost column
.col:   btst    d6,d0
        beq.s   .np
        move.w  d5,d7
        lsr.w   #4,d7
        lsl.w   #3,d7                   ; 16-pixel group * 8 bytes
        move.w  d5,d1
        and.w   #15,d1
        move.w  #$8000,d2
        lsr.w   d1,d2                   ; pixel mask
        or.w    d2,2(a2,d7.w)           ; colour 10 = %1010: plane 1 ...
        or.w    d2,6(a2,d7.w)           ; ... and plane 3
.np:    addq.w  #1,d5
        dbra    d6,.col
        lea     160(a2),a2
        dbra    d3,.row
.next:  addq.w  #5,d4
        bra.s   .char
.end:   movem.l (sp)+,d0-d7/a0-a2
.done:  rts

text:   dc.b    "v@VERSION@ enhanced by dad_prg",0
chars:  dc.b    " .0123456789_abcdeghnprvy",0
font:                                   ; 6 rows per glyph, in the order of `chars`
        dc.b    %0000,%0000,%0000,%0000,%0000,%0000    ; ' '
        dc.b    %0000,%0000,%0000,%0000,%1000,%0000    ; '.'
        dc.b    %0110,%1001,%1001,%1001,%0110,%0000    ; '0'
        dc.b    %0100,%1100,%0100,%0100,%1110,%0000    ; '1'
        dc.b    %0110,%1001,%0010,%0100,%1111,%0000    ; '2'
        dc.b    %1110,%0001,%0110,%0001,%1110,%0000    ; '3'
        dc.b    %1001,%1001,%1111,%0001,%0001,%0000    ; '4'
        dc.b    %1111,%1000,%1110,%0001,%1110,%0000    ; '5'
        dc.b    %0110,%1000,%1110,%1001,%0110,%0000    ; '6'
        dc.b    %1111,%0001,%0010,%0100,%0100,%0000    ; '7'
        dc.b    %0110,%1001,%0110,%1001,%0110,%0000    ; '8'
        dc.b    %0110,%1001,%0111,%0001,%0110,%0000    ; '9'
        dc.b    %0000,%0000,%0000,%0000,%0000,%1111    ; '_'
        dc.b    %0000,%0110,%0001,%0111,%1011,%0000    ; 'a'
        dc.b    %1000,%1110,%1001,%1001,%1110,%0000    ; 'b'
        dc.b    %0000,%0111,%1000,%1000,%0111,%0000    ; 'c'
        dc.b    %0001,%0111,%1001,%1001,%0111,%0000    ; 'd'
        dc.b    %0000,%0110,%1001,%1111,%0111,%0000    ; 'e'
        dc.b    %0000,%0111,%1001,%0111,%0001,%0110    ; 'g'
        dc.b    %1000,%1110,%1001,%1001,%1001,%0000    ; 'h'
        dc.b    %0000,%1110,%1001,%1001,%1001,%0000    ; 'n'
        dc.b    %0000,%1110,%1001,%1001,%1110,%1000    ; 'p'
        dc.b    %0000,%1011,%1100,%1000,%1000,%0000    ; 'r'
        dc.b    %0000,%1001,%1001,%1001,%0110,%0000    ; 'v'
        dc.b    %0000,%1001,%1001,%0111,%0001,%0110    ; 'y'
