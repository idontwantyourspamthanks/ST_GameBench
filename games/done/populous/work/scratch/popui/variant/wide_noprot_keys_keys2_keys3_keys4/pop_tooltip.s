; name: pop_tooltip
; default: no
; prog: populous
; site: $b93a
; orig: 4eb90000d4c0
; data: $c8200 1184
; note: Hover tooltips for the icons (PopUI).  The pointer over an icon prints its name, its key and (spells) its manna cost at the top of the
; note: book page in the game's own 8x8 font ($2364a, 40 bytes per character: mask byte + 4 plane bytes per row, drawn with `and mask / or data`
; note: exactly as the text renderer $180f4 does): line 1 in the rectangle (84,0)-(213,7), 16 characters, line 2 in (100,8)-(171,15), 9 characters
; note: (the user's choice, work/shots/tt_candidate_B_two_lines.png).  Both lines start at x = 4 (mod 8), which the renderer $180f4 cannot do
; note: (it rounds x down to a multiple of 8), so the glyphs are merged by this blob: the left nibble of a glyph byte goes to the low nibble of
; note: the screen byte k, the right nibble to the high nibble of byte k+1.
; note: Site $b93a is `jsr $d4c0.l`, the last call of the pass before the flip `jsr $16f16` at $b940 ($d4c0 draws the shield / query panel at the
; note: top right).  The hook runs it, then draws into the BACK buffer $3c510.  Every pass starts with the 32,000-byte copy of the clean background
; note: ($14a28), so nothing is erased and nothing can be left behind when the pointer leaves the icon; with no tooltip the pass is the original
; note: plus one hit test per pointer move (the pointer words are compared with the last pair; the cached icon number is reused) and a few compares.
; note: Hit test: the game's own ($c420 $c424-$c6c2): u = y + x/2 - 32, v = y - x/2 + 32; the minimap is 0 <= u, v < 64; u > $112 is the right-hand
; note: panel (i = (u - $110) / 16, j = (v - $20) / 16), otherwise the left panel (v >= $92, i = (u - $60) / 16, j = (v - $90) / 16), `divs` truncating
; note: toward 0 like the game's.  (i, j) -> icon number by the tables LT (9 x 5) and RT (3 x 5), i.e. the click's own cells.
; note: Composing a text (font -> cache of mask / plane words per 16-pixel group, 1,120 bytes) happens only when the icon changes; every pass with a
; note: tooltip then merges the cache into the back buffer (and mask, or data: about 16 k cycles).
; note: Key labels: a string is `name 1 key 0 line2 0`: with pop_keys installed (`$bb7c` starts with `jsr`) the label `(key)` follows the name; a
; note: line 2 that starts with byte 2 is shown only then.  While the Armageddon arm of pop_keys is running (KD+4) the hint replaces any hover.
; note: Data block T ($c8200): +0 CX.w +2 CY.w (pointer of the last hit test) +4 CID.w +6 SHOWN.w (icon the cache holds) +8 KEYS.w +10 NG1.w +12 NG2.w
; note: +14 TXT1[24] +38 TXT2[16] +56 C1[720] +776 C2[400].  Blob $c7400-.
T       equ     $c8200
KD      equ     $c8000
AWIN    equ     150
ID_ARM  equ     25
tCX     equ     0
tCY     equ     2
tCID    equ     4
tSHOWN  equ     6
tKEYS   equ     8
tNG1    equ     10
tNG2    equ     12
tTXT1   equ     14
tTXT2   equ     38
tC1     equ     56
tC2     equ     776

        org     $b93a
        jsr     $c7400.l

        org     $c7400
tt:     jsr     $0d4c0.l                ; the displaced call
        movem.l d0-d7/a0-a5,-(sp)
        lea     T.l,a3
        moveq   #0,d6                   ; d6 = pop_keys installed
        cmpi.w  #$4eb9,$0bb7c.l
        bne.s   .nk
        moveq   #1,d6
.nk:    moveq   #0,d7                   ; d7 = icon number wanted
        tst.w   d6
        beq.s   .hover
        move.l  KD+4.l,d0               ; the Armageddon arm (stamp + 1)
        beq.s   .hover
        move.l  $16d2a.l,d1
        sub.l   d0,d1
        addq.l  #1,d1
        cmp.l   #AWIN,d1
        bhi.s   .hover
        moveq   #ID_ARM,d7
        bra.s   .have
.hover: move.w  $24786.l,d0
        move.w  $24788.l,d1
        cmp.w   tCX(a3),d0
        bne.s   .calc
        cmp.w   tCY(a3),d1
        bne.s   .calc
        move.w  tCID(a3),d7
        bra.s   .have
.calc:  move.w  d0,tCX(a3)
        move.w  d1,tCY(a3)
        bsr.w   hit
        move.w  d7,tCID(a3)
.have:  tst.w   d7
        beq.w   .out
        cmp.w   tSHOWN(a3),d7
        bne.s   .comp
        cmp.w   tKEYS(a3),d6
        beq.s   .draw
.comp:  bsr.w   compose
.draw:  movea.l $3c510.l,a0             ; the back buffer
        lea     40(a0),a0               ; line 1: rows 0-7, 16-pixel group 5 (x = 80)
        lea     tC1(a3),a1
        move.w  tNG1(a3),d3
        move.w  #9,d4
        bsr.w   blit
        move.w  tNG2(a3),d3
        beq.s   .out
        movea.l $3c510.l,a0
        lea     1328(a0),a0             ; line 2: rows 8-15, group 6 (x = 96): 8 * 160 + 48
        lea     tC2(a3),a1
        moveq   #5,d4
        bsr.w   blit
.out:   movem.l (sp)+,d0-d7/a0-a5
        rts

; ---- hit: d0 = x, d1 = y (the pointer) -> d7 = icon number, 0 = none
hit:    moveq   #0,d7
        move.w  d0,d2
        asr.w   #1,d2                   ; x / 2
        move.w  d1,d3
        add.w   d2,d3
        sub.w   #$20,d3                 ; u
        move.w  d1,d4
        sub.w   d2,d4
        add.w   #$20,d4                 ; v
        tst.w   d3
        blt.s   .nomap
        cmp.w   #$40,d3
        bge.s   .nomap
        tst.w   d4
        blt.s   .nomap
        cmp.w   #$40,d4
        blt.s   .ret                    ; the minimap
.nomap: cmp.w   #$112,d3
        ble.s   .left
        sub.w   #$110,d3                ; the right-hand panel
        ext.l   d3
        divs.w  #16,d3                  ; i
        sub.w   #$20,d4
        ext.l   d4
        divs.w  #16,d4                  ; j
        cmp.w   #2,d3
        bhi.s   .ret
        cmp.w   #4,d4
        bhi.s   .ret                    ; (a negative j is a large unsigned one)
        mulu.w  #5,d3
        add.w   d4,d3
        lea     RT(pc),a0
        move.b  (a0,d3.w),d7
        rts
.left:  cmp.w   #$92,d4
        blt.s   .ret
        sub.w   #$90,d4
        ext.l   d4
        divs.w  #16,d4                  ; j
        sub.w   #$60,d3
        ext.l   d3
        divs.w  #16,d3                  ; i
        cmp.w   #8,d3
        bhi.s   .ret
        cmp.w   #4,d4
        bhi.s   .ret
        mulu.w  #5,d3
        add.w   d4,d3
        lea     LT(pc),a0
        move.b  (a0,d3.w),d7
.ret:   rts

; ---- compose: d7 = icon number, d6 = keys flag -> the two caches, tNG1 / tNG2
compose:move.w  d7,tSHOWN(a3)
        move.w  d6,tKEYS(a3)
        lea     TTB(pc),a0
        move.w  d7,d0
        subq.w  #1,d0
        add.w   d0,d0
        adda.w  (a0,d0.w),a0            ; the pair of strings
        lea     tTXT1(a3),a1
        bsr.s   expand
        lea     tTXT2(a3),a1
        bsr.s   expand
        lea     tC1(a3),a1              ; line 1
        moveq   #9,d3
        bsr.w   clear
        lea     tTXT1(a3),a0
        lea     tC1(a3),a1
        moveq   #9,d3
        moveq   #16,d5
        bsr.w   render                  ; -> d4 = characters drawn
        addq.w  #2,d4
        lsr.w   #1,d4                   ; groups = (n + 2) / 2
        move.w  d4,tNG1(a3)
        clr.w   tNG2(a3)
        tst.b   tTXT2(a3)
        beq.s   .done
        lea     tC2(a3),a1              ; line 2
        moveq   #5,d3
        bsr.w   clear
        lea     tTXT2(a3),a0
        lea     tC2(a3),a1
        moveq   #5,d3
        moveq   #9,d5
        bsr.w   render
        addq.w  #2,d4
        lsr.w   #1,d4
        move.w  d4,tNG2(a3)
.done:  rts

; expand: a0 = source string (NUL ended; byte 1 = key label follows, byte 2 = keys-only text follows), a1 = destination; a0 ends after the NUL
expand: move.b  (a0)+,d0
        beq.s   .end
        cmp.b   #1,d0
        beq.s   .key
        cmp.b   #2,d0
        beq.s   .only
        move.b  d0,(a1)+
        bra.s   expand
.key:   tst.w   d6
        beq.s   .skip
        move.b  #' ',(a1)+
        move.b  #'(',(a1)+
.kc:    move.b  (a0)+,d0
        beq.s   .kend
        move.b  d0,(a1)+
        bra.s   .kc
.kend:  move.b  #')',(a1)+
        clr.b   (a1)
        rts
.only:  tst.w   d6
        beq.s   .skip
.oc:    move.b  (a0)+,d0
        beq.s   .end
        move.b  d0,(a1)+
        bra.s   .oc
.skip:  tst.b   (a0)+
        bne.s   .skip
.end:   clr.b   (a1)
        rts

; clear: a1 = cache, d3 = groups per row: mask words $ffff, plane words 0 for 8 rows
clear:  move.w  d3,d0
        lsl.w   #3,d0
        subq.w  #1,d0
.c:     move.w  #$ffff,(a1)+
        clr.l   (a1)+
        clr.l   (a1)+
        dbra    d0,.c
        rts

; render: a0 = text, a1 = cache, d3 = groups per row, d5 = maximum characters -> d4 = characters drawn.
; Character k of the line sits at pixel 8k + 4: screen byte k gets the glyph's left nibble in its low nibble, byte k+1 the right nibble in its
; high nibble.  Cache byte address = row * (groups * 10) + (k >> 1) * 10 + field * 2 + (k & 1), field 0 = mask, 1-4 = planes 0-3.
render: mulu.w  #10,d3                  ; row stride in the cache
        moveq   #0,d4
.chr:   moveq   #0,d0
        move.b  (a0)+,d0
        beq.s   .done
        cmp.w   d5,d4
        bhs.s   .done
        sub.w   #$20,d0
        bmi.s   .next
        mulu.w  #40,d0
        lea     $2364a.l,a2             ; the game's font
        adda.l  d0,a2
        move.w  d4,d0
        lsr.w   #1,d0
        mulu.w  #10,d0
        lea     (a1,d0.w),a4
        moveq   #1,d2                   ; distance to byte k + 1
        btst    #0,d4
        beq.s   .ev
        addq.l  #1,a4
        moveq   #9,d2
.ev:    moveq   #7,d1
.row:   move.b  (a2)+,d0                ; mask: 1 = keep the screen pixel
        move.b  d0,d6
        lsr.b   #4,d6
        ori.b   #$f0,d6
        and.b   d6,(a4)
        lsl.b   #4,d0
        ori.b   #$0f,d0
        and.b   d0,(a4,d2.w)
        lea     2(a4),a5
        moveq   #3,d7
.pl:    move.b  (a2)+,d0                ; plane data
        move.b  d0,d6
        lsr.b   #4,d6
        or.b    d6,(a5)
        lsl.b   #4,d0
        or.b    d0,(a5,d2.w)
        addq.l  #2,a5
        dbra    d7,.pl
        adda.l  d3,a4
        dbra    d1,.row
.next:  addq.w  #1,d4
        bra.w   .chr
.done:  rts

; blit: a0 = screen address of group 0 of the line, a1 = cache, d3 = groups to draw, d4 = groups in the cache row
blit:   subq.w  #1,d3
        sub.w   d3,d4
        subq.w  #1,d4                   ; d4 = groups not drawn
        mulu.w  #10,d4                  ; their bytes: skipped at the end of every row
        moveq   #7,d1
.row:   movea.l a0,a2
        move.w  d3,d2
.grp:   move.w  (a1)+,d0                ; mask
        move.w  (a2),d5
        and.w   d0,d5
        or.w    (a1)+,d5
        move.w  d5,(a2)+
        move.w  (a2),d5
        and.w   d0,d5
        or.w    (a1)+,d5
        move.w  d5,(a2)+
        move.w  (a2),d5
        and.w   d0,d5
        or.w    (a1)+,d5
        move.w  d5,(a2)+
        move.w  (a2),d5
        and.w   d0,d5
        or.w    (a1)+,d5
        move.w  d5,(a2)+
        dbra    d2,.grp
        adda.w  d4,a1
        lea     160(a0),a0
        dbra    d1,.row
        rts

; icon numbers per (i, j): left panel i = 0-8 (rows), j = 0-4
LT:     dc.b    1,0,0,0,0               ; i0: flood
        dc.b    2,3,0,0,0               ; i1: Armageddon, volcano
        dc.b    4,5,6,0,0               ; i2: earthquake, knight, swamp
        dc.b    17,17,17,7,0            ; i3: scroll arrows, go to the magnet
        dc.b    17,18,17,8,10           ; i4: arrows round the shield (the view to the selection), settle, fight
        dc.b    17,17,17,9,0            ; i5: arrows, gather
        dc.b    11,12,13,0,0            ; i6: query, raise / lower, papal magnet
        dc.b    14,15,0,0,0             ; i7: view leader / magnet, view battle
        dc.b    16,0,0,0,0              ; i8: view knight / building
RT:     dc.b    19,0,0,22,23            ; i0: options (scales), music, effects
        dc.b    0,20,0,24,0             ; i1: game setup (globe), pause
        dc.b    0,0,21,0,0              ; i2: link (telephone)
        even

; wording: offsets to the string pairs (line 1, line 2).  Line 1 at most 16 characters and line 2 at most 9 with the key label (tools/popuitest.py
; `words` checks it).
TTB:    dc.w    s1-TTB,s2-TTB,s3-TTB,s4-TTB,s5-TTB,s6-TTB,s7-TTB,s8-TTB,s9-TTB,s10-TTB,s11-TTB,s12-TTB,s13-TTB
        dc.w    s14-TTB,s15-TTB,s16-TTB,s17-TTB,s18-TTB,s19-TTB,s20-TTB,s21-TTB,s22-TTB,s23-TTB,s24-TTB,s25-TTB
s1:     dc.b    "Flood",1,"F",0,"COST 40K",0
s2:     dc.b    "Armageddon",1,"AA",0,0
s3:     dc.b    "Volcano",1,"V",0,"COST 10K",0
s4:     dc.b    "Earthquake",1,"E",0,"COST 2500",0
s5:     dc.b    "Knight",1,"K",0,"COST 7500",0
s6:     dc.b    "Swamp",1,"W",0,"COST 5000",0
s7:     dc.b    "Go to magnet",1,"M",0,"BEHAVIOUR",0
s8:     dc.b    "Settle",1,"S",0,"BEHAVIOUR",0
s9:     dc.b    "Gather",1,"G",0,"BEHAVIOUR",0
s10:    dc.b    "Fight",1,"T",0,"BEHAVIOUR",0
s11:    dc.b    "Query",1,"Q",0,"INFO MODE",0
s12:    dc.b    "Shape land",1,"R",0,"UP / DOWN",0
s13:    dc.b    "Place magnet",1,"P",0,"COST 200",0
s14:    dc.b    "To leader",1,"L",0,2,"Z: MAGNET",0
s15:    dc.b    "To battle",1,"B",0,0
s16:    dc.b    "To knight",1,"N",0,2,"H: HOUSE",0
s17:    dc.b    "Scroll (KEYPAD)",0,0
s18:    dc.b    "To selection",0,0
s19:    dc.b    "Options",0,0
s20:    dc.b    "Game setup",0,0
s21:    dc.b    "Link up",0,0
s22:    dc.b    "Music",1,"U",0,"ON / OFF",0
s23:    dc.b    "Effects",1,"X",0,"ON / OFF",0
s24:    dc.b    "Pause",1,"Space",0,0
s25:    dc.b    "ARMAGEDDON?",0,"A AGAIN",0
