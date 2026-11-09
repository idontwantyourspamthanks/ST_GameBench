; name: snd_core
; default: no
; site: $1b77e
; orig: 4a390002c992
; data: $e0e00 64
; data: $e1000 16384
; note: STE DMA sound for Powermonger (work/notes/snd.md).  Needs snd_core + snd_start + snd_stop + snd_setup together.
; note: The game's only sound is a timer-A sample player: the VBL handler ($1282) calls the sequencer $1b77e, which starts one
; note: "chunk" (signed 8-bit PCM ended by a 0 byte, table at $2cba6, 12 B/entry) at a time through $1ae5c; the timer-A IRQ $1af32
; note: then writes 3 YM volume registers per byte (264 cycles at 2457600/4/d Hz, d = $2c99a, 2.4-8.7 kHz).  No YM tone/noise, no music.
; note: This site is the first instruction of the sequencer (`tst.b $2c992.l`, 6 B) -> `jsr $e0000.l`.  The payload (STE only: FLAGS bit0)
; note: runs the DMA producer + the "chunk finished" test ($2c993 = timer IRQ busy flag, cleared when the DMA stops), then does the
; note: replaced `tst.b $2c992.l; rts`.  Plain ST (FLAGS bit0 clear): just the `tst.b; rts`.
; note: Layout: code $e0000 (entry table: tick, start, stop, setup, live), state SV $e0e00, DMA staging buffer STAGE $e1000-$e4fff
; note: (a `; data:` span: zeroed at boot, no disk bytes).
; note: A chunk plays from STAGE through a single-shot DMA (6258 or 12517 Hz mono).  MODE (SV+1, 0 = default): 0 = live nearest-neighbour
; note: resample of the chunk from its own rate (614400/d) to the DMA rate, in 8-sample steps, one VBL ahead of the DMA read pointer;
; note: 1 = direct DMA of the chunk bytes at 6258 Hz (zero CPU, pitch/duration follow the DMA rate instead of d).
FLAGS   equ     $b87f0
SV      equ     $e0e00
STAGE   equ     $e1000
ENDFX   equ     $6f304                  ; $5879a + $16b6a: end of the unpacked FX.DAT (last chunk ends here)
FIRST   equ     512                     ; samples produced before the DMA starts
LEAD    equ     768                     ; samples kept produced ahead of the DMA read pointer
K6      equ     6433916                 ; 614400 * 65536 / 6258.29   (step = K / d, 16.16 source samples per output sample)
K12     equ     3216958                 ; 614400 * 65536 / 12516.58
o_busy  equ     0
o_mode  equ     1
o_neg   equ     2
o_rate  equ     3
o_src   equ     4
o_step  equ     8
o_idx   equ     10
o_frac  equ     12
o_p     equ     16
o_m     equ     20
        org     $1b77e
        jsr     $e0000.l
        org     $e0000
        bra.w   snd_tick                ; $e0000
        bra.w   snd_start               ; $e0004
        bra.w   snd_stop                ; $e0008
        bra.w   snd_setup               ; $e000c
        bra.w   snd_live                ; $e0010  debugger entry for the snapshot gates (ends with jmp $13020)
; ---------------------------------------------------------------------------------------------------------------
snd_tick:                               ; called by jsr from the sequencer: returns the flags of `tst.b $2c992.l`
        btst    #0,(FLAGS+3).l
        beq.s   .done
        tst.b   (SV+o_busy).l
        beq.s   .done
        btst    #0,$ffff8901.w            ; DMA still playing?
        bne.s   .prod
        clr.b   (SV+o_busy).l           ; chunk finished: what the timer IRQ's end (zero byte) did
        clr.b   $2c993.l
        bra.s   .done
.prod:  bsr.s   produce
.done:  tst.b   $2c992.l
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
snd_start:                              ; replaces the first instruction of $1ae5c: chunk $2c998, timer-A data d = $2c99a
        btst    #0,(FLAGS+3).l
        bne.s   .ste
        lea     $2cba6.l,a0             ; the displaced instruction, then the original
        jmp     $1ae62.l
.ste:   movem.l d0-d7/a0-a6,-(a7)
        clr.b   $ffff8901.w
        move.w  $2c998.l,d0
        mulu.w  #12,d0
        lea     $2cba6.l,a0
        movea.l (a0,d0.w),a2            ; chunk start
        move.l  8(a0,d0.w),d6           ; length incl. the 0 byte (the last chunk's table entry is bogus: clamp to the end of FX.DAT)
        move.l  #ENDFX,d7
        sub.l   a2,d7
        cmp.l   d7,d6
        bls.s   .n
        move.l  d7,d6
.n:     move.w  $2c99a.l,d1
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
        st      $2c993.l                ; the busy flag the timer IRQ would clear at the zero byte
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
snd_stop:                               ; replaces `move.l #$1b7fa,$1af3a.l` at $1ae36 (stop the player, wait for the IRQ to end it)
        btst    #0,(FLAGS+3).l
        bne.s   .ste
        move.l  #$1b7fa,$1af3a.l
        jmp     $1ae40.l
.ste:   clr.b   $ffff8901.w
        clr.b   (SV+o_busy).l
        clr.b   $2c993.l
        rts
; ---------------------------------------------------------------------------------------------------------------
snd_setup:                              ; replaces `addq.l #8,a7 ; move.w #1,$2de66.l` ($11f0) after the FX.DAT tables are built by $1b83c
        movem.l d0-d7/a0-a6,-(a7)
        bsr.s   setup
        movem.l (a7)+,d0-d7/a0-a6
        move.w  #1,$2de66.l             ; the displaced instructions
        move.l  (a7),8(a7)              ; addq.l #8,a7 under our return address
        addq.l  #8,a7
        rts
setup:  btst    #0,(FLAGS+3).l
        beq.s   .out
        tst.b   (SV+o_neg).l
        bne.s   .mw
        st      (SV+o_neg).l
        movea.l ($2cba6).l,a0           ; chunk 0 = start of the sample area
        move.l  #ENDFX,d0
        sub.l   a0,d0
.nl:    move.b  (a0),d1                 ; the YM table in $1af86 is an inverted ramp (louder = lower byte value): DMA = -sample
        neg.b   d1
        bvc.s   .st
        subq.b  #1,d1                   ; -(-128) = +127
.st:    move.b  d1,(a0)+
        subq.l  #1,d0
        bne.s   .nl
.mw:    bsr.s   microwire
.out:   rts
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
snd_live:                               ; gates only: run from a snapshot's main loop with `r pc=$e0010` at pc = $13020
        movem.l d0-d7/a0-a6,-(a7)
        bsr     setup
        movem.l (a7)+,d0-d7/a0-a6
        jmp     $13020.l
