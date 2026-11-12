; name: pop2_tooltip
; default: no
; site: $12740
; orig: 4eb90001334a
; note: Hover tooltips (work/notes/ui_impl.md, ui.md).  Site: `jsr $1334a.l` at $12740 in the play loop, the first instruction after the whole render stage
; note: (background copy $1e7b2, terrain/sprites, minimap/HUD) of a turn pass (T) and of a render-only pass (R); catch-up passes (S) jump over it (pop2_tick_render).  The blob
; note: ends in `jmp $1334a.l`, so $1334a returns to $12746 as before.  Nothing is drawn unless the pointer is on an icon: the hook then returns with every register restored
; note: and the frame is the stock frame.  The pointer is hit-tested with the game's own arithmetic (`$12dcc` command strip, `$13b4e` category row, `$13ba8` effect row; iso cells:
; note: u = dy + dx/2, v = dy - dx/2 from the origin, >> 4), only in the normal view ($39766 = 8, where the game's click code runs at all), on $393fa/$393fc.  An effect
; note: icon counts only when the game would act on it (`tst.b $70(a1,d4.w)` > 0, d4 = $39794*3 + slot, a1 = $46fc4 + $4739c*$13a).
; note: Text: the game's own renderer `$168b6` (a0 screen, a1 string, d0 column 0..39, d1 pixel row; opaque 8x8 font $37c84) into the BACK buffer $392e0: line 1 17 characters
; note: at column 15 (x 120-255, y 0-7), line 2 14 characters at column 17 (x 136-247, y 8-15), both padded with spaces to the full width.  The back buffer is rebuilt from the clean
; note: background every rendered pass, so nothing is ever erased; the shown buffer and the pointer code are not touched.
; note: Line 2 is the icon's existing key: F1-F6 (category), 1-5 after the category (effect slot), keypad ( ) / * and / (command strip).  Blob PB+$5800 (free: pop2_spr ends below
; note: PB+$5600, pop2_ptr_a starts at PB+$6000).
BLOB    equ     PB+$5800

        org     $12740
        jsr     BLOB.l

        org     PB+$5800
tt:     movem.l d0-d7/a0-a6,-(a7)
        cmpi.w  #8,$39766.l
        bne.w   .out
        move.w  $393fa.l,d6
        move.w  $393fc.l,d7
        suba.l  a3,a3                   ; a3 = key string (0 = none), d4 / d5 = digit characters patched into it (0 = none)
        moveq   #0,d4
        moveq   #0,d5
        move.w  d6,d0                   ; command strip: origin ($13d,$8c), cell index (u>>4) + 4 * (v>>4), entries 4, 8 .. 24 (game: $12dcc-$12e04)
        move.w  d7,d1
        subi.w  #$13d,d0
        subi.w  #$8c,d1
        asr.w   #1,d0
        move.w  d1,d3
        sub.w   d0,d3
        move.w  d0,d2
        add.w   d1,d2
        move.w  d2,d0
        bmi.s   .cat
        move.w  d3,d1
        bmi.s   .cat
        asr.w   #4,d0
        asr.w   #4,d1
        asl.w   #2,d1
        add.w   d1,d0
        bmi.s   .cat
        cmpi.w  #$18,d0
        bgt.s   .cat
        move.w  d0,d1
        andi.w  #3,d1
        bne.s   .cat
        lsr.w   #2,d0                   ; 1..6 (0 = no entry)
        beq.s   .cat
        subq.w  #1,d0
        lsl.w   #2,d0
        lea     stab(pc),a0
        lea     txt(pc),a2
        lea     txt(pc),a3
        adda.w  0(a0,d0.w),a2
        move.w  2(a0,d0.w),d0
        beq.s   .nokey
        adda.w  d0,a3
        bra.w   .show
.nokey: suba.l  a3,a3
        bra.w   .show
.cat:   move.w  d6,d0                   ; category row: origin ($3b,$89), v>>4 = 0, u>>4 = 0..5 (game: $13b4e)
        move.w  d7,d1
        subi.w  #$3b,d0
        subi.w  #$89,d1
        asr.w   #1,d0
        move.w  d1,d3
        sub.w   d0,d3
        move.w  d0,d2
        add.w   d1,d2
        asr.w   #4,d3
        bne.s   .eff
        asr.w   #4,d2
        bmi.s   .eff
        cmpi.w  #5,d2
        bgt.s   .eff
        move.w  d2,d4
        addi.w  #'1',d4                 ; F<n+1>
        add.w   d2,d2
        lea     ctab(pc),a0
        lea     txt(pc),a2
        adda.w  0(a0,d2.w),a2
        lea     txt(pc),a3
        adda.w  #kcat-txt,a3
        bra.w   .show
.eff:   move.w  d6,d0                   ; effect row: origin ($2a,$97), v>>4 = 0, u>>4 = 0..5 (game: $13ba8)
        move.w  d7,d1
        subi.w  #$2a,d0
        subi.w  #$97,d1
        asr.w   #1,d0
        move.w  d1,d3
        sub.w   d0,d3
        move.w  d0,d2
        add.w   d1,d2
        asr.w   #4,d3
        bne.w   .out
        asr.w   #4,d2
        bmi.w   .out
        cmpi.w  #4,d2                   ; slot 5 has no icon and no key
        bgt.w   .out
        move.w  $39794.l,d5             ; 2 * category (the game's $13b98)
        cmpi.w  #10,d5
        bhi.w   .out
        move.w  $4739c.l,d3
        mulu.w  #$13a,d3
        lea     $46fc4.l,a1
        adda.w  d3,a1
        move.w  d5,d0
        mulu.w  #3,d0
        add.w   d2,d0                   ; the game's d4 = $39794 * 3 + slot
        tst.b   $70(a1,d0.w)
        ble.w   .out                    ; the game ignores a click here
        lsr.w   #1,d5                   ; category 0..5
        move.w  d5,d4
        addi.w  #'1',d4                 ; F<n+1>
        move.w  d5,d0
        mulu.w  #5,d0
        add.w   d2,d0
        addi.w  #'1',d2
        move.w  d2,d5                   ; digit key of the slot
        add.w   d0,d0
        lea     etab(pc),a0
        lea     txt(pc),a2
        adda.w  0(a0,d0.w),a2
        lea     txt(pc),a3
        adda.w  #keff-txt,a3
.show:  tst.b   (a2)
        beq.w   .out                    ; a slot with no name (fire slot 5) shows nothing
        lea     L1(pc),a0               ; line 1: 17 spaces + name
        moveq   #16,d0
.f1:    move.b  #' ',(a0)+
        dbra    d0,.f1
        clr.b   (a0)
        lea     L1(pc),a0
.c1:    move.b  (a2)+,d0
        beq.s   .c1e
        move.b  d0,(a0)+
        bra.s   .c1
.c1e:   movea.l $392e0.l,a0
        lea     L1(pc),a1
        moveq   #15,d0
        moveq   #0,d1
        jsr     $168b6.l
        movea.l $392e0.l,a0
        adda.w  #56,a0                  ; line 1: group 7 (x 112-127), only its right half is ours
        move.l  #$00000007,d2
        movea.w #$ff,a2
        bsr.w   mask
        movea.l $392e0.l,a0
        adda.w  #64,a0                  ; groups 8-15 (x 128-255)
        move.l  #$00070007,d2
        movea.w #-1,a2
        bsr.w   mask
        move.l  a3,d0
        beq.w   .out
        lea     L2(pc),a0               ; line 2: 14 spaces + the key text
        moveq   #13,d0
.f2:    move.b  #' ',(a0)+
        dbra    d0,.f2
        clr.b   (a0)
        lea     L2(pc),a0
.c2:    move.b  (a3)+,d0
        beq.s   .c2e
        move.b  d0,(a0)+
        bra.s   .c2
.c2e:   lea     L2(pc),a1
        tst.w   d4
        beq.s   .d2
        move.b  d4,6(a1)                ; "KEY: F?"
.d2:    tst.w   d5
        beq.s   .d3
        move.b  d5,13(a1)               ; "KEY: F? THEN ?"
.d3:    movea.l $392e0.l,a0
        lea     L2(pc),a1
        moveq   #17,d0
        moveq   #8,d1
        jsr     $168b6.l
        movea.l $392e0.l,a0
        adda.w  #1344,a0                ; line 2: group 8 (x 128-143), only x 136-143 is ours
        move.l  #$00000007,d2
        movea.w #$ff,a2
        bsr.w   mask
        movea.l $392e0.l,a0
        adda.w  #1352,a0                ; groups 9-15 (x 144-255)
        move.l  #$00060007,d2
        movea.w #-1,a2
        bsr.w   mask
.out:   movem.l (a7)+,d0-d7/a0-a6
        jmp     $1334a.l

mask:   movea.l a0,a1                   ; the font's paper is colour index 13 (space glyph = planes ff 00 ff ff): turn it into the sky's colour 0.
        move.l  d2,d1                   ; a0 = first 16-px group, d2 = (groups-1) << 16 | (rows-1)
        swap    d1
.g:     move.w  (a1),d0
        move.w  2(a1),d3
        move.w  4(a1),d6
        move.w  6(a1),d7
        and.w   d6,d0
        and.w   d7,d0
        not.w   d3
        and.w   d3,d0                   ; pixels with p0 & ~p1 & p2 & p3
        move.w  a2,d3
        and.w   d3,d0                   ; a2 = pixel mask of the group ($ffff, or $00ff for the group that holds x 112-119)
        not.w   d0
        and.w   d0,(a1)
        and.w   d0,2(a1)
        and.w   d0,4(a1)
        and.w   d0,6(a1)
        addq.l  #8,a1
        dbra    d1,.g
        lea     160(a0),a0
        dbra    d2,mask
        rts


stab:
        dc.w    s0-txt,0
        dc.w    s1-txt,sk1-txt
        dc.w    s2-txt,sk2-txt
        dc.w    s3-txt,sk3-txt
        dc.w    s4-txt,sk4-txt
        dc.w    s5-txt,sk5-txt
ctab:   dc.w    c0-txt,c1-txt,c2-txt,c3-txt,c4-txt,c5-txt
etab:
        dc.w    e00-txt,e01-txt,e02-txt,e03-txt,e04-txt
        dc.w    e10-txt,e11-txt,e12-txt,e13-txt,e14-txt
        dc.w    e20-txt,e21-txt,e22-txt,e23-txt,e24-txt
        dc.w    e30-txt,e31-txt,e32-txt,e33-txt,e34-txt
        dc.w    e40-txt,e41-txt,e42-txt,e43-txt,e44-txt
        dc.w    e50-txt,e51-txt,e52-txt,e53-txt,e54-txt
txt:
s0:     dc.b    "GAME OPTIONS",0
s1:     dc.b    "QUERY",0
sk1:    dc.b    "KEY: /",0
s2:     dc.b    "GATHER",0
sk2:    dc.b    "KEY: KEYPAD )",0
s3:     dc.b    "FIGHT",0
sk3:    dc.b    "KEY: KEYPAD /",0
s4:     dc.b    "SETTLE",0
sk4:    dc.b    "KEY: KEYPAD (",0
s5:     dc.b    "GO TO MAGNET",0
sk5:    dc.b    "KEY: KEYPAD *",0
c0:     dc.b    "PEOPLE EFFECTS",0
c1:     dc.b    "PLANT EFFECTS",0
c2:     dc.b    "EARTH EFFECTS",0
c3:     dc.b    "AIR EFFECTS",0
c4:     dc.b    "FIRE EFFECTS",0
c5:     dc.b    "WATER EFFECTS",0
e00:    dc.b    "RAISE/LOWER LAND",0
e01:    dc.b    "PAPAL MAGNET",0
e02:    dc.b    "PERSEUS",0
e03:    dc.b    "PLAGUE",0
e04:    dc.b    "ARMAGEDDON",0
e10:    dc.b    "TREES",0
e11:    dc.b    "FLOWERS",0
e12:    dc.b    "SWAMP",0
e13:    dc.b    "FUNGUS",0
e14:    dc.b    "ADONIS",0
e20:    dc.b    "ROADS",0
e21:    dc.b    "BUILD CITY WALL",0
e22:    dc.b    "EARTHQUAKE",0
e23:    dc.b    "BATHOLITH",0
e24:    dc.b    "HERACLES",0
e30:    dc.b    "LIGHTNING",0
e31:    dc.b    "WHIRLWIND",0
e32:    dc.b    "STORM",0
e33:    dc.b    "ODYSSEUS",0
e34:    dc.b    "WIND",0
e40:    dc.b    "FIRE COLUMN",0
e41:    dc.b    "FIRE RAIN",0
e42:    dc.b    "ACHILLES",0
e43:    dc.b    "VOLCANO",0
e44:    dc.b    "",0
e50:    dc.b    "BASALT",0
e51:    dc.b    "WHIRLPOOL",0
e52:    dc.b    "BAPTISMAL FONTS",0
e53:    dc.b    "HELEN OF TROY",0
e54:    dc.b    "TIDAL WAVE",0
kcat:   dc.b    "KEY: F0",0
keff:   dc.b    "KEY: F0 THEN 0",0
        even
L1:     ds.b    18
L2:     ds.b    16
