; ---------------------------------------------------------------------------
; Player Manager v1.1 — Atari STE Amiga Audio & Visuals Engine (KO2STE.BIN)
;
; Loaded at $0ae940..$0affff (5.7 KB, cleanly above KO2_FILES_CR $09d000..$0ae940)
; ONLY activated on Atari STE / Mega STE (when BR_IS_STE == 1).
; Plain 68000 ST never calls this and runs 100% classic v1.0 ST mode.
;
; 1 MB STE RAM Layout during live match (after KRD finishes loading!):
;   $081000..$08101f : STE 12-bit Amiga pitch palette (colours 0..7)
;   $081020..$082e1f : 80x96 Amiga pitch tilemap (7,680 bytes, 0-based)
;   $082e20..$088e1f : 256 x (16x16x3bpp) ST-interleaved tiles (24,576 bytes)
;   $088f00..$09afff : STE Corkscrew scrolling buffer (424 x 168 = 71.2 KB)
;   $09b000..$09cfff : Blitter 4bpp sprite save-under slots (32 x 256 = 8 KB)
;
; Entry points (fixed header at $0ae940):
;   +$00 : bra.w ste_install_hooks  (after KO2ENG.BIN loads, before $01fd92)
;   +$04 : bra.w ste_cleanup        (in Supervisor SR=$2700 on KO2 exit)
;   +$08 : STE_SND_SIZE.l           (filled by ko2_bridge.s with AMIGASND.BIN size)
;   +$0c : bra.w ste_load_pitch     (after $013450, loads AMIGAP0..3.BIN -> $081000)
; ---------------------------------------------------------------------------

        org     $0ae940

KO2_A4          equ     $0284aa
BR_TOS_84       equ     $0b5814         ; saved original TOS TRAP #1 vector
STE_SND_STG     equ     $0c8b00         ; AMIGASND.BIN staging in KO2_REPLAY_BUF

STE_PIT_PAL     equ     $081000         ; 32 bytes (8 STE 12-bit pitch colours)
STE_PIT_MAP     equ     $081020         ; 7,680 bytes (80 x 96 tilemap)
STE_PIT_TILES   equ     $082e20         ; 24,576 bytes (256 x 96 bytes)
STE_CORK_BUF    equ     $088f00         ; 73,984 bytes (424 x 168 + 480 slack)
STE_SAVE_UNDER  equ     $09b000         ; 8,192 bytes (32 x 256 byte save-under slots)
; STE Blitter HUD/Radar save-under & 1bpp mask buffers (100% inside 1 MB RAM!):
STE_HUD_MASK    equ     $07fd00         ; 320 bytes (1bpp HUD/Banner mask & 32B sprite mask)
STE_MASK_BUF    equ     $07fd00         ; 32 bytes (16-line 1bpp sprite mask scratch)
STE_RADAR_SAVE  equ     $07fe40         ; 4,544 bytes (454 x 10B transparent vector radar save-under!)
STE_RADAR_MAX   equ     450             ; max 10-byte saved cells for transparent radar
STE_BHUD_SAVE   equ     $0b2400         ; 1,128 bytes (tight 3-box Bottom HUD) -> $0b2868
STE_DRAW_STACK  equ     $0b2880         ; 512 bytes (32 x 16B overlap-safe LIFO sprite stack!) -> $0b2a80
STE_BAN_SAVE    equ     $0b2a80         ; 1,344 bytes (8 lines x 21 cols x 8B) -> $0b2fc0 (< PMOK $0b2ff8!)

CORK_STRIDE     equ     168             ; 336 pixels = 21 x 16px words (4 planes)
CORK_RING_H     equ     224             ; 14 tile rows = 224 scanlines
CORK_RING_BYTES equ     37632           ; 224 * 168

; STE Blitter registers
BLT_SRC_XINC    equ     $00ff8a20
BLT_SRC_YINC    equ     $00ff8a22
BLT_SRC_ADDR    equ     $00ff8a24
BLT_ENDMASK1    equ     $00ff8a28
BLT_ENDMASK2    equ     $00ff8a2a
BLT_ENDMASK3    equ     $00ff8a2c
BLT_DST_XINC    equ     $00ff8a2e
BLT_DST_YINC    equ     $00ff8a30
BLT_DST_ADDR    equ     $00ff8a32
BLT_XCOUNT      equ     $00ff8a36
BLT_YCOUNT      equ     $00ff8a38
BLT_HOP         equ     $00ff8a3a
BLT_OP          equ     $00ff8a3b
BLT_LINE        equ     $00ff8a3c
BLT_SKEW        equ     $00ff8a3d

; Jump table & header at $0ae940
ste_entry:
        bra.w   ste_install_hooks       ; +$00
        bra.w   ste_cleanup             ; +$04
STE_SND_SIZE:   dc.l    0               ; +$08 (set by ko2_bridge.s)
        bra.w   ste_load_pitch          ; +$0c

; ---------------------------------------------------------------------------
; Audio State variables
; ---------------------------------------------------------------------------
STE_SND_BASE:   dc.l    0               ; +$10: base of AMIGASND.BIN in KO2 heap
STE_SCRIPT_ST:  dc.l    0               ; start of current sound script
STE_SCRIPT_PTR: dc.l    0               ; current pointer in sound script (0 = idle)
STE_REPEAT_CNT: dc.w    0               ; repeat counter
STE_SND_PEND:   dc.b    0               ; 1 = new sound requested
STE_SND_STOP:   dc.b    0               ; 1 = stop DMA requested
STE_SND_PITCH:  dc.b    0
STE_SND_PAD:    dc.b    0
STE_DMA_CNT:    dc.w    0               ; total STE DMA samples triggered

; ---------------------------------------------------------------------------
; Video / Corkscrew / Blitter State variables
; ---------------------------------------------------------------------------
STE_AMIGA_ON:   dc.w    0               ; 1 = Amiga STE Tiled Pitch ON, 0 = Classic ST
STE_PITCH_OK:   dc.w    0               ; 1 = AMIGAPx.BIN loaded successfully
STE_CUR_TX:     dc.w    -999            ; last top-left tile X in Corkscrew
STE_CUR_TY:     dc.w    -999            ; last top-left tile Y in Corkscrew
STE_VIEW_BASE:  dc.l    STE_CORK_BUF    ; current display address for VBL
STE_VIEW_HSCR:  dc.w    0               ; current STE fine hscroll (0..15)
STE_SLOT_NEXT:  dc.w    0               ; next free save-under slot (0..31)
STE_ST_PAL:     ds.w    8               ; saved Classic ST palette 0..7
STE_ST_PAL_OK:  dc.w    0               ; 1 = saved ST palette captured
STE_HUD_ACTIVE: dc.w    0               ; bit0=bhud saved, bit1=banner saved
STE_HUD_VBASE:  dc.l    0               ; STE_VIEW_BASE where HUD/Radar was drawn
STE_RADAR_CNT:  dc.w    0               ; active transparent radar saved cells (0..450)
STE_DRAW_CNT:   dc.w    0               ; number of sprites on LIFO draw stack (0..32)

; ---------------------------------------------------------------------------
; ste_install_hooks: Patch KO2ENG.BIN at $010000..$024000 for STE hardware
; ---------------------------------------------------------------------------
ste_install_hooks:
        clr.l   STE_SND_BASE
        clr.l   STE_SCRIPT_ST
        clr.l   STE_SCRIPT_PTR
        clr.w   STE_REPEAT_CNT
        clr.b   STE_SND_PEND
        clr.b   STE_SND_STOP
        clr.w   STE_DMA_CNT
        clr.w   STE_AMIGA_ON
        clr.w   STE_PITCH_OK
        clr.w   STE_ST_PAL_OK
        clr.w   STE_HUD_ACTIVE
        clr.w   STE_RADAR_CNT
        clr.w   STE_DRAW_CNT
        clr.w   STE_SLOT_NEXT
        move.w  #-999,STE_CUR_TX
        move.w  #-999,STE_CUR_TY
        move.l  #STE_CORK_BUF,STE_VIEW_BASE
        clr.w   STE_VIEW_HSCR

        ; Install TRAP #8 ($a0.w) fast Supervisor Blitter dispatcher via Supexec
        pea     ste_inst_trap8(pc)
        move.w  #$26,-(sp)
        trap    #14
        addq.l  #6,sp

        ; 1. Audio hooks ($01849e load, $0184fe play low, $018506 play hi, $018598 stop)
        move.w  #$4ef9,$01849e.l
        move.l  #ste_load_samples,$0184a0.l
        move.w  #$4ef9,$0184fe.l
        move.l  #ste_play_sound,$018500.l
        move.w  #$4ef9,$018506.l
        move.l  #ste_play_sound_hi,$018508.l
        move.w  #$4ef9,$018598.l
        move.l  #ste_stop_sound,$01859a.l

        ; 2. VBL top ($018d06 Timer B setup) & bottom ($018e0a $ff8240 write + $018e22 end)
        move.w  #$4ef9,$018d06.l
        move.l  #ste_vbl_top,$018d08.l
        move.w  #$4ef9,$018e0a.l
        move.l  #ste_vbl_end,$018e0c.l

        ; 3. Pitch camera & lines ($01c1d0)
        move.w  #$4ef9,$01c1d0.l
        move.l  #ste_pitch_update,$01c1d2.l

        ; 4. Universal sprite draw core ($01a426: mulu.w #$a0,d1 ; ext.l d0) & erase ($01a83e)
        ;    All 4 KO2 sprite entry points ($01a2fc, $01a346, $01a3bc, $01a412) funnel into $01a426!
        move.w  #$4ef9,$01a426.l
        move.l  #ste_draw_spr_core_hook,$01a428.l
        move.w  #$4ef9,$01a83e.l
        move.l  #ste_erase_spr,$01a840.l
        ; Also bypass KO2's Timer B raster-beam wait at $01a376 & $01a3cc when Amiga mode is ON!
        move.w  #$4ef9,$01a376.l
        move.l  #ste_skip_beam_1,$01a378.l
        move.w  #$4ef9,$01a3cc.l
        move.l  #ste_skip_beam_2,$01a3ce.l

        ; 5. In-match key handler ($01b564: cmpi.w #$72,d0 ; bne.b $1b570) -> 'V' view toggle!
        move.w  #$4ef9,$01b564.l
        move.l  #ste_key_hook,$01b566.l

        rts

ste_inst_trap8:
        move.l  #ste_trap8_handler,$a0.w
        rts

; ---------------------------------------------------------------------------
; ste_cleanup: Called in Supervisor mode (SR=$2700) when exiting KO2 back to PM
; ---------------------------------------------------------------------------
ste_cleanup:
        clr.b   $00ff8901.l             ; stop STE DMA audio
        clr.b   $00ff820f.l             ; reset STE line width (extra words = 0)
        clr.b   $00ff8265.l             ; reset STE fine hscroll = 0
        move.b  #$07,$00ff8201.l        ; restore standard $078000 screen base
        move.b  #$80,$00ff8203.l
        clr.b   $00ff820d.l
        clr.w   STE_AMIGA_ON
        clr.l   STE_SCRIPT_PTR
        clr.b   STE_SND_PEND
        clr.b   STE_SND_STOP
        rts

; ---------------------------------------------------------------------------
; ste_load_pitch (ste_init_pitch): Called after ko2_bridge.s loads AMIGAPx.BIN
; into $081000..$088e1f. Input: d0.l = bytes read (32288 = success).
; ---------------------------------------------------------------------------
ste_load_pitch:
        cmpi.l  #32288,d0
        bne.s   .lp_fail
        move.w  #1,STE_PITCH_OK
        move.w  #1,STE_AMIGA_ON
        clr.w   STE_SLOT_NEXT
        clr.w   STE_DRAW_CNT
        clr.w   STE_RADAR_CNT
        clr.w   STE_HUD_ACTIVE
        move.w  #-999,STE_CUR_TX
        move.w  #-999,STE_CUR_TY
        moveq   #4,d0                   ; cmd 4 = clear_cork via STE Blitter!
        trap    #8
        rts
.lp_fail:
        clr.w   STE_PITCH_OK
        clr.w   STE_AMIGA_ON
        rts

; ---------------------------------------------------------------------------
; Audio: ste_load_samples / ste_play_sound / ste_play_sound_hi / ste_stop_sound
; ---------------------------------------------------------------------------
ste_load_samples:
        movem.l d0/a0,-(sp)
        move.l  STE_SND_SIZE(pc),d0
        ble.s   .ls_none
        move.l  a5,d0
        addq.l  #1,d0
        and.l   #$fffffffe,d0
        movea.l d0,a5
        move.l  a5,-$1452(a4)
        move.l  a5,STE_SND_BASE
        lea     STE_SND_STG.l,a0
        move.l  STE_SND_SIZE(pc),d0
        addq.l  #3,d0
        lsr.l   #2,d0
        subq.w  #1,d0
.cp_s:  move.l  (a0)+,(a5)+
        dbra    d0,.cp_s
        bra.s   .ls_done
.ls_none:
        clr.l   STE_SND_BASE
.ls_done:
        clr.w   -$142a(a4)
        movem.l (sp)+,d0/a0
        rts

ste_play_sound:
        tst.w   -$142a(a4)
        bne.s   ste_ps_rts
ste_play_sound_hi:
        tst.w   -$5eec(a4)
        bne.s   ste_ps_rts
        tst.l   STE_SND_BASE
        beq.s   ste_ps_rts
        move.l  a2,STE_SCRIPT_ST
        move.l  a2,STE_SCRIPT_PTR
        clr.w   STE_REPEAT_CNT
        move.w  #1,-$142a(a4)
        clr.b   STE_SND_STOP
        move.b  #1,STE_SND_PEND
ste_ps_rts:
        rts

ste_stop_sound:
        clr.l   STE_SCRIPT_PTR
        clr.b   STE_SND_PEND
        move.b  #1,STE_SND_STOP
        clr.w   -$142a(a4)
        rts

; ---------------------------------------------------------------------------
; VBL Top ($018d06) & End ($018e0a): STE Shifter, Palette, & DMA Sound Step
; ---------------------------------------------------------------------------
ste_vbl_top:
        movem.l d0-d1,-(sp)
        tst.w   STE_AMIGA_ON
        beq.w   .vt_classic
        tst.w   $02356a.l               ; KO2 -$4f40(a4): Half-Time/Full-Time/Stats on $078000?
        bne.w   .vt_stats

        ; Amiga STE Mode: disable Timer B stripes, program STE Shifter + Palette 0..7!
        clr.b   $00fffa1b.l             ; stop Timer B
        ; Capture Classic ST palette 0..7 once (before we overwrite $ff8240..$ff824e!)
        tst.w   STE_ST_PAL_OK
        bne.s   .vt_pal_ok
        movem.l a0-a1,-(sp)
        lea     $00ff8240.l,a0
        lea     STE_ST_PAL(pc),a1
        move.l  (a0)+,(a1)+
        move.l  (a0)+,(a1)+
        move.l  (a0)+,(a1)+
        move.l  (a0)+,(a1)+
        move.w  #1,STE_ST_PAL_OK
        movem.l (sp)+,a0-a1
.vt_pal_ok:
        ; Load STE 12-bit Amiga pitch palette (0..7)
        movem.l a0-a1,-(sp)
        lea     STE_PIT_PAL.l,a0
        lea     $00ff8240.l,a1
        move.l  (a0)+,(a1)+
        move.l  (a0)+,(a1)+
        move.l  (a0)+,(a1)+
        move.l  (a0)+,(a1)+
        movem.l (sp)+,a0-a1

        ; Program STE Shifter display address ($ff8201 HIGH, $ff8203 MID, $ff820d LOW LAST!)
        ; NOTE: On Atari STE, writing $ff8201 or $ff8203 resets $ff820d to 0, so $ff820d MUST be last!
        move.l  STE_VIEW_BASE(pc),d0
        move.l  d0,d1
        swap    d1
        move.b  d1,$00ff8201.l          ; high byte
        move.w  d0,d1
        lsr.w   #8,d1
        move.b  d1,$00ff8203.l          ; mid byte
        move.b  d0,$00ff820d.l          ; low byte LAST!
        move.w  STE_VIEW_HSCR(pc),d0
        move.b  d0,$00ff8265.l          ; fine pixel hscroll (0..15)
        beq.s   .vt_h0
        clr.b   $00ff820f.l             ; hscroll != 0 -> STE adds 8 bytes automatically (=168)
        jmp     $018d6e.l               ; continue KO2 VBL joystick reader!
.vt_h0:
        move.b  #4,$00ff820f.l          ; hscroll == 0 -> +4 extra words = +8 bytes (=168)
        jmp     $018d6e.l

.vt_stats:
        ; KO2 Half-Time / Full-Time / Match Stats screen on $078000 (keep KO2 palette!)
        clr.b   $00fffa1b.l
        move.b  #$07,$00ff8201.l
        move.b  #$80,$00ff8203.l
        clr.b   $00ff820d.l
        clr.b   $00ff820f.l
        clr.b   $00ff8265.l
        jmp     $018d6e.l

.vt_classic:
        ; Classic ST Mode: ensure STE shifter is standard $078000, stride 160, hscroll 0
        move.b  #$07,$00ff8201.l
        move.b  #$80,$00ff8203.l
        clr.b   $00ff820d.l
        clr.b   $00ff820f.l
        clr.b   $00ff8265.l
        ; Execute original $018d0a..$018d5c Timer B grass stripes!
        move.w  $2739c.l,d0
        jmp     $018d10.l

; Replaces $018e0a..$018e2a: skip $ff8240 write in Amiga mode, then run STE DMA audio step
ste_vbl_end:
        tst.w   STE_AMIGA_ON
        bne.s   .ve_skip_col0
        move.w  $27186.l,$00ff8240.l
        eori.w  #$30,$27186.l
.ve_skip_col0:
        clr.w   $2718a.l
        move.w  #$ffff,$27190.l         ; VBL sync flag!

        ; STE DMA Audio step
        tst.b   STE_SND_STOP
        beq.s   .chk_pend
        clr.b   STE_SND_STOP
        clr.b   $00ff8901.l
        rts
.chk_pend:
        tst.b   STE_SND_PEND
        bne.s   .do_step
        tst.l   STE_SCRIPT_PTR
        beq.w   .vbl_done
        btst    #0,$00ff8901.l
        bne.w   .vbl_done
.do_step:
        clr.b   STE_SND_PEND
        movem.l d0-d3/a0-a1,-(sp)
        movea.l STE_SND_BASE(pc),a1
        move.l  a1,d0
        beq.w   .step_stop
.next_cmd:
        movea.l STE_SCRIPT_PTR(pc),a0
        move.l  a0,d0
        beq.w   .step_stop
        addq.w  #1,STE_REPEAT_CNT
        blt.s   .same_cmd
        addq.l  #2,STE_SCRIPT_PTR
.same_cmd:
        move.w  (a0),d0
        beq.w   .step_stop
        blt.s   .cmd_neg
        cmpi.w  #$c8,d0
        bge.s   .cmd_pitch
        cmpi.w  #$64,d0
        bge.s   .cmd_s100
        subq.w  #1,d0
        bra.s   .play_idx
.cmd_neg:
        cmpi.w  #-1,d0
        beq.s   .cmd_loop
        move.w  d0,STE_REPEAT_CNT
        bra.s   .next_cmd
.cmd_loop:
        move.l  STE_SCRIPT_ST(pc),STE_SCRIPT_PTR
        clr.w   STE_REPEAT_CNT
        bra.s   .next_cmd
.cmd_pitch:
        subi.w  #$c8,d0
        move.b  d0,STE_SND_PITCH
        bra.s   .next_cmd
.cmd_s100:
        subi.w  #$65,d0
.play_idx:
        cmpi.w  #17,d0
        bcc.s   .next_cmd
        mulu.w  #12,d0
        lea     0(a1,d0.w),a0
        move.l  (a0)+,d1
        move.l  (a0)+,d2
        move.w  (a0)+,d3
        cmpi.l  #16,d2
        ble.s   .step_stop              ; empty placeholder sample -> stop script (avoid VBL infinite loop on -1!)
        add.l   a1,d1
        add.l   d1,d2
        clr.b   $00ff8901.l
        move.b  d1,$00ff8907.l
        lsr.l   #8,d1
        move.b  d1,$00ff8905.l
        lsr.l   #8,d1
        move.b  d1,$00ff8903.l
        move.b  d2,$00ff8913.l
        lsr.l   #8,d2
        move.b  d2,$00ff8911.l
        lsr.l   #8,d2
        move.b  d2,$00ff890f.l
        move.b  d3,$00ff8921.l
        move.b  #1,$00ff8901.l
        addq.w  #1,STE_DMA_CNT
        bra.s   .step_ret
.step_stop:
        clr.b   $00ff8901.l
        clr.l   STE_SCRIPT_PTR
        clr.w   $0284aa-$142a
.step_ret:
        movem.l (sp)+,d0-d3/a0-a1
.vbl_done:
        rts

; ---------------------------------------------------------------------------
; ste_key_hook: Replaces $01b564 (in-match key handler) — 'V' toggles view!
; ---------------------------------------------------------------------------
ste_key_hook:
        cmpi.w  #'v',d0
        beq.s   .do_toggle
        cmpi.w  #'V',d0
        bne.s   .not_v
.do_toggle:
        tst.w   STE_PITCH_OK
        beq.s   .v_done
        bsr.w   ste_erase_all_slots     ; LIFO: restore sprites BEFORE HUD/Radar!
        bsr.w   ste_hud_restore         ; restore HUD/Radar to pristine grass!
        eori.w  #1,STE_AMIGA_ON
        tst.w   STE_AMIGA_ON
        beq.s   .to_classic
        ; Switching -> Amiga STE Mode: clear stale Classic ST lines on $078000 & force full redraw!
        move.w  #-999,STE_CUR_TX
        move.w  #-999,STE_CUR_TY
        moveq   #4,d0                   ; cmd 4 = clear_cork + clear $078000!
        trap    #8
        bra.s   .v_done
.to_classic:
        ; Switching -> Classic ST Mode: restore saved ST palette 0..7 via Supexec!
        tst.w   STE_ST_PAL_OK
        beq.s   .v_done
        pea     ste_restore_st_pal(pc)
        move.w  #$26,-(sp)
        trap    #14
        addq.l  #6,sp
.v_done:
        jmp     $01b556.l               ; continue key loop
.not_v:
        cmpi.w  #$72,d0                 ; original $01b564 instruction!
        bne.s   .not_r
        jmp     $01b56a.l
.not_r:
        jmp     $01b570.l

ste_restore_st_pal:
        lea     STE_ST_PAL(pc),a0
        lea     $00ff8240.l,a1
        move.l  (a0)+,(a1)+
        move.l  (a0)+,(a1)+
        move.l  (a0)+,(a1)+
        move.l  (a0)+,(a1)+
        rts

; ---------------------------------------------------------------------------
; ste_pitch_update: Replaces $01c1d0 (pitch lines + camera update)
; ---------------------------------------------------------------------------
ste_pitch_update:
        tst.w   STE_AMIGA_ON
        bne.s   .pu_amiga
        ; Classic ST Mode: run original $01c1d2..$01c40a
        lea     -$5234(a4),a1
        jmp     $01c1d6.l

.pu_amiga:
        ; 1. Exact KO2 smooth camera follow ($01c2b8..$01c2f0)
        movea.l -$110a(a4),a0
        move.l  (a0),d0
        move.l  $4(a0),d1
        subi.l  #$a00000,d0
        subi.l  #$640000,d1
        sub.l   -$1112(a4),d0
        asr.l   #3,d0
        add.l   d0,-$1112(a4)
        sub.l   -$110e(a4),d1
        asr.l   #3,d1
        add.l   d1,-$110e(a4)

        ; 2. Restore HUD & Transparent Radar right before updating STE_VIEW_BASE,
        ;    protecting any 0..2 sprites currently overlapping the Radar/HUD (LIFO!),
        ;    then IMMEDIATELY redraw HUD & Radar at .upd_done (< 0.5ms absent -> ZERO FLICKER!).
        movem.l d0-d7/a0-a3,-(sp)
        bsr.w   ste_hud_lift_spr        ; pop only sprites overlapping Radar/HUD (usually 0!)
        bsr.w   ste_hud_restore
        move.w  -$1112(a4),d0           ; camX (integer part)
        addi.w  #176,d0
        bge.s   .wx_lo
        moveq   #0,d0
.wx_lo: cmpi.w  #960,d0
        ble.s   .wx_ok
        move.w  #960,d0
.wx_ok:
        move.w  -$110e(a4),d1           ; camY (integer part)
        addi.w  #64,d1
        bge.s   .wy_lo
        moveq   #0,d1
.wy_lo: cmpi.w  #1336,d1
        ble.s   .wy_ok
        move.w  #1336,d1
.wy_ok:
        ; d2 = tx = wx >> 4 (0..60), d3 = ty = wy >> 4 (0..83)
        move.w  d0,d2
        lsr.w   #4,d2
        move.w  d1,d3
        lsr.w   #4,d3
        ; Save hscroll = wx & 15
        move.w  d0,d4
        andi.w  #15,d4
        move.w  d4,STE_VIEW_HSCR

        ; Compute STE_VIEW_BASE = STE_CORK_BUF + (wy % 224) * 168 + tx * 8
        moveq   #0,d4
        move.w  d1,d4
        divu.w  #CORK_RING_H,d4
        swap    d4                      ; d4.w = wy % 224 (0..223)
        mulu.w  #CORK_STRIDE,d4         ; d4.l = y_wrap * 168
        move.w  d2,d5
        lsl.w   #3,d5                   ; tx * 8
        ext.l   d5
        add.l   d5,d4
        addi.l  #STE_CORK_BUF,d4
        move.l  d4,STE_VIEW_BASE

        ; Check delta from (STE_CUR_TX, STE_CUR_TY)
        move.w  d2,d4
        sub.w   STE_CUR_TX(pc),d4       ; dtx
        move.w  d3,d5
        sub.w   STE_CUR_TY(pc),d5       ; dty
        move.w  d4,d6
        bpl.s   .adx
        neg.w   d6
.adx:   cmpi.w  #2,d6
        bgt.s   .full_fill
        move.w  d5,d6
        bpl.s   .ady
        neg.w   d6
.ady:   cmpi.w  #2,d6
        bgt.s   .full_fill

        ; Incremental dirty-edge updates (0 tiles on 3 of 4 frames!)
        tst.w   d4
        beq.s   .chk_y
        bgt.s   .scroll_r
        ; Scrolled left: fill column(s) d2 .. STE_CUR_TX-1
        move.w  d2,d6
.sl_lp: bsr.w   ste_draw_col            ; d6=tx_col, d3=ty_top
        addq.w  #1,d6
        cmp.w   STE_CUR_TX(pc),d6
        blt.s   .sl_lp
        bra.s   .chk_y
.scroll_r:
        ; Scrolled right: fill column(s) STE_CUR_TX+21 .. d2+20
        move.w  STE_CUR_TX(pc),d6
        addi.w  #21,d6
        move.w  d2,d7
        addi.w  #20,d7
.sr_lp: bsr.w   ste_draw_col
        addq.w  #1,d6
        cmp.w   d7,d6
        ble.s   .sr_lp

.chk_y:
        tst.w   d5
        beq.s   .upd_done
        bgt.s   .scroll_d
        ; Scrolled up: fill row(s) d3 .. STE_CUR_TY-1
        move.w  d3,d7
.su_lp: bsr.w   ste_draw_row            ; d2=tx_left, d7=ty_row
        addq.w  #1,d7
        cmp.w   STE_CUR_TY(pc),d7
        blt.s   .su_lp
        bra.s   .upd_done
.scroll_d:
        ; Scrolled down: fill row(s) STE_CUR_TY+14 .. d3+13
        move.w  STE_CUR_TY(pc),d7
        addi.w  #14,d7
        move.w  d3,d6
        addi.w  #13,d6
.sd_lp: bsr.w   ste_draw_row
        addq.w  #1,d7
        cmp.w   d6,d7
        ble.s   .sd_lp
        bra.s   .upd_done

.full_fill:
        ; Camera jump / kickoff / toggle: erase all sprites first, then fill 21x14 tiles!
        bsr.w   ste_erase_all_slots
        move.w  d3,d7                   ; ty_row = d3 .. d3+13
        moveq   #13,d5
.ff_y:  bsr.w   ste_draw_row            ; draws d2..d2+20 at row d7
        addq.w  #1,d7
        dbra    d5,.ff_y

.upd_done:
        move.w  d2,STE_CUR_TX
        move.w  d3,STE_CUR_TY
        ; Immediately redraw Transparent Radar & Bottom HUD (< 0.5 ms absent -> ZERO FLICKER!)
        bsr.w   ste_hud_draw
        bsr.w   ste_hud_drop_spr        ; re-draw any 0..2 sprites that were lifted over Radar/HUD
        movem.l (sp)+,d0-d7/a0-a3
        ; Still draw KO2's off-screen goal arrow ($01bffa)!
        jmp     $01bffa.l

; Draw 1 vertical column of 14 tiles: d6 = tx_col, d3 = ty_top
; Batched into ONE TRAP #8 (cmd 9) — 3.8x faster than per-tile TRAPs!
ste_draw_col:
        cmpi.w  #80,d6
        bcc.s   .dc_end
        movem.l d0-d3/a0-a1,-(sp)
        move.w  d6,d1                   ; d1 = tx_col
        move.w  d3,d2                   ; d2 = ty_top
        moveq   #9,d0                   ; cmd 9 = blit_col(d1=tx, d2=ty_top)
        trap    #8
        movem.l (sp)+,d0-d3/a0-a1
.dc_end:
        rts

; Draw 1 horizontal row of 21 tiles: d2 = tx_left, d7 = ty_row
; Batched into ONE TRAP #8 (cmd 8) — 3.8x faster than per-tile TRAPs!
ste_draw_row:
        cmpi.w  #96,d7
        bcc.s   .dr_end
        movem.l d0-d3/a0-a1,-(sp)
        move.w  d2,d1                   ; d1 = tx_left
        move.w  d7,d2                   ; d2 = ty_row
        moveq   #8,d0                   ; cmd 8 = blit_row(d1=tx_left, d2=ty_row)
        trap    #8
        movem.l (sp)+,d0-d3/a0-a1
.dr_end:
        rts

; ---------------------------------------------------------------------------
; Sprite Draw Core ($01a426) & Erase ($01a83e) — STE Blitter 4bpp Masked!
; All 4 KO2 sprite entry points ($01a2fc, $01a346, $01a3bc, $01a412) save
; movem.l d0-d2/d4/d7/a0-a1/a3,-(sp) and enter $01a426 with d0=x, d1=y, a1=src, a3=rec!
; ---------------------------------------------------------------------------
ste_skip_beam_1:
        tst.w   STE_AMIGA_ON
        beq.s   .sb1_st
        jmp     $01a39c.l               ; Amiga STE: skip Timer B wait (keep locked 50 FPS!)
.sb1_st:
        move.l  -$1320(a4),d4
        move.w  d4,d2
        jmp     $01a37c.l

ste_skip_beam_2:
        tst.w   STE_AMIGA_ON
        beq.s   .sb2_st
        jmp     $01a3f2.l               ; Amiga STE: skip Timer B wait (keep locked 50 FPS!)
.sb2_st:
        move.l  -$1320(a4),d4
        move.w  d4,d2
        jmp     $01a3d2.l

ste_draw_spr_core_hook:
        tst.w   STE_AMIGA_ON
        bne.s   .dsc_amiga
        ; Classic ST Mode: run original $01a426 (mulu.w #$a0,d1 ; ext.l d0)
        mulu.w  #$a0,d1
        ext.l   d0
        jmp     $01a42c.l

.dsc_amiga:
        movem.l d3/a2,-(sp)             ; preserve d3 & a2 (caller's entity struct ptr!)
        bsr.s   ste_blit_spr_core
        movem.l (sp)+,d3/a2
        movem.l (sp)+,d0-d2/d4/d7/a0-a1/a3
        rts

; Core Amiga STE 4bpp masked sprite draw: d0=x, d1=y, a1=3bpp src, a3=KO2 save record
ste_blit_spr_core:
        ; 1. Get or allocate persistent 256-byte save-under slot for a3
        cmpi.w  #$5354,8(a3)            ; magic "ST" already assigned?
        beq.s   .have_slot
        move.w  STE_SLOT_NEXT(pc),d2
        cmpi.w  #32,d2
        bcc.w   .spr_ret                ; safety cap (32 slots)
        addq.w  #1,STE_SLOT_NEXT
        ; Slot address = STE_SAVE_UNDER + d2 * 256
        lsl.w   #8,d2
        ext.l   d2
        addi.l  #STE_SAVE_UNDER,d2
        move.l  d2,4(a3)
        move.w  #$5354,8(a3)
.have_slot:
        ; 2. Compute dst inside STE_VIEW_BASE:
        ;    x_in_view = d0 + STE_VIEW_HSCR
        ;    dst = STE_VIEW_BASE + d1 * 168 + (x_in_view >> 4) * 8
        ;    skew = x_in_view & 15
        add.w   STE_VIEW_HSCR(pc),d0
        move.w  d0,d2
        andi.w  #15,d2                  ; d2 = skew (0..15)
        lsr.w   #4,d0
        lsl.w   #3,d0                   ; word_col * 8
        mulu.w  #CORK_STRIDE,d1         ; y * 168
        ext.l   d0
        add.l   d0,d1
        add.l   STE_VIEW_BASE(pc),d1
        movea.l d1,a0                   ; a0 = dst in STE_CORK_BUF
        move.l  a0,(a3)                 ; save dst addr in 0(a3)

        ; 3. Build 16-word 1bpp mask in STE_MASK_BUF (32 bytes, direct from a1!)
        ;    KO2 3bpp sprite layout: row y has p0 at (a1), p1 at $28(a1), p2 at $50(a1), stride $78!
        movea.l a1,a2                   ; save sprite src ptr in a2
        movem.l d4/d6/a0-a1,-(sp)
        lea     STE_MASK_BUF.l,a0
        moveq   #15,d6
.mk_lp:
        move.w  (a1),d4
        or.w    $28(a1),d4
        or.w    $50(a1),d4
        move.w  d4,(a0)+
        lea     $78(a1),a1
        dbra    d6,.mk_lp
        movem.l (sp)+,d4/d6/a0-a1

        ; 4. Combined Save-under + Direct NFSR 4bpp Masked Blitter Draw in ONE TRAP #8!
        ;    Push 16-byte record: +0=a3.l, +4=dst.l, +8=src.l, +12=skew.b, +13=slot.b, +14=x_col.b, +15=y_px.b
        ;    (d0.l currently holds x_col*8, d1.w was multiplied by 168 — recover x_col & y_px cleanly!)
        movea.l 4(a3),a2                ; a2 = save-under slot
        move.w  STE_DRAW_CNT(pc),d3
        cmpi.w  #32,d3
        bcc.s   .no_push
        addq.w  #1,STE_DRAW_CNT
        lsl.w   #4,d3                   ; index * 16
        movem.l d0-d1/a3,-(sp)
        lea     STE_DRAW_STACK.l,a3
        adda.w  d3,a3
        move.l  8(sp),(a3)+             ; +0: KO2 a3 ptr
        move.l  a0,(a3)+                ; +4: dst in STE_CORK_BUF
        move.l  a1,(a3)+                ; +8: src (KO2 3bpp sprite)
        move.b  d2,(a3)+                ; +12: skew (0..15)
        move.l  a2,d3
        subi.l  #STE_SAVE_UNDER,d3
        lsr.w   #8,d3
        move.b  d3,(a3)+                ; +13: slot_idx (0..31)
        lsr.w   #3,d0
        move.b  d0,(a3)+                ; +14: x_col (0..20)
        move.l  a0,d1
        sub.l   STE_VIEW_BASE(pc),d1
        divu.w  #CORK_STRIDE,d1         ; d1.w = y_px (0..199)
        move.b  d1,(a3)                 ; +15: y_px (0..199)
        movem.l (sp)+,d0-d1/a3
.no_push:
        move.w  d2,d1                   ; d1 = skew (0..15)
        moveq   #3,d0                   ; cmd 3 = save_and_draw_sprite
        trap    #8
.spr_ret:
        rts

; Erase sprite ($01a83e)
ste_erase_spr:
        tst.w   STE_AMIGA_ON
        bne.s   ste_erase_spr_amiga
        ; Classic ST Mode: run original $01a83e..
        tst.l   (a3)
        beq.s   .es_st_z
        jmp     $01a844.l
.es_st_z:
        jmp     $01aaaa.l

; Overlap-safe LIFO sprite erase for KO2 record a3:
; - If no sprite drawn AFTER a3 is within +-2688 bytes (16 scanlines): fast 1-blit restore!
; - If any sprite above a3 overlaps it (kickoff walk-out, tackles): LIFO restore from top
;   down to a3, remove a3, and re-draw the sprites that were above a3 -> ZERO GHOSTS!
ste_erase_spr_amiga:
        clr.l   (a3)
        movem.l d0-d7/a0-a2/a4-a5,-(sp)
        move.w  STE_DRAW_CNT(pc),d4
        beq.w   .es_done
        ; Search STE_DRAW_STACK backwards for a3
        move.w  d4,d3
        subq.w  #1,d3                   ; d3 = idx (d4-1 down to 0)
        move.w  d4,d0
        lsl.w   #4,d0
        lea     STE_DRAW_STACK.l,a4
        adda.w  d0,a4                   ; a4 = end of stack
.es_find:
        lea     -16(a4),a4
        cmpa.l  (a4),a3
        beq.s   .es_found
        dbra    d3,.es_find
        bra.w   .es_done                ; not on stack
.es_found:
        ; d3 = idx, a4 = &stack[idx], d4 = old STE_DRAW_CNT
        move.w  d4,d5
        subq.w  #1,d5
        sub.w   d3,d5                   ; d5 = count of sprites ABOVE idx (0 if top!)
        beq.s   .es_fast_one            ; top of stack -> fast 1-blit restore!

        ; Targeted 2D-overlap LIFO: collect ONLY the sprites above idx that actually
        ; 2D-overlap idx (expanding bbox for chains), NEVER touching unrelated players!
        ; Store matching entry pointers in a tiny stack frame (max 8 entries = 32 bytes).
        lea     -32(sp),sp              ; local ptr array at (sp)
        movea.l sp,a1                   ; a1 = match write cursor
        moveq   #0,d0                   ; d0.w = match count (0..8)
        moveq   #0,d1
        move.b  14(a4),d1               ; min_x = target x_col
        move.w  d1,d3                   ; max_x = target x_col (reuse d3!)
        moveq   #0,d2
        move.b  15(a4),d2               ; min_y = target y_px
        move.w  d2,d4                   ; max_y = target y_px (reuse d4!)
        lea     16(a4),a5               ; a5 = &stack[idx+1]
        move.w  d5,d6
        subq.w  #1,d6
.es_ovl:
        moveq   #0,d7
        move.b  14(a5),d7               ; j.x_col
        move.w  d1,d4
        subq.w  #1,d4
        cmp.w   d4,d7                   ; j.x_col < min_x - 1?
        blt.s   .es_nxt
        move.w  d3,d4
        addq.w  #1,d4
        cmp.w   d4,d7                   ; j.x_col > max_x + 1?
        bgt.s   .es_nxt
        moveq   #0,d7
        move.b  15(a5),d7               ; j.y_px
        move.w  d2,d4
        subi.w  #15,d4
        cmp.w   d4,d7                   ; j.y_px < min_y - 15?
        blt.s   .es_nxt
        move.w  d2,d4
        addi.w  #15,d4
        cmp.w   d4,d7                   ; j.y_px > min_y + 15?
        bgt.s   .es_nxt
        ; TRUE 2D overlap! Record pointer a5 (if < 8) and expand x range for chains!
        cmpi.w  #8,d0
        bcc.s   .es_nxt
        move.l  a5,(a1)+
        addq.w  #1,d0
        moveq   #0,d7
        move.b  14(a5),d7
        cmp.w   d1,d7
        bge.s   .es_nx1
        move.w  d7,d1                   ; min_x = j.x_col
.es_nx1: cmp.w  d3,d7
        ble.s   .es_nxt
        move.w  d7,d3                   ; max_x = j.x_col
.es_nxt:
        lea     16(a5),a5
        dbra    d6,.es_ovl

        tst.w   d0
        bne.s   .es_do_targeted
        lea     32(sp),sp               ; free local ptr array -> fast path!

.es_fast_one:
        ; Fast path: no overlapping sprite above idx!
        ; Only restore if dst is still inside current visible viewport [STE_VIEW_BASE .. +185*168]
        move.l  4(a4),a1                ; dst
        move.l  a1,d0
        sub.l   STE_VIEW_BASE(pc),d0
        blt.s   .es_skip_off
        cmpi.l  #(185*CORK_STRIDE),d0
        bgt.s   .es_skip_off
        moveq   #0,d0
        move.b  13(a4),d0               ; slot_idx.b
        lsl.w   #8,d0
        addi.l  #STE_SAVE_UNDER,d0
        movea.l d0,a0                   ; slot
        moveq   #1,d0                   ; cmd 1 = restore_one(a0=slot, a1=dst)
        trap    #8
.es_skip_off:
        bsr.w   .es_compact
        bra.w   .es_done

.es_do_targeted:
        ; Restore ONLY the d0 (1..8) overlapping sprites in reverse LIFO order!
        move.w  d0,d6                   ; save match count in d6
        move.w  d0,d4
        subq.w  #1,d4                   ; loop counter
.es_pop_m:
        move.w  d4,d2
        lsl.w   #2,d2
        movea.l 0(sp,d2.w),a5
        movea.l 4(a5),a1                ; dst
        moveq   #0,d0
        move.b  13(a5),d0
        lsl.w   #8,d0
        addi.l  #STE_SAVE_UNDER,d0
        movea.l d0,a0                   ; slot
        moveq   #1,d0                   ; cmd 1 = restore_one
        trap    #8
        dbra    d4,.es_pop_m

        ; Restore target sprite idx (a4) itself!
        movea.l 4(a4),a1
        moveq   #0,d0
        move.b  13(a4),d0
        lsl.w   #8,d0
        addi.l  #STE_SAVE_UNDER,d0
        movea.l d0,a0
        moveq   #1,d0
        trap    #8

        ; Re-draw ONLY the d6 (1..8) overlapping sprites in forward order!
        ; NOTE: compact shifts all entries above a4 down by 16 bytes, so subtract 16 from each ptr!
        bsr.s   .es_compact
        moveq   #0,d4                   ; i = 0 .. d6-1
.es_redr_m:
        move.w  d4,d2
        lsl.w   #2,d2
        movea.l 0(sp,d2.w),a5
        lea     -16(a5),a5              ; adjusted ptr after .es_compact!
        movea.l 4(a5),a0                ; dst
        movea.l 8(a5),a1                ; src (KO2 3bpp sprite)
        movem.l d4/d6/a0-a1,-(sp)
        lea     STE_MASK_BUF.l,a0
        moveq   #15,d6
.es_mk: move.w  (a1),d4
        or.w    $28(a1),d4
        or.w    $50(a1),d4
        move.w  d4,(a0)+
        lea     $78(a1),a1
        dbra    d6,.es_mk
        movem.l (sp)+,d4/d6/a0-a1
        moveq   #0,d0
        move.b  13(a5),d0
        lsl.w   #8,d0
        addi.l  #STE_SAVE_UNDER,d0
        movea.l d0,a2                   ; slot
        moveq   #0,d1
        move.b  12(a5),d1               ; skew
        moveq   #3,d0
        trap    #8
        addq.w  #1,d4
        cmp.w   d6,d4
        blt.s   .es_redr_m
        lea     32(sp),sp               ; free local ptr array

.es_done:
        movem.l (sp)+,d0-d7/a0-a2/a4-a5
        rts

; Helper: remove entry at a4 (&stack[idx]), shifting d5 entries above it down by 16 bytes
.es_compact:
        subq.w  #1,STE_DRAW_CNT
        move.w  d5,d0
        beq.s   .ec_ret
        movea.l a4,a0                   ; dst = &stack[idx]
        lea     16(a4),a1               ; src = &stack[idx+1]
        subq.w  #1,d0
.ec_lp: move.l  (a1)+,(a0)+
        move.l  (a1)+,(a0)+
        move.l  (a1)+,(a0)+
        move.l  (a1)+,(a0)+
        dbra    d0,.ec_lp
.ec_ret:
        rts

; Erase all active sprites in STRICT REVERSE (LIFO) order via ONE TRAP #8 (cmd 2)!
ste_erase_all_slots:
        movem.l d0-d1/a0,-(sp)
        move.w  STE_DRAW_CNT(pc),d1
        beq.s   .eas_done
        clr.w   STE_DRAW_CNT
        move.w  d1,d0
        lsl.w   #4,d0
        lea     STE_DRAW_STACK.l,a0
        adda.w  d0,a0                   ; a0 = end of stack
        moveq   #2,d0                   ; cmd 2 = restore_lifo_n(a0=end, d1=count)
        trap    #8
.eas_done:
        movem.l (sp)+,d0-d1/a0
        rts

; ---------------------------------------------------------------------------
; HUD & Transparent Vector Radar Overlay (called back-to-back in ste_pitch_update)
; Lifting only the 0..2 sprites overlapping Radar/HUD preserves strict LIFO
; (ZERO Radar ghosts on X/D!) while keeping Radar absent < 0.5 ms (ZERO FLICKER!)
; ---------------------------------------------------------------------------
STE_LIFT_CNT:   dc.w    0
STE_LIFT_PTRS:  ds.l    8               ; up to 8 sprites overlapping Radar/HUD

ste_hud_lift_spr:
        clr.w   STE_LIFT_CNT
        move.w  STE_DRAW_CNT(pc),d0
        beq.s   .hlf_ret
        movem.l d1-d3/a0-a2/a5,-(sp)
        lea     STE_DRAW_STACK.l,a5
        lea     STE_LIFT_PTRS(pc),a2
        moveq   #0,d2                   ; lifted count
        subq.w  #1,d0
.hlf_lp:
        ; Check if sprite overlaps Radar (x_col <= 8 && y_px < 180) OR Bottom HUD (y_px >= 168)
        moveq   #0,d1
        move.b  15(a5),d1               ; y_px
        cmpi.w  #168,d1
        bge.s   .hlf_hit
        cmpi.w  #180,d1
        bge.s   .hlf_nxt
        move.b  14(a5),d1               ; x_col
        cmpi.b  #8,d1
        bhi.s   .hlf_nxt
.hlf_hit:
        cmpi.w  #8,d2
        bcc.s   .hlf_nxt
        move.l  a5,(a2)+
        addq.w  #1,d2
.hlf_nxt:
        lea     16(a5),a5
        dbra    d0,.hlf_lp
        move.w  d2,STE_LIFT_CNT
        beq.s   .hlf_done
        ; Restore lifted sprites in reverse LIFO order!
        subq.w  #1,d2
.hlf_pop:
        movea.l -(a2),a5
        movea.l 4(a5),a1                ; dst
        moveq   #0,d0
        move.b  13(a5),d0
        lsl.w   #8,d0
        addi.l  #STE_SAVE_UNDER,d0
        movea.l d0,a0                   ; slot
        moveq   #1,d0                   ; cmd 1 = restore_one
        trap    #8
        dbra    d2,.hlf_pop
.hlf_done:
        movem.l (sp)+,d1-d3/a0-a2/a5
.hlf_ret:
        rts

ste_hud_drop_spr:
        move.w  STE_LIFT_CNT(pc),d0
        beq.s   .hdr_ret
        clr.w   STE_LIFT_CNT
        movem.l d1-d6/a0-a2/a5,-(sp)
        lea     STE_LIFT_PTRS(pc),a2
        subq.w  #1,d0
.hdr_lp:
        movea.l (a2)+,a5
        movea.l 4(a5),a0                ; dst
        movea.l 8(a5),a1                ; src
        movem.l d0/a0-a2,-(sp)
        lea     STE_MASK_BUF.l,a0
        moveq   #15,d6
.hdr_mk: move.w (a1),d4
        or.w    $28(a1),d4
        or.w    $50(a1),d4
        move.w  d4,(a0)+
        lea     $78(a1),a1
        dbra    d6,.hdr_mk
        movem.l (sp)+,d0/a0-a2
        move.l  a2,-(sp)
        moveq   #0,d1
        move.b  13(a5),d1
        lsl.w   #8,d1
        addi.l  #STE_SAVE_UNDER,d1
        movea.l d1,a2                   ; slot
        moveq   #0,d1
        move.b  12(a5),d1               ; skew
        move.w  d0,-(sp)
        moveq   #3,d0
        trap    #8
        move.w  (sp)+,d0
        movea.l (sp)+,a2
        dbra    d0,.hdr_lp
        movem.l (sp)+,d1-d6/a0-a2/a5
.hdr_ret:
        rts

ste_hud_restore:
        movem.l d0-d3/a0-a2,-(sp)
        ; 1. Reverse-LIFO restore of Transparent Vector Radar cells (10B each: [off.w, l0.l, l1.l])
        move.w  STE_RADAR_CNT(pc),d0
        beq.s   .hr_no_rad
        clr.w   STE_RADAR_CNT
        move.w  d0,d1
        mulu.w  #10,d0
        lea     STE_RADAR_SAVE.l,a0
        adda.l  d0,a0
        movea.l STE_HUD_VBASE(pc),a2
        subq.w  #1,d1
.hr_rlp:
        lea     -10(a0),a0
        moveq   #0,d2
        move.w  (a0),d2                 ; unsigned 16-bit byte offset from STE_HUD_VBASE
        lea     0(a2,d2.l),a1
        move.l  2(a0),(a1)
        move.l  6(a0),4(a1)
        dbra    d1,.hr_rlp
.hr_no_rad:
        move.w  STE_HUD_ACTIVE(pc),d3
        beq.w   .hr_done
        clr.w   STE_HUD_ACTIVE
        ; 2. Restore Bottom HUD tight 3 boxes:
        ;    2a. Player name (y=183..189, 7 lines, x=0..159 -> 11 cols = 44 words)
        lea     STE_BHUD_SAVE.l,a0
        movea.l STE_HUD_VBASE(pc),a1
        adda.l  #183*CORK_STRIDE,a1
        moveq   #44,d1
        moveq   #7,d2
        moveq   #6,d0
        trap    #8
        ;    2b. Score (y=183..189, 7 lines, x=224..287 -> 5 cols = 20 words)
        lea     STE_BHUD_SAVE+640.l,a0
        movea.l STE_HUD_VBASE(pc),a1
        adda.l  #183*CORK_STRIDE+112,a1
        moveq   #20,d1
        moveq   #7,d2
        moveq   #6,d0
        trap    #8
        ;    2c. Match clock (y=190..196, 7 lines, x=144..175 -> 3 cols = 12 words)
        lea     STE_BHUD_SAVE+960.l,a0
        movea.l STE_HUD_VBASE(pc),a1
        adda.l  #190*CORK_STRIDE+72,a1
        moveq   #12,d1
        moveq   #7,d2
        moveq   #6,d0
        trap    #8
        ; 3. Restore Center Banner if it was drawn (bit 1 of d3)
        btst    #1,d3
        beq.s   .hr_done
        lea     STE_BAN_SAVE.l,a0
        movea.l STE_HUD_VBASE(pc),a1
        adda.l  #96*CORK_STRIDE,a1
        moveq   #84,d1
        moveq   #8,d2
        moveq   #6,d0
        trap    #8
.hr_done:
        movem.l (sp)+,d0-d3/a0-a2
        rts

ste_hud_draw:
        tst.w   STE_HUD_ACTIVE
        beq.s   .hd_go
        bsr.w   ste_hud_restore
.hd_go:
        movem.l d0-d5/a0-a2,-(sp)
        move.l  STE_VIEW_BASE(pc),STE_HUD_VBASE
        move.w  STE_VIEW_HSCR(pc),d3    ; d3 = skew (0..15)
        moveq   #1,d5                   ; active flags: bit0=bhud

        ; 1. Transparent, X-Resizable, D-Toggleable Vector Radar (directly from KO2 vars!)
        bsr.w   ste_radar_draw

        ; 2. Bottom HUD tight 3 boxes (2 planes: black + orange, ~12k cycles total!):
        ;    2a. Player Name: y=183..189 (7 lines), x=0..159 (W=10 words, offset +0)
        lea     $078000+183*160,a0
        movea.l STE_HUD_VBASE(pc),a1
        adda.l  #183*CORK_STRIDE,a1
        lea     STE_BHUD_SAVE.l,a2
        moveq   #10,d1
        moveq   #7,d2
        moveq   #0,d4                   ; 2 planes
        moveq   #5,d0
        trap    #8
        ;    2b. Score: y=183..189 (7 lines), x=224..287 (W=4 words, offset +112)
        lea     $078000+183*160+112,a0
        movea.l STE_HUD_VBASE(pc),a1
        adda.l  #183*CORK_STRIDE+112,a1
        lea     STE_BHUD_SAVE+640.l,a2
        moveq   #4,d1
        moveq   #7,d2
        moveq   #0,d4
        moveq   #5,d0
        trap    #8
        ;    2c. Clock: y=190..196 (7 lines), x=144..175 (W=2 words, offset +72)
        lea     $078000+190*160+72,a0
        movea.l STE_HUD_VBASE(pc),a1
        adda.l  #190*CORK_STRIDE+72,a1
        lea     STE_BHUD_SAVE+960.l,a2
        moveq   #2,d1
        moveq   #7,d2
        moveq   #0,d4
        moveq   #5,d0
        trap    #8

        ; 3. Center Event Banner (y=96..103, 8 lines): quick non-zero check on y=99 first!
        lea     $078000+99*160,a0
        moveq   #39,d0                  ; 40 longs = 160 bytes
        moveq   #0,d1
.chk_b: or.l    (a0)+,d1
        dbra    d0,.chk_b
        tst.l   d1
        beq.s   .hd_done
        ori.w   #2,d5                   ; bit1 = banner active
        lea     $078000+96*160,a0
        movea.l STE_HUD_VBASE(pc),a1
        adda.l  #96*CORK_STRIDE,a1
        lea     STE_BAN_SAVE.l,a2
        moveq   #20,d1
        moveq   #8,d2
        moveq   #1,d4                   ; all 4 planes
        moveq   #5,d0
        trap    #8

.hd_done:
        move.w  d5,STE_HUD_ACTIVE
        movem.l (sp)+,d0-d5/a0-a2
        rts

; ---------------------------------------------------------------------------
; ste_radar_draw: 100% Transparent, X-Resizable, D-Toggleable Vector Radar!
; Reads KO2's live radar state:
;   -$0e10(a4) > 0 : Radar ON (D key toggles)
;   -$0e0e(a4)     : rx (top-left X)
;   -$0e0c(a4)     : ry (top-left Y)
;   -$0e0a(a4)     : scale (8, 12, 16, 20, 24 — cycled by X key!)
;   -$4d78(a4)     : KO2's exact pitch outline line table (hlines then vlines)
;   -$5012(a4)     : Home 11 players (stride $186, $20/$22 = radar dot x,y)
;   -$4fbc(a4)     : Away 11 players (stride $186, $20/$22 = radar dot x,y)
;   -$0e14/-$0e12  : Ball radar dot x,y
; Saves every touched 8-byte screen cell as 10B [off.w, l0.l, l1.l] into STE_RADAR_SAVE!
; ---------------------------------------------------------------------------
ste_radar_draw:
        tst.w   -$0e10(a4)              ; Radar ON (> 0)?
        ble.w   .rd_ret
        movem.l d0-d7/a0-a3/a5-a6,-(sp)
        lea     STE_RADAR_SAVE.l,a2     ; a2 = save-under cursor
        moveq   #0,d7                   ; d7 = saved cell count (max STE_RADAR_MAX)
        movea.l STE_HUD_VBASE(pc),a6    ; a6 = STE_VIEW_BASE
        move.w  -$0e0a(a4),d6           ; d6 = radar scale (8, 12, 16, 20, 24)
        ble.w   .rd_done

        ; --- A. Horizontal pitch outline lines from -$4d78(a4) ---
        lea     -$4d78(a4),a3
.rd_hlp:
        move.w  (a3)+,d0                ; x1
        blt.s   .rd_vstart
        move.w  (a3)+,d1                ; y
        move.w  (a3)+,d2                ; x2
        ext.l   d0
        divs.w  d6,d0
        add.w   -$0e0e(a4),d0           ; sx1
        ext.l   d1
        divs.w  d6,d1
        add.w   -$0e0c(a4),d1           ; sy
        ext.l   d2
        divs.w  d6,d2
        add.w   -$0e0e(a4),d2           ; sx2
        bsr.s   .rd_hline
        bra.s   .rd_hlp

        ; --- B. Vertical pitch outline lines ---
.rd_vstart:
        move.w  (a3)+,d0                ; x
        blt.s   .rd_dots
        move.w  (a3)+,d1                ; y1
        move.w  (a3)+,d2                ; y2
        ext.l   d0
        divs.w  d6,d0
        add.w   -$0e0e(a4),d0           ; sx
        ext.l   d1
        divs.w  d6,d1
        add.w   -$0e0c(a4),d1           ; sy1
        ext.l   d2
        divs.w  d6,d2
        add.w   -$0e0c(a4),d2           ; sy2
        bsr.w   .rd_vline
        bra.s   .rd_vstart

        ; --- C. 22 Player dots (Home=colour 10 orange, Away=colour 12 red) + Ball (colour 8 white) ---
.rd_dots:
        movea.l -$5012(a4),a5           ; Home 11 players
        moveq   #10,d5                  ; 11 - 1
        moveq   #2,d4                   ; colour 10 (p1=1, p3=1 -> $730 orange)
        bsr.w   .rd_team
        movea.l -$4fbc(a4),a5           ; Away 11 players
        moveq   #10,d5
        moveq   #4,d4                   ; colour 12 (p2=1, p3=1 -> $500 red)
        bsr.w   .rd_team
        ; Ball dot
        move.w  -$0e14(a4),d0
        blt.s   .rd_done
        move.w  -$0e12(a4),d1
        moveq   #0,d4                   ; colour 8 (p0=p1=p2=0, p3=1 -> $777 white!)
        bsr.w   .rd_dot

.rd_done:
        move.w  d7,STE_RADAR_CNT
        movem.l (sp)+,d0-d7/a0-a3/a5-a6
.rd_ret:
        rts

; Draw transparent black horizontal line (colour 9 = $000): d0=sx1, d1=sy, d2=sx2
.rd_hline:
        cmpi.w  #200,d1
        bcc.s   .hl_ret
        add.w   STE_VIEW_HSCR(pc),d0
        add.w   STE_VIEW_HSCR(pc),d2
        movea.w d0,a1                   ; save sx1 in a1 for exact left-edge clip!
        mulu.w  #CORK_STRIDE,d1         ; row_off = sy * 168
        move.w  d0,d3
        lsr.w   #4,d3                   ; w1 = sx1 >> 4
        move.w  d2,d4
        lsr.w   #4,d4                   ; w2 = sx2 >> 4
.hl_wlp:
        cmpi.w  #STE_RADAR_MAX,d7
        bcc.s   .hl_ret
        moveq   #-1,d5                  ; d5.w = $ffff
        ; Left-edge clip if col_x0 < sx1
        move.w  d3,d0
        lsl.w   #4,d0                   ; col_x0 = d3 * 16
        move.w  a1,d0
        sub.w   d0,d0                   ; dummy -> compute sx1 - col_x0 cleanly:
        move.w  d3,d0
        lsl.w   #4,d0
        neg.w   d0
        add.w   a1,d0                   ; d0 = sx1 - col_x0 (1..15 on first word, <=0 otherwise)
        ble.s   .hl_l_ok
        lsr.w   d0,d5                   ; clear left bits!
.hl_l_ok:
        ; Right-edge clip if col_x1 > sx2
        move.w  d3,d0
        lsl.w   #4,d0
        addi.w  #15,d0                  ; col_x1 = d3*16 + 15
        sub.w   d2,d0                   ; trailing zeros = col_x1 - sx2
        ble.s   .hl_r_ok
        moveq   #-1,d0
        ; shift right mask: (-1 << trailing)
        move.w  d3,d0
        lsl.w   #4,d0
        addi.w  #15,d0
        sub.w   d2,d0
        move.w  d5,-(sp)
        moveq   #-1,d5
        lsl.w   d0,d5
        and.w   (sp)+,d5                ; combine left & right clip masks!
.hl_r_ok:
        ; Byte offset = row_off + d3 * 8
        moveq   #0,d0
        move.w  d3,d0
        lsl.w   #3,d0
        add.w   d1,d0                   ; d0.l = unsigned byte offset in STE_VIEW_BASE
        lea     0(a6,d0.l),a0
        ; Save 10B record [off.w, l0.l, l1.l]
        move.w  d0,(a2)+
        move.l  (a0),(a2)+
        move.l  4(a0),(a2)+
        addq.w  #1,d7
        ; Plot colour 9 (black $000): p0|=m, p1&=~m, p2&=~m, p3|=m
        or.w    d5,(a0)
        or.w    d5,6(a0)
        not.w   d5
        and.w   d5,2(a0)
        and.w   d5,4(a0)
        addq.w  #1,d3
        cmp.w   d4,d3
        ble.s   .hl_wlp
.hl_ret:
        rts

; Draw transparent black vertical line (colour 9 = $000): d0=sx, d1=sy1, d2=sy2
.rd_vline:
        cmpi.w  #320,d0
        bcc.s   .vl_ret
        cmpi.w  #200,d1
        bcc.s   .vl_ret
        cmpi.w  #200,d2
        bcs.s   .vl_yok
        move.w  #199,d2
.vl_yok:
        add.w   STE_VIEW_HSCR(pc),d0
        move.w  d0,d3
        andi.w  #15,d3                  ; bit = 15 - (sx & 15)
        moveq   #15,d4
        sub.w   d3,d4
        moveq   #0,d5
        bset    d4,d5                   ; d5.w = single-pixel mask
        move.w  d5,d4
        not.w   d4                      ; d4.w = ~mask
        lsr.w   #4,d0
        lsl.w   #3,d0                   ; col_off = (sx >> 4) * 8
        sub.w   d1,d2                   ; count = sy2 - sy1
        blt.s   .vl_ret
        mulu.w  #CORK_STRIDE,d1
        add.w   d0,d1                   ; d1.w = initial byte offset (0..33600)
        ; At scale==8 (giant 176-line radar), step by 2 scanlines so save buffer never overflows!
        moveq   #1,d3                   ; step = 1 line
        move.w  #CORK_STRIDE,d0         ; byte step = 168
        cmpi.w  #10,d6
        bgt.s   .vl_lp
        lsr.w   #1,d2                   ; half iterations
        move.w  #(CORK_STRIDE*2),d0     ; step 2 scanlines (dotted crisp line!)
.vl_lp:
        cmpi.w  #STE_RADAR_MAX,d7
        bcc.s   .vl_ret
        moveq   #0,d3
        move.w  d1,d3
        lea     0(a6,d3.l),a0
        move.w  d1,(a2)+
        move.l  (a0),(a2)+
        move.l  4(a0),(a2)+
        addq.w  #1,d7
        or.w    d5,(a0)
        or.w    d5,6(a0)
        and.w   d4,2(a0)
        and.w   d4,4(a0)
        add.w   d0,d1
        dbra    d2,.vl_lp
.vl_ret:
        rts

; Draw 11 player dots for team at a5 (stride $186), d5=10, d4=colour (2=orange, 4=red)
.rd_team:
        tst.w   $0c(a5)
        beq.s   .rt_nxt
        move.w  $20(a5),d0
        blt.s   .rt_nxt
        move.w  $22(a5),d1
        bsr.s   .rd_dot
.rt_nxt:
        lea     $186(a5),a5
        dbra    d5,.rd_team
        rts

; Plot transparent 2x2 dot at (d0=x, d1=y), d4=colour (0->8 white, 2->10 orange, 4->12 red)
.rd_dot:
        cmpi.w  #318,d0
        bcc.s   .dot_ret
        cmpi.w  #198,d1
        bcc.s   .dot_ret
        add.w   STE_VIEW_HSCR(pc),d0
        move.w  d0,d2
        andi.w  #15,d2
        move.w  #$c000,d3               ; 2-pixel wide dot mask
        lsr.w   d2,d3                   ; shifted into word (if d2==15, 1px wide, still crisp!)
        lsr.w   #4,d0
        lsl.w   #3,d0
        mulu.w  #CORK_STRIDE,d1
        add.w   d0,d1                   ; d1.w = byte offset for top row of 2x2 dot
        moveq   #1,d2                   ; 2 scanlines
.dot_lp:
        cmpi.w  #STE_RADAR_MAX,d7
        bcc.s   .dot_ret
        moveq   #0,d0
        move.w  d1,d0
        lea     0(a6,d0.l),a0
        move.w  d1,(a2)+
        move.l  (a0),(a2)+
        move.l  4(a0),(a2)+
        addq.w  #1,d7
        move.w  d3,d0
        not.w   d0                      ; ~mask
        and.w   d0,(a0)                 ; clear p0
        and.w   d0,2(a0)                ; clear p1
        and.w   d0,4(a0)                ; clear p2
        or.w    d3,6(a0)                ; set p3 (palette 8..15!)
        tst.w   d4
        beq.s   .dot_c_ok               ; d4==0 -> colour 8 (white ball!)
        cmpi.w  #2,d4
        bne.s   .dot_c4
        or.w    d3,2(a0)                ; d4==2 -> colour 10 ($730 orange!)
        bra.s   .dot_c_ok
.dot_c4:
        or.w    d3,4(a0)                ; d4==4 -> colour 12 ($500 red!)
.dot_c_ok:
        addi.w  #CORK_STRIDE,d1
        dbra    d2,.dot_lp
.dot_ret:
        rts

; ---------------------------------------------------------------------------
; TRAP #8 ($a0.w) — Fast Supervisor STE Blitter Dispatcher!
; d0.w = cmd:
;   0 : blit_tile(a0=3bpp src 96B, a1=dst in STE_CORK_BUF)
;   1 : save_under(a0=dst in STE_CORK_BUF, a1=256B slot)
;   2 : restore_under(a0=256B slot, a1=dst in STE_CORK_BUF)
;   3 : draw_sprite(a0=dst in STE_CORK_BUF, d1.w=skew 0..15)
;   4 : clear_cork (zeroes STE_CORK_BUF 73,984 bytes with Blitter)
; ---------------------------------------------------------------------------
ste_trap8_handler:
        cmpi.w  #1,d0
        beq.s   .cmd1_rest_one
        cmpi.w  #2,d0
        beq.w   .cmd2_rest_lifo
        cmpi.w  #3,d0
        beq.w   .cmd3_spr
        cmpi.w  #4,d0
        beq.w   .cmd4_clr
        cmpi.w  #5,d0
        beq.w   .cmd5_hud_draw
        cmpi.w  #6,d0
        beq.w   .cmd6_hud_rest
        cmpi.w  #7,d0
        beq.w   .cmd7_radar_opaque
        cmpi.w  #8,d0
        beq.w   .cmd8_blit_row
        bra.w   .cmd9_blit_col

; --- cmd 1: Single sprite restore (a0=slot, a1=dst) ---
.cmd1_rest_one:
        move.l  a0,BLT_SRC_ADDR.l
        move.l  a1,BLT_DST_ADDR.l
        move.w  #2,BLT_SRC_XINC.l
        move.w  #2,BLT_SRC_YINC.l
        move.w  #2,BLT_DST_XINC.l
        move.w  #(CORK_STRIDE-14),BLT_DST_YINC.l
        move.w  #$ffff,BLT_ENDMASK1.l
        move.w  #$ffff,BLT_ENDMASK2.l
        move.w  #$ffff,BLT_ENDMASK3.l
        move.w  #8,BLT_XCOUNT.l
        move.w  #16,BLT_YCOUNT.l
        move.w  #$0203,BLT_HOP.l
        clr.b   BLT_SKEW.l
        move.b  #$c0,BLT_LINE.l
        rte

; --- cmd 2: Batched LIFO reverse-order restore of d1.w 16-byte records ending at a0 ---
.cmd2_rest_lifo:
        move.w  #2,BLT_SRC_XINC.l
        move.w  #2,BLT_SRC_YINC.l
        move.w  #2,BLT_DST_XINC.l
        move.w  #(CORK_STRIDE-14),BLT_DST_YINC.l
        move.w  #$ffff,BLT_ENDMASK1.l
        move.w  #$ffff,BLT_ENDMASK2.l
        move.w  #$ffff,BLT_ENDMASK3.l
        move.w  #8,BLT_XCOUNT.l
        move.w  #$0203,BLT_HOP.l
        clr.b   BLT_SKEW.l
        subq.w  #1,d1
.c2_lp:
        lea     -16(a0),a0
        moveq   #0,d0
        move.b  13(a0),d0               ; slot_idx.b (0..31)
        lsl.w   #8,d0
        addi.l  #STE_SAVE_UNDER,d0
        move.l  d0,BLT_SRC_ADDR.l       ; slot_addr
        move.l  4(a0),BLT_DST_ADDR.l    ; dst_addr
        move.w  #16,BLT_YCOUNT.l
        move.b  #$c0,BLT_LINE.l
        dbra    d1,.c2_lp
        rte


; --- cmd 3: Combined Save-under + Direct NFSR Masked 4bpp Sprite Draw ---
; a0 = dst in STE_CORK_BUF, a1 = KO2 3bpp sprite src, a2 = save-under slot, d1.w = skew (0..15)
.cmd3_spr:
        movem.l d2-d3/a3,-(sp)
        ; 1. Save-under (a0 -> a2, 16 lines x 8 words = 256 bytes)
        move.l  a0,BLT_SRC_ADDR.l
        move.l  a2,BLT_DST_ADDR.l
        move.w  #2,BLT_SRC_XINC.l
        move.w  #(CORK_STRIDE-14),BLT_SRC_YINC.l
        move.w  #2,BLT_DST_XINC.l
        move.w  #2,BLT_DST_YINC.l
        move.w  #$ffff,BLT_ENDMASK1.l
        move.w  #$ffff,BLT_ENDMASK2.l
        move.w  #$ffff,BLT_ENDMASK3.l
        move.w  #8,BLT_XCOUNT.l
        move.w  #16,BLT_YCOUNT.l
        move.w  #$0203,BLT_HOP.l
        clr.b   BLT_SKEW.l
        move.b  #$c0,BLT_LINE.l

        ; 2. Configure skew: skew==0 -> XCOUNT=1 (2x faster!), skew>0 -> XCOUNT=2, NFSR=$40|skew
        tst.w   d1
        bne.s   .c3_skew
        move.w  #1,BLT_XCOUNT.l
        clr.w   BLT_DST_XINC.l
        move.w  #CORK_STRIDE,BLT_DST_YINC.l
        clr.b   BLT_SKEW.l
        bra.s   .c3_mask
.c3_skew:
        move.w  #$ffff,d2
        lsr.w   d1,d2
        move.w  d2,BLT_ENDMASK1.l
        not.w   d2
        move.w  d2,BLT_ENDMASK3.l
        move.w  #2,BLT_XCOUNT.l
        move.w  #8,BLT_DST_XINC.l
        move.w  #(CORK_STRIDE-8),BLT_DST_YINC.l
        move.b  d1,d2
        ori.b   #$40,d2                 ; NFSR = 1 (1 src word -> 2 dst words!)
        move.b  d2,BLT_SKEW.l

.c3_mask:
        ; Pass 1: Clear mask holes in dst planes 0, 1, 2 (OP=4: ~SRC & DST)
        clr.w   BLT_SRC_XINC.l
        move.w  #2,BLT_SRC_YINC.l       ; STE_MASK_BUF = 1 word/line
        move.w  #$0204,BLT_HOP.l
        lea     STE_MASK_BUF.l,a3
        move.l  a3,BLT_SRC_ADDR.l
        move.l  a0,BLT_DST_ADDR.l
        move.w  #16,BLT_YCOUNT.l
        move.b  #$c0,BLT_LINE.l

        move.l  a3,BLT_SRC_ADDR.l
        pea     2(a0)
        move.l  (sp)+,BLT_DST_ADDR.l
        move.w  #16,BLT_YCOUNT.l
        move.b  #$c0,BLT_LINE.l

        move.l  a3,BLT_SRC_ADDR.l
        pea     4(a0)
        move.l  (sp)+,BLT_DST_ADDR.l
        move.w  #16,BLT_YCOUNT.l
        move.b  #$c0,BLT_LINE.l

        ; Pass 2: OR mask into plane 3 (a0+6 -> sets bit 3 = sprite colours 9..15!)
        move.w  #$0207,BLT_HOP.l
        move.l  a3,BLT_SRC_ADDR.l
        pea     6(a0)
        move.l  (sp)+,BLT_DST_ADDR.l
        move.w  #16,BLT_YCOUNT.l
        move.b  #$c0,BLT_LINE.l

        ; Pass 3: OR sprite planes 0, 1, 2 DIRECTLY from KO2 src a1 (stride $78)!
        move.w  #$78,BLT_SRC_YINC.l
        move.l  a1,BLT_SRC_ADDR.l
        move.l  a0,BLT_DST_ADDR.l
        move.w  #16,BLT_YCOUNT.l
        move.b  #$c0,BLT_LINE.l

        pea     $28(a1)
        move.l  (sp)+,BLT_SRC_ADDR.l
        pea     2(a0)
        move.l  (sp)+,BLT_DST_ADDR.l
        move.w  #16,BLT_YCOUNT.l
        move.b  #$c0,BLT_LINE.l

        pea     $50(a1)
        move.l  (sp)+,BLT_SRC_ADDR.l
        pea     4(a0)
        move.l  (sp)+,BLT_DST_ADDR.l
        move.w  #16,BLT_YCOUNT.l
        move.b  #$c0,BLT_LINE.l

        movem.l (sp)+,d2-d3/a3
        rte

; --- cmd 4: Zero STE_CORK_BUF (73,920B) AND $078000 (32,000B stale Classic ST lines!) ---
.cmd4_clr:
        move.l  #STE_CORK_BUF,BLT_DST_ADDR.l
        move.w  #2,BLT_DST_XINC.l
        move.w  #2,BLT_DST_YINC.l
        move.w  #$ffff,BLT_ENDMASK1.l
        move.w  #$ffff,BLT_ENDMASK2.l
        move.w  #$ffff,BLT_ENDMASK3.l
        move.w  #84,BLT_XCOUNT.l        ; 168 bytes / 2
        move.w  #440,BLT_YCOUNT.l       ; 440 * 168 = 73,920 bytes
        move.w  #$0000,BLT_HOP.l        ; all zeroes
        clr.b   BLT_SKEW.l
        move.b  #$c0,BLT_LINE.l
        ; Also zero $078000 (32,000 bytes) so no stale Classic ST pitch lines trigger HUD/Banner!
        move.l  #$078000,BLT_DST_ADDR.l
        move.w  #80,BLT_XCOUNT.l        ; 160 bytes / 2
        move.w  #200,BLT_YCOUNT.l       ; 200 * 160 = 32,000 bytes
        move.b  #$c0,BLT_LINE.l
        rte

; --- cmd 5: Blitter HUD/Radar band draw ---
; a0 = src ($078000+y*160), a1 = dst (STE_VIEW_BASE+y*168), a2 = save_buf
; d1.w = W (4 or 20), d2.w = H (lines), d3.w = skew (0..15), d4.w = 1 (all 4 planes) / 0 (2 planes)
.cmd5_hud_draw:
        movem.l d5-d7/a3,-(sp)
        ; 1. Save-under (a1 -> a2): (W+1)*4 words x H lines
        move.w  d1,d5
        addq.w  #1,d5
        lsl.w   #2,d5                   ; d5 = (W+1)*4 words
        move.w  d5,d6
        subq.w  #1,d6
        add.w   d6,d6                   ; bytes advanced by XINC
        move.w  #CORK_STRIDE,d7
        sub.w   d6,d7                   ; SRC_YINC = 168 - ((W+1)*4 - 1)*2
        move.l  a1,BLT_SRC_ADDR.l
        move.l  a2,BLT_DST_ADDR.l
        move.w  #2,BLT_SRC_XINC.l
        move.w  d7,BLT_SRC_YINC.l
        move.w  #2,BLT_DST_XINC.l
        move.w  #2,BLT_DST_YINC.l
        move.w  #$ffff,BLT_ENDMASK1.l
        move.w  #$ffff,BLT_ENDMASK2.l
        move.w  #$ffff,BLT_ENDMASK3.l
        move.w  d5,BLT_XCOUNT.l
        move.w  d2,BLT_YCOUNT.l
        move.w  #$0203,BLT_HOP.l
        clr.b   BLT_SKEW.l
        move.b  #$c0,BLT_LINE.l

        ; 2. Build 1bpp mask in STE_HUD_MASK (W words x H lines)
        ;    src_yinc = 160 - (W-1)*8
        move.w  d1,d6
        subq.w  #1,d6
        lsl.w   #3,d6
        move.w  #160,d7
        sub.w   d6,d7                   ; d7 = src_yinc for 4bpp $078000
        lea     STE_HUD_MASK.l,a3
        move.w  #8,BLT_SRC_XINC.l
        move.w  d7,BLT_SRC_YINC.l
        move.w  #2,BLT_DST_XINC.l
        move.w  #2,BLT_DST_YINC.l
        move.w  d1,BLT_XCOUNT.l
        ; Plane 0 -> copy
        move.l  a0,BLT_SRC_ADDR.l
        move.l  a3,BLT_DST_ADDR.l
        move.w  d2,BLT_YCOUNT.l
        move.w  #$0203,BLT_HOP.l
        move.b  #$c0,BLT_LINE.l
        ; Plane 1 -> OR
        pea     2(a0)
        move.l  (sp)+,BLT_SRC_ADDR.l
        move.l  a3,BLT_DST_ADDR.l
        move.w  d2,BLT_YCOUNT.l
        move.w  #$0207,BLT_HOP.l
        move.b  #$c0,BLT_LINE.l
        tst.w   d4
        beq.s   .c5_mask_ok
        ; Plane 2 -> OR
        pea     4(a0)
        move.l  (sp)+,BLT_SRC_ADDR.l
        move.l  a3,BLT_DST_ADDR.l
        move.w  d2,BLT_YCOUNT.l
        move.b  #$c0,BLT_LINE.l
        ; Plane 3 -> OR
        pea     6(a0)
        move.l  (sp)+,BLT_SRC_ADDR.l
        move.l  a3,BLT_DST_ADDR.l
        move.w  d2,BLT_YCOUNT.l
        move.b  #$c0,BLT_LINE.l

.c5_mask_ok:
        ; 3. Configure skew, endmasks, XCOUNT, and DST_YINC for compositing into a1
        tst.w   d3
        bne.s   .c5_skewed
        ; skew == 0: XCOUNT = W, ENDMASK = ffff/ffff/ffff, DST_YINC = 168 - (W-1)*8
        move.w  #$ffff,BLT_ENDMASK1.l
        move.w  #$ffff,BLT_ENDMASK3.l
        move.w  d1,BLT_XCOUNT.l
        move.w  #CORK_STRIDE,d5
        sub.w   d6,d5                   ; d6 is still (W-1)*8
        move.w  d5,BLT_DST_YINC.l
        clr.b   BLT_SKEW.l
        bra.s   .c5_comp
.c5_skewed:
        ; skew > 0: XCOUNT = W+1, NFSR=$40|skew, DST_YINC = 168 - W*8
        move.w  #$ffff,d5
        lsr.w   d3,d5
        move.w  d5,BLT_ENDMASK1.l
        not.w   d5
        move.w  d5,BLT_ENDMASK3.l
        move.w  d1,d5
        addq.w  #1,d5
        move.w  d5,BLT_XCOUNT.l
        move.w  d1,d5
        lsl.w   #3,d5                   ; W * 8
        neg.w   d5
        addi.w  #CORK_STRIDE,d5         ; 168 - W*8
        move.w  d5,BLT_DST_YINC.l
        move.b  d3,d5
        ori.b   #$40,d5                 ; NFSR = 1!
        move.b  d5,BLT_SKEW.l

.c5_comp:
        ; Clear mask holes in dst planes 0, 1, 2 (OP=4: ~SRC & DST)
        move.w  #2,BLT_SRC_XINC.l
        move.w  #2,BLT_SRC_YINC.l
        move.w  #8,BLT_DST_XINC.l
        move.w  #$0204,BLT_HOP.l
        ; dst plane 0
        move.l  a3,BLT_SRC_ADDR.l
        move.l  a1,BLT_DST_ADDR.l
        move.w  d2,BLT_YCOUNT.l
        move.b  #$c0,BLT_LINE.l
        ; dst plane 1
        move.l  a3,BLT_SRC_ADDR.l
        pea     2(a1)
        move.l  (sp)+,BLT_DST_ADDR.l
        move.w  d2,BLT_YCOUNT.l
        move.b  #$c0,BLT_LINE.l
        ; dst plane 2
        move.l  a3,BLT_SRC_ADDR.l
        pea     4(a1)
        move.l  (sp)+,BLT_DST_ADDR.l
        move.w  d2,BLT_YCOUNT.l
        move.b  #$c0,BLT_LINE.l
        ; Set plane 3 (OP=7: SRC | DST -> maps HUD colours 1..7 -> 9..15, 8 -> 8!)
        move.w  #$0207,BLT_HOP.l
        move.l  a3,BLT_SRC_ADDR.l
        pea     6(a1)
        move.l  (sp)+,BLT_DST_ADDR.l
        move.w  d2,BLT_YCOUNT.l
        move.b  #$c0,BLT_LINE.l

        ; 4. OR source planes from $078000 (a0) into dst (a1)
        move.w  #8,BLT_SRC_XINC.l
        move.w  d7,BLT_SRC_YINC.l
        ; plane 0
        move.l  a0,BLT_SRC_ADDR.l
        move.l  a1,BLT_DST_ADDR.l
        move.w  d2,BLT_YCOUNT.l
        move.b  #$c0,BLT_LINE.l
        ; plane 1
        pea     2(a0)
        move.l  (sp)+,BLT_SRC_ADDR.l
        pea     2(a1)
        move.l  (sp)+,BLT_DST_ADDR.l
        move.w  d2,BLT_YCOUNT.l
        move.b  #$c0,BLT_LINE.l
        tst.w   d4
        beq.s   .c5_done
        ; plane 2
        pea     4(a0)
        move.l  (sp)+,BLT_SRC_ADDR.l
        pea     4(a1)
        move.l  (sp)+,BLT_DST_ADDR.l
        move.w  d2,BLT_YCOUNT.l
        move.b  #$c0,BLT_LINE.l

.c5_done:
        movem.l (sp)+,d5-d7/a3
        rte

; --- cmd 6: Blitter HUD/Radar restore-under ---
; a0 = save_buf, a1 = dst (STE_VIEW_BASE+y*168), d1.w = XCOUNT (words), d2.w = YCOUNT (lines)
.cmd6_hud_rest:
        move.w  d1,d0
        subq.w  #1,d0
        add.w   d0,d0
        neg.w   d0
        addi.w  #CORK_STRIDE,d0         ; DST_YINC = 168 - (XCOUNT-1)*2
        move.l  a0,BLT_SRC_ADDR.l
        move.l  a1,BLT_DST_ADDR.l
        move.w  #2,BLT_SRC_XINC.l
        move.w  #2,BLT_SRC_YINC.l
        move.w  #2,BLT_DST_XINC.l
        move.w  d0,BLT_DST_YINC.l
        move.w  #$ffff,BLT_ENDMASK1.l
        move.w  #$ffff,BLT_ENDMASK2.l
        move.w  #$ffff,BLT_ENDMASK3.l
        move.w  d1,BLT_XCOUNT.l
        move.w  d2,BLT_YCOUNT.l
        move.w  #$0203,BLT_HOP.l
        clr.b   BLT_SKEW.l
        move.b  #$c0,BLT_LINE.l
        rte

; --- cmd 7: STE Hardware Video Counter Beam-Wait (d1.w = sprite_y) ---
; Exact STE equivalent of KO2's $01a376/$01a3cc Timer B beam-chasing -> ZERO player flicker!
.cmd7_radar_opaque:
        movem.l d2-d3,-(sp)
        move.w  d1,d3
        mulu.w  #CORK_STRIDE,d3         ; d3.l = sprite_y * 168
.bw_lp:
        moveq   #0,d0
        move.b  $00ff8205.l,d0
        swap    d0
        move.b  $00ff8207.l,d2
        lsl.w   #8,d2
        move.b  $00ff8209.l,d2
        move.w  d2,d0                   ; d0.l = current 24-bit STE Shifter address
        sub.l   STE_VIEW_BASE(pc),d0
        blt.s   .bw_ok                  ; in border -> safe!
        cmpi.l  #(200*CORK_STRIDE),d0
        bge.s   .bw_ok                  ; in bottom border -> safe!
        sub.l   d3,d0                   ; d0.l = (beam_y - sprite_y) * 168
        cmpi.l  #-(12*CORK_STRIDE),d0
        blt.s   .bw_ok                  ; beam > 12 lines above sprite -> safe!
        cmpi.l  #(18*CORK_STRIDE),d0
        ble.s   .bw_lp                  ; beam is RIGHT AT sprite (-12..+18) -> wait!
.bw_ok:
        movem.l (sp)+,d2-d3
        rte

; --- cmd 8: Batched 21-tile horizontal row blit (d1=tx_left, d2=ty_row) ---
; Sets Blitter regs ONCE, skips redundant plane-3 clear (plane 3 is always 0!),
; and handles primary + mirror in one tight Supervisor loop!
.cmd8_blit_row:
        movem.l d3-d7/a2-a4,-(sp)
        ; Configure constant Blitter registers ONCE for all 21 tiles
        move.w  #2,BLT_SRC_XINC.l
        move.w  #2,BLT_SRC_YINC.l
        move.w  #2,BLT_DST_XINC.l
        move.w  #(CORK_STRIDE-4),BLT_DST_YINC.l
        move.w  #$ffff,BLT_ENDMASK1.l
        move.w  #$ffff,BLT_ENDMASK2.l
        move.w  #$ffff,BLT_ENDMASK3.l
        move.w  #3,BLT_XCOUNT.l
        move.w  #$0203,BLT_HOP.l        ; HOP=2 (src), OP=3 (copy)
        clr.b   BLT_SKEW.l

        ; Compute map ptr a2 = STE_PIT_MAP + ty*80 + tx_left
        move.w  d2,d0
        mulu.w  #80,d0
        add.w   d1,d0
        lea     STE_PIT_MAP.l,a2
        adda.l  d0,a2
        ; Compute primary dst a3 = STE_CORK_BUF + (ty%14)*16*168 + tx_left*8
        moveq   #0,d0
        move.w  d2,d0
        divu.w  #14,d0
        swap    d0                      ; d0 = ty % 14
        move.w  d0,d6                   ; d6 = ty % 14 (mirror if <= 12)
        lsl.w   #4,d0
        mulu.w  #CORK_STRIDE,d0
        move.w  d1,d3
        lsl.w   #3,d3
        ext.l   d3
        add.l   d3,d0
        lea     STE_CORK_BUF.l,a3
        adda.l  d0,a3
        lea     STE_PIT_TILES.l,a4

        ; Number of valid tiles = min(21, 80 - tx_left)
        moveq   #21,d7
        moveq   #80,d0
        sub.w   d1,d0
        ble.w   .c8_done
        cmp.w   d7,d0
        bge.s   .c8_cnt
        move.w  d0,d7
.c8_cnt:
        ; First: clear Plane 3 for the entire tile row in ONE Blitter call (+ mirror)!
        move.w  d7,d5                   ; save tile count (1..21) in d5
        move.w  d7,d4
        subq.w  #1,d4
        lsl.w   #3,d4
        neg.w   d4
        addi.w  #CORK_STRIDE,d4         ; DST_YINC = 168 - (cnt-1)*8
        move.w  #8,BLT_DST_XINC.l
        move.w  d4,BLT_DST_YINC.l
        move.w  d7,BLT_XCOUNT.l
        move.w  #$0000,BLT_HOP.l        ; OP=0 (zero plane 3!)
        lea     6(a3),a1
        move.l  a1,BLT_DST_ADDR.l
        move.w  #16,BLT_YCOUNT.l
        move.b  #$c0,BLT_LINE.l
        cmpi.w  #12,d6
        bgt.s   .c8_p3_ok
        adda.l  #CORK_RING_BYTES,a1
        move.l  a1,BLT_DST_ADDR.l
        move.w  #16,BLT_YCOUNT.l
        move.b  #$c0,BLT_LINE.l
.c8_p3_ok:
        ; Restore 3bpp tile blit settings
        move.w  #2,BLT_DST_XINC.l
        move.w  #(CORK_STRIDE-4),BLT_DST_YINC.l
        move.w  #3,BLT_XCOUNT.l
        move.w  #$0203,BLT_HOP.l
        move.w  d5,d7
        subq.w  #1,d7
        cmpi.w  #12,d6
        bgt.s   .c8_nomir
.c8_mir_lp:
        moveq   #0,d0
        move.b  (a2)+,d0
        move.w  d0,d3
        lsl.w   #6,d0                   ; tid * 64
        lsl.w   #5,d3                   ; tid * 32
        add.w   d3,d0                   ; tid * 96
        lea     0(a4,d0.w),a0
        move.l  a0,BLT_SRC_ADDR.l
        move.l  a3,BLT_DST_ADDR.l
        move.w  #16,BLT_YCOUNT.l
        move.b  #$c0,BLT_LINE.l
        move.l  a0,BLT_SRC_ADDR.l
        movea.l a3,a1
        adda.l  #CORK_RING_BYTES,a1
        move.l  a1,BLT_DST_ADDR.l
        move.w  #16,BLT_YCOUNT.l
        move.b  #$c0,BLT_LINE.l
        addq.l  #8,a3
        dbra    d7,.c8_mir_lp
        bra.s   .c8_done
.c8_nomir:
        moveq   #0,d0
        move.b  (a2)+,d0
        move.w  d0,d3
        lsl.w   #6,d0
        lsl.w   #5,d3
        add.w   d3,d0
        lea     0(a4,d0.w),a0
        move.l  a0,BLT_SRC_ADDR.l
        move.l  a3,BLT_DST_ADDR.l
        move.w  #16,BLT_YCOUNT.l
        move.b  #$c0,BLT_LINE.l
        addq.l  #8,a3
        dbra    d7,.c8_nomir
.c8_done:
        movem.l (sp)+,d3-d7/a2-a4
        rte

; --- cmd 9: Batched 14-tile vertical column blit (d1=tx_col, d2=ty_top) ---
.cmd9_blit_col:
        movem.l d3-d7/a2-a4,-(sp)
        move.w  #2,BLT_SRC_XINC.l
        move.w  #2,BLT_SRC_YINC.l
        move.w  #2,BLT_DST_XINC.l
        move.w  #(CORK_STRIDE-4),BLT_DST_YINC.l
        move.w  #$ffff,BLT_ENDMASK1.l
        move.w  #$ffff,BLT_ENDMASK2.l
        move.w  #$ffff,BLT_ENDMASK3.l
        move.w  #3,BLT_XCOUNT.l
        move.w  #$0203,BLT_HOP.l
        clr.b   BLT_SKEW.l

        ; Map ptr a2 = STE_PIT_MAP + ty_top*80 + tx_col
        move.w  d2,d0
        mulu.w  #80,d0
        add.w   d1,d0
        lea     STE_PIT_MAP.l,a2
        adda.l  d0,a2
        ; Initial ty%14 in d6, initial dst a3 in STE_CORK_BUF
        moveq   #0,d0
        move.w  d2,d0
        divu.w  #14,d0
        swap    d0
        move.w  d0,d6                   ; d6 = cur_row_mod (0..13)
        lsl.w   #4,d0
        mulu.w  #CORK_STRIDE,d0
        move.w  d1,d3
        lsl.w   #3,d3
        ext.l   d3
        add.l   d3,d0
        lea     STE_CORK_BUF.l,a3
        adda.l  d0,a3
        lea     STE_PIT_TILES.l,a4

        ; Number of valid rows = min(14, 96 - ty_top)
        moveq   #14,d7
        moveq   #96,d0
        sub.w   d2,d0
        ble.w   .c9_done
        cmp.w   d7,d0
        bge.s   .c9_cnt
        move.w  d0,d7
.c9_cnt:
        ; First: clear Plane 3 for the entire vertical column in ONE Blitter call (424 lines)!
        move.w  d1,d0
        lsl.w   #3,d0
        ext.l   d0
        lea     STE_CORK_BUF+6.l,a1
        adda.l  d0,a1
        clr.w   BLT_DST_XINC.l
        move.w  #CORK_STRIDE,BLT_DST_YINC.l
        move.w  #1,BLT_XCOUNT.l
        move.w  #$0000,BLT_HOP.l        ; OP=0 (zero plane 3!)
        move.l  a1,BLT_DST_ADDR.l
        move.w  #424,BLT_YCOUNT.l       ; entire primary + mirror column in 1 blit!
        move.b  #$c0,BLT_LINE.l
        ; Restore 3bpp tile blit settings
        move.w  #2,BLT_DST_XINC.l
        move.w  #(CORK_STRIDE-4),BLT_DST_YINC.l
        move.w  #3,BLT_XCOUNT.l
        move.w  #$0203,BLT_HOP.l
        subq.w  #1,d7
.c9_lp:
        moveq   #0,d0
        move.b  (a2),d0
        adda.w  #80,a2
        move.w  d0,d3
        lsl.w   #6,d0
        lsl.w   #5,d3
        add.w   d3,d0
        lea     0(a4,d0.w),a0
        move.l  a0,BLT_SRC_ADDR.l
        move.l  a3,BLT_DST_ADDR.l
        move.w  #16,BLT_YCOUNT.l
        move.b  #$c0,BLT_LINE.l
        cmpi.w  #12,d6
        bgt.s   .c9_nomir
        move.l  a0,BLT_SRC_ADDR.l
        movea.l a3,a1
        adda.l  #CORK_RING_BYTES,a1
        move.l  a1,BLT_DST_ADDR.l
        move.w  #16,BLT_YCOUNT.l
        move.b  #$c0,BLT_LINE.l
.c9_nomir:
        addq.w  #1,d6
        cmpi.w  #14,d6
        blt.s   .c9_step
        moveq   #0,d6
        suba.l  #(CORK_RING_BYTES-16*CORK_STRIDE),a3
        bra.s   .c9_next
.c9_step:
        adda.w  #(16*CORK_STRIDE),a3
.c9_next:
        dbra    d7,.c9_lp
.c9_done:
        movem.l (sp)+,d3-d7/a2-a4
        rte
