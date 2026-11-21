; msedit.s - Moonshine Racers TRACK EDITOR overlay (FILES\MSEDIT.OVL).  Milestone 1: the VIEWER (read-only).  Design: work/notes/editor_design.md.
; Not a patch: tools/msrpatch.py assembles this file at EDBASE ($130000, no `org` line here), fills in the header's length and CRC-32 and writes it to the HD build's FILES folder.
; cp_title.s (F10 menu, item TRACK EDITOR) reads it there on first use, checks magic / EDVER / length / CRC and calls EDBASE+16.  Machines: ST family with 2 MB or more (the `; gate: ram2mb` of cp_title).
; The tool predefines EDBASE, EDWORK ($140000), EDVER, CPV, CPSTORE.  Everything the editor owns lies above $100000; it calls the game's vertical sync ($d206), file service ($d6fa)
; and reads its font ($190be), key tables ($5ffe held, $607e latched, $60ff last make) and joystick byte ($6105).
;
; Work RAM (EDWORK = $140000):
V       equ     EDWORK          ; variables (2 KB, cleared at entry)
BLK     equ     EDWORK+$400     ; raw track block read from the game's disk image (a stock track: at most 12 sectors)
SEGT    equ     EDWORK+$3000    ; segment list: 2048 x 12 B  start.w len.w curve.w hill.w wl.b wr.b pad.w
OBJT    equ     EDWORK+$9000    ; object list: 1000 x 8 B  at.w type.w lateral.w flags.w (bit 0 = the BAR)
HARR    equ     EDWORK+$10000   ; height byte per unit (32768)
WLARR   equ     EDWORK+$18000   ; left half-width per unit
WRARR   equ     EDWORK+$20000   ; right half-width per unit
PTS     equ     EDWORK+$28000   ; top-down path: x.w y.w (world units / 4, y down) every 8 units (4097 points)
SINT    equ     EDWORK+$2D000   ; sine table, 4096 steps per turn + a quarter (5120 words)
SCR     equ     EDWORK+$30000   ; the editor's own screen (32000 B)
MAXSEG  equ     2048
MAXOBJ  equ     999
SEGSZ   equ     12

vScr    equ     0               ; b,b the game's video base (hi, mid)
vPal    equ     2               ; 16 w the game's palette
vNSeg   equ     34              ; w
vNObj   equ     36              ; w
vTotal  equ     38              ; l units covered by the four streams (<= 32768)
vEnd    equ     42              ; l extent shown: max(race length, BAR) + 1024, <= vTotal
vRl     equ     46              ; w race length of the base level
vBase   equ     48              ; w base level 0..14
vBarT   equ     50              ; w the BAR's type (1-based), 0 = none in the type table
vBarAt  equ     52              ; l position of the BAR object, -1 = none
vNTypes equ     56              ; w
vNBar   equ     58              ; w number of BAR objects
vSeg    equ     60              ; w cursor: segment
vPos    equ     62              ; l cursor: unit
vObj    equ     66              ; w cursor: object
vFocus  equ     68              ; w 0 road, 1 objects
vZoom   equ     70              ; w 0..7 (strips 128 >> zoom units per pixel; map x1..x16)
vVStart equ     72              ; l first unit of the strips
vOx     equ     76              ; w map origin (world / 4)
vOy     equ     78
vS      equ     80              ; w map scale at zoom 0 (pixels per world/4 unit, 16 fraction bits)
vSh     equ     82              ; w 16 - map zoom shift
vCx     equ     84              ; w bbox centre
vCy     equ     86
vRedraw equ     88              ; w bit 0 everything, bit 1 highlight + status
vPDir   equ     90              ; w directions held at the previous poll
vRep    equ     92              ; w auto-repeat countdown
vRes    equ     94              ; w 1 = leave the viewer
vState  equ     96              ; w 0 lists, 1 viewer, 2 viewer menu, 3 help (read by the gate scripts)
vSrc    equ     98              ; w 0 campaign track, 1 stock track, 2 plain straight
vSrcIx  equ     100             ; w
vMsg    equ     102             ; l message for the hint row (0 = the key hints)
vFire   equ     106             ; w fire is held
vFireMv equ     108             ; w a direction was used while fire was held
vMCnt   equ     110             ; w list picker: items
vMSel   equ     112             ; w selection
vAcc    equ     114             ; l expand: hill accel of the segment
vAx     equ     118             ; l expand: path accumulators (world * 2^15)
vAy     equ     122
vTmp    equ     126             ; l
vPX     equ     130             ; w path drawing: previous point
vPY     equ     132
vPOk    equ     134             ; w
vThick  equ     136             ; w
vBlkEnd equ     138             ; l
vAcc2   equ     142             ; l
vName   equ     146             ; 26 B track name
vMItems equ     176             ; 20 l list picker item texts
vLine   equ     256             ; 64 B text line
vTxt    equ     320             ; 20 x 40 B item texts

        dc.b    'MSED'          ; +0  magic
        dc.w    EDVER,0         ; +4  version (cp_title refuses another one), flags
        dc.l    0               ; +8  file length (msrpatch.py)
        dc.l    0               ; +12 CRC-32 of the bytes from +16 (msrpatch.py)

; ---------------------------------------------------------------- entry (called by cp_title; supervisor, the title's context).  Returns when the user leaves.
ed_main:
        movem.l d0-d7/a0-a6,-(a7)
        lea     V.l,a5
        movea.l a5,a0
        move.w  #$1ff,d0
.zv:    clr.l   (a0)+
        dbra    d0,.zv
        bsr     sin_init
        bsr     take
.top:   bsr     top_list                ; d0 = -1 leave, else a track is loaded
        tst.w   d0
        bmi   .x
        bsr     view
        bra   .top
.x:     bsr     give
        clr.b   $60ff.w
        movem.l (a7)+,d0-d7/a0-a6
        rts

; ---- the screen: own buffer and palette while the editor runs; the game's VBL ($d11e: music, mouse poll) and IKBD handler stay as they are (the title has no raster split)
take:   move.b  $ffff8201.w,vScr(a5)
        move.b  $ffff8203.w,vScr+1(a5)
        lea     $ffff8240.w,a0
        lea     vPal(a5),a1
        moveq   #15,d0
.s:     move.w  (a0)+,(a1)+
        dbra    d0,.s
        bsr     cls
        jsr     $d206.l
        move.b  #SCR>>16,$ffff8201.w
        move.b  #(SCR>>8)&$ff,$ffff8203.w
        lea     pal(pc),a0
        lea     $ffff8240.w,a1
        moveq   #15,d0
.p:     move.w  (a0)+,(a1)+
        dbra    d0,.p
        rts

give:   jsr     $d206.l
        move.b  vScr(a5),$ffff8201.w
        move.b  vScr+1(a5),$ffff8203.w
        lea     vPal(a5),a0
        lea     $ffff8240.w,a1
        moveq   #15,d0
.p:     move.w  (a0)+,(a1)+
        dbra    d0,.p
        rts

cls:    lea     SCR.l,a0
        move.w  #7999,d0
.c:     clr.l   (a0)+
        dbra    d0,.c
        rts

sin_init:                               ; SINT[i] = 32767 * sin(2 pi i / 4096), i = 0..5119 (cos = SINT[i + 1024])
        lea     SINT.l,a0
        lea     qsin(pc),a1
        moveq   #0,d0
.l:     move.w  d0,d1
        andi.w  #$fff,d1
        cmpi.w  #2048,d1
        bcs   .pos
        subi.w  #2048,d1
        bsr   .q
        neg.w   d2
        bra   .st
.pos:   bsr   .q
.st:    move.w  d2,(a0)+
        addq.w  #1,d0
        cmpi.w  #5120,d0
        bne   .l
        rts
.q:     cmpi.w  #1024,d1                ; d1 = 0..2047 -> d2 = sine of the half wave
        bls   .q1
        neg.w   d1
        addi.w  #2048,d1
.q1:    add.w   d1,d1
        move.w  (a1,d1.w),d2
        rts

; ---------------------------------------------------------------- text
; ptext: a0 = text (NUL), d0 = column 0..39, d1 = row 0..24, d2 = colour 0..15 (+16 = inverse: a bar of the colour, black text).  Lower case is shown as capitals (the game's font has no descenders).
ptext:  movem.l d0-d7/a0-a3,-(a7)
        lea     SCR.l,a2
        mulu    #1280,d1
        adda.l  d1,a2
        move.w  d0,d3
        lsr.w   #1,d3
        lsl.w   #3,d3
        adda.w  d3,a2
        andi.w  #1,d0
        adda.w  d0,a2
.ch:    moveq   #0,d0
        move.b  (a0)+,d0
        beq   .x
        cmpi.b  #'a',d0
        bcs   .u
        cmpi.b  #'z',d0
        bhi   .u
        subi.b  #$20,d0
.u:     subi.w  #$20,d0
        bcc   .ok
        moveq   #0,d0
.ok:    lsl.w   #4,d0
        lea     $190be.l,a1             ; the game's 8x8 font: 16 B per character from $20, per row a shade byte and the glyph byte
        adda.w  d0,a1
        movea.l a2,a3
        moveq   #7,d7
.r:     move.b  1(a1),d3
        addq.l  #2,a1
        btst    #4,d2
        beq   .ni
        not.b   d3
.ni:    btst    #0,d2
        sne     d5
        and.b   d3,d5
        move.b  d5,(a3)
        btst    #1,d2
        sne     d5
        and.b   d3,d5
        move.b  d5,2(a3)
        btst    #2,d2
        sne     d5
        and.b   d3,d5
        move.b  d5,4(a3)
        btst    #3,d2
        sne     d5
        and.b   d3,d5
        move.b  d5,6(a3)
        lea     160(a3),a3
        dbra    d7,.r
        move.l  a2,d0
        btst    #0,d0
        beq   .ev
        addq.l  #6,a2
.ev:    addq.l  #1,a2
        bra   .ch
.x:     movem.l (a7)+,d0-d7/a0-a3
        rts

; line builder: a1 = write pointer into vLine
lbeg:   lea     vLine(a5),a1
        rts
apps:   move.b  (a0)+,(a1)+             ; a0 = text
        bne   apps
        subq.l  #1,a1
        rts
; appn: d0.l = value (unsigned), d1 = digits, zero padded
appn:   movem.l d0-d3,-(a7)
        adda.w  d1,a1
        movea.l a1,a0
        subq.w  #1,d1
.d:     divu    #10,d0
        swap    d0
        addi.b  #'0',d0
        move.b  d0,-(a0)
        clr.w   d0
        swap    d0
        dbra    d1,.d
        movem.l (a7)+,d0-d3
        rts
; apsn: d0.w signed value -> sign and d1 digits
apsn:   move.b  #'+',(a1)
        tst.w   d0
        bpl   .p
        move.b  #'-',(a1)
        neg.w   d0
.p:     addq.l  #1,a1
        andi.l  #$ffff,d0
        bra   appn
; lend: pad the line to 40 columns and show it on row d1 in colour d2
lend:   lea     vLine+40(a5),a0
.p:     cmpa.l  a0,a1
        bcc   .t
        move.b  #' ',(a1)+
        bra   .p
.t:     clr.b   vLine+40(a5)
        lea     vLine(a5),a0
        moveq   #0,d0
        bra     ptext

; ---------------------------------------------------------------- pixels
; plot: d0 = x 0..319, d1 = y 0..199, d2 = colour (the planes of its set bits are OR-ed).  All registers kept.
plot:   movem.l d0-d1/d3/a2,-(a7)
        mulu    #160,d1
        move.w  d0,d3
        lsr.w   #4,d3
        lsl.w   #3,d3
        add.w   d3,d1
        lea     SCR.l,a2
        adda.w  d1,a2
        andi.w  #15,d0
        move.w  #$8000,d3
        lsr.w   d0,d3
        btst    #0,d2
        beq   .1
        or.w    d3,(a2)
.1:     btst    #1,d2
        beq   .2
        or.w    d3,2(a2)
.2:     btst    #2,d2
        beq   .3
        or.w    d3,4(a2)
.3:     btst    #3,d2
        beq   .4
        or.w    d3,6(a2)
.4:     movem.l (a7)+,d0-d1/d3/a2
        rts

; vline: d0 = x, d1 = y0, d4 = y1 (>= y0), d2 = colour
vline:  movem.l d1/d4,-(a7)
.l:     bsr   plot
        addq.w  #1,d1
        cmp.w   d4,d1
        ble   .l
        movem.l (a7)+,d1/d4
        rts
; hline: d0 = x0, d4 = x1 (>= x0), d1 = y, d2 = colour
hline:  movem.l d0/d4,-(a7)
.l:     bsr   plot
        addq.w  #1,d0
        cmp.w   d4,d0
        ble   .l
        movem.l (a7)+,d0/d4
        rts

; line: (d0,d1) -> (d4,d5), colour d2 (both ends on the screen); the start point is not drawn
line:   movem.l d0-d7/a0,-(a7)
        move.w  d4,d6
        sub.w   d0,d6                   ; dx
        moveq   #1,d3                   ; sx
        tst.w   d6
        bpl   .x1
        neg.w   d6
        moveq   #-1,d3
.x1:    move.w  d5,d7
        sub.w   d1,d7                   ; dy
        movea.w #1,a0                   ; sy
        tst.w   d7
        bpl   .y1
        neg.w   d7
        movea.w #-1,a0
.y1:    cmp.w   d7,d6
        bcs   .steep
        move.w  d6,d4                   ; count = dx, error in d5
        beq   .done
        move.w  d6,d5
        lsr.w   #1,d5
.lx:    add.w   d3,d0
        sub.w   d7,d5
        bpl   .px
        add.w   d6,d5
        add.w   a0,d1
.px:    bsr     plot
        subq.w  #1,d4
        bne   .lx
        bra   .done
.steep: move.w  d7,d4
        move.w  d7,d5
        lsr.w   #1,d5
.ly:    add.w   a0,d1
        sub.w   d6,d5
        bpl   .py
        add.w   d7,d5
        add.w   d3,d0
.py:    bsr     plot
        subq.w  #1,d4
        bne   .ly
.done:  movem.l (a7)+,d0-d7/a0
        rts

clr_hi:                                 ; clear bitplane 3 of rows 8..175 (the highlight and the cursor live there)
        lea     SCR+8*160+6.l,a0
        move.w  #168*20-1,d0
.c:     clr.w   (a0)
        addq.l  #8,a0
        dbra    d0,.c
        rts

; ---------------------------------------------------------------- the track model
; rd_stock: d0.w = level 0..14 -> the level's track block in BLK (the game's own file service, as the race setup $77c6 calls it); a0 = BLK, a6 = its end
rd_stock:
        movem.l d0-d7/a1-a5,-(a7)
        lea     $28a2.w,a0
        add.w   d0,d0
        add.w   d0,d0
        movea.l (a0,d0.w),a0
        moveq   #0,d0
        move.w  (a0)+,d1
        move.w  (a0),d2
        moveq   #0,d3
        move.w  d2,V+vTmp.l
        lea     BLK.l,a0
        jsr     $d6fa.l
        movem.l (a7)+,d0-d7/a1-a5
        lea     BLK.l,a0
        moveq   #0,d0
        move.w  vTmp(a5),d0
        lsl.l   #8,d0
        add.l   d0,d0
        lea     (a0,d0.l),a6
        rts

; skip: a0 -> a (count, value) stream; -> a0 behind its zero count.  Carry set = it runs past the block end a6
skip:   cmpa.l  a6,a0
        bcc   .bad
        tst.w   (a0)+
        beq   .ok
        addq.l  #2,a0
        bra   skip
.ok:    andi    #$fe,ccr
        rts
.bad:   ori     #1,ccr
        rts

; parse: a0 = track block, a6 = its end -> the segment list (the union of the breakpoints of the four ring streams: one segment = a stretch with one curve delta, one hill
; accel and one pair of width targets), the object list, the BAR.  d0 = 0 ok / 1 damaged block
parse:  movem.l d1-d7/a0-a4/a6,-(a7)
        movea.l a0,a4
        bsr   skip                    ; S0 curve
        bcs     .bad
        movea.l a0,a1                   ; S1 left
        bsr   skip
        bcs     .bad
        movea.l a0,a2                   ; S2 right
        bsr   skip
        bcs     .bad
        movea.l a0,a3                   ; S3 hill
        bsr   skip
        bcs     .bad
        move.l  a0,vTmp(a5)             ; S4 objects
        movea.l a4,a0
        moveq   #0,d0
        moveq   #0,d1
        moveq   #0,d2
        moveq   #0,d3
        move.w  (a0),d0
        beq     .bad
        move.w  (a1),d1
        beq     .bad
        move.w  (a2),d2
        beq     .bad
        move.w  (a3),d3
        beq     .bad
        lea     SEGT.l,a4
        moveq   #0,d6                   ; position
        moveq   #0,d7                   ; segments
.m:     move.l  d0,d5                   ; length = the shortest remainder
        cmp.l   d1,d5
        bls   .m1
        move.l  d1,d5
.m1:    cmp.l   d2,d5
        bls   .m2
        move.l  d2,d5
.m2:    cmp.l   d3,d5
        bls   .m3
        move.l  d3,d5
.m3:    move.l  #32768,d4
        sub.l   d6,d4
        beq   .segd
        cmp.l   d4,d5
        bls   .m4
        move.l  d4,d5
.m4:    move.w  d6,(a4)+
        move.w  d5,(a4)+
        move.w  2(a0),(a4)+
        move.w  2(a3),(a4)+
        move.b  3(a1),(a4)+
        move.b  3(a2),(a4)+
        clr.w   (a4)+
        addq.w  #1,d7
        add.l   d5,d6
        sub.l   d5,d0
        bne   .k0
        addq.l  #4,a0
        move.w  (a0),d0
        beq   .segd
.k0:    sub.l   d5,d1
        bne   .k1
        addq.l  #4,a1
        move.w  (a1),d1
        beq   .segd
.k1:    sub.l   d5,d2
        bne   .k2
        addq.l  #4,a2
        move.w  (a2),d2
        beq   .segd
.k2:    sub.l   d5,d3
        bne   .k3
        addq.l  #4,a3
        move.w  (a3),d3
        beq   .segd
.k3:    cmpi.w  #MAXSEG,d7
        bcs   .m
.segd:  move.w  d7,vNSeg(a5)
        move.l  d6,vTotal(a5)
        ; objects: first.w, then (type, lateral, gap to the next), gap 0 ends the list
        movea.l vTmp(a5),a0
        lea     OBJT.l,a1
        moveq   #0,d7
        moveq   #0,d6
        move.w  (a0)+,d6                ; position of the first
.o:     cmpa.l  a6,a0
        bcc     .bad
        move.w  d6,(a1)+
        move.w  (a0)+,(a1)+
        move.w  (a0)+,(a1)+
        clr.w   (a1)+
        addq.w  #1,d7
        move.w  (a0)+,d0
        beq   .od
        add.w   d0,d6
        cmpi.w  #MAXOBJ,d7
        bcs   .o
.od:    move.w  d7,vNObj(a5)
        ; type table: 12-byte entries $ff00, kind, size, sprite, w4, w5; the BAR is the type with sprite $21
        moveq   #0,d7
        clr.w   vBarT(a5)
.t:     lea     12(a0),a1
        cmpa.l  a6,a1
        bhi   .td
        cmpi.w  #$ff00,(a0)
        bne   .td
        addq.w  #1,d7
        cmpi.w  #$21,6(a0)
        bne   .tn
        tst.w   vBarT(a5)
        bne   .tn
        move.w  d7,vBarT(a5)
.tn:    movea.l a1,a0
        bra   .t
.td:    move.w  d7,vNTypes(a5)
        bsr     find_bar
        moveq   #0,d0
        bra   .x
.bad:   moveq   #1,d0
.x:     movem.l (a7)+,d1-d7/a0-a4/a6
        tst.w   d0
        rts

find_bar:                               ; flag the BAR objects, vBarAt = the first, vNBar = how many
        lea     OBJT.l,a0
        moveq   #-1,d1
        moveq   #0,d2
        move.w  vNObj(a5),d0
        beq   .x
        subq.w  #1,d0
        move.w  vBarT(a5),d3
        beq   .x
.l:     clr.w   6(a0)
        cmp.w   2(a0),d3
        bne   .n
        move.w  #1,6(a0)
        addq.w  #1,d2
        tst.l   d1
        bpl   .n
        moveq   #0,d1
        move.w  (a0),d1
.n:     addq.l  #8,a0
        dbra    d0,.l
.x:     move.l  d1,vBarAt(a5)
        move.w  d2,vNBar(a5)
        rts

; expand: the per-unit arrays as the game's own setup computes them ($ff3a curve ring, $fde0 widths, $ffe4 hill) and the top-down path (heading = curve value / 600 rad, as tools/msrtrack.py render)
expand: movem.l d0-d7/a0-a6,-(a7)
        lea     HARR.l,a0               ; the three arrays are consecutive: clear them
        move.w  #3*8192-1,d0
.z:     clr.l   (a0)+
        dbra    d0,.z
        lea     HARR.l,a0
        lea     WLARR.l,a1
        lea     WRARR.l,a2
        lea     PTS.l,a3
        clr.l   (a3)+
        clr.l   vAx(a5)
        clr.l   vAy(a5)
        lea     SEGT.l,a4
        moveq   #0,d0                   ; c
        moveq   #0,d1                   ; sum of c over 8 units
        moveq   #0,d2                   ; hill: slope
        moveq   #0,d3                   ; hill: height (16.16)
        moveq   #0,d4
        moveq   #0,d5
        move.b  8(a4),d4                ; the widths start at the first targets
        move.b  9(a4),d5
        move.w  vNSeg(a5),d7
        beq     .x
        move.w  d7,vTmp(a5)
.seg:   move.w  6(a4),d6
        ext.l   d6
        move.l  d6,vAcc(a5)
        moveq   #0,d6
        move.w  2(a4),d6
        subq.l  #1,d6                   ; 1..32768 units
.u:     add.w   4(a4),d0
        movea.w d0,a6
        add.l   a6,d1
        add.l   d2,d3
        add.l   vAcc(a5),d2
        move.l  d3,d7
        bpl   .hp
        moveq   #0,d7
        bra   .hs
.hp:    swap    d7
        cmpi.w  #127,d7
        bls   .hs
        moveq   #127,d7
.hs:    move.b  d7,(a0)+
        move.b  d4,(a1)+
        cmp.b   8(a4),d4
        beq   .l2
        bhi   .l1
        addq.b  #1,d4
        bra   .l2
.l1:    subq.b  #1,d4
.l2:    move.b  d5,(a2)+
        cmp.b   9(a4),d5
        beq   .r2
        bhi   .r1
        addq.b  #1,d5
        bra   .r2
.r1:    subq.b  #1,d5
.r2:    move.w  a0,d7
        andi.w  #7,d7
        bne   .n8
        asr.l   #3,d1                   ; mean curve value of the 8 units
        muls    #17801,d1               ; * 4096 / (2 pi 600) = 1.08649 (17801 / 16384)
        moveq   #14,d7
        asr.l   d7,d1
        andi.w  #$fff,d1
        add.w   d1,d1
        lea     SINT.l,a6
        move.w  (a6,d1.w),d7
        ext.l   d7
        asl.l   #3,d7
        add.l   d7,vAx(a5)
        lea     SINT+2048.l,a6
        move.w  (a6,d1.w),d7
        ext.l   d7
        asl.l   #3,d7
        sub.l   d7,vAy(a5)              ; heading 0 = up the screen
        move.l  vAx(a5),d7
        swap    d7
        asr.w   #1,d7
        move.w  d7,(a3)+
        move.l  vAy(a5),d7
        swap    d7
        asr.w   #1,d7
        move.w  d7,(a3)+
        moveq   #0,d1
.n8:    subq.l  #1,d6
        bpl     .u
        lea     SEGSZ(a4),a4
        subq.w  #1,vTmp(a5)
        bne     .seg
.x:     ; the extent shown: max(race length, BAR) + 1024, at most the stream length
        moveq   #0,d0
        move.w  vBase(a5),d0
        add.w   d0,d0
        lea     rltab(pc),a0
        move.w  (a0,d0.w),d0
        move.w  d0,vRl(a5)
        addi.l  #1024,d0                ; race length + the ring's look-ahead (what msrtrack.py render shows) ...
        move.l  vBarAt(a5),d1
        bmi   .e1
        addi.l  #512,d1                 ; ... and at least 512 units behind the BAR
        cmp.l   d0,d1
        ble   .e1
        move.l  d1,d0
.e1:
        cmp.l   vTotal(a5),d0
        bls   .e2
        move.l  vTotal(a5),d0
.e2:    andi.w  #$fff8,d0
        move.l  d0,vEnd(a5)
        ; bounding box of the path -> scale and centre of the map (window 304 x 96 pixels inside x 0..319, y 8..111)
        lea     PTS.l,a0
        lsr.l   #3,d0
        move.w  (a0),d1                 ; min x
        move.w  d1,d2                   ; max x
        move.w  2(a0),d3
        move.w  d3,d4
.bb:    move.w  (a0)+,d5
        cmp.w   d1,d5
        bge   .b1
        move.w  d5,d1
.b1:    cmp.w   d2,d5
        ble   .b2
        move.w  d5,d2
.b2:    move.w  (a0)+,d5
        cmp.w   d3,d5
        bge   .b3
        move.w  d5,d3
.b3:    cmp.w   d4,d5
        ble   .b4
        move.w  d5,d4
.b4:    dbra    d0,.bb
        move.w  d1,d5
        add.w   d2,d5
        asr.w   #1,d5
        move.w  d5,vCx(a5)
        move.w  d3,d5
        add.w   d4,d5
        asr.w   #1,d5
        move.w  d5,vCy(a5)
        sub.w   d1,d2                   ; width
        cmpi.w  #1024,d2
        bcc   .w1
        move.w  #1024,d2
.w1:    sub.w   d3,d4                   ; height
        cmpi.w  #1024,d4
        bcc   .w2
        move.w  #1024,d4
.w2:    move.l  #304<<16,d0
        divu    d2,d0
        move.l  #96<<16,d1
        divu    d4,d1
        cmp.w   d0,d1
        bcc   .w3
        move.w  d1,d0
.w3:    move.w  d0,vS(a5)
        movem.l (a7)+,d0-d7/a0-a6
        rts

; find_seg: vPos -> vSeg (the segment that holds the unit)
find_seg:
        movem.l d0-d2/a0,-(a7)
        lea     SEGT.l,a0
        move.l  vPos(a5),d0
        moveq   #0,d1
        move.w  vNSeg(a5),d2
        subq.w  #1,d2
.l:     cmp.w   d2,d1
        bcc   .f
        cmp.w   SEGSZ(a0),d0            ; the next segment starts beyond the unit
        bcs   .f
        lea     SEGSZ(a0),a0
        addq.w  #1,d1
        bra   .l
.f:     move.w  d1,vSeg(a5)
        movem.l (a7)+,d0-d2/a0
        rts
; seg_ptr: vSeg -> a0
seg_ptr:
        move.w  vSeg(a5),d0
        mulu    #SEGSZ,d0
        lea     SEGT.l,a0
        adda.l  d0,a0
        rts

; ---------------------------------------------------------------- the viewer's picture
; mapxy: a0 -> path point -> d0 = x, d1 = y on the screen; carry set = outside the map window.  Trashes d3
mapxy:  move.w  (a0),d0
        sub.w   vOx(a5),d0
        muls    vS(a5),d0
        move.w  vSh(a5),d3
        asr.l   d3,d0
        addi.l  #160,d0
        cmpi.l  #320,d0
        bcc   .out
        move.w  2(a0),d1
        sub.w   vOy(a5),d1
        muls    vS(a5),d1
        asr.l   d3,d1
        addi.l  #60,d1
        cmpi.l  #8,d1
        blt   .out
        cmpi.l  #112,d1
        bge   .out
        andi    #$fe,ccr
        rts
.out:   ori     #1,ccr
        rts

; path: units d6 .. d7 of the path in colour d2; vThick = 2x2 pixels (the highlight)
path:   movem.l d0-d7/a0,-(a7)
        lsr.l   #3,d6
        lsr.l   #3,d7
        sub.w   d6,d7
        bcs   .x
        lea     PTS.l,a0
        lsl.w   #2,d6
        adda.w  d6,a0
        clr.w   vPOk(a5)
.l:     bsr   mapxy
        bcs   .no
        tst.w   vPOk(a5)
        beq   .pl
        move.w  d0,d4                   ; more than one pixel from the previous point: join them
        sub.w   vPX(a5),d4
        addq.w  #1,d4
        cmpi.w  #2,d4
        bhi   .ln
        move.w  d1,d4
        sub.w   vPY(a5),d4
        addq.w  #1,d4
        cmpi.w  #2,d4
        bls   .pl
.ln:    move.w  d0,d4
        move.w  d1,d5
        move.w  vPX(a5),d0
        move.w  vPY(a5),d1
        bsr     line
        move.w  d4,d0
        move.w  d5,d1
.pl:    bsr     plot
        tst.w   vThick(a5)
        beq   .th
        addq.w  #1,d0
        bsr     plot
        addq.w  #1,d1
        bsr     plot
        subq.w  #1,d0
        bsr     plot
        subq.w  #1,d1
.th:    move.w  d0,vPX(a5)
        move.w  d1,vPY(a5)
        move.w  #1,vPOk(a5)
        bra   .nx
.no:    clr.w   vPOk(a5)
.nx:    addq.l  #4,a0
        dbra    d7,.l
.x:     movem.l (a7)+,d0-d7/a0
        rts

; box: a 5x5 outline around the path point of unit d6 in colour d2
box:    movem.l d0-d7/a0,-(a7)
        lsr.l   #3,d6
        lsl.w   #2,d6
        lea     PTS.l,a0
        adda.w  d6,a0
        bsr     mapxy
        bcs   .x
        cmpi.w  #3,d0
        bcs   .x
        cmpi.w  #316,d0
        bhi   .x
        cmpi.w  #11,d1
        bcs   .x
        cmpi.w  #108,d1
        bhi   .x
        subq.w  #2,d0
        subq.w  #2,d1
        move.w  d0,d4
        addq.w  #4,d4
        bsr     hline
        addq.w  #4,d1
        bsr     hline
        subq.w  #4,d1
        move.w  d1,d4
        addq.w  #4,d4
        bsr     vline
        addq.w  #4,d0
        bsr     vline
.x:     movem.l (a7)+,d0-d7/a0
        rts

; upx: d0.l = unit -> d0 = x of the strips (64..319); carry set = not in view
upx:    sub.l   vVStart(a5),d0
        bcs   .out
        moveq   #7,d1
        sub.w   vZoom(a5),d1
        lsr.l   d1,d0
        cmpi.l  #256,d0
        bcc   .out
        addi.w  #64,d0
        andi    #$fe,ccr
        rts
.out:   ori     #1,ccr
        rts

draw_all:
        bsr     cls
        ; header: source, name, scenery
        bsr     lbeg
        lea     t_src(pc),a0
        move.w  vSrc(a5),d0
        lsl.w   #2,d0
        adda.w  d0,a0
        bsr     apps
        cmpi.w  #2,vSrc(a5)
        beq   .h1
        moveq   #0,d0
        move.w  vSrcIx(a5),d0
        addq.w  #1,d0
        moveq   #2,d1
        bsr     appn
.h1:    move.b  #' ',(a1)+
        lea     vName(a5),a0
        bsr     apps
        lea     vLine+29(a5),a0
.h2:    cmpa.l  a0,a1
        bcc   .h3
        move.b  #' ',(a1)+
        bra   .h2
.h3:    lea     t_scen(pc),a0
        bsr     apps
        moveq   #0,d0
        move.w  vBase(a5),d0
        addq.w  #1,d0
        moveq   #2,d1
        bsr     appn
        moveq   #0,d1
        moveq   #8,d2
        bsr     lend
        lea     t_hill(pc),a0
        moveq   #0,d0
        moveq   #15,d1
        moveq   #3,d2
        bsr     ptext
        lea     t_width(pc),a0
        moveq   #19,d1
        moveq   #4,d2
        bsr     ptext
        lea     t_objs(pc),a0
        moveq   #21,d1
        moveq   #5,d2
        bsr     ptext
        ; ---- strips: one column per pixel, 128 >> zoom units each
        moveq   #7,d7
        sub.w   vZoom(a5),d7            ; shift
        moveq   #0,d6                   ; a tick every 1000 units at the top of the hill strip
.g:     move.l  d6,d0
        bsr     upx
        bcs   .g1
        moveq   #114,d1                 ; a tick under the highlight bar
        moveq   #117,d4
        moveq   #1,d2
        bsr     vline
.g1:    addi.l  #1000,d6
        cmp.l   vEnd(a5),d6
        bcs   .g
        moveq   #0,d5                   ; pixel column
        lea     HARR.l,a0
        lea     WLARR.l,a1
        lea     WRARR.l,a2
.c:     moveq   #0,d6
        move.w  d5,d6
        lsl.l   d7,d6
        add.l   vVStart(a5),d6          ; unit
        cmp.l   vEnd(a5),d6
        bcc   .cd
        moveq   #64,d0
        add.w   d5,d0
        moveq   #0,d3
        move.b  (a0,d6.l),d3
        lsr.w   #2,d3
        move.w  #143,d4
        move.w  d4,d1
        sub.w   d3,d1
        moveq   #3,d2
        cmp.l   vBarAt(a5),d6
        ble   .c1
        tst.l   vBarAt(a5)
        bmi   .c1
        moveq   #1,d2                   ; behind the BAR: dim
.c1:    bsr     vline
        moveq   #0,d3
        move.b  (a1,d6.l),d3
        lsr.w   #3,d3
        move.w  #156,d1
        sub.w   d3,d1
        moveq   #0,d3
        move.b  (a2,d6.l),d3
        lsr.w   #3,d3
        move.w  #156,d4
        add.w   d3,d4
        moveq   #4,d2
        bsr     vline
        move.w  #172,d1
        moveq   #1,d2
        bsr     plot
        addq.w  #1,d5
        cmpi.w  #256,d5
        bne   .c
.cd:    lea     OBJT.l,a3               ; objects: left of the road above the line, right below, the BAR in red over both
        move.w  vNObj(a5),d5
        beq   .od
        subq.w  #1,d5
.o:     moveq   #0,d0
        move.w  (a3),d0
        cmp.l   vEnd(a5),d0
        bcc   .on
        bsr     upx
        bcs   .on
        tst.w   6(a3)
        beq   .o1
        move.w  #168,d1
        move.w  #175,d4
        moveq   #6,d2
        bra   .o3
.o1:    moveq   #5,d2
        move.w  #169,d1
        move.w  #171,d4
        tst.w   4(a3)
        bmi   .o3
        move.w  #173,d1
        move.w  #175,d4
.o3:    bsr     vline
.on:    addq.l  #8,a3
        dbra    d5,.o
.od:    ; ---- the map
        clr.w   vThick(a5)
        moveq   #0,d6
        move.l  vEnd(a5),d7
        moveq   #2,d2
        move.l  vBarAt(a5),d0
        bmi   .m1
        cmp.l   d7,d0
        bcc   .m1
        move.l  d0,d7
        bsr     path
        move.l  d0,d6
        move.l  vEnd(a5),d7
        moveq   #1,d2                   ; behind the BAR: dim
.m1:    bsr     path
        move.l  #1000,d6                ; a dot every 1000 units
.k:     cmp.l   vEnd(a5),d6
        bcc   .kd
        move.l  d6,d0
        lsr.l   #3,d0
        lsl.w   #2,d0
        lea     PTS.l,a0
        adda.w  d0,a0
        bsr     mapxy
        bcs   .kn
        moveq   #5,d2
        bsr     plot
        addq.w  #1,d0
        cmpi.w  #320,d0
        bcc   .kn
        bsr     plot
.kn:    addi.l  #1000,d6
        bra   .k
.kd:    moveq   #0,d6
        moveq   #3,d2
        bsr     box                     ; start: green
        move.l  vBarAt(a5),d6
        bmi   .nb
        cmp.l   vEnd(a5),d6
        bcc   .nb
        moveq   #6,d2
        bsr     box                     ; the BAR: red
.nb:    rts

; draw_hi: the highlight (bitplane 3): the cursor's segment on the map and above / below the strips, the cursor, the two status rows and the hint row
draw_hi:
        bsr     clr_hi
        bsr     seg_ptr
        moveq   #0,d6
        move.w  (a0),d6                 ; start
        moveq   #0,d7
        move.w  2(a0),d7
        add.l   d6,d7                   ; end (exclusive)
        cmp.l   vEnd(a5),d7
        bls   .a
        move.l  vEnd(a5),d7
.a:     moveq   #8,d2
        move.w  #1,vThick(a5)
        bsr     path
        clr.w   vThick(a5)
        ; the segment's span on the strips
        move.l  vVStart(a5),d0
        cmp.l   d0,d6
        bcc   .s1
        move.l  d0,d6
.s1:    moveq   #7,d1
        sub.w   vZoom(a5),d1
        move.l  #256,d3
        lsl.l   d1,d3
        add.l   d0,d3                   ; first unit right of the strips
        cmp.l   d3,d7
        bls   .s2
        move.l  d3,d7
.s2:    cmp.l   d7,d6
        bcc   .s3
        subq.l  #1,d7
        move.l  d7,d0
        bsr     upx
        move.w  d0,d4
        move.l  d6,d0
        bsr     upx
        moveq   #112,d1
        moveq   #8,d2
        bsr     hline
        moveq   #113,d1
        bsr     hline
        move.w  #174,d1
        bsr     hline
        move.w  #175,d1
        bsr     hline
.s3:    move.l  vPos(a5),d0             ; the cursor
        bsr     upx
        bcs   .s4
        moveq   #112,d1
        move.w  #175,d4
        moveq   #8,d2
        bsr     vline
.s4:    move.l  vPos(a5),d0
        lsr.l   #3,d0
        lsl.w   #2,d0
        lea     PTS.l,a0
        adda.w  d0,a0
        bsr     mapxy
        bcs   .st
        cmpi.w  #4,d0
        bcs   .st
        cmpi.w  #315,d0
        bhi   .st
        cmpi.w  #12,d1
        bcs   .st
        cmpi.w  #107,d1
        bhi   .st
        moveq   #8,d2
        subq.w  #4,d0
        move.w  d0,d4
        addq.w  #8,d4
        bsr     hline
        addq.w  #4,d0
        subq.w  #4,d1
        move.w  d1,d4
        addq.w  #8,d4
        bsr     vline
.st:    ; ---- status row 22: SEG nnnn/nnnn AT nnnnn LEN nnnnn ZOOM n
        bsr     lbeg
        lea     t_seg(pc),a0
        bsr     apps
        moveq   #0,d0
        move.w  vSeg(a5),d0
        addq.w  #1,d0
        moveq   #4,d1
        bsr     appn
        move.b  #'/',(a1)+
        moveq   #0,d0
        move.w  vNSeg(a5),d0
        bsr     appn
        lea     t_at(pc),a0
        bsr     apps
        move.l  vPos(a5),d0
        moveq   #5,d1
        bsr     appn
        lea     t_len(pc),a0
        bsr     apps
        bsr     seg_ptr
        movea.l a0,a2
        moveq   #0,d0
        move.w  2(a2),d0
        moveq   #5,d1
        bsr     appn
        lea     t_zoom(pc),a0
        bsr     apps
        moveq   #0,d0
        move.w  vZoom(a5),d0
        addq.w  #1,d0
        moveq   #1,d1
        bsr     appn
        moveq   #22,d1
        moveq   #7,d2
        bsr     lend
        ; ---- status row 23
        bsr     lbeg
        tst.w   vFocus(a5)
        bne   .ob
        lea     t_curve(pc),a0          ; CURVE L09 / R10 / --- , HILL +nnnn, WIDTH nn/nn
        bsr     apps
        move.w  4(a2),d0
        bne   .cv
        lea     t_strt(pc),a0
        bsr     apps
        bra   .cw
.cv:    move.b  #'R',(a1)
        tst.w   d0
        bpl   .cp
        move.b  #'L',(a1)
        neg.w   d0
.cp:    addq.l  #1,a1
        andi.l  #$ffff,d0
        moveq   #2,d1
        bsr     appn
.cw:    lea     t_hil2(pc),a0
        bsr     apps
        move.w  6(a2),d0
        moveq   #4,d1
        bsr     apsn
        lea     t_wid2(pc),a0
        bsr     apps
        moveq   #0,d0
        move.b  8(a2),d0
        moveq   #2,d1
        bsr     appn
        move.b  #'/',(a1)+
        moveq   #0,d0
        move.b  9(a2),d0
        bsr     appn
        bra   .r23
.ob:    lea     t_obj(pc),a0            ; OBJ nnn/nnn AT nnnnn TYPE nnn SIDE +nnn
        bsr     apps
        moveq   #0,d0
        move.w  vObj(a5),d0
        move.w  d0,d3
        addq.w  #1,d0
        moveq   #3,d1
        bsr     appn
        move.b  #'/',(a1)+
        moveq   #0,d0
        move.w  vNObj(a5),d0
        bsr     appn
        lea     t_at(pc),a0
        bsr     apps
        lsl.w   #3,d3
        lea     OBJT.l,a3
        adda.w  d3,a3
        moveq   #0,d0
        move.w  (a3),d0
        moveq   #5,d1
        bsr     appn
        tst.w   6(a3)
        beq   .ot
        lea     t_bar(pc),a0
        bsr     apps
        bra   .os
.ot:    lea     t_type(pc),a0
        bsr     apps
        moveq   #0,d0
        move.w  2(a3),d0
        moveq   #3,d1
        bsr     appn
.os:    lea     t_side(pc),a0
        bsr     apps
        move.w  4(a3),d0
        moveq   #3,d1
        bsr     apsn
.r23:   moveq   #23,d1
        moveq   #7,d2
        bsr     lend
        bsr     lbeg                    ; hint row: a message once, else the keys
        moveq   #1,d2
        lea     t_hint(pc),a0
        move.l  vMsg(a5),d0
        beq   .hm
        movea.l d0,a0
        clr.l   vMsg(a5)
        moveq   #8,d2
.hm:    bsr     apps
        moveq   #24,d1
        bra     lend

; ---------------------------------------------------------------- the viewer
view:   move.w  #1,vState(a5)
        clr.w   vRes(a5)
        clr.w   vSeg(a5)
        clr.l   vPos(a5)
        clr.w   vObj(a5)
        clr.w   vFocus(a5)
        clr.w   vZoom(a5)
        clr.l   vMsg(a5)
        bsr     set_zoom
        bsr     in_reset
.loop:  move.w  vRedraw(a5),d0
        beq   .in
        clr.w   vRedraw(a5)
        btst    #0,d0
        beq   .hi
        bsr     draw_all
.hi:    bsr     draw_hi
.in:    jsr     $d206.l
        bsr     input
        tst.w   vRes(a5)
        beq   .loop
        clr.w   vState(a5)
        rts

in_reset:                               ; forget every key and wait until fire is released
        clr.b   $60ff.w
        clr.b   $607e+$48.w
        clr.b   $607e+$50.w
        clr.b   $607e+$4b.w
        clr.b   $607e+$4d.w
        move.w  #$f,vPDir(a5)
        clr.w   vFire(a5)
.f:     jsr     $d206.l
        btst    #7,$6105.w
        bne   .f
        rts

; set_zoom: the strips start so that the cursor sits in the middle; the map is the whole track at zoom 0, else centred on the cursor (x2 .. x16)
set_zoom:
        moveq   #7,d1
        sub.w   vZoom(a5),d1
        move.l  #128,d0
        lsl.l   d1,d0                   ; half the strip, in units
        move.l  vPos(a5),d2
        sub.l   d0,d2
        bpl   .v1
        moveq   #0,d2
.v1:    lsr.l   d1,d2
        lsl.l   d1,d2
        move.l  d2,vVStart(a5)
        move.w  vZoom(a5),d0
        cmpi.w  #4,d0
        bls   .z1
        moveq   #4,d0
.z1:    moveq   #16,d1
        sub.w   d0,d1
        move.w  d1,vSh(a5)
        move.w  vCx(a5),vOx(a5)
        move.w  vCy(a5),vOy(a5)
        tst.w   d0
        beq   .z2
        move.l  vPos(a5),d0
        lsr.l   #3,d0
        lsl.w   #2,d0
        lea     PTS.l,a0
        adda.w  d0,a0
        move.w  (a0)+,vOx(a5)
        move.w  (a0),vOy(a5)
.z2:    move.w  #1,vRedraw(a5)
        rts

; moved: the cursor changed: scroll the strips / re-centre the zoomed map when it left the middle, else redraw the highlight only
moved:  bsr     find_seg
        ori.w   #2,vRedraw(a5)
        move.l  vPos(a5),d0
        bsr     upx
        bcs   set_zoom
        tst.l   vVStart(a5)
        beq   .l1
        cmpi.w  #64+16,d0
        bcs   set_zoom
.l1:    cmpi.w  #64+240,d0
        bcc   set_zoom
        tst.w   vZoom(a5)
        beq   .x
        move.l  vPos(a5),d0
        lsr.l   #3,d0
        lsl.w   #2,d0
        lea     PTS.l,a0
        adda.w  d0,a0
        bsr     mapxy
        bcs   set_zoom
        cmpi.w  #48,d0
        bcs   set_zoom
        cmpi.w  #272,d0
        bcc   set_zoom
        cmpi.w  #28,d1
        bcs     set_zoom
        cmpi.w  #92,d1
        bcc     set_zoom
.x:     rts

; input: one poll per frame.  Directions = joystick port 1 or the cursor keys (latched makes, so a short tap counts), auto-repeat while held
input:  moveq   #0,d0
        move.b  $60ff.w,d0
        beq   .dirs
        clr.b   $60ff.w
        lea     keytab(pc),a0
.kt:    move.b  (a0)+,d1
        beq   .dirs
        move.b  (a0)+,d2
        cmp.b   d0,d1
        bne   .kt
        moveq   #0,d0
        move.b  d2,d0
        bra     command
.dirs:  moveq   #0,d0
        move.b  $6105.w,d0
        move.w  d0,d3                   ; fire in bit 7
        andi.w  #$f,d0
        lea     $5ffe.w,a0              ; keys held
        lea     $607e.w,a1              ; keys latched
        moveq   #0,d1                   ; taps
        tst.b   $48(a0)
        beq   .a1
        ori.w   #1,d0
.a1:    tst.b   $50(a0)
        beq   .a2
        ori.w   #2,d0
.a2:    tst.b   $4b(a0)
        beq   .a3
        ori.w   #4,d0
.a3:    tst.b   $4d(a0)
        beq   .a4
        ori.w   #8,d0
.a4:    tst.b   $48(a1)
        beq   .b1
        ori.w   #1,d1
        clr.b   $48(a1)
.b1:    tst.b   $50(a1)
        beq   .b2
        ori.w   #2,d1
        clr.b   $50(a1)
.b2:    tst.b   $4b(a1)
        beq   .b3
        ori.w   #4,d1
        clr.b   $4b(a1)
.b3:    tst.b   $4d(a1)
        beq   .b4
        ori.w   #8,d1
        clr.b   $4d(a1)
.b4:    move.w  vPDir(a5),d2
        move.w  d0,vPDir(a5)
        not.w   d2
        and.w   d0,d2
        or.w    d1,d2                   ; new this poll
        bne   .new
        tst.w   d0
        beq   .fire
        subq.w  #1,vRep(a5)
        bne   .fire
        move.w  #3,vRep(a5)
        move.w  d0,d2
        bra   .act
.new:   move.w  #14,vRep(a5)
.act:   moveq   #0,d4                   ; modifier: 1 fine (fire or Control held), 2 coarse (Shift held)
        tst.b   $1d(a0)
        bne   .fi
        tst.b   d3
        bpl   .m1
        move.w  #1,vFireMv(a5)
.fi:    moveq   #1,d4
        bra   .m2
.m1:    tst.b   $2a(a0)
        bne   .co
        tst.b   $36(a0)
        beq   .m2
.co:    moveq   #2,d4
.m2:    btst    #3,d2
        beq   .n1
        moveq   #1,d0
        bra     step
.n1:    btst    #2,d2
        beq   .n2
        moveq   #-1,d0
        bra     step
.n2:    cmpi.w  #1,d4                   ; fire + up / down = zoom, else up / down = road <> objects
        bne   .n3
        moveq   #4,d0
        btst    #0,d2
        bne     command
        moveq   #5,d0
        bra     command
.n3:    moveq   #6,d0
        bra     command
.fire:  tst.b   d3                      ; fire tapped (released with no direction used) = the menu
        bmi   .fd
        tst.w   vFire(a5)
        beq   .x
        clr.w   vFire(a5)
        tst.w   vFireMv(a5)
        bne   .x
        moveq   #8,d0
        bra     command
.fd:    tst.w   vFire(a5)
        bne   .x
        move.w  #1,vFire(a5)
        clr.w   vFireMv(a5)
.x:     rts

; step: d0 = -1 / +1, d4 = 0 one segment (or object), 1 fine (one pixel of the strips), 2 coarse (to the next 1000 units)
step:   move.l  vPos(a5),d1
        tst.w   d4
        beq   .item
        cmpi.w  #1,d4
        bne   .coarse
        moveq   #7,d2
        sub.w   vZoom(a5),d2
        moveq   #1,d3
        lsl.l   d2,d3
        tst.w   d0
        bpl   .f1
        neg.l   d3
.f1:    add.l   d3,d1
        bra   .clamp
.coarse:
        divu    #1000,d1
        move.l  d1,d2
        swap    d2                      ; remainder
        andi.l  #$ffff,d1
        tst.w   d0
        bmi   .c1
        addq.w  #1,d1
        bra   .c2
.c1:    tst.w   d2
        bne   .c2
        subq.w  #1,d1
        bpl   .c2
        moveq   #0,d1
.c2:    mulu    #1000,d1
.clamp: tst.l   d1
        bpl   .k1
        moveq   #0,d1
.k1:    move.l  vEnd(a5),d2
        subq.l  #1,d2
        cmp.l   d2,d1
        bls   .k2
        move.l  d2,d1
.k2:    move.l  d1,vPos(a5)
        bra     moved
.item:  tst.w   vFocus(a5)
        bne   .obj
        move.w  d0,d5
        bsr     seg_ptr
        tst.w   d5
        bmi   .left
        move.w  vSeg(a5),d2
        addq.w  #1,d2
        cmp.w   vNSeg(a5),d2
        bcc   step_no
        moveq   #0,d1
        move.w  SEGSZ(a0),d1
        cmp.l   vEnd(a5),d1
        bcc   step_no
        bra   .k2
.left:  moveq   #0,d2
        move.w  (a0),d2
        cmp.l   d2,d1                   ; inside the segment: to its start
        bhi   .l1
        tst.w   vSeg(a5)
        beq   step_no
        move.w  -SEGSZ(a0),d2
.l1:    move.l  d2,d1
        bra   .k2
.obj:   move.w  vObj(a5),d2
        add.w   d0,d2
        bmi   step_no
        cmp.w   vNObj(a5),d2
        bcc   step_no
        move.w  d2,vObj(a5)
obj_pos:
        move.w  vObj(a5),d2
        lsl.w   #3,d2
        lea     OBJT.l,a0
        moveq   #0,d1
        move.w  (a0,d2.w),d1
        move.l  vEnd(a5),d2
        subq.l  #1,d2
        cmp.l   d2,d1
        bls   .o1
        move.l  d2,d1
.o1:    move.l  d1,vPos(a5)
        bra     moved
step_no: rts

; command: d0 = 1 leave, 2 start, 3 the BAR, 4 zoom in, 5 zoom out, 6 road <> objects, 7 help, 8 menu, 9 Return / Space (the editor's "repeat": nothing to repeat in the viewer)
command:
        subq.w  #1,d0
        bne   .c2
        move.w  #1,vRes(a5)
        rts
.c2:    subq.w  #1,d0
        bne   .c3
        clr.l   vPos(a5)
.go:    clr.w   vFocus(a5)
        bra     moved
.c3:    subq.w  #1,d0
        bne   .c4
        move.l  vBarAt(a5),d1
        bmi   .nobar
        move.l  d1,vPos(a5)
        bra   .go
.nobar: lea     t_nobar(pc),a0
.msg:   move.l  a0,vMsg(a5)
        ori.w   #2,vRedraw(a5)
        rts
.c4:    subq.w  #1,d0
        bne   .c5
        cmpi.w  #7,vZoom(a5)
        bcc   .r
        addq.w  #1,vZoom(a5)
        bra     set_zoom
.c5:    subq.w  #1,d0
        bne   .c6
        tst.w   vZoom(a5)
        beq   .r
        subq.w  #1,vZoom(a5)
        bra     set_zoom
.c6:    subq.w  #1,d0
        bne   .c7
        tst.w   vFocus(a5)
        beq   .toobj
        clr.w   vFocus(a5)
        bra     moved
.toobj: move.w  vNObj(a5),d1            ; the first object at or behind the cursor (else the last one)
        beq   .r
        lea     OBJT.l,a0
        moveq   #0,d2
        move.l  vPos(a5),d3
.s:     cmp.w   (a0),d3
        bls   .sf
        addq.l  #8,a0
        addq.w  #1,d2
        cmp.w   d1,d2
        bcs   .s
        subq.w  #1,d2
.sf:    move.w  d2,vObj(a5)
        move.w  #1,vFocus(a5)
        bra     obj_pos
.c7:    subq.w  #1,d0
        bne   .c8
        bsr     help
        bra   .back
.c8:    subq.w  #1,d0
        bne   .c9
        bsr     vmenu
        move.w  d0,-(a7)
        bsr     in_reset
        move.w  #1,vRedraw(a5)
        move.w  (a7)+,d0
        bgt     command                 ; a menu item = the same command
        rts
.c9:    lea     t_ronly(pc),a0
        bra   .msg
.back:  bsr     in_reset
        move.w  #1,vRedraw(a5)
.r:     rts

; vmenu: the viewer's menu (FIRE) -> d0 = command or 0
vmenu:  move.w  #2,vState(a5)
        lea     m_view(pc),a0
        bsr     list_fixed
        lea     t_vmenu(pc),a0
        moveq   #0,d0
        bsr     pick
        move.w  #1,vState(a5)
        tst.w   d0
        bmi   .n
        lea     vmcmd(pc),a0
        move.b  (a0,d0.w),d0
        ext.w   d0
        rts
.n:     moveq   #0,d0
        rts

help:   move.w  #3,vState(a5)
        bsr     cls
        lea     t_help(pc),a0
        moveq   #1,d1
        moveq   #8,d2
.l:     moveq   #1,d0
        bsr     ptext
.s:     tst.b   (a0)+
        bne   .s
        moveq   #7,d2
        addq.w  #1,d1
        tst.b   (a0)
        bne   .l
        clr.b   $60ff.w
.w:     jsr     $d206.l
        tst.b   $60ff.w
        bne   .d
        btst    #7,$6105.w
        beq   .w
.d:     move.w  #1,vState(a5)
        rts

; ---------------------------------------------------------------- lists (a visible selection: the chosen row is a white bar)
; list_fixed: a0 = NUL-separated texts, an empty one ends the list -> vMItems / vMCnt
list_fixed:
        lea     vMItems(a5),a1
        moveq   #0,d0
.l:     tst.b   (a0)
        beq   .x
        move.l  a0,(a1)+
        addq.w  #1,d0
.s:     tst.b   (a0)+
        bne   .s
        bra   .l
.x:     move.w  d0,vMCnt(a5)
        rts

; pick: a0 = heading, d0 = first selection -> d0 = the chosen item, or -1 (Esc, Backspace, F10, joystick left)
pick:   movem.l d1-d7/a0-a4,-(a7)
        move.w  d0,vMSel(a5)
        movea.l a0,a4
        bsr     cls
        movea.l a4,a0
        moveq   #1,d0
        moveq   #1,d1
        moveq   #8,d2
        bsr     ptext
        lea     t_lhint(pc),a0
        moveq   #24,d1
        moveq   #1,d2
        bsr     ptext
        move.l  vMsg(a5),d3
        beq   .nm
        movea.l d3,a0
        clr.l   vMsg(a5)
        moveq   #22,d1
        moveq   #6,d2
        bsr     ptext
.nm:    moveq   #0,d6
.d:     bsr   .row
        addq.w  #1,d6
        cmp.w   vMCnt(a5),d6
        bcs   .d
        move.b  $6105.w,d7              ; previous joystick byte
        clr.b   $60ff.w
.k:     jsr     $d206.l
        moveq   #0,d0
        move.b  $60ff.w,d0
        beq   .joy
        clr.b   $60ff.w
        bra   .key
.joy:   move.b  $6105.w,d1
        move.b  d7,d2
        move.b  d1,d7
        not.b   d2
        and.b   d2,d1
        beq   .k
        moveq   #$48,d0
        btst    #0,d1
        bne   .key
        moveq   #$50,d0
        btst    #1,d1
        bne   .key
        moveq   #$01,d0
        btst    #2,d1
        bne   .key
        moveq   #$1c,d0
        tst.b   d1
        bpl   .k
.key:   move.w  vMSel(a5),d6
        cmpi.b  #$48,d0
        bne   .k1
        subq.w  #1,vMSel(a5)
        bpl   .mv
        move.w  vMCnt(a5),d1
        subq.w  #1,d1
        move.w  d1,vMSel(a5)
        bra   .mv
.k1:    cmpi.b  #$50,d0
        bne   .k2
        move.w  vMSel(a5),d1
        addq.w  #1,d1
        cmp.w   vMCnt(a5),d1
        bcs   .k1a
        moveq   #0,d1
.k1a:   move.w  d1,vMSel(a5)
.mv:    bsr   .row                    ; the old row plain, the new one as a bar
        move.w  vMSel(a5),d6
        bsr   .row
        bra   .k
.k2:    cmpi.b  #$1c,d0
        beq   .ok
        cmpi.b  #$72,d0
        beq   .ok
        cmpi.b  #$39,d0
        beq   .ok
        cmpi.b  #$01,d0
        beq   .esc
        cmpi.b  #$0e,d0
        beq   .esc
        cmpi.b  #$44,d0
        beq   .esc
        bra     .k
.ok:    move.w  vMSel(a5),d0
        bra   .out
.esc:   moveq   #-1,d0
.out:   move.w  d0,-(a7)
.fr:    jsr     $d206.l                 ; fire must be released before the next screen
        btst    #7,$6105.w
        bne   .fr
        clr.b   $60ff.w
        move.w  (a7)+,d0
        movem.l (a7)+,d1-d7/a0-a4
        rts
.row:   move.w  d6,d0                   ; item d6 on row 3 + d6 (a short list: every second row)
        lsl.w   #2,d0
        lea     vMItems(a5),a0
        movea.l (a0,d0.w),a0
        moveq   #1,d0
        move.w  d6,d1
        cmpi.w  #10,vMCnt(a5)
        bhi   .r1
        add.w   d1,d1
.r1:    addq.w  #3,d1
        moveq   #7,d2
        cmp.w   vMSel(a5),d6
        bne   .rp
        moveq   #23,d2
.rp:    bra     ptext

; ---------------------------------------------------------------- the track list: the campaign in memory, a copy of an original track, a plain straight.  -> d0 = 0 a track is loaded, -1 leave
top_list:
        clr.w   vState(a5)
.again: lea     vMItems(a5),a2
        lea     vTxt(a5),a3
        moveq   #0,d5                   ; items
        moveq   #0,d6                   ; campaign tracks
        tst.b   CPV+1.l                 ; a validated campaign is in the store
        beq   .nc
        move.w  CPV+2.l,d6
        lea     CPSTORE+16.l,a4
        moveq   #0,d4
.t:     move.l  a3,(a2)+
        movea.l a3,a1
        moveq   #0,d0
        move.w  d4,d0
        addq.w  #1,d0
        moveq   #2,d1
        bsr     appn
        move.b  #' ',(a1)+
        movea.l a4,a0
        moveq   #23,d1
.n:     move.b  (a0)+,(a1)+
        dbeq    d1,.n
        bne   .n1
        subq.l  #1,a1
.n1:    lea     28(a3),a0
.n2:    cmpa.l  a0,a1
        bcc   .n3
        move.b  #' ',(a1)+
        bra   .n2
.n3:    lea     t_scen(pc),a0
        bsr     apps
        moveq   #0,d0
        move.w  24(a4),d0
        addq.w  #1,d0
        moveq   #2,d1
        bsr     appn
        clr.b   (a1)
        lea     40(a3),a3
        lea     40(a4),a4
        addq.w  #1,d4
        addq.w  #1,d5
        cmp.w   d6,d4
        bcs   .t
.nc:    lea     t_tstock(pc),a0
        move.l  a0,(a2)+
        lea     t_tstr(pc),a0
        move.l  a0,(a2)+
        lea     t_tback(pc),a0
        move.l  a0,(a2)+
        addq.w  #3,d5
        move.w  d5,vMCnt(a5)
        lea     t_top(pc),a0
        tst.w   d6
        bne   .hd
        lea     t_top0(pc),a0
.hd:    moveq   #0,d0
        bsr     pick
        tst.w   d0
        bmi     .leave
        cmp.w   d6,d0
        bcc   .other
        ; a campaign track: parsed where it lies in the campaign file
        move.w  d0,vSrcIx(a5)
        clr.w   vSrc(a5)
        mulu    #40,d0
        lea     CPSTORE+16.l,a4
        adda.l  d0,a4
        move.w  24(a4),vBase(a5)
        lea     vName(a5),a1
        movea.l a4,a0
        moveq   #23,d1
.cn:    move.b  (a0)+,(a1)+
        dbeq    d1,.cn
        clr.b   (a1)
        movea.l 28(a4),a0
        adda.l  #CPSTORE,a0
        movea.l a0,a6
        adda.l  32(a4),a6
        bsr     parse
        bne     .bad
        bra     .have
.other: sub.w   d6,d0
        beq   .stock
        subq.w  #1,d0
        bne     .leave
        ; ---- a plain straight with the scenery (object types, colours, race length) of an original track
        lea     t_pscen(pc),a0
        bsr     lev_pick
        bmi     .again
        move.w  d0,vBase(a5)
        move.w  d0,vSrcIx(a5)
        move.w  #2,vSrc(a5)
        bsr     rd_stock
        bsr     parse
        bne     .bad
        lea     SEGT.l,a0               ; one segment, the widths of the track's start, and the BAR where the original has it
        clr.w   (a0)+
        move.w  #$8000,(a0)+
        clr.l   (a0)+
        move.w  #1,vNSeg(a5)
        move.l  #32768,vTotal(a5)
        lea     OBJT.l,a0
        move.w  vNObj(a5),d0
        beq     .bad
        subq.w  #1,d0
.fb:    tst.w   6(a0)
        bne   .gb
        addq.l  #8,a0
        dbra    d0,.fb
        bra     .bad
.gb:    lea     OBJT.l,a1
        move.l  (a0)+,(a1)+
        move.l  (a0),(a1)
        move.w  #1,vNObj(a5)
        bsr     find_bar
        lea     t_nnew(pc),a0
        lea     vName(a5),a1
        bsr     apps
        clr.b   (a1)
        bra   .have
        ; ---- a copy of an original track
.stock: lea     t_pstock(pc),a0
        bsr     lev_pick
        bmi     .again
        move.w  d0,vBase(a5)
        move.w  d0,vSrcIx(a5)
        move.w  #1,vSrc(a5)
        bsr     rd_stock
        bsr     parse
        bne   .bad
        lea     vName(a5),a1
        lea     t_nstock(pc),a0
        bsr     apps
        moveq   #0,d0
        move.w  vBase(a5),d0
        addq.w  #1,d0
        moveq   #2,d1
        bsr     appn
        clr.b   (a1)
.have:  bsr     expand
        moveq   #0,d0
        rts
.bad:   lea     t_ebad(pc),a0
        move.l  a0,vMsg(a5)
        bra     .again
.leave: moveq   #-1,d0
        rts

; lev_pick: a0 = heading -> d0 = level 0..14 or -1 (list: TRACK 01 .. TRACK 15, < BACK)
lev_pick:
        movem.l d1-d7/a0-a4,-(a7)
        movea.l a0,a4
        lea     vMItems(a5),a2
        lea     vTxt(a5),a3
        moveq   #1,d4
.l:     move.l  a3,(a2)+
        movea.l a3,a1
        lea     t_track(pc),a0
        bsr     apps
        moveq   #0,d0
        move.w  d4,d0
        moveq   #2,d1
        bsr     appn
        clr.b   (a1)
        lea     40(a3),a3
        addq.w  #1,d4
        cmpi.w  #16,d4
        bne   .l
        lea     t_back(pc),a0
        move.l  a0,(a2)+
        move.w  #16,vMCnt(a5)
        movea.l a4,a0
        moveq   #0,d0
        bsr     pick
        cmpi.w  #15,d0
        bcs   .x
        moveq   #-1,d0
.x:     movem.l (a7)+,d1-d7/a0-a4
        tst.w   d0
        rts

; ---------------------------------------------------------------- tables and texts
pal:    dc.w    $000,$444,$567,$070,$057,$740,$700,$777,$770,$777,$777,$777,$777,$777,$777,$777
rltab:  dc.w    19472,19720,19800,19000,19375,18000,18626,20000,19000,20000,20000,22000,18500,22000,23000   ; race length of the 15 levels (word 0 of the minimap header, tools/msrtrack.py LEVELS)
keytab: dc.b    $01,1,$44,1             ; Esc, F10: leave
        dc.b    $47,2                   ; Clr/Home: start
        dc.b    $30,3                   ; B: the BAR
        dc.b    $4e,4,$0d,4             ; keypad +, =/+: zoom in
        dc.b    $4a,5,$0c,5             ; keypad -, -: zoom out
        dc.b    $0f,6                   ; Tab: road <> objects
        dc.b    $62,7,$3b,7             ; Help, F1
        dc.b    $1c,9,$72,9,$39,9       ; Return, Enter, Space: repeat (nothing in the viewer)
        dc.b    0
vmcmd:  dc.b    2,3,4,5,6,7,0,1
m_view: dc.b    "GO TO THE START        CLR/HOME",0
        dc.b    "GO TO THE FINISH (BAR)        B",0
        dc.b    "ZOOM IN                       +",0
        dc.b    "ZOOM OUT                      -",0
        dc.b    "ROAD <> OBJECTS             TAB",0
        dc.b    "KEYS                       HELP",0
        dc.b    "< BACK TO THE MAP",0
        dc.b    "LEAVE THIS TRACK            F10",0,0
t_vmenu: dc.b   "VIEWER MENU",0
t_src:  dc.b    "C",0,0,0,"S",0,0,0,"NEW",0
t_scen: dc.b    "SCENERY ",0
t_hill: dc.b    "HILL",0
t_width: dc.b   "WIDTH",0
t_objs: dc.b    "OBJECTS",0
t_seg:  dc.b    "SEG ",0
t_at:   dc.b    " AT ",0
t_len:  dc.b    " LEN ",0
t_zoom: dc.b    " ZOOM ",0
t_curve: dc.b   "CURVE ",0
t_strt: dc.b    "---",0
t_hil2: dc.b    "  HILL ",0
t_wid2: dc.b    "  WIDTH ",0
t_obj:  dc.b    "OBJ ",0
t_type: dc.b    " TYPE ",0
t_bar:  dc.b    " THE BAR ",0
t_side: dc.b    " SIDE ",0
t_hint: dc.b    "L/R MOVE  U/D ROAD-OBJECTS  FIRE=MENU",0
t_lhint: dc.b   "UP/DOWN + FIRE OR RETURN    ESC = BACK",0
t_nobar: dc.b   "THIS TRACK HAS NO BAR (E-BAR)",0
t_ronly: dc.b   "VIEWER: NOTHING TO REPEAT YET",0
t_top:  dc.b    "TRACK EDITOR (VIEWER): CAMPAIGN TRACKS",0
t_top0: dc.b    "TRACK EDITOR (VIEWER): NO CAMPAIGN",0
t_tstock: dc.b  "COPY OF AN ORIGINAL TRACK >",0
t_tstr: dc.b    "PLAIN STRAIGHT ROAD >",0
t_tback: dc.b   "< BACK TO THE CAMPAIGN MENU",0
t_back: dc.b    "< BACK",0
t_pstock: dc.b  "COPY WHICH ORIGINAL TRACK?",0
t_pscen: dc.b   "STRAIGHT WITH THE SCENERY OF:",0
t_track: dc.b   "TRACK ",0
t_nstock: dc.b  "COPY OF TRACK ",0
t_nnew: dc.b    "NEW STRAIGHT",0
t_ebad: dc.b    "TRACK DATA IS DAMAGED (E-TERM)",0
t_help: dc.b    "TRACK VIEWER KEYS",0
        dc.b    " ",0
        dc.b    "LEFT / RIGHT   PREVIOUS / NEXT SEGMENT",0
        dc.b    "               (OBJECT IN THE OBJECT ROW)",0
        dc.b    "UP / DOWN, TAB ROAD <> OBJECTS",0
        dc.b    "SHIFT + L/R    1000 UNITS",0
        dc.b    "CONTROL + L/R  ONE PIXEL OF THE STRIPS",0
        dc.b    "FIRE + L/R     THE SAME ON THE JOYSTICK",0
        dc.b    "+ / -          ZOOM IN / OUT",0
        dc.b    "FIRE + U/D     THE SAME ON THE JOYSTICK",0
        dc.b    "CLR/HOME       TO THE START",0
        dc.b    "B              TO THE BAR (THE FINISH)",0
        dc.b    "FIRE           MENU",0
        dc.b    "ESC, F10       LEAVE THE TRACK",0
        dc.b    "HELP, F1       THIS PAGE",0
        dc.b    " ",0
        dc.b    "MAP: THE ROAD FROM ABOVE.  GREEN BOX =",0
        dc.b    "START, RED BOX = THE BAR, A DOT EVERY",0
        dc.b    "1000 UNITS.  YELLOW = THE SEGMENT.",0
        dc.b    "STRIPS: HILL, ROAD WIDTH (LEFT ABOVE",0
        dc.b    "THE MIDDLE), OBJECTS (LEFT SIDE ABOVE)",0
        dc.b    " ",0
        dc.b    "PRESS A KEY",0,0
        even
qsin:
        dc.w    0,50,101,151,201,251,302,352,402,452,503,553,603,653,704,754
        dc.w    804,854,905,955,1005,1055,1106,1156,1206,1256,1307,1357,1407,1457,1507,1558
        dc.w    1608,1658,1708,1758,1809,1859,1909,1959,2009,2059,2110,2160,2210,2260,2310,2360
        dc.w    2410,2461,2511,2561,2611,2661,2711,2761,2811,2861,2911,2962,3012,3062,3112,3162
        dc.w    3212,3262,3312,3362,3412,3462,3512,3562,3612,3662,3712,3761,3811,3861,3911,3961
        dc.w    4011,4061,4111,4161,4210,4260,4310,4360,4410,4460,4509,4559,4609,4659,4708,4758
        dc.w    4808,4858,4907,4957,5007,5056,5106,5156,5205,5255,5305,5354,5404,5453,5503,5552
        dc.w    5602,5651,5701,5750,5800,5849,5899,5948,5998,6047,6096,6146,6195,6245,6294,6343
        dc.w    6393,6442,6491,6540,6590,6639,6688,6737,6786,6836,6885,6934,6983,7032,7081,7130
        dc.w    7179,7228,7277,7326,7375,7424,7473,7522,7571,7620,7669,7718,7767,7815,7864,7913
        dc.w    7962,8010,8059,8108,8157,8205,8254,8303,8351,8400,8448,8497,8545,8594,8642,8691
        dc.w    8739,8788,8836,8885,8933,8981,9030,9078,9126,9175,9223,9271,9319,9367,9416,9464
        dc.w    9512,9560,9608,9656,9704,9752,9800,9848,9896,9944,9992,10039,10087,10135,10183,10231
        dc.w    10278,10326,10374,10421,10469,10517,10564,10612,10659,10707,10754,10802,10849,10897,10944,10992
        dc.w    11039,11086,11133,11181,11228,11275,11322,11370,11417,11464,11511,11558,11605,11652,11699,11746
        dc.w    11793,11840,11886,11933,11980,12027,12074,12120,12167,12214,12260,12307,12353,12400,12446,12493
        dc.w    12539,12586,12632,12679,12725,12771,12817,12864,12910,12956,13002,13048,13094,13141,13187,13233
        dc.w    13279,13324,13370,13416,13462,13508,13554,13599,13645,13691,13736,13782,13828,13873,13919,13964
        dc.w    14010,14055,14101,14146,14191,14236,14282,14327,14372,14417,14462,14507,14553,14598,14643,14688
        dc.w    14732,14777,14822,14867,14912,14956,15001,15046,15090,15135,15180,15224,15269,15313,15358,15402
        dc.w    15446,15491,15535,15579,15623,15667,15712,15756,15800,15844,15888,15932,15976,16019,16063,16107
        dc.w    16151,16195,16238,16282,16325,16369,16413,16456,16499,16543,16586,16630,16673,16716,16759,16802
        dc.w    16846,16889,16932,16975,17018,17061,17104,17146,17189,17232,17275,17317,17360,17403,17445,17488
        dc.w    17530,17573,17615,17657,17700,17742,17784,17827,17869,17911,17953,17995,18037,18079,18121,18163
        dc.w    18204,18246,18288,18330,18371,18413,18454,18496,18537,18579,18620,18661,18703,18744,18785,18826
        dc.w    18868,18909,18950,18991,19032,19072,19113,19154,19195,19236,19276,19317,19357,19398,19438,19479
        dc.w    19519,19560,19600,19640,19680,19721,19761,19801,19841,19881,19921,19961,20000,20040,20080,20120
        dc.w    20159,20199,20238,20278,20317,20357,20396,20436,20475,20514,20553,20592,20631,20670,20709,20748
        dc.w    20787,20826,20865,20904,20942,20981,21019,21058,21096,21135,21173,21212,21250,21288,21326,21364
        dc.w    21403,21441,21479,21516,21554,21592,21630,21668,21705,21743,21781,21818,21856,21893,21930,21968
        dc.w    22005,22042,22079,22116,22154,22191,22227,22264,22301,22338,22375,22411,22448,22485,22521,22558
        dc.w    22594,22631,22667,22703,22739,22776,22812,22848,22884,22920,22956,22991,23027,23063,23099,23134
        dc.w    23170,23205,23241,23276,23311,23347,23382,23417,23452,23487,23522,23557,23592,23627,23662,23697
        dc.w    23731,23766,23801,23835,23870,23904,23938,23973,24007,24041,24075,24109,24143,24177,24211,24245
        dc.w    24279,24312,24346,24380,24413,24447,24480,24514,24547,24580,24613,24647,24680,24713,24746,24779
        dc.w    24811,24844,24877,24910,24942,24975,25007,25040,25072,25105,25137,25169,25201,25233,25265,25297
        dc.w    25329,25361,25393,25425,25456,25488,25519,25551,25582,25614,25645,25676,25708,25739,25770,25801
        dc.w    25832,25863,25893,25924,25955,25986,26016,26047,26077,26108,26138,26168,26198,26229,26259,26289
        dc.w    26319,26349,26378,26408,26438,26468,26497,26527,26556,26586,26615,26644,26674,26703,26732,26761
        dc.w    26790,26819,26848,26876,26905,26934,26962,26991,27019,27048,27076,27104,27133,27161,27189,27217
        dc.w    27245,27273,27300,27328,27356,27384,27411,27439,27466,27493,27521,27548,27575,27602,27629,27656
        dc.w    27683,27710,27737,27764,27790,27817,27843,27870,27896,27923,27949,27975,28001,28027,28053,28079
        dc.w    28105,28131,28157,28182,28208,28234,28259,28284,28310,28335,28360,28385,28411,28436,28460,28485
        dc.w    28510,28535,28560,28584,28609,28633,28658,28682,28706,28730,28755,28779,28803,28827,28850,28874
        dc.w    28898,28922,28945,28969,28992,29016,29039,29062,29085,29108,29131,29154,29177,29200,29223,29246
        dc.w    29268,29291,29313,29336,29358,29380,29403,29425,29447,29469,29491,29513,29534,29556,29578,29599
        dc.w    29621,29642,29664,29685,29706,29728,29749,29770,29791,29812,29832,29853,29874,29894,29915,29936
        dc.w    29956,29976,29997,30017,30037,30057,30077,30097,30117,30136,30156,30176,30195,30215,30234,30253
        dc.w    30273,30292,30311,30330,30349,30368,30387,30406,30424,30443,30462,30480,30498,30517,30535,30553
        dc.w    30571,30589,30607,30625,30643,30661,30679,30696,30714,30731,30749,30766,30783,30800,30818,30835
        dc.w    30852,30868,30885,30902,30919,30935,30952,30968,30985,31001,31017,31033,31050,31066,31082,31097
        dc.w    31113,31129,31145,31160,31176,31191,31206,31222,31237,31252,31267,31282,31297,31312,31327,31341
        dc.w    31356,31371,31385,31400,31414,31428,31442,31456,31470,31484,31498,31512,31526,31539,31553,31567
        dc.w    31580,31593,31607,31620,31633,31646,31659,31672,31685,31698,31710,31723,31736,31748,31760,31773
        dc.w    31785,31797,31809,31821,31833,31845,31857,31869,31880,31892,31903,31915,31926,31937,31949,31960
        dc.w    31971,31982,31993,32004,32014,32025,32036,32046,32057,32067,32077,32087,32098,32108,32118,32128
        dc.w    32137,32147,32157,32166,32176,32185,32195,32204,32213,32223,32232,32241,32250,32258,32267,32276
        dc.w    32285,32293,32302,32310,32318,32327,32335,32343,32351,32359,32367,32375,32382,32390,32397,32405
        dc.w    32412,32420,32427,32434,32441,32448,32455,32462,32469,32476,32482,32489,32495,32502,32508,32514
        dc.w    32521,32527,32533,32539,32545,32550,32556,32562,32567,32573,32578,32584,32589,32594,32599,32604
        dc.w    32609,32614,32619,32624,32628,32633,32637,32642,32646,32650,32655,32659,32663,32667,32671,32674
        dc.w    32678,32682,32685,32689,32692,32696,32699,32702,32705,32708,32711,32714,32717,32720,32722,32725
        dc.w    32728,32730,32732,32735,32737,32739,32741,32743,32745,32747,32748,32750,32752,32753,32755,32756
        dc.w    32757,32758,32759,32760,32761,32762,32763,32764,32765,32765,32766,32766,32766,32767,32767,32767
        dc.w    32767
