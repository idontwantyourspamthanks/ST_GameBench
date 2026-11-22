; msedit.s - Moonshine Racers TRACK EDITOR overlay (FILES\MSEDIT.OVL).  Milestone 2: viewer + EDITING (in RAM; saving to disk is milestone 4).  Design: work/notes/editor_design.md.
; Not a patch: tools/msrpatch.py assembles this file at EDBASE ($130000, no `org` line here), fills in the header's length and CRC-32 and writes it to the HD build's FILES folder.
; cp_title.s (F10 menu, item TRACK EDITOR) reads it there on first use, checks magic / EDVER / length / CRC and calls EDBASE+16.  Machines: ST family with 2 MB or more (the `; gate: ram2mb` of cp_title).
; The tool predefines EDBASE, EDWORK ($140000), EDVER, CPV, CPSTORE.  Everything the editor owns lies above $100000; it calls the game's vertical sync ($d206), file service ($d6fa)
; and reads its font ($190be), key tables ($5ffe held, $607e latched, $60ff last make) and joystick byte ($6105).
;
; Work RAM (EDWORK = $140000):
V       equ     EDWORK          ; variables (4 KB, cleared at entry)
BLK     equ     EDWORK+$1000    ; raw track block read from the game's disk image (a stock track: at most 12 sectors)
TYPS    equ     EDWORK+$2800    ; the object type table (S5 + end word) of the track being edited: copied verbatim into the block when it is kept
SEGT    equ     EDWORK+$3000    ; segment list: 2048 x 12 B  start.w len.w curve.w hill.w wl.b wr.b pad.w
OBJT    equ     EDWORK+$9000    ; object list: 1000 x 8 B  at.w type.w lateral.w flags.w (bit 0 = the BAR)
HARR    equ     EDWORK+$10000   ; height byte per unit (32768)
WLARR   equ     EDWORK+$18000   ; left half-width per unit
WRARR   equ     EDWORK+$20000   ; right half-width per unit
PTS     equ     EDWORK+$28000   ; top-down path: x.w y.w (world units / 4, y down) every 8 units (4097 points)
SINT    equ     EDWORK+$2D000   ; sine table, 4096 steps per turn + a quarter (5120 words)
SCR     equ     EDWORK+$30000   ; screen 1 (32000 B)
ARENA   equ     EDWORK+$38000   ; undo history ($178000-$19FFFF); the campaign file is rebuilt here when a track is kept (history is dead by then)
ARENAE  equ     EDWORK+$60000
CKPT    equ     EDWORK+$60000   ; expand checkpoints: one 32 B state per segment (2048 x 32)
ENCBUF  equ     EDWORK+$70000   ; the encoded track block (64 KB)
SCR2    equ     EDWORK+$80000   ; screen 2: live-preview pages are drawn here and flipped in
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
vTyp    equ     172             ; l parse: start of the type table in the block
vTypLen equ     176             ; w bytes of TYPS (entries + end word)
vShow   equ     178             ; l the screen the shifter shows
vDraw   equ     182             ; l the screen the drawing routines write to
vMapW   equ     186             ; w map window width (304, or 208 while a list is open)
vMapCx  equ     188             ; w map window centre x
vMapLim equ     190             ; w map window right edge
vBW     equ     192             ; w bounding box of the path (>= 1024)
vBH     equ     194
vK      equ     196             ; w expand: segment counter
vDirty  equ     198             ; w first segment whose per-unit data is stale ($7fff = none)
vMod    equ     200             ; w the working copy differs from the loaded one
vHCur   equ     202             ; l undo history: the current entry
vHTop   equ     206             ; l end of the last entry
vHDrop  equ     210             ; w the oldest entry fell out of the ring
vLastAct equ    212             ; w repeat: act (0 = none)
vLastVal equ    214             ; w repeat: value
vLastType equ   216             ; w type the next added object gets (1-based, 0 = the first one that is not the BAR)
vLastSide equ   218             ; w lateral of the next added object
vLAct   equ     220             ; w pick list: act 1 curve 2 hill 3 length 4 width L 5 width R 6 type 7 side 8 raw accel
vLKind  equ     222             ; w 0 strings, 1 numbers, 2 object types
vLBias  equ     224             ; w kind 0: value = index + bias
vLCnt   equ     226             ; w items (the BACK item is index vLCnt)
vLAdj   equ     228             ; w left / right adjust the value
vLMin   equ     230             ; w
vLMax   equ     232             ; w
vLTab   equ     234             ; l texts / numbers
vLHead  equ     238             ; l heading text
vLHintP equ     242             ; l hint row text while the list is open
vLSel   equ     246             ; w selected item (-1 none)
vLTop   equ     248             ; w first visible item
vLVal   equ     250             ; w the value shown / applied
vLWide  equ     252             ; w 1 = full screen list (types)
vLOpen  equ     254             ; w a list is open
vLPend  equ     256             ; w the value changed, the preview is stale
vLBad   equ     258             ; w the value was refused
vLCol   equ     260             ; w box column
vLW     equ     262             ; w box width in characters
vLRow0  equ     264             ; w first item row
vLRows  equ     266             ; w visible rows
vMode   equ     268             ; w 1 = moving an object
vMoveOrg equ    270             ; w the object's position before the move
vLeaveW equ     272             ; w leaving was refused once
vEncLen equ     274             ; l length of the encoded block
vPlay   equ     278             ; w track + 1 to play (result of the editor)
vPcN    equ     280             ; w hill shape pieces
vPc     equ     282             ; 5 x (len.w, accel.w)
vChkN   equ     302             ; w check messages
vChkE   equ     304             ; w blocking errors
vChk    equ     306             ; 8 l message texts
vChkK   equ     338             ; 8 w message codes
vChkT   equ     354             ; 40 B text
vLTxt   equ     394             ; 48 B list item text
vLMsg   equ     442             ; l the last message shown on the hint row (read by the gate scripts)
vLBusy  equ     446             ; w a preview (apply, expand, draw) is running
vMItems equ     1200            ; 24 l list picker item texts
vLine   equ     1296            ; 64 B text line
vTxt    equ     1360            ; 20 x 40 B item texts
vKqH    equ     2200            ; w key queue: next code to pop
vKqT    equ     2202            ; w key queue: next free slot (the IKBD hook writes it)
vOldKb  equ     2204            ; l the game's IKBD handler ($118) while the editor's hook is in
vKq     equ     2208            ; 64 B ring of make codes
vPend   equ     2272            ; w an edit left per-unit data stale: recomputed when no key is waiting
vPD     equ     2274            ; w pending: first stale segment ($7fff = none)
vPM     equ     2276            ; w pending: what is stale (bit 0 heights, 1 widths, 2 path)
vXm     equ     2278            ; w what the edit being applied makes stale (bit 3: only that segment's own parameters changed)
vXNS    equ     2280            ; w segments at the last expand
vXEnd   equ     2282            ; l extent at the last expand
vXk     equ     2286            ; w expand_from: the mask in use
vLRd    equ     2288            ; w the list rows are stale (redrawn when no key is waiting)
vTd102c equ    2300            ; w test drive: the game's $102c before the race
vTd1021 equ    2302            ; b $1021 sound mode
vTd1020 equ    2303            ; b $1020 music enable
vTd1027 equ    2304            ; b $1027 lost races
vTdScrA equ    2306            ; l $1004
vTdScrB equ    2310            ; l $1008
vTdN    equ    2314            ; w the cursor unit the race starts at
vTdCnt  equ    2316            ; w VBL frames since the race was decided (tdvbl)
vTdOldV equ    2318            ; l the game's VBL handler ($70) while tdvbl is in
vTdOldK equ    2322            ; l the game's IKBD handler ($118) while tdkb is in
vTdHit  equ    2326            ; w number of td_ff runs (read by the gate scripts)
vTdRes  equ    2328            ; b $1024 when the race returned
vTdRes2 equ    2329            ; b $1226
vTdLast equ    2330            ; w $5ff8 when the race returned
vTdRem  equ     2332            ; w td_ff: units still to fast-forward
vTdKill equ     2335            ; b Esc / F10 was pressed in the race (tdkb)
vTdWhy  equ     2334            ; b how the race was decided (tdvbl): 1 the BAR was reached, 2 time-out, 0 neither (F10, Esc, crashes)

        dc.b    'MSED'          ; +0  magic
        dc.w    EDVER,0         ; +4  version (cp_title refuses another one), flags
        dc.l    0               ; +8  file length (msrpatch.py)
        dc.l    0               ; +12 CRC-32 of the bytes from +16 (msrpatch.py)
        bra.w   ed_main         ; +16 entry of the editor (cp_title: jsr EDBASE+16)
        bra.w   td_ff           ; +20 entry of the test drive's fast-forward (cp_td: jsr EDBASE+20, inside the game's race setup)

; ---------------------------------------------------------------- entry (called by cp_title; supervisor, the title's context).  Returns when the user leaves.
ed_main:
        movem.l d1-d7/a0-a6,-(a7)
        lea     V.l,a5
        movea.l a5,a0
        move.w  #$3ff,d0
.zv:    clr.l   (a0)+
        dbra    d0,.zv
        move.w  #304,vMapW(a5)
        move.w  #160,vMapCx(a5)
        move.w  #320,vMapLim(a5)
        bsr     sin_init
        bsr     crc_init
        bsr     take
.top:   bsr     top_list                ; d0 = -1 leave, 0 a track is loaded, n = play track n-1
        tst.w   d0
        bmi   .x
        beq   .view
        move.w  d0,vPlay(a5)
        bra   .x
.view:  bsr     view
        bra   .top
.x:     bsr     give
        clr.b   $60ff.w
        moveq   #0,d0
        move.w  vPlay(a5),d0
        movem.l (a7)+,d1-d7/a0-a6
        rts

; ---- the screen: own buffer and palette while the editor runs; the game's VBL ($d11e: music, mouse poll) and IKBD handler stay as they are (the title has no raster split)
take:   move.b  $ffff8201.w,vScr(a5)
        move.b  $ffff8203.w,vScr+1(a5)
        lea     $ffff8240.w,a0
        lea     vPal(a5),a1
        moveq   #15,d0
.s:     move.w  (a0)+,(a1)+
        dbra    d0,.s
        move.l  #SCR,vShow(a5)
        move.l  #SCR,vDraw(a5)
        bsr     cls
        jsr     $d206.l
        move.b  #SCR>>16,$ffff8201.w
        move.b  #(SCR>>8)&$ff,$ffff8203.w
        lea     pal(pc),a0
        lea     $ffff8240.w,a1
        moveq   #15,d0
.p:     move.w  (a0)+,(a1)+
        dbra    d0,.p
        move.w  sr,-(a7)                ; the key queue: our IKBD hook in front of the game's handler
        ori.w   #$700,sr
        clr.l   vKqH(a5)
        move.w  (a7)+,sr
        bsr     kb_hook
        rts

give:   jsr     $d206.l
        move.b  vScr(a5),$ffff8201.w
        move.b  vScr+1(a5),$ffff8203.w
        lea     vPal(a5),a0
        lea     $ffff8240.w,a1
        moveq   #15,d0
.p:     move.w  (a0)+,(a1)+
        dbra    d0,.p
        move.w  sr,-(a7)
        ori.w   #$700,sr
        move.l  vOldKb(a5),$118.w
        move.w  (a7)+,sr
        rts

; ---- key queue.  The game's IKBD handler ($cfb4) keeps one make code ($60ff) and a latch per cursor key: a second key pressed while the editor is busy (a redraw takes a few frames) would be lost.
; kbhook runs the game's handler, then moves the make code it left in $60ff into a 64-entry ring (modifier keys are skipped); the editor pops codes one per frame (kq_pop / kq_popn / kq_arrow).
kbhook: pea     .back(pc)
        move.w  sr,-(a7)
        move.l  V+vOldKb.l,-(a7)
        rts                             ; = jmp to the game's handler, whose rte returns to .back
.back:  movem.l d0-d2/a0-a1,-(a7)
        move.b  $60ff.w,d0
        beq   .x
        clr.b   $60ff.w
        cmpi.b  #$2a,d0
        beq   .x
        cmpi.b  #$36,d0
        beq   .x
        cmpi.b  #$1d,d0
        beq   .x
        cmpi.b  #$38,d0
        beq   .x
        lea     V.l,a0
        moveq   #0,d1
        move.w  vKqT(a0),d1
        move.w  d1,d2
        addq.w  #1,d2
        andi.w  #63,d2
        cmp.w   vKqH(a0),d2
        beq   .x                        ; full: dropped
        lea     vKq(a0),a1
        move.b  d0,(a1,d1.w)
        move.w  d2,vKqT(a0)
.x:     movem.l (a7)+,d0-d2/a0-a1
        rte
kb_hook:                                ; the hook is the IKBD vector (again: the game's file service may have put its own back)
        move.l  a0,-(a7)
        lea     kbhook(pc),a0
        cmpa.l  $118.w,a0
        beq   .x
        move.w  sr,-(a7)
        ori.w   #$700,sr
        move.l  $118.w,vOldKb(a5)
        move.l  a0,$118.w
        move.w  (a7)+,sr
.x:     movea.l (a7)+,a0
        rts
kq_empty:                               ; Z set = no key waiting (trashes d0)
        move.w  vKqH(a5),d0
        cmp.w   vKqT(a5),d0
        rts
kq_pop:                                 ; d0.w = the next key code, 0 = none
        movem.l d1/a0,-(a7)
        moveq   #0,d0
        move.w  vKqH(a5),d1
        cmp.w   vKqT(a5),d1
        beq   .x
        lea     vKq(a5),a0
        move.b  (a0,d1.w),d0
        addq.w  #1,d1
        andi.w  #63,d1
        move.w  d1,vKqH(a5)
.x:     movem.l (a7)+,d1/a0
        rts
kq_popn:                                ; as kq_pop, but a cursor key at the head stays in the queue (poll_dirs takes it)
        movem.l d1/a0,-(a7)
        moveq   #0,d0
        move.w  vKqH(a5),d1
        cmp.w   vKqT(a5),d1
        beq   .x
        lea     vKq(a5),a0
        move.b  (a0,d1.w),d0
        cmpi.b  #$48,d0
        beq   .s
        cmpi.b  #$50,d0
        beq   .s
        cmpi.b  #$4b,d0
        beq   .s
        cmpi.b  #$4d,d0
        bne   .p
.s:     moveq   #0,d0
        bra   .x
.p:     addq.w  #1,d1
        andi.w  #63,d1
        move.w  d1,vKqH(a5)
.x:     movem.l (a7)+,d1/a0
        rts
kq_arrow:                               ; d1.w = a cursor key at the head of the queue, popped, as the poll_dirs bit (1 up 2 down 4 left 8 right); 0 = none (nothing popped)
        movem.l d0/a0,-(a7)
        moveq   #0,d1
        move.w  vKqH(a5),d0
        cmp.w   vKqT(a5),d0
        beq   .x
        lea     vKq(a5),a0
        move.b  (a0,d0.w),d1
        cmpi.b  #$48,d1
        beq   .u
        cmpi.b  #$50,d1
        beq   .d
        cmpi.b  #$4b,d1
        beq   .l
        cmpi.b  #$4d,d1
        bne   .n
        moveq   #8,d1
        bra   .p
.u:     moveq   #1,d1
        bra   .p
.d:     moveq   #2,d1
        bra   .p
.l:     moveq   #4,d1
.p:     addq.w  #1,d0
        andi.w  #63,d0
        move.w  d0,vKqH(a5)
        bra   .x
.n:     moveq   #0,d1
.x:     movem.l (a7)+,d0/a0
        rts
; flush_pend: the per-unit data an edit left stale (refresh remembers it while keys are waiting) is recomputed, then the view
flush_pend:
        tst.w   vPend(a5)
        beq   .x
        clr.w   vPend(a5)
        move.w  vPD(a5),d0
        move.w  vPM(a5),d1
        move.w  #$7fff,vPD(a5)
        clr.w   vPM(a5)
        bsr     expand_from
        bsr     find_seg
        bsr     set_zoom
.x:     rts
; act_mask: d0.w = pick list act -> d1.w = what its value makes stale (see expand_from)
act_mask:
        moveq   #7,d1
        cmpi.w  #1,d0
        beq   .p
        cmpi.w  #4,d0
        beq   .w
        cmpi.w  #5,d0
        beq   .w
        cmpi.w  #8,d0
        bne   .r
        moveq   #1,d1
.r:     rts
.p:     moveq   #4,d1
        rts
.w:     moveq   #10,d1
        rts

cls:    movem.l d0-d7/a0,-(a7)
        movea.l vDraw(a5),a0
        lea     32000(a0),a0
        moveq   #0,d0
        moveq   #0,d1
        moveq   #0,d2
        moveq   #0,d3
        moveq   #0,d4
        moveq   #0,d5
        moveq   #0,d6
        moveq   #0,d7
.c:     movem.l d0-d7,-(a0)
        cmpa.l  vDraw(a5),a0
        bhi   .c
        movem.l (a7)+,d0-d7/a0
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
        movea.l vDraw(a5),a2
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
        movea.l vDraw(a5),a2
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
vline:  movem.l d0-d5/a1-a2,-(a7)
        move.w  d4,d5
        sub.w   d1,d5                   ; pixels - 1
        bpl   .p
        moveq   #0,d5                   ; a single pixel
.p:     mulu    #160,d1
        move.w  d0,d3
        lsr.w   #4,d3
        lsl.w   #3,d3
        add.w   d3,d1
        movea.l vDraw(a5),a2
        adda.w  d1,a2
        andi.w  #15,d0
        move.w  #$8000,d3
        lsr.w   d0,d3
        btst    #0,d2
        beq   .1
        movea.l a2,a1
        move.w  d5,d4
.l1:    or.w    d3,(a1)
        lea     160(a1),a1
        dbra    d4,.l1
.1:     btst    #1,d2
        beq   .2
        lea     2(a2),a1
        move.w  d5,d4
.l2:    or.w    d3,(a1)
        lea     160(a1),a1
        dbra    d4,.l2
.2:     btst    #2,d2
        beq   .3
        lea     4(a2),a1
        move.w  d5,d4
.l3:    or.w    d3,(a1)
        lea     160(a1),a1
        dbra    d4,.l3
.3:     btst    #3,d2
        beq   .4
        lea     6(a2),a1
        move.w  d5,d4
.l4:    or.w    d3,(a1)
        lea     160(a1),a1
        dbra    d4,.l4
.4:     movem.l (a7)+,d0-d5/a1-a2
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
        movea.l vDraw(a5),a0
        adda.w  #8*160+6,a0
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
        bsr     kb_hook
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
        move.l  a0,vTyp(a5)
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
        movea.l vTyp(a5),a1             ; keep the type table: it is copied into every block written
        lea     TYPS.l,a2
        move.w  d7,d0
        mulu    #12,d0
        move.w  d0,d1
        lsr.w   #1,d0
        beq   .tz
        subq.w  #1,d0
.tc:    move.w  (a1)+,(a2)+
        dbra    d0,.tc
.tz:    clr.w   (a2)
        addq.w  #2,d1
        move.w  d1,vTypLen(a5)
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

; expand: the per-unit arrays as the game's own setup computes them ($ff3a curve ring, $fde0 widths, $ffe4 hill) and the top-down path (heading = curve value / 600 rad, as tools/msrtrack.py render).
; expand_from(d0 = first segment): incremental.  Every segment's start state (c, 8-unit sum, slope, height, two widths, path accumulators) is kept in CKPT; units before the segment are not touched.
expand: moveq   #0,d0
        moveq   #7,d1
; expand_from: d0.w = first stale segment, d1.w = what is stale: bit 0 heights, 1 widths, 2 path (3 = only that segment's own parameters changed: the width pass may stop where its state meets the old one).
; Three passes (xp_hill, xp_width, xp_path) resume from the checkpoints of segment d0; a pass that is not stale is not run.  A changed segment count or extent makes everything stale.
expand_from:
        movem.l d0-d7/a0-a6,-(a7)
        move.w  d0,vK(a5)
        move.w  d1,vXk(a5)
        bsr     calc_end
        move.w  vNSeg(a5),d0
        cmp.w   vXNS(a5),d0
        beq   .e1
        move.w  d0,vXNS(a5)
        move.w  #7,vXk(a5)
.e1:    move.l  vEnd(a5),d0
        cmp.l   vXEnd(a5),d0
        beq   .e2
        move.l  d0,vXEnd(a5)
        move.w  #7,vXk(a5)
.e2:    move.w  vK(a5),d0
        cmp.w   vNSeg(a5),d0
        bcc   .e3
        moveq   #0,d6
        move.w  d0,d6
        mulu    #SEGSZ,d6
        lea     SEGT.l,a4
        adda.l  d6,a4
        move.w  (a4),d6                 ; start of the segment
        cmp.w   vEnd+2(a5),d6
        bcs   .e4
.e3:    ori.w   #4,vXk(a5)              ; beyond the extent: nothing is shown there, the map is fitted again
        bra   .x
.e4:    move.w  vXk(a5),d0
        btst    #0,d0
        beq   .e5
        bsr     xp_hill
.e5:    move.w  vXk(a5),d0
        btst    #1,d0
        beq   .e6
        bsr     xp_width
.e6:    move.w  vXk(a5),d0
        btst    #2,d0
        beq   .xx
        bsr     xp_path
.x:     ; bounding box of the path -> scale and centre of the map
        move.l  vEnd(a5),d0
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
.w2:    move.w  d2,vBW(a5)
        move.w  d4,vBH(a5)
        bsr     map_fit
.xx:    movem.l (a7)+,d0-d7/a0-a6
        rts

; xp_hill: heights from segment vK on: 16.16 integrator, slope += accel per unit, the byte = the integer part clamped to 0..127 (the game's ring filler $ffe4)
xp_hill:
        moveq   #0,d6
        move.w  vK(a5),d6
        move.l  d6,d7
        mulu    #SEGSZ,d6
        lea     SEGT.l,a4
        adda.l  d6,a4
        lsl.l   #5,d7
        lea     CKPT.l,a6
        adda.l  d7,a6
        moveq   #0,d6
        move.w  (a4),d6
        lea     HARR.l,a0
        adda.l  d6,a0
        moveq   #0,d2
        moveq   #0,d3
        tst.w   vK(a5)
        beq   .h
        move.l  8(a6),d2
        move.l  12(a6),d3
.h:     move.w  vNSeg(a5),d5
        sub.w   vK(a5),d5
.seg:   move.l  d2,8(a6)
        move.l  d3,12(a6)
        move.w  6(a4),d4
        ext.l   d4
        moveq   #0,d6
        move.w  2(a4),d6
        subq.w  #1,d6
.u:     add.l   d2,d3
        add.l   d4,d2
        move.l  d3,d7
        bpl   .p
        moveq   #0,d7
        bra   .s
.p:     swap    d7
        cmpi.w  #127,d7
        bls   .s
        moveq   #127,d7
.s:     move.b  d7,(a0)+
        dbra    d6,.u
        lea     SEGSZ(a4),a4
        lea     32(a6),a6
        subq.w  #1,d5
        beq   .x
        move.w  (a4),d6
        cmp.w   vEnd+2(a5),d6
        bcs   .seg
.x:     rts

; xp_width: left / right half-widths from segment vK on (1 per unit towards the segment's target: a ramp, then a run of the target).  With bit 3 of vXk the pass stops where its state equals the old checkpoint.
xp_width:
        moveq   #0,d6
        move.w  vK(a5),d6
        move.l  d6,d7
        mulu    #SEGSZ,d6
        lea     SEGT.l,a4
        adda.l  d6,a4
        lsl.l   #5,d7
        lea     CKPT.l,a6
        adda.l  d7,a6
        moveq   #0,d6
        move.w  (a4),d6
        lea     WLARR.l,a1
        adda.l  d6,a1
        lea     WRARR.l,a2
        adda.l  d6,a2
        moveq   #0,d4
        moveq   #0,d5
        tst.w   vK(a5)
        bne   .r
        move.b  8(a4),d4                ; the widths start at the first targets
        move.b  9(a4),d5
        bra   .h
.r:     move.l  16(a6),d4
        move.l  20(a6),d5
.h:     move.w  vNSeg(a5),d0
        sub.w   vK(a5),d0
        move.w  d0,vTmp(a5)
        moveq   #0,d0                   ; 0 = the first segment (no early stop there)
.seg:   tst.w   d0
        beq   .nc
        btst    #3,vXk+1(a5)
        beq   .nc
        cmp.l   16(a6),d4
        bne   .nc
        cmp.l   20(a6),d5
        beq   .x
.nc:    moveq   #1,d0
        move.l  d4,16(a6)
        move.l  d5,20(a6)
        move.w  2(a4),d2                ; units
        move.l  d4,d1
        movea.l a1,a0
        moveq   #0,d3
        move.b  8(a4),d3
        move.w  d2,d6
        bsr     wfill
        move.l  d1,d4
        movea.l a0,a1
        move.l  d5,d1
        movea.l a2,a0
        moveq   #0,d3
        move.b  9(a4),d3
        move.w  d2,d6
        bsr     wfill
        move.l  d1,d5
        movea.l a0,a2
        subq.w  #1,vTmp(a5)
        beq   .x
        lea     SEGSZ(a4),a4
        lea     32(a6),a6
        move.w  (a4),d6
        cmp.w   vEnd+2(a5),d6
        bcs   .seg
.x:     rts
; wfill: d1 = current width (byte), d3 = target, d6 = units (1..32768), a0 = array -> d1, a0 advanced.  Writes the current value, then steps one towards the target (as the game's ring filler); the run of the target goes by longs
wfill:  cmp.b   d3,d1
        beq   .f
        bhi   .dn
        move.w  d3,d7
        sub.w   d1,d7
        cmp.w   d6,d7
        bls   .u1
        move.w  d6,d7
.u1:    sub.w   d7,d6
        subq.w  #1,d7
.ul:    move.b  d1,(a0)+
        addq.b  #1,d1
        dbra    d7,.ul
        bra   .f
.dn:    move.w  d1,d7
        sub.w   d3,d7
        cmp.w   d6,d7
        bls   .d1
        move.w  d6,d7
.d1:    sub.w   d7,d6
        subq.w  #1,d7
.dl:    move.b  d1,(a0)+
        subq.b  #1,d1
        dbra    d7,.dl
.f:     tst.w   d6
        beq   .r
        moveq   #0,d3
        move.b  d1,d3
        move.w  d3,d7
        lsl.w   #8,d7
        or.w    d7,d3
        move.w  d3,d7
        swap    d3
        move.w  d7,d3                   ; the byte in all four lanes
        move.w  a0,d7
        btst    #0,d7
        beq   .al
        move.b  d1,(a0)+
        subq.w  #1,d6
        beq   .r
.al:    move.w  d6,d7
        lsr.w   #2,d7
        beq   .tl
        subq.w  #1,d7
.l4:    move.l  d3,(a0)+
        dbra    d7,.l4
.tl:    andi.w  #3,d6
        beq   .r
        subq.w  #1,d6
.l1:    move.b  d1,(a0)+
        dbra    d6,.l1
.r:     rts

; xp_path: the top-down path from segment vK on.  c = the heading (curve value), c += the segment's delta per unit; every 8 units one point from the mean c (xp_emit).  A block of 8 units inside a segment is one closed-form step
; (sum of c = 8 c0 + 36 delta, c = c0 + 8 delta) while c stays inside 16 bits; head, tail and the wrap case go unit by unit (xp_pu).
xp_path:
        moveq   #0,d6
        move.w  vK(a5),d6
        move.l  d6,d7
        mulu    #SEGSZ,d6
        lea     SEGT.l,a4
        adda.l  d6,a4
        lsl.l   #5,d7
        lea     CKPT.l,a2
        adda.l  d7,a2
        moveq   #0,d6
        move.w  (a4),d6
        lsr.l   #3,d6
        lsl.l   #2,d6
        lea     PTS+4.l,a3
        adda.l  d6,a3                   ; the next point to store
        tst.w   vK(a5)
        bne   .r
        clr.l   PTS.l
        suba.l  a0,a0                   ; a0 = x accumulator (world * 2^15), a1 = y accumulator, a6 = the sine table
        suba.l  a1,a1
        moveq   #0,d0
        moveq   #0,d1
        bra   .h
.r:     movem.l (a2),d0-d1
        movea.l 24(a2),a0
        movea.l 28(a2),a1
.h:     lea     SINT.l,a6
        move.w  vNSeg(a5),d2
        sub.w   vK(a5),d2
        move.w  d2,vTmp(a5)
.seg:   movem.l d0-d1,(a2)
        move.l  a0,24(a2)
        move.l  a1,28(a2)
        move.w  4(a4),d4
        ext.l   d4                      ; delta
        moveq   #0,d3
        move.w  2(a4),d3                ; units left
        moveq   #0,d2
        move.w  (a4),d2
        andi.w  #7,d2                   ; place of the first unit in its block of 8
.l:     tst.l   d3
        beq   .sd
        tst.w   d2
        bne   .one
        cmpi.l  #8,d3
        bcs   .one
        move.l  d3,d5
        lsr.l   #3,d5                   ; full blocks of 8 from here to the end of the segment
        move.l  d4,d7
        asl.l   #3,d7                   ; 8 delta
        muls    d5,d7
        move.w  d0,d6
        ext.l   d6                      ; c0
        add.l   d6,d7                   ; c after the run: no 16-bit wrap in the run (+-32000: the mean stays in a word)
        cmpi.l  #32000,d7
        bgt   .one
        cmpi.l  #-32000,d7
        blt   .one
        cmpi.l  #32000,d6
        bgt   .one
        cmpi.l  #-32000,d6
        blt   .one
        move.l  d4,d7
        asl.l   #3,d7
        add.l   d4,d7
        asr.l   #1,d7                   ; floor(4.5 delta): the mean of a block is c + that (sum 8 c + 36 delta, / 8)
        add.l   d7,d6
        muls    #17801,d6               ; mean * 17801 for the first block; every next block adds 8 delta * 17801
        move.w  d5,d1
        subq.w  #1,d1
        move.l  d4,d5
        asl.l   #3,d5
        muls    #17801,d5
.blk:   move.l  d6,d7
        asl.l   #2,d7
        swap    d7                      ; = (product >> 14) in the low word: the heading in 1/4096 turns
        andi.w  #$fff,d7
        add.w   d7,d7
        move.w  (a6,d7.w),d2            ; sine
        ext.l   d2
        asl.l   #3,d2
        adda.l  d2,a0
        addi.w  #2048,d7
        move.w  (a6,d7.w),d2            ; cosine
        ext.l   d2
        asl.l   #3,d2
        suba.l  d2,a1                   ; heading 0 = up the screen
        move.l  a0,d2
        swap    d2
        asr.w   #1,d2
        move.w  d2,(a3)+
        move.l  a1,d2
        swap    d2
        asr.w   #1,d2
        move.w  d2,(a3)+
        add.l   d5,d6
        dbra    d1,.blk
        move.l  d3,d1
        lsr.l   #3,d1
        move.l  d4,d7
        asl.l   #3,d7
        muls    d1,d7
        add.w   d7,d0                   ; c after the run
        andi.l  #7,d3                   ; the units left (less than a block)
        moveq   #0,d2
        moveq   #0,d1
        bra   .l
.one:   bsr     xp_pu
        subq.l  #1,d3
        bra   .l
.sd:    subq.w  #1,vTmp(a5)
        beq   .x
        lea     SEGSZ(a4),a4
        lea     32(a2),a2
        move.w  (a4),d6
        cmp.w   vEnd+2(a5),d6
        bcs   .seg
.x:     rts
xp_pu:  add.w   d4,d0
        move.w  d0,d7
        ext.l   d7
        add.l   d7,d1
        addq.w  #1,d2
        cmpi.w  #8,d2
        bne   .r
        moveq   #0,d2
        bra     xp_emit
.r:     rts
; xp_emit: d1 = sum of c over 8 units -> the next path point (a3); d1 = 0.  Mean c * 4096 / (2 pi 600) = the heading in 1/4096 turns
xp_emit:
        asr.l   #3,d1
        muls    #17801,d1               ; * 4096 / (2 pi 600) = 1.08649 (17801 / 16384)
        asl.l   #2,d1
        swap    d1                      ; = (product >> 14) in the low word
        andi.w  #$fff,d1
        add.w   d1,d1
        move.w  (a6,d1.w),d7            ; sine
        ext.l   d7
        asl.l   #3,d7
        adda.l  d7,a0
        addi.w  #2048,d1
        move.w  (a6,d1.w),d7            ; cosine (the table is a quarter turn longer)
        ext.l   d7
        asl.l   #3,d7
        suba.l  d7,a1                   ; heading 0 = up the screen
        move.l  a0,d7
        swap    d7
        asr.w   #1,d7
        move.w  d7,(a3)+
        move.l  a1,d7
        swap    d7
        asr.w   #1,d7
        move.w  d7,(a3)+
        moveq   #0,d1
        rts

; map_fit: scale of the map so that the whole path fits the window (vMapW x 96 pixels)
map_fit:
        movem.l d0-d2,-(a7)
        moveq   #0,d0
        move.w  vMapW(a5),d0
        swap    d0
        divu    vBW(a5),d0
        move.l  #96<<16,d1
        divu    vBH(a5),d1
        cmp.w   d0,d1
        bcc   .w3
        move.w  d1,d0
.w3:    move.w  d0,vS(a5)
        movem.l (a7)+,d0-d2
        rts

; calc_end: the extent shown = max(race length, BAR) + 1024, at most the stream length
calc_end:
        movem.l d0-d1/a0,-(a7)
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
.e1:    cmp.l   vTotal(a5),d0
        bls   .e2
        move.l  vTotal(a5),d0
.e2:    andi.w  #$fff8,d0
        move.l  d0,vEnd(a5)
        movem.l (a7)+,d0-d1/a0
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
        move.w  vMapCx(a5),d1
        ext.l   d1
        add.l   d1,d0
        move.w  vMapLim(a5),d1
        ext.l   d1
        cmp.l   d1,d0
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

; path: units d6 .. d7 of the path in colour d2; vThick = 2x2 pixels (the highlight).  A long range at a small map scale (the points lie a fraction of a pixel apart) takes every 2nd or 4th point; a point on the pixel
; of the previous one is not drawn again.
path:   movem.l d0-d7/a0-a1,-(a7)
        lsr.l   #3,d6
        lsr.l   #3,d7
        sub.w   d6,d7
        bcs   .x
        lea     PTS.l,a0
        lsl.w   #2,d6
        adda.w  d6,a0
        clr.w   vPOk(a5)
        movea.w #4,a1                   ; bytes from point to point
        cmpi.w  #64,d7
        bls   .l
        moveq   #0,d3
        move.w  vS(a5),d3
        lsl.l   #5,d3
        move.w  vSh(a5),d4
        lsr.l   d4,d3                   ; 16 x pixels per point
        cmpi.w  #4,d3
        bcc   .s2
        lsr.w   #2,d7
        movea.w #16,a1
        bra   .l
.s2:    cmpi.w  #8,d3
        bcc   .l
        lsr.w   #1,d7
        movea.w #8,a1
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
.pl:    tst.w   vPOk(a5)
        beq   .p1
        cmp.w   vPX(a5),d0
        bne   .p1
        cmp.w   vPY(a5),d1
        beq   .nx
.p1:    bsr     plot
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
.nx:    adda.w  a1,a0
        dbra    d7,.l
.x:     movem.l (a7)+,d0-d7/a0-a1
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
        tst.w   vMod(a5)
        beq   .h4
        move.b  #'*',(a1)+
.h4:
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
        tst.w   vLOpen(a5)
        beq   .hl1
        movea.l vLHintP(a5),a0
.hl1:   tst.w   vLeaveW(a5)
        beq   .hl2
        lea     t_hdisc(pc),a0
.hl2:   tst.w   vMode(a5)
        beq   .hl3
        lea     t_hmove(pc),a0
.hl3:
        move.l  vMsg(a5),d0
        beq   .hm
        movea.l d0,a0
        move.l  d0,vLMsg(a5)
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
        clr.w   vMod(a5)
        clr.w   vMode(a5)
        clr.w   vLeaveW(a5)
        clr.w   vLastAct(a5)
        clr.w   vLastType(a5)
        clr.w   vLastSide(a5)
        clr.w   vLOpen(a5)
        move.w  #$7fff,vDirty(a5)
        move.w  #$7fff,vPD(a5)
        clr.w   vPM(a5)
        clr.w   vPend(a5)
        move.w  #7,vXm(a5)
        bsr     set_zoom
        bsr     in_reset
        bsr     hist_init
.loop:  bsr     kq_empty
        bne   .in                       ; a key is waiting: nothing is recomputed or drawn before it is handled
        bsr     flush_pend              ; per-unit data the edits made stale (with a pending edit this sets the redraw)
        move.w  vRedraw(a5),d0
        beq   .in
        clr.w   vRedraw(a5)
        btst    #0,d0
        beq   .hi
        bsr     full_draw
        bra   .in
.hi:    bsr     draw_hi
.in:    jsr     $d206.l
        bsr     input
        tst.w   vRes(a5)
        beq   .loop
        clr.w   vState(a5)
        rts

; full_draw: the whole picture (map, strips, highlight, a list box when one is open) is drawn on the hidden screen and flipped in at the next vertical sync: no flicker
full_draw:
        bsr     hide
        bsr     draw_all
        bsr     draw_hi
        tst.w   vLOpen(a5)
        beq   .s
        bsr     lbox
.s:     bra     show
hide:   move.l  #SCR,d0                 ; vDraw = the screen that is not shown
        cmp.l   vShow(a5),d0
        bne   .a
        move.l  #SCR2,d0
.a:     move.l  d0,vDraw(a5)
        rts
show:   move.l  vDraw(a5),-(a7)         ; wait for the sync, point the shifter at vDraw; drawing continues on the screen that is shown
        jsr     $d206.l
        move.l  (a7)+,d0
        move.l  d0,vShow(a5)
        lsr.l   #8,d0
        move.b  d0,$ffff8203.w
        lsr.w   #8,d0
        move.b  d0,$ffff8201.w
        rts

in_reset:                               ; forget every key and wait until fire is released
        clr.b   $60ff.w
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
input:  bsr     kq_popn
        tst.b   d0
        beq   .dirs
        lea     keytab(pc),a0
.kt:    move.b  (a0)+,d1
        beq   .dirs
        move.b  (a0)+,d2
        cmp.b   d0,d1
        bne   .kt
        moveq   #0,d0
        move.b  d2,d0
        tst.b   $5ffe+$2a.w
        bne   .sh
        tst.b   $5ffe+$36.w
        beq     command
.sh:    cmpi.w  #3,d0                   ; Shift + B = put the BAR here, Shift + U = redo
        bne   .s2
        moveq   #19,d0
        bra     command
.s2:    cmpi.w  #20,d0
        bne     command
        moveq   #21,d0
        bra     command
.dirs:  bsr     poll_dirs
        tst.w   d2
        beq   .fire
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
step:   tst.w   vMode(a5)
        bne     obj_mv_step
        move.l  vPos(a5),d1
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
        tst.w   vMode(a5)
        bne     mv_cmd
        cmpi.w  #10,d0
        bcc     cmd_edit
        subq.w  #1,d0
        bne   .c2
        bra     leave
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
.c9:    bra     rep_cmd
.back:  bsr     in_reset
        move.w  #1,vRedraw(a5)
.r:     rts

; vmenu: the menu (FIRE): the road row's or the objects row's edit items, then the common ones -> d0 = command or 0
vmenu:  move.w  #2,vState(a5)
        lea     m_road(pc),a0
        lea     vmroad(pc),a2
        tst.w   vFocus(a5)
        beq   .r
        lea     m_obj(pc),a0
        lea     vmobj(pc),a2
.r:     bsr     list_fixed
        lea     t_vmenu(pc),a0
        moveq   #0,d0
        bsr     pick
        move.w  #1,vState(a5)
        tst.w   d0
        bmi   .n
        move.b  (a2,d0.w),d0
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
        bsr     kq_pop
        tst.b   d0
        bne   .d
        btst    #7,$6105.w
        beq   .w
.d:     move.w  #1,vState(a5)
        rts

; ======================================================================================================= milestone 2: EDITING
; ---- CRC-32 (reflected, $edb88320); the table lives at CPTAB, rebuilt here so the editor does not depend on anything but the address
crc_init:
        lea     CPTAB.l,a0
        moveq   #0,d3
.i:     move.l  d3,d0
        moveq   #7,d2
.b:     lsr.l   #1,d0
        bcc   .n
        eori.l  #$edb88320,d0
.n:     dbra    d2,.b
        move.l  d0,(a0)+
        addq.w  #1,d3
        cmpi.w  #256,d3
        bne   .i
        rts
; crc: d0 = state (start -1), a1 = data (advanced), d1.l = length 1..65536 -> d0 = state (invert at the end)
crc:    movem.l d1-d2/a6,-(a7)
        lea     CPTAB.l,a6
        subq.w  #1,d1
.l:     moveq   #0,d2
        move.b  (a1)+,d2
        eor.b   d0,d2
        lsr.l   #8,d0
        lsl.w   #2,d2
        move.l  (a6,d2.w),d2
        eor.l   d2,d0
        dbra    d1,.l
        movem.l (a7)+,d1-d2/a6
        rts
; cpyw: copy d0.l bytes (even) from a1 to a0 (upwards; no overlap trouble when a0 < a1)
cpyw:   movem.l d0-d1/a0-a1,-(a7)
        move.l  d0,d1
        lsr.l   #2,d1
        beq   .w
        subq.w  #1,d1
.l:     move.l  (a1)+,(a0)+
        dbra    d1,.l
.w:     btst    #1,d0
        beq   .x
        move.w  (a1)+,(a0)+
.x:     movem.l (a7)+,d0-d1/a0-a1
        rts
; apdn: d0.w signed -> decimal text at a1 (a1 advanced), no padding
apdn:   movem.l d0-d3/a0,-(a7)
        tst.w   d0
        bpl   .p
        move.b  #'-',(a1)+
        neg.w   d0
.p:     andi.l  #$ffff,d0
        moveq   #0,d2
.d:     divu    #10,d0
        swap    d0
        move.w  d0,-(a7)
        clr.w   d0
        swap    d0
        addq.w  #1,d2
        tst.l   d0
        bne   .d
.o:     move.w  (a7)+,d0
        addi.b  #'0',d0
        move.b  d0,(a1)+
        subq.w  #1,d2
        bne   .o
        movem.l (a7)+,d0-d3/a0
        rts
msg:    move.l  a0,vMsg(a5)             ; a0 = text for the hint row (shown once)
        ori.w   #2,vRedraw(a5)
        rts

; poll_dirs: the directions that are new this poll (joystick port 1, or a cursor key tapped: the key queue holds every tap, however short and however busy the editor was), auto-repeat while held.
; -> d2 = bits 0 up 1 down 2 left 3 right (0 = none), d3 = joystick byte (fire = bit 7), a0 = $5ffe (the held-key table)
poll_dirs:
        move.l  d4,-(a7)
        bsr     pd_poll
        move.l  (a7)+,d4
        rts
pd_poll:
        moveq   #0,d0
        move.b  $6105.w,d0
        move.w  d0,d3
        andi.w  #$f,d0
        move.w  d0,d4                   ; the joystick's directions
        lea     $5ffe.w,a0              ; keys held (for the auto-repeat)
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
.a4:    bsr     kq_arrow                ; d1 = a cursor key tapped
        move.w  vPDir(a5),d2
        move.w  d4,vPDir(a5)
        not.w   d2
        and.w   d4,d2
        or.w    d1,d2                   ; new this poll
        bne   .new
        tst.w   d0
        beq   .none
        subq.w  #1,vRep(a5)
        bne   .none
        move.w  #3,vRep(a5)
        move.w  d0,d2
        rts
.new:   move.w  #14,vRep(a5)
        rts
.none:  moveq   #0,d2
        rts

; ---------------------------------------------------------------- list elements (segments 12 B = 3 longs, objects 8 B = 2 longs)
; lst_open: a2 = list, d0.w = index, d1.w = elements now in the list, d2.w = element size in longs: a free slot at the index
lst_open:
        movem.l d1-d4/a0-a3,-(a7)
        move.w  d2,d4
        add.w   d4,d4
        add.w   d4,d4                   ; bytes per element
        move.w  d1,d3
        mulu    d4,d3
        lea     (a2,d3.l),a1            ; end of the list
        move.w  d1,d3
        sub.w   d0,d3
        mulu    d2,d3                   ; longs to move up
        beq   .n
        subq.w  #1,d3
        lea     (a1,d4.w),a3
.l:     move.l  -(a1),-(a3)
        dbra    d3,.l
.n:     movem.l (a7)+,d1-d4/a0-a3
        rts
; lst_close: the same arguments: removes the element at the index
lst_close:
        movem.l d1-d4/a0-a3,-(a7)
        move.w  d2,d4
        add.w   d4,d4
        add.w   d4,d4
        move.w  d0,d3
        mulu    d4,d3
        lea     (a2,d3.l),a1            ; destination
        lea     (a1,d4.w),a3            ; source = the next element
        move.w  d1,d3
        sub.w   d0,d3
        subq.w  #1,d3                   ; elements behind it
        mulu    d2,d3
        beq   .n
        subq.w  #1,d3
.l:     move.l  (a3)+,(a1)+
        dbra    d3,.l
.n:     movem.l (a7)+,d1-d4/a0-a3
        rts
seg_open:                               ; d0.w = index -> a0 = the free slot (nseg + 1)
        movem.l d1-d2/a2,-(a7)
        lea     SEGT.l,a2
        move.w  vNSeg(a5),d1
        moveq   #3,d2
        bsr     lst_open
        addq.w  #1,vNSeg(a5)
        moveq   #0,d1
        move.w  d0,d1
        mulu    #SEGSZ,d1
        lea     SEGT.l,a0
        adda.l  d1,a0
        movem.l (a7)+,d1-d2/a2
        rts
seg_shut:                               ; d0.w = index: remove the segment
        movem.l d1-d2/a2,-(a7)
        lea     SEGT.l,a2
        move.w  vNSeg(a5),d1
        moveq   #3,d2
        bsr     lst_close
        subq.w  #1,vNSeg(a5)
        movem.l (a7)+,d1-d2/a2
        rts
obj_open:                               ; d0.w = index -> a0 = the free slot
        movem.l d1-d2/a2,-(a7)
        lea     OBJT.l,a2
        move.w  vNObj(a5),d1
        moveq   #2,d2
        bsr     lst_open
        addq.w  #1,vNObj(a5)
        moveq   #0,d1
        move.w  d0,d1
        lsl.l   #3,d1
        lea     OBJT.l,a0
        adda.l  d1,a0
        movem.l (a7)+,d1-d2/a2
        rts
obj_shut:
        movem.l d1-d2/a2,-(a7)
        lea     OBJT.l,a2
        move.w  vNObj(a5),d1
        moveq   #2,d2
        bsr     lst_close
        subq.w  #1,vNObj(a5)
        movem.l (a7)+,d1-d2/a2
        rts
obj_ptr:                                ; a0 = the object under the cursor (vObj)
        moveq   #0,d0
        move.w  vObj(a5),d0
        lsl.l   #3,d0
        lea     OBJT.l,a0
        adda.l  d0,a0
        rts
seg_of:                                 ; d0.w = unit -> d0.w = the segment that holds it
        movem.l d1-d2/a0,-(a7)
        lea     SEGT.l,a0
        moveq   #0,d1
        move.w  vNSeg(a5),d2
        subq.w  #1,d2
.l:     cmp.w   d2,d1
        bcc   .f
        cmp.w   SEGSZ(a0),d0
        bcs   .f
        lea     SEGSZ(a0),a0
        addq.w  #1,d1
        bra   .l
.f:     move.w  d1,d0
        movem.l (a7)+,d1-d2/a0
        rts
dirty_end:                              ; the extent may change: recompute from the segment that holds its end
        move.l  vEnd(a5),d0
        subq.l  #1,d0
        bsr     seg_of
        move.w  d0,vDirty(a5)
        rts

; obj_norm: objects strictly increasing (a later one that would meet its predecessor moves one unit on), the first at 1 or later -> d0 = 1 when the last lies past 32767
obj_norm:
        movem.l d1-d2/a0,-(a7)
        lea     OBJT.l,a0
        move.w  vNObj(a5),d1
        beq   .c
        tst.w   (a0)
        bne   .n0
        move.w  #1,(a0)
.n0:    subq.w  #2,d1
        bmi   .c
        move.w  (a0),d2
.l:     addq.l  #8,a0
        cmp.w   (a0),d2
        bcs   .k
        move.w  d2,(a0)
        addq.w  #1,(a0)
.k:     move.w  (a0),d2
        dbra    d1,.l
.c:     moveq   #0,d0
        move.w  vNObj(a5),d1
        beq   .x
        subq.w  #1,d1
        lsl.w   #3,d1
        lea     OBJT.l,a0
        cmpi.w  #32767,(a0,d1.w)
        bls   .x
        moveq   #1,d0
.x:     movem.l (a7)+,d1-d2/a0
        rts

; road_shift: the road from unit P on moves by delta (the last segment, the padding behind the finish, absorbs it).  d2.l = P, d3.l = delta, d4.w = the first segment that moves
; (segment d4 on: start += delta; objects at or behind P move with the road; objects in the removed stretch go to its end).  -> d0 = 0 / 1 no room / 2 objects past the end
road_shift:
        movem.l d1-d7/a0-a2,-(a7)
        move.w  vNSeg(a5),d5
        subq.w  #1,d5
        mulu    #SEGSZ,d5
        lea     SEGT.l,a2
        adda.l  d5,a2                   ; the last segment
        moveq   #0,d1
        move.w  2(a2),d1
        sub.l   d3,d1                   ; its new length
        cmpi.l  #16,d1
        bge   .room
        moveq   #1,d0
        bra   .x
.room:  move.w  vNSeg(a5),d5
        sub.w   d4,d5
        beq   .nm
        subq.w  #1,d5
        andi.l  #$ffff,d4
        mulu    #SEGSZ,d4
        lea     SEGT.l,a0
        adda.l  d4,a0
.s:     add.w   d3,(a0)
        lea     SEGSZ(a0),a0
        dbra    d5,.s
.nm:    move.w  d1,2(a2)
        lea     OBJT.l,a0
        move.w  vNObj(a5),d5
        beq   .od
        subq.w  #1,d5
        move.l  d2,d6
        add.l   d3,d6                   ; P + delta
.o:     moveq   #0,d7
        move.w  (a0),d7
        cmp.l   d2,d7
        bcs   .lt
        add.l   d3,d7
        bra   .st
.lt:    tst.l   d3
        bpl   .nx
        cmp.l   d6,d7
        bcs   .nx
        move.l  d6,d7
.st:    move.w  d7,(a0)
.nx:    addq.l  #8,a0
        dbra    d5,.o
.od:    bsr     obj_norm
        tst.w   d0
        beq   .x
        moveq   #2,d0
.x:     movem.l (a7)+,d1-d7/a0-a2
        rts

; ---------------------------------------------------------------- undo history: entry = size.l nseg.w nobj.w seg.w obj.w pos.l pad.l, segments, objects, size.l (so the previous entry is found from the end)
hist_init:
        move.l  #ARENA,vHCur(a5)
        move.l  #ARENA,vHTop(a5)
        clr.w   vHDrop(a5)
hist_push:                              ; the working copy becomes the newest entry (redo entries are dropped, the oldest entries fall out when the ring is full)
        movem.l d0-d4/a0-a2,-(a7)
        lea     ARENA.l,a1
        cmpi.l  #ARENA,vHTop(a5)
        beq   .sz
        movea.l vHCur(a5),a1
        move.l  (a1),d1
        lea     (a1,d1.l),a1            ; behind the current entry
.sz:    moveq   #0,d3
        move.w  vNSeg(a5),d3
        mulu    #SEGSZ,d3
        moveq   #0,d4
        move.w  vNObj(a5),d4
        lsl.l   #3,d4
        add.l   d4,d3
        addi.l  #24,d3
.fit:   lea     (a1,d3.l),a2
        cmpa.l  #ARENAE,a2
        bls   .ok
        move.l  ARENA.l,d1              ; no room: the oldest entry goes
        lea     ARENA.l,a0
        lea     (a0,d1.l),a2
        move.l  a1,d2
        move.l  a2,d0
        sub.l   d0,d2
        lsr.l   #2,d2
        beq   .dd
        subq.w  #1,d2
.m:     move.l  (a2)+,(a0)+
        dbra    d2,.m
.dd:    suba.l  d1,a1
        sub.l   d1,vHCur(a5)
        move.w  #1,vHDrop(a5)
        bra   .fit
.ok:    move.l  d3,(a1)
        move.w  vNSeg(a5),4(a1)
        move.w  vNObj(a5),6(a1)
        move.w  vSeg(a5),8(a1)
        move.w  vObj(a5),10(a1)
        move.l  vPos(a5),12(a1)
        clr.l   16(a1)
        lea     20(a1),a0
        lea     SEGT.l,a2
        moveq   #0,d0
        move.w  vNSeg(a5),d0
        mulu    #3,d0
        beq   .s0
        subq.w  #1,d0
.s:     move.l  (a2)+,(a0)+
        dbra    d0,.s
.s0:    lea     OBJT.l,a2
        move.w  vNObj(a5),d0
        add.w   d0,d0
        beq   .o0
        subq.w  #1,d0
.o:     move.l  (a2)+,(a0)+
        dbra    d0,.o
.o0:    move.l  d3,(a0)
        move.l  a1,vHCur(a5)
        lea     (a1,d3.l),a2
        move.l  a2,vHTop(a5)
        movem.l (a7)+,d0-d4/a0-a2
        rts
hist_cur:                               ; the working copy := the current entry (the cursor stays where it is)
        move.w  vSeg(a5),-(a7)
        move.w  vObj(a5),-(a7)
        move.l  vPos(a5),-(a7)
        movea.l vHCur(a5),a0
        bsr     hist_load
        move.l  (a7)+,vPos(a5)
        move.w  (a7)+,vObj(a5)
        move.w  (a7)+,vSeg(a5)
        rts
hist_load:                              ; a0 = entry
        movem.l d0-d2/a0-a2,-(a7)
        move.w  4(a0),vNSeg(a5)
        move.w  6(a0),vNObj(a5)
        move.w  8(a0),vSeg(a5)
        move.w  10(a0),vObj(a5)
        move.l  12(a0),vPos(a5)
        lea     20(a0),a1
        lea     SEGT.l,a2
        moveq   #0,d0
        move.w  vNSeg(a5),d0
        mulu    #3,d0
        beq   .s0
        subq.w  #1,d0
.s:     move.l  (a1)+,(a2)+
        dbra    d0,.s
.s0:    lea     OBJT.l,a2
        move.w  vNObj(a5),d0
        add.w   d0,d0
        beq   .o0
        subq.w  #1,d0
.o:     move.l  (a1)+,(a2)+
        dbra    d0,.o
.o0:    bsr     find_bar
        movem.l (a7)+,d0-d2/a0-a2
        rts
c_undo: movea.l vHCur(a5),a0
        cmpa.l  #ARENA,a0
        beq   .no
        move.l  -4(a0),d0
        suba.l  d0,a0
        move.l  a0,vHCur(a5)
        bsr     hist_load
        bra     hist_done
.no:    lea     t_nound(pc),a0
        bra     msg
c_redo: movea.l vHCur(a5),a0
        move.l  (a0),d0
        lea     (a0,d0.l),a0
        cmpa.l  vHTop(a5),a0
        bcc   .no
        move.l  a0,vHCur(a5)
        bsr     hist_load
        bra     hist_done
.no:    lea     t_noredo(pc),a0
        bra     msg
hist_done:                              ; a state came back: all per-unit data is stale
        clr.w   vDirty(a5)
        move.w  #7,vXm(a5)
        moveq   #1,d0
        cmpi.l  #ARENA,vHCur(a5)
        bne   .m
        tst.w   vHDrop(a5)
        bne   .m
        moveq   #0,d0
.m:     move.w  d0,vMod(a5)
        clr.w   vLeaveW(a5)
        bra     refresh
refresh:                                ; per-unit data stale from vDirty on: remembered (vPD, vPM) and recomputed by flush_pend when no key is waiting
        move.w  vDirty(a5),d0
        cmpi.w  #$7fff,d0
        beq   .nd
        cmp.w   vPD(a5),d0
        bcc   .k
        move.w  d0,vPD(a5)
.k:     move.w  vXm(a5),d0
        tst.w   vPend(a5)
        beq   .f
        andi.w  #7,d0                   ; two edits waiting: no early stop in the width pass
        andi.w  #7,vPM(a5)
.f:     or.w    d0,vPM(a5)
        move.w  #1,vPend(a5)
.nd:    move.w  #7,vXm(a5)
        move.w  #$7fff,vDirty(a5)
        bsr     find_seg
        tst.w   vPend(a5)
        bne   .r
        bra     set_zoom
.r:     rts
ed_commit:                              ; an edit was made: history, modified, per-unit data, view
        bsr     hist_push
        move.w  #1,vMod(a5)
        clr.w   vLeaveW(a5)
        bra     refresh
ed_fail:                                ; a0 = message: the edit is undone
        move.l  a0,-(a7)
        bsr     hist_cur
        move.w  #$7fff,vDirty(a5)
        movea.l (a7)+,a0
        bra     msg
rs_fail:                                ; d0 = road_shift result
        lea     t_eroom(pc),a0
        cmpi.w  #1,d0
        beq     ed_fail
        lea     t_eobjend(pc),a0
        bra     ed_fail

; ---------------------------------------------------------------- apply: d0 = act, d1.w = value -> the working copy (the cursor's segment / object); d0 = 0 done / 1 refused (message set)
; acts: 1 curve 2 hill shape 3 length 4 width L 5 width R 6 object type 7 object side 8 raw hill accel
apply:  movem.l d2-d7/a1-a3,-(a7)
        move.w  vSeg(a5),vDirty(a5)
        move.w  #7,vXm(a5)
        move.w  d0,d2
        bsr     seg_ptr
        subq.w  #1,d2
        cmpi.w  #8,d2
        bcc   ap_ok
        add.w   d2,d2
        move.w  .t(pc,d2.w),d2
        jmp     .t(pc,d2.w)
.t:     dc.w    ap_curve-.t,ap_hill-.t,ap_len-.t,ap_wl-.t,ap_wr-.t,ap_type-.t,ap_side-.t,ap_raw-.t
ap_ok:  moveq   #0,d0
ap_x:   movem.l (a7)+,d2-d7/a1-a3
        rts
ap_bad: move.l  a0,vMsg(a5)             ; a0 = message
        moveq   #1,d0
        bra   ap_x
ap_curve:
        move.w  #4,vXm(a5)
        move.w  d1,4(a0)
        bra   ap_ok
ap_wl:  cmpi.w  #10,d1
        blt   ap_range
        cmpi.w  #85,d1
        bgt   ap_range
        move.w  #10,vXm(a5)
        move.b  d1,8(a0)
        bra   ap_ok
ap_wr:  cmpi.w  #10,d1
        blt   ap_range
        cmpi.w  #85,d1
        bgt   ap_range
        move.w  #10,vXm(a5)
        move.b  d1,9(a0)
        bra   ap_ok
ap_range:
        lea     t_erange(pc),a0
        bra   ap_bad
ap_raw: cmpi.w  #-6000,d1
        blt   ap_range
        cmpi.w  #4000,d1
        bgt   ap_range
        move.w  #1,vXm(a5)
        move.w  d1,6(a0)
ap_hov: bsr     hill_ovf
        tst.w   d0
        beq   ap_ok
        lea     t_ehill(pc),a0
        bra   ap_bad
ap_type: move.w #$7fff,vDirty(a5)
        bsr     obj_ptr
        tst.w   6(a0)
        bne   .bar
        move.w  d1,2(a0)
        bra   ap_ok
.bar:   lea     t_ebart(pc),a0
        bra   ap_bad
ap_side: move.w #$7fff,vDirty(a5)
        cmpi.w  #-128,d1
        blt   .r
        cmpi.w  #127,d1
        bgt   .r
        bsr     obj_ptr
        move.w  d1,4(a0)
        bra   ap_ok
.r:     lea     t_elat(pc),a0
        bra   ap_bad
ap_len: move.w  vSeg(a5),d4
        move.w  vNSeg(a5),d0
        subq.w  #1,d0
        cmp.w   d0,d4
        bcc   .last
        tst.w   d1
        ble   .r
        moveq   #0,d2
        move.w  (a0),d2
        moveq   #0,d3
        move.w  2(a0),d3
        andi.l  #$ffff,d1
        sub.l   d3,d1                   ; delta
        beq   ap_ok
        add.l   d3,d2                   ; P = the old end
        add.w   d1,2(a0)
        move.l  d1,d3
        addq.w  #1,d4
        bsr     road_shift
        tst.w   d0
        beq   ap_hov
        lea     t_eroom(pc),a0
        cmpi.w  #1,d0
        beq   ap_bad
        lea     t_eobjend(pc),a0
        bra   ap_bad
.last:  lea     t_elast(pc),a0
        bra   ap_bad
.r:     lea     t_erange(pc),a0
        bra   ap_bad
ap_hill: move.w d1,d2
        cmpi.w  #13,d2
        beq   ap_ok                     ; RAW ACCEL...: the exact list follows
        tst.w   d2
        bne   .shape
        clr.w   6(a0)                   ; FLAT
        bra   ap_hov
.shape: subq.w  #1,d2                   ; 0..11: family = d2 / 3 (RISE DROP CREST DIP), size = d2 mod 3
        ext.l   d2
        divu    #3,d2
        move.w  d2,d5                   ; family
        swap    d2
        add.w   d2,d2
        lea     hh_tab(pc),a1
        move.w  (a1,d2.w),d6            ; the height the shape reaches
        moveq   #0,d3
        move.w  2(a0),d3                ; length
        clr.w   vPcN(a5)
        cmpi.w  #2,d5
        bcc   .crest
        lsr.w   #1,d3                   ; n = length / 2: +a for n, 0 for the odd unit, -a for n
        beq   .short
        bsr     ap_accel
        btst    #0,d5
        beq   .r1
        neg.w   d4
.r1:    move.w  2(a0),d7
        move.w  d3,d1
        add.w   d1,d1
        sub.w   d1,d7                   ; remainder 0 / 1
        move.w  d3,d0
        move.w  d4,d2
        bsr     pc_add
        move.w  d7,d0
        moveq   #0,d2
        bsr     pc_add
        move.w  d3,d0
        move.w  d4,d2
        neg.w   d2
        bsr     pc_add
        bra   .build
.crest: lsr.w   #2,d3                   ; n = length / 4: +a n, -a n, 0 for the remainder, -a n, +a n (back to the start slope)
        beq   .short
        bsr     ap_accel
        btst    #0,d5
        beq   .c1
        neg.w   d4
.c1:    move.w  2(a0),d7
        move.w  d3,d1
        lsl.w   #2,d1
        sub.w   d1,d7                   ; remainder 0..3
        move.w  d3,d0
        move.w  d4,d2
        bsr     pc_add
        move.w  d3,d0
        move.w  d4,d2
        neg.w   d2
        bsr     pc_add
        move.w  d7,d0
        moveq   #0,d2
        bsr     pc_add
        move.w  d3,d0
        move.w  d4,d2
        neg.w   d2
        bsr     pc_add
        move.w  d3,d0
        move.w  d4,d2
        bsr     pc_add
.build: move.w  vPcN(a5),d3
        move.w  vNSeg(a5),d0
        add.w   d3,d0
        subq.w  #1,d0
        cmpi.w  #MAXSEG,d0
        bhi   .full
        move.w  vSeg(a5),d7
        lea     vPc(a5),a2
        move.w  (a2),2(a0)              ; piece 0 replaces the segment's length and accel
        move.w  2(a2),6(a0)
        moveq   #1,d3
.l:     cmp.w   vPcN(a5),d3
        bcc   .done
        move.w  d7,d0
        add.w   d3,d0
        bsr     seg_open                ; a0 = the new slot, a copy of the piece before it
        lea     -SEGSZ(a0),a1
        move.l  (a1)+,(a0)+
        move.l  (a1)+,(a0)+
        move.l  (a1)+,(a0)+
        lea     -SEGSZ(a0),a0
        move.w  -SEGSZ(a0),d0
        add.w   -SEGSZ+2(a0),d0
        move.w  d0,(a0)                 ; start = the end of the piece before
        move.w  d3,d0
        lsl.w   #2,d0
        move.w  (a2,d0.w),2(a0)
        move.w  2(a2,d0.w),6(a0)
        addq.w  #1,d3
        bra   .l
.done:  bra   ap_hov
.short: lea     t_eshort(pc),a0
        bra   ap_bad
.full:  lea     t_efullseg(pc),a0
        bra   ap_bad
; ap_accel: d3.w = n, d6.w = height -> d4.w = accel (1..4000) so that +a for n units, then -a for n units gains about that height (a n^2 / 65536)
ap_accel:
        movem.l d0-d2,-(a7)
        moveq   #0,d1
        move.w  d3,d1
        mulu    d3,d1                   ; n^2
        moveq   #0,d0
        move.w  d6,d0
        swap    d0                      ; h << 16
.sh:    cmpi.l  #$ffff,d1
        bls   .dv
        lsr.l   #1,d1
        lsr.l   #1,d0
        bra   .sh
.dv:    divu    d1,d0
        bvs   .big
        cmpi.w  #4000,d0
        bls   .c
.big:   move.w  #4000,d0
.c:     tst.w   d0
        bne   .n
        moveq   #1,d0
.n:     move.w  d0,d4
        movem.l (a7)+,d0-d2
        rts
; pc_add: d0.w = length, d2.w = accel: a piece of the hill shape (a zero length is skipped, an equal accel joins the piece before)
pc_add: movem.l d0-d3/a1,-(a7)
        tst.w   d0
        beq   .x
        move.w  vPcN(a5),d3
        lea     vPc(a5),a1
        tst.w   d3
        beq   .new
        subq.w  #1,d3
        lsl.w   #2,d3
        cmp.w   2(a1,d3.w),d2
        bne   .new
        add.w   d0,(a1,d3.w)
        bra   .x
.new:   move.w  vPcN(a5),d3
        lsl.w   #2,d3
        move.w  d0,(a1,d3.w)
        move.w  d2,2(a1,d3.w)
        addq.w  #1,vPcN(a5)
.x:     movem.l (a7)+,d0-d3/a1
        rts
hill_ovf:                               ; d0 = 1 when the 32-bit hill integrator overflows anywhere in the stream (E-HILL)
        movem.l d1-d5/a0,-(a7)
        lea     SEGT.l,a0
        move.w  vNSeg(a5),d5
        subq.w  #1,d5
        moveq   #0,d2
        moveq   #0,d3
.s:     move.w  6(a0),d4
        ext.l   d4
        move.w  2(a0),d1
        subq.w  #1,d1
.u:     add.l   d2,d3
        bvs   .ov
        add.l   d4,d2
        bvs   .ov
        dbra    d1,.u
        lea     SEGSZ(a0),a0
        dbra    d5,.s
        moveq   #0,d0
        bra   .x
.ov:    moveq   #1,d0
.x:     movem.l (a7)+,d1-d5/a0
        rts

apply_try:                              ; d0 = act, d1 = value: apply to the working copy, keep it as a new history entry
        bsr     apply
        tst.w   d0
        bne   .f
        bra     ed_commit
.f:     bsr     hist_cur
        move.w  #$7fff,vDirty(a5)
        move.w  #7,vXm(a5)
        ori.w   #2,vRedraw(a5)
        rts
record: move.w  vLAct(a5),vLastAct(a5)
        move.w  vLVal(a5),vLastVal(a5)
        cmpi.w  #6,vLAct(a5)
        bne   .s
        move.w  vLVal(a5),vLastType(a5)
.s:     cmpi.w  #7,vLAct(a5)
        bne   .x
        move.w  vLVal(a5),vLastSide(a5)
.x:     rts
rep_cmd:                                ; Return / Space: the last picked value again, at the cursor
        move.w  vLastAct(a5),d0
        beq   .none
        cmpi.w  #6,d0
        beq   .o
        cmpi.w  #7,d0
        beq   .o
        tst.w   vFocus(a5)
        bne   .wrong
        bra   .go
.o:     tst.w   vFocus(a5)
        beq   .wrong
.go:    move.w  vLastVal(a5),d1
        bra     apply_try
.none:  lea     t_norep(pc),a0
        bra     msg
.wrong: lea     t_wrongrow(pc),a0
        bra     msg
curve_step:                             ; d2 = -1 / +1: one step more to the left / right
        tst.w   vFocus(a5)
        bne   el_road
        bsr     seg_ptr
        move.w  4(a0),d1
        add.w   d2,d1
        cmpi.w  #-9,d1
        blt   .lim
        cmpi.w  #10,d1
        bgt   .lim
        moveq   #1,d0
        move.w  d0,vLastAct(a5)
        move.w  d1,vLastVal(a5)
        bra     apply_try
.lim:   lea     t_climit(pc),a0
        bra     msg

; ---------------------------------------------------------------- pick lists with a live preview: the box takes the right 12 columns (the map is fitted into the rest), moving the selection applies the value to the
; working copy, re-expands and redraws (double buffered); BACK / Esc restores.  Types: a full screen list (no preview).  Left / right = exact value (fire / Control 10, Shift 100) in the numeric lists.
cmd_edit:
        subi.w  #10,d0
        cmpi.w  #17,d0
        bcc   .r
        add.w   d0,d0
        move.w  .t(pc,d0.w),d0
        jmp     .t(pc,d0.w)
.r:     rts
.t:     dc.w    c_curve-.t,c_hill-.t,c_len-.t,c_wl-.t,c_wr-.t,c_ins-.t,c_spl-.t,c_del-.t,c_type-.t,c_bar-.t,c_undo-.t,c_redo-.t,c_check-.t,c_mrg-.t,c_cm-.t,c_cp-.t,c_td-.t
c_curve: moveq  #1,d0
        bra   el_road
c_hill: moveq   #2,d0
        bra   el_road
c_len:  moveq   #3,d0
        bra   el_road
c_wl:   moveq   #4,d0
        bra   el_road
c_wr:   moveq   #5,d0
        bra   el_road
el_road: tst.w  vFocus(a5)
        bne   .no
        bra     edit_list
.no:    lea     t_roadrow(pc),a0
        bra     msg
c_type: moveq   #6,d0
el_obj: tst.w   vFocus(a5)
        beq   .no
        bra     edit_list
.no:    lea     t_objrow(pc),a0
        bra     msg
c_spl:  tst.w   vFocus(a5)
        beq     seg_split
        moveq   #7,d0
        bra   el_obj
c_ins:  tst.w   vFocus(a5)
        beq     seg_copy
        bra     obj_add
c_del:  tst.w   vFocus(a5)
        beq     seg_del
        bra     obj_del
c_mrg:  tst.w   vFocus(a5)
        beq     seg_merge
        bra     obj_move
c_bar:  bra     bar_here
c_cm:   moveq   #-1,d2
        bra     curve_step
c_cp:   moveq   #1,d2
        bra     curve_step

edit_list:                              ; d0 = act
        movem.l d1-d7/a0-a4,-(a7)
        bsr     flush_pend
        move.w  d0,vLAct(a5)
        cmpi.w  #3,d0
        bne   .nl
        move.w  vSeg(a5),d1
        move.w  vNSeg(a5),d2
        subq.w  #1,d2
        cmp.w   d2,d1
        bcc   .last
.nl:    cmpi.w  #6,d0
        bne   .nt
        bsr     obj_ptr
        tst.w   6(a0)
        bne   .bart
.nt:    move.w  vLAct(a5),d0
        subq.w  #1,d0
        mulu    #20,d0
        lea     ad_tab(pc),a1
        adda.w  d0,a1
        move.w  (a1)+,vLKind(a5)
        move.w  (a1)+,vLBias(a5)
        move.w  (a1)+,vLCnt(a5)
        move.w  (a1)+,vLAdj(a5)
        move.w  (a1)+,vLMin(a5)
        move.w  (a1)+,vLMax(a5)
        move.l  (a1)+,vLTab(a5)
        move.l  (a1)+,vLHead(a5)
        clr.w   vLWide(a5)
        move.w  #28,vLCol(a5)
        move.w  #12,vLW(a5)
        move.w  #2,vLRow0(a5)
        move.w  #18,vLRows(a5)
        lea     t_lhsel(pc),a0
        tst.w   vLAdj(a5)
        beq   .h
        lea     t_lhadj(pc),a0
.h:     move.l  a0,vLHintP(a5)
        cmpi.w  #2,vLKind(a5)
        bne   .nw
        move.w  #1,vLWide(a5)
        move.w  #1,vLCol(a5)
        move.w  #38,vLW(a5)
        move.w  #3,vLRow0(a5)
        move.w  #20,vLRows(a5)
        move.w  vNTypes(a5),d0
        tst.w   vBarT(a5)
        beq   .nb
        subq.w  #1,d0
.nb:    move.w  d0,vLCnt(a5)
.nw:    clr.w   vLTop(a5)
        bsr     cur_val
        move.w  d0,vLVal(a5)
        bsr     val_sel
        bsr     lpick
        move.w  d0,-(a7)
        bsr     lb_close
        move.w  (a7)+,d0
        bmi   .cancel
        tst.w   vLWide(a5)
        bne   .wide
        cmpi.w  #2,vLAct(a5)
        bne   .rec
        cmpi.w  #13,vLVal(a5)
        bne   .rec
        bsr     hist_cur                ; RAW ACCEL...: the exact list, from the unchanged segment
        move.w  vSeg(a5),d0
        moveq   #7,d1
        bsr     expand_from
        move.w  #7,vXm(a5)
        moveq   #8,d0
        bsr     edit_list
        bra   .x
.rec:   bsr     record
        bsr     hist_push
        move.w  #1,vMod(a5)
        clr.w   vLeaveW(a5)
        bsr     set_zoom
        bra   .x
.wide:  bsr     record
        move.w  vLAct(a5),d0
        move.w  vLVal(a5),d1
        bsr     apply_try
        bra   .x
.cancel: bsr    hist_cur
        move.w  vLAct(a5),d0
        bsr     act_mask
        move.w  vSeg(a5),d0
        bsr     expand_from
        move.w  #7,vXm(a5)
        move.w  #$7fff,vDirty(a5)
        bsr     set_zoom
        bra   .x
.last:  lea     t_elast(pc),a0
        bsr     msg
        bra   .x
.bart:  lea     t_ebart(pc),a0
        bsr     msg
.x:     movem.l (a7)+,d1-d7/a0-a4
        rts
cur_val:                                ; the value of the cursor's segment / object for the act -> d0.w
        move.w  vLAct(a5),d1
        cmpi.w  #6,d1
        bcs   .rd
        cmpi.w  #8,d1
        beq   .rd
        bsr     obj_ptr
        bra   .go
.rd:    bsr     seg_ptr
.go:    lea     cv_tab(pc),a1
        subq.w  #1,d1
        lsl.w   #2,d1
        adda.w  d1,a1
        move.w  (a1)+,d2
        move.w  (a1),d3
        moveq   #0,d0
        tst.w   d3
        beq   .x
        cmpi.w  #1,d3
        beq   .b
        move.w  (a0,d2.w),d0
        rts
.b:     move.b  (a0,d2.w),d0
.x:     rts
type_of:                                ; d0.w = list index -> d0.w = type number (the BAR's type is not in the list)
        addq.w  #1,d0
        tst.w   vBarT(a5)
        beq   .x
        cmp.w   vBarT(a5),d0
        blt   .x
        addq.w  #1,d0
.x:     rts
sel_val:                                ; vLSel (a valid item) -> vLVal
        movem.l d0-d1/a0,-(a7)
        move.w  vLSel(a5),d0
        move.w  vLKind(a5),d1
        bne   .k1
        add.w   vLBias(a5),d0
        bra   .st
.k1:    cmpi.w  #1,d1
        bne   .k2
        movea.l vLTab(a5),a0
        add.w   d0,d0
        move.w  (a0,d0.w),d0
        bra   .st
.k2:    bsr     type_of
.st:    move.w  d0,vLVal(a5)
        movem.l (a7)+,d0-d1/a0
        rts
val_sel:                                ; vLVal -> the item that shows it (vLSel, -1 = none)
        movem.l d0-d2/a0,-(a7)
        move.w  vLVal(a5),d0
        move.w  vLKind(a5),d1
        bne   .k1
        sub.w   vLBias(a5),d0
        bmi   .z
        cmp.w   vLCnt(a5),d0
        bcs   .set
.z:     moveq   #0,d0
.set:   move.w  d0,vLSel(a5)
        bra   .x
.k1:    cmpi.w  #1,d1
        bne   .k2
        movea.l vLTab(a5),a0
        moveq   #0,d1
.s1:    cmp.w   vLCnt(a5),d1
        bcc   .no1
        cmp.w   (a0)+,d0
        beq   .f1
        addq.w  #1,d1
        bra   .s1
.f1:    move.w  d1,vLSel(a5)
        bra   .x
.no1:   move.w  #-1,vLSel(a5)
        bra   .x
.k2:    tst.w   vBarT(a5)
        beq   .t1
        cmp.w   vBarT(a5),d0
        ble   .t1
        subq.w  #1,d0
.t1:    subq.w  #1,d0
        bpl   .set
        bra   .z
.x:     movem.l (a7)+,d0-d2/a0
        rts
lscroll:                                ; keep the selection inside the visible rows
        move.w  vLSel(a5),d0
        bmi   .x
        move.w  vLTop(a5),d1
        cmp.w   d1,d0
        bcc   .a
        move.w  d0,d1
        bra   .s
.a:     move.w  vLRows(a5),d2
        add.w   d1,d2
        cmp.w   d2,d0
        bcs   .x
        move.w  d0,d1
        sub.w   vLRows(a5),d1
        addq.w  #1,d1
.s:     move.w  d1,vLTop(a5)
.x:     rts
litem:                                  ; d0.w = item -> a0 = its text
        cmp.w   vLCnt(a5),d0
        bne   .n
        lea     t_back(pc),a0
        rts
.n:     movem.l d1-d2/a1-a2,-(a7)
        move.w  vLKind(a5),d1
        bne   .k1
        movea.l vLTab(a5),a0
        move.w  d0,d1
        beq   .x
        subq.w  #1,d1
.k0:    tst.b   (a0)+
        bne   .k0
        dbra    d1,.k0
        bra   .x
.k1:    cmpi.w  #1,d1
        bne   .k2
        movea.l vLTab(a5),a0
        add.w   d0,d0
        move.w  (a0,d0.w),d0
        lea     vLTxt(a5),a1
        bsr     apdn
        clr.b   (a1)
        lea     vLTxt(a5),a0
        bra   .x
.k2:    bsr     type_of
        lea     vLTxt(a5),a1
        move.w  d0,d2
        andi.l  #$ffff,d0
        moveq   #3,d1
        bsr     appn
        lea     t_tk(pc),a0
        bsr     apps
        subq.w  #1,d2
        mulu    #12,d2
        lea     TYPS.l,a2
        adda.l  d2,a2
        moveq   #0,d0
        move.w  2(a2),d0
        moveq   #1,d1
        bsr     appn
        lea     t_ts(pc),a0
        bsr     apps
        moveq   #0,d0
        move.w  4(a2),d0
        moveq   #1,d1
        bsr     appn
        lea     t_tp(pc),a0
        bsr     apps
        move.w  6(a2),d0
        bsr     apdn
        clr.b   (a1)
        lea     vLTxt(a5),a0
.x:     movem.l (a7)+,d1-d2/a1-a2
        rts
lrow:                                   ; d6.w = item: drawn padded to the box width on its row, the selected one as a white bar
        movem.l d0-d3/a0-a1,-(a7)
        move.w  d6,d0
        bsr     litem
        lea     vLine(a5),a1
        move.w  vLW(a5),d3
        subq.w  #1,d3
.c:     move.b  (a0),d0
        beq   .p
        addq.l  #1,a0
        move.b  d0,(a1)+
        dbra    d3,.c
        bra   .e
.p:     move.b  #' ',(a1)+
        dbra    d3,.p
.e:     clr.b   (a1)
        move.w  d6,d1
        sub.w   vLTop(a5),d1
        add.w   vLRow0(a5),d1
        move.w  vLCol(a5),d0
        moveq   #7,d2
        cmp.w   vLSel(a5),d6
        bne   .pt
        moveq   #23,d2
.pt:    lea     vLine(a5),a0
        bsr     ptext
        movem.l (a7)+,d0-d3/a0-a1
        rts
lrows:  movem.l d0-d7/a0-a3,-(a7)
        lea     vLine(a5),a1
        movea.l vLHead(a5),a0
        bsr     apps
        tst.w   vLAdj(a5)
        beq   .h1
        move.b  #' ',(a1)+
        move.w  vLVal(a5),d0
        bsr     apdn
.h1:    lea     vLine(a5),a0
        adda.w  vLW(a5),a0
.h2:    cmpa.l  a0,a1
        bcc   .h3
        move.b  #' ',(a1)+
        bra   .h2
.h3:    clr.b   (a0)
        lea     vLine(a5),a0
        move.w  vLCol(a5),d0
        moveq   #1,d1
        moveq   #8,d2
        bsr     ptext
        move.w  vLTop(a5),d6
        move.w  vLRows(a5),d7
        subq.w  #1,d7
.rl:    cmp.w   vLCnt(a5),d6
        bhi   .rd
        bsr     lrow
        addq.w  #1,d6
        dbra    d7,.rl
.rd:    tst.w   vLWide(a5)
        beq   .x
        movea.l vLHintP(a5),a0
        moveq   #1,d0
        moveq   #24,d1
        moveq   #1,d2
        bsr     ptext
.x:     movem.l (a7)+,d0-d7/a0-a3
        rts
box_clr:                                ; the right 12 columns, rows 1..21
        movea.l vDraw(a5),a0
        adda.w  #8*160+112,a0
        move.w  #167,d0
.l:     moveq   #11,d1
.i:     clr.l   (a0)+
        dbra    d1,.i
        lea     160-48(a0),a0
        dbra    d0,.l
        rts
lbox:   tst.w   vLWide(a5)
        bne   lrows
        bsr     box_clr
        bra     lrows
lb_open:                                ; narrow lists: the map goes into the left 224 columns, the page is redrawn with the box
        tst.w   vLWide(a5)
        bne   .w
        move.w  #208,vMapW(a5)
        move.w  #112,vMapCx(a5)
        move.w  #224,vMapLim(a5)
        bsr     map_fit
        move.w  #1,vLOpen(a5)
        bsr     lscroll
        bra     full_draw
.w:     move.w  #1,vLOpen(a5)
        bsr     lscroll
        bsr     cls
        bra     lrows
lb_close:
        clr.w   vLOpen(a5)
        move.w  #304,vMapW(a5)
        move.w  #160,vMapCx(a5)
        move.w  #320,vMapLim(a5)
        bra     map_fit
lpreview:                               ; the working copy with the shown value applied, expanded and drawn
        move.w  #1,vLBusy(a5)
        clr.w   vLPend(a5)
        bsr     hist_cur
        move.w  vLAct(a5),d0
        move.w  vLVal(a5),d1
        bsr     apply
        clr.w   vLBad(a5)
        tst.w   d0
        beq   .ok
        move.w  #1,vLBad(a5)
        bsr     hist_cur                ; refused: the old state, the message stays on the hint row
.ok:    move.w  vDirty(a5),d0
        move.w  vXm(a5),d1
        bsr     expand_from
        move.w  #$7fff,vDirty(a5)
        move.w  #7,vXm(a5)
        bsr     full_draw
        clr.w   vLBusy(a5)
        rts
lpick:  movem.l d1-d7/a0-a4,-(a7)
        clr.w   vLPend(a5)
        clr.w   vLBad(a5)
        bsr     lb_open
        bsr     in_reset
.loop:  jsr     $d206.l
        bsr     kq_popn
        tst.b   d0
        beq   .nk
        cmpi.b  #$1c,d0
        beq   .ok
        cmpi.b  #$72,d0
        beq   .ok
        cmpi.b  #$39,d0
        beq   .ok
        cmpi.b  #$01,d0
        beq   .cancel
        cmpi.b  #$0e,d0
        beq   .cancel
        cmpi.b  #$44,d0
        beq   .cancel
.nk:    bsr     poll_dirs
        move.w  d2,d5
        tst.b   d3
        bpl   .fu
        tst.w   vFire(a5)
        bne   .fh
        move.w  #1,vFire(a5)
        clr.w   vFireMv(a5)
.fh:    tst.w   d5
        beq   .e1
        move.w  #1,vFireMv(a5)
        bra   .e1
.fu:    tst.w   vFire(a5)
        beq   .e1
        clr.w   vFire(a5)
        tst.w   vFireMv(a5)
        beq   .ok
.e1:    tst.w   d5
        beq   .idle
        btst    #0,d5
        bne   .up
        btst    #1,d5
        bne   .dn
        btst    #2,d5
        bne   .lf
        tst.w   vLAdj(a5)
        beq   .loop
        moveq   #1,d0
        bra   .adj
.lf:    tst.w   vLAdj(a5)
        beq   .cancel
        moveq   #-1,d0
.adj:   moveq   #1,d1                   ; step 1; 10 with fire or Control; 100 with Shift
        tst.b   d3
        bmi   .s10
        tst.b   $5ffe+$1d.w
        beq   .s2
.s10:   moveq   #10,d1
.s2:    tst.b   $5ffe+$2a.w
        bne   .s100
        tst.b   $5ffe+$36.w
        beq   .s3
.s100:  moveq   #100,d1
.s3:    muls    d1,d0
        add.w   vLVal(a5),d0
        cmp.w   vLMax(a5),d0
        ble   .a1
        move.w  vLMax(a5),d0
.a1:    cmp.w   vLMin(a5),d0
        bge   .a2
        move.w  vLMin(a5),d0
.a2:    move.w  d0,vLVal(a5)
        bsr     val_sel
        bra   .chg
.up:    move.w  vLSel(a5),d0
        subq.w  #1,d0
        bpl   .u1
        move.w  vLCnt(a5),d0
.u1:    move.w  d0,vLSel(a5)
        bra   .sel
.dn:    move.w  vLSel(a5),d0
        addq.w  #1,d0
        cmp.w   vLCnt(a5),d0
        bls   .d1
        moveq   #0,d0
.d1:    move.w  d0,vLSel(a5)
.sel:   move.w  vLSel(a5),d0
        cmp.w   vLCnt(a5),d0
        bcc   .rows
        bsr     sel_val
.chg:   tst.w   vLWide(a5)
        bne   .rows
        move.w  #1,vLPend(a5)
.rows:  bsr     lscroll
        move.w  #1,vLRd(a5)
        bra   .loop
.idle:  bsr     kq_empty
        bne   .loop                     ; keys waiting: move the selection first (the rows and the preview follow when they are all in)
        tst.w   vLRd(a5)
        beq   .id1
        clr.w   vLRd(a5)
        bsr     lrows
.id1:   tst.w   vLPend(a5)
        beq   .loop
        bsr     lpreview
        bra   .loop
.ok:    move.w  vLSel(a5),d0
        cmp.w   vLCnt(a5),d0
        beq   .cancel
        tst.w   vLWide(a5)
        bne   .o2
        bsr     lpreview
.o2:    tst.w   vLBad(a5)
        bne   .loop
        moveq   #0,d0
        bra   .out
.cancel: moveq  #-1,d0
.out:   move.w  d0,-(a7)
.fr:    jsr     $d206.l                 ; fire must be released before the next screen
        btst    #7,$6105.w
        bne   .fr
        clr.b   $60ff.w
        move.w  (a7)+,d0
        movem.l (a7)+,d1-d7/a0-a4
        rts

; ---------------------------------------------------------------- segment edits (the road row)
seg_copy:                               ; I: insert a copy of the segment behind it (the road behind moves down by its length)
        move.w  vSeg(a5),d6
        move.w  vNSeg(a5),d0
        subq.w  #1,d0
        cmp.w   d0,d6
        bcc   el_last
        cmpi.w  #MAXSEG,vNSeg(a5)
        bcc   el_fullseg
        bsr     seg_ptr
        moveq   #0,d2
        move.w  (a0),d2
        moveq   #0,d5
        move.w  2(a0),d5
        add.l   d5,d2                   ; P
        move.w  d6,d0
        addq.w  #1,d0
        bsr     seg_open
        lea     -SEGSZ(a0),a1
        move.l  (a1)+,(a0)+
        move.l  (a1)+,(a0)+
        move.l  (a1)+,(a0)+
        move.w  d2,-SEGSZ(a0)
        move.l  d5,d3
        move.w  d6,d4
        addq.w  #2,d4
        bsr     road_shift
        tst.w   d0
        bne     rs_fail
        bsr     hill_ovf
        tst.w   d0
        bne     hov_fail
        move.l  d2,vPos(a5)
        addq.w  #1,d6
        move.w  d6,vSeg(a5)
        move.w  d6,vDirty(a5)
        bra     ed_commit
el_last: lea    t_elast(pc),a0
        bra     msg
el_fullseg: lea t_efullseg(pc),a0
        bra     msg
seg_del:                                ; Delete: remove the segment (the road behind moves up)
        move.w  vSeg(a5),d6
        move.w  vNSeg(a5),d0
        subq.w  #1,d0
        cmp.w   d0,d6
        bcc   el_last
        bsr     seg_ptr
        moveq   #0,d2
        move.w  (a0),d2
        moveq   #0,d5
        move.w  2(a0),d5
        add.l   d5,d2                   ; P
        move.l  d5,d3
        neg.l   d3
        move.w  d6,d0
        bsr     seg_shut
        move.w  d6,d4
        bsr     road_shift
        tst.w   d0
        bne     rs_fail
        bsr     hill_ovf
        tst.w   d0
        bne     hov_fail
        bsr     seg_ptr
        moveq   #0,d0
        move.w  (a0),d0
        move.l  d0,vPos(a5)
        move.w  d6,vDirty(a5)
        bra     ed_commit
seg_split:                              ; S: split at the cursor (after a fine move)
        cmpi.w  #MAXSEG,vNSeg(a5)
        bcc   el_fullseg
        move.w  vSeg(a5),d6
        bsr     seg_ptr
        moveq   #0,d2
        move.w  (a0),d2
        move.l  vPos(a5),d3
        sub.l   d2,d3
        bhi   .in
        lea     t_esplit(pc),a0
        bra     msg
.in:    moveq   #0,d4
        move.w  2(a0),d4
        cmp.l   d4,d3
        bcc   .out
        move.w  d3,-(a7)                ; first part
        move.w  d4,-(a7)                ; old length
        move.w  d6,d0
        addq.w  #1,d0
        bsr     seg_open
        lea     -SEGSZ(a0),a1
        move.l  (a1)+,(a0)+
        move.l  (a1)+,(a0)+
        move.l  (a1)+,(a0)+
        lea     -SEGSZ(a0),a0
        move.w  (a7)+,d4
        move.w  (a7)+,d3
        move.w  vPos+2(a5),(a0)         ; the new segment starts at the cursor
        move.w  d4,d5
        sub.w   d3,d5
        move.w  d5,2(a0)
        move.w  d3,-SEGSZ+2(a0)         ; the first part keeps the start
        addq.w  #1,d6
        move.w  d6,vSeg(a5)
        subq.w  #1,d6
        move.w  d6,vDirty(a5)
        bra     ed_commit
.out:   lea     t_esplit(pc),a0
        bra     msg
seg_merge:                              ; M: join the segment with the next one (this one's curve, hill and widths win)
        move.w  vSeg(a5),d6
        move.w  vNSeg(a5),d0
        subq.w  #1,d0
        cmp.w   d0,d6
        bcc   el_last
        bsr     seg_ptr
        move.w  SEGSZ+2(a0),d0
        add.w   d0,2(a0)
        move.w  d6,d0
        addq.w  #1,d0
        bsr     seg_shut
        bsr     hill_ovf
        tst.w   d0
        bne     hov_fail
        move.w  d6,vDirty(a5)
        bra     ed_commit
hov_fail: lea   t_ehill(pc),a0
        bra     ed_fail

; ---------------------------------------------------------------- object edits (the objects row)
obj_add:                                ; I: an object of the last picked type at the cursor
        move.l  vPos(a5),d3
        beq   .e0
        cmpi.w  #MAXOBJ,vNObj(a5)
        bcc   .full
        lea     OBJT.l,a0
        moveq   #0,d0
        move.w  vNObj(a5),d1
.f:     cmp.w   d1,d0
        bcc   .ins
        cmp.w   (a0),d3
        bcs   .ins
        beq   .gap
        addq.l  #8,a0
        addq.w  #1,d0
        bra   .f
.ins:   move.w  d0,d6
        bsr     obj_open
        move.w  d3,(a0)
        move.w  vLastType(a5),d0
        bne   .t
        moveq   #1,d0
        cmp.w   vBarT(a5),d0
        bne   .t
        moveq   #2,d0
.t:     move.w  d0,2(a0)
        move.w  vLastSide(a5),4(a0)
        clr.w   6(a0)
        move.w  d6,vObj(a5)
        move.w  #$7fff,vDirty(a5)
        bsr     ed_commit
        bsr     dens_chk
        tst.w   d0
        beq   .x
        lea     t_wdens(pc),a0
        bra     msg
.x:     rts
.e0:    lea     t_eobj0(pc),a0
        bra     msg
.gap:   lea     t_egap(pc),a0
        bra     msg
.full:  lea     t_efullobj(pc),a0
        bra     msg
obj_del:                                ; Delete: remove the object (never the BAR)
        tst.w   vNObj(a5)
        beq   .x
        bsr     obj_ptr
        tst.w   6(a0)
        bne   .bar
        cmpi.w  #1,vNObj(a5)
        beq   .x
        move.w  vObj(a5),d0
        bsr     obj_shut
        move.w  vNObj(a5),d0
        subq.w  #1,d0
        cmp.w   vObj(a5),d0
        bcc   .k
        move.w  d0,vObj(a5)
.k:     bsr     obj_pos
        move.w  #$7fff,vDirty(a5)
        bra     ed_commit
.bar:   lea     t_ebardel(pc),a0
        bra     msg
.x:     rts
obj_move:                               ; M: the object follows left / right until FIRE / Return (Esc = back)
        tst.w   vNObj(a5)
        beq   .x
        bsr     obj_ptr
        move.w  (a0),vMoveOrg(a5)
        move.w  #1,vMode(a5)
        ori.w   #2,vRedraw(a5)
.x:     rts
obj_mv_step:                            ; moving: d0 = -1 / +1, d4 = 0 ten units, 1 one unit (fire / Control), 2 a hundred (Shift)
        moveq   #10,d1
        cmpi.w  #1,d4
        bne   .a1
        moveq   #1,d1
.a1:    cmpi.w  #2,d4
        bne   .a2
        moveq   #100,d1
.a2:    tst.w   d0
        bpl   .a3
        neg.w   d1
.a3:    bsr     obj_ptr
        move.w  (a0),d3
        add.w   d1,d3                   ; the wanted position
        move.w  #1,d5                   ; lowest: 1, or behind the object before
        tst.w   vObj(a5)
        beq   .a4
        move.w  -8(a0),d5
        addq.w  #1,d5
.a4:    move.w  #32767,d6               ; highest: before the next object
        move.w  vObj(a5),d2
        addq.w  #1,d2
        cmp.w   vNObj(a5),d2
        bcc   .a5
        move.w  8(a0),d6
        subq.w  #1,d6
.a5:    cmp.w   d5,d3
        bge   .a6
        move.w  d5,d3
.a6:    cmp.w   d6,d3
        ble   .a7
        move.w  d6,d3
.a7:    move.w  d3,(a0)
        bra     obj_pos
mv_cmd:                                 ; moving: Return / Space / FIRE = keep the new place, Esc / F10 = back
        cmpi.w  #8,d0
        beq   .ok
        cmpi.w  #9,d0
        beq   .ok
        cmpi.w  #1,d0
        bne   .x
        clr.w   vMode(a5)
        bsr     obj_ptr
        move.w  vMoveOrg(a5),(a0)
        bsr     obj_pos
        ori.w   #3,vRedraw(a5)
        rts
.ok:    clr.w   vMode(a5)
        bsr     obj_ptr
        move.w  #$7fff,vDirty(a5)
        tst.w   6(a0)
        beq   .c
        bsr     dirty_end               ; the BAR moved: the extent changes
        bsr     find_bar
.c:     bra     ed_commit
.x:     rts
bar_here:                               ; Shift+B: the BAR goes to the cursor (it is moved, never deleted or doubled)
        move.l  vPos(a5),d3
        beq   .e0
        tst.w   vBarT(a5)
        beq   .nb
        moveq   #0,d4                   ; the BAR's lateral
        lea     OBJT.l,a0
        move.w  vNObj(a5),d1
        beq   .x
        subq.w  #1,d1
.s:     tst.w   6(a0)
        beq   .sn
        cmp.w   (a0),d3
        beq   .gapok
.sn:    cmp.w   (a0),d3
        beq   .gap
        addq.l  #8,a0
        dbra    d1,.s
        bra   .go
.gapok: bra   .go
.go:    bsr     dirty_end
        move.w  vNObj(a5),d6
        subq.w  #1,d6
.d:     bmi   .dd
        move.w  d6,d0
        lsl.w   #3,d0
        lea     OBJT.l,a0
        tst.w   6(a0,d0.w)
        beq   .dn
        move.w  4(a0,d0.w),d4
        move.w  d6,d0
        bsr     obj_shut
.dn:    subq.w  #1,d6
        bra   .d
.dd:    lea     OBJT.l,a0
        moveq   #0,d0
        move.w  vNObj(a5),d1
.f:     cmp.w   d1,d0
        bcc   .ins
        cmp.w   (a0),d3
        bcs   .ins
        addq.l  #8,a0
        addq.w  #1,d0
        bra   .f
.ins:   move.w  d0,d6
        bsr     obj_open
        move.w  d3,(a0)
        move.w  vBarT(a5),2(a0)
        move.w  d4,4(a0)
        move.w  #1,6(a0)
        move.w  d6,vObj(a5)
        bsr     find_bar
        bsr     ed_commit
        move.l  vBarAt(a5),d0
        bmi   .x
        moveq   #0,d1
        move.w  vRl(a5),d1
        addi.l  #500,d1
        cmp.l   d1,d0
        bls   .x
        lea     t_wfin(pc),a0
        bra     msg
.x:     rts
.e0:    lea     t_eobj0(pc),a0
        bra     msg
.nb:    lea     t_ebart0(pc),a0
        bra     msg
.gap:   lea     t_egap(pc),a0
        bra     msg

; ---------------------------------------------------------------- checks
; check_all: every message of the check page (vChk / vChkK / vChkN), blocking errors counted in vChkE; also encodes the block (vEncLen)
; codes: 1 no BAR 2 several BARs 3 hill overflow 4 block too big 5 value outside the original range (flagged, does not block) 10 W-DENS 11 W-HILL 12 W-CURVE 13 W-FINISH
check_all:
        movem.l d1-d7/a0-a3,-(a7)
        clr.w   vChkN(a5)
        clr.w   vChkE(a5)
        move.w  vNBar(a5),d0
        cmpi.w  #1,d0
        beq   .b1
        moveq   #1,d1
        lea     t_ebar0(pc),a0
        tst.w   d0
        beq   .be
        lea     vChkT(a5),a1
        bsr     apdn
        lea     t_ebarn(pc),a0
        bsr     apps
        clr.b   (a1)
        lea     vChkT(a5),a0
        moveq   #2,d1
.be:    bsr     chk_add
.b1:    bsr     hill_ovf
        tst.w   d0
        beq   .h1
        lea     t_ehill(pc),a0
        moveq   #3,d1
        bsr     chk_add
.h1:    bsr     encode
        cmpi.l  #8192,d0
        bls   .s1
        lea     t_esize(pc),a0
        moveq   #4,d1
        bsr     chk_add
.s1:    bsr     range_chk
        tst.w   d0
        beq   .r1
        lea     t_erange(pc),a0
        moveq   #5,d1
        bsr     chk_add
.r1:    bsr     dens_chk
        tst.w   d0
        beq   .w1
        lea     t_wdens(pc),a0
        moveq   #10,d1
        bsr     chk_add
.w1:    lea     HARR.l,a0               ; W-HILL: the height sits at the top for more than 300 race units
        moveq   #0,d2
        move.w  vRl(a5),d1
        subq.w  #1,d1
.hl:    cmpi.b  #127,(a0)+
        bcs   .hn
        addq.w  #1,d2
.hn:    dbra    d1,.hl
        cmpi.w  #300,d2
        bls   .w2
        lea     t_whill(pc),a0
        moveq   #11,d1
        bsr     chk_add
.w2:    lea     SEGT.l,a0               ; W-CURVE: the curve value leaves -4473..8876 (a segment's extremes are its ends)
        moveq   #0,d2                   ; c
        moveq   #0,d4                   ; min
        moveq   #0,d5                   ; max
        move.w  vNSeg(a5),d1
        subq.w  #1,d1
.cl:    move.w  4(a0),d0
        ext.l   d0
        moveq   #0,d3
        move.w  2(a0),d3
        lsr.w   #1,d3
        muls    d3,d0
        add.l   d0,d0
        add.l   d0,d2
        cmp.l   d4,d2
        bge   .c1
        move.l  d2,d4
.c1:    cmp.l   d5,d2
        ble   .c2
        move.l  d2,d5
.c2:    lea     SEGSZ(a0),a0
        dbra    d1,.cl
        cmpi.l  #-4473,d4
        blt   .cw
        cmpi.l  #8876,d5
        ble   .w3
.cw:    lea     t_wcurve(pc),a0
        moveq   #12,d1
        bsr     chk_add
.w3:    move.l  vBarAt(a5),d0           ; W-FINISH
        bmi   .x
        moveq   #0,d1
        move.w  vRl(a5),d1
        addi.l  #500,d1
        cmp.l   d1,d0
        bls   .x
        lea     t_wfin(pc),a0
        moveq   #13,d1
        bsr     chk_add
.x:     movem.l (a7)+,d1-d7/a0-a3
        rts
chk_add:                                ; a0 = text, d1 = code
        movem.l d2-d3/a1,-(a7)
        move.w  vChkN(a5),d2
        cmpi.w  #8,d2
        bcc   .x
        move.w  d2,d3
        lsl.w   #2,d3
        lea     vChk(a5),a1
        move.l  a0,(a1,d3.w)
        add.w   d2,d2
        lea     vChkK(a5),a1
        move.w  d1,(a1,d2.w)
        addq.w  #1,vChkN(a5)
        cmpi.w  #5,d1
        bcc   .x
        addq.w  #1,vChkE(a5)
.x:     movem.l (a7)+,d2-d3/a1
        rts
range_chk:                              ; d0 = 1 when a value is outside the stock envelope (curve -9..10, hill -6000..4000, widths 10..85)
        movem.l d1-d2/a0,-(a7)
        lea     SEGT.l,a0
        move.w  vNSeg(a5),d1
        subq.w  #1,d1
.l:     move.w  4(a0),d2
        cmpi.w  #-9,d2
        blt   .bad
        cmpi.w  #10,d2
        bgt   .bad
        move.w  6(a0),d2
        cmpi.w  #-6000,d2
        blt   .bad
        cmpi.w  #4000,d2
        bgt   .bad
        moveq   #0,d2
        move.b  8(a0),d2
        cmpi.w  #10,d2
        blt   .bad
        cmpi.w  #85,d2
        bgt   .bad
        move.b  9(a0),d2
        cmpi.w  #10,d2
        blt   .bad
        cmpi.w  #85,d2
        bgt   .bad
        lea     SEGSZ(a0),a0
        dbra    d1,.l
        moveq   #0,d0
        bra   .x
.bad:   moveq   #1,d0
.x:     movem.l (a7)+,d1-d2/a0
        rts
dens_chk:                               ; d0 = 1 when 32 or more objects lie within 888 units (the game has 32 scenery slots)
        movem.l d1-d4/a0-a1,-(a7)
        lea     OBJT.l,a0
        lea     OBJT.l,a1
        moveq   #0,d1
        moveq   #0,d2
        move.w  vNObj(a5),d4
        beq   .n
.l:     move.w  (a0),d3
        sub.w   (a1),d3
        cmpi.w  #888,d3
        bcs   .w
        addq.l  #8,a1
        addq.w  #1,d2
        bra   .l
.w:     move.w  d1,d3
        sub.w   d2,d3
        addq.w  #1,d3
        cmpi.w  #32,d3
        bcc   .yes
        addq.l  #8,a0
        addq.w  #1,d1
        cmp.w   d4,d1
        bcs   .l
.n:     moveq   #0,d0
        bra   .x
.yes:   moveq   #1,d0
.x:     movem.l (a7)+,d1-d4/a0-a1
        rts
c_check:                                ; K: the check page
        bsr     check_all
        move.w  #3,vState(a5)
        bsr     cls
        lea     t_chk(pc),a0
        moveq   #1,d0
        moveq   #1,d1
        moveq   #8,d2
        bsr     ptext
        bsr     lbeg
        moveq   #0,d0
        move.w  vNSeg(a5),d0
        moveq   #4,d1
        bsr     appn
        lea     t_csegs(pc),a0
        bsr     apps
        moveq   #0,d0
        move.w  vNObj(a5),d0
        moveq   #3,d1
        bsr     appn
        lea     t_cobjs(pc),a0
        bsr     apps
        move.l  vEncLen(a5),d0
        moveq   #4,d1
        bsr     appn
        lea     t_cbytes(pc),a0
        bsr     apps
        moveq   #3,d1
        moveq   #7,d2
        bsr     lend
        moveq   #5,d6
        moveq   #0,d7
.m:     cmp.w   vChkN(a5),d7
        bcc   .md
        move.w  d7,d0
        lsl.w   #2,d0
        lea     vChk(a5),a1
        movea.l (a1,d0.w),a0
        move.w  d7,d0
        add.w   d0,d0
        lea     vChkK(a5),a1
        moveq   #6,d2
        cmpi.w  #10,(a1,d0.w)
        bcs   .p
        moveq   #8,d2
.p:     moveq   #1,d0
        move.w  d6,d1
        bsr     ptext
        addq.w  #1,d6
        addq.w  #1,d7
        bra   .m
.md:    tst.w   vChkN(a5)
        bne   .k
        lea     t_cok(pc),a0
        moveq   #1,d0
        moveq   #5,d1
        moveq   #3,d2
        bsr     ptext
.k:     lea     t_pak(pc),a0
        moveq   #1,d0
        moveq   #24,d1
        moveq   #1,d2
        bsr     ptext
        clr.b   $60ff.w
.w:     jsr     $d206.l
        bsr     kq_pop
        tst.b   d0
        bne   .d
        btst    #7,$6105.w
        beq   .w
.d:     move.w  #1,vState(a5)
        bsr     in_reset
        move.w  #1,vRedraw(a5)
        rts

; ---------------------------------------------------------------- the working copy -> a native track block (the same six streams and the same bytes tools/msrtrack.py encodes) in ENCBUF -> d0.l = its length
encode: movem.l d1-d7/a0-a4,-(a7)
        lea     ENCBUF.l,a1
        lea     enc_tab(pc),a3
        moveq   #3,d7
.st:    move.w  (a3)+,d5                ; field offset in the segment
        move.w  (a3)+,d6                ; 0 word, 1 byte
        lea     SEGT.l,a0
        move.w  vNSeg(a5),d4
        subq.w  #1,d4
        moveq   #0,d2                   ; run length (0 = no run yet)
        moveq   #0,d3                   ; run value
.sg:    tst.w   d6
        bne   .by
        move.w  (a0,d5.w),d0
        bra   .gv
.by:    moveq   #0,d0
        move.b  (a0,d5.w),d0
.gv:    moveq   #0,d1
        move.w  2(a0),d1
        tst.l   d2
        beq   .new
        cmp.w   d3,d0
        bne   .fl
        add.l   d1,d2
        bra   .nx
.fl:    move.w  d2,(a1)+
        move.w  d3,(a1)+
.new:   move.l  d1,d2
        move.w  d0,d3
.nx:    lea     SEGSZ(a0),a0
        dbra    d4,.sg
        move.w  d2,(a1)+
        move.w  d3,(a1)+
        clr.w   (a1)+
        dbra    d7,.st
        lea     OBJT.l,a0               ; objects: first position, then (type, lateral, gap to the next; 0 = the last)
        move.w  vNObj(a5),d4
        subq.w  #1,d4
        move.w  (a0),(a1)+
.ob:    move.w  2(a0),(a1)+
        move.w  4(a0),(a1)+
        tst.w   d4
        beq   .last
        move.w  8(a0),d0
        sub.w   (a0),d0
        move.w  d0,(a1)+
        bra   .on
.last:  clr.w   (a1)+
.on:    addq.l  #8,a0
        dbra    d4,.ob
        lea     TYPS.l,a0               ; the type table of the base level, unchanged, and the end word
        move.w  vTypLen(a5),d0
        lsr.w   #1,d0
        subq.w  #1,d0
.tc:    move.w  (a0)+,(a1)+
        dbra    d0,.tc
        move.l  a1,d0
        subi.l  #ENCBUF,d0
        move.l  d0,vEncLen(a5)
        movem.l (a7)+,d1-d7/a0-a4
        rts

; ---------------------------------------------------------------- leaving the map: the track is kept (the campaign file in memory is updated)
leave:  tst.w   vSrc(a5)
        bne   .chk
        tst.w   vMod(a5)
        beq   .go                       ; a campaign track nobody changed
.chk:   bsr     check_all
        tst.w   vChkE(a5)
        beq   .ok
        tst.w   vLeaveW(a5)
        bne   .go                       ; the second Esc discards the track
        move.w  #1,vLeaveW(a5)
        moveq   #0,d0
        move.w  vChkK(a5),d0
        lsl.w   #2,d0
        lea     keepmsg(pc),a0
        movea.l -4(a0,d0.w),a0
        bra     msg
.ok:    moveq   #1,d6
        tst.w   vSrc(a5)
        bne   .st
        moveq   #0,d6
        move.w  vSrcIx(a5),d7
.st:    cmpi.w  #1,d6
        bne   .do
        tst.b   CPV+1.l
        beq   .do
        cmpi.w  #15,CPV+2.l
        bcs   .do
        lea     t_efull(pc),a0
        bra     msg
.do:    bsr     store_rebuild
        lea     t_kept(pc),a0
        move.l  a0,vMsg(a5)
.go:    move.w  #1,vRes(a5)
        rts

; store_rebuild: the campaign file in CPSTORE is rebuilt (offsets, lengths, block CRCs, table CRC, count) with the working copy's block (ENCBUF, vEncLen, vName, vBase) replacing entry d7 (d6 = 0),
; appended (d6 = 1) or entry d7 removed (d6 = 2).  The new file is made in ARENA (the undo history is dead by now) and copied back: the store is always a valid MSTRACKS.TRK.
store_rebuild:
        movem.l d1-d7/a0-a4,-(a7)
        moveq   #0,d4
        tst.b   CPV+1.l
        beq   .n0
        move.w  CPV+2.l,d4              ; entries now
.n0:    move.w  d4,d5                   ; entries after
        tst.w   d6
        beq   .nc
        cmpi.w  #1,d6
        bne   .dl
        addq.w  #1,d5
        bra   .nc
.dl:    subq.w  #1,d5
.nc:    lea     ARENA.l,a2
        move.w  d5,d0
        mulu    #40,d0
        addi.l  #16,d0
        move.l  d0,d3                   ; offset of the next block
        lea     16(a2),a3               ; next table entry
        moveq   #0,d2                   ; entry counter
.e:     cmp.w   d5,d2
        bcc   .done
        cmpi.w  #1,d6
        beq   .ap
        tst.w   d6
        beq   .rp
        move.w  d2,d1                   ; delete: skip the removed entry
        cmp.w   d7,d2
        bcs   .old
        addq.w  #1,d1
        bra   .old
.rp:    move.w  d2,d1
        cmp.w   d7,d2
        bne   .old
        bra   .new
.ap:    move.w  d2,d1
        cmp.w   d4,d2
        beq   .new
.old:   move.w  d1,d0
        mulu    #40,d0
        lea     CPSTORE+16.l,a4
        adda.l  d0,a4
        movea.l a3,a0
        movea.l a4,a1
        moveq   #9,d0
.oc:    move.l  (a1)+,(a0)+
        dbra    d0,.oc
        move.l  28(a4),d0
        lea     CPSTORE.l,a1
        adda.l  d0,a1
        move.l  32(a4),d1
        bra   .blk
.new:   movea.l a3,a0
        moveq   #5,d0
.z:     clr.l   (a0)+
        dbra    d0,.z
        lea     vName(a5),a1
        movea.l a3,a0
        moveq   #23,d0
.nl:    move.b  (a1)+,d1
        beq   .nn
        move.b  d1,(a0)+
        dbra    d0,.nl
.nn:    move.w  vBase(a5),24(a3)
        clr.w   26(a3)
        lea     ENCBUF.l,a1
        move.l  vEncLen(a5),d1
        move.l  a1,-(a7)
        moveq   #-1,d0
        bsr     crc
        not.l   d0
        move.l  d0,36(a3)
        movea.l (a7)+,a1
.blk:   move.l  d3,28(a3)
        move.l  d1,32(a3)
        lea     (a2,d3.l),a0
        move.l  d1,d0
        bsr     cpyw
        add.l   d1,d3
        lea     40(a3),a3
        addq.w  #1,d2
        bra   .e
.done:  move.l  #'MSTK',(a2)
        move.w  #1,4(a2)
        move.w  d5,6(a2)
        move.l  d3,8(a2)
        moveq   #-1,d0
        movea.l a2,a1
        moveq   #12,d1
        bsr     crc
        lea     16(a2),a1
        moveq   #0,d1
        move.w  d5,d1
        mulu    #40,d1
        bsr     crc
        not.l   d0
        move.l  d0,12(a2)
        lea     CPSTORE.l,a0
        movea.l a2,a1
        move.l  d3,d0
        bsr     cpyw
        move.w  d5,CPV+2.l
        st      CPV+1.l
        movem.l (a7)+,d1-d7/a0-a4
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
        moveq   #23,d1                  ; (row 22 is the 20th item of the longest menu)
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
        bsr     kq_pop
        tst.b   d0
        beq   .joy
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
        ; a campaign track: EDIT / PLAY / DELETE / BACK
        move.w  d0,vSrcIx(a5)
        lea     m_trk(pc),a0
        bsr     list_fixed
        lea     t_trkh(pc),a0
        moveq   #0,d0
        bsr     pick
        tst.w   d0
        bmi     .again
        beq   .edit
        cmpi.w  #1,d0
        beq   .play
        cmpi.w  #2,d0
        bne     .again
        bra     .delete
.edit:  clr.w   vSrc(a5)
        moveq   #0,d0
        move.w  vSrcIx(a5),d0
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
.play:  moveq   #0,d0                   ; PLAY THIS TRACK: leave the editor, the menu starts the race on this track of the campaign in memory
        move.w  vSrcIx(a5),d0
        addq.w  #1,d0
        rts
.delete: cmpi.w #1,d6
        bhi   .dl1
        lea     t_elastt(pc),a0
        move.l  a0,vMsg(a5)
        bra     .again
.dl1:   lea     m_del(pc),a0
        bsr     list_fixed
        lea     t_delh(pc),a0
        moveq   #0,d0
        bsr     pick
        cmpi.w  #1,d0
        bne     .again
        moveq   #2,d6
        moveq   #0,d7
        move.w  vSrcIx(a5),d7
        bsr     store_rebuild
        lea     t_deleted(pc),a0
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

; ======================================================================================================= milestone 3: TEST DRIVE FROM THE CURSOR (design: work/notes/editor_design.md 13)
; c_td (key P / menu): the working copy is encoded into ENCBUF and the game's own race routine ($76f4: setup, loop and exit in one subroutine) is CALLED from here, started at the cursor unit; the race's end (the BAR, the time,
; the crashes, F10, Esc) is its `rts`.  cp_fetch's hookb sees V_TD (CPV+14) and leaves PTR (= ENCBUF) alone; cp_td's hook at the end of the setup calls td_ff.  No shop, no campaign advance, no hi-score.
c_td:   movem.l d1-d7/a0-a6,-(a7)
        cmpi.w  #$4eb9,$7926.w          ; cp_td's `jsr hooktd.l` is at the end of the race setup (without it the drive would start at unit 0)
        bne   .nopatch
        cmpi.l  #$b8260,$7928.w
        bne   .nopatch
        move.l  vPos(a5),d0
        move.l  vBarAt(a5),d1
        bmi   .go
        cmp.l   d1,d0
        bhi   .behind                   ; the BAR would lie behind the camera: no finish possible
.go:    move.w  d0,vTdN(a5)
        bsr     encode                  ; the block as it is now, kept or not (ENCBUF)
        bsr     in_reset                ; no key, fire released
        move.w  sr,-(a7)                ; the game's IKBD handler alone (the race reads $60ff itself); the editor's hook comes back afterwards
        ori.w   #$700,sr
        move.l  vOldKb(a5),$118.w
        move.w  (a7)+,sr
        move.w  $102c.w,vTd102c(a5)     ; what the title / the menu expect after the race
        move.b  $1021.w,vTd1021(a5)
        move.b  $1020.w,vTd1020(a5)
        move.b  $1027.w,vTd1027(a5)
        move.l  $1004.w,vTdScrA(a5)
        move.l  $1008.w,vTdScrB(a5)
        clr.l   vTdOldV(a5)
        clr.b   vTdWhy(a5)
        clr.b   vTdKill(a5)
        move.w  vBase(a5),d0            ; the preparations of the campaign loop ($726c-$72c0) and of cp_wrap: $102c = the BASE level
        move.w  d0,$102c.w
        moveq   #0,d1                   ; $1029 = the world tier of the map screens ($7282-$72b4), read by the race ($112c8)
        cmpi.w  #5,d0
        bcs   .tier
        moveq   #1,d1
        cmpi.w  #10,d0
        bcs   .tier
        moveq   #2,d1
.tier:  move.b  d1,$1029.w
        clr.b   $1026.w                 ; crashes of this race
        move.b  $1023.w,$1021.w         ; sound mode of the race
        st      $1020.w
        move.l  #ENCBUF,CPV+8.l         ; PTR (cp_ptr: the stream setup reads the block here)
        st      CPV+14.l                ; V_TD
        st      $1028.w                 ; race flag (the extra-frame patches look at it)
        jsr     $d866.l                 ; the editor's screen fades to black with the game's own fade
.f1:    tst.w   $3a88.w
        bne   .f1
        jsr     $76f4.l                 ; the race
        lea     V.l,a5
        move.b  $1024.w,vTdRes(a5)
        move.b  $1226.w,vTdRes2(a5)
        move.w  $5ff8.w,vTdLast(a5)
        move.w  sr,-(a7)
        ori.w   #$700,sr
        tst.l   vTdOldV(a5)             ; td_ff put its wrappers in: take them out
        beq   .nh
        move.l  vTdOldV(a5),$70.w
        move.l  vTdOldK(a5),$118.w
        clr.l   vTdOldV(a5)
.nh:    move.w  (a7)+,sr
        clr.b   $6042.w                 ; the F10 hold byte the race loop reads (set by F10, or by tdkb / tdvbl)
        clr.b   $60ff.w
        clr.b   CPV+14.l
        clr.w   $91f0.l                 ; the campaign loop's clean-up after the race ($72ca-$72e4)
        clr.b   $1028.w
        jsr     $d82c.l
.f2:    tst.w   $3a88.w
        bne   .f2
        clr.b   $3d2e.w
        jsr     $d770.l                 ; sound player reset
        lea     V.l,a5
        move.w  vTd102c(a5),$102c.w
        move.b  vTd1021(a5),$1021.w
        move.b  vTd1020(a5),$1020.w
        move.b  vTd1027(a5),$1027.w
        move.l  vTdScrA(a5),$1004.w
        move.l  vTdScrB(a5),$1008.w
        jsr     $d206.l                 ; the editor's screen and palette back
        move.l  vShow(a5),d0
        lsr.l   #8,d0
        move.b  d0,$ffff8203.w
        lsr.w   #8,d0
        move.b  d0,$ffff8201.w
        lea     pal(pc),a0
        lea     $ffff8240.w,a1
        moveq   #15,d0
.p:     move.w  (a0)+,(a1)+
        dbra    d0,.p
        move.w  sr,-(a7)
        ori.w   #$700,sr
        clr.l   vKqH(a5)                ; vKqH / vKqT: nothing typed during the race is kept
        move.w  (a7)+,sr
        bsr     kb_hook
        bsr     in_reset
        move.w  #1,vRedraw(a5)
        lea     t_tdover(pc),a0
        bsr     msg
        bra   .x
.nopatch: lea   t_tdnopatch(pc),a0
        bra   .m
.behind: lea    t_tdbehind(pc),a0
.m:     bsr     msg
.x:     movem.l (a7)+,d1-d7/a0-a6
        rts

; td_ff: called by cp_td (`jsr EDBASE+20`) at the end of the race setup of a test drive, when the rings, the objects, the opponents and the race state stand at unit 0.  Fast-forward to the cursor unit N with the game's own
; updaters, set the distance, the speech pointer and the time bar, put the test drive's two wrappers in.
td_ff:  movem.l d0-d7/a0-a6,-(a7)
        addq.w  #1,V+vTdHit.l           ; (the game's updaters below use every register: the counters live in memory)
        clr.b   $C0008.l                ; rd_geom's standing-frame reuse off (trackloader.md 6)
        move.w  V+vTdN.l,V+vTdRem.l     ; units still to go
        beq   .nff
.ch:    move.w  V+vTdRem.l,d0
        cmpi.w  #1023,d0                ; the ring updaters take at most 1023 steps per call
        bls   .c1
        move.w  #1023,d0
.c1:    move.w  d0,$130c.w
        sub.w   d0,V+vTdRem.l
        jsr     $e2e8.l                 ; objects: the ones passed are freed (BEFORE the spawner: the race loop spawns first, which is exact for steps of 10 only)
        jsr     $e218.l                 ; objects: spawn what entered the 1023-unit window
        jsr     $fe50.l                 ; left / right width rings
        jsr     $ff76.l                 ; curve ring
        jsr     $1003c.l                ; hill ring
        tst.w   V+vTdRem.l
        bne   .ch
        clr.w   $130c.w
.nff:   lea     V.l,a5
        moveq   #0,d7
        move.w  vTdN(a5),d7             ; N
        move.w  d7,$5ff8.w              ; the distance
        movea.w $12a4.w,a0              ; speech: the entries (distance + $320) below N are over
.sp:    move.w  (a0),d0
        beq   .spd
        subi.w  #$320,d0
        cmp.w   d7,d0
        bcc   .spd
        addq.l  #4,a0
        bra   .sp
.spd:   move.w  a0,$12a4.w
        move.l  vBarAt(a5),d0           ; the time bar: 2 x (the distance left to the chase start at full speed) + 10 s, never more than the stock bar; the rate $10d2 stays the base level's
        bmi   .tb
        subi.l  #500,d0
        sub.l   d7,d0
        bpl   .r1
        moveq   #0,d0
.r1:    divu    #10,d0                  ; passes at 10 units per pass
        andi.l  #$ffff,d0
        add.l   d0,d0
        addi.l  #100,d0                 ; + 100 passes (10 s)
        moveq   #0,d1
        move.w  $10d2.w,d1
        mulu    d1,d0                   ; passes x rate (<= 6654 x 65535)
        move.l  #$ff0000,d2
        sub.l   d0,d2
        bpl   .t1
        moveq   #0,d2
.t1:    move.l  d2,$10ce.w
.tb:    clr.w   vTdCnt(a5)
        move.w  sr,-(a7)                ; the wrappers go in now: every $d6fa call of the setup swaps the vectors through HAGA's TOS window
        ori.w   #$700,sr
        move.l  $70.w,vTdOldV(a5)
        move.l  $118.w,vTdOldK(a5)
        move.l  #tdvbl,$70.w
        move.l  #tdkb,$118.w
        move.w  (a7)+,sr
        movem.l (a7)+,d0-d7/a0-a6
        rts

; tdkb: IKBD wrapper of the race: the game's handler, then Esc (make code 1 in $60ff) AND F10 (make $44) are turned into the F10 hold byte the race loop aborts on ($7970): the race loop polls it once per pass (10 per second), so
; a quick tap of the real F10 (held byte set and cleared between two polls) would be missed; here the byte stays set until the editor clears it after the race
tdkb:   pea     .back(pc)
        move.w  sr,-(a7)
        move.l  V+vTdOldK.l,-(a7)
        rts                             ; = jmp to the game's handler, whose rte returns to .back
.back:  cmpi.b  #1,$60ff.w
        beq   .k
        cmpi.b  #$44,$60ff.w
        bne   .c
.k:     clr.b   $60ff.w
        st      V+vTdKill.l
.c:     tst.b   V+vTdKill.l             ; asserted again after every IKBD byte: the break code of F10 clears the held byte
        beq   .x
        st      $6042.w
.x:     rte

; tdvbl: VBL wrapper of the race: the game's handler, then, once the race is decided (the finish: $1024 >= 2; the time-out message: $1226 = 5) and 75 frames (1.5 s) have passed, the same F10 byte ends the race: the stop at
; the BAR / the time-out text stay visible, the closing message sequence, score count and place text of a real race are skipped
tdvbl:  pea     .back(pc)
        move.w  sr,-(a7)
        move.l  V+vTdOldV.l,-(a7)
        rts
.back:  tst.b   $1024.w                 ; no register is touched: this runs in the middle of the interrupted code
        beq   .t
        cmpi.b  #2,$1024.w
        bcs   .x                        ; 1 = the car is being driven into the BAR
        cmpi.b  #3,$1024.w
        bhi   .t                        ; $ff (over): only a time-out is still told apart
        tst.w   V+vTdCnt.l              ; 2 / 3: the BAR is reached
        bne   .c
        move.b  #1,V+vTdWhy.l
        bra   .c
.t:     cmpi.b  #5,$1226.w
        bcs   .x
        tst.w   V+vTdCnt.l              ; the time-out message
        bne   .c
        move.b  #2,V+vTdWhy.l
.c:     addq.w  #1,V+vTdCnt.l
        cmpi.w  #75,V+vTdCnt.l
        bcs   .x
        st      $6042.w
.x:     rte

; ---------------------------------------------------------------- tables and texts
pal:    dc.w    $000,$444,$567,$070,$057,$740,$700,$777,$770,$777,$777,$777,$777,$777,$777,$777
rltab:  dc.w    19472,19720,19800,19000,19375,18000,18626,20000,19000,20000,20000,22000,18500,22000,23000   ; race length of the 15 levels (word 0 of the minimap header, tools/msrtrack.py LEVELS)
keytab: dc.b    $01,1,$44,1             ; Esc, F10: leave (the track is kept)
        dc.b    $47,2                   ; Clr/Home: start
        dc.b    $30,3                   ; B: the BAR (Shift + B: put the BAR here)
        dc.b    $4e,4,$0d,4             ; keypad +, =/+: zoom in
        dc.b    $4a,5,$0c,5             ; keypad -, -: zoom out
        dc.b    $0f,6                   ; Tab: road <> objects
        dc.b    $62,7,$3b,7             ; Help, F1
        dc.b    $1c,9,$72,9,$39,9       ; Return, Enter, Space: repeat the last pick at the cursor
        dc.b    $2e,10                  ; C curve
        dc.b    $23,11                  ; H hill
        dc.b    $26,12                  ; L length
        dc.b    $11,13,$12,14           ; W E widths
        dc.b    $17,15,$52,15           ; I, Insert
        dc.b    $1f,16                  ; S
        dc.b    $53,17                  ; Delete
        dc.b    $14,18                  ; T
        dc.b    $16,20,$61,20           ; U, Undo (Shift: redo)
        dc.b    $25,22                  ; K check
        dc.b    $32,23                  ; M
        dc.b    $33,24,$34,25           ; , . bend left / right
        dc.b    $19,26                  ; P test drive from the cursor
        dc.b    0
vmroad: dc.b    10,11,12,13,14,15,16,23,17,19,20,21,22,26,4,5,6,7,0,1
vmobj:  dc.b    18,16,23,15,17,19,20,21,22,26,4,5,6,7,0,1
        even
enc_tab: dc.w   4,0, 8,1, 9,1, 6,0      ; the four ring streams: curve, left width, right width, hill = field offset in the segment, 1 = byte
cv_tab: dc.w    4,2, 0,0, 2,2, 8,1, 9,1, 2,2, 4,2, 6,2   ; current value per act: offset, 0 none / 1 byte / 2 word
hh_tab: dc.w    8,20,40                 ; heights of the hill shapes small / medium / big
ad_tab: dc.w    0,-9,20,0,-9,10         ; per act: kind (0 strings 1 numbers 2 types), bias, items, adjustable, min, max, texts, heading
        dc.l    l_curve,h_curve
        dc.w    0,0,14,0,0,13
        dc.l    l_hill,h_hill
        dc.w    1,0,15,1,1,32767
        dc.l    n_len,h_len
        dc.w    1,0,16,1,0,255
        dc.l    n_wid,h_wl
        dc.w    1,0,16,1,0,255
        dc.l    n_wid,h_wr
        dc.w    2,0,0,0,1,999
        dc.l    0,h_type
        dc.w    1,0,9,1,-200,200
        dc.l    n_side,h_side
        dc.w    1,0,14,1,-9999,9999
        dc.l    n_acc,h_acc
keepmsg: dc.l   k_bar0,k_barn,k_hill,k_size
n_len:  dc.w    10,20,30,50,75,100,150,200,300,400,600,800,1000,1500,2000
n_wid:  dc.w    10,15,20,25,30,35,40,45,50,55,60,65,70,75,80,85
n_side: dc.w    -120,-80,-50,-25,0,25,50,80,120
n_acc:  dc.w    -3000,-1500,-800,-400,-200,-100,0,100,200,400,800,1500,3000,4000
l_curve: dc.b   "LEFT 9",0,"LEFT 8",0,"LEFT 7",0,"LEFT 6",0,"LEFT 5",0,"LEFT 4",0,"LEFT 3",0,"LEFT 2",0,"LEFT 1",0,"STRAIGHT",0
        dc.b    "RIGHT 1",0,"RIGHT 2",0,"RIGHT 3",0,"RIGHT 4",0,"RIGHT 5",0,"RIGHT 6",0,"RIGHT 7",0,"RIGHT 8",0,"RIGHT 9",0,"RIGHT 10",0
l_hill: dc.b    "FLAT",0,"RISE SMALL",0,"RISE MEDIUM",0,"RISE BIG",0,"DROP SMALL",0,"DROP MEDIUM",0,"DROP BIG",0
        dc.b    "CREST SMALL",0,"CREST MEDIUM",0,"CREST BIG",0,"DIP SMALL",0,"DIP MEDIUM",0,"DIP BIG",0,"RAW ACCEL...",0
h_curve: dc.b   "CURVE",0
h_hill: dc.b    "HILL",0
h_len:  dc.b    "LENGTH",0
h_wl:   dc.b    "WIDTH L",0
h_wr:   dc.b    "WIDTH R",0
h_type: dc.b    "OBJECT TYPE (THIS BASE LEVEL'S OWN)",0
h_side: dc.b    "SIDE",0
h_acc:  dc.b    "ACCEL",0
m_trk:  dc.b    "EDIT THIS TRACK",0,"PLAY THIS TRACK",0,"DELETE THIS TRACK",0,"< BACK",0,0
m_del:  dc.b    "NO, KEEP IT",0,"YES, DELETE IT",0,0
t_trkh: dc.b    "THIS TRACK:",0
t_delh: dc.b    "REALLY DELETE THE TRACK?",0
t_elastt: dc.b  "A CAMPAIGN NEEDS AT LEAST ONE TRACK",0
t_deleted: dc.b "TRACK DELETED FROM THE CAMPAIGN",0
m_road:
        dc.b    "CURVE...                           C",0
        dc.b    "HILL...                            H",0
        dc.b    "LENGTH...                          L",0
        dc.b    "WIDTH LEFT...                      W",0
        dc.b    "WIDTH RIGHT...                     E",0
        dc.b    "INSERT A COPY BEHIND               I",0
        dc.b    "SPLIT AT THE CURSOR                S",0
        dc.b    "MERGE WITH THE NEXT                M",0
        dc.b    "DELETE THIS SEGMENT              DEL",0
        dc.b    "PUT THE BAR HERE             SHIFT B",0
        dc.b    "UNDO                               U",0
        dc.b    "REDO                         SHIFT U",0
        dc.b    "CHECK THE TRACK                    K",0
        dc.b    "TEST DRIVE FROM THE CURSOR         P",0
        dc.b    "ZOOM IN                            +",0
        dc.b    "ZOOM OUT                           -",0
        dc.b    "ROAD <> OBJECTS                  TAB",0
        dc.b    "KEYS                            HELP",0
        dc.b    "< BACK TO THE MAP",0
        dc.b    "LEAVE AND KEEP THIS TRACK         F10",0,0
m_obj:
        dc.b    "TYPE...                            T",0
        dc.b    "SIDE...                            S",0
        dc.b    "MOVE THIS OBJECT                   M",0
        dc.b    "ADD AN OBJECT HERE                 I",0
        dc.b    "DELETE THIS OBJECT               DEL",0
        dc.b    "PUT THE BAR HERE             SHIFT B",0
        dc.b    "UNDO                               U",0
        dc.b    "REDO                         SHIFT U",0
        dc.b    "CHECK THE TRACK                    K",0
        dc.b    "TEST DRIVE FROM THE CURSOR         P",0
        dc.b    "ZOOM IN                            +",0
        dc.b    "ZOOM OUT                           -",0
        dc.b    "ROAD <> OBJECTS                  TAB",0
        dc.b    "KEYS                            HELP",0
        dc.b    "< BACK TO THE MAP",0
        dc.b    "LEAVE AND KEEP THIS TRACK         F10",0,0
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
t_hint: dc.b    "L/R MOVE  U/D ROAD/OBJ  FIRE=MENU  HELP",0
t_hdisc: dc.b   "ESC AGAIN = DISCARD THIS TRACK   K=CHECK",0
t_hmove: dc.b   "MOVING: L/R  FIRE=OK  ESC=CANCEL",0
t_lhsel: dc.b   "UP/DOWN PICK  FIRE/RETURN=OK  ESC=BACK",0
t_lhadj: dc.b   "U/D PICK  L/R +-1 (FIRE 10)  FIRE=OK",0
t_nound: dc.b   "NOTHING TO UNDO",0
t_noredo: dc.b  "NOTHING TO REDO",0
t_norep: dc.b   "NOTHING TO REPEAT: PICK A VALUE FIRST",0
t_wrongrow: dc.b "THAT VALUE IS FOR THE OTHER ROW (TAB)",0
t_roadrow: dc.b "ROAD ROW ONLY: PRESS TAB FIRST",0
t_objrow: dc.b  "OBJECTS ROW ONLY: PRESS TAB FIRST",0
t_climit: dc.b  "THE SHARPEST CURVE ALREADY",0
t_elast: dc.b   "THE LAST SEGMENT IS THE PADDING (E-SUM)",0
t_eroom: dc.b   "NO ROAD LEFT: LENGTH IS FIXED (E-SUM)",0
t_eobjend: dc.b "OBJECTS WOULD PASS THE END OF THE ROAD",0
t_erange: dc.b  "OUTSIDE THE ORIGINAL RANGE (E-RANGE)",0
t_ehill: dc.b   "HILL TOO STEEP: OVERFLOW (E-HILL)",0
t_ebart: dc.b   "THE BAR'S TYPE CANNOT CHANGE (E-BAR)",0
t_elat: dc.b    "SIDE MUST BE -128..127 (E-LAT)",0
t_eshort: dc.b  "SEGMENT TOO SHORT FOR THAT SHAPE",0
t_efullseg: dc.b "TOO MANY SEGMENTS (2048)",0
t_efullobj: dc.b "TOO MANY OBJECTS (999)",0
t_esplit: dc.b  "FINE-MOVE THE CURSOR INSIDE THE SEGMENT",0
t_eobj0: dc.b   "NO OBJECT AT UNIT 0 (E-OBJ)",0
t_egap: dc.b    "AN OBJECT IS ALREADY HERE (E-GAP)",0
t_ebardel: dc.b "THE BAR CANNOT BE DELETED (E-BAR)",0
t_ebart0: dc.b  "THIS BASE LEVEL HAS NO BAR TYPE (E-BAR)",0
t_wdens: dc.b   "OVER 31 OBJECTS IN VIEW (W-DENS)",0
t_whill: dc.b   "HEIGHT STAYS AT THE TOP LONG (W-HILL)",0
t_wcurve: dc.b  "VERY LONG TURN (W-CURVE)",0
t_wfin: dc.b    "BAR IS FAR FOR THIS SCENERY (W-FINISH)",0
t_ebar0: dc.b   "THIS TRACK HAS NO BAR (E-BAR)",0
t_ebarn: dc.b   " BARS: ONLY THE FIRST COUNTS (E-BAR)",0
t_esize: dc.b   "TRACK FULL: 8192 BYTES (E-SIZE)",0
k_bar0: dc.b    "NO BAR (E-BAR). ESC AGAIN = DISCARD",0
k_barn: dc.b    "SEVERAL BARS (E-BAR). ESC AGAIN=DISCARD",0
k_hill: dc.b    "HILL OVERFLOW (E-HILL). ESC = DISCARD",0
k_size: dc.b    "TRACK FULL (E-SIZE). ESC AGAIN=DISCARD",0
t_efull: dc.b   "CAMPAIGN FULL: 15 TRACKS (E-CAMP)",0
t_kept: dc.b    "KEPT IN THE CAMPAIGN (NOT ON DISK YET)",0
t_chk:  dc.b    "TRACK CHECK",0
t_csegs: dc.b   " SEGMENTS  ",0
t_cobjs: dc.b   " OBJECTS  ",0
t_cbytes: dc.b  " BYTES OF 8192",0
t_cok:  dc.b    "NO PROBLEMS FOUND",0
t_pak:  dc.b    "PRESS A KEY",0
t_tk:   dc.b    " KIND ",0
t_ts:   dc.b    " SIZE ",0
t_tp:   dc.b    " SPRITE ",0
t_lhint: dc.b   "UP/DOWN + FIRE OR RETURN    ESC = BACK",0
t_nobar: dc.b   "THIS TRACK HAS NO BAR (E-BAR)",0
t_tdover: dc.b  "BACK FROM THE TEST DRIVE",0
t_tdbehind: dc.b "TEST DRIVE: THE CURSOR IS BEHIND THE BAR",0
t_tdnopatch: dc.b "TEST DRIVE NEEDS THE CP_TD PATCH",0
t_top:  dc.b    "TRACK EDITOR: CAMPAIGN TRACKS",0
t_top0: dc.b    "TRACK EDITOR: NO CAMPAIGN YET",0
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
t_help: dc.b    "TRACK EDITOR KEYS",0
        dc.b    " ",0
        dc.b    "L/R  PREVIOUS / NEXT SEGMENT (OBJECT)",0
        dc.b    "U/D, TAB  ROAD ROW <> OBJECTS ROW",0
        dc.b    "SHIFT+L/R 1000   CTRL+L/R ONE PIXEL",0
        dc.b    "+ / -  ZOOM    HOME  START   B  THE BAR",0
        dc.b    "FIRE  MENU   F10 / ESC  LEAVE (KEEPS)",0
        dc.b    " ",0
        dc.b    "C CURVE  , .  BEND LEFT / RIGHT",0
        dc.b    "H HILL  L LENGTH  W / E WIDTH L / R",0
        dc.b    "I INSERT A COPY / ADD AN OBJECT",0
        dc.b    "S SPLIT / OBJECT SIDE  M MERGE / MOVE",0
        dc.b    "DEL DELETE   T OBJECT TYPE",0
        dc.b    "SHIFT+B PUT THE BAR HERE",0
        dc.b    "U UNDO  SHIFT+U REDO  K CHECK",0
        dc.b    "RETURN / SPACE  REPEAT THE LAST PICK",0
        dc.b    "P TEST DRIVE FROM CURSOR (F10/ESC ENDS)",0
        dc.b    " ",0
        dc.b    "LISTS: UP/DOWN, FIRE / RETURN = OK",0
        dc.b    "L/R = EXACT VALUE (CTRL OR FIRE 10,",0
        dc.b    "SHIFT 100).  ESC = BACK, NOTHING CHANGES",0
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
