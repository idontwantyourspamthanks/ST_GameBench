; msedit.s - Moonshine Racers TRACK EDITOR overlay (FILES\MSEDIT.OVL).  Milestone 2: viewer + EDITING (in RAM; saving to disk is milestone 4).  Design: work/notes/editor_design.md (section 15: the tile grid of milestone 2c).
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
TILE    equ     EDWORK+$10000   ; tile word per segment: bits 0-2 direction class, 3-5 hill class, 6 an object, 7 the BAR, 15 no tile (the segment is beyond the race)
SHW     equ     EDWORK+$11000   ; 128 words: what each grid slot currently shows (tile word + bits 8/9 selection), so a redraw touches only changed tiles
SCR     equ     EDWORK+$30000   ; screen (32000 B)
ARENA   equ     EDWORK+$38000   ; undo history ($178000-$19FFFF); the campaign file is rebuilt here when a track is kept (history is dead by then)
ARENAE  equ     EDWORK+$60000
ENCBUF  equ     EDWORK+$70000   ; the encoded track block (64 KB)
MAXSEG  equ     2048
MAXOBJ  equ     999
SEGSZ   equ     12
GRIDX   equ     32              ; the grid: tile pitch 16 x 12, 16 x 8 tiles, x 32..287, y 8..103
GRIDY   equ     8
TILEW   equ     16
TILEH   equ     12

vScr    equ     0               ; b,b the game's video base (hi, mid)
vPal    equ     2               ; 16 w the game's palette
vNSeg   equ     34              ; w
vNObj   equ     36              ; w
vTotal  equ     38              ; l units covered by the four streams (<= 32768)
vEnd    equ     42              ; l the segment whose start lies at or past this is beyond the race (no tile, no cursor)
vRl     equ     46              ; w race length of the base level
vBase   equ     48              ; w base level 0..14
vBarT   equ     50              ; w the BAR's type (1-based), 0 = none in the type table
vBarAt  equ     52              ; l position of the BAR object, -1 = none
vNTypes equ     56              ; w
vNBar   equ     58              ; w number of BAR objects
vSeg    equ     60              ; w cursor: segment (the grid's cell)
vPos    equ     62              ; l cursor: the segment's first unit (the test drive starts here)
vObj    equ     66              ; w cursor: object (its index in OBJT) while the object list has the cursor
vFocus  equ     68              ; w 0 the grid, 1 the object list of the selected segment
vFirst  equ     70              ; w the segment of the top-left tile (a multiple of 16)
vTOk    equ     72              ; w the tile words in TILE are current
vOCnt   equ     74              ; w objects in the selected segment
vOF     equ     76              ; w first index of them in OBJT
vOTop   equ     78              ; w object list: first object shown in the panel
vPage   equ     80              ; w the key page (1 keys, 2 the legend)
vRedraw equ     88              ; w bit 0 everything, bit 1 the grid + panel only
vPDir   equ     90              ; w directions held at the previous poll
vRep    equ     92              ; w auto-repeat countdown
vRes    equ     94              ; w 1 = leave the editor
vState  equ     96              ; w 0 lists, 1 view, 2 menu, 3 help / check (read by the gate scripts)
vSrc    equ     98              ; w 0 campaign track, 1 stock track, 2 plain straight
vSrcIx  equ     100             ; w
vMsg    equ     102             ; l message for the hint row (0 = the key hints)
vFire   equ     106             ; w fire is held
vFireMv equ     108             ; w a direction was used while fire was held
vMCnt   equ     110             ; w list picker: items
vMSel   equ     112             ; w selection
vSLab   equ     114             ; w draw_labels: what the label column shows (scroll position + the cursor's row, + 1; 0 = nothing)
vSHdr   equ     116             ; w draw_header: the changed mark the header shows + 1 (0 = no header)
vSKey   equ     118             ; w draw_keys: the focus the key reminder shows + 1 (0 = none)
vSHint  equ     120             ; l draw_hint: the text the hint row shows (0 = a message, or nothing)
vSLab2  equ     124             ; w draw_labels: the last segment with a tile when the labels were drawn
vTmp    equ     126             ; w
vTmp2   equ     128             ; w
vName   equ     146             ; 26 B track name
vTyp    equ     172             ; l parse: start of the type table in the block
vTypLen equ     176             ; w bytes of TYPS (entries + end word)
vShow   equ     178             ; l the screen the shifter shows
vDraw   equ     182             ; l the screen the drawing routines write to
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
vLBusy  equ     446             ; w a preview (apply, tiles, draw) is running
vMItems equ     1200            ; 24 l list picker item texts
vLine   equ     1296            ; 64 B text line
vTxt    equ     1360            ; 20 x 40 B item texts
vKqH    equ     2200            ; w key queue: next code to pop
vKqT    equ     2202            ; w key queue: next free slot (the IKBD hook writes it)
vOldKb  equ     2204            ; l the game's IKBD handler ($118) while the editor's hook is in
vKq     equ     2208            ; 64 B ring of make codes
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
vPSh    equ     2400            ; 11 x 32 B draw_panel shadow: per text row 13-23 the colour + 1 (0 = nothing drawn) and the 28 characters shown
vTdHit  equ    2326            ; w number of td_ff runs (read by the gate scripts)
vTdRes  equ    2328            ; b $1024 when the race returned
vTdRes2 equ    2329            ; b $1226
vTdLast equ    2330            ; w $5ff8 when the race returned
vTdRem  equ    2332            ; w td_ff: units still to fast-forward
vTdKill equ    2335            ; b Esc / F10 was pressed in the race (tdkb)
vTdWhy  equ    2334            ; b how the race was decided (tdvbl): 1 the BAR was reached, 2 time-out, 0 neither (F10, Esc, crashes)

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
        move.w  #1,vPage(a5)
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
; flush_pend: the tile words are recomputed when no key is waiting (the view loop and the list loop call it), so a burst of keys is one recompute and one redraw
flush_pend:
        tst.w   vTOk(a5)
        bne   .x
        bsr     tiles_calc
        ori.w   #2,vRedraw(a5)
.x:     rts

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
        lea     vPSh(a5),a0             ; the panel shadow: nothing drawn
        moveq   #87,d0
.z:     clr.l   (a0)+
        dbra    d0,.z
        movem.l (a7)+,d0-d7/a0
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
        bra     pt_core
; ptextp: as ptext but d1 = the pixel row (for the grid's row labels and the legend)
ptextp: movem.l d0-d7/a0-a3,-(a7)
        movea.l vDraw(a5),a2
        mulu    #160,d1
        adda.l  d1,a2
        move.w  d0,d3
        lsr.w   #3,d3
        move.w  d3,d4
        lsr.w   #1,d4
        lsl.w   #3,d4
        adda.w  d4,a2
        andi.w  #1,d3
        adda.w  d3,a2
pt_core: moveq  #0,d0
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
        bra     pt_core
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

; seg_ptr: vSeg -> a0
seg_ptr:
        move.w  vSeg(a5),d0
        mulu    #SEGSZ,d0
        lea     SEGT.l,a0
        adda.l  d0,a0
        rts

; ---------------------------------------------------------------- the tile grid (design: work/notes/editor_design.md 15)
; tiles_calc: one pass over the segments and the sorted object list integrates what the game integrates (the curve value c, 16-bit like its ring, and the hill slope,
; 32-bit) and classifies the value at each segment's middle: the tile shows what the player sees, not the raw field.
; TILE[k] = bits 0-2 direction class (0 straight, 1-3 left gentle/medium/sharp, 4-6 right ...), 3-5 hill class (0 level, 1-2 rise small/big, 3-4 drop small/big),
; 6 an object in the segment, 7 the BAR; $8000 = the segment starts at or past vEnd (beyond the race).  Also: the extent (calc_end) and the cursor segment's objects (obj_find).
tiles_calc:
        movem.l d0-d7/a0/a3-a4,-(a7)
        bsr     find_bar                ; (a length edit moves the objects behind it, the BAR too: its unit decides the extent)
        bsr     calc_end
        bsr     obj_find
        lea     SEGT.l,a4
        lea     TILE.l,a0
        lea     OBJT.l,a3
        moveq   #0,d2                   ; object index
        moveq   #0,d0                   ; c (word)
        moveq   #0,d1                   ; slope (32-bit, height units * 65536 per unit)
        move.w  vNSeg(a5),d3
        beq     .x
        subq.w  #1,d3
.seg:   moveq   #0,d4
        move.w  (a4),d4                 ; start
        cmp.l   vEnd(a5),d4
        bcc     .beyond
        moveq   #0,d6
        move.w  2(a4),d6                ; length
        add.l   d6,d4                   ; end (exclusive)
        moveq   #0,d7                   ; the tile word
.of:    cmp.w   vNObj(a5),d2            ; the objects of this segment (the segments are contiguous and the list is sorted: one pass)
        bcc     .ofd
        moveq   #0,d5
        move.w  (a3),d5
        cmp.l   d4,d5
        bcc     .ofd
        ori.w   #$40,d7
        tst.w   6(a3)
        beq     .on
        ori.w   #$80,d7
.on:    addq.l  #8,a3
        addq.w  #1,d2
        bra     .of
.ofd:   move.w  d6,d5
        lsr.w   #1,d5
        muls    4(a4),d5                ; curve delta * half the length
        add.w   d0,d5                   ; c at the middle (the 16-bit wrap of the game's ring)
        moveq   #3,d4                   ; to the right: classes 4..6
        tst.w   d5
        bpl     .cr
        moveq   #0,d4                   ; to the left: 1..3
        neg.w   d5
.cr:    cmpi.w  #300,d5
        bcs     .cd                     ; straight
        addq.w  #1,d4
        cmpi.w  #1200,d5
        bcs     .co
        addq.w  #1,d4
        cmpi.w  #2400,d5
        bcs     .co
        addq.w  #1,d4
.co:    or.w    d4,d7
.cd:    move.w  d6,d5
        lsr.w   #1,d5
        muls    6(a4),d5                ; hill accel * half the length
        add.l   d1,d5                   ; the slope at the middle
        moveq   #0,d4                   ; climbing: classes 1..2
        tst.l   d5
        bpl     .hr
        moveq   #2,d4                   ; dropping: 3..4
        neg.l   d5
.hr:    cmpi.l  #1311,d5                ; 0.02 height units per unit
        bcs     .hd                     ; level
        addq.w  #1,d4
        cmpi.l  #6554,d5                ; 0.10
        bcs     .ho
        addq.w  #1,d4
.ho:    lsl.w   #3,d4
        or.w    d4,d7
.hd:    move.w  d7,(a0)+
        move.w  4(a4),d4                ; c += delta * length (the low word of the product is the same signed or unsigned)
        mulu    d6,d4
        add.w   d4,d0
        move.w  6(a4),d4                ; slope += accel * length (a length of 32768 reads as -32768 in muls)
        muls    d6,d4
        tst.w   d6
        bpl     .ls
        neg.l   d4
.ls:    add.l   d4,d1
        lea     SEGSZ(a4),a4
        dbra    d3,.seg
        bra     .x
.beyond:
        move.w  #$8000,(a0)+            ; no tile for this segment and the ones behind it
        dbra    d3,.beyond
.x:     move.w  #1,vTOk(a5)
        movem.l (a7)+,d0-d7/a0/a3-a4
        rts

; tile_draw: d0 = x (a multiple of 16), d1 = y, d2 = tile word (+ bit 8 white frame / bit 9 magenta frame).  Complete words only: a tile is never half drawn.
; A tile is 15 x 11 pixels in its hill colour (the BAR: white chequers) with the direction symbol in black (rows 2..8, columns 2..12) and, when the segment holds
; objects, a black 2 x 2 dot in the top right corner.  Selected: a two pixel frame in the frame colour, a black ring inside it, the tile's middle (9 x 5) inside that.
tile_draw:
        movem.l d0-d7/a0-a1,-(a7)
        mulu    #160,d1
        lsr.w   #4,d0
        lsl.w   #3,d0
        add.w   d0,d1
        movea.l vDraw(a5),a0
        adda.w  d1,a0
        tst.w   d2
        bpl     .full
        moveq   #TILEH-1,d0             ; bit 15: no tile
.er:    clr.l   (a0)+
        clr.l   (a0)+
        lea     152(a0),a0
        dbra    d0,.er
        bra     .x
.full:  move.w  d2,d3
        lsr.w   #2,d3
        andi.w  #$e,d3                  ; 2 x the hill class
        lea     hillcol(pc),a1
        move.w  (a1,d3.w),d7            ; the tile colour
        btst    #7,d2
        beq     .c1
        moveq   #7,d7                   ; the BAR: white
.c1:    moveq   #0,d6                   ; the frame colour (0 = not selected)
        btst    #8,d2
        beq     .c2
        moveq   #7,d6
.c2:    btst    #9,d2
        beq     .c3
        moveq   #10,d6
.c3:    move.w  d2,d3
        andi.w  #7,d3
        mulu    #14,d3
        lea     gtab-4(pc),a1
        adda.w  d3,a1                   ; the symbol's word for tile row r (2..8) is (a1, 2r)
        moveq   #0,d0                   ; row
.row:   moveq   #0,d1                   ; the pixels in the tile colour
        moveq   #0,d4                   ; the pixels in the frame colour
        cmpi.w  #TILEH-1,d0
        beq     .wr                     ; the gap row
        btst    #7,d2
        beq     .gl
        move.w  #$cccc,d1               ; the BAR: 2 x 2 chequers
        btst    #1,d0
        beq     .fr
        move.w  #$3332,d1
        bra     .fr
.gl:    move.w  #$fffe,d1
        cmpi.w  #2,d0
        bcs     .dot
        cmpi.w  #9,d0
        bcc     .fr
        move.w  d0,d5
        add.w   d5,d5
        move.w  (a1,d5.w),d5
        not.w   d5
        and.w   d5,d1                   ; the direction symbol
        bra     .fr
.dot:   btst    #6,d2
        beq     .fr
        andi.w  #$fff9,d1               ; the object dot (rows 0-1, columns 13-14)
.fr:    tst.w   d6
        beq     .wr
        cmpi.w  #2,d0
        bcs     .edge
        cmpi.w  #9,d0
        bcc     .edge
        move.w  #$c006,d4               ; selected: the frame's two first and last columns, ...
        andi.w  #$1ff0,d1               ; ... the tile's middle (columns 3..11), black between them
        cmpi.w  #2,d0
        beq     .ring
        cmpi.w  #8,d0
        bne     .wr
.ring:  moveq   #0,d1                   ; rows 2 and 8: the black ring
        bra     .wr
.edge:  btst    #7,d2
        beq     .e1
        move.w  #$fffe,d1
.e1:    move.w  d1,d4                   ; rows 0-1 and 9-10: the frame (the dot stays a notch in it)
        moveq   #0,d1
.wr:    moveq   #0,d5                   ; the four bitplanes of this row
.pl:    moveq   #0,d3
        btst    d5,d7
        beq     .p1
        move.w  d1,d3
.p1:    btst    d5,d6
        beq     .p2
        or.w    d4,d3
.p2:    move.w  d3,(a0)+
        addq.w  #1,d5
        cmpi.w  #4,d5
        bne     .pl
        lea     152(a0),a0
        addq.w  #1,d0
        cmpi.w  #TILEH,d0
        bne     .row
.x:     movem.l (a7)+,d0-d7/a0-a1
        rts

; draw_grid: every slot's desired word (tile + frame bits) against what it shows (SHW); only changed tiles are drawn
draw_grid:
        movem.l d0-d7/a0,-(a7)
        move.w  vFirst(a5),d7
        moveq   #0,d6                   ; slot
        moveq   #0,d5                   ; row
.grow:  moveq   #0,d4                   ; column
.gcol:  move.w  #$8000,d2
        cmp.w   vNSeg(a5),d7
        bcc     .cmp
        move.w  d7,d3
        add.w   d3,d3
        lea     TILE.l,a0
        move.w  (a0,d3.w),d2
        bmi     .cmp
        cmp.w   vSeg(a5),d7
        bne     .cmp
        ori.w   #$100,d2                ; the cursor: a white frame, magenta while the object list has it
        tst.w   vFocus(a5)
        beq     .cmp
        eori.w  #$300,d2
.cmp:   move.w  d6,d3
        add.w   d3,d3
        lea     SHW.l,a0
        cmp.w   (a0,d3.w),d2
        beq     .next
        move.w  d2,(a0,d3.w)
        move.w  d4,d0
        lsl.w   #4,d0
        addi.w  #GRIDX,d0
        move.w  d5,d1
        mulu    #TILEH,d1
        addi.w  #GRIDY,d1
        bsr     tile_draw
.next:  addq.w  #1,d7
        addq.w  #1,d6
        addq.w  #1,d4
        cmpi.w  #16,d4
        bne     .gcol
        addq.w  #1,d5
        cmpi.w  #8,d5
        bne     .grow
        movem.l (a7)+,d0-d7/a0
        rts

; draw_labels: the number of the first segment of every grid row in the left margin (the cursor's row yellow); drawn when the scroll position or the cursor's row changed
draw_labels:
        movem.l d0-d3/d6-d7/a0-a1,-(a7)
        move.w  vSeg(a5),d3
        sub.w   vFirst(a5),d3
        lsr.w   #4,d3                   ; the cursor's row on the screen
        move.w  d3,d0
        ror.w   #4,d0
        add.w   vFirst(a5),d0
        addq.w  #1,d0
        move.w  d0,d2
        bsr     seg_last
        cmp.w   vSLab(a5),d2
        bne     .nw
        cmp.w   vSLab2(a5),d0
        beq     .x
.nw:    move.w  d2,vSLab(a5)
        move.w  d0,vSLab2(a5)
        move.w  d0,d7                   ; the last segment that has a tile
        moveq   #0,d6
.ll:    moveq   #0,d0
        move.w  d6,d0
        lsl.w   #4,d0
        add.w   vFirst(a5),d0           ; the first segment of this row
        lea     t_nolab(pc),a0
        cmp.w   d7,d0
        bhi     .dr
        addq.w  #1,d0
        lea     vLTxt(a5),a1
        moveq   #4,d1
        bsr     appn
        clr.b   (a1)
        lea     vLTxt(a5),a0
.dr:    moveq   #1,d2
        cmp.w   d3,d6
        bne     .pt
        moveq   #8,d2
.pt:    move.w  d6,d1
        mulu    #TILEH,d1
        addi.w  #GRIDY+2,d1
        moveq   #0,d0
        bsr     ptextp
        addq.w  #1,d6
        cmpi.w  #8,d6
        bne     .ll
.x:     movem.l (a7)+,d0-d3/d6-d7/a0-a1
        rts

; lp28: pad vLine to 28 columns (the panel's width; a longer line is cut) and show it at column 0, row d1, colour d2.  Only the characters that differ from what the row shows (shadow vPSh) are drawn: a text call costs about 1500 cycles per character
lp28:   lea     vLine+28(a5),a0
.p:     cmpa.l  a0,a1
        bcc     .t
        move.b  #' ',(a1)+
        bra     .p
.t:     clr.b   (a0)
        movem.l d0/d3-d4/a0/a2-a3,-(a7)
        move.w  d1,d3
        subi.w  #13,d3
        lsl.w   #5,d3
        lea     vPSh(a5),a2
        adda.w  d3,a2                   ; this row's shadow
        move.b  d2,d4
        addq.b  #1,d4
        lea     vLine(a5),a0
        cmp.b   (a2),d4
        beq     .same
        move.b  d4,(a2)                 ; another colour (or nothing drawn yet): the whole line
        lea     1(a2),a3
        moveq   #27,d3
.cp:    move.b  (a0)+,(a3)+
        dbra    d3,.cp
        lea     vLine(a5),a0
        moveq   #0,d0
        bsr     ptext
        bra     .x
.same:  lea     1(a2),a3
        moveq   #0,d3
.ch:    move.b  (a0,d3.w),d4
        cmp.b   (a3,d3.w),d4
        beq     .nx
        move.b  d4,(a3,d3.w)
        move.b  d4,vLine+30(a5)
        clr.b   vLine+31(a5)
        lea     vLine+30(a5),a0
        move.w  d3,d0
        bsr     ptext
        lea     vLine(a5),a0
.nx:    addq.w  #1,d3
        cmpi.w  #28,d3
        bne     .ch
.x:     movem.l (a7)+,d0/d3-d4/a0/a2-a3
        rts

; draw_panel: the selected segment and its object list (text rows 13-23, the left 28 columns)
draw_panel:
        movem.l d0-d7/a0-a2/a4,-(a7)
        bsr     seg_ptr
        movea.l a0,a4
        bsr     lbeg                    ; SEGMENT nnnn/nnnn  AT nnnnn
        lea     t_pseg(pc),a0
        bsr     apps
        moveq   #0,d0
        move.w  vSeg(a5),d0
        addq.w  #1,d0
        moveq   #4,d1
        bsr     appn
        move.b  #'/',(a1)+
        move.w  vNSeg(a5),d0
        bsr     appn
        lea     t_pat(pc),a0
        bsr     apps
        move.l  vPos(a5),d0
        moveq   #5,d1
        bsr     appn
        moveq   #13,d1
        moveq   #7,d2
        bsr     lp28
        bsr     lbeg                    ; LENGTH
        lea     t_plen(pc),a0
        bsr     apps
        moveq   #0,d0
        move.w  2(a4),d0
        moveq   #5,d1
        bsr     appn
        moveq   #14,d1
        moveq   #7,d2
        bsr     lp28
        bsr     lbeg                    ; CURVE: the segment's own value (what the C list and , . change)
        lea     t_pcur(pc),a0
        bsr     apps
        lea     t_sy0(pc),a0
        move.w  4(a4),d0
        beq     .cv
        lea     t_cright(pc),a0
        bpl     .cv
        lea     t_cleft(pc),a0
        neg.w   d0
.cv:    bsr     apps
        tst.w   d0
        beq     .cv2
        bsr     apdn
.cv2:   moveq   #15,d1
        moveq   #7,d2
        bsr     lp28
        move.w  vSeg(a5),d6
        add.w   d6,d6
        lea     TILE.l,a0
        move.w  (a0,d6.w),d6            ; the tile word
        bsr     lbeg                    ; BEND: what the road does here = the tile's symbol
        lea     t_pben(pc),a0
        bsr     apps
        move.w  d6,d0
        andi.w  #7,d0
        lsl.w   #2,d0
        lea     bendtab(pc),a0
        movea.l (a0,d0.w),a0
        bsr     apps
        moveq   #16,d1
        moveq   #7,d2
        bsr     lp28
        bsr     lbeg                    ; HILL: the slope class = the tile's colour, then the segment's own accel
        lea     t_phil(pc),a0
        bsr     apps
        move.w  d6,d0
        lsr.w   #1,d0
        andi.w  #$1c,d0
        lea     hilltab(pc),a0
        movea.l (a0,d0.w),a0
        bsr     apps
        lea     t_pacc(pc),a0
        bsr     apps
        move.w  6(a4),d0
        moveq   #4,d1
        bsr     apsn
        moveq   #17,d1
        moveq   #7,d2
        bsr     lp28
        bsr     lbeg                    ; WIDTH
        lea     t_pwid(pc),a0
        bsr     apps
        moveq   #0,d0
        move.b  8(a4),d0
        moveq   #2,d1
        bsr     appn
        lea     t_prgt(pc),a0
        bsr     apps
        moveq   #0,d0
        move.b  9(a4),d0
        moveq   #2,d1
        bsr     appn
        moveq   #18,d1
        moveq   #7,d2
        bsr     lp28
        bsr     lbeg                    ; OBJECTS n
        lea     t_pobj(pc),a0
        bsr     apps
        moveq   #0,d0
        move.w  vOCnt(a5),d0
        moveq   #2,d1
        bsr     appn
        tst.w   vOCnt(a5)
        beq     .oh
        lea     vLine+22(a5),a0         ; the heading of the unit column
.op:    move.b  #' ',(a1)+
        cmpa.l  a0,a1
        bcs     .op
        lea     t_punit(pc),a0
        bsr     apps
.oh:    moveq   #19,d1
        moveq   #7,d2
        bsr     lp28
        ; the object list: four lines, scrolled so the selection shows
        move.w  vObj(a5),d0
        sub.w   vOF(a5),d0
        tst.w   vFocus(a5)
        bne     .o1
        moveq   #0,d0                   ; the grid has the cursor: from the first object
.o1:    cmp.w   vOTop(a5),d0
        bcc     .o2
        move.w  d0,vOTop(a5)
.o2:    move.w  vOTop(a5),d1
        addq.w  #3,d1
        cmp.w   d1,d0
        bls     .o3
        move.w  d0,d1
        subq.w  #3,d1
        move.w  d1,vOTop(a5)
.o3:    moveq   #0,d6                   ; line 0..3
.ol:    bsr     lbeg
        moveq   #7,d2
        move.w  vOTop(a5),d0
        add.w   d6,d0
        cmp.w   vOCnt(a5),d0
        bcs     .obj
        tst.w   d0
        bne     .od                     ; an empty line
        lea     t_pnone(pc),a0          ; no objects at all: how to add one
        bsr     apps
        moveq   #2,d2
        bra     .od
.obj:   move.w  vOF(a5),d7
        add.w   d0,d7                   ; its index in OBJT
        move.w  d7,d1
        lsl.w   #3,d1
        lea     OBJT.l,a2
        adda.w  d1,a2
        andi.l  #$ffff,d0
        addq.w  #1,d0
        moveq   #2,d1
        bsr     appn
        lea     t_obar(pc),a0
        tst.w   6(a2)
        bne     .ob
        lea     t_ot(pc),a0
        bsr     apps
        moveq   #0,d0
        move.w  2(a2),d0
        moveq   #3,d1
        bsr     appn
        lea     t_oside(pc),a0
.ob:    bsr     apps
        move.w  4(a2),d0
        moveq   #3,d1
        bsr     apsn
        move.b  #' ',(a1)+
        moveq   #0,d0
        move.w  (a2),d0
        moveq   #5,d1
        bsr     appn
        moveq   #7,d2
        tst.w   vFocus(a5)
        beq     .od
        cmp.w   vObj(a5),d7
        bne     .od
        moveq   #23,d2                  ; the selected object: a white bar
.od:    move.w  d6,d1
        addi.w  #20,d1
        bsr     lp28
        addq.w  #1,d6
        cmpi.w  #4,d6
        bne     .ol
        movem.l (a7)+,d0-d7/a0-a2/a4
        rts

; draw_keys: the key reminder of the current focus in the right 12 columns (rows 13-23); drawn when the focus changed (a pick list's box takes the same place)
draw_keys:
        movem.l d0-d2/d6/a0/a2,-(a7)
        move.w  vFocus(a5),d0
        addq.w  #1,d0
        cmp.w   vSKey(a5),d0
        beq     .x
        move.w  d0,vSKey(a5)
        lea     t_keyg(pc),a2
        subq.w  #1,d0
        beq     .g
        lea     t_keyo(pc),a2
.g:     moveq   #0,d6
.l:     movea.l a2,a0
        moveq   #28,d0
        move.w  d6,d1
        addi.w  #13,d1
        moveq   #2,d2
        tst.w   d6
        bne     .p
        moveq   #8,d2                   ; the heading
.p:     bsr     ptext
        lea     13(a2),a2
        addq.w  #1,d6
        cmpi.w  #11,d6
        bne     .l
.x:     movem.l (a7)+,d0-d2/d6/a0/a2
        rts

; draw_hint: the hint row (24): a message once (yellow), else the keys of what is going on (drawn when it changed)
draw_hint:
        movem.l d0-d2/a0-a1,-(a7)
        lea     t_hint(pc),a0
        tst.w   vFocus(a5)
        beq   .h0
        lea     t_hinto(pc),a0
.h0:    tst.w   vLOpen(a5)
        beq   .h1
        movea.l vLHintP(a5),a0
.h1:    tst.w   vLeaveW(a5)
        beq   .h2
        lea     t_hdisc(pc),a0
.h2:    tst.w   vMode(a5)
        beq   .h3
        lea     t_hmove(pc),a0
.h3:    moveq   #1,d2
        move.l  vMsg(a5),d0
        beq   .hm
        movea.l d0,a0
        move.l  d0,vLMsg(a5)
        clr.l   vMsg(a5)
        clr.l   vSHint(a5)
        moveq   #8,d2
        bra   .dr
.hm:    cmpa.l  vSHint(a5),a0
        beq   .x
        move.l  a0,vSHint(a5)
.dr:    bsr     lbeg
        bsr     apps
        moveq   #24,d1
        bsr     lend
.x:     movem.l (a7)+,d0-d2/a0-a1
        rts

; draw_header: source, name, scenery, * = changed (row 0); drawn when the changed mark changes
draw_header:
        movem.l d0-d2/a0-a1,-(a7)
        move.w  vMod(a5),d0
        addq.w  #1,d0
        cmp.w   vSHdr(a5),d0
        beq     .x
        move.w  d0,vSHdr(a5)
        bsr     lbeg
        cmpi.w  #2,vSrc(a5)
        beq   .h0
        lea     t_src(pc),a0
        move.w  vSrc(a5),d0
        lsl.w   #2,d0
        adda.w  d0,a0
        bsr     apps
        moveq   #0,d0
        move.w  vSrcIx(a5),d0
        addq.w  #1,d0
        moveq   #2,d1
        bsr     appn
        move.b  #' ',(a1)+
.h0:    lea     vName(a5),a0
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
.h4:    moveq   #0,d1
        moveq   #8,d2
        bsr     lend
.x:     movem.l (a7)+,d0-d2/a0-a1
        rts

; draw_full: the whole view on an empty page (after a menu, the key page, a full-screen list, a test drive).  draw_view: what changed since the last draw.
draw_full:
        bsr     cls
        movem.l d0/a0,-(a7)
        lea     SHW.l,a0                ; nothing is on the screen: no tile, no header, labels, key reminder, hint
        moveq   #127,d0
.iv:    move.w  #$ffff,(a0)+
        dbra    d0,.iv
        movem.l (a7)+,d0/a0
        clr.w   vSHdr(a5)
        clr.w   vSLab(a5)
        clr.w   vSKey(a5)
        clr.l   vSHint(a5)
draw_view:
        bsr     draw_header
        bsr     draw_labels
        bsr     draw_grid
        bsr     draw_panel
        bsr     draw_hint
        tst.w   vLOpen(a5)
        bne     lrows
        bra     draw_keys

; grid_fit: the grid scrolls by whole rows so that the cursor stays one row from the edge while more rows exist; a cursor outside the window gets its row at row 3
grid_fit:
        movem.l d0-d3,-(a7)
        bsr     seg_last
        andi.w  #$fff0,d0
        subi.w  #7*16,d0
        bpl     .m
        moveq   #0,d0
.m:     move.w  d0,d2                   ; the highest first row: the last row of tiles is the grid's last row
        move.w  vSeg(a5),d1
        andi.w  #$fff0,d1               ; the cursor's row
        move.w  vFirst(a5),d0
        move.w  d1,d3
        sub.w   d0,d3
        asr.w   #4,d3                   ; its row on the screen
        bmi     .ctr
        cmpi.w  #7,d3
        bgt     .ctr
        bne     .top
        addi.w  #16,d0                  ; the last row: one row on
        bra     .set
.top:   tst.w   d3
        bne     .set
        subi.w  #16,d0                  ; the first row: one row back
        bra     .set
.ctr:   move.w  d1,d0
        subi.w  #3*16,d0
.set:   tst.w   d0
        bpl     .s1
        moveq   #0,d0
.s1:    cmp.w   d2,d0
        bls     .s2
        move.w  d2,d0
.s2:    move.w  d0,vFirst(a5)
        movem.l (a7)+,d0-d3
        rts

; obj_find: the objects of the selected segment -> vOF / vOCnt; vPos = its first unit; vObj kept inside the range; a segment without objects gives the grid the cursor
obj_find:
        movem.l d0-d5/a0,-(a7)
        bsr     seg_ptr
        moveq   #0,d3
        move.w  (a0),d3
        move.l  d3,vPos(a5)
        moveq   #0,d4
        move.w  2(a0),d4
        add.l   d3,d4                   ; end (exclusive)
        lea     OBJT.l,a0
        moveq   #0,d1                   ; index
        moveq   #0,d5                   ; count
        move.w  vNObj(a5),d2
.s:     cmp.w   d2,d1
        bcc     .e
        moveq   #0,d0
        move.w  (a0),d0
        cmp.l   d3,d0
        bcc     .f
        addq.l  #8,a0
        addq.w  #1,d1
        bra     .s
.f:     move.w  d1,d0                   ; count the ones before its end
        add.w   d5,d0
        cmp.w   d2,d0
        bcc     .e
        moveq   #0,d0
        move.w  (a0),d0
        cmp.l   d4,d0
        bcc     .e
        addq.w  #1,d5
        addq.l  #8,a0
        bra     .f
.e:     move.w  d5,vOCnt(a5)
        bne     .has
        clr.w   vOF(a5)
        clr.w   vObj(a5)
        clr.w   vFocus(a5)
        bra     .x
.has:   move.w  d1,vOF(a5)
        move.w  vObj(a5),d0
        cmp.w   d1,d0
        bcc     .c2
        move.w  d1,d0
.c2:    add.w   d5,d1
        cmp.w   d1,d0
        bcs     .set
        move.w  d1,d0
        subq.w  #1,d0
.set:   move.w  d0,vObj(a5)
.x:     movem.l (a7)+,d0-d5/a0
        rts

; pick_unit: d0 = candidate unit, d1 = segment start, d2 = segment end (exclusive), d3 = 1: BAR objects do not block -> d0 = the first free unit from the candidate
; to the segment's end, then from its start (never unit 0), or 0 = the segment is full
pick_unit:
        movem.l d1-d7/a0,-(a7)
        move.w  d0,d4
        move.w  d1,d6
        move.w  d2,d7
        move.w  d3,d5
.s1:    cmp.w   d7,d0
        bcc     .w1
        tst.w   d0
        beq     .n1
        bsr     .occ
        beq     .x
.n1:    addq.w  #1,d0
        bra     .s1
.w1:    move.w  d6,d0
.w2:    cmp.w   d4,d0
        bcc     .fail
        tst.w   d0
        beq     .n2
        bsr     .occ
        beq     .x
.n2:    addq.w  #1,d0
        bra     .w2
.fail:  moveq   #0,d0
.x:     movem.l (a7)+,d1-d7/a0
        rts
.occ:   movem.l d2-d3/a0,-(a7)          ; Z set = no object on unit d0 (a BAR counts as none when d5 is set)
        lea     OBJT.l,a0
        move.w  vNObj(a5),d2
        beq     .free
        subq.w  #1,d2
.l:     move.w  (a0),d3
        cmp.w   d0,d3
        bcc     .hit
        addq.l  #8,a0
        dbra    d2,.l
        bra     .free
.hit:   bne     .free
        tst.w   d5
        beq     .occ2
        tst.w   6(a0)
        bne     .free
.occ2:  moveq   #1,d3
        bra     .r
.free:  moveq   #0,d3
.r:     movem.l (a7)+,d2-d3/a0          ; (movem leaves the flags of the moveq)
        rts

; obj_sort: the object selected by vObj changed its unit: re-insert it in the sorted list (vObj = its new index)
obj_sort:
        movem.l d0-d3/a0,-(a7)
        bsr     obj_ptr
        move.l  (a0),d1                 ; unit.w type.w
        move.l  4(a0),d2
        move.w  vObj(a5),d0
        bsr     obj_shut
        swap    d1                      ; the unit
        lea     OBJT.l,a0
        moveq   #0,d0
.l:     cmp.w   vNObj(a5),d0
        bcc     .ins
        cmp.w   (a0),d1
        bls     .ins
        addq.l  #8,a0
        addq.w  #1,d0
        bra     .l
.ins:   swap    d1
        move.w  d0,vObj(a5)
        bsr     obj_open
        move.l  d1,(a0)+
        move.l  d2,(a0)
        bsr     find_bar
        movem.l (a7)+,d0-d3/a0
        rts

; obj_follow: the object under the cursor (vObj) has a new unit: the list is sorted again and the cursor's segment is the one that holds it now
obj_follow:
        movem.l d0/a0,-(a7)
        bsr     obj_sort
        bsr     obj_ptr
        move.w  (a0),d0
        bsr     seg_of
        move.w  d0,vSeg(a5)
        bsr     obj_find
        clr.w   vTOk(a5)
        bsr     grid_fit
        ori.w   #2,vRedraw(a5)
        movem.l (a7)+,d0/a0
        rts

; obj_mv_seg: MOVE mode, d0 = -1 / +1: the object goes into the previous / next segment at the same offset (at most its last unit); a unit that holds another
; object is skipped in the direction of the move
obj_mv_seg:
        movem.l d0-d7/a0-a1,-(a7)
        move.w  d0,d7                   ; the direction
        move.w  vSeg(a5),d5
        add.w   d7,d5
        bmi     .x
        bsr     seg_last
        cmp.w   d0,d5
        bhi     .x
        bsr     seg_ptr
        movea.l a0,a1                   ; the segment it is in
        bsr     obj_ptr
        moveq   #0,d2
        move.w  (a0),d2
        sub.w   (a1),d2                 ; its offset there
        lea     SEGSZ(a1),a1
        tst.w   d7
        bpl     .tg
        lea     -2*SEGSZ(a1),a1
.tg:    moveq   #0,d3
        move.w  (a1),d3                 ; the target segment's first unit
        moveq   #0,d6
        move.w  2(a1),d6
        add.l   d3,d6
        subq.l  #1,d6                   ; ... and its last one (inside the race)
        move.l  vEnd(a5),d4
        subq.l  #1,d4
        cmp.l   d4,d6
        bls     .k1
        move.l  d4,d6
.k1:    add.l   d3,d2                   ; the candidate
        cmp.l   d6,d2
        bls     .k2
        move.l  d6,d2
.k2:    tst.l   d2
        bne     .lp
        moveq   #1,d2                   ; never unit 0
.lp:    move.w  d2,d0
        move.w  vObj(a5),d1
        bsr     occ_unit
        bne     .got
        tst.w   d7
        bmi     .dn
        addq.l  #1,d2
        cmp.l   d6,d2
        bhi     .x
        bra     .lp
.dn:    subq.l  #1,d2
        beq     .x
        cmp.l   d3,d2
        bcs     .x
        bra     .lp
.got:   bsr     obj_ptr
        move.w  d2,(a0)
        bsr     obj_follow
.x:     movem.l (a7)+,d0-d7/a0-a1
        rts

; in_reset: forget every key and wait until fire is released
in_reset:
        clr.b   $60ff.w
        move.w  #$f,vPDir(a5)
        clr.w   vFire(a5)
.f:     jsr     $d206.l
        btst    #7,$6105.w
        bne   .f
        rts

; ---------------------------------------------------------------- the editor's view
view:   move.w  #1,vState(a5)
        clr.w   vRes(a5)
        clr.w   vSeg(a5)
        clr.l   vPos(a5)
        clr.w   vObj(a5)
        clr.w   vFocus(a5)
        clr.w   vFirst(a5)
        clr.w   vOTop(a5)
        clr.l   vMsg(a5)
        clr.w   vMod(a5)
        clr.w   vMode(a5)
        clr.w   vLeaveW(a5)
        clr.w   vLastAct(a5)
        clr.w   vLastType(a5)
        clr.w   vLastSide(a5)
        clr.w   vLOpen(a5)
        move.w  #1,vPage(a5)
        bsr     hist_init
        bsr     tiles_calc              ; the tile words, the extent, the first segment's objects
        bsr     in_reset
        move.w  #1,vRedraw(a5)
.loop:  bsr     kq_empty
        bne   .in                       ; a key is waiting: nothing is recomputed or drawn before it is handled
        bsr     flush_pend              ; the tile words (when an edit made them stale), then the redraw
        move.w  vRedraw(a5),d0
        beq   .in
        clr.w   vRedraw(a5)
        btst    #0,d0
        beq   .part
        bsr     draw_full
        bra   .in
.part:  bsr     draw_view
.in:    jsr     $d206.l
        bsr     input
        tst.w   vRes(a5)
        beq   .loop
        clr.w   vState(a5)
        rts

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
        moveq   #0,d4                   ; modifier: 1 fire or Control (MOVE: one unit), 2 Shift (100 units)
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
.m2:    tst.w   vMode(a5)
        beq   .nav
        btst    #3,d2                   ; MOVE mode: left / right = move the object, up / down = into the previous / next segment
        beq   .mv1
        moveq   #1,d0
        bra     obj_mv_step
.mv1:   btst    #2,d2
        beq   .mv2
        moveq   #-1,d0
        bra     obj_mv_step
.mv2:   btst    #1,d2
        beq   .mv3
        moveq   #1,d0
        bra     obj_mv_seg
.mv3:   moveq   #-1,d0
        bra     obj_mv_seg
.nav:   btst    #3,d2
        beq   .n1
        moveq   #1,d0
        bra     seg_move
.n1:    btst    #2,d2
        beq   .n2
        moveq   #-1,d0
        bra     seg_move
.n2:    tst.b   d3                      ; fire + down = into the object list, fire + up = back to the grid
        bpl   .n3
        btst    #1,d2
        beq   .fu
        tst.w   vFocus(a5)
        bne   .x
        bra   .tab
.fu:    tst.w   vFocus(a5)
        beq   .x
.tab:   moveq   #6,d0
        bra     command
.n3:    moveq   #1,d0
        btst    #1,d2
        bne     step_row
        moveq   #-1,d0
        bra     step_row
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

; step_row: d0 = -1 / +1: one grid row = 16 segments; in the object list the previous / next object
step_row:
        tst.w   vFocus(a5)
        bne     obj_sel
        lsl.w   #4,d0

; seg_move: d0 = +-n: the cursor moves by n segments (clamped to the segments the race reaches); the object list gives the cursor back to the grid
seg_move:
        movem.l d0-d2,-(a7)
        move.w  d0,d2
        add.w   vSeg(a5),d2
        bsr     seg_last
        tst.w   d2
        bpl   .a
        moveq   #0,d2
.a:     cmp.w   d0,d2
        bls   .b
        move.w  d0,d2
.b:     move.w  d2,vSeg(a5)
        clr.w   vFocus(a5)
        bsr     obj_find
        bsr     grid_fit
        ori.w   #2,vRedraw(a5)
        movem.l (a7)+,d0-d2
        rts

; seg_last: d0 = the last segment whose start lies before vEnd (0 when there is none)
seg_last:
        movem.l d1/a0,-(a7)
        move.w  vNSeg(a5),d0
        subq.w  #1,d0
        bmi   .z
        move.w  d0,d1
        mulu    #SEGSZ,d1
        lea     SEGT.l,a0
        adda.l  d1,a0
.l:     moveq   #0,d1
        move.w  (a0),d1
        cmp.l   vEnd(a5),d1
        bcs   .x
        subq.w  #1,d0
        bmi   .z
        lea     -SEGSZ(a0),a0
        bra   .l
.z:     moveq   #0,d0
.x:     movem.l (a7)+,d1/a0
        rts

; obj_sel: d0 = -1 / +1: the previous / next object of the selected segment (up on the first one gives the cursor back to the grid)
obj_sel:
        movem.l d1-d2,-(a7)
        move.w  vObj(a5),d2
        add.w   d0,d2
        move.w  vOF(a5),d1
        cmp.w   d1,d2
        bge   .a
        clr.w   vFocus(a5)
        bra   .r
.a:     add.w   vOCnt(a5),d1
        cmp.w   d1,d2
        bge   .x                        ; the last one: stays
        move.w  d2,vObj(a5)
.r:     ori.w   #2,vRedraw(a5)
.x:     movem.l (a7)+,d1-d2
        rts

; command: d0 = 1 leave, 2 the first segment, 3 the BAR, 6 the grid <> the object list, 7 help, 8 menu, 9 Return / Space (repeat the last pick),
; 10..27 the edits (see cmd_edit)
command:
        tst.w   vMode(a5)
        bne     mv_cmd
        cmpi.w  #10,d0
        bcc     cmd_edit
        subq.w  #1,d0
        beq     leave
        subq.w  #1,d0
        bne   .c3
        move.w  vSeg(a5),d0             ; Clr/Home: the first segment
        neg.w   d0
        bra     seg_move
.c3:    subq.w  #1,d0
        bne   .c6
        move.l  vBarAt(a5),d0           ; B: the segment that holds the BAR
        bmi   .nobar
        bsr     seg_of
        sub.w   vSeg(a5),d0
        bra     seg_move
.nobar: lea     t_nobar(pc),a0
        bra     msg
.c6:    subq.w  #3,d0
        bne   .c7
        tst.w   vFocus(a5)              ; Tab / fire + down / up: the grid <> the object list of the selected segment
        beq   .toobj
        clr.w   vFocus(a5)
        bra   .foc
.toobj: tst.w   vOCnt(a5)
        beq   .noobj
        move.w  vOF(a5),vObj(a5)
        move.w  #1,vFocus(a5)
.foc:   ori.w   #2,vRedraw(a5)
        rts
.noobj: lea     t_noobj(pc),a0
        bra     msg
.c7:    subq.w  #1,d0
        bne   .c8
        bsr     help
        bsr     in_reset
        move.w  #1,vRedraw(a5)
        rts
.c8:    subq.w  #1,d0
        bne     rep_cmd
        bsr     vmenu
        move.w  d0,-(a7)
        bsr     in_reset
        move.w  #1,vRedraw(a5)
        move.w  (a7)+,d0
        bgt     command                 ; a menu item = the same command
        rts

; vmenu: the menu (FIRE): the grid's or the object list's items, then the common ones -> d0 = command or 0
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

; help: page 1 the keys, page 2 what the tiles mean (the legend is drawn with the tile routine itself); a key or fire turns the page
help:   move.w  #3,vState(a5)
        move.w  #1,vPage(a5)
.page:  bsr     cls
        cmpi.w  #2,vPage(a5)
        beq     .leg
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
        bra     .wait
.leg:   bsr     legend
.wait:  bsr     in_reset
.w:     jsr     $d206.l
        bsr     kq_pop
        tst.b   d0
        bne     .d
        btst    #7,$6105.w
        beq     .w
.d:     addq.w  #1,vPage(a5)
        cmpi.w  #3,vPage(a5)
        bne     .page
        move.w  #1,vPage(a5)
        move.w  #1,vState(a5)
        rts

; legend: the second page of HELP, from legtab: every symbol, colour and mark drawn by the tile routine with its name beside it
legend:
        movem.l d0-d2/a0/a2,-(a7)
        lea     t_leg(pc),a0
        moveq   #1,d0
        moveq   #0,d1
        moveq   #8,d2
        bsr     ptext
        lea     legtab(pc),a2
.l:     move.w  (a2)+,d0                ; x, y, tile word (bit 15: a heading, no tile), text
        bmi   .e
        move.w  (a2)+,d1
        move.w  (a2)+,d2
        movea.l (a2)+,a0                ; (movea leaves the flags of the tile word)
        bmi   .h
        bsr     tile_draw
        addi.w  #24,d0
        addq.w  #2,d1
        moveq   #7,d2
        bra   .t
.h:     moveq   #2,d2
.t:     bsr     ptextp
        bra   .l
.e:     lea     t_pak(pc),a0
        moveq   #27,d0
        moveq   #24,d1
        moveq   #1,d2
        bsr     ptext
        movem.l (a7)+,d0-d2/a0/a2
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
hist_done:                              ; a state came back
        moveq   #1,d0
        cmpi.l  #ARENA,vHCur(a5)
        bne   .m
        tst.w   vHDrop(a5)
        bne   .m
        moveq   #0,d0
.m:     move.w  d0,vMod(a5)
        clr.w   vLeaveW(a5)
        bra     refresh
refresh:                                ; the model changed: the tile words are recomputed by flush_pend when no key is waiting
        clr.w   vTOk(a5)
        ori.w   #2,vRedraw(a5)
        bsr     obj_find
        bra     grid_fit
ed_commit:                              ; an edit was made: history, modified, the view
        bsr     hist_push
        move.w  #1,vMod(a5)
        clr.w   vLeaveW(a5)
        bra     refresh
ed_fail:                                ; a0 = message: the edit is undone
        move.l  a0,-(a7)
        bsr     hist_cur
        clr.w   vTOk(a5)
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
        clr.w   vTOk(a5)                ; (a preview: the working copy changed, the tiles follow)
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
        move.w  d1,4(a0)
        bra   ap_ok
ap_wl:  cmpi.w  #10,d1
        blt   ap_range
        cmpi.w  #85,d1
        bgt   ap_range
        move.b  d1,8(a0)
        bra   ap_ok
ap_wr:  cmpi.w  #10,d1
        blt   ap_range
        cmpi.w  #85,d1
        bgt   ap_range
        move.b  d1,9(a0)
        bra   ap_ok
ap_range:
        lea     t_erange(pc),a0
        bra   ap_bad
ap_raw: cmpi.w  #-6000,d1
        blt   ap_range
        cmpi.w  #4000,d1
        bgt   ap_range
        move.w  d1,6(a0)
ap_hov: bsr     hill_ovf
        tst.w   d0
        beq   ap_ok
        lea     t_ehill(pc),a0
        bra   ap_bad
ap_type:
        bsr     obj_ptr
        tst.w   6(a0)
        bne   .bar
        move.w  d1,2(a0)
        bra   ap_ok
.bar:   lea     t_ebart(pc),a0
        bra   ap_bad
ap_side:
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
        clr.w   vTOk(a5)
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
        bne   .go
.o:     tst.w   vFocus(a5)              ; a type or a side needs the selected object
        beq   .wrong
.go:    move.w  vLastVal(a5),d1
        bra     apply_try
.none:  lea     t_norep(pc),a0
        bra     msg
.wrong: lea     t_wrongrow(pc),a0
        bra     msg
curve_step:                             ; d2 = -1 / +1: one step more to the left / right
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
        cmpi.w  #18,d0
        bcc   .r
        add.w   d0,d0
        move.w  .t(pc,d0.w),d0
        jmp     .t(pc,d0.w)
.r:     rts
.t:     dc.w    c_curve-.t,c_hill-.t,c_len-.t,c_wl-.t,c_wr-.t,c_ins-.t,c_spl-.t,c_del-.t,c_type-.t,c_bar-.t,c_undo-.t,c_redo-.t,c_check-.t,c_mrg-.t,c_cm-.t,c_cp-.t,c_td-.t,c_objadd-.t
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
el_road: bra    edit_list
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
c_objadd: bra   obj_add
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
        move.w  #28,vLCol(a5)           ; the box: the right 12 columns of the panel, rows 13-23
        move.w  #12,vLW(a5)
        move.w  #14,vLRow0(a5)          ; heading row 13, items 14..23
        move.w  #10,vLRows(a5)
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
        clr.w   vTOk(a5)
        moveq   #8,d0
        bsr     edit_list
        bra   .x
.rec:   bsr     record
        bsr     hist_push
        move.w  #1,vMod(a5)
        clr.w   vLeaveW(a5)
        ori.w   #2,vRedraw(a5)
        bra   .x
.wide:  bsr     record
        move.w  vLAct(a5),d0
        move.w  vLVal(a5),d1
        bsr     apply_try
        bra   .x
.cancel: bsr    hist_cur
        clr.w   vTOk(a5)
        ori.w   #2,vRedraw(a5)
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
        move.w  vLRow0(a5),d1
        subq.w  #1,d1
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
box_clr:                                ; the right 12 columns, rows 13..23 (the panel stays visible while a list is open)
        movea.l vDraw(a5),a0
        adda.w  #104*160+112,a0
        move.w  #87,d0
.l:     moveq   #11,d1
.i:     clr.l   (a0)+
        dbra    d1,.i
        lea     160-48(a0),a0
        dbra    d0,.l
        rts
lb_open:                                ; narrow lists: the panel keeps the left 28 columns, the box takes the key reminder's 12; wide lists (types) take the page
        move.w  #1,vLOpen(a5)
        bsr     lscroll
        tst.w   vLWide(a5)
        bne     .w
        bsr     box_clr
        clr.w   vSKey(a5)
        bra     draw_view
.w:     bsr     cls
        bra     lrows
lb_close:
        clr.w   vLOpen(a5)
        tst.w   vLWide(a5)
        bne     draw_full
        bra     draw_view
lpreview:                               ; the working copy with the shown value applied: the grid and the panel follow
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
.ok:    bsr     tiles_calc
        bsr     draw_view
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
seg_copy:                               ; I (grid): insert a copy of the segment behind it (the road behind moves down by its length)
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
        addq.w  #1,d6
        move.w  d6,vSeg(a5)
        bra     ed_commit
el_last: lea    t_elast(pc),a0
        bra     msg
el_fullseg: lea t_efullseg(pc),a0
        bra     msg
seg_del:                                ; Delete (grid): remove the segment (the road behind moves up)
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
        bra     ed_commit
seg_split:                              ; S (grid): cut the segment in half
        cmpi.w  #MAXSEG,vNSeg(a5)
        bcc   el_fullseg
        move.w  vSeg(a5),d6
        bsr     seg_ptr
        moveq   #0,d4
        move.w  2(a0),d4                ; the length
        move.w  d4,d3
        lsr.w   #1,d3                   ; the first part
        beq   .short
        move.w  d3,-(a7)
        move.w  d4,-(a7)
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
        moveq   #0,d5
        move.w  (a0),d5
        add.w   d3,d5
        move.w  d5,(a0)                 ; the new segment starts where the first one ends
        move.w  d4,d5
        sub.w   d3,d5
        move.w  d5,2(a0)
        move.w  d3,-SEGSZ+2(a0)         ; the first part keeps the start
        bra     ed_commit               ; (the cursor stays on the first half)
.short: lea     t_esplit(pc),a0
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
        bra     ed_commit
hov_fail: lea   t_ehill(pc),a0
        bra     ed_fail

; ---------------------------------------------------------------- object edits (the object list of the selected segment)
; obj_add: O / the menu: an object of the last picked type at the first free unit of the selected segment (pick_unit), selected in the list
obj_add:
        cmpi.w  #MAXOBJ,vNObj(a5)
        bcc   .full
        bsr     seg_ptr
        moveq   #0,d1
        move.w  (a0),d1                 ; start
        moveq   #0,d2
        move.w  2(a0),d2
        add.w   d1,d2                   ; end
        tst.w   vFocus(a5)
        beq   .mid
        bsr     obj_ptr                 ; list: behind the selected object
        moveq   #0,d0
        move.w  (a0),d0
        addq.w  #1,d0
        bra     .pick
.mid:   move.w  d1,d0
        move.w  d2,d3
        sub.w   d1,d3
        lsr.w   #1,d3
        add.w   d3,d0                   ; grid: the middle of the segment
.pick:  moveq   #0,d3                   ; (a BAR's unit is taken too)
        bsr     pick_unit
        tst.w   d0
        bne     .ok
        lea     t_egap(pc),a0
        bra     msg
.ok:    move.w  d0,d3                   ; the unit
        moveq   #0,d0
        move.w  vNObj(a5),d1
        lea     OBJT.l,a0
.f:     cmp.w   d1,d0
        bcc     .ins
        cmp.w   (a0),d3
        bcs     .ins
        addq.l  #8,a0
        addq.w  #1,d0
        bra     .f
.ins:   move.w  d0,d6
        bsr     obj_open
        move.w  d3,(a0)
        move.w  vLastType(a5),d0
        bne     .t
        moveq   #1,d0
        cmp.w   vBarT(a5),d0
        bne     .t
        moveq   #2,d0
.t:     move.w  d0,2(a0)
        move.w  vLastSide(a5),4(a0)
        clr.w   6(a0)
        move.w  d6,vObj(a5)
        move.w  #1,vFocus(a5)
        bsr     ed_commit
        bsr     dens_chk
        tst.w   d0
        beq   .x
        lea     t_wdens(pc),a0
        bra     msg
.x:     rts
.full:  lea     t_efullobj(pc),a0
        bra     msg
obj_del:                                ; Delete: remove the selected object (never the BAR); the selection moves on, an empty segment gives the grid the cursor
        tst.w   vNObj(a5)
        beq   .x
        cmpi.w  #1,vNObj(a5)
        beq   .x
        bsr     obj_ptr
        tst.w   6(a0)
        bne   .bar
        move.w  vObj(a5),d0
        bsr     obj_shut
        subq.w  #1,vOCnt(a5)
        tst.w   vOCnt(a5)
        beq   .grid
        move.w  vObj(a5),d0
        move.w  vOF(a5),d1
        add.w   vOCnt(a5),d1
        cmp.w   d1,d0
        bcs   .sel
        move.w  d1,d0
        subq.w  #1,d0
        move.w  d0,vObj(a5)
.sel:   bra     ed_commit
.grid:  clr.w   vFocus(a5)
        bra     ed_commit
.bar:   lea     t_ebardel(pc),a0
        bra     msg
.x:     rts
obj_move:                               ; M: the object follows left / right (and up / down across the segments) until FIRE / Return (Esc = back)
        tst.w   vNObj(a5)
        beq   .x
        bsr     obj_ptr
        move.w  (a0),vMoveOrg(a5)
        move.w  #1,vMode(a5)
        ori.w   #2,vRedraw(a5)
.x:     rts
obj_mv_step:                            ; MOVE mode: d0 = -1 / +1, d4 = 0 ten units, 1 one unit (fire / Control), 2 a hundred (Shift).  The object goes anywhere in the race
        movem.l d0-d7/a0,-(a7)          ; (1 .. the extent - 1); a unit that holds another object is skipped in the direction of the move; the cursor follows it
        moveq   #10,d1
        cmpi.w  #1,d4
        bne   .a1
        moveq   #1,d1
.a1:    cmpi.w  #2,d4
        bne   .a2
        moveq   #100,d1
.a2:    moveq   #1,d7                   ; the direction
        tst.w   d0
        bpl   .a3
        moveq   #-1,d7
        neg.l   d1
.a3:    bsr     obj_ptr
        moveq   #0,d2
        move.w  (a0),d2
        add.l   d1,d2                   ; the wanted unit
        moveq   #1,d5                   ; lowest
        move.l  vEnd(a5),d6
        subq.l  #1,d6                   ; highest
        cmp.l   d5,d2
        bge   .a4
        move.l  d5,d2
.a4:    cmp.l   d6,d2
        ble   .a5
        move.l  d6,d2
.a5:    move.w  d2,d0
        move.w  vObj(a5),d1
        bsr     occ_unit
        bne   .set                      ; free
        add.l   d7,d2
        cmp.l   d5,d2
        blt   .x
        cmp.l   d6,d2
        ble   .a5
        bra   .x
.set:   bsr     obj_ptr
        move.w  d2,(a0)
        bsr     obj_follow
.x:     movem.l (a7)+,d0-d7/a0
        rts

; occ_unit: d0 = unit, d1 = an object's index -> Z clear when no OTHER object sits on that unit (all registers kept)
occ_unit:
        movem.l d0-d3/a0,-(a7)
        move.w  d1,d3
        moveq   #0,d1
        lea     OBJT.l,a0
        move.w  vNObj(a5),d2
        beq     .fr
        subq.w  #1,d2
.l:     cmp.w   (a0),d0
        beq   .hit
        bcs   .fr
        addq.l  #8,a0
        addq.w  #1,d1
        dbra    d2,.l
        bra     .fr
.hit:   cmp.w   d3,d1
        beq   .fr
        moveq   #0,d0
        tst.w   d0
        bra     .r
.fr:    moveq   #1,d0
        tst.w   d0
.r:     movem.l (a7)+,d0-d3/a0
        rts

mv_cmd:                                 ; MOVE mode: Return / Space / FIRE = keep the new place, Esc / F10 = put the object back
        cmpi.w  #8,d0
        beq   .ok
        cmpi.w  #9,d0
        beq   .ok
        cmpi.w  #1,d0
        bne   .x
        clr.w   vMode(a5)
        bsr     obj_ptr
        move.w  vMoveOrg(a5),(a0)
        bra     obj_follow
.ok:    clr.w   vMode(a5)
        bra     ed_commit
.x:     rts
bar_here:                               ; Shift+B / menu: the BAR goes to the first free unit of the selected segment
        tst.w   vBarT(a5)
        beq   .nb
        bsr     seg_ptr
        moveq   #0,d1
        move.w  (a0),d1
        moveq   #0,d2
        move.w  2(a0),d2
        add.w   d1,d2
        move.w  d1,d0
        moveq   #1,d3                   ; BAR objects do not block
        bsr     pick_unit
        tst.w   d0
        bne   .ok
        lea     t_egap(pc),a0
        bra     msg
.ok:    move.w  d0,d3
        moveq   #0,d4                   ; the BAR keeps its side
        move.w  vNObj(a5),d6            ; a damaged track may hold several BARs: they all go
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
.dd:    moveq   #0,d0
        move.w  vNObj(a5),d1
        lea     OBJT.l,a0
.f:     cmp.w   d1,d0
        bcc   .ins
        cmp.w   (a0),d3
        bcs   .ins
        addq.l  #8,a0
        addq.w  #1,d0
        bra     .f
.ins:   move.w  d0,d6
        bsr     obj_open
        move.w  d3,(a0)
        move.w  vBarT(a5),2(a0)
        move.w  d4,4(a0)
        move.w  #1,6(a0)
        move.w  d6,vObj(a5)
        move.w  #1,vFocus(a5)
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
.nb:    lea     t_ebart0(pc),a0
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
.w1:    moveq   #0,d2                   ; W-HILL: the height sits at the top for more than 300 race units (the game's integrator, as tools/msrtrack.py validate)
        moveq   #0,d3
        moveq   #0,d4
        move.w  vRl(a5),d0              ; the race's units only
        lea     SEGT.l,a0
        move.w  vNSeg(a5),d1
        subq.w  #1,d1
.hl:    move.w  6(a0),d5
        ext.l   d5
        move.w  2(a0),d6
        subq.w  #1,d6
.hu:    subq.w  #1,d0
        bcs   .he
        add.l   d3,d4
        add.l   d5,d3
        tst.l   d4
        bmi   .hn
        move.l  d4,d7
        swap    d7
        cmpi.w  #127,d7
        blt   .hn
        addq.w  #1,d2
.hn:    dbra    d6,.hu
        lea     SEGSZ(a0),a0
        dbra    d1,.hl
.he:    cmpi.w  #300,d2
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
.have:  moveq   #0,d0
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
        move.l  vPos(a5),d0             ; from the selected segment's first unit, or from the selected object while the object list has the cursor
        tst.w   vFocus(a5)
        beq   .cu
        bsr     obj_ptr
        moveq   #0,d0
        move.w  (a0),d0
.cu:
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
pal:    dc.w    $000,$444,$567,$070,$067,$740,$700,$777,$770,$037,$707,$777,$777,$777,$777,$777   ; 4 / 9 = light / deep blue (DROP tiles), 10 = magenta (the cursor's frame while the object list has it)
; the tile grid's tables
hillcol: dc.w   3,8,6,4,9                ; LEVEL green, RISE SMALL yellow, RISE BIG red, DROP SMALL light blue, DROP BIG dark blue
gtab:   dc.w    $0180,$0180,$0180,$0180,$0180,$0180,$0180   ; STRAIGHT (7 rows, columns 2..12 of the tile)
        dc.w    $0c00,$0c00,$0600,$0600,$0300,$0300,$0180   ; GENTLE LEFT
        dc.w    $1800,$0c00,$0600,$0300,$0180,$00c0,$0060   ; MEDIUM LEFT
        dc.w    $0000,$3800,$0e00,$0380,$00e0,$0038,$0000   ; SHARP LEFT
        dc.w    $0060,$0060,$00c0,$00c0,$0180,$0180,$0300   ; GENTLE RIGHT
        dc.w    $0030,$0060,$00c0,$0180,$0300,$0600,$0c00   ; MEDIUM RIGHT
        dc.w    $0000,$0038,$00e0,$0380,$0e00,$3800,$0000   ; SHARP RIGHT
bendtab: dc.l   t_sy0,t_sy1,t_sy2,t_sy3,t_sy4,t_sy5,t_sy6   ; names of the direction classes (long entries: index * 4)
hilltab: dc.l   t_hc0,t_hc1,t_hc2,t_hc3,t_hc4               ; ... of the hill classes
legtab: dc.w    16,10,$8000                                 ; the legend page: x, y, tile word (bit 15 = a heading), text
        dc.l    t_lg1
        dc.w    16,20,0
        dc.l    t_sy0
        dc.w    16,32,1
        dc.l    t_sy1
        dc.w    16,44,2
        dc.l    t_sy2
        dc.w    16,56,3
        dc.l    t_sy3
        dc.w    16,68,4
        dc.l    t_sy4
        dc.w    16,80,5
        dc.l    t_sy5
        dc.w    16,92,6
        dc.l    t_sy6
        dc.w    16,106,$8000
        dc.l    t_lg2
        dc.w    16,116,$00
        dc.l    t_hc0
        dc.w    16,128,$08
        dc.l    t_hc1
        dc.w    16,140,$10
        dc.l    t_hc2
        dc.w    16,152,$18
        dc.l    t_hc3
        dc.w    16,164,$20
        dc.l    t_hc4
        dc.w    176,10,$8000
        dc.l    t_lg3
        dc.w    176,20,$40
        dc.l    t_legdot
        dc.w    176,36,$80
        dc.l    t_legbar
        dc.w    176,52,$100
        dc.l    t_legcur
        dc.w    176,68,$200
        dc.l    t_legobj
        dc.w    -1
rltab:  dc.w    19472,19720,19800,19000,19375,18000,18626,20000,19000,20000,20000,22000,18500,22000,23000   ; race length of the 15 levels (word 0 of the minimap header, tools/msrtrack.py LEVELS)
keytab: dc.b    $01,1,$44,1             ; Esc, F10: leave (the track is kept)
        dc.b    $47,2                   ; Clr/Home: the first segment
        dc.b    $30,3                   ; B: the segment that holds the BAR (Shift + B: put the BAR here)
        dc.b    $0f,6                   ; Tab: the grid <> the object list
        dc.b    $62,7,$3b,7             ; Help, F1 (the keys, then the legend)
        dc.b    $1c,9,$72,9,$39,9       ; Return, Enter, Space: repeat the last pick at the cursor
        dc.b    $2e,10                  ; C curve
        dc.b    $23,11                  ; H hill
        dc.b    $26,12                  ; L length
        dc.b    $11,13,$12,14           ; W E widths
        dc.b    $17,15,$52,15           ; I, Insert: a copy of the segment (grid) / an object (list)
        dc.b    $1f,16                  ; S: split in half (grid) / the object's SIDE (list)
        dc.b    $53,17                  ; Delete
        dc.b    $14,18                  ; T: the object's TYPE (list)
        dc.b    $16,20,$61,20           ; U, Undo (Shift: redo)
        dc.b    $25,22                  ; K check
        dc.b    $32,23                  ; M: merge (grid) / move the object (list)
        dc.b    $33,24,$34,25           ; , . bend left / right
        dc.b    $19,26                  ; P test drive from the cursor (or from the selected object)
        dc.b    $18,27                  ; O: add an object to the selected segment
        dc.b    0
vmroad: dc.b    10,11,12,13,14,15,16,23,17,27,19,20,21,22,26,6,7,0,1
vmobj:  dc.b    18,16,23,27,17,19,20,21,22,26,6,7,0,1
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
        dc.b    "SPLIT IN HALF                      S",0
        dc.b    "MERGE WITH THE NEXT                M",0
        dc.b    "DELETE THIS SEGMENT              DEL",0
        dc.b    "ADD AN OBJECT HERE                 O",0
        dc.b    "PUT THE BAR HERE             SHIFT B",0
        dc.b    "UNDO                               U",0
        dc.b    "REDO                         SHIFT U",0
        dc.b    "CHECK THE TRACK                    K",0
        dc.b    "TEST DRIVE FROM THE CURSOR         P",0
        dc.b    "OBJECTS <> SEGMENTS              TAB",0
        dc.b    "KEYS                            HELP",0
        dc.b    "< BACK TO THE GRID",0
        dc.b    "LEAVE AND KEEP THIS TRACK         F10",0,0
m_obj:
        dc.b    "TYPE...                            T",0
        dc.b    "SIDE...                            S",0
        dc.b    "MOVE THIS OBJECT                   M",0
        dc.b    "ADD AN OBJECT                      O",0
        dc.b    "DELETE THIS OBJECT               DEL",0
        dc.b    "PUT THE BAR HERE             SHIFT B",0
        dc.b    "UNDO                               U",0
        dc.b    "REDO                         SHIFT U",0
        dc.b    "CHECK THE TRACK                    K",0
        dc.b    "TEST DRIVE FROM THIS OBJECT        P",0
        dc.b    "SEGMENTS <> OBJECTS              TAB",0
        dc.b    "KEYS                            HELP",0
        dc.b    "< BACK TO THE OBJECTS",0
        dc.b    "LEAVE AND KEEP THIS TRACK         F10",0,0
t_vmenu: dc.b   "EDIT MENU",0
t_src:  dc.b    "C",0,0,0,"S",0,0,0,"NEW",0
t_scen: dc.b    "SCENERY ",0
t_hint: dc.b    "FIRE=MENU RET=REPEAT P=DRIVE HELP=KEYS",0
t_hinto: dc.b   "OBJECT LIST: UP/DOWN PICK  TAB=THE GRID",0
t_hdisc: dc.b   "ESC AGAIN = DISCARD THIS TRACK   K=CHECK",0
t_hmove: dc.b   "MOVE L/R U/D  RETURN=KEEP  ESC=PUT BACK",0
t_lhsel: dc.b   "UP/DOWN PICK  FIRE/RETURN=OK  ESC=BACK",0
t_lhadj: dc.b   "U/D PICK  L/R +-1 (FIRE 10)  FIRE=OK",0
t_nound: dc.b   "NOTHING TO UNDO",0
t_noredo: dc.b  "NOTHING TO REDO",0
t_norep: dc.b   "NOTHING TO REPEAT: PICK A VALUE FIRST",0
t_wrongrow: dc.b "THAT VALUE IS FOR AN OBJECT: TAB FIRST",0
t_objrow: dc.b  "THE OBJECT LIST ONLY: TAB FIRST",0
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
t_esplit: dc.b  "SEGMENT TOO SHORT TO SPLIT",0
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
t_nolab: dc.b   "    ",0
t_pseg: dc.b    "SEGMENT ",0
t_pat:  dc.b    "  AT ",0
t_plen: dc.b    "LENGTH ",0
t_pcur: dc.b    "CURVE  ",0
t_cleft: dc.b   "LEFT ",0
t_cright: dc.b  "RIGHT ",0
t_pben: dc.b    "BEND   ",0
t_phil: dc.b    "HILL   ",0
t_pacc: dc.b    " ACC ",0
t_pwid: dc.b    "WIDTH  LEFT ",0
t_prgt: dc.b    "  RIGHT ",0
t_pobj: dc.b    "OBJECTS ",0
t_punit: dc.b   "UNIT",0
t_pnone: dc.b   "NONE HERE: O ADDS ONE",0
t_ot:   dc.b    " TYPE ",0
t_oside: dc.b   " SIDE ",0
t_obar: dc.b    " THE BAR  SIDE ",0
t_noobj: dc.b   "NO OBJECTS HERE: O ADDS ONE",0
t_sy0:  dc.b    "STRAIGHT",0
t_sy1:  dc.b    "GENTLE LEFT",0
t_sy2:  dc.b    "MEDIUM LEFT",0
t_sy3:  dc.b    "SHARP LEFT",0
t_sy4:  dc.b    "GENTLE RIGHT",0
t_sy5:  dc.b    "MEDIUM RIGHT",0
t_sy6:  dc.b    "SHARP RIGHT",0
t_hc0:  dc.b    "LEVEL",0
t_hc1:  dc.b    "RISE SMALL",0
t_hc2:  dc.b    "RISE BIG",0
t_hc3:  dc.b    "DROP SMALL",0
t_hc4:  dc.b    "DROP BIG",0
t_leg:  dc.b    "WHAT THE TILES MEAN",0
t_lg1:  dc.b    "SYMBOL = BEND",0
t_lg2:  dc.b    "COLOUR = HILL",0
t_lg3:  dc.b    "MARKS",0
t_legdot: dc.b  "AN OBJECT HERE",0
t_legbar: dc.b  "THE BAR",0
t_legcur: dc.b  "THE CURSOR",0
t_legobj: dc.b  "ITS OBJECT LIST",0
t_keyg: dc.b    "KEYS        ",0
        dc.b    "C CURVE     ",0
        dc.b    "H HILL      ",0
        dc.b    "L LENGTH    ",0
        dc.b    "W E WIDTH   ",0
        dc.b    ", . BEND    ",0
        dc.b    "I COPY      ",0
        dc.b    "S SPLIT     ",0
        dc.b    "M MERGE     ",0
        dc.b    "DEL DELETE  ",0
        dc.b    "O OBJECT    ",0
t_keyo: dc.b    "OBJECT KEYS ",0
        dc.b    "T TYPE      ",0
        dc.b    "S SIDE      ",0
        dc.b    "M MOVE      ",0
        dc.b    "I O ADD     ",0
        dc.b    "DEL DELETE  ",0
        dc.b    "TAB BACK    ",0
        dc.b    "UP DOWN PICK",0
        dc.b    "L R SEGMENT ",0
        dc.b    "            ",0
        dc.b    "            ",0,0
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
        dc.b    "L/R PREVIOUS / NEXT SEGMENT",0
        dc.b    "U/D ONE GRID ROW (16 SEGMENTS)",0
        dc.b    "TAB / FIRE+DOWN  THE OBJECT LIST",0
        dc.b    "IN THE LIST: U/D AN OBJECT, L/R LEAVE",0
        dc.b    "HOME FIRST   B THE BAR   FIRE MENU",0
        dc.b    "F10 / ESC  LEAVE (KEEPS THE TRACK)",0
        dc.b    " ",0
        dc.b    "C CURVE  H HILL  L LENGTH  W E WIDTH",0
        dc.b    ", .  BEND LEFT / RIGHT",0
        dc.b    "I COPY  S SPLIT  M MERGE  DEL DELETE",0
        dc.b    "O ADD AN OBJECT   SHIFT+B PUT THE BAR",0
        dc.b    "T TYPE  S SIDE  M MOVE  DEL DELETE",0
        dc.b    "MOVE: L/R 10 UNITS, U/D A SEGMENT",0
        dc.b    "U UNDO  SHIFT+U REDO  K CHECK",0
        dc.b    "RETURN / SPACE  REPEAT THE LAST PICK",0
        dc.b    "P TEST DRIVE FROM THE CURSOR / OBJECT",0
        dc.b    " ",0
        dc.b    "TILES: SYMBOL = BEND, COLOUR = HILL",0
        dc.b    "A KEY: WHAT THE TILES MEAN",0
        dc.b    " ",0
        dc.b    "PRESS A KEY",0,0
        even
