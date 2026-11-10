; name: snd_core
; default: yes
; site: $c628
; orig: 082d00070093
; data: $8f000 256
; data: $8f800 1024
; note: STE DMA sound for Hunter (work/notes/snd.md).  The site is the sound-driver tick `$C628` (`btst #7,$93(a5)` = "3D loop
; note: active", then `movea.l $7f44(pc),a0 / jmp $40(a0)`); it becomes `jmp $8e000.l` (6 B).  The payload does the btst itself.
; note: Plain ST (FLAGS bit0 clear), no bank ('HSND' at $90000 missing): the payload runs the ORIGINAL tick unchanged (YM plays).
; note: STE: the original driver state machine runs as before, but its 16 YM operands ($ff8800/$ff8802 absolute.l inside the driver,
; note: offsets in tab_ym) are redirected to a scratch long (SV+$30) so the YM stays silent; then the payload reads the driver
; note: state (per channel: request/lock $c, duration $10, effect id $18, game volume word $4+2c), allocates up to 2 mixer
; note: voices (best sustained/loop + best one-shot, class table $AF38), mixes the Amiga samples (bank at $90000, native rate,
; note: 16.16 phase stepping, 16 volume tables) into a 1024-byte DMA ring at 6258 Hz mono, engine pitch from the object speed
; note: ($3e(obj) via the channel record $1de(a5)+8c: period = base - 4*speed, as the Amiga main code at $2dea).
; note: The 3D view left ($93 bit 7 clear): DMA stopped.  No timer, no new interrupt: everything runs inside the VBL tick.
; note: Memory: code $8e000..$8efff, state SV $8f000.., ring $8f800..$8fbff.  Preserves a5/a6/sp, uses d0-d7/a0-a4 (VBL saved them).
; note: 50/60 Hz (hn_hz.s, work/notes/timing.md): HZ_SKIP (written by hn_hz each VBL) non-zero = this VBL is not a world tick (60 Hz: 1 in 6).
; note: The original driver tick (state machine: request/priority/duration/volume) and the scan/voice allocation then wait, so effect durations
; note: and envelopes run on 50 Hz-equivalent ticks; the mixer (snd_act) still tops up the ring to TARGET samples ahead of the DMA position every VBL.
ENTRY   equ     $8e000
FLAGS   equ     $8bff0
HZ_SKIP equ     $8dbf2                  ; hn_hz.s: non-zero = this VBL is not a world tick (0 when hn_hz is not built)
BANK    equ     $90000
B_FX    equ     BANK+$100
B_PRIO  equ     BANK+$300
B_MULV  equ     BANK+$400
B_ENV2  equ     BANK+$500
B_HB    equ     BANK+$600
B_VTAB  equ     BANK+$1000
SV      equ     $8f000
RING    equ     $8f800
RL      equ     1024
TARGET  equ     192
K4      equ     9285653
v_mode  equ     0
v_in3d  equ     1
v_dma   equ     2
v_silent equ    3
v_wr    equ     4
v_mw    equ     6
v_n8    equ     8
v_run1  equ     10
v_run2  equ     12
v_gen   equ     $10
v_age   equ     $14
v_done  equ     $18
v_vol   equ     $20
v_key   equ     $24
v_keyp  equ     $2a
v_scr   equ     $30
v_vox0  equ     $40
v_vox1  equ     $68
x_ch    equ     0
x_gen   equ     1
x_mode  equ     2
x_base  equ     4
x_vt    equ     8
x_idx   equ     12
x_frac  equ     14
x_incf  equ     16
x_inci  equ     18
x_end   equ     20
x_loop  equ     22
x_per   equ     24
x_spd   equ     26
x_sbase equ     28
x_hbase equ     32
x_size  equ     40
        org     $c628
        jmp     ENTRY.l
        org     $8e000
snd_vbl:
        btst    #7,$93(a5)
        beq     snd_off3d
        cmpi.b  #2,SV+v_mode
        beq.s   snd_run
        tst.b   SV+v_mode
        bne.s   snd_pass
        bsr     snd_init0
        cmpi.b  #2,SV+v_mode
        beq.s   snd_run
snd_pass:                               ; the original tick
        tst.b   HZ_SKIP.l               ; hn_hz: not a world tick (60 Hz): the driver waits
        bne.s   .rts
        movea.l $7f44.w,a0
        jmp     $40(a0)
.rts:   rts
snd_init0:                              ; once: STE hardware (loader probe) and sample bank present?
        move.b  #1,SV+v_mode
        btst    #0,FLAGS+3.l
        beq.s   .rts
        cmpi.l  #'HSND',BANK.l
        bne.s   .rts
        cmpi.w  #2,BANK+4.l
        bne.s   .rts
        move.b  #2,SV+v_mode
.rts:   rts
snd_run:
        tst.b   SV+v_in3d
        bne.s   .in
        bsr     snd_enter
.in:    movea.l $7f44.w,a0
        cmpi.l  #SV+v_scr,$24(a0)       ; driver still redirected (it may be reloaded)?
        beq.s   .ok
        bsr     snd_ympatch
        movea.l $7f44.w,a0
.ok:    tst.b   HZ_SKIP.l               ; hn_hz: not a world tick (60 Hz): the driver state machine and the scan wait,
        bne.s   .top                    ; only the mixer tops up the ring (voices and phases as the last tick left them)
        jsr     $40(a0)                 ; the original state machine (its YM writes go to the scratch)
        bra     snd_update
.top:   lea     SV.l,a4
        bra     snd_act
snd_off3d:                              ; 3D view not active: the original did nothing
        tst.b   SV+v_in3d
        beq.s   .rts
        clr.b   SV+v_in3d
        clr.b   $ff8901.l               ; DMA off
        clr.b   SV+v_dma
        st      SV+v_vox0+x_ch
        st      SV+v_vox1+x_ch
.rts:   rts
snd_enter:                              ; first tick of a 3D session
        bsr     snd_ympatch
        bsr     snd_ymsilence
        tst.b   SV+v_mw
        bne.s   .mw
        bsr     snd_microwire
        st      SV+v_mw
.mw:    lea     SV.l,a0
        moveq   #0,d0
        move.l  d0,v_gen(a0)
        move.l  d0,v_age(a0)
        move.l  d0,v_done(a0)
        clr.b   v_dma(a0)
        clr.b   v_silent(a0)
        st      v_vox0+x_ch(a0)
        st      v_vox1+x_ch(a0)
        st      v_in3d(a0)
        rts
snd_ympatch:                            ; redirect the driver's YM absolute operands to SV+v_scr (idempotent)
        movea.l $7f44.w,a0
        lea     tab_ym(pc),a1
        moveq   #15,d0
.l:     move.w  (a1)+,d1
        move.l  (a0,d1.w),d2
        move.l  #SV+v_scr,d3
        cmpi.l  #$ff8800,d2
        beq.s   .w
        addq.l  #2,d3
        cmpi.l  #$ff8802,d2
        bne.s   .n
.w:     move.l  d3,(a0,d1.w)
.n:     dbra    d0,.l
        bra     snd_cflush
tab_ym: dc.w    $24,$2e,$38,$15c,$162,$16e,$174,$17c,$2fe,$304,$314,$31a,$34c,$354,$36c,$378
snd_cflush:                             ; 68020+ (the _CPU cookie): drop the instruction cache after the code patch
        move.l  $5a0.w,d0
        beq.s   .rts
        movea.l d0,a1
.l:     move.l  (a1)+,d0
        beq.s   .rts
        move.l  (a1)+,d1
        cmpi.l  #'_CPU',d0
        bne.s   .l
        cmpi.l  #20,d1
        blt.s   .rts
        dc.w    $4e7a,$0002             ; movec cacr,d0
        ori.l   #$808,d0
        dc.w    $4e7b,$0002             ; movec d0,cacr
.rts:   rts
snd_ymsilence:                          ; the YM may still hold the title music: effects off, volumes 0
        lea     $ff8800.l,a0
        moveq   #0,d1
        move.b  #7,(a0)
        move.b  (a0),d0
        ori.b   #$3f,d0
        move.b  #7,(a0)
        move.b  d0,2(a0)
        move.b  #8,(a0)
        move.b  d1,2(a0)
        move.b  #9,(a0)
        move.b  d1,2(a0)
        move.b  #10,(a0)
        move.b  d1,2(a0)
        rts
snd_microwire:                          ; master 40 (0 dB), left/right 20 (0 dB), mix DMA with YM, treble/bass 6 (flat)
        movea.l sp,a2                   ; bus error safe (the Falcon has no Microwire): the handler resets the stack here
        movea.l $8.w,a1
        lea     .berr(pc),a0
        move.l  a0,$8.w
        lea     .cmds(pc),a0
        moveq   #5,d3
.nx:    move.w  #$07ff,$ff8924.l
        move.w  (a0)+,$ff8922.l
        move.w  #1000,d0
.w:     cmpi.w  #$07ff,$ff8924.l
        beq.s   .d
        dbra    d0,.w
.d:     dbra    d3,.nx
.out:   move.l  a1,$8.w
        rts
.berr:  movea.l a2,sp
        bra.s   .out
.cmds:  dc.w    $04e8,$0554,$0514,$0401,$0486,$0446
snd_dmapos:                             ; d0.w = DMA read position inside the ring
        lea     $ff8909.l,a0
.rd:    movep.l 0(a0),d0
        movep.l 0(a0),d1
        cmp.l   d0,d1
        bne.s   .rd
        lsr.l   #8,d0
        subi.l  #RING,d0
        andi.w  #RL-1,d0
        rts
snd_dmastart:
        lea     $ff8900.l,a0
        moveq   #0,d0
        move.b  d0,1(a0)
        move.b  #(RING>>16)&$ff,3(a0)
        move.b  #(RING>>8)&$ff,5(a0)
        move.b  #RING&$ff,7(a0)
        move.b  #((RING+RL)>>16)&$ff,$f(a0)
        move.b  #((RING+RL)>>8)&$ff,$11(a0)
        move.b  #(RING+RL)&$ff,$13(a0)
        move.b  #$80,$21(a0)            ; mono, 6258 Hz
        move.b  #3,1(a0)                ; play + repeat
        rts
; ---------------------------------------------------------------------------------------------------------------
snd_update:
        movea.l $7f44.w,a1
        lea     $3d6(a1),a1             ; driver channel state: request +0, volume words +4, lock +$c, duration +$10, effect +$18
        lea     SV.l,a4
        tst.b   v_dma(a4)
        bne.s   .scan
        tst.b   $10(a1)
        bne.s   .scan
        tst.b   $11(a1)
        bne.s   .scan
        tst.b   $12(a1)
        beq     snd_ret
.scan:  moveq   #2,d7
.sc:    move.w  d7,d0
        add.w   d0,d0
        move.w  #$ffff,v_key(a4,d0.w)   ; default: not a candidate
        move.w  #$ffff,v_keyp(a4,d0.w)
        tst.b   $10(a1,d7.w)            ; duration counter: 0 = channel idle
        beq     .idle
        cmpi.b  #$32,$c(a1,d7.w)        ; lock counter = fresh start this tick
        bne.s   .age
        addq.b  #1,v_gen(a4,d7.w)
        clr.b   v_age(a4,d7.w)
        clr.b   v_done(a4,d7.w)
        bra.s   .chk
.age:   addq.b  #1,v_age(a4,d7.w)       ; saturating
        bne.s   .chk
        st      v_age(a4,d7.w)
.chk:   tst.b   v_done(a4,d7.w)
        bne     .nx
        moveq   #0,d5
        move.b  $18(a1,d7.w),d5
        cmpi.b  #21,d5
        bhs     .nx
        move.w  d0,d2
        move.w  4(a1,d2.w),d2
        andi.w  #15,d2                  ; game volume 0..15
        move.w  d5,d1
        asl.w   #4,d1
        lea     B_FX.l,a0
        adda.w  d1,a0
        move.w  10(a0),d3               ; flags
        btst    #1,d3
        beq.s   .nenv
        moveq   #0,d4
        move.b  v_age(a4,d7.w),d4
        lea     B_ENV2.l,a2
        move.b  (a2,d4.w),d4
        asl.w   #4,d2
        or.w    d4,d2
        lea     B_MULV.l,a2
        move.b  (a2,d2.w),d2
.nenv:  tst.w   d2
        beq.s   .nx
        move.b  d2,v_vol(a4,d7.w)
        lea     B_PRIO.l,a2
        moveq   #0,d4
        move.b  (a2,d5.w),d4
        asl.w   #8,d4                   ; key = class<<8 | (15-vol)<<4 | min(age,15)
        moveq   #15,d1
        sub.w   d2,d1
        asl.w   #4,d1
        or.w    d1,d4
        moveq   #0,d1
        move.b  v_age(a4,d7.w),d1
        cmpi.b  #15,d1
        bls.s   .a15
        moveq   #15,d1
.a15:   or.w    d1,d4
        move.w  d4,v_key(a4,d0.w)
        btst    #2,d3                   ; sustained effects rank after every one-shot for the first voice
        beq.s   .ns
        addi.w  #$4000,d4
.ns:    move.w  d4,v_keyp(a4,d0.w)
        bra.s   .nx
.idle:  clr.b   v_age(a4,d7.w)
.nx:    dbra    d7,.sc
; ---- first voice: best one-shot, else best sustained; second voice: best of the rest
        movem.w v_keyp(a4),d0-d2
        moveq   #0,d4
        move.w  d0,d5
        cmp.w   d5,d1
        bhs.s   .f1
        move.w  d1,d5
        moveq   #1,d4
.f1:    cmp.w   d5,d2
        bhs.s   .f2
        move.w  d2,d5
        moveq   #2,d4
.f2:    moveq   #-1,d3
        cmpi.w  #$ffff,d5
        bne.s   .f3
        moveq   #-1,d4                  ; no candidate at all
        bra.s   .g3
.f3:    move.w  d4,d5
        add.w   d5,d5
        move.w  #$ffff,v_key(a4,d5.w)   ; exclude the first
        movem.w v_key(a4),d0-d2
        moveq   #0,d3
        move.w  d0,d5
        cmp.w   d5,d1
        bhs.s   .g1
        move.w  d1,d5
        moveq   #1,d3
.g1:    cmp.w   d5,d2
        bhs.s   .g2
        move.w  d2,d5
        moveq   #2,d3
.g2:    cmpi.w  #$ffff,d5
        bne.s   .g3
        moveq   #-1,d3
.g3:
; ---- keep voices whose channel is still wanted with the same start; free the others
        lea     v_vox0(a4),a3
        moveq   #1,d7
.kp:    move.b  x_ch(a3),d0
        bmi.s   .kn
        ext.w   d0
        move.b  v_gen(a4,d0.w),d1
        cmp.b   x_gen(a3),d1
        bne.s   .fr
        cmp.w   d4,d0
        bne.s   .k2
        moveq   #-1,d4
        bra.s   .kn
.k2:    cmp.w   d3,d0
        bne.s   .fr
        moveq   #-1,d3
        bra.s   .kn
.fr:    st      x_ch(a3)
.kn:    lea     x_size(a3),a3
        dbra    d7,.kp
; ---- start the wanted channels that have no voice yet
        move.w  d4,d7
        bmi.s   .p2
        bsr     snd_place
.p2:    move.w  d3,d7
        bmi.s   .p3
        bsr     snd_place
.p3:
; ---- per tick voice parameters: volume table and engine pitch
        lea     v_vox0(a4),a3
        moveq   #1,d6
.up:    move.b  x_ch(a3),d7
        bmi     .upn
        andi.w  #3,d7
        moveq   #0,d0
        move.b  v_vol(a4,d7.w),d0
        move.l  x_sbase(a3),x_base(a3)
        clr.b   x_mode(a3)
        cmpi.b  #15,d0                  ; full volume: the half-scale copy needs no table lookup
        bne.s   .tb
        tst.l   x_hbase(a3)
        beq.s   .tb
        move.l  x_hbase(a3),x_base(a3)
        st      x_mode(a3)
.tb:    lsl.w   #8,d0
        addi.l  #B_VTAB,d0
        move.l  d0,x_vt(a3)
        lea     $1de(a5),a0             ; channel record: flag byte = engine object, +6 = object offset
        move.w  d7,d0
        asl.w   #3,d0
        tst.b   (a0,d0.w)
        beq     .upn
        move.w  6(a0,d0.w),d0
        lea     $262(a5),a2
        move.w  $3e(a2,d0.w),d0         ; object speed
        cmp.w   x_spd(a3),d0            ; unchanged: the increment is still right
        beq     .upn
        move.w  d0,x_spd(a3)
        asl.w   #2,d0
        move.w  x_per(a3),d1
        sub.w   d0,d1
        cmpi.w  #284,d1
        bge.s   .p1
        move.w  #284,d1
.p1:    cmpi.w  #2047,d1
        ble.s   .p2b
        move.w  #2047,d1
.p2b:   move.l  #K4,d2
        divu.w  d1,d2
        andi.l  #$ffff,d2
        lsl.l   #2,d2
        move.w  d2,x_incf(a3)
        swap    d2
        move.w  d2,x_inci(a3)
.upn:   lea     x_size(a3),a3
        dbra    d6,.up
; ---- active voices: a2 = first, a3 = second, d5 = count
snd_act:
        lea     v_vox0(a4),a2
        lea     v_vox1(a4),a3
        moveq   #0,d5
        tst.b   x_ch(a2)
        bmi.s   .c1
        addq.w  #1,d5
.c1:    tst.b   x_ch(a3)
        bmi.s   .c2
        addq.w  #1,d5
        tst.b   x_ch(a2)
        bpl.s   .both
        movea.l a3,a2
        bra.s   .c2
.both:  tst.b   x_mode(a2)              ; two voices: a table-free one goes first
        bne.s   .c2
        tst.b   x_mode(a3)
        beq.s   .c2
        exg     a2,a3
.c2:    tst.b   v_dma(a4)
        bne.s   .on
        tst.w   d5
        beq     snd_ret
        clr.w   v_wr(a4)                ; start: fill the first TARGET samples, then enable the DMA at the ring start
        moveq   #TARGET/8,d0
        bsr     snd_mix
        bsr     snd_dmastart
        clr.b   v_silent(a4)
        st      v_dma(a4)
        bra     .post
.on:    bsr     snd_dmapos              ; d0 = play position; keep the write cursor TARGET samples ahead
        move.w  v_wr(a4),d1
        sub.w   d0,d1
        andi.w  #RL-1,d1
        cmpi.w  #768,d1
        bls.s   .okp
        addi.w  #16,d0                  ; underrun: resync just ahead of the DMA
        andi.w  #RL-8,d0
        move.w  d0,v_wr(a4)
        moveq   #16,d1
.okp:   move.w  #TARGET,d0
        sub.w   d1,d0
        ble.s   .sil
        lsr.w   #3,d0
        beq.s   .sil
        cmpi.w  #31,d0
        bls.s   .n8
        moveq   #31,d0
.n8:    bsr     snd_mix
.sil:   tst.w   d5
        bne.s   .nsil
        addq.b  #1,v_silent(a4)
        cmpi.b  #12,v_silent(a4)        ; ring completely silent: stop the DMA
        blo     .post
        clr.b   $ff8901.l
        clr.b   v_dma(a4)
        bra     .post
.nsil:  clr.b   v_silent(a4)
.post:  lea     v_vox0(a4),a3           ; loop wrap / one-shot end
        moveq   #1,d6
.pl:    tst.b   x_ch(a3)
        bmi.s   .pn
        move.w  x_idx(a3),d1
        cmp.w   x_end(a3),d1
        blo.s   .pn
        move.w  x_loop(a3),d0
        beq.s   .once
        sub.w   d0,d1
        move.w  d1,x_idx(a3)
        bra.s   .pn
.once:  move.b  x_ch(a3),d0
        ext.w   d0
        st      v_done(a4,d0.w)
        st      x_ch(a3)
.pn:    lea     x_size(a3),a3
        dbra    d6,.pl
snd_ret: rts
snd_place:                              ; d7 = channel: take a free voice slot and start it
        lea     v_vox0(a4),a3
        tst.b   x_ch(a3)
        bmi.s   snd_vstart
        lea     v_vox1(a4),a3
snd_vstart:                             ; a3 = slot, d7 = channel, a1 = driver state, a4 = SV
        moveq   #0,d1
        move.b  $18(a1,d7.w),d1
        asl.w   #4,d1
        lea     B_FX.l,a0
        adda.w  d1,a0
        move.b  d7,x_ch(a3)
        move.b  v_gen(a4,d7.w),x_gen(a3)
        move.l  (a0),x_base(a3)
        move.l  (a0),x_sbase(a3)
        lsr.w   #2,d1                   ; effect id * 4: half-scale copy (loops only) for the table-free path
        lea     B_HB.l,a2
        move.l  (a2,d1.w),x_hbase(a3)
        clr.b   x_mode(a3)
        move.w  4(a0),x_end(a3)
        move.w  6(a0),x_loop(a3)
        move.w  8(a0),x_per(a3)
        move.w  #$7fff,x_spd(a3)
        move.l  12(a0),d0
        move.w  d0,x_incf(a3)
        swap    d0
        move.w  d0,x_inci(a3)
        clr.w   x_frac(a3)
        clr.w   x_idx(a3)
        tst.w   x_loop(a3)
        bne.s   .rts
        moveq   #0,d0                   ; a one-shot that was not heard from its start: skip ahead by its age
        move.b  v_age(a4,d7.w),d0
        beq.s   .rts
        mulu.w  #125,d0
        move.w  d0,d2
        mulu.w  x_incf(a3),d2
        swap    d2
        tst.w   x_inci(a3)
        beq.s   .ni
        add.w   d0,d2
.ni:    cmp.w   x_end(a3),d2
        bhs.s   .dead
        move.w  d2,x_idx(a3)
.rts:   rts
.dead:  st      x_ch(a3)
        st      v_done(a4,d7.w)
        rts
; ---------------------------------------------------------------------------------------------------------------
snd_mix:                                ; d0 = groups of 8 outputs (>=1), d5 = voices, a2/a3 = voices, a4 = SV
        move.w  d5,-(sp)
        move.w  d0,v_n8(a4)
        move.w  v_wr(a4),d1
        move.w  #RL,d2
        sub.w   d1,d2
        lsr.w   #3,d2                   ; groups to the ring end
        cmp.w   d0,d2
        bls.s   .m1
        move.w  d0,d2
.m1:    sub.w   d2,d0
        move.w  d2,v_run1(a4)
        move.w  d0,v_run2(a4)
        subq.w  #1,d5
        bmi.s   .z
        beq.s   .one
        tst.b   x_mode(a2)
        bne.s   .d2
        bsr     mix2tt
        bra.s   .adv
.d2:    tst.b   x_mode(a3)
        bne.s   .dd
        bsr     mix2dt
        bra.s   .adv
.dd:    bsr     mix2dd
        bra.s   .adv
.one:   tst.b   x_mode(a2)
        bne.s   .od
        bsr     mix1t
        bra.s   .adv
.od:    bsr     mix1d
        bra.s   .adv
.z:     bsr     mixz
.adv:   move.w  v_n8(a4),d0
        lsl.w   #3,d0
        add.w   v_wr(a4),d0
        andi.w  #RL-1,d0
        move.w  d0,v_wr(a4)
        move.w  (sp)+,d5
        rts
mixz:   moveq   #0,d0
        lea     RING.l,a0
        adda.w  v_wr(a4),a0
        move.w  v_run1(a4),d1
        bsr.s   .fill
        lea     RING.l,a0
        move.w  v_run2(a4),d1
.fill:  subq.w  #1,d1
        bmi.s   .r
.l:     move.l  d0,(a0)+
        move.l  d0,(a0)+
        dbra    d1,.l
.r:     rts
MIX1T   macro
        move.b  (a0,d0.w),d4
        move.b  (a2,d4.w),(a6)+
        add.w   a4,d1
        addx.w  d6,d0
        endm
MIX1D   macro
        move.b  (a0,d0.w),(a6)+
        add.w   a4,d1
        addx.w  d6,d0
        endm
MIX2TT  macro
        move.b  (a0,d0.w),d4
        move.b  (a2,d4.w),d4
        move.b  (a1,d2.w),d5
        move.b  (a3,d5.w),d5
        add.b   d5,d4
        move.b  d4,(a6)+
        add.w   a4,d1
        addx.w  d6,d0
        add.w   a5,d3
        addx.w  d7,d2
        endm
MIX2DT  macro
        move.b  (a0,d0.w),d4
        move.b  (a1,d2.w),d5
        move.b  (a3,d5.w),d5
        add.b   d5,d4
        move.b  d4,(a6)+
        add.w   a4,d1
        addx.w  d6,d0
        add.w   a5,d3
        addx.w  d7,d2
        endm
MIX2DD  macro
        move.b  (a0,d0.w),d4
        move.b  (a1,d2.w),d5
        add.b   d5,d4
        move.b  d4,(a6)+
        add.w   a4,d1
        addx.w  d6,d0
        add.w   a5,d3
        addx.w  d7,d2
        endm
MIX1R   macro
\1:     movem.l a2/a4-a6,-(sp)
        movea.l x_base(a2),a0
        move.w  x_idx(a2),d0
        move.w  x_frac(a2),d1
        movea.w x_incf(a2),a4
        move.w  x_inci(a2),d6
        movea.l x_vt(a2),a2
        moveq   #0,d4
        lea     RING.l,a6
        adda.w  SV+v_wr,a6
        move.w  SV+v_run1,-(sp)
        beq.s   .s1
        bsr.s   .loop
.s1:    addq.w  #2,sp
        move.w  SV+v_run2,-(sp)
        beq.s   .s2
        lea     RING.l,a6
        bsr.s   .loop
.s2:    addq.w  #2,sp
        movea.l (sp),a2
        move.w  d0,x_idx(a2)
        move.w  d1,x_frac(a2)
        movem.l (sp)+,a2/a4-a6
        rts
.loop:  rept    8
        \2
        endr
        subq.w  #1,4(sp)
        bne     .loop
        rts
        endm
MIX2R   macro
\1:     movem.l a2-a6,-(sp)
        movea.l x_base(a2),a0
        movea.l x_base(a3),a1
        move.w  x_idx(a2),d0
        move.w  x_frac(a2),d1
        movea.w x_incf(a2),a4
        move.w  x_inci(a2),d6
        move.w  x_idx(a3),d2
        move.w  x_frac(a3),d3
        movea.w x_incf(a3),a5
        move.w  x_inci(a3),d7
        movea.l x_vt(a3),a3
        movea.l x_vt(a2),a2
        moveq   #0,d4
        moveq   #0,d5
        lea     RING.l,a6
        adda.w  SV+v_wr,a6
        move.w  SV+v_run1,-(sp)
        beq.s   .s1
        bsr.s   .loop
.s1:    addq.w  #2,sp
        move.w  SV+v_run2,-(sp)
        beq.s   .s2
        lea     RING.l,a6
        bsr.s   .loop
.s2:    addq.w  #2,sp
        movea.l (sp),a0
        move.w  d0,x_idx(a0)
        move.w  d1,x_frac(a0)
        movea.l 4(sp),a1
        move.w  d2,x_idx(a1)
        move.w  d3,x_frac(a1)
        movem.l (sp)+,a2-a6
        rts
.loop:  rept    8
        \2
        endr
        subq.w  #1,4(sp)
        bne     .loop
        rts
        endm
        MIX1R   mix1t,MIX1T
        MIX1R   mix1d,MIX1D
        MIX2R   mix2tt,MIX2TT
        MIX2R   mix2dt,MIX2DT
        MIX2R   mix2dd,MIX2DD
