; name: test_walk
; default: no
; site: $22fa2
; orig: 23c00003979a
; data: PB+$6f00 12
; note: TEST ONLY (gate driver for tools/p2abtest.py; never in a build).  Together with test_walk2 / test_walk3 it makes the game's input a pure
; note: function of the world turn, so a patched run and an unpatched run see the same pointer position and the same held scroll key in every pass,
; note: whatever their speed.  Site: the turn increment of the pass top ($22fa2 `move.l d0,$3979a.l`, work/notes/display.md).  After storing the turn it
; note: (MODE bit 0) sets PX/PY and the game's pointer words $393fa/$393fc from a 16-entry table (each entry held for 2 turns: edges, the x > 304 one-column
; note: case, the y > 184 clip, corners, panel areas, map) and (MODE bit 1) sets the view $3e79e/$3e7a0 to (BX,BY) + a point on a 16-cell square walked at one cell per turn (+x, +y, -x, -y, period 64 turns:
; note: an absolute function of the turn, so runs that start at the same turn agree at any CPU speed; the game's own clamp $22fc8 still runs).  test_walk2/3 replace the two IKBD position copies ($1cd0, $1cda) by PX/PY.
; note: Data (zero in the live image): PX.w PY.w MODE.w BX.w BY.w at PB+$6f00 (the host pokes BX/BY = the snapshot's view - 8, so the square surrounds the scene).
PX      equ     PB+$6f00
PY      equ     PB+$6f02
MODE    equ     PB+$6f04
BX      equ     PB+$6f06
BY      equ     PB+$6f08
WALKA   equ     PB+$6800

        org     $22fa2
        jmp     WALKA.l

        org     PB+$6800
WALK:   move.l  d0,$3979a.l
        movem.l d0-d2/a0,-(a7)
        move.w  MODE.l,d2
        btst    #0,d2
        beq.s   .keys
        move.w  d0,d1
        lsr.w   #1,d1
        andi.w  #15,d1
        lsl.w   #2,d1
        lea     postab(pc),a0
        move.w  0(a0,d1.w),d2
        move.w  d2,PX.l
        move.w  d2,$393fa.l
        move.w  2(a0,d1.w),d2
        move.w  d2,PY.l
        move.w  d2,$393fc.l
.keys:  btst    #1,MODE+1.l
        beq.s   .out
        move.w  d0,d2                   ; view = 20 + a point on a 16-cell square, a pure function of the turn: u = turn & 63,
        andi.w  #63,d2                  ; segment u >> 4 (+x, +y, -x, -y), r = u & 15
        move.w  d2,d1
        lsr.w   #4,d2
        andi.w  #15,d1
        tst.w   d2
        bne.s   .s1
        move.w  d1,d0                   ; x = r, y = 0
        moveq   #0,d2
        bra.s   .set
.s1:    cmpi.w  #1,d2
        bne.s   .s2
        moveq   #16,d0                  ; x = 16, y = r
        move.w  d1,d2
        bra.s   .set
.s2:    cmpi.w  #2,d2
        bne.s   .s3
        moveq   #16,d0                  ; x = 16 - r, y = 16
        sub.w   d1,d0
        moveq   #16,d2
        bra.s   .set
.s3:    moveq   #0,d0                   ; x = 0, y = 16 - r
        moveq   #16,d2
        sub.w   d1,d2
.set:   add.w   BX.l,d0
        add.w   BY.l,d2
        move.w  d0,$3e79e.l
        move.w  d2,$3e7a0.l
.out:   movem.l (a7)+,d0-d2/a0
        jmp     $22fa8.l
postab: dc.w    160,100
        dc.w    20,20
        dc.w    300,30
        dc.w    319,199
        dc.w    8,190
        dc.w    150,189
        dc.w    96,170
        dc.w    310,100
        dc.w    1,100
        dc.w    200,60
        dc.w    305,185
        dc.w    304,184
        dc.w    15,195
        dc.w    250,199
        dc.w    64,128
        dc.w    270,150
