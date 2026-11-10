; name: pm_tooltip
; default: yes
; stage: 2
; site: $130a4
; orig: 4eb9000178ae
; data: $cdc00 1024
; note: hover tooltips (work/notes/tooltip.md).  The top bar (screen rows 0..5) is black right of x = 104; when the pointer is over an
;       icon (map-mode icons, rotate / zoom buttons, compass, and the command / posture / option symbols of the perspective grid)
;       a one-line description is drawn there, with the amount the captain's posture (1/2/3 swords) gives.
;       Site: `jsr $178ae` of the main loop pass, right after the window copy $12ce0 (the back buffer [$2df7c] now holds the clean
;       frame picture).  The hook draws the text into the back buffer only; the frame picture $78000 is never written, so the next
;       pass's copy removes the text by itself.  Passes that skip the render (tick S passes, the speed-slider skip) never reach it.
;       Pointer = $2df92/$2df94 (the words the game's own click code reads).  Hit test = the game's own, run only when the pointer
;       moved since the previous pass:  y < 6, x < 64, no window open ($7a36): map icon x>>4;  the 4 rectangles at $13250 (rotate, zoom);  x < 32, y > $a7:
;       compass;  x >= 64, y >= 129: the line tables $12e6a / $12ee4 (loop of $13506, same instructions) and the cell table $19bde.
;       Level = the selected captain's posture word [$51538 + [$57fd2] + $3c]: 4 = 1 sword, 3 = 2, 2 = 3.
;       Text: the game's own 4x6 font (4 glyph columns per 16-px word, 4-plane blocks of 48 B at $8976 + 48 * (ch >> 2), column
;       ch & 3; the window code $8838 does the same) composed into BUF; background colour 1 of the glyphs becomes colour 0.
;       The composed rows are rebuilt only when (target, level, keys on/off) changes; every rendered pass while a text is up copies 6 x 104 B.
;       Data S ($cdc00): +0 LX.w +2 LY.w +4 ID.w +6 KEY.w +8 VAL.w +$A KF.w (key labels on: qol_keys writes 1 here every pass) +$E MAG.l ('PTIP' written
;       by every hook call: qol_hover's liveness check) +$12 HK.w (the hover text that BUF currently holds, 0 = an icon text or none), BUF at +$20 (6 rows x 104 B =
;       cols 7..19), SB at +$290 (64 B).
;       Exports for qol_hover (jump table at $cd006 / $cd00c, never moves): compose_sb = SB (52 chars, space padded) -> BUF;  blit = BUF -> back buffer.
;       ALL WORDING IS IN THE ONE TABLE AT THE END OF THIS FILE (org $cf000: entry = count byte 1|3, name, key label, then 1 or 3 effect strings;
;       the label " (K)" is shown only while qol_keys is active; "Name (K): effect" must fit 52 characters, tools/pmtt_check.py).
S       equ     $cdc00
ET      equ     $cf000                  ; the wording table: 33 words (id -> entry offset in TXT), then the strings
TXT     equ     $cf042
sLX     equ     0
sLY     equ     2
sID     equ     4
sKEY    equ     6
sVAL    equ     8
sKF     equ     $a
sMAG    equ     $e
sHK     equ     $12
BUF     equ     S+$20
SB      equ     S+$290
FONT    equ     $8976
ID_MAP  equ     24                      ; 24..27 map-mode icons
ID_ROT  equ     28                      ; 28/29 rotate left/right, 30/31 zoom in/out (rect table $13250)
ID_COMP equ     32

        org     $130a4
        jsr     $cd000.l

        org     $cd000
        jmp     hook.l                  ; $cd000: the site's target (jsr $cd000)
        jmp     compose_sb.l            ; $cd006: export, qol_hover: SB -> BUF
        jmp     blit.l                  ; $cd00c: export, qol_hover: BUF -> back buffer
cell    macro                           ; \1 = cell 0..3, \2 = areg of the glyph block, \3 = dreg with the rotate count
        moveq   #0,d5
        move.b  (a2)+,d5
        move.w  d5,d6
        lsr.w   #2,d6
        mulu.w  #48,d6
        lea     FONT.l,\2
        adda.w  d6,\2
        and.w   #3,d5
        sub.w   #\1,d5
        add.w   d5,d5
        add.w   d5,d5
        move.w  d5,\3
        endm

plane   macro                           ; \1 = plane byte offset 0,2,4,6
        move.w  \1(a0),d5
        rol.w   d0,d5
        and.w   #$f000,d5
        move.w  \1(a1),d6
        rol.w   d1,d6
        and.w   #$0f00,d6
        or.w    d6,d5
        move.w  \1(a4),d6
        rol.w   d2,d6
        and.w   #$00f0,d6
        or.w    d6,d5
        move.w  \1(a5),d6
        rol.w   d3,d6
        and.w   #$000f,d6
        or.w    d6,d5
        move.w  d5,\1(a3)
        endm

hook:   movem.l d0-d7/a0-a6,-(a7)
        lea     S.l,a6
        move.l  #$50544950,sMAG(a6)     ; 'PTIP': qol_hover checks this before it calls the exports
        move.w  $2df92.l,d0
        move.w  $2df94.l,d1
        tst.w   sVAL(a6)
        beq.s   .mv
        cmp.w   sLX(a6),d0
        bne.s   .mv
        cmp.w   sLY(a6),d1
        beq.s   .lvl
.mv:    move.w  d0,sLX(a6)
        move.w  d1,sLY(a6)
        move.w  #1,sVAL(a6)
        bsr     hit
        move.w  d2,sID(a6)
.lvl:   move.w  sID(a6),d2
        beq.s   .none
        moveq   #1,d3                   ; neutral unless the posture word says otherwise
        move.w  $57fd2.l,d4
        lea     $51538.l,a0
        move.w  $3c(a0,d4.w),d4
        cmp.w   #2,d4
        blo.s   .lv
        cmp.w   #4,d4
        bhi.s   .lv
        moveq   #4,d3
        sub.w   d4,d3                   ; 4 -> 0 (1 sword), 3 -> 1, 2 -> 2
.lv:    move.w  d2,d5
        lsl.w   #2,d5
        add.w   d3,d5                   ; KEY = id*4 + level (never 0)
        tst.w   sKF(a6)
        beq.s   .nk
        add.w   #$100,d5                ; + key labels on (qol_keys): recompose when it appears
.nk:    cmp.w   sKEY(a6),d5
        beq.s   .blit
        move.w  d5,sKEY(a6)
        bsr     compose
.blit:  tst.w   sKEY(a6)
        beq.s   .out
        bsr     blit
        bra.s   .out
.none:  clr.w   sKEY(a6)
.out:   movem.l (a7)+,d0-d7/a0-a6
        jmp     $178ae.l

; d0 = x, d1 = y  ->  d2 = target id (0 none).  Clobbers d3-d7, a0, a1.
hit:    moveq   #0,d2
        cmp.w   #319,d0
        bhi.w   .no
        cmp.w   #199,d1
        bhi.w   .no
        cmp.w   #6,d1
        bhs.s   .body
        cmp.w   #64,d0
        bhs.w   .no
        tst.w   $7a36.l                 ; a window is open (the option menu covers these icons)
        bne.w   .no
        move.w  d0,d2
        lsr.w   #4,d2
        add.w   #ID_MAP,d2
        rts
.body:  lea     $13250.l,a0
        moveq   #3,d3
        moveq   #ID_ROT,d2
.r:     cmp.w   (a0),d0
        blt.s   .rn
        cmp.w   2(a0),d1
        blt.s   .rn
        cmp.w   4(a0),d0
        bge.s   .rn
        cmp.w   6(a0),d1
        bge.s   .rn
        rts
.rn:    addq.l  #8,a0
        addq.w  #1,d2
        dbra    d3,.r
        moveq   #0,d2
        cmp.w   #32,d0
        bge.s   .grid
        cmp.w   #$a7,d1
        ble.w   .no
        moveq   #ID_COMP,d2
        rts
.grid:  cmp.w   #64,d0
        blt.w   .no
        cmp.w   #129,d1
        blt.w   .no
        moveq   #0,d6
        lea     $12e6a.l,a1
.l1:    movem.w (a1)+,d2-d5
        tst.w   d2
        beq.s   .l1e
        move.w  d0,d7
        sub.w   d2,d7
        sub.w   d2,d4
        sub.w   d3,d5
        muls.w  d5,d7
        divs.w  d4,d7
        move.w  d1,d2
        sub.w   d3,d2
        addq.w  #1,d6
        cmp.w   d7,d2
        blt.s   .l1
.l1e:   lea     $12ee4.l,a1
.l2:    movem.w (a1)+,d2-d5
        tst.w   d2
        beq.s   .l2e
        move.w  d0,d7
        sub.w   d2,d7
        sub.w   d2,d4
        sub.w   d3,d5
        muls.w  d5,d7
        divs.w  d4,d7
        move.w  d1,d2
        sub.w   d3,d2
        add.w   #$10,d6
        cmp.w   d7,d2
        bgt.s   .l2
.l2e:   lea     $19bde.l,a1
        moveq   #0,d2
.s:     move.w  (a1)+,d3
        bmi.w   .no
        cmp.w   d3,d6
        beq.s   .found
        addq.w  #1,d2
        bra.s   .s
.found: rts
.no:    moveq   #0,d2
        rts

; d2 = id, d3 = level 0..2  ->  BUF (6 rows x 104 B).  Clobbers d0-d7, a0-a5.
compose:
        clr.w   S+sHK.l                 ; BUF no longer holds a hover text
        lea     ET.l,a0
        add.w   d2,d2
        move.w  (a0,d2.w),d4
        bne.s   .have
        clr.w   S+sKEY.l
        rts
.have:  lea     TXT.l,a1
        adda.w  d4,a1
        lea     SB.l,a2
        moveq   #15,d0
        move.l  #$20202020,d1
.f:     move.l  d1,(a2)+
        dbra    d0,.f
        lea     SB.l,a2
        moveq   #0,d4
        move.b  (a1)+,d4
.nm:    move.b  (a1)+,d0
        beq.s   .nmd
        move.b  d0,(a2)+
        bra.s   .nm
.nmd:   tst.w   S+sKF.l
        beq.s   .ksk                    ; key labels off (no qol_keys): skip the key string
        tst.b   (a1)
        beq.s   .ksk                    ; this entry has no key label
        move.b  #$20,(a2)+
        move.b  #$28,(a2)+              ; " ("
.kc:    move.b  (a1)+,d0
        beq.s   .kd
        move.b  d0,(a2)+
        bra.s   .kc
.kd:    move.b  #$29,(a2)+              ; ")"
        bra.s   .col
.ksk:   tst.b   (a1)+
        bne.s   .ksk
.col:   move.b  #$3a,(a2)+              ; ": "
        move.b  #$20,(a2)+
        cmp.w   #3,d4
        beq.s   .skp
        moveq   #0,d3
.skp:   tst.w   d3
        beq.s   .ef
.s1:    tst.b   (a1)+
        bne.s   .s1
        subq.w  #1,d3
        bra.s   .skp
.ef:    move.b  (a1)+,d0
        beq.s   compose_sb
        move.b  d0,(a2)+
        bra.s   .ef
compose_sb:                             ; export: SB holds the 52 characters (space padded) -> BUF.  Clobbers d0-d7, a0-a5.
        lea     SB.l,a2
        lea     BUF.l,a3
        moveq   #12,d7
.w:     move.l  (a2),d5
        cmp.l   #$20202020,d5
        bne.s   .nb
        addq.l  #4,a2
        moveq   #0,d5
        move.l  d5,(a3)
        move.l  d5,4(a3)
        move.l  d5,104(a3)
        move.l  d5,108(a3)
        move.l  d5,208(a3)
        move.l  d5,212(a3)
        move.l  d5,312(a3)
        move.l  d5,316(a3)
        move.l  d5,416(a3)
        move.l  d5,420(a3)
        move.l  d5,520(a3)
        move.l  d5,524(a3)
        bra.w   .nx
.nb:    cell    0,a0,d0
        cell    1,a1,d1
        cell    2,a4,d2
        cell    3,a5,d3
        move.w  #5,-(a7)
.row:   plane   0
        plane   2
        plane   4
        plane   6
        move.w  2(a3),d5                ; glyph background (colour 1) -> colour 0
        or.w    4(a3),d5
        or.w    6(a3),d5
        and.w   d5,(a3)
        lea     8(a0),a0
        lea     8(a1),a1
        lea     8(a4),a4
        lea     8(a5),a5
        lea     104(a3),a3
        subq.w  #1,(a7)
        bpl.w   .row
        addq.l  #2,a7
        lea     -624(a3),a3
.nx:    addq.l  #8,a3
        dbra    d7,.w
        rts

blit:   movea.l $2df7c.l,a1
        lea     56(a1),a1               ; column 7
        lea     BUF.l,a0
        moveq   #5,d0
.r:     movem.l (a0)+,d1-d7/a2-a5
        movem.l d1-d7/a2-a5,(a1)
        movem.l (a0)+,d1-d7/a2-a5
        movem.l d1-d7/a2-a5,44(a1)
        movem.l (a0)+,d1-d4
        movem.l d1-d4,88(a1)
        lea     160(a1),a1
        dbra    d0,.r
        rts

; ---- all wording below (org $cf000, the qol_ range; ET / TXT are equs above because pmpatch assembles every org on its own) -----------------
; Entry = count byte (3: three effect strings for 1 / 2 / 3 swords, 1: one string), name, key label, effect string(s).
; Shown as "name (key): effect", the " (key)" only while qol_keys is active and the label is not empty; "name (key): effect" must fit
; 52 characters (tools/pmtt_check.py checks every effect with and without the key).  Levels: 1 sword = passive, 2 = neutral, 3 = aggressive.
; Key labels are physical key positions ([ ] are the keys right of P on a UK/US keyboard).
        org     $cf000
ETA:    dc.w    0
        dc.w    e1-TXTA,e2-TXTA,e3-TXTA,e4-TXTA,e5-TXTA,e6-TXTA,e7-TXTA,e8-TXTA,e9-TXTA,e10-TXTA
        dc.w    0,e12-TXTA,e13-TXTA,e14-TXTA,e15-TXTA,e16-TXTA,0,0
        dc.w    e19-TXTA,e20-TXTA,e21-TXTA,e22-TXTA,e23-TXTA
        dc.w    e24-TXTA,e25-TXTA,e26-TXTA,e27-TXTA,e28-TXTA,e29-TXTA,e30-TXTA,e31-TXTA,e32-TXTA
TXTA:   dc.b    0
        ifne    TXTA-TXT
        fail    "TXT equ must equal the label TXTA (ET is 33 words)"
        endc
e1:     dc.b    1,"Send Captain",0,"G",0,"walk to a spot you pick",0
e2:     dc.b    3,"Transfer Men",0,"X",0,"give 25% of the army",0,"give 50% of the army",0,"give the whole army",0
e3:     dc.b    3,"Get Food",0,"F",0,"take 25% of a village's food",0,"take 50% of a village's food",0,"take ALL of a village's food",0
e4:     dc.b    3,"Get Men",0,"M",0,"recruit a few men",0,"recruit more men",0,"recruit nearly every man",0
e5:     dc.b    1,"Go Home",0,"H",0,"army walks back to base",0
e6:     dc.b    3,"Attack",0,"A",0,"conquer, spare as many as you can",0,"conquer, some die and some live",0,"kill everyone and take everything",0
e7:     dc.b    3,"Invent",0,"I",0,"ploughs, boats; iron: swords",0,"pikes; iron: swords",0,"bows, catapults; iron: swords, cannons",0   ; the traced rule of $5cde (work/notes/qol.md section 4); the village hover (qol_hover) names the exact item
e8:     dc.b    3,"Equip",0,"E",0,"pick up 25% of the items",0,"pick up 50% of the items",0,"pick up all the items",0
e9:     dc.b    3,"Drop Food",0,"D",0,"leave 25% of your food",0,"leave 50% of your food",0,"leave ALL of your food",0
e10:    dc.b    3,"Derank",0,"R",0,"send 25% of the army home",0,"send 50% of the army home",0,"disband the whole army",0
e12:    dc.b    3,"Drop Items",0,"N",0,"leave 25% of spare stock",0,"leave 50% of spare stock",0,"leave all spare stock",0
e13:    dc.b    3,"Supply Food",0,"S",0,"ferry 25% of food, repeat",0,"ferry 50% of food, repeat",0,"ferry all the food, repeat",0
e14:    dc.b    3,"Trade",0,"T",0,"ploughs, boats, pots first",0,"boats, pikes, ploughs first",0,"cannons, catapults first",0
e15:    dc.b    1,"Alliance",0,"L",0,"pay tribute for a pact",0
e16:    dc.b    1,"Spy",0,"Y",0,"scout a settlement",0
e19:    dc.b    1,"Aggressive (3 swords)",0,"3",0,"takes all, kills all",0
e20:    dc.b    1,"Neutral (2 swords)",0,"2",0,"takes half, spares some",0
e21:    dc.b    1,"Passive (1 sword)",0,"1",0,"takes a quarter, spares most",0
e22:    dc.b    1,"Query",0,"Q",0,"info on what you click",0
e23:    dc.b    1,"Option",0,"O",0,"speed, save/load, retire, pause",0
e24:    dc.b    1,"Map",0,"F1",0,"height contours",0
e25:    dc.b    1,"Map",0,"F2",0,"trees, houses, men",0
e26:    dc.b    1,"Map",0,"F3",0,"settlements and roads",0
e27:    dc.b    1,"Map",0,"F4",0,"settlement food (click: update)",0
e28:    dc.b    1,"Rotate left",0,"[",0,"click 90 deg, right-click fine",0
e29:    dc.b    1,"Rotate right",0,"]",0,"click 90 deg, right-click fine",0
e30:    dc.b    1,"Zoom in",0,"= or KP+",0,"right-click: closest",0
e31:    dc.b    1,"Zoom out",0,"- or KP-",0,"right-click: farthest",0
e32:    dc.b    1,"Compass (cursor keys)",0,0,"scroll the view",0
