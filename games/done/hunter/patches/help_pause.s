; name: help_pause
; default: yes
; requires: key_item jag_pad
; site: $260a
; orig: 082d0005009366f8
; note: Pause shows a controls guide (work/notes/help.md).  The game's pause is `bchg.b #5,$93(a5)` in the key decoder ($b0ae, key P or the pad's Pause);
; note: the 3D loop sees bit 5 at $254c, runs $2606 (`bsr $2eee`: clear the 3 timer words, wait one VBL, clear bit 7 = the 3D-loop gate) and then spins in
; note: `btst.b #5,$93(a5) / bne.b $260a` until the bit is clear, then `bset.b #7,$93(a5)` ($2612).  The site is that 8-byte spin loop: it now jumps here.
; note: What it does, in this order: (1) pointer off with the game's own `$a648` (restores the pixels under the pointer; the VBL's `$a65c` stops drawing it);
; note: (2) copies the 288x88 rectangle (rows 24..111 of the 3D window, 18 sixteen-pixel groups from x=16) of the SHOWN page ($148(a5)) into the same
; note: place of the draw page ($144(a5): the pass redraws the whole page every frame, so it is free scratch while the game is paused); (3) clears the
; note: rectangle in the shown page to colour 0 with a 1-pixel frame in colour 8 (plane 3 only) and draws the text in colour 8 (plane 3 only) with a 4x5
; note: font (advance 5, line pitch 7); colour 0 is black and colour 8 the brightest grey in the day, dusk and night palettes (visuals.md), and the rectangle
; note: stays above row 140 (the panel's palette split); (4) spins on bit 5 as before; (5) copies the saved rectangle back (byte-exact), shows the pointer
; note: again (`$a638`, only if it was on), and continues at $2612.  Nothing in the world is touched; the page that is drawn into next is the saved one.
; note: Script codes: '+' draws #, ',' draws *, ':' draws ? (the table starts at code 43; a space is skipped).  Pad cells (the third column) are drawn only when jag_pad found the pad ports (JAG_ST = 1).  Script records: x/2, y (bit 7 = pad only), text, 0;
; note: a record with x/2 = 0 ends a list.  Font: codes 43..90 (+ , - . / 0-9 : and upper case), 3 bytes per glyph = 5 rows of 4 pixels.
JAG     equ     $8d9e0                  ; jag_pad state: byte 0 = 1 when the pad ports exist
FONT    equ     $8ce80
SCRIPTB equ     $8cf10                  ; FONT + 48*3
Y0      equ     24                      ; first window row of the rectangle
H       equ     88                      ; rows
OFF     equ     Y0*160+8                ; byte offset of the rectangle (group 1)

        org     $260a
        jmp     $8cbbe.l                ; replaces `btst.b #5,$93(a5) / bne.b $260a`
        nop                             ; (never executed: the blob leaves by `jmp $2612`)

        org     $8cbbe
help:   btst    #5,$93(a5)
        beq.w   .out                    ; un-paused already: as the original loop
        movem.l d0-d7/a0-a4,-(sp)
        move.b  $1ce(a5),d7             ; bit 7 = the pointer is on
        bpl.s   .np
        jsr     $a648.l                 ; pointer off, pixels under it restored
.np:    bsr.w   hp_rect
        bsr.w   hp_copy                 ; shown -> spare page
        bsr.w   hp_box
        moveq   #0,d4
        cmpi.b  #1,JAG.l
        bne.s   .nopad
        moveq   #1,d4                   ; show the pad column
.nopad: lea     FONT.l,a4
        lea     script_a(pc),a3
        bsr.w   hp_draw
        lea     SCRIPTB.l,a3
        bsr.w   hp_draw
.wait:  btst    #5,$93(a5)
        bne.s   .wait
        bsr.w   hp_rect
        exg     a0,a1                   ; spare -> shown
        bsr.w   hp_copy
        tst.b   d7
        bpl.s   .nop2
        jsr     $a638.l                 ; pointer on again
.nop2:  movem.l (sp)+,d0-d7/a0-a4
.out:   jmp     $2612.l

hp_rect:                                ; a0 = rectangle in the shown page, a1 = in the draw page
        movea.l $148(a5),a0
        lea     OFF(a0),a0
        movea.l $144(a5),a1
        lea     OFF(a1),a1
        rts

hp_copy:                                ; a0 -> a1, H rows of 144 bytes
        move.w  #H-1,d0
.r:     moveq   #35,d1
.l:     move.l  (a0)+,(a1)+
        dbra    d1,.l
        lea     16(a0),a0
        lea     16(a1),a1
        dbra    d0,.r
        rts

hp_box:                                 ; clear the shown rectangle, frame in colour 8
        movea.l $148(a5),a0
        lea     OFF(a0),a0
        move.w  #H-1,d3
.r:     moveq   #0,d0
        cmpi.w  #H-1,d3
        beq.s   .b
        tst.w   d3
        bne.s   .s
.b:     moveq   #-1,d0                  ; top and bottom line
.s:     movea.l a0,a2
        moveq   #17,d1
.g:     clr.l   (a2)+
        clr.w   (a2)+
        move.w  d0,(a2)+                ; plane 3
        dbra    d1,.g
        tst.w   d0
        bne.s   .n
        move.w  #$8000,6(a0)            ; left edge
        move.w  #$0001,6+17*8(a0)       ; right edge
.n:     lea     160(a0),a0
        dbra    d3,.r
        rts

hp_end: rts
hp_draw:                                ; a3 = list, a4 = font, d4 = pad column on
        moveq   #0,d0
        move.b  (a3)+,d0
        beq.s   hp_end
        add.w   d0,d0                   ; x
        moveq   #0,d1
        move.b  (a3)+,d1                ; y, bit 7 = only with a pad
        bpl.s   .show
        tst.b   d4
        bne.s   .pad
.skip:  tst.b   (a3)+
        bne.s   .skip
        bra.s   hp_draw
.pad:   andi.w  #$7f,d1
.show:  mulu    #160,d1
        movea.l $148(a5),a0
        adda.l  d1,a0
        lea     Y0*160(a0),a0
        move.w  d0,d1
        lsr.w   #4,d1
        lsl.w   #3,d1
        adda.w  d1,a0                   ; the glyph's 16-pixel group
        andi.w  #15,d0                  ; pixel shift in it
.chr:   moveq   #0,d1
        move.b  (a3)+,d1
        beq.s   hp_draw
        cmpi.w  #32,d1
        beq.s   .adv                    ; blank
        subi.w  #43,d1
        move.w  d1,d2
        add.w   d1,d1
        add.w   d2,d1
        lea     (a4,d1.w),a1
        moveq   #0,d2
        move.b  (a1)+,d2
        lsl.l   #8,d2
        move.b  (a1)+,d2
        lsl.l   #8,d2
        move.b  (a1)+,d2
        lsl.l   #8,d2                   ; the 5 rows from bit 31 down, 4 bits each
        movea.l a0,a2
        moveq   #4,d3
.gr:    move.l  d2,d6
        andi.l  #$f0000000,d6
        lsr.l   d0,d6
        or.w    d6,14(a2)               ; plane 3, next group
        swap    d6
        or.w    d6,6(a2)                ; plane 3
        lea     160(a2),a2
        lsl.l   #4,d2
        dbra    d3,.gr
.adv:   addq.w  #5,d0
        cmpi.w  #16,d0
        blt.s   .chr
        subi.w  #16,d0
        addq.l  #8,a0
        bra.s   .chr

; x/2, y, text; y = 4 title, 12 pad header, 19 + 7n rows
script_a:
        dc.b    47,4,"PAUSED   PRESS P TO RESUME",0
        dc.b    12,19,"STICK   MOVE",0
        dc.b    12,26,"BUTTON  FIRE",0
        dc.b    12,33,"RETURN  NEXT WEAPON",0
        dc.b    12,40,"1-9     WEAPON",0
        dc.b    12,47,"H       MEDICAL KIT",0
        dc.b    12,54,"G       FUEL CAN",0
        dc.b    12,61,"J       PARACHUTE",0
        dc.b    12,68,"SPACE   GET OUT",0
        dc.b    12,75,"ESC     OPTIONS",0
        dc.b    0

        org     $8ce80
G       macro                           ; 5 rows of 4 pixels, leftmost = bit 3
        dc.b    (\1<<4)|\2,(\3<<4)|\4,\5<<4
        endm
        G       %0101,%1111,%0101,%1111,%0101   ; 43 '+' = #
        G       %0000,%1001,%0110,%1001,%0000   ; 44 ',' = *
        G       %0000,%0000,%1111,%0000,%0000   ; 45 -
        G       %0000,%0000,%0000,%0000,%0100   ; 46 .
        G       %0001,%0010,%0010,%0100,%1000   ; 47 /
        G       %0110,%1011,%1101,%1001,%0110   ; 48 0
        G       %0100,%1100,%0100,%0100,%1110   ; 49 1
        G       %0110,%1001,%0010,%0100,%1111   ; 50 2
        G       %1110,%0001,%0110,%0001,%1110   ; 51 3
        G       %1001,%1001,%1111,%0001,%0001   ; 52 4
        G       %1111,%1000,%1110,%0001,%1110   ; 53 5
        G       %0110,%1000,%1110,%1001,%0110   ; 54 6
        G       %1111,%0001,%0010,%0100,%0100   ; 55 7
        G       %0110,%1001,%0110,%1001,%0110   ; 56 8
        G       %0110,%1001,%0111,%0001,%0110   ; 57 9
        G       %0110,%1001,%0010,%0000,%0010   ; 58 ':' = ?
        ds.b    18                      ; 59..64
        G       %0110,%1001,%1111,%1001,%1001   ; A
        G       %1110,%1001,%1110,%1001,%1110   ; B
        G       %0111,%1000,%1000,%1000,%0111   ; C
        G       %1110,%1001,%1001,%1001,%1110   ; D
        G       %1111,%1000,%1110,%1000,%1111   ; E
        G       %1111,%1000,%1110,%1000,%1000   ; F
        G       %0111,%1000,%1011,%1001,%0111   ; G
        G       %1001,%1001,%1111,%1001,%1001   ; H
        G       %1110,%0100,%0100,%0100,%1110   ; I
        G       %0011,%0001,%0001,%1001,%0110   ; J
        G       %1001,%1010,%1100,%1010,%1001   ; K
        G       %1000,%1000,%1000,%1000,%1111   ; L
        G       %1001,%1111,%1111,%1001,%1001   ; M
        G       %1001,%1101,%1111,%1011,%1001   ; N
        G       %0110,%1001,%1001,%1001,%0110   ; O
        G       %1110,%1001,%1110,%1000,%1000   ; P
        G       %0110,%1001,%1001,%1011,%0111   ; Q
        G       %1110,%1001,%1110,%1010,%1001   ; R
        G       %0111,%1000,%0110,%0001,%1110   ; S
        G       %1111,%0100,%0100,%0100,%0100   ; T
        G       %1001,%1001,%1001,%1001,%0110   ; U
        G       %1001,%1001,%1001,%0110,%0110   ; V
        G       %1001,%1001,%1111,%1111,%1001   ; W
        G       %1001,%1001,%0110,%1001,%1001   ; X
        G       %1001,%1001,%0110,%0100,%0100   ; Y
        G       %1111,%0001,%0110,%1000,%1111   ; Z
script_b:
        dc.b    65,$80|12,"PAD",0
        dc.b    65,$80|19,"D-PAD",0
        dc.b    65,$80|26,"A B",0
        dc.b    65,$80|33,"C",0
        dc.b    65,$80|47,"+",0
        dc.b    65,$80|54,"0",0
        dc.b    65,$80|61,"8",0
        dc.b    65,$80|68,"OPTION",0
        dc.b    65,$80|75,",",0
        dc.b    128,$80|12,"PAD",0
        dc.b    85,19,"R     RADAR",0
        dc.b    128,$80|19,"1",0
        dc.b    85,26,":     MAP",0
        dc.b    128,$80|26,"2",0
        dc.b    85,33,"L     LOG BOOK",0
        dc.b    128,$80|33,"3",0
        dc.b    85,40,"A     DRONE",0
        dc.b    128,$80|40,"4",0
        dc.b    85,47,"F     FLARE",0
        dc.b    128,$80|47,"5",0
        dc.b    85,54,"C     CLOCK",0
        dc.b    128,$80|54,"6",0
        dc.b    85,61,"UP    REAR ZOOM",0
        dc.b    128,$80|61,"7",0
        dc.b    85,68,"DOWN  FRONT ZOOM",0
        dc.b    128,$80|68,"9",0
        dc.b    85,75,"P     RESUME",0
        dc.b    128,$80|75,"PAUSE",0
        dc.b    0
