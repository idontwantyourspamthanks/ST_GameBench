; name: p3b_interp
; default: yes
; site: $13e1e
; orig: 4eb90000fc78
; data: $73f80 32
; data: $c0000 2048
; data: $c0800 5632
; note: predict-ahead (extrapolation) interpolation of the moving people-table records (master p3b_interp / work/notes/interp.md, re-sited).  Needs tick_* and p3b_delta (the second
;       half: it fills the velocity list after every world tick).  Site: `jsr $fc78` (landscape + objects, the only call; master $f898), replaced by `jsr ap`.  The renderer
;       takes a record's screen position from the LOW BYTES of its x/z words ($8/$a(a3), `andi.w #$ff` at $12cc2 = master's sub_011f1a), so a render-only pass can draw a man part-way
;       into his next step by shifting those low bytes.  ap: for every entry of the mover list (record offset, dx, dz, saved x, saved z: built by p3b_delta from the last tick's
;       position change, 0 when the change was more than STEP in an axis = teleport, spawn, landing...) writes x/z low byte + (delta*FQ)>>8, clamped to 0..255 (the cell edge; the high
;       byte, i.e. the chain cell, is untouched), calls $fc78, then writes the saved words back: the people table is bit-identical outside of the render.
;       FQ (256 = one tick = 75 units of 1/300 s = 0.25 s; at most 384): ACC * 256/75 on a render-only pass; on a tick pass (ACC + 75) * 256/75 (see master's note: keeps the frame
;       sequence monotonic).  PD+0 TOFF != 0 forces 0 there (pixel gate).  Pause ($5a856), an empty list or FQ = 0: no offset, `jsr $fc78` is called untouched.
;       WW1 differences from master: addresses; the people table is $55df4 .. $5a7c7 = 350 records of $36 = 54 bytes (the men loop $158b2: `adda.w #$36,a1` ... `cmpa.l #$5a7c8,a1`;
;       master: 512 records of $32 from $51b66), so OLD / LST are filled / read for 350 records (the zero spans keep master's 2048 / 5120 bytes).
;       Data: PD = $73f80: +0 TOFF.w, +2 NMOV.w (mover count, written by p3b_delta), +4 APPLIED.w (this pass), +8 NPASS.l (passes drawn with offsets), +16 RSEEN.l, +20 NSCAN.l and
;       +24 ACTIVE.w (p3b_delta).  OLD = $c0000 (350 x x.w z.w = positions after the last tick), LST = $c0800 (350 x 10 B): HIGH area, zero-filled at boot.
D       equ     $72a80
PD      equ     $73f80
LST     equ     $c0800
RST     equ     $c15b0                  ; 350 x 6 B restore list (only visible movers applied this pass)
PEOPLE  equ     $55df4
        org     $13e1e
        jsr     $73c00.l

        org     $73c00
ap:     movem.l d0-d7/a0-a5,-(a7)
        moveq   #0,d7
        tst.w   $5a856.l                ; paused: the world is not moving, draw it as it is
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
        move.w  $50fd4.l,d4             ; visible cell window: [cam - rad - 1 .. cam - rad + grid + 1]
        sub.w   $5a860.l,d4
        subq.w  #1,d4                   ; min_x
        move.w  $50fd6.l,d5
        sub.w   $5a860.l,d5
        subq.w  #1,d5                   ; min_z
        move.w  $10260.l,d1
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
        jsr     $fc78.l
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
