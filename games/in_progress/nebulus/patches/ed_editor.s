; name: ed_editor
; media: hd
; default: no
; site: $377a2 $37a90 $3d6c4 $3adb4 $3d110 $3e352 $3dfd6
; ram: code $75740.. (dead zone, unverified block) + tables $76d40.. (zero gap), runtime state RS $77c80, vars V $77cc0, stack $77eb8; store at $BC000 (file NEBLEVEL.OVL)
; doc: work/notes/editor.md
; note: Nebulus campaign + level editor (NebEditor).  Hooks (jump table at CODE1): +0 ed_dec ($377a2 decode), +6 ed_dir ($37a90 spawn direction),
; note: +12 ed_title ($3d6c4 title poll, F10 = manager), +18 ed_time ($3adb4 initial time), +24 ed_name ($3d110 tower name), +30 ed_next ($3e352 tower complete),
; note: +36 ed_game ($3dfd6 frame flip, F10 in playtest).  Store (NEBLEVEL.OVL, OVSZ bytes, loaded at boot to OVS by the loader stub):
; note:   'NCMP' ver.w nlev.w ncamp.w (16 B header) | 8 campaigns x 32 B {name[12] cnt.b pad.b entry[16] pad[2]} | level records (variable):
; note:   {mission.b tower.b rows.b flags.b len.w time.w name[12], mask[rows*2], stream} in the game's own tower encoding.
; note: entry byte: bit7 set = original tower ($80 | (mission-1)<<3 | tower), else custom level index.

CODE1   equ     $75740
DATA    equ     $76d40
CODE2   equ     $77300
RS      equ     $77c80
V       equ     $77cc0
STK     equ     $77eb8
OVS     equ     $BC000
OVSZ    equ     $2000
TREC    equ     $BE000
ES      equ     $A0000
MB      equ     $A8000
GRID    equ     $327f0
LV0     equ     272                     ; offset of the first level record
REC     equ     20                      ; level record header size

; runtime state (persistent while the game runs)
rsCamp  equ     0                       ; active campaign + 1 (0 none)
rsPos   equ     2                       ; entry index in the active campaign
rsLvl   equ     4                       ; custom level + 1 playing now (0 = original tower, $7fff = playtest working copy)
rsEd    equ     6                       ; editor session active (working grid valid)
rsTest  equ     8                       ; playtest running
rsSlot  equ     10                      ; level slot being edited + 1 (0 = new)
rsMis   equ     12
rsTow   equ     14                      ; base tower (palette, backdrop, default time)
rsRows  equ     16
rsTime  equ     18
rsCx    equ     20
rsCy    equ     22
rsTop   equ     24
rsFrom  equ     26                      ; 0 editor entered from the title, 1 from the running game
rsName  equ     28                      ; 12 bytes

; editor variables (V)
vFrame  equ     0
vMode   equ     2                       ; 0 map, 1 menu, 3 name entry
vMenu   equ     4
vSel    equ     8
vMTop   equ     10
vPFire  equ     12
vRep    equ     14
vHeld   equ     16
vRedraw equ     18
vMsg    equ     20
vKind   equ     24
vCur    equ     26
vCamp   equ     28
vScr    equ     30                      ; 0 list screens, 1 editor map
vRes    equ     32                      ; result: 0 stay, 1 playtest, 2 play campaign/level, 3 quit to title
vSr     equ     34
vOld70  equ     36
vOld758 equ     40
vOffs   equ     44
vBaseH  equ     46
vBaseM  equ     47
vMis0   equ     48
vTow0   equ     50
vErr    equ     52
vGsp    equ     56
vPal    equ     60
vMfp    equ     92
vTile   equ     192
vNum    equ     124
vNPos   equ     156
vNDst   equ     158
vDirty  equ     162
vMBP    equ     164
vMCol   equ     168
vShow   equ     170
ETILE   equ     $A8800
rsOk    equ     40

        org     CODE1
        dc.w    $4ef9
        dc.l    ed_dec
        dc.w    $4ef9
        dc.l    ed_dir
        dc.w    $4ef9
        dc.l    ed_title
        dc.w    $4ef9
        dc.l    ed_time
        dc.w    $4ef9
        dc.l    ed_name
        dc.w    $4ef9
        dc.l    ed_next
        dc.w    $4ef9
        dc.l    ed_game

; ------------------------------------------------------------------ store helpers
; d0.w = level index -> a0 = record (0 if the store or the index is invalid)
lvl_ptr:
        bsr.w   ov_ok
        lea     OVS.l,a0
        cmpi.l  #'NCMP',(a0)
        bne.s   .bad
        cmp.w   6(a0),d0
        bhs.s   .bad
        lea     LV0(a0),a0
.l:     tst.w   d0
        beq.s   .r
        move.w  4(a0),d1
        lea     REC(a0,d1.w),a0
        subq.w  #1,d0
        bra.s   .l
.r:     rts
.bad:   suba.l  a0,a0
        rts

; a0 = end of the last level record (valid store assumed)
store_end:
        lea     OVS.l,a0
        move.w  6(a0),d0
        lea     LV0(a0),a0
        bra.s   .t
.l:     move.w  4(a0),d1
        lea     REC(a0,d1.w),a0
.t:     dbra    d0,.l
        rts

; d0.w = campaign index -> a0 (0 if invalid)
camp_ptr:
        bsr.w   ov_ok
        lea     OVS.l,a0
        cmpi.l  #'NCMP',(a0)
        bne.s   .bad
        cmp.w   8(a0),d0
        bhs.s   .bad
        lsl.w   #5,d0
        lea     16(a0,d0.w),a0
        rts
.bad:   suba.l  a0,a0
        rts

; the record of the level being played (rsLvl), a0 = 0 for an original tower
cur_rec:
        move.w  RS+rsLvl.l,d0
        beq.s   .none
        cmp.w   #$7fff,d0
        bne.s   .l
        lea     TREC.l,a0
        rts
.l:     subq.w  #1,d0
        bra.s   lvl_ptr
.none:  suba.l  a0,a0
        rts

; ------------------------------------------------------------------ game hooks
; decode hook ($377a2): custom level -> the game's own decode loop ($37812: d7 = rows, a0 = mask, a1 = stream, a2 = grid)
ed_dec:
        bsr.s   cur_rec
        move.l  a0,d0
        beq.s   .stock
        moveq   #0,d7
        move.b  2(a0),d7
        move.w  d7,$33912.l
        lea     GRID.l,a2
        move.w  #$3ff,d6
.clr:   clr.l   (a2)+
        dbra    d6,.clr
        lea     REC(a0),a0
        move.l  a0,a1
        adda.w  d7,a1
        adda.w  d7,a1
        lea     GRID.l,a2
        jmp     $37812.l
.stock: lea     GRID.l,a0
        jmp     $377a8.l

; spawn direction ($37a90, a0 = creature slot, a1 = marker cell): low nibble bit 0 = start in the negative direction
ed_dir:
        btst    #0,(a1)
        beq.s   .d
        neg.w   $54(a0)
.d:     move.l  a1,d0
        subi.l  #GRID,d0
        rts

; initial time ($3adb4: d0 = tower index in, BCD time out)
ed_time:
        add.w   d0,d0
        lea     $3ad9e.l,a0
        move.w  0(a0,d0.w),d0
        move.w  d0,-(a7)
        bsr.s   cur_rec
        move.w  (a7)+,d0
        move.l  a0,d1
        beq.s   .r
        move.w  6(a0),d1
        beq.s   .r
        move.w  d1,d0
.r:     rts

; tower name ($3d110: a0 = name table, d1 = tower index; out a0 = string; d0 preserved)
ed_name:
        lsl.w   #2,d1
        adda.w  d1,a0
        movea.l (a0),a0
        move.w  d0,-(a7)
        move.l  a0,-(a7)
        bsr.s   cur_rec
        move.l  a0,d0
        bne.s   .c
        move.l  (a7)+,a0
        move.w  (a7)+,d0
        rts
.c:     lea     8(a0),a0
        addq.l  #4,a7
        move.w  (a7)+,d0
        rts

; tower complete ($3e352)
ed_next:
        tst.w   RS+rsTest.l
        bne.w   pt_done
        move.w  RS+rsCamp.l,d0
        bne.s   .camp
        tst.w   RS+rsLvl.l
        bne.s   end_run
        move.w  $33a34.l,d0
        jmp     $3e358.l
.camp:  subq.w  #1,d0
        bsr.w   camp_ptr
        move.l  a0,d0
        beq.s   end_run
        move.w  RS+rsPos.l,d0
        addq.w  #1,d0
        move.w  d0,RS+rsPos.l
        moveq   #0,d1
        move.b  12(a0),d1
        cmp.w   d1,d0
        bhs.s   end_run
        move.b  14(a0,d0.w),d0
        bra.w   apply_entry
end_run:
        move.w  #8,$3390c.l
        clr.w   RS+rsCamp.l
        clr.w   RS+rsLvl.l
        rts

; d0.b = entry byte -> rsLvl, tower, mission, the player's tower word
apply_entry:
        moveq   #0,d1
        move.b  d0,d1
        tst.b   d0
        bpl.s   .cust
        move.w  d1,d2
        lsr.w   #3,d2
        and.w   #1,d2
        addq.w  #1,d2
        and.w   #7,d1
        clr.w   RS+rsLvl.l
        bra.s   .set
.cust:  move.w  d1,d0
        addq.w  #1,d1
        move.w  d1,RS+rsLvl.l
        bsr.w   lvl_ptr
        moveq   #1,d2
        moveq   #0,d1
        move.l  a0,d0
        beq.s   .set
        move.b  (a0),d2
        move.b  1(a0),d1
.set:   move.w  d2,$33910.l
        move.w  d1,$3390c.l
        move.w  d1,$33a44.l
        lea     $3e274.l,a0
        tst.w   $3391e.l
        beq.s   .p
        addq.l  #2,a0
.p:     move.w  d1,(a0)
        rts

; frame flip in the game ($3dfd6): F10 during a playtest -> editor
ed_game:
        cmpi.b  #$44,$38498.l
        bne.s   .n
        tst.w   RS+rsTest.l
        beq.s   .n
        clr.b   $38498.l
        bra.w   pt_done
.n:     jmp     $3868a.l

; playtest ended (level complete or F10) -> editor, then restart the playtest or leave
pt_done:
        move.w  #1,RS+rsFrom.l
        bsr.w   ed_run
        bra.w   run_result

; d0 = vRes after the editor returns inside the game
run_result:
        lea     $800.l,a7
        cmp.w   #3,d0
        beq.s   .title
        jmp     $3dbb0.l
.title: clr.w   RS+rsTest.l
        jmp     $3db8c.l

; title poll ($3d6c4): F10 = manager; a finished playtest (game over) returns to the editor
ed_title:
        jsr     $3853a.l
        tst.w   RS+rsTest.l
        beq.s   .nt
        clr.w   RS+rsFrom.l
        bsr.w   ed_run
        bra.s   .res
.nt:    clr.w   RS+rsCamp.l
        clr.w   RS+rsLvl.l
        clr.w   $33a44.l
        cmpi.b  #$44,$38498.l
        bne.s   .no
        clr.b   $38498.l
        clr.w   RS+rsFrom.l
        bsr.w   ed_run
.res:   addq.l  #4,a7
        tst.w   d0
        beq.s   .back
        cmp.w   #3,d0
        beq.s   .back
        jmp     $3d85a.l
.back:  jmp     $3d5e2.l
.no:    tst.w   $338f0.l
        rts

; ------------------------------------------------------------------ own VBL
ed_vbl:
        move.b  #0,$ffff8260.w
        movem.l d0-d7/a0-a6,-(a7)
        lea     pal(pc),a0
        lea     $ffff8240.w,a1
        moveq   #7,d0
.p:     move.l  (a0)+,(a1)+
        dbra    d0,.p
        addq.w  #1,V+vFrame.l
        jsr     $33d02.l
        movem.l (a7)+,d0-d7/a0-a6
        rte

pal:    dc.w    $000,$333,$0a0,$5a2,$666,$35f,$fea,$f40
        dc.w    $520,$630,$740,$750,$760,$770,$771,$777

; ------------------------------------------------------------------ editor main: returns d0 = vRes
ed_run:
        movem.l d1-d7/a0-a6,-(a7)
        lea     V.l,a5
        move.l  a5,a0
        moveq   #63,d0
.zv:    clr.l   (a0)+
        dbra    d0,.zv
        bsr.w   tiles_init
        bsr.w   ov_ok
        move.w  sr,vSr(a5)
        ori.w   #$700,sr
        move.l  $70.w,vOld70(a5)
        move.l  $38758.l,vOld758(a5)
        move.w  $33a38.l,vOffs(a5)
        move.b  $ffff8201.w,vBaseH(a5)
        move.b  $ffff8203.w,vBaseM(a5)
        move.w  $33910.l,vMis0(a5)
        move.w  $3390c.l,vTow0(a5)
        lea     $ffff8240.w,a0
        lea     vPal(a5),a1
        moveq   #7,d0
.sp:    move.l  (a0)+,(a1)+
        dbra    d0,.sp
        clr.b   $fffffa1b.w
        move.l  #ed_vbl,$70.w
        move.b  #$0a,$ffff8201.w
        clr.b   $ffff8203.w
        move.w  #$2300,sr
        clr.b   $38498.l
        clr.w   RS+rsTest.l
        tst.w   RS+rsEd.l
        beq.s   .fresh
        ; resume the playtested session: working copy back into the grid
        move.w  #$7fff,RS+rsLvl.l
        move.w  RS+rsTow.l,$3390c.l
        move.w  RS+rsMis.l,$33910.l
        jsr     $377a2.l
        clr.w   RS+rsLvl.l
        move.w  #1,vScr(a5)
        move.w  #1,vDirty(a5)
        bra.s   .go
.fresh: bsr.w   m_main
.go:    move.w  #3,vRedraw(a5)
.loop:  bsr.w   redraw
        move.w  vFrame(a5),d0
.w:     cmp.w   vFrame(a5),d0
        beq.s   .w
        jsr     $3853a.l
        cmpi.b  #$44,$38498.l
        bne.s   .nk
        clr.b   $38498.l
        bsr.w   f10
.nk:    bsr.w   input
        tst.w   vRes(a5)
        beq.s   .loop
        move.w  #$2700,sr
        move.l  vOld70(a5),$70.w
        move.l  vOld758(a5),$38758.l
        move.w  vOffs(a5),$33a38.l
        move.b  vBaseH(a5),$ffff8201.w
        move.b  vBaseM(a5),$ffff8203.w
        lea     vPal(a5),a0
        lea     $ffff8240.w,a1
        moveq   #7,d0
.rp:    move.l  (a0)+,(a1)+
        dbra    d0,.rp
        clr.b   $38498.l
        move.w  #$ffff,$3849a.l
        move.w  vRes(a5),d0
        cmp.w   #1,d0
        beq.s   .keep
        cmp.w   #2,d0
        beq.s   .rest
        ; 3: quit to the title (original game): restore the title's mission/tower
        move.w  vMis0(a5),$33910.l
        move.w  vTow0(a5),$3390c.l
.rest:  clr.w   RS+rsEd.l
.keep:  move.w  vSr(a5),sr
        movem.l (a7)+,d1-d7/a0-a6
        rts

; F10: editor -> list screen, list -> quit
f10:    tst.w   vScr(a5)
        beq.s   .q
        tst.w   vMode(a5)
        bne.s   .r
        bra.w   c_leaveed
.q:     move.w  #3,vRes(a5)
.r:     rts

; ------------------------------------------------------------------ drawing
redraw:
        move.w  vRedraw(a5),d0
        beq.s   .none
        clr.w   vRedraw(a5)
        moveq   #0,d1
        tst.w   vScr(a5)
        beq.s   .m
        tst.w   vMode(a5)
        beq.s   .ed
.m:     moveq   #1,d1
.ed:    cmp.w   vShow(a5),d1
        beq.s   .same
        or.w    #1,d0
.same:  move.w  d1,vShow(a5)
        tst.w   d1
        beq.s   .map
        bsr.w   clr_screen
        cmp.w   #3,vMode(a5)
        beq.w   draw_name
        bra.w   draw_menu
.map:   btst    #0,d0
        beq.s   .pan
        bsr.w   clr_screen
        bsr.w   draw_map
        bsr.w   draw_cursor
.pan:   bra.w   draw_panel
.none:  rts

clr_screen:
        lea     ES.l,a0
        move.w  #7999,d0
        moveq   #0,d1
.c:     move.l  d1,(a0)+
        dbra    d0,.c
        rts

; the tower map: 22 lines x 16 columns of 16x8 pixel cells, top row rsTop; the frog start (column 0, row 2) is marked when empty
draw_map:
        moveq   #0,d5
.ln:    move.w  RS+rsTop.l,d4
        sub.w   d5,d4
        bmi.s   .skip
        cmp.w   RS+rsRows.l,d4
        bge.s   .skip
        moveq   #0,d6
.cl:    move.w  d6,d0
        lsl.w   #8,d0
        lea     GRID.l,a0
        adda.w  d0,a0
        move.b  0(a0,d4.w),d0
        move.w  d6,d1
        move.w  d5,d2
        tst.b   d0
        bne.s   .n
        cmp.w   #2,d4
        bne.s   .n
        tst.w   d6
        bne.s   .n
        bsr.w   draw_cellf
        bra.s   .nx
.n:     bsr.w   draw_cell
.nx:    addq.w  #1,d6
        cmp.w   #16,d6
        blt.s   .cl
.skip:  addq.w  #1,d5
        cmp.w   #22,d5
        blt.s   .ln
        rts

; d0.b = cell value, d1 = column 0..15, d2 = 8-pixel line index
draw_cellf:
        movem.l d0-d7/a0-a2,-(a7)
        move.w  d1,d7
        move.w  d2,d6
        moveq   #16,d3
        bra.s   draw_id
draw_cell:
        movem.l d0-d7/a0-a2,-(a7)
        move.w  d1,d7
        move.w  d2,d6
        bsr.w   classify
draw_id:
        lea     ETILE.l,a1
        move.w  d3,d2
        lsl.w   #4,d2
        adda.w  d2,a1
        lea     vTile(a5),a2
        move.l  (a1)+,(a2)+
        move.l  (a1)+,(a2)+
        move.l  (a1)+,(a2)+
        move.l  (a1)+,(a2)+
        lea     tiles(pc),a1
        mulu.w  #10,d3
        moveq   #0,d5
        move.b  8(a1,d3.w),d5
        lea     vTile(a5),a2
        tst.b   d0
        bmi.s   .nodir
        move.b  d0,d1
        and.b   #$70,d1
        beq.s   .nodir
        lsr.b   #4,d1
        btst    #0,d0
        bne.s   .neg
        cmp.b   #4,d1
        beq.s   .up
        cmp.b   #5,d1
        beq.s   .up
        or.w    #$0003,6(a2)
        or.w    #$0003,8(a2)
        bra.s   .nodir
.neg:   cmp.b   #4,d1
        beq.s   .dn
        cmp.b   #5,d1
        beq.s   .dn
        or.w    #$c000,6(a2)
        or.w    #$c000,8(a2)
        bra.s   .nodir
.up:    or.w    #$0ff0,(a2)
        bra.s   .nodir
.dn:    or.w    #$0ff0,14(a2)
.nodir: lea     ES.l,a0
        mulu.w  #1280,d6
        adda.l  d6,a0
        lsl.w   #3,d7
        adda.w  d7,a0
        moveq   #0,d1
        btst    #0,d5
        sne     d1
        ext.w   d1
        moveq   #0,d2
        btst    #1,d5
        sne     d2
        ext.w   d2
        moveq   #0,d3
        btst    #2,d5
        sne     d3
        ext.w   d3
        moveq   #7,d7
.row:   move.w  (a2)+,d4
        move.w  d4,d0
        and.w   d1,d0
        move.w  d0,(a0)
        move.w  d4,d0
        and.w   d2,d0
        move.w  d0,2(a0)
        move.w  d4,d0
        and.w   d3,d0
        move.w  d0,4(a0)
        clr.w   6(a0)
        lea     160(a0),a0
        dbra    d7,.row
        movem.l (a7)+,d0-d7/a0-a2
        rts

; d0.b = cell value -> d3 = tile id
classify:
        moveq   #0,d3
        tst.b   d0
        beq.s   .r
        bmi.s   .t
        move.b  d0,d1
        lsr.b   #4,d1
        and.b   #7,d1
        moveq   #1,d3
        tst.b   d1
        beq.s   .r
        moveq   #8,d3
        add.b   d1,d3
.r:     rts
.t:     move.b  d0,d1
        and.b   #3,d1
        moveq   #7,d3
        cmp.b   #3,d1
        bne.s   .n3
        btst    #6,d0
        beq.s   .r
        moveq   #8,d3
        rts
.n3:    moveq   #4,d3
        tst.b   d1
        beq.s   .r
        moveq   #5,d3
        cmp.b   #2,d1
        beq.s   .r
        moveq   #6,d3
        move.b  d0,d1
        and.b   #$0c,d1
        bne.s   .r
        moveq   #2,d3
        move.b  d0,d1
        and.b   #$70,d1
        beq.s   .r
        moveq   #3,d3
        rts

; cursor: XOR a 16x8 box over the cell (call again to erase)
draw_cursor:
        movem.l d0-d2/a0,-(a7)
        move.w  RS+rsTop.l,d0
        sub.w   RS+rsCy.l,d0
        bmi.s   .x
        cmp.w   #22,d0
        bge.s   .x
        mulu.w  #1280,d0
        lea     ES.l,a0
        adda.l  d0,a0
        move.w  RS+rsCx.l,d1
        lsl.w   #3,d1
        adda.w  d1,a0
        moveq   #7,d1
.l:     tst.w   d1
        beq.s   .full
        cmp.w   #7,d1
        beq.s   .full
        eori.w  #$8001,(a0)
        eori.w  #$8001,2(a0)
        eori.w  #$8001,4(a0)
        bra.s   .nx
.full:  eori.w  #$ffff,(a0)
        eori.w  #$ffff,2(a0)
        eori.w  #$ffff,4(a0)
.nx:    lea     160(a0),a0
        dbra    d1,.l
.x:     movem.l (a7)+,d0-d2/a0
        rts

; the right-hand panel (8 characters) and the status line (cell name, help or message)
draw_panel:
        lea     ES+128.l,a0
        move.w  #175,d0
        moveq   #0,d1
.l:     moveq   #7,d2
        move.l  a0,a1
.c:     move.l  d1,(a1)+
        dbra    d2,.c
        lea     160(a0),a0
        dbra    d0,.l
        lea     ES+28160.l,a0
        move.w  #959,d0
.s:     move.l  d1,(a0)+
        dbra    d0,.s
        lea     vNum(a5),a2
        move.b  #'T',(a2)+
        move.w  RS+rsTow.l,d0
        addq.w  #1,d0
        bsr.w   dec1
        move.b  #' ',(a2)+
        move.b  #'M',(a2)+
        move.w  RS+rsMis.l,d0
        bsr.w   dec1
        clr.b   (a2)
        moveq   #0,d2
        bsr.w   pline
        lea     vNum(a5),a2
        move.b  #'H',(a2)+
        move.w  RS+rsRows.l,d0
        bsr.w   dec3
        clr.b   (a2)
        moveq   #1,d2
        bsr.w   pline
        lea     vNum(a5),a2
        move.b  #'C',(a2)+
        move.w  RS+rsCx.l,d0
        bsr.w   dec3
        clr.b   (a2)
        moveq   #2,d2
        bsr.w   pline
        lea     vNum(a5),a2
        move.b  #'R',(a2)+
        move.w  RS+rsCy.l,d0
        bsr.w   dec3
        clr.b   (a2)
        moveq   #3,d2
        bsr.w   pline
        bsr.w   cur_cell
        lea     vNum(a5),a2
        move.b  #'$',(a2)+
        bsr.w   hex2
        clr.b   (a2)
        moveq   #4,d2
        bsr.w   pline
        bsr.w   cur_cell
        bsr.w   classify
        lea     names(pc),a0
        add.w   d3,d3
        move.w  0(a0,d3.w),d3
        lea     names(pc),a0
        adda.w  d3,a0
        moveq   #0,d1
        moveq   #11,d2
        bsr.w   txt
        move.l  vMsg(a5),d0
        bne.s   .m
        lea     sHelp(pc),a0
        bra.s   .h
.m:     move.l  d0,a0
.h:     moveq   #19,d1
        moveq   #11,d2
        bra.w   txt

; text line from vNum in the right panel (column 32), line d2
pline:  lea     vNum(a5),a0
        moveq   #32,d1
        bra.w   txt

draw_menu:
        move.l  vMenu(a5),a0
        moveq   #0,d6
        move.b  (a0)+,d6                ; count
        moveq   #0,d5                   ; item index
        move.w  vMTop(a5),d4
.it:    addq.l  #2,a0
        move.l  a0,-(a7)                ; text start
.sk:    tst.b   (a0)+
        bne.s   .sk
        move.l  a0,-(a7)                ; next item
        move.w  d5,d0
        sub.w   d4,d0
        bmi.s   .skip
        cmp.w   #12,d0
        bge.s   .skip
        move.l  4(a7),a0
        lea     vNum(a5),a2
        move.b  #' ',(a2)+
        cmp.w   vSel(a5),d5
        bne.s   .ns
        move.b  #'>',-1(a2)
.ns:    bsr.w   cpstr
        clr.b   (a2)
        lea     vNum(a5),a0
        move.w  vMCol(a5),d1
        move.w  d0,d2
        bsr.w   txt
.skip:  move.l  (a7)+,a0
        addq.l  #4,a7
        addq.w  #1,d5
        cmp.w   d6,d5
        blt.s   .it
        move.l  vMsg(a5),d0
        beq.s   .nm
        tst.w   vScr(a5)
        bne.s   .nm
        move.l  d0,a0
        moveq   #22,d1
        moveq   #11,d2
        bsr.w   txt
.nm:    rts

draw_name:
        lea     vNum(a5),a2
        lea     sName(pc),a0
        bsr.w   cpstr
        move.l  vNDst(a5),a0
        moveq   #11,d0
.c:     move.b  (a0)+,(a2)+
        dbra    d0,.c
        clr.b   (a2)
        lea     vNum(a5),a0
        moveq   #8,d1
        moveq   #0,d2
        bsr.w   txt
        lea     sNameH(pc),a0
        moveq   #8,d1
        moveq   #3,d2
        bsr.w   txt
        lea     sNameH2(pc),a0
        moveq   #8,d1
        moveq   #4,d2
        bsr.w   txt
        lea     vNum(a5),a2
        moveq   #15,d0
.b:     move.b  #' ',(a2)+
        dbra    d0,.b
        clr.b   (a2)
        move.w  vNPos(a5),d0
        lea     vNum+5(a5),a2
        adda.w  d0,a2
        move.b  #'^',(a2)
        lea     vNum(a5),a0
        moveq   #8,d1
        moveq   #1,d2
        bra.w   txt

; current cell value -> d0.b
cur_cell:
        move.w  RS+rsCx.l,d0
        lsl.w   #8,d0
        lea     GRID.l,a0
        adda.w  d0,a0
        move.w  RS+rsCy.l,d0
        move.b  0(a0,d0.w),d0
        rts

; text: a0 string, d1 = x8 column, d2 = 16-pixel line
txt:    movem.l d0-d3/a0-a2,-(a7)
        move.l  #ES,$38758.l
        mulu.w  #2560,d2
        move.w  d1,d3
        lsr.w   #1,d1
        lsl.w   #3,d1
        and.w   #1,d3
        add.w   d3,d1
        add.w   d2,d1
        move.w  d1,$33a38.l
        jsr     $3b344.l
        movem.l (a7)+,d0-d3/a0-a2
        rts

; string helpers: a0 = NUL-terminated source -> appended at a2 (a2 advanced, a0 left after the NUL)
cpstr:  move.b  (a0)+,(a2)+
        bne.s   cpstr
        subq.l  #1,a2
        rts
dec1:   and.w   #$f,d0
        add.b   #'0',d0
        move.b  d0,(a2)+
        rts
dec3:   ext.l   d0
        divu.w  #100,d0
        add.b   #'0',d0
        move.b  d0,(a2)+
        swap    d0
        ext.l   d0
        divu.w  #10,d0
        add.b   #'0',d0
        move.b  d0,(a2)+
        swap    d0
        add.b   #'0',d0
        move.b  d0,(a2)+
        rts
hex2:   move.w  d0,-(a7)
        lsr.b   #4,d0
        bsr.s   hexd
        move.w  (a7)+,d0
hexd:   and.b   #$f,d0
        cmp.b   #10,d0
        blt.s   .d
        addq.b  #7,d0
.d:     add.b   #'0',d0
        move.b  d0,(a2)+
        rts

; ------------------------------------------------------------------ input
input:
        move.w  $338f0.l,d3
        move.w  $338f2.l,d1
        move.w  $338f4.l,d2
        move.w  vPFire(a5),d4
        move.w  d3,vPFire(a5)
        tst.w   d3
        beq.s   .nofire
        tst.w   d4
        bne.s   .nofire
        bra.w   fire_edge
.nofire:
        move.w  d1,d0
        or.w    d2,d0
        bne.s   .mv
        clr.w   vRep(a5)
        clr.w   vHeld(a5)
        rts
.mv:    move.w  vRep(a5),d0
        beq.s   .go
        subq.w  #1,d0
        move.w  d0,vRep(a5)
        rts
.go:    move.w  #4,vRep(a5)
        tst.w   vHeld(a5)
        bne.s   .rp
        move.w  #1,vHeld(a5)
        move.w  #14,vRep(a5)
.rp:    move.w  vMode(a5),d0
        beq.w   move_map
        cmp.w   #3,d0
        beq.w   move_name
        bra.w   move_menu

move_map:
        bsr.w   draw_cursor
        move.w  RS+rsCx.l,d0
        add.w   d1,d0
        and.w   #15,d0
        move.w  d0,RS+rsCx.l
        move.w  RS+rsCy.l,d0
        add.w   d2,d0
        bpl.s   .p
        moveq   #0,d0
.p:     move.w  RS+rsRows.l,d3
        subq.w  #1,d3
        cmp.w   d0,d3
        bge.s   .ok
        move.w  d3,d0
.ok:    move.w  d0,RS+rsCy.l
        move.w  RS+rsTop.l,d1
        cmp.w   d1,d0
        ble.s   .t2
        move.w  d0,RS+rsTop.l
        bra.s   .rd
.t2:    sub.w   #21,d1
        cmp.w   d1,d0
        bge.s   .nr
        add.w   #21,d0
        move.w  d0,RS+rsTop.l
.rd:    move.w  #3,vRedraw(a5)
        rts
.nr:    bsr.w   draw_cursor
        move.w  #2,vRedraw(a5)
        clr.l   vMsg(a5)
        rts

move_menu:
        move.w  vSel(a5),d0
        sub.w   d2,d0
        bpl.s   .a
        moveq   #0,d0
.a:     move.l  vMenu(a5),a0
        moveq   #0,d3
        move.b  (a0),d3
        subq.w  #1,d3
        cmp.w   d3,d0
        ble.s   .b
        move.w  d3,d0
.b:     move.w  d0,vSel(a5)
        tst.w   d1
        bpl.s   .win
        move.w  d3,vSel(a5)
        bra.w   menu_exec               ; left = the last item ("< back")
.win:   move.w  vMTop(a5),d1
        cmp.w   d1,d0
        bge.s   .w2
        move.w  d0,vMTop(a5)
        bra.s   .w3
.w2:    sub.w   #11,d0
        cmp.w   d1,d0
        ble.s   .w3
        move.w  d0,vMTop(a5)
.w3:    move.w  #2,vRedraw(a5)
        rts

fire_edge:
        move.w  vMode(a5),d0
        cmp.w   #3,d0
        beq.w   name_done
        tst.w   d0
        bne.w   menu_exec
        ; map: open the cell menu
        move.w  #8,vMCol(a5)
        lea     m_root(pc),a0
        bsr.w   menu_open
        rts

; a0 = menu -> shown
menu_open:
        move.l  a0,vMenu(a5)
        clr.w   vSel(a5)
        clr.w   vMTop(a5)
        move.w  #1,vMode(a5)
        move.w  #2,vRedraw(a5)
        rts

; item vSel of the current menu -> a0 at its action byte
menu_item:
        move.l  vMenu(a5),a0
        addq.l  #1,a0
        move.w  vSel(a5),d0
        beq.s   .r
        subq.w  #1,d0
.s:     addq.l  #2,a0
.z:     tst.b   (a0)+
        bne.s   .z
        dbra    d0,.s
.r:     rts

; actions: 0 cell, 1 cell x3, 2 submenu, 3 enemy kind, 4 command, 5 enemy direction, 6 level, 7 campaign, 8 level op, 9 campaign op, 10 entry, 11 entry op
menu_exec:
        bsr.s   menu_item
        move.b  (a0)+,d0
        moveq   #0,d1
        move.b  (a0),d1
        and.w   #$ff,d0
        add.w   d0,d0
        lea     acts(pc),a0
        move.w  0(a0,d0.w),d0
        jmp     0(a0,d0.w)

acts:   dc.w    a_set-acts,a_tri-acts,a_sub-acts,a_enemy-acts,a_cmd-acts,a_edir-acts,a_lvl-acts,a_camp-acts,a_lop-acts,a_cop-acts,a_ent-acts,a_eop-acts

a_set:  move.w  d1,d0
        bsr.w   place
        bra.w   a_done
a_tri:  move.w  d1,d3
        move.w  RS+rsCy.l,-(a7)
        moveq   #2,d4
.t1:    move.w  d3,d0
        bsr.w   place
        move.w  RS+rsCy.l,d0
        addq.w  #1,d0
        cmp.w   RS+rsRows.l,d0
        bge.s   .t2
        move.w  d0,RS+rsCy.l
        dbra    d4,.t1
.t2:    move.w  (a7)+,RS+rsCy.l
        bra.w   a_done
a_sub:  lea     menus(pc),a0
        add.w   d1,d1
        move.w  0(a0,d1.w),d1
        lea     menus(pc),a0
        adda.w  d1,a0
        bra.w   menu_open
a_enemy:
        move.w  d1,vKind(a5)
        cmp.b   #$30,d1
        beq.s   .nodir
        lea     m_dirh(pc),a0
        cmp.b   #$40,d1
        blt.s   .sm
        cmp.b   #$60,d1
        bge.s   .sm
        lea     m_dirv(pc),a0
.sm:    bra.w   menu_open
.nodir: move.w  vKind(a5),d0
        bsr.w   place_enemy
        bra.w   a_done
a_edir: move.w  vKind(a5),d0
        or.w    d1,d0
        bsr.w   place_enemy
a_done: tst.w   vScr(a5)
        beq.w   m_main
        clr.w   vMode(a5)
        move.w  #3,vRedraw(a5)
        rts

; d0 = cell value -> grid at cursor
place:  movem.l d0-d1/a0,-(a7)
        move.w  RS+rsCx.l,d1
        lsl.w   #8,d1
        lea     GRID.l,a0
        adda.w  d1,a0
        move.w  RS+rsCy.l,d1
        move.b  d0,0(a0,d1.w)
        move.w  #1,vDirty(a5)
        movem.l (a7)+,d0-d1/a0
        rts

; enemy marker with warnings (d0 = marker)
place_enemy:
        move.w  d0,-(a7)
        bsr.s   place
        move.w  (a7)+,d0
        clr.l   vMsg(a5)
        move.w  d0,d1
        and.w   #$70,d1
        cmp.w   #$40,d1
        blt.s   .ground
        cmp.w   #$60,d1
        bge.s   .ok
        move.w  RS+rsCx.l,d1
        lsl.w   #8,d1
        lea     GRID.l,a0
        adda.w  d1,a0
        move.w  RS+rsCy.l,d2
        move.w  d2,d3
.up:    addq.w  #1,d3
        cmp.w   RS+rsRows.l,d3
        bge.s   .bad
        tst.b   0(a0,d3.w)
        bpl.s   .up
.dn:    subq.w  #1,d2
        bmi.s   .bad
        tst.b   0(a0,d2.w)
        bpl.s   .dn
        rts
.bad:   lea     sWarnEye(pc),a0
        move.l  a0,vMsg(a5)
.ok:    rts
.ground:
        move.w  RS+rsCx.l,d1
        lsl.w   #8,d1
        lea     GRID.l,a0
        adda.w  d1,a0
        move.w  RS+rsCy.l,d2
        subq.w  #1,d2
        bmi.s   .nl
        tst.b   0(a0,d2.w)
        bmi.s   .ok
.nl:    lea     sWarnLedge(pc),a0
        move.l  a0,vMsg(a5)
        rts

; ------------------------------------------------------------------ commands (param d1)
a_cmd:  lea     cmds(pc),a0
        add.w   d1,d1
        move.w  0(a0,d1.w),d1
        jmp     0(a0,d1.w)

cmds:   dc.w    m_main-cmds,m_levels-cmds,m_camps-cmds,c_newlvl-cmds,c_newcamp-cmds,c_quit-cmds,c_save-cmds,c_edroot-cmds
        dc.w    c_leaveed-cmds,c_look-cmds,c_mis-cmds,c_copyorig-cmds,c_blank-cmds,c_tup-cmds,c_tdn-cmds,c_rename-cmds
        dc.w    c_play-cmds,c_addent-cmds,cp_edit-cmds

; --- main menu / list screens
m_main: clr.w   vScr(a5)
        move.w  #8,vMCol(a5)
        lea     m_mainm(pc),a0
        bsr.w   menu_open
        move.w  #3,vRedraw(a5)
        rts

c_quit: move.w  #3,vRes(a5)
        rts

c_edroot:
        clr.w   vMode(a5)
        move.w  #2,vRedraw(a5)
        rts

; level list (dynamic): "name" (6,i), "<new level>", "< back"
m_levels:
        clr.w   vScr(a5)
        move.w  #8,vMCol(a5)
        lea     MB.l,a2
        clr.b   (a2)+
        move.l  a2,vMBP(a5)
        lea     OVS.l,a0
        moveq   #0,d3
        cmpi.l  #'NCMP',(a0)
        bne.s   .nl
        move.w  6(a0),d3
.nl:    moveq   #0,d2
        bra.s   .t
.l:     move.w  d2,d0
        bsr.w   lvl_ptr
        lea     8(a0),a0
        moveq   #6,d0
        move.w  d2,d1
        bsr.w   mb_add
        addq.w  #1,d2
.t:     cmp.w   d3,d2
        blt.s   .l
        lea     sNewLvl(pc),a0
        moveq   #4,d0
        moveq   #3,d1
        bsr.w   mb_add
        lea     sBack(pc),a0
        moveq   #4,d0
        moveq   #0,d1
        bsr.w   mb_add
        lea     MB.l,a0
        bsr.w   menu_open
        move.w  #3,vRedraw(a5)
        rts

; campaign list (dynamic): "name" (7,i), "<new campaign>", "< back"
m_camps:
        clr.w   vScr(a5)
        move.w  #8,vMCol(a5)
        lea     MB.l,a2
        clr.b   (a2)+
        move.l  a2,vMBP(a5)
        lea     OVS.l,a0
        moveq   #0,d3
        cmpi.l  #'NCMP',(a0)
        bne.s   .nl
        move.w  8(a0),d3
.nl:    moveq   #0,d2
        bra.s   .t
.l:     move.w  d2,d0
        bsr.w   camp_ptr
        moveq   #7,d0
        move.w  d2,d1
        bsr.w   mb_add
        addq.w  #1,d2
.t:     cmp.w   d3,d2
        blt.s   .l
        lea     sNewCamp(pc),a0
        moveq   #4,d0
        moveq   #4,d1
        bsr.w   mb_add
        lea     sBack(pc),a0
        moveq   #4,d0
        moveq   #0,d1
        bsr.w   mb_add
        lea     MB.l,a0
        bsr.w   menu_open
        move.w  #3,vRedraw(a5)
        rts

; append an item: a0 = text (12 chars max, NUL or padded), d0.b = action, d1.b = param
mb_add: move.l  vMBP(a5),a2
        move.b  d0,(a2)+
        move.b  d1,(a2)+
        moveq   #14,d0
.c:     move.b  (a0)+,d1
        beq.s   .e
        move.b  d1,(a2)+
        dbra    d0,.c
.e:     clr.b   (a2)+
        move.l  a2,vMBP(a5)
        lea     MB.l,a2
        addq.b  #1,(a2)
        rts

; level selected: submenu
a_lvl:  move.w  d1,vCur(a5)
        lea     m_lvl(pc),a0
        bra.w   menu_open

a_camp: move.w  d1,vCur(a5)
        lea     m_camp(pc),a0
        bra.w   menu_open

; level operations: 0 play, 1 edit, 2 copy, 3 delete
a_lop:  move.w  vCur(a5),d2
        tst.w   d1
        beq.w   lv_play
        cmp.w   #1,d1
        beq.w   lv_edit
        cmp.w   #2,d1
        beq.w   lv_copy
        bra.w   lv_delete

; campaign operations: 0 play, 1 edit entries, 2 rename, 3 delete
a_cop:  move.w  vCur(a5),d2
        move.w  d2,vCamp(a5)
        tst.w   d1
        beq.w   cp_play
        cmp.w   #1,d1
        beq.w   cp_edit
        cmp.w   #2,d1
        beq.w   cp_rename
        bra.w   cp_delete

; --- levels
lv_play:
        move.w  d2,d0
        bsr.w   lvl_ptr
        move.l  a0,d0
        beq.w   a_done
        clr.w   RS+rsCamp.l
        addq.w  #1,d2
        move.w  d2,RS+rsLvl.l
        moveq   #0,d1
        move.b  1(a0),d1
        moveq   #0,d2
        move.b  (a0),d2
        move.w  d1,$3390c.l
        move.w  d2,$33910.l
        move.w  d1,$33a44.l
        move.w  #2,vRes(a5)
        rts

; edit level d2: load it into the grid
lv_edit:
        move.w  d2,d0
        bsr.w   lvl_ptr
        move.l  a0,d0
        beq.w   a_done
        lea     RS+rsName.l,a1
        moveq   #11,d0
.n:     move.b  8(a0,d0.w),0(a1,d0.w)
        dbra    d0,.n
        moveq   #0,d0
        move.b  (a0),d0
        move.w  d0,RS+rsMis.l
        move.b  1(a0),d0
        move.w  d0,RS+rsTow.l
        move.b  2(a0),d0
        move.w  d0,RS+rsRows.l
        move.w  6(a0),RS+rsTime.l
        addq.w  #1,d2
        move.w  d2,RS+rsSlot.l
        move.w  d2,RS+rsLvl.l
        move.w  RS+rsTow.l,$3390c.l
        move.w  RS+rsMis.l,$33910.l
        jsr     $377a2.l
        clr.w   RS+rsLvl.l
        clr.w   vDirty(a5)
        bra.w   ed_begin

c_newlvl:
        clr.w   RS+rsSlot.l
        bsr.w   c_blank
        lea     sNewName(pc),a0
        lea     RS+rsName.l,a1
        moveq   #11,d0
.n:     move.b  (a0)+,(a1)+
        dbra    d0,.n
        move.w  #1,RS+rsMis.l
        clr.w   RS+rsTow.l
        move.w  #$0450,RS+rsTime.l
        bra.w   ed_begin

; editor opened on the working grid
ed_begin:
        move.w  #8,vMCol(a5)
        move.w  #1,RS+rsEd.l
        move.w  #1,vScr(a5)
        clr.w   RS+rsCx.l
        move.w  #1,RS+rsCy.l
        move.w  #21,RS+rsTop.l
        clr.w   vMode(a5)
        clr.l   vMsg(a5)
        move.w  #3,vRedraw(a5)
        rts

lv_copy:
        move.w  d2,d0
        bsr.w   lvl_ptr
        move.l  a0,d0
        beq.w   a_done
        move.l  a0,a3
        moveq   #0,d3
        move.w  4(a3),d3
        add.w   #REC,d3
        bsr.w   store_end
        lea     OVS+OVSZ.l,a1
        suba.l  a0,a1
        cmpa.l  d3,a1
        blt.w   no_room
        move.l  a0,a1
.c:     move.b  (a3)+,(a1)+
        subq.w  #1,d3
        bne.s   .c
        addq.w  #1,OVS+6.l
        bra.w   m_levels

no_room:
        lea     sFull(pc),a0
        move.l  a0,vMsg(a5)
        move.w  #2,vRedraw(a5)
        rts

; delete level d2: close the gap, fix the campaigns
lv_delete:
        move.w  d2,d0
        bsr.w   lvl_ptr
        move.l  a0,d0
        beq.w   a_done
        moveq   #0,d3
        move.w  4(a0),d3
        add.w   #REC,d3
        move.l  a0,a3
        lea     0(a0,d3.l),a1
        move.l  a0,-(a7)
        bsr.w   store_end
        move.l  a0,a2
        move.l  (a7)+,a0
.m:     cmp.l   a2,a1
        bhs.s   .md
        move.b  (a1)+,(a0)+
        bra.s   .m
.md:    subq.w  #1,OVS+6.l
        ; campaigns: drop / renumber custom references
        move.w  OVS+8.l,d5
        lea     OVS+16.l,a1
        bra.s   .ct
.cl:    moveq   #0,d4
        move.b  12(a1),d4
        lea     14(a1),a0
        move.l  a0,a2
        moveq   #0,d6                   ; new count
        bra.s   .et
.el:    move.b  (a0)+,d0
        bmi.s   .keep
        cmp.b   d2,d0
        beq.s   .drop
        blo.s   .keep
        subq.b  #1,d0
.keep:  move.b  d0,(a2)+
        addq.w  #1,d6
.drop:
.et:    dbra    d4,.el
        move.b  d6,12(a1)
        lea     32(a1),a1
.ct:    dbra    d5,.cl
        bra.w   m_levels

; --- campaigns
cp_play:
        move.w  d2,d0
        bsr.w   camp_ptr
        move.l  a0,d0
        beq.w   a_done
        tst.b   12(a0)
        beq.w   a_done
        addq.w  #1,d2
        move.w  d2,RS+rsCamp.l
        clr.w   RS+rsPos.l
        move.b  14(a0),d0
        bsr.w   apply_entry
        move.w  #2,vRes(a5)
        rts

cp_rename:
        move.w  d2,d0
        bsr.w   camp_ptr
        move.l  a0,vNDst(a5)
        bra.w   name_begin

cp_delete:
        move.w  d2,d0
        bsr.w   camp_ptr
        move.l  a0,d0
        beq.w   a_done
        lea     32(a0),a1
        lea     OVS+16.l,a2
        move.w  OVS+8.l,d0
        lsl.w   #5,d0
        adda.w  d0,a2                   ; end of the table
.m:     cmp.l   a2,a1
        bhs.s   .md
        move.b  (a1)+,(a0)+
        bra.s   .m
.md:    moveq   #31,d0
.z:     clr.b   (a0)+
        dbra    d0,.z
        subq.w  #1,OVS+8.l
        bra.w   m_camps

c_newcamp:
        bsr.w   chk_init
        move.w  OVS+8.l,d0
        cmp.w   #8,d0
        bhs.w   a_done
        addq.w  #1,OVS+8.l
        move.w  d0,d2
        move.w  d0,vCamp(a5)
        bsr.w   camp_ptr
        move.l  a0,a1
        moveq   #31,d0
.z:     clr.b   (a1)+
        dbra    d0,.z
        lea     sNewCampN(pc),a1
        moveq   #11,d0
.n:     move.b  (a1)+,(a0)+
        dbra    d0,.n
        bra.w   cp_edit

; make sure the store has a valid header
chk_init:
        lea     OVS.l,a0
        cmpi.l  #'NCMP',(a0)
        beq.s   .ok
        move.w  #(OVSZ/4)-1,d0
.z:     clr.l   (a0)+
        dbra    d0,.z
        move.l  #'NCMP',OVS.l
        move.w  #1,OVS+4.l
.ok:    rts

; entry editor for campaign vCamp: "n O m t" / "n L name" (10,i), "<add entry>", "< back"
cp_edit:
        move.w  vCamp(a5),d0
        bsr.w   camp_ptr
        move.l  a0,a3
        clr.w   vScr(a5)
        move.w  #8,vMCol(a5)
        lea     MB.l,a2
        clr.b   (a2)+
        move.l  a2,vMBP(a5)
        moveq   #0,d3
        move.b  12(a3),d3
        moveq   #0,d2
        bra.s   .t
.l:     move.b  14(a3,d2.w),d0
        lea     vNum(a5),a2
        move.w  d2,d1
        addq.w  #1,d1
        move.w  d1,d0
        exg     d0,d1
        move.w  d1,-(a7)
        move.w  d2,d0
        addq.w  #1,d0
        bsr.w   dec2
        move.w  (a7)+,d1
        move.b  #' ',(a2)+
        move.b  14(a3,d2.w),d0
        bpl.s   .cust
        move.b  #'O',(a2)+
        move.b  #' ',(a2)+
        move.b  14(a3,d2.w),d0
        move.b  d0,d1
        lsr.b   #3,d1
        and.b   #1,d1
        add.b   #'1',d1
        move.b  d1,(a2)+
        move.b  #'-',(a2)+
        and.b   #7,d0
        add.b   #'1',d0
        move.b  d0,(a2)+
        clr.b   (a2)
        bra.s   .add
.cust:  move.b  #'L',(a2)+
        move.b  #' ',(a2)+
        and.w   #$7f,d0
        bsr.w   lvl_ptr
        move.l  a0,d0
        beq.s   .nm
        lea     8(a0),a0
        moveq   #7,d0
.cn:    move.b  (a0)+,d1
        beq.s   .cd
        move.b  d1,(a2)+
        dbra    d0,.cn
.cd:    clr.b   (a2)
        bra.s   .add
.nm:    move.b  #'?',(a2)+
        clr.b   (a2)
.add:   lea     vNum(a5),a0
        moveq   #10,d0
        move.w  d2,d1
        bsr.w   mb_add
        addq.w  #1,d2
.t:     cmp.w   d3,d2
        blt.s   .l
        lea     sAddEnt(pc),a0
        moveq   #4,d0
        moveq   #17,d1
        bsr.w   mb_add
        lea     sBackC(pc),a0
        moveq   #4,d0
        moveq   #2,d1
        bsr.w   mb_add
        lea     MB.l,a0
        bsr.w   menu_open
        move.w  #3,vRedraw(a5)
        rts

dec2:   ext.l   d0
        divu.w  #10,d0
        add.b   #'0',d0
        move.b  d0,(a2)+
        swap    d0
        add.b   #'0',d0
        move.b  d0,(a2)+
        rts

c_addent:
        move.w  vCamp(a5),d0
        bsr.w   camp_ptr
        move.l  a0,d0
        beq.w   a_done
        moveq   #0,d0
        move.b  12(a0),d0
        cmp.w   #16,d0
        bhs.w   cp_edit
        move.b  #$80,14(a0,d0.w)
        addq.b  #1,12(a0)
        bra.w   cp_edit


; entry selected -> submenu
a_ent:  move.w  d1,vCur(a5)
        lea     m_ent(pc),a0
        bra.w   menu_open

; entry operations: 0 change source, 1 insert after, 2 remove, 3 up, 4 down
a_eop:  move.w  vCamp(a5),d0
        bsr.w   camp_ptr
        move.l  a0,d0
        beq.w   a_done
        moveq   #0,d2
        move.w  vCur(a5),d2
        moveq   #0,d3
        move.b  12(a0),d3               ; count
        lea     14(a0),a1               ; entries
        tst.w   d1
        beq.s   .cyc
        cmp.w   #1,d1
        beq.s   .ins
        cmp.w   #2,d1
        beq.s   .rem
        cmp.w   #3,d1
        beq.s   .up
        ; down
        move.w  d2,d0
        addq.w  #1,d0
        cmp.w   d3,d0
        bhs.w   cp_edit
        move.b  0(a1,d2.w),d4
        move.b  0(a1,d0.w),0(a1,d2.w)
        move.b  d4,0(a1,d0.w)
        bra.w   cp_edit
.up:    tst.w   d2
        beq.w   cp_edit
        move.w  d2,d0
        subq.w  #1,d0
        move.b  0(a1,d2.w),d4
        move.b  0(a1,d0.w),0(a1,d2.w)
        move.b  d4,0(a1,d0.w)
        bra.w   cp_edit
.cyc:   move.b  0(a1,d2.w),d4
        and.w   #$ff,d4
        addq.w  #1,d4
        cmp.w   #$90,d4
        bhs.s   .w0
        cmp.w   #$80,d4
        bhs.s   .st
        move.l  a0,-(a7)
        lea     OVS.l,a0
        cmp.w   6(a0),d4
        move.l  (a7)+,a0
        blo.s   .st
        move.w  #$80,d4
        bra.s   .st
.w0:    moveq   #0,d4
        move.l  a0,-(a7)
        lea     OVS.l,a0
        tst.w   6(a0)
        move.l  (a7)+,a0
        bne.s   .st
        move.w  #$80,d4
.st:    move.b  d4,0(a1,d2.w)
        bra.w   cp_edit
.ins:   cmp.w   #16,d3
        bhs.w   cp_edit
        move.w  d3,d4
.is:    cmp.w   d2,d4
        ble.s   .id
        move.b  -1(a1,d4.w),0(a1,d4.w)
        subq.w  #1,d4
        bra.s   .is
.id:    addq.b  #1,12(a0)
        bra.w   cp_edit
.rem:   move.w  d2,d4
        addq.w  #1,d4
.rs:    cmp.w   d3,d4
        bge.s   .rd
        move.b  0(a1,d4.w),-1(a1,d4.w)
        addq.w  #1,d4
        bra.s   .rs
.rd:    subq.b  #1,12(a0)
        bra.w   cp_edit

; --- editor commands
c_blank:
        lea     GRID.l,a0
        move.w  #$3ff,d0
.c:     clr.l   (a0)+
        dbra    d0,.c
        move.w  #48,RS+rsRows.l
        moveq   #15,d0
        lea     GRID+1.l,a0
.r:     move.b  #$81,(a0)
        lea     $100(a0),a0
        dbra    d0,.r
        lea     GRID+$300.l,a0
        move.b  #$81,43(a0)
        move.b  #$81,$100+43(a0)
        move.b  #$81,$200+43(a0)
        lea     GRID+$400.l,a0
        move.b  #$c3,44(a0)
        move.b  #$c3,45(a0)
        move.b  #$c3,46(a0)
        move.w  #1,vDirty(a5)
        clr.w   RS+rsCx.l
        move.w  #1,RS+rsCy.l
        move.w  #21,RS+rsTop.l
        clr.w   vMode(a5)
        move.w  #3,vRedraw(a5)
        rts

        org     CODE2
c_look: move.w  RS+rsTow.l,d0
        addq.w  #1,d0
        and.w   #7,d0
        move.w  d0,RS+rsTow.l
        bra.s   c_ldone
c_mis:  eori.w  #3,RS+rsMis.l
c_ldone: move.w #1,vDirty(a5)
        clr.w   vMode(a5)
        move.w  #2,vRedraw(a5)
        rts

c_copyorig:
        clr.w   RS+rsLvl.l
        move.w  RS+rsTow.l,$3390c.l
        move.w  RS+rsMis.l,$33910.l
        jsr     $377a2.l
        move.w  $33912.l,RS+rsRows.l
        move.w  #1,vDirty(a5)
        clr.w   RS+rsCx.l
        move.w  #1,RS+rsCy.l
        move.w  #21,RS+rsTop.l
        clr.w   vMode(a5)
        move.w  #3,vRedraw(a5)
        rts

c_tup:  moveq   #5,d0
        bra.s   c_time
c_tdn:  moveq   #-5,d0
c_time: move.w  RS+rsTime.l,d1
        ; BCD step of 50 s: hundreds in bits 8-11, tens in bits 4-7
        move.w  d1,d2
        lsr.w   #4,d2
        and.w   #$ff,d2                 ; BCD hundreds+tens
        move.w  d2,d3
        and.w   #$f,d2                  ; tens
        lsr.w   #4,d3                   ; hundreds
        add.w   d0,d2
        bpl.s   .a
        add.w   #10,d2
        subq.w  #1,d3
.a:     cmp.w   #10,d2
        blt.s   .b
        sub.w   #10,d2
        addq.w  #1,d3
.b:     cmp.w   #1,d3
        blt.s   .done
        cmp.w   #9,d3
        bgt.s   .done
        lsl.w   #8,d3
        lsl.w   #4,d2
        or.w    d2,d3
        move.w  d3,RS+rsTime.l
.done:  move.w  #1,vDirty(a5)
        clr.w   vMode(a5)
        move.w  #2,vRedraw(a5)
        rts

c_rename:
        lea     RS+rsName.l,a0
        move.l  a0,vNDst(a5)
        bra.w   name_begin

; level name entry: up/down change the character, left/right move, fire = done
name_begin:
        clr.w   vNPos(a5)
        move.w  #3,vMode(a5)
        move.w  #2,vRedraw(a5)
        rts

move_name:
        move.w  vNPos(a5),d0
        add.w   d1,d0
        bpl.s   .a
        moveq   #0,d0
.a:     cmp.w   #10,d0
        ble.s   .b
        moveq   #10,d0
.b:     move.w  d0,vNPos(a5)
        tst.w   d2
        beq.s   .r
        move.l  vNDst(a5),a0
        adda.w  d0,a0
        move.b  (a0),d3
        lea     chars(pc),a1
        moveq   #0,d4
.f:     move.b  0(a1,d4.w),d0
        beq.s   .nf
        cmp.b   d0,d3
        beq.s   .fd
        addq.w  #1,d4
        bra.s   .f
.nf:    moveq   #0,d4
.fd:    add.w   d2,d4
        bpl.s   .p
        moveq   #37,d4
.p:     tst.b   0(a1,d4.w)
        bne.s   .w
        moveq   #0,d4
.w:     move.b  0(a1,d4.w),(a0)
.r:     move.w  #2,vRedraw(a5)
        rts

name_done:
        clr.w   vMode(a5)
        move.w  #1,vDirty(a5)
        tst.w   vScr(a5)
        bne.s   .ed
        move.w  vCur(a5),d0
        tst.l   vNDst(a5)
        bra.w   m_camps
.ed:    move.w  #2,vRedraw(a5)
        rts

; --- leaving / saving
; commit the working grid into its slot (store in RAM) and into TREC
c_leaveed:
        bsr.w   commit
        clr.w   RS+rsEd.l
        bra.w   m_levels

c_save: bsr.w   chk_init
        tst.w   vScr(a5)
        beq.s   .w
        bsr.w   commit
.w:     bsr.w   save_file
        move.w  #3,vRedraw(a5)
        rts

c_play: bsr.w   commit
        move.w  #1,RS+rsTest.l
        move.w  #$7fff,RS+rsLvl.l
        move.w  RS+rsTow.l,d1
        move.w  d1,$3390c.l
        move.w  d1,$33a44.l
        move.w  RS+rsMis.l,$33910.l
        clr.w   RS+rsCamp.l
        move.w  #1,vRes(a5)
        rts

; encode the working grid + meta into TREC, then into the slot (replacing or appending)
commit: tst.w   vDirty(a5)
        beq.s   .enc
.enc:   lea     TREC.l,a2
        move.w  RS+rsMis.l,d0
        move.b  d0,(a2)
        move.w  RS+rsTow.l,d0
        move.b  d0,1(a2)
        move.w  RS+rsRows.l,d0
        move.b  d0,2(a2)
        clr.b   3(a2)
        move.w  RS+rsTime.l,6(a2)
        lea     8(a2),a0
        lea     RS+rsName.l,a1
        moveq   #11,d0
.nm:    move.b  (a1)+,(a0)+
        dbra    d0,.nm
        clr.b   19(a2)
        lea     REC(a2),a0              ; mask
        move.l  a0,a1
        move.w  RS+rsRows.l,d0
        adda.w  d0,a1
        adda.w  d0,a1                   ; stream
        move.l  a1,d6
        move.w  d0,d5
        subq.w  #1,d5
        lea     GRID.l,a3
.er:    moveq   #1,d3
        move.l  a3,a4
.eh:    moveq   #0,d1
        moveq   #0,d2
.eb:    move.b  (a4),d0
        beq.s   .e0
        bset    d2,d1
        move.b  d0,(a1)+
.e0:    lea     $100(a4),a4
        addq.w  #1,d2
        cmp.w   #8,d2
        blt.s   .eb
        move.b  d1,(a0)+
        dbra    d3,.eh
        addq.l  #1,a3
        dbra    d5,.er
        move.l  a1,d0
        sub.l   a2,d0
        sub.w   #REC,d0
        move.w  d0,4(a2)                ; len
        ; into the store
        bsr.w   chk_init
        moveq   #0,d3
        move.w  4(a2),d3
        add.w   #REC,d3                 ; new size
        move.w  RS+rsSlot.l,d0
        beq.s   .app
        subq.w  #1,d0
        bsr.w   lvl_ptr
        move.l  a0,d0
        beq.s   .app
        ; replace in place: shift the tail by (new - old)
        move.l  a0,a3
        moveq   #0,d4
        move.w  4(a3),d4
        add.w   #REC,d4                 ; old size
        move.l  a3,-(a7)
        bsr.w   store_end
        move.l  a0,a4                   ; end
        move.l  (a7)+,a3
        move.l  d3,d0
        sub.l   d4,d0                   ; delta
        move.l  a4,d1
        add.l   d0,d1
        cmp.l   #OVS+OVSZ,d1
        bhi.w   no_room
        lea     0(a3,d4.l),a0           ; old tail start
        lea     0(a3,d3.l),a1           ; new tail start
        tst.l   d0
        beq.s   .cp
        bmi.s   .dn
        ; growing: move backwards
        move.l  a4,a2
        lea     0(a2,d0.l),a1
.gb:    cmp.l   a0,a2
        bls.s   .cp
        move.b  -(a2),-(a1)
        bra.s   .gb
.dn:    move.l  a0,a2
.sf:    cmp.l   a4,a2
        bhs.s   .cp
        move.b  (a2)+,(a1)+
        bra.s   .sf
.cp:    lea     TREC.l,a0
        move.l  a3,a1
        move.l  d3,d0
.cl:    move.b  (a0)+,(a1)+
        subq.l  #1,d0
        bne.s   .cl
        clr.l   vMsg(a5)
        rts
.app:   bsr.w   store_end
        lea     OVS+OVSZ.l,a1
        suba.l  a0,a1
        cmpa.l  d3,a1
        blt.w   no_room
        lea     TREC.l,a1
        move.l  d3,d0
.ac:    move.b  (a1)+,(a0)+
        subq.l  #1,d0
        bne.s   .ac
        move.w  OVS+6.l,d0
        addq.w  #1,OVS+6.l
        addq.w  #1,d0
        move.w  d0,RS+rsSlot.l
        clr.l   vMsg(a5)
        rts

; ------------------------------------------------------------------ save OVS to NEBLEVEL.OVL through a TOS excursion
save_file:
        movem.l d0-d7/a0-a6,-(a7)
        clr.l   vErr(a5)
        move.l  a5,-(a7)
        move.w  sr,d0
        move.w  d0,-(a7)
        ori.w   #$700,sr
        move.l  a7,vGsp(a5)
        lea     STK.l,a7
        move.l  a5,-(a7)
        bsr.w   mfp_save
        bsr.w   swap_tos
        lea     $fffaa.l,a2
        bsr.w   mfp_set
        move.w  #$2500,sr
        move.w  #1,-(a7)
        pea     fname(pc)
        move.w  #$3d,-(a7)
        trap    #1
        addq.l  #8,a7
        move.l  d0,d7
        tst.l   d0
        bmi.s   .res
        move.w  d0,d6
        pea     OVS.l
        pea     OVSZ.l
        move.w  d6,-(a7)
        move.w  #$40,-(a7)
        trap    #1
        lea     12(a7),a7
        move.l  d0,d7
        sub.l   #OVSZ,d7
        move.w  d6,-(a7)
        move.w  #$3e,-(a7)
        trap    #1
        addq.l  #4,a7
.res:   move.w  #$2700,sr
        move.l  d7,-(a7)
        bsr.w   swap_tos
        move.l  (a7)+,d7
        move.l  (a7)+,a5
        lea     V+vMfp.l,a2
        bsr.w   mfp_set
.dr:    btst    #0,$fffffc00.w
        beq.s   .dd
        move.b  $fffffc02.w,d0
        bra.s   .dr
.dd:
        move.l  d7,vErr(a5)
        move.l  vGsp(a5),a7
        move.w  (a7)+,d0
        move.l  (a7)+,a5
        move.w  d0,sr
        lea     sSaved(pc),a0
        tst.l   vErr(a5)
        beq.s   .ok
        lea     sFail(pc),a0
.ok:    move.l  a0,vMsg(a5)
        movem.l (a7)+,d0-d7/a0-a6
        rts

swap_tos:
        lea     8.w,a0
        move.l  $ffd80.l,a1
        move.w  $ffd86.l,d0
        addq.w  #1,d0
        mulu.w  #48,d0
        lea     8(a0,d0.l),a6
.l:     movem.l (a0),d0-d5
        movem.l (a1),d6/d7/a2-a5
        movem.l d6/d7/a2-a5,(a0)
        movem.l d0-d5,(a1)
        lea     24(a0),a0
        lea     24(a1),a1
        cmpa.l  a6,a0
        blo.s   .l
        rts

mfp_save:
        lea     $fffffa01.w,a0
        lea     V+vMfp.l,a1
        moveq   #23,d0
.r:     move.b  (a0),(a1)+
        addq.l  #2,a0
        dbra    d0,.r
        moveq   #0,d2
        moveq   #0,d4
        moveq   #0,d6
        move.w  #4777,d7
.s:     move.b  $fffffa1f.w,d1
        cmp.b   d1,d2
        bcc.s   .a
        move.b  d1,d2
.a:     move.b  $fffffa23.w,d3
        cmp.b   d3,d4
        bcc.s   .b
        move.b  d3,d4
.b:     move.b  $fffffa25.w,d5
        cmp.b   d5,d6
        bcc.s   .c
        move.b  d5,d6
.c:     dbra    d7,.s
        move.b  d2,V+vMfp+15.l
        move.b  d4,V+vMfp+17.l
        move.b  d6,V+vMfp+18.l
        rts

mfp_set:
        clr.b   $fffffa07.w
        clr.b   $fffffa09.w
        clr.b   $fffffa0b.w
        clr.b   $fffffa0d.w
        clr.b   $fffffa0f.w
        clr.b   $fffffa11.w
        lea     $fffffa01.w,a1
        moveq   #23,d2
.l:     move.b  (a2)+,(a1)
        addq.l  #2,a1
        dbra    d2,.l
        rts

fname:  dc.b    'NEBLEVEL.OVL',0
        even

; expand the 8-pixel tile patterns to 16-pixel words (ETILE, 17 tiles x 8 words)
tiles_init:
        lea     tiles(pc),a0
        lea     ETILE.l,a1
        moveq   #16,d6
.t:     moveq   #7,d5
.r:     move.b  (a0)+,d4
        moveq   #0,d0
        moveq   #7,d2
.b:     moveq   #0,d3
        add.b   d4,d4
        bcc.s   .z
        moveq   #3,d3
.z:     lsl.w   #2,d0
        or.w    d3,d0
        dbra    d2,.b
        move.w  d0,(a1)+
        dbra    d5,.r
        addq.l  #2,a0
        dbra    d6,.t
        rts

; the campaign store is validated once (RS+rsOk): bad version, counts, ranges, lengths or mask/stream mismatch => magic cleared (= absent)
ov_ok:  tst.w   RS+rsOk.l
        bne.s   .r
        movem.l d0-d7/a0-a4,-(a7)
        bsr.w   ov_check
        move.w  #1,RS+rsOk.l
        movem.l (a7)+,d0-d7/a0-a4
.r:     rts

ov_check:
        lea     OVS.l,a0
        cmpi.l  #'NCMP',(a0)
        bne.w   .out
        cmpi.w  #1,4(a0)
        bne.w   .bad
        move.w  6(a0),d3
        cmp.w   #127,d3
        bhi.w   .bad
        move.w  8(a0),d2
        cmp.w   #8,d2
        bhi.w   .bad
        lea     16(a0),a1
        bra.s   .ct
.cl:    cmpi.b  #16,12(a1)
        bhi.w   .bad
        lea     32(a1),a1
.ct:    dbra    d2,.cl
        lea     LV0(a0),a1
        lea     OVS+OVSZ.l,a3
        bra.w   .lt
.ll:    lea     REC(a1),a2
        cmpa.l  a3,a2
        bhi.w   .bad
        move.b  (a1),d0
        cmp.b   #1,d0
        blo.w   .bad
        cmp.b   #2,d0
        bhi.w   .bad
        cmpi.b  #7,1(a1)
        bhi.w   .bad
        moveq   #0,d4
        move.b  2(a1),d4
        cmp.w   #16,d4
        blo.w   .bad
        cmp.w   #120,d4
        bhi.w   .bad
        moveq   #0,d5
        move.w  4(a1),d5
        move.w  d4,d0
        add.w   d0,d0
        cmp.w   d0,d5
        blo.w   .bad
        lea     0(a2,d5.l),a4
        cmpa.l  a3,a4
        bhi.w   .bad
        move.w  d0,d1
        subq.w  #1,d1
        moveq   #0,d6
        move.l  a2,a0
.pc:    move.b  (a0)+,d0
        moveq   #7,d2
.pb:    lsr.b   #1,d0
        bcc.s   .pn
        addq.w  #1,d6
.pn:    dbra    d2,.pb
        dbra    d1,.pc
        move.w  d5,d0
        sub.w   d4,d0
        sub.w   d4,d0
        cmp.w   d0,d6
        bne.w   .bad
        move.l  a4,a1
.lt:    dbra    d3,.ll
.out:   rts
.bad:   clr.l   OVS.l
        rts

; ------------------------------------------------------------------ data (second block)
        org     DATA
; tiles: 8 pattern bytes, colour (plane mask), pad.  ids: 0 empty, 1 inert marker, 2 ledge, 3 wide ledge, 4 pillar, 5 blue block, 6 pale block,
; 7 door, 8 exit, 9 stone ball, 10 red ball, 11 red ball (waits), 12/13 eye vertical slow/fast, 14/15 eye horizontal slow/fast
tiles:
        dc.b    $00,$00,$00,$10,$00,$00,$00,$00,1,0
        dc.b    $00,$00,$00,$00,$18,$00,$00,$00,1,0
        dc.b    $00,$00,$00,$00,$00,$ff,$ff,$00,2,0
        dc.b    $00,$00,$00,$00,$ff,$ff,$ff,$00,3,0
        dc.b    $18,$3c,$7e,$7e,$7e,$7e,$3c,$18,4,0
        dc.b    $ff,$81,$bd,$bd,$bd,$bd,$81,$ff,5,0
        dc.b    $7e,$ff,$ff,$ff,$ff,$ff,$ff,$7e,6,0
        dc.b    $ff,$81,$81,$81,$81,$81,$81,$ff,7,0
        dc.b    $ff,$c3,$a5,$99,$99,$a5,$c3,$ff,7,0
        dc.b    $3c,$42,$81,$81,$81,$81,$42,$3c,4,0
        dc.b    $3c,$7e,$ff,$ff,$ff,$ff,$7e,$3c,7,0
        dc.b    $3c,$7e,$e7,$c3,$c3,$e7,$7e,$3c,7,0
        dc.b    $18,$3c,$7e,$db,$db,$7e,$3c,$18,5,0
        dc.b    $3c,$18,$7e,$db,$db,$7e,$18,$3c,5,0
        dc.b    $00,$3c,$7e,$db,$db,$7e,$3c,$00,5,0
        dc.b    $00,$7e,$ff,$db,$db,$ff,$7e,$00,5,0
        dc.b    $00,$24,$3c,$7e,$5a,$7e,$24,$00,6,0
sHelp:  dc.b    'Fire=menu F10=back',0
        even

names:  dc.w    n0-names,n1-names,n2-names,n3-names,n4-names,n5-names,n6-names,n7-names,n8-names
        dc.w    n9-names,n10-names,n11-names,n12-names,n13-names,n14-names,n15-names
n0:     dc.b    'Empty',0
n1:     dc.b    'Marker (inert)',0
n2:     dc.b    'Ledge',0
n3:     dc.b    'Ledge (wide)',0
n4:     dc.b    'Pillar',0
n5:     dc.b    'Blue block',0
n6:     dc.b    'Pale block',0
n7:     dc.b    'Door opening',0
n8:     dc.b    'Exit door',0
n9:     dc.b    'Stone ball',0
n10:    dc.b    'Red ball',0
n11:    dc.b    'Red ball (waits)',0
n12:    dc.b    'Eye up/down slow',0
n13:    dc.b    'Eye up/down fast',0
n14:    dc.b    'Eye left/right',0
n15:    dc.b    'Eye l/r fast',0

sTower: dc.b    'Tower ',0
sMission: dc.b  '  Mission ',0
sRows:  dc.b    'Rows ',0
sCol:   dc.b    'Col ',0
sRow:   dc.b    ' Row ',0
sCell:  dc.b    'Cell ',0
sHelp1: dc.b    'Fire = menu',0
sHelp2: dc.b    'F10 = back',0
sFull:  dc.b    'Overlay full!',0
sSaved: dc.b    'Saved to disk',0
sFail:  dc.b    'SAVE FAILED',0
sWarnEye: dc.b  'Eye needs terrain',0
sWarnLedge: dc.b 'No ledge below!',0
sName:  dc.b    'Name ',0
sNameH: dc.b    'U/D letter L/R move',0
sNameH2: dc.b   'Fire = done',0
sNewLvl: dc.b   '<new level>',0
sNewCamp: dc.b  '<new campaign>',0
sBack:  dc.b    '< back',0
sBackC: dc.b    '< back',0
sAddEnt: dc.b   '<add entry>',0
sNewName: dc.b  'NEW LEVEL  ',0
sNewCampN: dc.b 'NEW CAMP',0,0,0,0
chars:  dc.b    ' ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-',0
        even

; menus: count, then per item: action.b param.b text,0
menus:  dc.w    m_root-menus,m_enemy-menus,m_tower-menus
m_mainm: dc.b   4
        dc.b    4,5,'Original game',0
        dc.b    4,2,'Campaigns >',0
        dc.b    4,1,'Levels >',0
        dc.b    4,6,'Save to disk',0
m_lvl:  dc.b    5
        dc.b    8,0,'Play',0
        dc.b    8,1,'Edit',0
        dc.b    8,2,'Copy',0
        dc.b    8,3,'Delete',0
        dc.b    4,1,'< back',0
m_camp: dc.b    5
        dc.b    9,0,'Play',0
        dc.b    9,1,'Edit entries',0
        dc.b    9,2,'Rename',0
        dc.b    9,3,'Delete',0
        dc.b    4,2,'< back',0
m_ent:  dc.b    6
        dc.b    11,0,'Change source',0
        dc.b    11,1,'Insert after',0
        dc.b    11,2,'Remove',0
        dc.b    11,3,'Move up',0
        dc.b    11,4,'Move down',0
        dc.b    4,18,'< back',0
m_root: dc.b    12
        dc.b    0,$00,'Empty',0
        dc.b    0,$81,'Ledge',0
        dc.b    0,$80,'Pillar',0
        dc.b    0,$82,'Blue block (shoot)',0
        dc.b    0,$85,'Pale block',0
        dc.b    1,$83,'Door opening',0
        dc.b    1,$c3,'Exit door',0
        dc.b    2,1,'Enemy >',0
        dc.b    2,2,'Tower >',0
        dc.b    4,16,'Playtest',0
        dc.b    4,6,'Save to disk',0
        dc.b    4,8,'Leave editor',0
m_enemy: dc.b   8
        dc.b    3,$10,'Stone ball',0
        dc.b    3,$20,'Red ball',0
        dc.b    3,$30,'Red ball (waits)',0
        dc.b    3,$40,'Eye up/down slow',0
        dc.b    3,$50,'Eye up/down fast',0
        dc.b    3,$60,'Eye left/right',0
        dc.b    3,$70,'Eye l/r fast',0
        dc.b    4,7,'< back',0
m_dirh: dc.b    3
        dc.b    5,0,'Start right',0
        dc.b    5,1,'Start left',0
        dc.b    4,7,'< back',0
m_dirv: dc.b    3
        dc.b    5,0,'Start up',0
        dc.b    5,1,'Start down',0
        dc.b    4,7,'< back',0
m_tower: dc.b   8
        dc.b    4,9,'Look: next tower',0
        dc.b    4,10,'Look: other mission',0
        dc.b    4,11,'Copy original grid',0
        dc.b    4,12,'Blank grid',0
        dc.b    4,13,'Time +50',0
        dc.b    4,14,'Time -50',0
        dc.b    4,15,'Name...',0
        dc.b    4,7,'< back',0
        even
