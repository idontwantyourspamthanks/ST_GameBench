; name: pop_credit
; default: yes
; version: 1.0
; prog: demo
; site: $b42a
; orig: 33fc00020004c576
; note: Release credit (st-game-speedup skill): a small, dim `v@VERSION@ enhanced by dad_prg` on the TUTORIAL / CONQUEST / CUSTOM
; note: menu screen (DEMO.TOS, the picture LOAD.PIC) that every start passes.  The line sits at the bottom edge of the picture,
; note: right of the "COPYRIGHT BULLFROG 1989" caption, 4 x 6 pixel cells with our own 3 x 5 font, colour index 8 ($444, the
; note: dark grey of the picture's palette).  Only glyph pixels are written, so the rest of the picture is untouched.
; note: THE ONE PLACE FOR THE RELEASE VERSION is the `; version:` header above: poppatch.py substitutes it for the placeholder
; note: token in the string below and `poppatch.py version` prints it (README, zip names).
; note: Where (disassembly of DEMO.TOS, work/notes/delivery.md): sub_00b33c loads LOAD.PIC to the screen buffer ($12fa4 holds its
; note: address) and sets the palette; sub_00b426 is the menu wait loop.  Its second instruction, `move.w #2,$4c576.l` at $b42a,
; note: is the site: the picture is complete and about to be shown ($cd3e sets the video base to that buffer).  The blob replays the
; note: displaced instruction first.
COL     equ     8                       ; palette index of the text
CX      equ     72                      ; first character's x (pixels, a multiple of 4)
CY      equ     193                     ; first row

        org     $b42a
        jsr     $b4000.l

        org     $b4000
        move.w  #2,$4c576.l             ; displaced instruction
        movem.l d0-d7/a0-a3,-(a7)
        movea.l $12fa4.l,a0
        adda.l  #CY*160,a0
        move.w  #CX,d4
        lea     text(pc),a1
.next:  moveq   #0,d0
        move.b  (a1)+,d0
        beq.w   .done
        cmpi.b  #'a',d0
        blo.s   .nl
        cmpi.b  #'z',d0
        bhi.s   .nl
        subi.b  #'a',d0
        bra.s   .g
.nl:    cmpi.b  #'0',d0
        blo.s   .sym
        cmpi.b  #'9',d0
        bhi.s   .sym
        subi.b  #'0'-26,d0
        bra.s   .g
.sym:   cmpi.b  #'.',d0
        bne.s   .s1
        moveq   #36,d0
        bra.s   .g
.s1:    cmpi.b  #'_',d0
        bne.s   .s2
        moveq   #37,d0
        bra.s   .g
.s2:    cmpi.b  #'-',d0
        bne.s   .s3
        moveq   #38,d0
        bra.s   .g
.s3:    moveq   #39,d0
.g:     mulu    #5,d0
        lea     font(pc),a2
        adda.w  d0,a2
        move.w  d4,d1
        lsr.w   #4,d1
        lsl.w   #3,d1
        lea     (a0,d1.w),a3
        move.w  d4,d1
        lsr.w   #2,d1
        andi.w  #3,d1
        lsl.w   #2,d1
        moveq   #13,d2
        sub.w   d1,d2                   ; shift: the 3 glyph pixels are bits 15-4n .. 13-4n of the plane word
        moveq   #4,d6
.row:   moveq   #0,d3
        move.b  (a2)+,d3
        lsl.w   d2,d3
        move.w  d3,d7
        not.w   d7
        and.w   d7,(a3)
        and.w   d7,2(a3)
        and.w   d7,4(a3)
        and.w   d7,6(a3)
        ifne    COL&1
        or.w    d3,(a3)
        endc
        ifne    COL&2
        or.w    d3,2(a3)
        endc
        ifne    COL&4
        or.w    d3,4(a3)
        endc
        ifne    COL&8
        or.w    d3,6(a3)
        endc
        lea     160(a3),a3
        dbra    d6,.row
        addq.w  #4,d4
        bra.w   .next
.done:  movem.l (a7)+,d0-d7/a0-a3
        rts
text:   dc.b    'v@VERSION@ enhanced by dad_prg',0
        even
; 3 x 5 glyphs, one byte per row (bit 2 = left pixel): a-z, 0-9, '.', '_', '-', blank
font:   dc.b    7,5,7,5,5, 6,5,6,5,6, 7,4,4,4,7, 6,5,5,5,6, 7,4,7,4,7, 7,4,7,4,4
        dc.b    7,4,5,5,7, 5,5,7,5,5, 7,2,2,2,7, 1,1,1,5,7, 5,5,6,5,5, 4,4,4,4,7
        dc.b    5,7,7,5,5, 6,5,5,5,5, 7,5,5,5,7, 7,5,7,4,4, 7,5,5,7,1, 6,5,6,5,5
        dc.b    7,4,7,1,7, 7,2,2,2,2, 5,5,5,5,7, 5,5,5,5,2, 5,5,7,7,5, 5,5,2,5,5
        dc.b    5,5,2,2,2, 7,1,2,4,7
        dc.b    7,5,5,5,7, 2,6,2,2,7, 7,1,7,4,7, 7,1,7,1,7, 5,5,7,1,1
        dc.b    7,4,7,1,7, 7,4,7,5,7, 7,1,1,1,1, 7,5,7,5,7, 7,5,7,1,7
        dc.b    0,0,0,0,2, 0,0,0,0,7, 0,0,7,0,0, 0,0,0,0,0
