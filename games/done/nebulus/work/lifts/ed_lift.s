; Proposed in-game "Lift" command for the level editor (patches/ed_editor.s).  NOT part of the build: the lead merges it (work/notes/lifts.md sections 6, 7).
; work/lifts/build_lift_editor.py applies the edits listed below to a COPY of the editor source (under /tmp), assembles this code as a fourth block at $77a40
; and builds a private game dir; that build was exercised in Hatari (notes 6b).  Standalone assembly (stubs at the end) only measures sizes:
;   vasmm68k_mot -Fbin -m68000 -o /tmp/ed_lift.bin work/lifts/ed_lift.s   (the real build lets vasm size the branches; the tiles/names are applied by the script)
;
; The lift is NOT a new data structure: it is three cell values in ONE grid column (the game's own encoding, nothing in the NCMP file changes):
;     $85  start slab (lower row)      $08  end marker (higher row, non-terrain)      $0c  optional stop (the ride only goes on while Up is held)
; plus a ledge $81 under the slab (all 145 shipped lifts have it).  Flow: Fire -> Lift > -> "Lift: from here" (writes $85, arms vLift),
; the joystick then moves the cursor UP/DOWN in this column only, Fire = other end (lower of the two rows becomes the slab, the upper one the end; the ledge
; under the slab is added then).  F10 cancels.  "Lift: stop here" writes $0c, "Lift: delete" removes the lift the cursor is in.
;
; ---- edits to the existing source (everything else unchanged) ----------------------------------------------------------------------------
;  equ:      vLift equ 172 (word in V; V is cleared at editor entry; 172..191 are free)
;  menus:    menus: dc.w m_root-menus,m_enemy-menus,m_tower-menus,m_lift-menus            (a_sub param 3)
;  m_root:   replace  dc.b 0,$85,'Pale block',0   by   dc.b 2,3,'Lift >',0               (a lone $85 is a lift start, never a "solid block")
;  acts:     append a_lift-acts (action 12)
;  move_map: first lines     bsr.w draw_cursor / move.w RS+rsCx.l,d0     ->  insert  tst.w vLift(a5) / beq.s .h / moveq #0,d1 / .h:  before the add
;            and at .nr: replace  clr.l vMsg(a5)  by  bsr.w lift_msg
;  fire_edge map case ("; map: open the cell menu"): insert first   tst.w vLift(a5) / bne.w lift_set
;  f10:      before  bra.w c_leaveed  insert   tst.w vLift(a5) / bne.w lift_cancel
;  classify: in the bit7-clear branch, where  tst.b d1 / beq.s .r  returns tile 1 for k == 0, insert the lift_tile test (below) before that beq
;  tiles:    two more 10-byte tiles (17 lift end, 18 lift stop), tiles_init count 16 -> 18, names: n6 'Lift start' (was 'Pale block'), n16 '' , n17 'Lift end', n18 'Lift stop'
; --------------------------------------------------------------------------------------------------------------------------------------------

vLift   equ     172
RS      equ     $77c80
V       equ     $77cc0
GRID    equ     $327f0
rsCx    equ     20
rsCy    equ     22
rsRows  equ     16
vMsg    equ     20
vDirty  equ     162
vRedraw equ     18
vMode   equ     2
vScr    equ     30

        org     $77940
prop_begin:

; a0 = column base in the grid, d2 = cursor row
colbase:
        move.w  RS+rsCx.l,d0
        lsl.w   #8,d0
        lea     GRID.l,a0
        adda.w  d0,a0
        move.w  RS+rsCy.l,d2
        rts

; status line while the second end is being picked (called from move_map's .nr and after the command)
lift_msg:
        moveq   #0,d0
        tst.w   vLift(a5)
        beq.s   .z
        lea     sLiftEnd(pc),a0
        move.l  a0,d0
.z:     move.l  d0,vMsg(a5)
        rts

; menu action 12, d1 = 0 lift from here / 1 stop here / 2 delete lift
a_lift: bsr.s   colbase
        tst.w   d1
        beq.s   .new
        subq.w  #1,d1
        beq.s   .stop
        bsr.s   lift_slab                ; delete: d3 = slab row (or -1)
        bmi.s   .out
        clr.b   0(a0,d3.w)
        bsr.s   lift_clr
.out:   bra.s   .done
.stop:  moveq   #$0c,d0
        bsr.w   place
        bra.s   .done
.new:   cmp.b   #$85,0(a0,d2.w)         ; cursor on an existing slab: forget its old end first
        bne.s   .slab
        move.w  d2,d3
        bsr.s   lift_clr
.slab:  move.b  #$85,0(a0,d2.w)
.arm:   addq.w  #1,d2
        move.w  d2,vLift(a5)
        move.w  #1,vDirty(a5)
        bsr.s   lift_msg
.done:  bra.w   a_done

; d2 = row, a0 = column: d3 = row of the $85 of the lift the cursor belongs to (the cursor on its end $08, or in its shaft above the slab), N set when none
lift_slab:
        move.w  d2,d3
        cmp.b   #$08,0(a0,d3.w)
        bne.s   .l
        subq.w  #1,d3
        bmi.s   .y
.l:     move.b  0(a0,d3.w),d0
        cmp.b   #$85,d0
        beq.s   .y
        cmp.b   #$08,d0
        beq.s   .n
        subq.w  #1,d3
        bpl.s   .l
.n:     moveq   #-1,d3
.y:     tst.w   d3
        rts

; d3 = slab row: clear the $0c stops and the $08 end above it
lift_clr:
        move.w  d3,d4
.l:     addq.w  #1,d4
        cmp.w   RS+rsRows.l,d4
        bge.s   .r
        move.b  0(a0,d4.w),d0
        cmp.b   #$0c,d0
        beq.s   .c
        cmp.b   #$08,d0
        bne.s   .l
        clr.b   0(a0,d4.w)
.r:     rts
.c:     clr.b   0(a0,d4.w)
        bra.s   .l

; Fire while vLift is set: the cursor row is the other end
lift_set:
        bsr.w   colbase
        move.w  vLift(a5),d3
        subq.w  #1,d3                    ; d3 = first row (the slab so far)
        cmp.w   d3,d2
        beq.s   .bad
        blt.s   .below
        move.b  #$08,0(a0,d2.w)          ; second row above: end marker there, the slab is the first row
        move.w  d3,d2
        bra.s   .floor
.below: move.b  #$08,0(a0,d3.w)          ; second row below: the first cell becomes the end, the slab moves down
        move.b  #$85,0(a0,d2.w)
.floor: tst.w   d2                       ; ledge under the slab when that cell is empty (all shipped lifts have one)
        beq.s   .ok
        tst.b   -1(a0,d2.w)
        bne.s   .ok
        move.b  #$81,-1(a0,d2.w)
.ok:    clr.w   vLift(a5)
        bsr.w   lift_msg
        bsr.s   lift_warn
        move.w  #1,vDirty(a5)
        move.w  #3,vRedraw(a5)
        rts
.bad:   lea     sLiftBad(pc),a0
        move.l  a0,vMsg(a5)
        move.w  #2,vRedraw(a5)
        rts

; warning after a lift is complete: a $80 pillar between slab and end blocks the ride (blue blocks are a puzzle, the frog can shoot them)
lift_warn:
        bsr.w   colbase
        bsr.w   lift_slab
        bmi.s   .r
.l:     addq.w  #1,d3
        move.b  0(a0,d3.w),d0
        cmp.b   #$08,d0
        beq.s   .r
        cmp.b   #$80,d0
        bne.s   .nx
        lea     sLiftBlk(pc),a0
        move.l  a0,vMsg(a5)
        rts
.nx:    cmp.w   RS+rsRows.l,d3
        blt.s   .l
.r:     rts

; F10 while vLift is set: forget the pending lift (the slab stays, it is an ordinary start without an end: "Lift: delete" removes it)
lift_cancel:
        clr.w   vLift(a5)
        bsr.w   lift_msg
        move.w  #2,vRedraw(a5)
        rts

; classify, bit7 clear and k == 0 (inert marker): d0.b = value -> d3 = 17 ($08 end) / 18 ($0c stop), else leave d3 = 1
lift_tile:
        move.b  d0,d1
        and.b   #$0c,d1
        cmp.b   #$08,d1
        bne.s   .a
        moveq   #17,d3
        rts
.a:     cmp.b   #$0c,d1
        bne.s   .r
        moveq   #18,d3
.r:     rts

sLiftEnd: dc.b  'Lift: U/D = other end',0
sLiftBad: dc.b  'Pick another row',0
sLiftBlk: dc.b  'Pillar blocks lift',0
        even

; menu (tables block): count, then action.b param.b text,0
m_lift: dc.b    4
        dc.b    12,0,'Lift: from here',0
        dc.b    12,1,'Lift: stop here',0
        dc.b    12,2,'Lift: delete',0
        dc.b    4,7,'< back',0
        even

; two tiles (8 pattern bytes, plane mask, pad): 17 lift end (arrow), 18 lift stop (arrow + bar)
        dc.b    $18,$3c,$7e,$18,$18,$18,$18,$00,7,0
        dc.b    $18,$3c,$7e,$00,$7e,$00,$7e,$00,7,0
nLE:    dc.b    'Lift end',0
nLS:    dc.b    'Lift stop',0
        even
prop_end:

; ---- stand-ins for the editor's existing symbols (not counted) ----
place:  rts
a_done: rts
