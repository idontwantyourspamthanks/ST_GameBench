; asn_blob.s: the code of the asn_* patch group (NOT a patch: no `; site:`; tools/asn_build.py assembles it into the bank file at ORG).
; Sound effects (work/notes/amiga_sound.md): asn_core ($18f92 -> j_tick), asn_wd ($262c2 -> j_wd), asn_lvc ($18ed8), asn_lv1 ($18e72), asn_lv2 ($18ea0).
; Music (work/notes/amiga_music_port.md): asn_mus (the YM driver's vector table $806/$80a -> j_mtick/j_mstart).
; One mixer and one DMA ring serve both; the game's VBL tick pointer ($5138) is either the sound-effect tick or the music tick, never both.
BANK    equ     $bb000
B_SIL   equ     BANK+$40                ; zeros (192 B): the second part of the one-shot instruments, and what a finished voice reads
B_ROWS  equ     BANK+$100
B_SEQ   equ     BANK+$300
B_REC   equ     BANK+$700
SV      equ     BANK+$e00
MS      equ     BANK+$f00               ; 4 music channel records
RING    equ     BANK+$1000
B_VT    equ     BANK+$1800              ; 3 gain sets x 16 levels x 256 B
ORG     equ     BANK+$4800
B_MUS   equ     BANK+$6000              ; music section (tools/asn_music.py build_music): tune table, flags, fixed streams, score, samples
M_FLAGS equ     B_MUS+$120              ; per tune: rate.b (0 = 6258 Hz, 1 = 12517 Hz), gain set.b
M_IDLEL equ     B_MUS+$144              ; a null list: the first NEXT loads the tune's list
M_IDLE  equ     B_MUS+$148              ; idle stream $2c $18 $1c $08
M_SILENV equ    B_MUS+$150              ; the silence envelope of a REST
M_FIXENV equ    B_MUS+$166              ; terminator of the envelope (0, 32, $ff) of a channel that never ran ENV (the Amiga reads low memory there)
RL      equ     2048
PMAX    equ     2000
v_mode  equ     0                       ; 0 not probed, 1 YM (original code), 2 DMA
v_act   equ     1                       ; session: 0 none, 1 sound effects (3D view), 2 music
v_dma   equ     2
v_silent equ    3
v_wr    equ     4
v_n8    equ     6
v_run1  equ     8
v_run2  equ     10
v_hb    equ     12                      ; heartbeat for asn_wd
v_mw    equ     13                      ; Microwire set up
v_acc   equ     14                      ; 60 Hz tick accumulator
v_k     equ     16                      ; audible voices
v_mus   equ     $12                     ; the DMA tune being played (1..17); 0 = the YM driver owns the music
v_lock  equ     $13                     ; a start is in progress: the tick does nothing
v_rate  equ     $14                     ; $ff8921 = $80 | rate
v_mend  equ     $15                     ; a channel's list wrapped (end of the tune for the once flag)
v_gfix  equ     $16                     ; music: volume table offset of the tune's gain set; -1 = by the number of voices (sound effects)
v_grpb  equ     $18                     ; group bytes (8)
v_act0  equ     $20                     ; 4 x (voice ptr.l, volume table ptr.l)
v_vox   equ     $40                     ; 4 voices x $20
v_target equ    $c0                     ; samples kept ahead of the DMA position
v_thr   equ     $c2                     ; a lead above this = underrun
v_maxg  equ     $c4                     ; groups of 8 per call at most
v_sh    equ     $c6                     ; increment = (v_k4 / period) << v_sh
v_k4    equ     $c8
v_pmin  equ     $cc
v_nom   equ     $ce                     ; outputs per VBL (silent voices keep running while the DMA is off)
v_tick  equ     $d0                     ; music ticks since the start (diagnostic)
VS      equ     $20
V_VOL   equ     0                       ; 8.8 volume the mixer uses
V_VSL   equ     2
V_PER   equ     4                       ; period (AUDxPER)
V_PSL   equ     6
V_CNT   equ     8
V_REC   equ     $a
V_SEQ   equ     $c
V_GRP   equ     $e
V_SMP   equ     $10                     ; the buffer being played (Paula's latch)
V_LEN   equ     $14                     ; its length in words
V_IDX   equ     $16
V_FRAC  equ     $18
V_INCF  equ     $1a
V_INCI  equ     $1c
V_LV    equ     $1e
; music view of a voice (the sound-effect fields +2 .. +$f are free then):
V_AVOL  equ     2                       ; AUDxVOL as the Amiga driver wrote it
V_DMA   equ     6                       ; DMACON bit
V_NSMP  equ     8                       ; AUDxLC  (taken at a DMA start and at each end of the buffer)
V_NLEN  equ     $c                      ; AUDxLEN (words)
V_DEAD  equ     $e                      ; the one-shot is over (it loops silence until the next DMA start)
; music channel record
RS      equ     $40
R_CNT   equ     0
R_STATE equ     2
R_PER   equ     4
R_SLIDE equ     6
R_STEP  equ     8
R_TGT   equ     $a
R_DELAY equ     $c
R_VIB   equ     $e
R_VCNT  equ     $10
R_VREL  equ     $12
R_VUP   equ     $14
R_VDN   equ     $16
R_VDEL  equ     $18
R_VDELR equ     $1a
R_VADD  equ     $1c
R_VADDF equ     $1e
R_WRAPS equ     $1f
R_ENV   equ     $20
R_EV    equ     $24
R_LST   equ     $28
R_LST0  equ     $2c
R_ENV0  equ     $30
R_LC    equ     $34
R_LEN   equ     $38
R_LC2   equ     $3a
R_LEN2  equ     $3e
        org     ORG
; ---- fixed entry points (the sites and the vector table point here): 6 bytes each, `jmp abs.l` spelled out so the assembler cannot shorten it ----
JENT    macro
        dc.w    $4ef9
        dc.l    \1
        endm
        JENT    asn_tick                ; +$00 asn_core
        JENT    asn_wd                  ; +$06 asn_wd
        JENT    asn_lvc                 ; +$0c asn_lvc
        JENT    asn_lv1                 ; +$12 asn_lv1
        JENT    asn_lv2                 ; +$18 asn_lv2
        JENT    asn_mtick               ; +$1e asn_mus: $806 (tick)
        JENT    asn_mstart              ; +$24 asn_mus: $80a (start)
asn_tick:
        lea     SV.l,a4
        tst.b   v_mode(a4)
        bne.s   .m
        bsr     asn_init0
.m:     cmpi.b  #2,v_mode(a4)
        beq.s   asn_run
        move.w  $6862.w,d0              ; the displaced instructions
        bmi.s   .neg
        jmp     $18f98.l
.neg:   jmp     $18fa2.l
asn_init0:                              ; once: a 68000 (not a 68020+) with DMA sound (guarded tst.b $ff8901) and the bank
        move.b  #1,v_mode(a4)
        cmpi.l  #'ASN2',BANK.l
        bne     .rts
        cmpi.l  #BANK,BANK+8.l
        bne     .rts
        movea.l a7,a2                   ; bus error guard: the handler puts a7 back here
        moveq   #1,d0
        suba.l  a0,a0
        dc.w    $43f0,$0200             ; lea (0,a0,d0.w*2),a1: 1 on a 68000, 2 on a 68020+
        cmpa.w  #1,a1
        bne     .rts
        move.w  sr,d6
        ori.w   #$700,sr
        move.l  $8.w,d7
        lea     .berr(pc),a0
        move.l  a0,$8.w
        moveq   #0,d3
        tst.b   $ffff8901.w             ; answers: DMA sound present
        moveq   #1,d3
        bra.s   .done
.berr:  movea.l a2,a7                   ; (entered by a bus error)
.done:  move.l  d7,$8.w
        move.w  d6,sr
        cmpi.b  #1,d3
        bne     .rts
        move.b  #2,v_mode(a4)
.rts:   rts
; ---------------------------------------------------------------------------------------------------------------
asn_run:
        st      v_hb(a4)
        cmpi.b  #1,v_act(a4)
        beq.s   .in
        bsr     asn_enter
.in:    move.w  $19218.l,d5             ; engine level (patched by asn_lvc/1/2 to the Amiga range 2..9)
        bsr     asn_t50
        beq.s   .nt
        bsr     asn_drv
.nt:    bra     asn_mixer
asn_t50:                                ; Z clear = a driver tick is due this VBL (50 Hz: always; 60 Hz: five of six)
        btst    #1,$ffff820a.w          ; shifter sync: bit set = 50 Hz
        bne.s   .y
        move.w  v_acc(a4),d0
        addq.w  #5,d0
        cmpi.w  #6,d0
        blo.s   .n
        subq.w  #6,d0
        move.w  d0,v_acc(a4)
        moveq   #1,d0
        rts
.n:     move.w  d0,v_acc(a4)
        moveq   #0,d0
.y:     rts
; ---- a sound-effect session (3D view) starts: YM silent, Microwire, voices cleared ---------------------------------
asn_enter:
        bsr     asn_ymsilence
        bsr     asn_mwonce
        lea     par_sfx(pc),a0
        bsr     asn_setpar
        moveq   #0,d0
        move.l  d0,v_grpb(a4)
        move.l  d0,v_grpb+4(a4)
        move.w  d0,v_k(a4)
        lea     v_vox(a4),a1
        moveq   #3,d1
.v:     clr.w   V_CNT(a1)
        clr.w   V_VOL(a1)
        move.w  #-1,V_GRP(a1)
        lea     VS(a1),a1
        dbra    d1,.v
        move.b  #1,v_act(a4)
        rts
asn_setpar:                             ; a0 = parameter block: the DMA stops, the ring restarts with these
        clr.b   $ff8901.l
        clr.b   v_dma(a4)
        clr.b   v_silent(a4)
        clr.w   v_wr(a4)
        move.b  (a0)+,v_rate(a4)
        addq.l  #1,a0
        move.w  (a0)+,v_gfix(a4)
        lea     v_target(a4),a1
        moveq   #7,d0
.c:     move.w  (a0)+,(a1)+
        dbra    d0,.c
        rts
;                rate   gfix target thr maxg sh       K        pmin nom
par_sfx: dc.b   0,0
        dc.w    -1,192,768,31,2
        dc.l    9285653                 ; PAL clock * 65536 / 6258.29 / 4
        dc.w    142,125
par_m12: dc.b   1,0
        dc.w    0,640,656,64,2
        dc.l    4642826                 ; PAL clock * 65536 / 12516.58 / 4
        dc.w    113,250
par_m6: dc.b    0,0
        dc.w    0,320,336,32,3
        dc.l    4642826
        dc.w    113,125
asn_ymsilence:                          ; YM silent while the DMA plays: reg 7 := $ff ABSOLUTE (never read back): tone A-C + noise off (bits 0-5), ports A+B output (bits 6-7;
        lea     $ff8800.l,a0            ; the original YM tick writes $f8/$dc/... = the same bits 6+7), amplitudes 8-10 := 0.  Port A (bit 6) must stay an OUTPUT: it carries
        moveq   #0,d1                   ; the floppy drive-select / side lines (reg 14).
        move.b  #7,(a0)
        move.b  #$ff,2(a0)
        move.b  #8,(a0)
        move.b  d1,2(a0)
        move.b  #9,(a0)
        move.b  d1,2(a0)
        move.b  #10,(a0)
        move.b  d1,2(a0)
        rts
asn_mwonce:
        tst.b   v_mw(a4)
        beq.s   .do
        rts
.do:    st      v_mw(a4)
asn_microwire:                          ; master 40 (0 dB), left/right 20 (0 dB), mix DMA with YM, treble/bass 6 (flat)
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
; ---- the Amiga sound-effect driver tick ($2f3b2) -------------------------------------------------------------------
asn_drv:                                ; d5 = level; a4 = SV
        move.w  $6862.w,d0
        bmi.s   .nt
        move.w  #-1,$6862.w
        bsr     asn_start               ; d0 = request word = sound id * 6
.nt:    lea     v_vox(a4),a1            ; all voices idle: re-request the sustained sound
        move.w  V_CNT(a1),d0
        or.w    V_CNT+VS(a1),d0
        or.w    V_CNT+2*VS(a1),d0
        or.w    V_CNT+3*VS(a1),d0
        bne.s   .go
        move.w  $686c.w,d0
        bmi.s   .go
        bsr     asn_start
.go:    lea     v_vox(a4),a1
        moveq   #1,d7
.vl:    bsr     asn_voice
        lea     VS(a1),a1
        addq.w  #1,d7
        cmpi.w  #5,d7
        bne.s   .vl
        rts
asn_start:                              ; d0.w = ST request word (id * 6): Amiga $2f28c / $2f2f2
        andi.l  #$ffff,d0
        divu.w  #6,d0                   ; d0.w = sound id
        cmpi.w  #41,d0
        bhs     .rts
        lsl.w   #3,d0
        lea     B_ROWS.l,a0
        adda.w  d0,a0                   ; a0 = row (4 words)
        move.l  a0,a3
        lea     v_vox(a4),a1
        moveq   #3,d3
.k:     tst.w   (a3)+                   ; word >= 0: this channel takes part, its old group is killed
        bmi.s   .kn
        bsr     asn_kill
.kn:    lea     VS(a1),a1
        dbra    d3,.k
        lea     v_grpb+1(a4),a2         ; first free group byte
        moveq   #1,d2
.g:     tst.b   (a2)
        beq.s   .gf
        addq.w  #1,d2
        addq.l  #1,a2
        bra.s   .g
.gf:    lea     v_vox(a4),a1
        moveq   #1,d6
.s:     move.w  (a0)+,d0
        bmi.s   .sn
        bset    d6,(a2)
        move.w  #1,V_CNT(a1)
        move.w  d0,V_SEQ(a1)
        move.w  d2,V_GRP(a1)
.sn:    lea     VS(a1),a1
        addq.w  #1,d6
        cmpi.w  #5,d6
        bne.s   .s
.rts:   rts
asn_kill:                               ; a1 = voice: the whole group of the sound that owns it stops ($2f2f2)
        move.w  V_GRP(a1),d2
        bmi.s   .r
        lea     v_grpb(a4),a2
        moveq   #0,d4
        move.b  (a2,d2.w),d4
        clr.b   (a2,d2.w)
        lea     v_vox(a4),a2
        moveq   #1,d6
.l:     btst    d6,d4
        beq.s   .n
        clr.w   V_CNT(a2)
        clr.w   V_VOL(a2)
        move.w  #-1,V_GRP(a2)
.n:     lea     VS(a2),a2
        addq.w  #1,d6
        cmpi.w  #5,d6
        bne.s   .l
.r:     rts
asn_voice:                              ; a1 = voice, d7 = channel + 1, d5 = level ($2f46c)
        lea     B_REC.l,a5
        adda.w  V_REC(a1),a5
        subq.w  #1,V_CNT(a1)
        beq     asn_step
        bmi.s   .idle
        move.w  V_VOL(a1),d0
        move.w  V_VSL(a1),d1
        add.w   d1,d0
        add.w   4(a5),d1
        move.w  8(a5),d2
        cmp.w   d2,d0
        bmi.s   .vmin
        move.w  d2,d0
        bra.s   .vst
.vmin:  move.w  6(a5),d2
        cmp.w   d2,d0
        bpl.s   .vst
        move.w  d2,d0
.vst:   move.w  d0,V_VOL(a1)
        move.w  d1,V_VSL(a1)
        tst.w   $a(a5)
        bpl.s   .pfix
        move.w  $e(a5),d1               ; engine: period = base + scale * level
        muls.w  d5,d1
        move.w  $c(a5),d0
        add.w   d1,d0
        bra.s   .pcl
.pfix:  move.w  V_PER(a1),d0
        move.w  V_PSL(a1),d1
        add.w   d1,d0
        add.w   $e(a5),d1
.pcl:   move.w  $12(a5),d2
        cmp.w   d2,d0
        bmi.s   .pmin
        move.w  d2,d0
        bra.s   .pst
.pmin:  move.w  $10(a5),d2
        cmp.w   d2,d0
        bpl.s   .pst
        move.w  d2,d0
.pst:   move.w  d0,V_PER(a1)
        move.w  d1,V_PSL(a1)
        rts
.idle:  addq.w  #1,V_CNT(a1)
        rts
asn_step:                               ; the step is over: next effect record ($2f4fa)
        lea     B_SEQ.l,a2
        move.w  V_SEQ(a1),d1
        addq.w  #2,V_SEQ(a1)
        move.w  (a2,d1.w),d0
        move.w  d0,V_REC(a1)
        beq.s   asn_stop
        bpl.s   .rec
        add.w   d0,d1                   ; negative: relative jump back
        move.w  d1,V_SEQ(a1)
        addq.w  #2,V_SEQ(a1)
        move.w  (a2,d1.w),d0
        move.w  d0,V_REC(a1)
.rec:   lea     B_REC.l,a5
        adda.w  d0,a5
        move.l  $16(a5),V_SMP(a1)
        move.w  $1a(a5),V_LEN(a1)
        move.w  (a5),V_VOL(a1)
        move.w  2(a5),V_VSL(a1)
        clr.w   V_IDX(a1)
        clr.w   V_FRAC(a1)
        move.w  $a(a5),d0
        bpl.s   .p
        move.w  $e(a5),d0
        muls.w  d5,d0
        add.w   $c(a5),d0
.p:     move.w  d0,V_PER(a1)
        move.w  $c(a5),V_PSL(a1)
        move.w  $14(a5),d0
        bne.s   .c
        moveq   #7,d0
.c:     move.w  d0,V_CNT(a1)
        rts
asn_stop:                               ; $2f5b0
        clr.w   V_VOL(a1)
        move.w  V_GRP(a1),d0
        bmi.s   .ng
        lea     v_grpb(a4),a2
        bclr    d7,(a2,d0.w)
.ng:    move.w  #-1,V_GRP(a1)
        rts
; ---- the music: the YM driver's vector table $806 (tick) / $80a (start) lands here ---------------------------------------
asn_mtick:                              ; every VBL while the game's tick pointer is the music tick (all registers are the caller's to lose)
        lea     SV.l,a4
        tst.b   v_mode(a4)
        bne.s   .m
        bsr     asn_init0
.m:     tst.b   v_lock(a4)
        bne.s   .ret
        tst.b   v_mus(a4)               ; a DMA tune (only ever set on an STE / Mega STE with the bank)
        bne.s   mus_run
        jmp     $d0e.l                  ; the YM driver's tick, untouched
.ret:   rts
mus_run:
        st      v_hb(a4)
        cmpi.b  #2,v_act(a4)
        beq.s   .in
        bsr     mus_enter
.in:    bsr     asn_t50
        beq.s   .nt
        bsr     mus_drv
        tst.b   v_mus(a4)               ; a once tune just ended: the YM driver has the tick again
        beq.s   .ret
.nt:    bsr     mus_vols
        bra     asn_mixer
.ret:   rts
asn_mstart:                             ; the game stored the tune number in $b96.l: the YM driver's $c6c
        movem.l d0-d7/a0-a6,-(sp)
        lea     SV.l,a4
        tst.b   v_mode(a4)
        bne.s   .m
        bsr     asn_init0
.m:     cmpi.b  #2,v_mode(a4)
        bne.s   .ym
        st      v_lock(a4)
        move.l  $b96.w,d7
        beq.s   .no
        cmpi.l  #17,d7
        bhi.s   .no
        move.w  d7,d0
        lsl.w   #4,d0
        lea     B_MUS.l,a0
        adda.w  d0,a0
        tst.l   (a0)
        beq.s   .no                     ; not in the bank: the YM driver plays it
        move.l  a0,-(sp)
        clr.l   $b96.w                  ; the YM driver is parked on its silent tune 0 (and the chip is silenced)
        jsr     $c6c.w
        move.l  d7,$b96.w
        movea.l (sp)+,a0
        lea     SV.l,a4
        bsr     mus_setup
        clr.b   v_lock(a4)
        movem.l (sp)+,d0-d7/a0-a6
        rts
.no:    bsr     mus_off
        clr.b   v_lock(a4)
.ym:    movem.l (sp)+,d0-d7/a0-a6
        jmp     $c6c.l
mus_off:                                ; the DMA tune (if any) stops at once
        tst.b   v_mus(a4)
        beq.s   .r
        clr.b   v_mus(a4)
        cmpi.b  #2,v_act(a4)
        bne.s   .r
        clr.b   $ff8901.l
        clr.b   v_dma(a4)
        clr.b   v_act(a4)
.r:     rts
mus_setup:                              ; a0 = the tune's 4 list pointers, d7 = tune: the Amiga's $5760c
        cmp.b   v_mus(a4),d7
        beq.s   .same                   ; the same tune again: the ring keeps running
        bsr.s   mus_off                 ; another tune may use another rate / gain: mus_enter sets them up
.same:  move.b  d7,v_mus(a4)
        clr.b   v_mend(a4)
        clr.l   v_tick(a4)
        lea     MS.l,a5
        moveq   #3,d1
.c:     movea.l a5,a1
        moveq   #RS/4-1,d0
.z:     clr.l   (a1)+
        dbra    d0,.z
        move.l  #M_IDLE,R_EV(a5)
        move.l  #M_IDLEL,R_LST(a5)
        move.l  (a0)+,R_LST0(a5)
        move.l  #M_FIXENV,R_ENV0(a5)
        move.l  #M_FIXENV,R_ENV(a5)
        lea     RS(a5),a5
        dbra    d1,.c
mus_hwreset:                            ; $5750a: every channel off
        lea     v_vox(a4),a3
        moveq   #3,d1
.l:     clr.w   V_VOL(a3)
        clr.w   V_AVOL(a3)
        move.w  #1,V_PER(a3)
        clr.w   V_DMA(a3)
        move.l  #B_SIL,V_NSMP(a3)
        move.w  #$10,V_NLEN(a3)
        clr.w   V_DEAD(a3)
        move.l  #B_SIL,V_SMP(a3)
        move.w  #$10,V_LEN(a3)
        clr.l   V_IDX(a3)
        clr.w   V_LV(a3)
        lea     VS(a3),a3
        dbra    d1,.l
        rts
mus_enter:                              ; the music tick takes the DMA over (from nothing or from the sound effects)
        bsr     asn_mwonce
        moveq   #0,d0
        move.b  v_mus(a4),d0
        add.w   d0,d0
        lea     M_FLAGS.l,a1
        adda.w  d0,a1
        lea     par_m12(pc),a0
        tst.b   (a1)
        bne.s   .r1
        lea     par_m6(pc),a0
.r1:    moveq   #0,d2
        move.b  1(a1),d2
        moveq   #12,d1
        lsl.w   d1,d2                   ; gain set * 16 levels * 256
        move.w  d2,-(sp)
        bsr     asn_setpar
        move.w  (sp)+,v_gfix(a4)
        bsr.s   mus_hwreset
        move.b  #2,v_act(a4)
        rts
mus_vols:                               ; the mixer's volume of each channel: AUDxVOL (0..64) x the game's attenuation $b9a (read every VBL)
        moveq   #0,d0
        move.b  $b9a.w,d0
        andi.w  #15,d0
        add.w   d0,d0
        move.w  att_tab(pc,d0.w),d2
        lea     v_vox(a4),a3
        moveq   #3,d1
.l:     moveq   #0,d0
        tst.w   V_DMA(a3)
        beq.s   .s
        tst.w   V_DEAD(a3)
        bne.s   .s
        move.w  V_AVOL(a3),d0
        cmpi.w  #64,d0
        bls.s   .c
        moveq   #64,d0
.c:     mulu.w  d2,d0
.s:     move.w  d0,V_VOL(a3)
        lea     VS(a3),a3
        dbra    d1,.l
        rts
att_tab: dc.w   256,256,256,181,128,91,64,45,32,23,16,11,8,6,4,0       ; $b9a: 2 = normal, one YM volume step (3 dB) each, $f = mute
mus_drv:                                ; one 50 Hz tick of the Amiga driver ($57720)
        addq.l  #1,v_tick(a4)
        lea     MS.l,a5
        lea     v_vox(a4),a3
        moveq   #3,d6
.c:     bsr.s   mus_chan
        lea     RS(a5),a5
        lea     VS(a3),a3
        dbra    d6,.c
        tst.b   v_mend(a4)
        beq.s   .r
        clr.b   v_mend(a4)
        tst.w   $ba2.w                  ; once flag: the tune is over, as the YM driver ends it ($e72): tune 0
        beq.s   .r
        bsr     mus_off
        clr.l   $b96.w
        jsr     $c6c.w
        lea     SV.l,a4
.r:     rts
mus_chan:                               ; a5 = record, a3 = voice ($57a8a)
        move.w  R_CNT(a5),d0
        beq     mus_event
        cmpi.w  #1,d0
        bne.s   .n1
        tst.w   R_STATE(a5)
        beq.s   .nd
        clr.w   V_DMA(a3)               ; end of the note: DMA off, the next note starts the sample again
.nd:    clr.w   R_CNT(a5)
        bra.s   mus_proc
.n1:    cmpi.w  #3,R_STATE(a5)
        bne.s   .n3
        move.l  R_LC2(a5),V_NSMP(a3)    ; the tick after a note start: the second part is queued
        move.w  R_LEN2(a5),V_NLEN(a3)
        move.w  #1,R_STATE(a5)
.n3:    subq.w  #1,R_CNT(a5)
mus_proc:                               ; slide, vibrato, envelope
        moveq   #0,d7
        move.w  R_PER(a5),d2
        move.w  R_SLIDE(a5),d0
        beq.s   .vib
        tst.w   R_DELAY(a5)
        beq.s   .sl
        subq.w  #1,R_DELAY(a5)
        bra.s   .vib
.sl:    addq.w  #1,d7
        move.w  R_TGT(a5),d4
        cmpi.w  #1,d0
        bne.s   .dn
        add.w   R_STEP(a5),d2
        cmp.w   d2,d4
        bhs.s   .vib
        bra.s   .hit
.dn:    sub.w   R_STEP(a5),d2
        cmp.w   d2,d4
        blo.s   .vib
.hit:   move.w  d4,d2
        clr.w   R_SLIDE(a5)
.vib:   move.w  R_VIB(a5),d0
        beq.s   .set
        tst.w   R_VDEL(a5)
        beq.s   .v1
        subq.w  #1,R_VDEL(a5)
        bra.s   .set
.v1:    tst.w   R_VCNT(a5)
        beq.s   .v2
        subq.w  #1,R_VCNT(a5)
        bra.s   .set
.v2:    move.w  R_VREL(a5),R_VCNT(a5)
        addq.w  #1,d7
        cmpi.w  #3,d0
        bhs.s   .up
        sub.w   R_VDN(a5),d2
        addq.w  #1,d0
        bra.s   .vs
.up:    add.w   R_VUP(a5),d2
        addq.w  #1,d0
        cmpi.w  #5,d0
        bne.s   .vs
        moveq   #1,d0
.vs:    move.w  d0,R_VIB(a5)
.set:   tst.w   d7
        beq.s   mus_vol
        move.w  d2,R_PER(a5)
        move.w  d2,V_PER(a3)
mus_vol:                                ; one envelope word per tick; the terminator $00ff holds the word before it
        movea.l R_ENV(a5),a1
        move.w  (a1),d0
        cmpi.w  #$ff,d0
        bne.s   .n
        move.w  -2(a1),d0
        bra.s   .w
.n:     addq.l  #2,a1
        move.l  a1,R_ENV(a5)
        cmpi.b  #1,R_VADDF(a5)
        bne.s   .w
        add.w   R_VADD(a5),d0
.w:     move.w  d0,V_AVOL(a3)
        rts
mus_event:                              ; the event is over: read the stream up to the next note / rest ($57b20..)
        clr.b   R_VADDF(a5)
        movea.l R_EV(a5),a1
ev_next: move.w (a1)+,d0
        cmpi.w  #$64,d0
        bhi.s   ev_note
        lsr.w   #1,d0
        move.w  .jt(pc,d0.w),d0
        jmp     .jt(pc,d0.w)
.jt:    dc.w    ev_halt-.jt,ev_instr-.jt,ev_nextp-.jt,ev_env-.jt,ev_slide-.jt,ev_vib-.jt,ev_slideoff-.jt,ev_viboff-.jt
        dc.w    ev_rest-.jt,ev_end-.jt,ev_end-.jt,ev_next-.jt,ev_next-.jt,ev_voladd-.jt,ev_goto-.jt
ev_note: move.w d0,R_PER(a5)
        move.w  d0,V_PER(a3)
        move.w  (a1)+,d0
        subq.w  #1,d0
        move.w  d0,R_CNT(a5)
        move.l  a1,R_EV(a5)
        move.l  R_ENV0(a5),R_ENV(a5)
        move.w  R_VDELR(a5),R_VDEL(a5)
        tst.w   R_VIB(a5)
        beq.s   .nv
        move.w  #1,R_VIB(a5)
.nv:    tst.w   R_STATE(a5)
        beq.s   .on
        move.w  #3,R_STATE(a5)
        move.l  R_LC(a5),V_NSMP(a3)
        move.w  R_LEN(a5),V_NLEN(a3)
.on:    tst.w   V_DMA(a3)               ; DMACON set: Paula starts the sample only if the channel was off ...
        beq.s   .st
        tst.w   V_DEAD(a3)              ; ... or as soon as the silence loop it is in ends (16 bytes: at once here)
        beq     mus_vol
.st:    move.w  #1,V_DMA(a3)
        move.l  V_NSMP(a3),V_SMP(a3)
        move.w  V_NLEN(a3),V_LEN(a3)
        clr.l   V_IDX(a3)
        clr.w   V_DEAD(a3)
        bra     mus_vol
ev_halt: rts                            ; (the stream is parked: read again next tick)
ev_instr: movea.l (a1)+,a2              ; descriptor: flag.w LC1.l LEN1.w LC2.l LEN2.w
        move.w  (a2)+,d0
        move.w  d0,R_STATE(a5)
        move.l  (a2)+,R_LC(a5)
        move.l  (a2)+,R_LEN(a5)
        move.l  (a2)+,R_LC2+2(a5)
        tst.w   d0
        bne     ev_next
        move.l  R_LC(a5),V_NSMP(a3)     ; flag 0: written to the registers at once
        move.w  R_LEN(a5),V_NLEN(a3)
        bra     ev_next
ev_nextp: movea.l R_LST(a5),a2
        tst.l   (a2)
        bne.s   .ok
        movea.l R_LST0(a5),a2           ; end of the list: back to its start (the first tick comes here from the null list)
        addq.b  #1,R_WRAPS(a5)
        cmpi.b  #2,R_WRAPS(a5)
        blo.s   .ok
        move.b  #1,R_WRAPS(a5)
        st      SV+v_mend.l
.ok:    movea.l (a2)+,a1
        move.l  a2,R_LST(a5)
        bra     ev_next
ev_env: movea.l (a1)+,a2                ; volsub.w voladd.w steps... $00ff
        move.w  2(a2),R_VADD(a5)
        addq.l  #4,a2
        move.l  a2,R_ENV0(a5)
        bra     ev_next
ev_slide: move.l (a1)+,R_SLIDE(a5)      ; mode, step
        move.l  (a1)+,R_TGT(a5)         ; target, delay
        bra     ev_next
ev_vib: move.w  #1,R_VIB(a5)
        move.l  (a1)+,R_VCNT(a5)        ; counter, reload
        move.l  (a1)+,R_VUP(a5)         ; up, down
        move.l  (a1)+,R_VDEL(a5)        ; delay, delay reload
        bra     ev_next
ev_slideoff: clr.w R_SLIDE(a5)
        bra     ev_next
ev_viboff: clr.w R_VIB(a5)
        bra     ev_next
ev_rest: move.w (a1)+,d0
        subq.w  #1,d0
        move.w  d0,R_CNT(a5)
        move.l  a1,R_EV(a5)
        move.l  #M_SILENV,R_ENV(a5)
        clr.w   V_AVOL(a3)
        bra     mus_vol
ev_end: clr.w   V_DMA(a3)               ; channel off; the Amiga writes period 1 to channel 0 here, whatever the channel
        move.w  #1,SV+v_vox+V_PER.l
        clr.w   V_AVOL(a3)
        rts
ev_voladd: move.b #1,R_VADDF(a5)
        bra     ev_next
ev_goto: movea.l (a1),a1
        bra     ev_next
; ---- the mixer -------------------------------------------------------------------------------------------------
asn_inc:                                ; a3 = voice: period -> 16.16 increment.  Trashes d1-d3
        move.w  V_PER(a3),d2
        cmp.w   v_pmin(a4),d2
        bhs.s   .p1
        move.w  v_pmin(a4),d2
.p1:    cmpi.w  #PMAX,d2
        bls.s   .p2
        move.w  #PMAX,d2
.p2:    move.l  v_k4(a4),d3
        divu.w  d2,d3                   ; quotient < 65536 for period >= v_pmin
        andi.l  #$ffff,d3
        move.w  v_sh(a4),d1
        lsl.l   d1,d3                   ; 16.16 increment
        move.w  d3,V_INCF(a3)
        swap    d3
        move.w  d3,V_INCI(a3)
        rts
asn_prep:                               ; audible voices -> v_act0 list; d5 = count.  Trashes d0-d4,a0,a3
        lea     v_vox(a4),a3
        lea     v_act0(a4),a0
        moveq   #0,d5
        moveq   #3,d4
.l:     clr.w   V_LV(a3)
        move.w  V_VOL(a3),d0
        bmi.s   .off
        lsr.w   #8,d0
        cmpi.w  #64,d0
        bls.s   .ok
        moveq   #64,d0
.ok:    addq.w  #2,d0
        lsr.w   #2,d0                   ; level 0..16
        beq.s   .off
        move.w  d0,V_LV(a3)
        bsr.s   asn_inc
        move.l  a3,(a0)+
        addq.l  #4,a0
        addq.w  #1,d5
.off:   lea     VS(a3),a3
        dbra    d4,.l
        move.w  d5,v_k(a4)
        beq.s   .rts
        lea     v_act0(a4),a0           ; volume table of each
        move.w  v_gfix(a4),d3           ; music: the tune's gain set
        bpl.s   .g
        moveq   #0,d3                   ; sound effects: by the number of voices
        cmpi.w  #2,d5
        bls.s   .g
        move.w  #16*256,d3
.g:     move.w  d5,d4
        subq.w  #1,d4
.t:     movea.l (a0),a3
        move.w  V_LV(a3),d0
        subq.w  #1,d0
        lsl.w   #8,d0
        add.w   d3,d0
        lea     B_VT.l,a3
        adda.w  d0,a3
        move.l  a3,4(a0)
        addq.l  #8,a0
        dbra    d4,.t
.rts:   rts
asn_mixer:                              ; a4 = SV
        move.b  #7,$ff8800.l            ; every VBL the asn code owns the tick: PSG reg 7 := $ff (all YM channels off, ports A+B OUTPUT).  The YM tick that
        move.b  #$ff,$ff8802.l          ; wrote reg 7 (always with bits 6+7 set) every VBL does not run; the game's init $33870 zeroes reg 7, and with bit 6 = 0
                                        ; (port A = input) the real YM does not drive the floppy select/side lines (reg 14), so no drive is ever selected
                                        ; (Hatari does not model the direction bit).  Interrupt-safe: the FDC driver's select+RMW of reg 14 runs at sr=$2700.
        bsr     asn_prep
        tst.b   v_dma(a4)
        bne.s   .on
        tst.w   d5
        beq     .idle
        lea     RING.l,a0               ; start: clean ring, fill it ahead, DMA on at the ring start
        moveq   #0,d0
        move.w  #RL/4-1,d1
.z:     move.l  d0,(a0)+
        dbra    d1,.z
        clr.w   v_wr(a4)
        move.w  v_target(a4),d0
        lsr.w   #3,d0
        cmp.w   v_maxg(a4),d0
        bls.s   .f
        move.w  v_maxg(a4),d0
.f:     bsr     asn_mix
        bsr     asn_dmastart
        clr.b   v_silent(a4)
        st      v_dma(a4)
        bra.s   .done
.on:    bsr     asn_dmapos              ; d0 = play position; keep the write cursor v_target samples ahead
        move.w  v_wr(a4),d1
        sub.w   d0,d1
        andi.w  #RL-1,d1
        cmp.w   v_thr(a4),d1
        bls.s   .okp
        addi.w  #16,d0                  ; underrun: resync just ahead of the DMA
        andi.w  #RL-8,d0
        move.w  d0,v_wr(a4)
        moveq   #16,d1
.okp:   clr.w   v_n8(a4)
        move.w  v_target(a4),d0
        sub.w   d1,d0
        ble.s   .sil
        lsr.w   #3,d0
        beq.s   .sil
        cmp.w   v_maxg(a4),d0
        bls.s   .n8
        move.w  v_maxg(a4),d0
.n8:    bsr     asn_mix
.sil:   tst.w   v_k(a4)
        bne.s   .nsil
        addq.b  #1,v_silent(a4)
        cmpi.b  #12,v_silent(a4)        ; ring completely silent for 12 VBL: stop the DMA
        blo.s   .done
        clr.b   $ff8901.l
        clr.b   v_dma(a4)
        bra.s   .done
.nsil:  clr.b   v_silent(a4)
.done:  move.w  v_n8(a4),d0
        lsl.w   #3,d0
        bra.s   .sk
.idle:  move.w  v_nom(a4),d0
.sk:    cmpi.b  #2,v_act(a4)
        bne.s   .ret
        bsr     mus_skip
.ret:   rts
mus_skip:                               ; d0 = outputs just mixed: the music voices that play at volume 0 advance like Paula's
        move.w  d0,d7
        beq     .r
        lea     v_vox(a4),a3
        moveq   #3,d6
.l:     tst.w   V_DMA(a3)
        beq.s   .n
        tst.w   V_DEAD(a3)
        bne.s   .n
        tst.w   V_LV(a3)
        bne.s   .n
        bsr     asn_inc
        move.w  V_INCF(a3),d1
        mulu.w  d7,d1
        moveq   #0,d0
        move.w  V_FRAC(a3),d0
        add.l   d0,d1
        move.w  d1,V_FRAC(a3)
        clr.w   d1
        swap    d1
        move.w  V_INCI(a3),d0
        mulu.w  d7,d0
        add.l   d0,d1
        moveq   #0,d0
        move.w  V_IDX(a3),d0
        add.l   d0,d1                   ; the new index
        moveq   #0,d2
        move.w  V_LEN(a3),d2
        add.l   d2,d2
.w:     cmp.l   d2,d1
        blo.s   .st
        sub.l   d2,d1
        tst.l   d2
        beq.s   .dead
        movea.l V_NSMP(a3),a0           ; end of the buffer: Paula takes the pending LC / LEN
        moveq   #0,d2
        move.w  V_NLEN(a3),d2
        move.l  a0,V_SMP(a3)
        move.w  d2,V_LEN(a3)
        add.l   d2,d2
        cmpa.l  #B_SIL,a0
        bne.s   .w
.dead:  move.w  #-1,V_DEAD(a3)
        moveq   #0,d1
        clr.w   V_FRAC(a3)
.st:    move.w  d1,V_IDX(a3)
.n:     lea     VS(a3),a3
        dbra    d6,.l
.r:     rts
asn_dmapos:                             ; d0.w = DMA read position inside the ring
        lea     $ff8909.l,a0
.rd:    movep.l 0(a0),d0
        movep.l 0(a0),d1
        cmp.l   d0,d1
        bne.s   .rd
        lsr.l   #8,d0
        subi.l  #RING,d0
        andi.w  #RL-1,d0
        rts
asn_dmastart:
        lea     $ff8900.l,a0
        moveq   #0,d0
        move.b  d0,1(a0)
        move.b  #(RING>>16)&$ff,3(a0)
        move.b  #(RING>>8)&$ff,5(a0)
        move.b  #RING&$ff,7(a0)
        move.b  #((RING+RL)>>16)&$ff,$f(a0)
        move.b  #((RING+RL)>>8)&$ff,$11(a0)
        move.b  #(RING+RL)&$ff,$13(a0)
        move.b  v_rate(a4),d0
        ori.b   #$80,d0
        move.b  d0,$21(a0)              ; mono, 6258 Hz (sound effects) or 12517 Hz
        move.b  #3,1(a0)                ; play + repeat
        rts
asn_mix:                                ; d0 = groups of 8 outputs (>=1): the ring from the write cursor; a4 = SV
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
        move.w  v_k(a4),d4
        beq.s   .z
        lea     v_act0(a4),a1
        movea.l (a1)+,a3
        movea.l (a1)+,a2
        bsr     mixs
        lea     SV.l,a4
        move.w  v_k(a4),d4
        subq.w  #1,d4
        beq.s   .adv
        subq.w  #1,d4
.a:     movea.l (a1)+,a3
        movea.l (a1)+,a2
        move.w  d4,-(sp)
        bsr     mixa
        move.w  (sp)+,d4
        dbra    d4,.a
        bra.s   .adv
.z:     bsr     mixz
.adv:   lea     SV.l,a4
        move.w  v_n8(a4),d0
        lsl.w   #3,d0
        add.w   v_wr(a4),d0
        andi.w  #RL-1,d0
        move.w  d0,v_wr(a4)
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
mix_end:                                ; the voice a3 reached the end of its buffer (d0 >= d5) at a group boundary
        sub.w   d5,d0
        cmpi.b  #2,SV+v_act.l
        bne.s   .lp                     ; sound effect: the region loops
        movea.l V_NSMP(a3),a0           ; music: Paula takes the pending LC / LEN
        move.w  V_NLEN(a3),d5
        move.l  a0,V_SMP(a3)
        move.w  d5,V_LEN(a3)
        add.w   d5,d5
        beq.s   .dead
        cmpa.l  #B_SIL,a0
        bne.s   .r
.dead:  move.w  #-1,V_DEAD(a3)          ; the silence loop: nothing to mix until the next DMA start
.zero:  lea     B_SIL.l,a0
        moveq   #0,d0
        moveq   #0,d1
        suba.l  a4,a4
        moveq   #0,d6
        moveq   #-1,d5
.r:     rts
.lp:    tst.w   d5
        beq.s   .zero
        rts
MIXS    macro
        move.b  (a0,d0.w),d4
        move.b  (a2,d4.w),(a6)+
        add.w   a4,d1
        addx.w  d6,d0
        endm
MIXA    macro
        move.b  (a0,d0.w),d4
        move.b  (a2,d4.w),d4
        add.b   d4,(a6)+
        add.w   a4,d1
        addx.w  d6,d0
        endm
MIXV    macro                           ; a3 = voice, a2 = volume table; the ring segments from v_wr (v_run1 groups, then v_run2 from the start)
\1:     move.l  a1,-(sp)
        movea.l V_SMP(a3),a0
        move.w  V_LEN(a3),d5
        add.w   d5,d5                   ; end of the buffer (bytes); the PAD behind every region covers the group that crosses it
        move.w  V_IDX(a3),d0
        move.w  V_FRAC(a3),d1
        movea.w V_INCF(a3),a4
        move.w  V_INCI(a3),d6
        moveq   #0,d4
        lea     RING.l,a6
        adda.w  SV+v_wr.l,a6
        move.w  SV+v_run1.l,d7
        beq.s   .s1
        subq.w  #1,d7
        bsr.s   .loop
.s1:    move.w  SV+v_run2.l,d7
        beq.s   .s2
        subq.w  #1,d7
        lea     RING.l,a6
        bsr.s   .loop
.s2:    move.w  d0,V_IDX(a3)
        move.w  d1,V_FRAC(a3)
        movea.l (sp)+,a1
        rts
.loop:  cmp.w   d5,d0
        bhs.s   .end
        rept    8
        \2
        endr
        dbra    d7,.loop
        rts
.end:   bsr     mix_end
        bra.s   .loop
        endm
        MIXV    mixs,MIXS
        MIXV    mixa,MIXA
; ---- asn_wd: boot site $262c2 (the watchdog), see patches/asn_wd.s ------------------------------------------------------------------
asn_wd: tst.b   SV+v_hb.l               ; heartbeat set by the tick of the last VBL?
        bne.s   .alive
        clr.b   SV+v_act.l              ; no: no session
        tst.b   SV+v_dma.l              ; DMA running?
        beq.s   .ex
        clr.b   $ff8901.l               ; DMA off
        clr.b   SV+v_dma.l
        bra.s   .ex
.alive: clr.b   SV+v_hb.l
.ex:    jmp     $27228.l                ; the displaced call
; ---- asn_lvc: site $18ed8 (engine level clamp), see patches/asn_lvc.s -----------------------------------------------------------------
asn_lvc: move.w #1,d6
        move.w  #7,d7
        cmpi.b  #2,SV.l
        bne.s   .go
        move.w  #2,d6
        move.w  #9,d7
.go:    jmp     $4f8a.w
; ---- asn_lv1 / asn_lv2: sites $18e72 / $18ea0 (level constant 7 -> 9) --------------------------------------------------------------------
asn_lv1:
asn_lv2: cmpi.b #2,SV.l
        beq.s   .d
        move.w  #7,$19218.l
        rts
.d:     move.w  #9,$19218.l
        rts
