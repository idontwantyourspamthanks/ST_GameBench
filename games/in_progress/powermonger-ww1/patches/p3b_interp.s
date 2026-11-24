; name: p3b_interp
; default: yes
; site: $13e1e
; orig: 4eb90000fc78
; data: $73f80 32
; data: $c0000 2048
; data: $c0800 5120
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
PEOPLE  equ     $55df4
        org     $13e1e
        jsr     $73c00.l

        org     $73c00
ap:     movem.l d0-d7/a0-a2,-(a7)
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
        move.w  d6,d7                   ; applied
        subq.w  #1,d6
        lea     LST.l,a1
        lea     PEOPLE.l,a0
.al:    move.w  (a1)+,d1                ; record byte offset
        lea     (a0,d1.w),a2
        move.w  (a1)+,d2                ; dx
        move.w  (a1)+,d3                ; dz
        move.w  8(a2),d4                ; x
        move.w  10(a2),d5               ; z
        move.w  d4,(a1)+                ; saved
        move.w  d5,(a1)+
        muls.w  d0,d2
        asr.l   #8,d2
        muls.w  d0,d3
        asr.l   #8,d3
        move.w  d4,d1
        andi.w  #$ff,d1
        add.w   d2,d1
        bpl.s   .x1
        moveq   #0,d1
        bra.s   .x2
.x1:    cmpi.w  #255,d1
        ble.s   .x2
        move.w  #255,d1
.x2:    andi.w  #$ff00,d4
        or.w    d1,d4
        move.w  d4,8(a2)
        move.w  d5,d1
        andi.w  #$ff,d1
        add.w   d3,d1
        bpl.s   .z1
        moveq   #0,d1
        bra.s   .z2
.z1:    cmpi.w  #255,d1
        ble.s   .z2
        move.w  #255,d1
.z2:    andi.w  #$ff00,d5
        or.w    d1,d5
        move.w  d5,10(a2)
        dbra    d6,.al
        addq.l  #1,PD+8.l
.go:    move.w  d7,PD+4.l
        movem.l (a7)+,d0-d7/a0-a2
        jsr     $fc78.l
        tst.w   PD+4.l
        beq.s   .out
        movem.l d0-d2/d7/a0-a2,-(a7)
        move.w  PD+4.l,d7
        subq.w  #1,d7
        lea     LST.l,a1
        lea     PEOPLE.l,a0
.rl:    move.w  (a1),d1
        lea     (a0,d1.w),a2
        move.w  6(a1),8(a2)
        move.w  8(a1),10(a2)
        lea     10(a1),a1
        dbra    d7,.rl
        clr.w   PD+4.l
        movem.l (a7)+,d0-d2/d7/a0-a2
.out:   rts
