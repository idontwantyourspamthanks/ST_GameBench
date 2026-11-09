; name: p3b_interp
; default: yes
; site: $130aa
; orig: 4eb90000f898
; data: $b8a80 32
; data: $b8d00 2048
; data: $b9500 5120
; note: P5 predict-ahead (extrapolation) interpolation of the moving people-table records (work/notes/interp.md). Needs tick_* and
;       p3b_delta (the second half: it fills the velocity list after every world tick). Site: `jsr $f898` (landscape + objects,
;       the only call), replaced by `jsr ap`. The renderer takes a record's screen position from the LOW BYTES of its x/z words
;       ($8/$a(a3), `andi.w #$ff` in sub_011f1a: position inside the cell the record is chained into; the high bytes only select the cell
;       at the tick), so a render-only pass can draw a man part-way into his next step by shifting those low bytes.
;       ap: for every entry of the mover list (record offset, dx, dz, saved x, saved z: built by p3b_delta from the last tick's
;       position change, 0 when the change was more than STEP in an axis = teleport, spawn, landing...) writes
;       x/z low byte + (delta*FQ)>>8, clamped to 0..255 (the cell edge; the high byte, i.e. the chain cell, is untouched),
;       calls $f898, then writes the saved words back: the people table is bit-identical outside of the render.
;       FQ (256 = one tick = 12.5 VBL = 25 half-VBL; at most 384): the time since the tick the records describe, i.e. ACC (tick_head's
;       half-VBL accumulator: lateness plus time since the tick pass) * 256/25 on a render-only pass (ACC < 25); on a tick pass the
;       render still shows the people as the PREVIOUS tick left them (the men update runs after it) and ACC has already had the tick
;       taken off, so FQ = (ACC + 25) * 256/25: the same straight line, which keeps the frame sequence monotonic (FQ = 0 on tick passes
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
PEOPLE  equ     $51b66
        org     $130aa
        jsr     $b8aa0.l

        org     $b8aa0
ap:     movem.l d0-d7/a0-a2,-(a7)
        moveq   #0,d7
        tst.w   $57ff2.l                ; paused: the world is not moving, draw it as it is
        bne.w   .go
        move.w  PD+2.l,d6               ; NMOV
        beq.w   .go
        move.w  D+2.l,d0                ; ACC: half-VBLs since the last tick (render-only pass: < 25) ...
        tst.w   D+6.l                   ; RON
        bne.s   .fq
        tst.w   PD.l                    ; TOFF
        bne.w   .go
        add.w   #25,d0                  ; ... tick pass: ACC is what is left after the tick was taken off: one tick more
.fq:    mulu.w  #1311,d0
        lsr.l   #7,d0                   ; *256/25
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
        jsr     $f898.l
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
