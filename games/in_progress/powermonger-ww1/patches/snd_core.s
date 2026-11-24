; name: snd_core
; default: yes
; site: $1c4de
; orig: 4a390002d7b2
; init: $76780
; data: $76700 64
; data: $bc000 16384
; note: STE DMA sound for WW1 (master snd_core / work/notes/snd.md; WW1's player is the same code, re-sited: sequencer $1b77e -> $1c4de, chunk start $1ae5c -> $1bbbc, stop $1ae36 -> $1bb96,
;       game start $11f0 -> $6de; timer-A IRQ $1af32 -> $1bc92).  Needs snd_core + snd_start + snd_stop + snd_setup together.
;       The game's only sound is a timer-A sample player: the VBL handler calls the sequencer $1c4de, which starts one "chunk" (signed 8-bit PCM ended by a 0 byte, table at $2d9c6,
;       12 B/entry) at a time through $1bbbc; the timer-A IRQ $1bc92 then writes 3 YM volume registers per byte (265 cycles at 2457600/4/d Hz, d = $2d7ba, 2.4-8.7 kHz).
;       This site is the first instruction of the sequencer (`tst.b $2d7b2.l`, 6 B) -> `jsr $76400.l`.  The payload (STE-class hardware only: FLAGS bit0, probed by this patch's own
;       `init`, master kept the probe in its core) runs the DMA producer + the "chunk finished" test ($2d7b3 = timer IRQ busy flag, cleared when the DMA stops), then does the replaced
;       `tst.b $2d7b2.l; rts`.  Plain ST (FLAGS bit0 clear): just the `tst.b; rts`.
;       Layout: code $76400 (entry table: tick, start, stop, setup), state SV $76700 (FLAGS at SV+24), DMA staging buffer STAGE $bc000-$bffff (HIGH area; a `; data:` span: zeroed at boot).
;       A chunk plays from STAGE through a single-shot DMA (6258 or 12517 Hz mono).  MODE (SV+1, 0 = default): 0 = live nearest-neighbour resample of the chunk from its own rate
;       (614400/d) to the DMA rate, in 8-sample steps, one VBL ahead of the DMA read pointer; 1 = direct DMA of the chunk bytes at 6258 Hz.  Build option DEFMODE below.
;       Polarity: the bytes are used as they are (signed PCM); the LMC1992 inverts the DMA signal and the game's YM level table is an inverted ramp, so the two agree.
SV      equ     $76700
FLAGS   equ     SV+24                   ; .l bit0 = STE-class DMA sound hardware answers (bus-error safe probe + register read-back), bit1 = the probe ran, bit2 = probe took a bus error
DEFMODE equ     0                       ; 0 = live resample (default), 1 = direct DMA at 6258 Hz
STAGE   equ     $bc000
ENDFX   equ     $71b7c                  ; $5b012 + $16b6a: end of the unpacked FX.PAK (last chunk ends here; also the VBL counter's address)
FIRST   equ     512                     ; samples produced before the DMA starts
LEAD    equ     768                     ; samples kept produced ahead of the DMA read pointer
K6      equ     6433916                 ; 614400 * 65536 / 6258.29   (step = K / d, 16.16 source samples per output sample)
K12     equ     3216958                 ; 614400 * 65536 / 12516.58
o_busy  equ     0
o_mode  equ     1
o_rate  equ     3
o_src   equ     4
o_step  equ     8
o_idx   equ     10
o_frac  equ     12
o_p     equ     16
o_m     equ     20
        org     $1c4de
        jsr     $76400.l
        org     $76400
        bra.w   snd_tick                ; $76400
        bra.w   snd_start               ; $76404
        bra.w   snd_stop                ; $76408
        bra.w   snd_setup               ; $7640c
; ---------------------------------------------------------------------------------------------------------------
snd_tick:                               ; called by jsr from the sequencer: returns the flags of `tst.b $2d7b2.l`
        btst    #0,(FLAGS+3).l
        beq.s   .done
        tst.b   (SV+o_busy).l
        beq.s   .done
        btst    #0,$ffff8901.w            ; DMA still playing?
        bne.s   .prod
        clr.b   (SV+o_busy).l           ; chunk finished: what the timer IRQ's end (zero byte) did
        clr.b   $2d7b3.l
        bra.s   .done
.prod:  bsr.s   produce
.done:  tst.b   $2d7b2.l
        rts
; ---------------------------------------------------------------------------------------------------------------
produce:                                ; keep LEAD samples produced ahead of the DMA read position
        move.l  (SV+o_p).l,d0
        cmp.l   (SV+o_m).l,d0
        bhs.s   .x
        lea     $ff8909.l,a0
.rd:    movep.l 0(a0),d1
        movep.l 0(a0),d2
        cmp.l   d1,d2
        bne.s   .rd
        lsr.l   #8,d1                   ; DMA read address
        subi.l  #STAGE-LEAD,d1          ; position + LEAD
        andi.l  #$fffffff8,d1
        move.l  (SV+o_m).l,d2
        cmp.l   d2,d1
        bls.s   .c
        move.l  d2,d1
.c:     sub.l   d0,d1                   ; samples to make (multiple of 8)
        bls.s   .x
        bsr.s   resample
.x:     rts
; ---------------------------------------------------------------------------------------------------------------
resample:                               ; d0 = samples already made, d1 = count (multiple of 8, > 0); nearest neighbour, 16.16 phase
        move.w  sr,-(a7)
        move.w  #$2500,sr               ; MFP interrupts (keyboard/mouse) stay serviceable, VBL does not re-enter
        lea     STAGE.l,a1
        adda.l  d0,a1
        add.l   d1,d0
        move.l  d0,(SV+o_p).l
        lsr.l   #3,d1
        subq.w  #1,d1
        movea.l (SV+o_src).l,a0
        move.w  (SV+o_idx).l,d3
        move.w  (SV+o_frac).l,d2
        move.w  (SV+o_step).l,d4
        moveq   #0,d5
.l:     rept    8
        move.b  (a0,d3.w),(a1)+
        add.w   d4,d2
        addx.w  d5,d3
        endr
        dbra    d1,.l
        move.w  d3,(SV+o_idx).l
        move.w  d2,(SV+o_frac).l
        move.w  (a7)+,sr
        rts
; ---------------------------------------------------------------------------------------------------------------
snd_start:                              ; replaces the first instruction of $1bbbc: chunk $2d7b8, timer-A data d = $2d7ba
        btst    #0,(FLAGS+3).l
        bne.s   .ste
        lea     $2d9c6.l,a0             ; the displaced instruction, then the original
        jmp     $1bbc2.l
.ste:   movem.l d0-d7/a0-a6,-(a7)
        clr.b   $ffff8901.w
        move.w  $2d7b8.l,d0
        mulu.w  #12,d0
        lea     $2d9c6.l,a0
        movea.l (a0,d0.w),a2            ; chunk start
        move.l  8(a0,d0.w),d6           ; length incl. the 0 byte (the last chunk's table entry is bogus: clamp to the end of FX.DAT)
        move.l  #ENDFX,d7
        sub.l   a2,d7
        cmp.l   d7,d6
        bls.s   .n
        move.l  d7,d6
.n:     move.w  $2d7ba.l,d1
        bne.s   .d
        move.w  #256,d1                 ; timer data 0 = 256
.d:     lea     SV.l,a3
        cmpi.w  #99,d1                  ; source rate 614400/d below the DMA's 6258 Hz: play at 6258, else at 12517
        bhs.s   .r6
        move.l  #K12,d7
        moveq   #1,d4
        bra.s   .rs
.r6:    move.l  #K6,d7
        moveq   #0,d4
.rs:    divu.w  d1,d7
        bvc.s   .sv
        move.w  #$ffff,d7
.sv:    andi.l  #$ffff,d7               ; step, 16.16
        tst.b   o_mode(a3)
        bne.s   .direct
        move.b  d4,o_rate(a3)
        move.l  d6,d0
        subq.l  #1,d0                   ; sample bytes without the 0 terminator
        swap    d0
        clr.w   d0
        divu.w  d7,d0                   ; output samples = (n-1) / step
        andi.l  #$fff8,d0
        bne.s   .m8
        moveq   #8,d0
.m8:    move.l  a2,o_src(a3)
        move.w  d7,o_step(a3)
        clr.w   o_idx(a3)
        clr.w   o_frac(a3)
        move.l  d0,o_m(a3)
        move.l  d0,d6
        moveq   #0,d0
        move.l  #FIRST,d1
        cmp.l   d6,d1
        bls.s   .f
        move.l  d6,d1
.f:     bsr     resample
        move.l  #STAGE,d2
        move.l  d2,d3
        add.l   d6,d3
        bra.s   .go
.direct:                                ; DMA straight from the chunk at 6258 Hz
        clr.b   o_rate(a3)
        clr.l   o_p(a3)
        clr.l   o_m(a3)
        move.l  a2,d2
        andi.l  #-2,d2
        move.l  a2,d3
        add.l   d6,d3
        addq.l  #1,d3
        andi.l  #-2,d3
.go:    bsr.s   dmaprog
        st      o_busy(a3)
        st      $2d7b3.l                ; the busy flag the timer IRQ would clear at the zero byte
        movem.l (a7)+,d0-d7/a0-a6
        rts
dmaprog:                                ; d2 = start, d3 = end (exclusive), rate code from SV
        lea     $ff8900.l,a0
        move.b  (SV+o_rate).l,d0
        ori.b   #$80,d0                 ; mono
        move.b  d0,$21(a0)
        move.l  d2,d0
        move.b  d0,7(a0)
        lsr.l   #8,d0
        move.b  d0,5(a0)
        lsr.l   #8,d0
        move.b  d0,3(a0)
        move.l  d3,d0
        move.b  d0,$13(a0)
        lsr.l   #8,d0
        move.b  d0,$11(a0)
        lsr.l   #8,d0
        move.b  d0,$f(a0)
        move.b  #1,1(a0)                ; play, single frame
        rts
; ---------------------------------------------------------------------------------------------------------------
snd_stop:                               ; replaces `move.l #$1c55a,$1bc9a.l` at $1bb96 (stop the player, wait for the IRQ to end it)
        btst    #0,(FLAGS+3).l
        bne.s   .ste
        move.l  #$1c55a,$1bc9a.l
        jmp     $1bba0.l
.ste:   clr.b   $ffff8901.w
        clr.b   (SV+o_busy).l
        clr.b   $2d7b3.l
        rts
; ---------------------------------------------------------------------------------------------------------------
snd_setup:                              ; replaces `addq.l #8,a7 ; move.w #1,$2ec86.l` ($6de) after the FX tables are built by $1c59c
        movem.l d0-d7/a0-a6,-(a7)
        bsr.s   setup
        move.b  #DEFMODE,(SV+o_mode).l
        movem.l (a7)+,d0-d7/a0-a6
        move.w  #1,$2ec86.l             ; the displaced instructions
        move.l  (a7),8(a7)              ; addq.l #8,a7 under our return address
        addq.l  #8,a7
        rts
setup:  btst    #0,(FLAGS+3).l
        beq.s   .out
        bsr.s   microwire               ; the chunk bytes are used as they are: signed PCM; the LMC1992 inverts the DMA signal, as the
.out:   rts                             ; game's YM volume table does ($1af86: louder = lower byte value), so the polarity matches
microwire:                              ; master 40 (0 dB), left/right 20 (0 dB), mix DMA with YM, treble/bass 6 (flat); bus error safe
        movea.l sp,a2
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
; ---------------------------------------------------------------------------------------------------------------
; init (core.s calls it in supervisor mode, TOS's vectors intact; may not use a2 unsaved): the STE-class DMA sound probe, master's core.s `probe`.  A plain ST bus-errors on $ff8901;
; STE, Mega STE, TT and Falcon answer, and the frame start (mid byte $ff8905) must read back what is written (only tried while the DMA is stopped).
        org     $76780
init:   movem.l d0-d3/a0-a2,-(a7)
        moveq   #2,d3                   ; bit1: probe ran
        movea.l a7,a2                   ; the bus error handler resets the stack here
        movea.l $8.w,a1
        lea     .berr(pc),a0
        move.l  a0,$8.w
        move.b  $ffff8901.w,d0          ; DMA control; bus error on a plain ST
        btst    #0,d0
        bne.s   .yes                    ; DMA already running: it exists
        move.b  $ffff8905.w,d1          ; frame start mid byte
        move.b  #$5a,$ffff8905.w
        cmpi.b  #$5a,$ffff8905.w
        bne.s   .no
        move.b  #$a5,$ffff8905.w
        cmpi.b  #$a5,$ffff8905.w
        bne.s   .no
        move.b  d1,$ffff8905.w
.yes:   bset    #0,d3
        bra.s   .no
.berr:  movea.l a2,a7
        bset    #2,d3
.no:    move.l  a1,$8.w
        move.l  d3,FLAGS.l
        movem.l (a7)+,d0-d3/a0-a2
        rts
