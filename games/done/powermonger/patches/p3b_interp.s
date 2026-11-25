; name: p3b_interp
; default: yes
; site: $130aa
; orig: 4eb90000f898
; data: $b8a80 32
; data: $b8d00 2048
; data: $b9500 5120
; data: $bac40 960
; note: P5 predict-ahead (extrapolation) interpolation of the moving people-table records (work/notes/interp.md). Needs tick_* and
;       p3b_delta (the second half: it fills the velocity list after every world tick). Site: `jsr $f898` (landscape + objects,
;       the only call), replaced by `jsr ap`. The renderer takes a record's screen position from the LOW BYTES of its x/z words
;       ($8/$a(a3), `andi.w #$ff` in sub_011f1a: position inside the cell the record is chained into; the high bytes only select the cell
;       at the tick), so a render-only pass can draw a man part-way into his next step by shifting those low bytes.
;       ap: for every entry of the mover list (record offset, dx, dz, saved x, saved z: built by p3b_delta from the last tick's
;       position change, 0 when the change was more than STEP in an axis = teleport, spawn, landing...) writes
;       x/z low byte + (delta*FQ)>>8, clamped to 0..255 (the cell edge; the high byte, i.e. the chain cell, is untouched),
;       calls $f898, then writes the saved words back: the people table is bit-identical outside of the render.
;       FQ (256 = one tick = 75 units of 1/300 s = 0.25 s; at most 384): the time since the tick the records describe, i.e. ACC (tick_head's
;       1/300 s accumulator: lateness plus time since the tick pass) * 256/75 on a render-only pass (ACC < 75); on a tick pass the
;       render still shows the people as the PREVIOUS tick left them (the men update runs after it) and ACC has already had the tick
;       taken off, so FQ = (ACC + 75) * 256/75: the same straight line, which keeps the frame sequence monotonic (FQ = 0 on tick passes
;       makes every man jump back one step at each tick pass). PD+0 TOFF != 0 forces 0 there: the frame of the tick-only build, for
;       the pixel gate (tools/pmab.py --tonly --poke b8a80:0001) and for comparison, not for play.
;       Pause ($57ff2), an empty list (p3b_delta keeps it empty while no render-only pass happens: an 8 MHz machine) or FQ = 0: no offset,
;       `jsr $f898` is called untouched.
;       The clamp at the cell edge is deliberate: the sprite is drawn when the renderer reaches the cell the record is CHAINED in
;       (changed by the men update at the tick, not by this patch); past the edge it would be painted under the next cell's ground
;       when that cell is drawn later. A man crossing a cell edge (1 tick in 8 per axis) therefore waits at the edge for the rest of the tick.
;       Data: PD = $b8a80: +0 TOFF.w, +2 NMOV.w (mover count, written by p3b_delta), +4 APPLIED.w (this pass), +8 NPASS.l (passes
;       drawn with offsets), +16 RSEEN.l, +20 NSCAN.l and +24 ACTIVE.w (p3b_delta). OLD = $b8d00 (512 x x.w z.w = positions after the last tick), LST = $b9500 (512 x 10 B).
D       equ     $b8a00
PD      equ     $b8a80
LST     equ     $b9500
RST     equ     $bac40                  ; up to 160 x 6 B restore list (only visible movers applied this pass)
PEOPLE  equ     $51b66
        org     $130aa
        jsr     $baaa0.l

        org     $baaa0
ap:     movem.l d0-d7/a0-a5,-(a7)
        moveq   #0,d7
        tst.w   $57ff2.l                ; paused: the world is not moving, draw it as it is
        bne.w   .go
        move.w  PD+2.l,d6               ; NMOV
        beq.w   .go
        move.w  D+2.l,d0                ; ACC: 1/300 s since the last tick (render-only pass: < 75) ...
        tst.w   D+6.l                   ; RON
        bne.s   .fq
        tst.w   PD.l                    ; TOFF
        bne.w   .go
        add.w   #75,d0                  ; ... tick pass: ACC is what is left after the tick was taken off: one tick more
.fq:    mulu.w  #874,d0
        lsr.l   #8,d0                   ; *256/75 (874/256 = 3.4141, 256/75 = 3.4133)
        cmpi.w  #384,d0
        bls.s   .have
        move.w  #384,d0                 ; at most 1.5 steps ahead
.have:  tst.w   d0
        beq.w   .go
        move.w  $4bb3a.l,d4             ; visible cell window: [cam - rad - 1 .. cam - rad + grid + 1]
        sub.w   $57ffc.l,d4
        subq.w  #1,d4                   ; min_x
        move.w  $4bb3c.l,d5
        sub.w   $57ffc.l,d5
        subq.w  #1,d5                   ; min_z
        move.w  $fdf0.l,d1
        addq.w  #2,d1
        movea.w d1,a3                   ; span (unsigned upper bound)
        subq.w  #1,d6
        lea     LST.l,a1
        lea     PEOPLE.l,a0
        lea     RST.l,a4
.al:    move.w  (a1),d1                 ; record byte offset
        lea     (a0,d1.w),a2
        moveq   #0,d2
        move.b  8(a2),d2                ; cell_x = high byte of x
        sub.w   d4,d2
        cmp.w   a3,d2
        bhi.s   .skp
        moveq   #0,d2
        move.b  10(a2),d2               ; cell_z = high byte of z
        sub.w   d5,d2
        cmp.w   a3,d2
        bhi.s   .skp
        cmpi.w  #158,d7
        bhs.s   .skp
        move.w  d1,(a4)+                ; visible: record for restore
        move.w  8(a2),d2                ; x
        move.w  10(a2),d3               ; z
        move.w  d2,(a4)+                ; saved_x
        move.w  d3,(a4)+                ; saved_z
        move.w  2(a1),d1                ; dx
        muls.w  d0,d1
        asr.l   #8,d1
        movea.w d2,a5
        andi.w  #$ff,d2
        add.w   d1,d2
        bpl.s   .x1
        moveq   #0,d2
        bra.s   .x2
.x1:    cmpi.w  #255,d2
        ble.s   .x2
        move.w  #255,d2
.x2:    move.w  a5,d1
        andi.w  #$ff00,d1
        or.w    d2,d1
        move.w  d1,8(a2)
        move.w  4(a1),d1                ; dz
        muls.w  d0,d1
        asr.l   #8,d1
        movea.w d3,a5
        andi.w  #$ff,d3
        add.w   d1,d3
        bpl.s   .z1
        moveq   #0,d3
        bra.s   .z2
.z1:    cmpi.w  #255,d3
        ble.s   .z2
        move.w  #255,d3
.z2:    move.w  a5,d1
        andi.w  #$ff00,d1
        or.w    d3,d1
        move.w  d1,10(a2)
        addq.w  #1,d7
.skp:   lea     10(a1),a1
        dbra    d6,.al
        addq.l  #1,PD+8.l
.go:    move.w  d7,PD+4.l
        movem.l (a7)+,d0-d7/a0-a5
        jsr     $f898.l
        tst.w   PD+4.l
        beq.s   .out
        movem.l d1/d7/a0-a2,-(a7)
        move.w  PD+4.l,d7
        subq.w  #1,d7
        lea     RST.l,a1
        lea     PEOPLE.l,a0
.rl:    move.w  (a1)+,d1
        lea     (a0,d1.w),a2
        move.l  (a1)+,8(a2)
        dbra    d7,.rl
        clr.w   PD+4.l
        movem.l (a7)+,d1/d7/a0-a2
.out:   rts
