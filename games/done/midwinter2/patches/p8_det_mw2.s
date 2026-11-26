; name: p8_det_mw2
; default: yes
; site: $315c0
; orig: 4eb90003166c
; phase: boot
; note: MW2 Detail-mode toggle ('D' key, scancode $20) + on-screen banner (HIGH / MEDIUM / LOW).
; note: Hooks `jsr $3166c.l` at $315c0 (just before `jsr $4f36.w` screen flip).
; note: State block at $B9100 (initialized in payload):
; note:   $B9100 LEVEL.w     0 = HIGH (exact), 1 = MEDIUM, 2 = LOW
; note:   $B9102 PREV_D.w    edge-detect state for 'D' ($76a6.w)
; note:   $B9104 TIMER.w     banner countdown frames (0 = off)
; note:   $B9106 DIST_CUT.w  terrain draw distance ($0a90 HIGH, $0900 MED, $0790 LOW)
; note:   $B9108 LAST_PAR.w  p4_grid cached parity (-1 = force full init)
; note:   $B910A OBJ_LIM.l   static scenery object cull distance ($7fffffff HIGH, $1000 MED, $0a00 LOW)
; note: Zero-overhead flat shading: in HIGH/MED, $38ce6 holds original bytes; in LOW, patches $38ce6
; note: to `jsr $b9800.l; nop` which maps all 256 colour/fog classes to nearest solid colour (0..15).
DET     equ     $b9100
oLVL    equ     0
oPREVD  equ     2
oTIMER  equ     4
oDIST   equ     6
oPAR    equ     8
oOBJLIM equ     10

SKIPVAL equ     $b6000          ; p7_skip_render VAL[0..1] (4 bytes)
PFXKB   equ     $b4680          ; p4_hud_pfx_fill KB[0..1] (4 bytes)

        org     $315c0
        jsr     $b9300.l

        org     $b9100
        dc.w    0               ; +0 LEVEL (0 = HIGH)
        dc.w    0               ; +2 PREV_D
        dc.w    0               ; +4 TIMER
        dc.w    $0a90           ; +6 DIST_CUT (full original draw distance)
        dc.w    $ffff           ; +8 LAST_PAR (-1 = force first p4_grid init)
        dc.l    $7fffffff       ; +10 OBJ_LIM (no object culling in HIGH)

        org     $b9300
        jsr     $3166c.l                ; displaced pre-flip call
        movem.l d0-d2/a0-a1/a6,-(a7)
        lea     DET.l,a0
        cmpi.w  #2,$700a.w              ; only toggle in 3D game context
        bne.w   .chk_tmr
        tst.b   $7686+$20.w             ; scancode $20 = 'D'
        bne.s   .down
        clr.w   oPREVD(a0)
        bra.w   .chk_tmr
.down:  tst.w   oPREVD(a0)
        bne.w   .chk_tmr
        move.w  #1,oPREVD(a0)
        move.w  oLVL(a0),d0
        addq.w  #1,d0
        cmpi.w  #3,d0
        bcs.s   .oklvl
        moveq   #0,d0
.oklvl: move.w  d0,oLVL(a0)
        ; Set DIST_CUT
        move.w  d0,d1
        add.w   d1,d1
        lea     .dists(pc),a1
        move.w  (a1,d1.w),oDIST(a0)
        ; Set OBJ_LIM
        add.w   d1,d1
        lea     .olims(pc),a1
        move.l  (a1,d1.w),oOBJLIM(a0)
        ; Runtime patch $38ce6 (8 bytes) for LOW flat shading vs HIGH/MED original
        cmpi.w  #2,d0
        bne.s   .orig_fill
        move.w  #$4eb9,$38ce6.l         ; jsr $b9800.l
        move.l  #$000b9800,$38ce8.l
        move.w  #$4e71,$38cec.l         ; nop
        bra.s   .arm
.orig_fill:
        move.l  #$14322000,$38ce6.l     ; move.b (a2,d2.w),d2
        move.l  #$d440d442,$38cea.l     ; add.w d0,d2 / add.w d2,d2
.arm:   move.w  #25,oTIMER(a0)
        clr.l   SKIPVAL.l
        clr.l   PFXKB.l
.chk_tmr:
        move.w  oTIMER(a0),d0
        beq.w   .done
        subq.w  #1,d0
        move.w  d0,oTIMER(a0)
        clr.l   SKIPVAL.l
        clr.l   PFXKB.l
        tst.w   d0
        beq.w   .done
        ; Draw banner using MW2's own font 1 ($4ed0.w), saving/restoring scratch fields like mw2_credit
        movem.l d3-d7/a2-a5,-(a7)
        lea     $770e.w,a6
        lea     -70(a7),a7
        lea     $e(a6),a0
        movea.l a7,a1
        moveq   #29,d0
.sv1:   move.w  (a0)+,(a1)+
        dbra    d0,.sv1
        lea     $11e(a6),a0
        moveq   #4,d0
.sv2:   move.w  (a0)+,(a1)+
        dbra    d0,.sv2
        jsr     $4eee.w                 ; init text renderer draw-buffer/clip state (as sub_03264a)
        move.w  #1,$11e(a6)
        clr.w   $120(a6)
        clr.w   $122(a6)
        clr.w   $124(a6)
        move.w  #160,$e(a6)             ; centre x = 160
        move.w  #64,$10(a6)             ; y = 64 (top of 3D window)
        move.w  DET+oLVL.l,d2
        add.w   d2,d2
        lea     .strs(pc),a1
        adda.w  (a1,d2.w),a1
        jsr     $4ed0.w
        movea.l a7,a0
        lea     $e(a6),a1
        moveq   #29,d0
.rs1:   move.w  (a0)+,(a1)+
        dbra    d0,.rs1
        lea     $11e(a6),a1
        moveq   #4,d0
.rs2:   move.w  (a0)+,(a1)+
        dbra    d0,.rs2
        lea     70(a7),a7
        movem.l (a7)+,d3-d7/a2-a5
.done:  movem.l (a7)+,d0-d2/a0-a1/a6
        rts

.dists: dc.w    $0a90,$0900,$0790
.olims: dc.l    $7fffffff,$00001000,$00000a00
.strs:  dc.w    .s_hi-.strs,.s_med-.strs,.s_lo-.strs
.s_hi:  dc.b    1,0,5,"DETAIL HIGH",0
.s_med: dc.b    1,0,5,"DETAIL MEDIUM",0
.s_lo:  dc.b    1,0,5,"DETAIL LOW",0
        even

        org     $b9800
flat_cls:
        move.b  (a2,d2.w),d2            ; original class lookup
        add.w   d0,d2                   ; + fog band offset (0..255)
        and.w   #$ff,d2
        lea     solid_map(pc),a2
        move.b  (a2,d2.w),d2            ; map to nearest solid colour (0..15)
        add.w   d2,d2                   ; word index into $3b85a
        rts
solid_map:
        dc.b    0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15
        dc.b    0,1,1,1,3,3,3,7,7,0,2,2,2,6,6,6
        dc.b    14,14,0,4,4,4,12,12,0,5,5,5,13,13,0,8
        dc.b    8,8,9,9,1,3,2,2,3,3,3,7,4,4,5,5
        dc.b    0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15
        dc.b    1,1,1,3,3,3,7,7,7,2,2,2,6,6,6,14
        dc.b    14,14,4,4,4,12,12,12,5,5,5,13,13,13,8,8
        dc.b    8,9,9,9,1,3,2,2,3,3,3,7,4,4,5,5
        dc.b    15,15,15,15,15,15,15,15,15,15,15,15,15,15,15,15
        dc.b    15,15,15,15,15,15,15,15,15,15,15,15,15,15,15,15
        dc.b    15,15,15,15,15,15,15,15,15,15,15,15,15,15,15,15
        dc.b    15,15,15,15,1,3,2,2,3,3,3,7,4,4,5,5
        dc.b    15,15,15,15,15,15,15,15,15,15,15,15,15,15,15,15
        dc.b    15,15,15,15,15,15,15,15,15,15,15,15,15,15,15,15
        dc.b    15,15,15,15,15,15,15,15,15,15,15,15,15,15,15,15
        dc.b    15,15,15,15,1,3,2,2,3,3,3,7,4,4,5,5
