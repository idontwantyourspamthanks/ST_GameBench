; ---------------------------------------------------------------------------
; Player Manager v1.1 — Atari STE True Double-Buffered Amiga Engine (KO2STE.BIN)
;
; Loaded at $0ae940..$0b02ff (max 6,592 bytes) ONLY on Atari STE / Mega STE
; (when BR_IS_STE == 1). Plain 68000 ST never loads/calls this and keeps
; 100% classic v1.0 ST mode automatically.
;
; True Double-Buffered 1 MB STE RAM Layout during live match:
;   $078000..$079fff : Buffer B sprite save-under (32 x 256B = 8 KB; KO2 radar $01fae8/$01fbb4 stubbed!)
;   $07a000..$07aa7f : Buffer A transparent HUD save-under (16 x 168B = 2,688B)
;   $07ab00..$07b57f : Buffer B transparent HUD save-under (16 x 168B = 2,688B)
;   $07b600..$07b87f : 1bpp transparent HUD mask buffer (16 x 40B = 640B)
;   $07c800..$07e7ff : Buffer A sprite save-under (32 x 256B = 8 KB, below KO2 $07bc00 banners!)
;   $07f1c0..$07fcff : KO2 hidden Bottom HUD source (composited transparently onto 200-line pitch!)
;   $07fd00..$0804ff : Buffer A radar line save pool (2 KB, outside $078000..$07fcff!)
;   $080500..$080cff : Buffer B radar line save pool (2 KB, outside $078000..$07fcff!)
;   $081000..$088e1f : Active Amiga pitch (AMIGAP0..3.BIN: pal + 80x96 map + 256 tiles)
;   $088e60..$0923ef : Ring Buffer A (224 lines x 168B + 1 mirror + 488B slack = 38,288B)
;   $0923f0..$09b97f : Ring Buffer B (224 lines x 168B + 1 mirror + 488B slack = 38,288B)
;   $09ba00..$09c45f : Double-buffer stacks, radar records, mask & active sprite list (< $09d000!)
;   $0b2880..$0b2cff : Double-buffer radar dot restore records (below PMOK @ $0b2ff8)
;
; Entry points (fixed header at $0ae940):
;   +$00 : bra.w ste_install_hooks  (after KO2ENG.BIN loads, before $01fd92)
;   +$04 : bra.w ste_cleanup        (in Supervisor SR=$2700 on KO2 exit)
;   +$08 : STE_SND_SIZE.l           (filled by ko2_bridge.s with AMIGASND.BIN size)
;   +$0c : bra.w ste_load_pitch     (after $013450, loads AMIGAP0..3.BIN -> $081000)
; ---------------------------------------------------------------------------

        org     $0ae940

KO2_A4          equ     $0284aa
STE_SND_STG     equ     $0c8b00         ; AMIGASND.BIN staging in KO2_REPLAY_BUF

; Amiga pitch data ($081000..$088e1f)
STE_PIT_PAL     equ     $081000         ; 32 bytes (8 STE 12-bit pitch colours)
STE_PIT_MAP     equ     $081020         ; 7,680 bytes (80 x 96 tilemap)
STE_PIT_TILES   equ     $082e20         ; 24,576 bytes (256 x 96 bytes 3bpp tiles)

; Double-buffered 224-line x 168B Ring Buffers (14 tile rows x 21 tiles, unmirrored!)
; ALL metadata (stacks, records, sprite list) lives OUTSIDE $078000..$07fcff so KO2's
; center banners ("KICK OFF" / "GOAL") at $07bc00..$07c800 can NEVER corrupt pointers!
STE_RING_A      equ     $088e60         ; $088e60..$0923ef (225*168 + 488B slack = 38,288B)
STE_RING_B      equ     $0923f0         ; $0923f0..$09b97f (225*168 + 488B slack = 38,288B)
STE_SAV_A       equ     $07c800         ; $07c800..$07e7ff (8 KB: below KO2 $07bc00 banners, above $07f1c0 HUD!)
STE_SAV_B       equ     $078000         ; $078000..$079fff (8 KB: y=0..51, KO2 radar $01fae8/$01fbb4 stubbed!)
STE_HUD_SAV_A   equ     $07a000         ; $07a000..$07aa7f (16 x 168B = 2,688B)
STE_HUD_SAV_B   equ     $07ab00         ; $07ab00..$07b57f (16 x 168B = 2,688B)
STE_HUD_MASK    equ     $07b600         ; $07b600..$07b87f (16 x 40B  = 640B 1bpp HUD mask)
STE_HUD_SRC     equ     $07f1c0         ; KO2 hidden bottom HUD (16 lines x 160B)
STE_RPOOL_A     equ     $07fd00         ; $07fd00..$0804ff (2 KB, cleanly above $07fcff screen!)
STE_RPOOL_B     equ     $080500         ; $080500..$080cff (2 KB, cleanly above $07fcff screen!)

; Double-buffer metadata in 100% KO2-untouched RAM ($09ba00..$09c460 & $0b2880..$0b2d00!)
STE_STK_A       equ     $09ba00         ; 32 x 16B = 512B -> $09bc00
STE_STK_B       equ     $09bc00         ; 32 x 16B = 512B -> $09be00
STE_RLR_A       equ     $09be00         ; 28 x 16B = 448B -> $09bfc0
STE_RLR_B       equ     $09bfc0         ; 28 x 16B = 448B -> $09c180
STE_SPR_LIST    equ     $09c180         ; 32 x 16B = 512B -> $09c380
STE_RAD_CACHE   equ     $09c380         ; 24 x 8B  = 192B -> $09c440
STE_MASK_BUF    equ     $09c440         ; 32B             -> $09c460 (< $09d000!)
STE_RDR_A       equ     $0b2880         ; 48 x 12B = 576B -> $0b2ac0
STE_RDR_B       equ     $0b2ac0         ; 48 x 12B = 576B -> $0b2d00 (< PMOK $0b2ff8!)

RING_STRIDE     equ     168             ; 336 pixels = 21 x 16px words (4bpp)
RING_H          equ     224             ; 14 tile rows = 224 scanlines (covers 200px @ any wy%16!)
RING_ROWS       equ     14              ; 224 / 16
RING_BYTES      equ     37632           ; 224 * 168
PITCH_VIS_H     equ     200             ; full 320x200 pitch! (transparent HUD overlaid at y=183..198)
HUD_SCR_Y       equ     183             ; transparent HUD top scanline (183..198 = 16 lines)

; Buffer descriptor offsets (64 bytes per buffer: DB_A at 0, DB_B at 64)
DB_RING         equ     0               ; .l ring base ($088e60 / $0923f0)
DB_SAV          equ     4               ; .l save-under base ($07c800 / $078000)
DB_STK          equ     8               ; .l sprite restore stack base
DB_RPOOL        equ     12              ; .l radar line save pool base (2 KB)
DB_RLR          equ     16              ; .l radar line record base (28 x 16B)
DB_RDR          equ     20              ; .l radar dot record base (48 x 12B)
DB_TX           equ     24              ; .w last tile X drawn into this ring
DB_TY           equ     26              ; .w last tile Y drawn into this ring
DB_SCNT         equ     28              ; .w sprites drawn onto this ring (0..32)
DB_RLCNT        equ     30              ; .w radar lines drawn onto this ring (0..28)
DB_RDCNT        equ     32              ; .w radar dots drawn onto this ring (0..48)
DB_WTGT         equ     34              ; .w (TARGET - 8) & $ffff for exact video-counter wrap lock!
DB_START        equ     36              ; .l display start addr (RING + y0*168 + tx*8)
DB_WRAP         equ     40              ; .l display wrap addr  (RING + tx*8)
DB_WRAPY        equ     44              ; .w wrap scanline (224 - y0, 1..224)
DB_HSCR         equ     46              ; .w fine hscroll (0..15)
DB_HUDSAV       equ     48              ; .l HUD save-under base (STE_HUD_SAV_A / B)
DB_HUD_T        equ     52              ; .l HUD top dst on ring
DB_HUD_B        equ     56              ; .l HUD wrap bottom dst on ring (or 0)
DB_HUD_H1       equ     60              ; .w HUD top height (0 = none, 1..16)
DB_HUD_H2       equ     62              ; .w HUD wrap bottom height (0..15)
DB_SIZE         equ     64

; STE Blitter registers (short I/O addresses $ffff8a20..$ffff8a3d)
BLT_SRC_XINC    equ     $ffff8a20
BLT_SRC_YINC    equ     $ffff8a22
BLT_SRC_ADDR    equ     $ffff8a24
BLT_ENDMASK1    equ     $ffff8a28
BLT_ENDMASK2    equ     $ffff8a2a
BLT_ENDMASK3    equ     $ffff8a2c
BLT_DST_XINC    equ     $ffff8a2e
BLT_DST_YINC    equ     $ffff8a30
BLT_DST_ADDR    equ     $ffff8a32
BLT_XCOUNT      equ     $ffff8a36
BLT_YCOUNT      equ     $ffff8a38
BLT_HOP         equ     $ffff8a3a
BLT_OP          equ     $ffff8a3b
BLT_LINE        equ     $ffff8a3c
BLT_SKEW        equ     $ffff8a3d

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
STE_SCRIPT_ST:  dc.l    0
STE_SCRIPT_PTR: dc.l    0
STE_REPEAT_CNT: dc.w    0
STE_SND_PEND:   dc.b    0
STE_SND_STOP:   dc.b    0
STE_SND_PITCH:  dc.b    0
STE_SND_PAD:    dc.b    0
STE_DMA_CNT:    dc.w    0

; ---------------------------------------------------------------------------
; Double-Buffered Video State
; ---------------------------------------------------------------------------
STE_PITCH_OK:   dc.w    0               ; 1 = AMIGAPx.BIN loaded
STE_SHOW_IDX:   dc.w    0               ; 0 = Buffer A displayed, 1 = Buffer B displayed (ATOMIC!)
STE_STATS_DIRTY: dc.w   0               ; 1 = returning from Half-Time/Stats ($078000 was overwritten)
STE_ORIG_TB:    dc.l    0               ; saved KO2 original Timer B vector ($120.w)
STE_ORIG_VBL:   dc.l    0               ; saved TOS original VBL vector ($70.w)
STE_ORIG_TC:    dc.l    0               ; saved Timer C vector ($114.w) for Timer B preemption
STE_ORIG_IKBD:  dc.l    0               ; saved IKBD vector ($118.w) for Timer B preemption
STE_CUR_WX:     dc.w    176             ; current camera world X (pixels) for sprite world coords
STE_CUR_WY:     dc.w    64              ; current camera world Y (pixels)
STE_SPR_CNT:    dc.w    0               ; active sprites in STE_SPR_LIST (0..32)
STE_TB_WRAP_A:  dc.l    STE_RING_A      ; latched wrap address for active frame's Timer B
STE_TB_WRAP_Y:  dc.w    224             ; latched wrap scanline for active frame's Timer B
STE_TB_TGT_W:   dc.w    0               ; latched (TARGET - 8) & $ffff for video-counter lock!
STE_RAD_C_SC:   dc.w    0               ; cached radar scale
STE_RAD_C_HCNT: dc.w    0
STE_RAD_C_VCNT: dc.w    0
STE_BK_HSCR:    dc.w    0               ; temp backbuffer hscr during draw
STE_BK_Y0:      dc.w    0               ; temp backbuffer y0 (0..223) during draw
STE_BK_TX8:     dc.l    0               ; temp backbuffer tx*8 during draw
STE_BK_REND:    dc.l    0               ; temp backbuffer radar pool end during draw
STE_UL_DASH:    dc.l    0               ; secondary/pass-target player struct ptr ($fc3f dashed bar)

DB_A:
        dc.l    STE_RING_A, STE_SAV_A, STE_STK_A, STE_RPOOL_A, STE_RLR_A, STE_RDR_A
        dc.w    -999, -999, 0, 0, 0, 0
        dc.l    STE_RING_A, STE_RING_A
        dc.w    224, 0
        dc.l    STE_HUD_SAV_A, 0, 0
        dc.w    0, 0
DB_B:
        dc.l    STE_RING_B, STE_SAV_B, STE_STK_B, STE_RPOOL_B, STE_RLR_B, STE_RDR_B
        dc.w    -999, -999, 0, 0, 0, 0
        dc.l    STE_RING_B, STE_RING_B
        dc.w    224, 0
        dc.l    STE_HUD_SAV_B, 0, 0
        dc.w    0, 0

; ---------------------------------------------------------------------------
; ste_install_hooks: Patch KO2ENG.BIN at $010000..$024000 for pure STE mode
; ---------------------------------------------------------------------------
ste_install_hooks:
        clr.l   STE_SND_BASE
        clr.l   STE_SCRIPT_ST
        clr.l   STE_SCRIPT_PTR
        clr.w   STE_REPEAT_CNT
        clr.b   STE_SND_PEND
        clr.b   STE_SND_STOP
        clr.w   STE_DMA_CNT
        clr.w   STE_PITCH_OK
        clr.w   STE_SHOW_IDX
        clr.w   STE_STATS_DIRTY
        clr.l   STE_ORIG_TB
        clr.l   STE_ORIG_VBL
        clr.l   STE_ORIG_TC
        clr.l   STE_ORIG_IKBD
        clr.w   STE_SPR_CNT
        clr.w   STE_RAD_C_SC
        clr.l   STE_UL_DASH

        ; Install TRAP #8 ($a0.w) fast Supervisor Blitter dispatcher via Supexec
        pea     ste_inst_trap8(pc)
        move.w  #$26,-(sp)
        trap    #14
        addq.l  #6,sp

        ; 1. Audio hooks ($01849e load, $0184fe play low, $018506 play hi, $018598 stop)
        move.w  #$4ef9,d0
        move.w  d0,$01849e.l
        move.l  #ste_load_samples,$0184a0.l
        move.w  d0,$0184fe.l
        move.l  #ste_play_sound,$018500.l
        move.w  d0,$018506.l
        move.l  #ste_play_sound_hi,$018508.l
        move.w  d0,$018598.l
        move.l  #ste_stop_sound,$01859a.l

        ; 2. VBL top ($018d06 -> skip KO2 ST screen setup; real setup runs at scanline -50 via $70.w!) & bottom ($018e0a)
        move.w  d0,$018d06.l
        move.l  #ste_vbl_skip,$018d08.l
        move.w  d0,$018e0a.l
        move.l  #ste_vbl_end,$018e0c.l

        ; 3. Pitch camera & double-buffered frame render ($01c1d0)
        move.w  d0,$01c1d0.l
        move.l  #ste_pitch_update,$01c1d2.l

        ; 4. Sprite draw core ($01a426) & erase ($01a83e) -> ZERO-blit list updates!
        move.w  d0,$01a426.l
        move.l  #ste_draw_spr_core,$01a428.l
        move.w  d0,$01a83e.l
        move.l  #ste_erase_spr,$01a840.l
        ; Bypass KO2's Classic ST Timer B raster-beam waits ($01a376 & $01a3cc) -> ZERO wait!
        move.w  d0,$01a376.l
        move.l  #$01a39c,$01a378.l
        move.w  d0,$01a3cc.l
        move.l  #$01a3f2,$01a3ce.l
        ; Expand KO2's sprite Y-culling limit from 183 ($b7) to 200 ($c8) for full 320x200 pitch!
        move.w  #PITCH_VIS_H,d1
        move.w  d1,$01a304.l
        move.w  d1,$01a34e.l
        move.w  d1,$01a3c4.l
        move.w  d1,$01a41c.l

        ; 5. Skip KO2's hidden $078000 radar line ($01fae8), dot ($01fbb4) & underline ($01f9e0/$01fa76) drawers!
        move.w  #$4e75,$01fae8.l        ; rts!
        move.w  #$4e75,$01fbb4.l        ; rts! (keeps KO2's $20(a5)/$22(a5) coord updates intact!)
        move.l  #$60000036,$01f9e0.l    ; bra.w $01fa18 (skip $078000 solid underline; keeps replay record!)
        move.w  d0,$01fa76.l            ; jmp ste_rec_ul_dash (skip $078000 dashed underline + capture ptr!)
        move.l  #ste_rec_ul_dash,$01fa78.l
        rts

ste_rec_ul_dash:
        move.l  a5,STE_UL_DASH
        jmp     $01faae.l

ste_inst_trap8:
        move.l  #ste_trap8_handler,$a0.w
        move.l  $70.w,STE_ORIG_VBL
        move.l  #ste_vbl_irq,$70.w
        rts

; ---------------------------------------------------------------------------
; ste_cleanup: Called in Supervisor mode (SR=$2700) when exiting KO2 back to PM
; ---------------------------------------------------------------------------
ste_cleanup:
        clr.b   $ffff8901.w             ; stop STE DMA audio
        clr.b   $fffffa1b.w             ; stop Timer B
        tst.l   STE_ORIG_TB
        beq.s   .cl_notb
        move.l  STE_ORIG_TB(pc),$0120.w
.cl_notb:
        tst.l   STE_ORIG_VBL
        beq.s   .cl_novbl
        move.l  STE_ORIG_VBL(pc),$70.w
.cl_novbl:
        tst.l   STE_ORIG_TC
        beq.s   .cl_notc
        move.l  STE_ORIG_TC(pc),$0114.w
        clr.l   STE_ORIG_TC
.cl_notc:
        tst.l   STE_ORIG_IKBD
        beq.s   .cl_noik
        move.l  STE_ORIG_IKBD(pc),$0118.w
        clr.l   STE_ORIG_IKBD
.cl_noik:
        clr.b   $ffff820f.w
        clr.b   $ffff8265.w
        move.b  #$07,$ffff8201.w
        move.b  #$80,$ffff8203.w
        clr.b   $ffff820d.w
        clr.w   STE_PITCH_OK
        clr.l   STE_SCRIPT_PTR
        clr.b   STE_SND_PEND
        clr.b   STE_SND_STOP
        rts

; ---------------------------------------------------------------------------
; ste_load_pitch: Called after ko2_bridge.s loads AMIGAPx.BIN -> $081000
; ---------------------------------------------------------------------------
ste_load_pitch:
        cmpi.l  #32288,d0
        bne.s   .lp_fail
        clr.w   STE_SHOW_IDX
        clr.w   STE_SPR_CNT
        clr.w   STE_RAD_C_SC
        clr.l   STE_UL_DASH
        clr.w   STE_STATS_DIRTY
        bsr.s   ste_reset_bufs
        moveq   #4,d0                   ; cmd 4 = clear rings & blank line buffer
        trap    #8
        move.w  #1,STE_PITCH_OK
        rts
.lp_fail:
        clr.w   STE_PITCH_OK
        rts

ste_reset_bufs:
        lea     DB_A(pc),a0
        move.w  #-999,DB_TX(a0)
        move.w  #-999,DB_TY(a0)
        clr.w   DB_SCNT(a0)
        clr.w   DB_RLCNT(a0)
        clr.w   DB_RDCNT(a0)
        move.l  #STE_RING_A,DB_START(a0)
        move.l  #STE_RING_A,DB_WRAP(a0)
        move.w  #RING_H,DB_WRAPY(a0)
        clr.w   DB_HSCR(a0)
        clr.w   DB_HUD_H1(a0)
        clr.w   DB_HUD_H2(a0)
        lea     DB_B(pc),a0
        move.w  #-999,DB_TX(a0)
        move.w  #-999,DB_TY(a0)
        clr.w   DB_SCNT(a0)
        clr.w   DB_RLCNT(a0)
        clr.w   DB_RDCNT(a0)
        move.l  #STE_RING_B,DB_START(a0)
        move.l  #STE_RING_B,DB_WRAP(a0)
        move.w  #RING_H,DB_WRAPY(a0)
        clr.w   DB_HSCR(a0)
        clr.w   DB_HUD_H1(a0)
        clr.w   DB_HUD_H2(a0)
        rts

; ---------------------------------------------------------------------------
; Audio: ste_load_samples / ste_play_sound / ste_play_sound_hi / ste_stop_sound
; ---------------------------------------------------------------------------
ste_load_samples:
        movem.l d0,-(sp)
        move.l  a5,d0
        addq.l  #1,d0
        and.l   #$fffffffe,d0
        movea.l d0,a5
        move.l  a5,-$1452(a4)
        move.l  a5,STE_SND_BASE         ; ko2_bridge.s loads AMIGASND.BIN directly here!
        adda.l  #$5a00,a5               ; reserve 23,040B inside KO2's $1c138 Malloc block (no staging RAM!)
        clr.w   -$142a(a4)
        movem.l (sp)+,d0
        rts

ste_play_sound:
        tst.w   -$142a(a4)
        bne.s   ste_ps_rts
ste_play_sound_hi:
        tst.w   -$5eec(a4)
        bne.s   ste_ps_rts
        tst.l   STE_SND_BASE
        beq.s   ste_ps_rts
        clr.b   STE_SND_PEND            ; disarm VBL stepper during update (zero IRQ race!)
        clr.l   STE_SCRIPT_PTR
        move.l  a2,STE_SCRIPT_ST
        clr.w   STE_REPEAT_CNT          ; 0 -> first step advances normally
        move.w  #1,-$142a(a4)
        clr.b   STE_SND_STOP
        move.l  a2,STE_SCRIPT_PTR
        move.b  #1,STE_SND_PEND         ; trigger VBL stepper atomically LAST!
ste_ps_rts:
        rts

ste_stop_sound:
        clr.b   STE_SND_PEND
        clr.l   STE_SCRIPT_PTR
        move.b  #1,STE_SND_STOP
        clr.w   -$142a(a4)
        rts

; ---------------------------------------------------------------------------
; VBL IRQ ($70.w): Runs at scanline -50 (BEFORE TOS VBL queue!) -> Timer B is
; ALWAYS armed 50 scanlines before line 0, even under 100% Blitter load!
; Writes SHOW_START to BOTH $8201/$03/$0d AND $8205/$07/$09 (ZERO +16px judder!)
; ---------------------------------------------------------------------------
ste_vbl_skip:
        movem.l d0-d1,-(sp)             ; $018d6e expects d0-d1 on stack (original $018d06)!
        jmp     $018d6e.l

ste_vbl_irq:
        tst.w   STE_PITCH_OK
        beq.w   .vt_chain_fast
        movem.l d0-d2/a0-a1,-(sp)
        bclr    #7,BLT_LINE.w           ; pause Blitter briefly so VBL setup finishes at line -49!
        sne     d2
        tst.l   $0231c8.l               ; KO2 -$52e2(a4): KO2 VBL active? (0 = Half-Time/Full-Time/Exit!)
        beq.w   .vt_stats_mark
        tst.w   $02356a.l               ; KO2 -$4f40(a4): Half-Time/Full-Time/Stats on $078000?
        bne.w   .vt_stats_mark

        clr.b   $fffffa1b.w             ; stop Timer B
        tst.l   STE_ORIG_TB
        bne.s   .vt_tb_ok
        move.l  $0120.w,STE_ORIG_TB
.vt_tb_ok:
        ; Wrap Timer C ($114.w) & IKBD ($118.w) so higher-priority MFP Timer B (prio 8)
        ; ALWAYS preempts them immediately (fixes MiSTerFPGA/real-STE Timer C/IKBD black-line slip!)
        move.l  $0114.w,d0
        beq.s   .vt_tc_ok
        cmpi.l  #ste_tc_wrap,d0
        beq.s   .vt_tc_ok
        move.l  d0,STE_ORIG_TC
        move.l  #ste_tc_wrap,$0114.w
.vt_tc_ok:
        move.l  $0118.w,d0
        beq.s   .vt_ik_ok
        cmpi.l  #ste_ikbd_wrap,d0
        beq.s   .vt_ik_ok
        move.l  d0,STE_ORIG_IKBD
        move.l  #ste_ikbd_wrap,$0118.w
.vt_ik_ok:
        ; Load STE 12-bit Amiga pitch palette (0..7)
        lea     STE_PIT_PAL.l,a0
        lea     $ffff8240.w,a1
        move.l  (a0)+,(a1)+
        move.l  (a0)+,(a1)+
        move.l  (a0)+,(a1)+
        move.l  (a0)+,(a1)+

        ; Select active Front buffer descriptor (DB_A or DB_B)
        lea     DB_A(pc),a0
        tst.w   STE_SHOW_IDX
        beq.s   .vt_buf
        lea     DB_B(pc),a0
.vt_buf:
        ; Program BOTH Video Base ($8201/$03/$0d) AND live Video Counter ($8205/$07/$09)
        ; -> Takes effect THIS frame alongside $8265/$820f -> ZERO +16px judder!
        move.l  DB_START(a0),d0
        move.l  d0,d1
        swap    d1
        move.b  d1,$ffff8201.w
        move.b  d1,$ffff8205.w
        move.w  d0,d1
        lsr.w   #8,d1
        move.b  d1,$ffff8203.w
        move.b  d1,$ffff8207.w
        move.b  d0,$ffff820d.w
        move.b  d0,$ffff8209.w

        move.w  DB_HSCR(a0),d0
        move.b  d0,$ffff8265.w          ; fine pixel hscroll (0..15)
        beq.s   .vt_h0
        clr.b   $ffff820f.w             ; hscroll != 0 -> STE adds +8B auto = 168B!
        bra.s   .vt_arm_tb
.vt_h0:
        move.b  #4,$ffff820f.w          ; hscroll == 0 -> +4 extra words (+8B) = 168B!

.vt_arm_tb:
        ; Full 320x200 pitch! Only arm Timer B if ring wraps within lines 0..199!
        move.l  DB_WRAP(a0),STE_TB_WRAP_A
        move.w  DB_WTGT(a0),STE_TB_TGT_W
        move.w  DB_WRAPY(a0),d0
        move.w  d0,STE_TB_WRAP_Y
        cmpi.w  #PITCH_VIS_H,d0         ; wrap_y >= 200 -> ZERO Timer B IRQs this frame!
        bge.s   .vt_exit
        ; DB_WRAPY is ALWAYS in 2..199 (y0=223 mirrors row 0->224 and sets wrap_y=2)!
        ; Arm 1 scanline early (wrap_y - 1 >= 1) so ste_tb_wrap locks onto exact video counter!
        subq.w  #1,d0
        move.l  #ste_tb_wrap,$0120.w
        move.b  d0,$fffffa21.w
        move.b  #8,$fffffa1b.w          ; Event Count mode
        bset    #0,$fffffa07.w          ; enable Timer B in IERA
        bset    #0,$fffffa13.w          ; enable Timer B in IMRA
.vt_exit:
        tst.b   d2
        beq.s   .vt_nr
        bset    #7,BLT_LINE.w           ; resume paused Blitter!
.vt_nr: movem.l (sp)+,d0-d2/a0-a1
.vt_chain_fast:
        move.l  STE_ORIG_VBL(pc),-(sp)
        rts

.vt_stats_mark:
        move.w  #1,STE_STATS_DIRTY
        clr.b   $fffffa1b.w
        tst.l   STE_ORIG_TC
        beq.s   .vsm_notc
        move.l  STE_ORIG_TC(pc),$0114.w
        clr.l   STE_ORIG_TC
.vsm_notc:
        tst.l   STE_ORIG_IKBD
        beq.s   .vsm_noik
        move.l  STE_ORIG_IKBD(pc),$0118.w
        clr.l   STE_ORIG_IKBD
.vsm_noik:
        move.b  #$07,$ffff8201.w
        move.b  #$80,$ffff8203.w
        clr.b   $ffff820d.w
        move.b  #$07,$ffff8205.w
        move.b  #$80,$ffff8207.w
        clr.b   $ffff8209.w
        clr.b   $ffff820f.w
        clr.b   $ffff8265.w
        bra.s   .vt_exit

; MFP IPL-5 preemption wrappers: ISRB stays set (no re-entry!), but Timer B (prio 8) preempts immediately!
ste_tc_wrap:
        move.w  #$2500,sr
        move.l  STE_ORIG_TC(pc),-(sp)
        rts

ste_ikbd_wrap:
        move.w  #$2500,sr
        move.l  STE_ORIG_IKBD(pc),-(sp)
        rts

; ---------------------------------------------------------------------------
; Exact Video-Counter-Locked Timer B ISR (Blitter-Paused -> ZERO 1px judder!):
;   ste_tb_wrap  : Mid-screen 224-line Ring Buffer vertical wrap (ONLY IRQ!)
;   Compares live Shifter counter ($8207/$8209 via movep.w) against TARGET-8 so
;   even late IRQ arrival into HBlank of line (wrap_y-1) NEVER slips a scanline!
; ---------------------------------------------------------------------------
ste_tb_wrap:
        clr.b   $fffffa1b.w
        bclr    #7,BLT_LINE.w           ; pause active $80 Blitter FIRST (movem preserves CCR!)
        movem.l d0-d5/a0,-(sp)
        sne     d4                      ; d4.b = $ff if Blitter was running
        ; Pre-split STE_TB_WRAP_A into HIGH(d1), MID(d2), LOW(d3) BEFORE HBlank
        move.l  STE_TB_WRAP_A(pc),d3
        move.l  d3,d1
        swap    d1                      ; d1.b = HIGH ($8205)
        move.w  d3,d2
        lsr.w   #8,d2                   ; d2.b = MID  ($8207); d3.b = LOW ($8209)
        move.w  STE_TB_TGT_W(pc),d5     ; d5.w = (TARGET - 8) & $ffff
        lea     $ffff8205.w,a0
        ; Wait until Shifter live counter reaches exact end of line (wrap_y - 1)!
.tw_wt: movep.w 2(a0),d0                ; atomic 16-bit read of $8207 (MID) + $8209 (LOW)
        sub.w   d5,d0                   ; signed (VCOUNT_16 - (TARGET - 8))
        blt.s   .tw_wt                  ; loop while still before end of line (wrap_y - 1)
        nop                             ; 8 x nop = 32 cycles -> safely past DE=0 & LINEWID!
        nop
        nop
        nop
        nop
        nop
        nop
        nop
        ; Reload live video counter HIGH->MID->LOW dead-center in HBlank (before pre-fetch!)
        move.b  d1,(a0)                 ; $ffff8205 HIGH
        move.b  d2,2(a0)                ; $ffff8207 MID
        move.b  d3,4(a0)                ; $ffff8209 LOW
        tst.b   d4
        beq.s   .tw_no_res
        bset    #7,BLT_LINE.w           ; resume paused Blitter seamlessly!
.tw_no_res:
        movem.l (sp)+,d0-d5/a0
        bclr    #0,$fffffa0f.w
        rte

; ---------------------------------------------------------------------------
; VBL End ($018e0a): Skip ST $ff8240 stripe write, set VBL flag, step DMA Audio
; ---------------------------------------------------------------------------
ste_vbl_end:
        clr.w   $2718a.l
        move.w  #$ffff,$27190.l         ; VBL sync flag!

        ; STE DMA Audio step
        tst.b   STE_SND_STOP
        beq.s   .chk_pend
        clr.b   STE_SND_STOP
        clr.b   $ffff8901.w
        rts
.chk_pend:
        tst.b   STE_SND_PEND
        bne.s   .do_step
        tst.l   STE_SCRIPT_PTR
        beq.w   .vbl_done
        btst    #0,$ffff8901.w
        bne.w   .vbl_done
.do_step:
        clr.b   STE_SND_PEND
        movem.l d0-d4/a0-a1,-(sp)
        movea.l STE_SND_BASE(pc),a1
        move.l  a1,d0
        beq.w   .step_stop
        moveq   #8,d4                   ; guard against >8 control words per VBL
.next_cmd:
        subq.w  #1,d4
        blt.w   .step_stop
        movea.l STE_SCRIPT_PTR(pc),a0
        move.l  a0,d0
        beq.w   .step_stop
        ; Exact KO2 16-bit word script interpreter (matches $018610..$018714!):
        ;   d0 == 0        : end of script -> stop
        ;   d0 == -1       : loop back to STE_SCRIPT_ST
        ;   d0 <= -2       : repeat next word (-d0) times
        ;   d0 >= 200      : pitch override (d0 - 200), advance to next word
        ;   100 <= d0 <200 : play sample (d0 - 101) (0..16)
        ;   1   <= d0 <100 : play sample (d0 - 1)   (0..16)
        addq.w  #1,STE_REPEAT_CNT
        blt.s   .keep_ptr               ; still repeating current word!
        addq.l  #2,STE_SCRIPT_PTR       ; advance to next 16-bit word
.keep_ptr:
        move.w  (a0),d0                 ; read 16-bit signed script word!
        beq.w   .step_stop              ; 0 = end of script!
        blt.s   .cmd_neg
        cmpi.w  #200,d0
        bge.s   .cmd_pitch
        cmpi.w  #100,d0
        bge.s   .cmd_s_hi
        subq.w  #1,d0                   ; 1..17 -> 0..16
        bra.s   .cmd_sample
.cmd_s_hi:
        subi.w  #101,d0                 ; 101..117 -> 0..16
        bra.s   .cmd_sample
.cmd_neg:
        cmpi.w  #-1,d0
        beq.s   .cmd_loop
        move.w  d0,STE_REPEAT_CNT       ; repeat next word (-d0) times!
        bra.s   .next_cmd
.cmd_loop:
        move.l  STE_SCRIPT_ST(pc),STE_SCRIPT_PTR
        clr.w   STE_REPEAT_CNT
        bra.s   .next_cmd
.cmd_pitch:
        subi.w  #200,d0
        move.b  d0,STE_SND_PITCH
        bra.s   .next_cmd
.cmd_sample:
        cmpi.w  #17,d0
        bcc.s   .next_cmd               ; out-of-range -> skip safely
        mulu.w  #12,d0
        lea     0(a1,d0.w),a0
        move.l  (a0)+,d1                ; sample offset
        move.l  (a0)+,d2                ; sample length
        move.w  (a0)+,d3                ; DMA mode ($0080 = 6258 Hz mono)
        cmpi.l  #16,d2
        ble.s   .step_ret               ; 2-byte silence placeholder (samples 4/6/10/11) -> pause 1 VBL (20ms)!
        add.l   a1,d1
        add.l   d1,d2
        clr.b   $ffff8901.w
        move.b  d1,$ffff8907.w
        lsr.l   #8,d1
        move.b  d1,$ffff8905.w
        lsr.l   #8,d1
        move.b  d1,$ffff8903.w
        move.b  d2,$ffff8913.w
        lsr.l   #8,d2
        move.b  d2,$ffff8911.w
        lsr.l   #8,d2
        move.b  d2,$ffff890f.w
        move.b  d3,$ffff8921.w
        move.b  #1,$ffff8901.w
        addq.w  #1,STE_DMA_CNT
        bra.s   .step_ret
.step_stop:
        clr.b   $ffff8901.w
        clr.l   STE_SCRIPT_PTR
        clr.w   STE_REPEAT_CNT
        clr.w   $0284aa-$142a
.step_ret:
        movem.l (sp)+,d0-d4/a0-a1
.vbl_done:
        rts

; ---------------------------------------------------------------------------
; ZERO-Blit Sprite List Hooks ($01a426 draw, $01a83e erase)
; Records world-space (a3, src, wx, wy) into STE_SPR_LIST; all actual Blitter
; rendering happens invisibly on the Backbuffer inside ste_pitch_update!
; ---------------------------------------------------------------------------
ste_draw_spr_core:
        ; Input: d0.w = x_scr, d1.w = y_scr, a1 = KO2 3bpp src, a3 = KO2 save record
        ; Caller pushed movem.l d0-d2/d4/d7/a0-a1/a3,-(sp)
        move.l  #1,(a3)                 ; mark entity active for KO2
        add.w   STE_CUR_WX(pc),d0       ; world_x (0..1279)
        add.w   STE_CUR_WY(pc),d1       ; world_y (0..1535)
        lea     STE_SPR_LIST.l,a0
        move.w  STE_SPR_CNT(pc),d2
        beq.s   .dsc_add
        subq.w  #1,d2
.dsc_fnd:
        cmpa.l  (a0),a3
        beq.s   .dsc_upd
        lea     16(a0),a0
        dbra    d2,.dsc_fnd
.dsc_add:
        move.w  STE_SPR_CNT(pc),d2
        cmpi.w  #32,d2
        bcc.s   .dsc_ret
        addq.w  #1,STE_SPR_CNT
        move.l  a3,(a0)
.dsc_upd:
        move.l  a1,4(a0)
        move.w  d0,8(a0)                ; world_x
        move.w  d1,10(a0)               ; world_y
.dsc_ret:
        movem.l (sp)+,d0-d2/d4/d7/a0-a1/a3
        rts

ste_erase_spr:
        ; Input: a3 = KO2 save record
        clr.l   (a3)
        movem.l d0-d1/a0-a1,-(sp)
        move.w  STE_SPR_CNT(pc),d0
        beq.s   .es_ret
        lea     STE_SPR_LIST.l,a0
        move.w  d0,d1
        subq.w  #1,d1
.es_fnd:
        cmpa.l  (a0),a3
        beq.s   .es_rm
        lea     16(a0),a0
        dbra    d1,.es_fnd
        bra.s   .es_ret
.es_rm:
        ; O(1) swap-with-last removal!
        subq.w  #1,d0
        move.w  d0,STE_SPR_CNT
        lsl.w   #4,d0
        lea     STE_SPR_LIST.l,a1
        adda.w  d0,a1                   ; a1 = last valid entry
        cmpa.l  a0,a1
        beq.s   .es_ret
        move.l  (a1)+,(a0)+
        move.l  (a1)+,(a0)+
        move.l  (a1)+,(a0)+
        move.l  (a1)+,(a0)+
.es_ret:
        movem.l (sp)+,d0-d1/a0-a1
        rts

; ---------------------------------------------------------------------------
; ste_pitch_update ($01c1d0): True Double-Buffered Frame Render + Atomic Swap!
; ---------------------------------------------------------------------------
ste_pitch_update:
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

        ; 2. Compute clamped world camera (wx, wy) AND write exact clamped position back to
        ;    KO2's -$1112(a4) / -$110e(a4) so STE_CUR_WX - (-$1112) == +176 and
        ;    STE_CUR_WY - (-$110e) == +64 IDENTICALLY at all 4 pitch edges (0px sprite drift!)
        movem.l d0-d7/a0-a3/a5-a6,-(sp)
        move.w  -$1112(a4),d0
        addi.w  #176,d0
        bge.s   .wx_lo
        moveq   #0,d0
        move.l  #$ff500000,-$1112(a4)   ; clamp KO2 cam_x = -176.0 (exact left edge!)
        bra.s   .wx_ok
.wx_lo: cmpi.w  #960,d0
        ble.s   .wx_ok
        move.w  #960,d0
        move.l  #$03100000,-$1112(a4)   ; clamp KO2 cam_x = +784.0 (exact right edge!)
.wx_ok:
        move.w  -$110e(a4),d1
        addi.w  #64,d1
        bge.s   .wy_lo
        moveq   #0,d1
        move.l  #$ffc00000,-$110e(a4)   ; clamp KO2 cam_y = -64.0 (exact top edge!)
        bra.s   .wy_ok
.wy_lo: cmpi.w  #1336,d1                ; 1536 - 200 = 1336 (full 320x200 bottom behind-goal view!)
        ble.s   .wy_ok
        move.w  #1336,d1
        move.l  #$04f80000,-$110e(a4)   ; clamp KO2 cam_y = +1272.0 (exact bottom edge!)
.wy_ok:
        move.w  d0,STE_CUR_WX
        move.w  d1,STE_CUR_WY

        ; Call KO2's off-screen goal arrow updater ($01bffa) BEFORE drawing Backbuffer!
        movem.l d0-d1,-(sp)
        jsr     $01bffa.l
        movem.l (sp)+,d0-d1

        ; If returning from Half-Time/Stats screen ($078000 was overwritten), reset cleanly!
        tst.w   STE_STATS_DIRTY
        beq.s   .pu_clean
        clr.w   STE_STATS_DIRTY
        bsr.w   ste_reset_bufs
        moveq   #4,d0
        trap    #8
        move.w  STE_CUR_WX(pc),d0
        move.w  STE_CUR_WY(pc),d1
.pu_clean:
        ; d2 = tx = wx >> 4 (0..60), d3 = ty = wy >> 4 (0..83), d7 = hscr = wx & 15
        move.w  d0,d2
        lsr.w   #4,d2
        move.w  d1,d3
        lsr.w   #4,d3
        move.w  d0,d7
        andi.w  #15,d7
        move.w  d7,STE_BK_HSCR

        ; Compute y0 = wy % 208 -> d4.w
        moveq   #0,d4
        move.w  d1,d4
        divu.w  #RING_H,d4
        swap    d4                      ; d4.w = y0 (0..207)
        move.w  d4,STE_BK_Y0
        move.w  d2,d5
        lsl.w   #3,d5
        ext.l   d5
        move.l  d5,STE_BK_TX8

        ; Select INVISIBLE Backbuffer descriptor a6 = (STE_SHOW_IDX == 0) ? DB_B : DB_A
        lea     DB_B(pc),a6
        tst.w   STE_SHOW_IDX
        beq.s   .pu_got_bk
        lea     DB_A(pc),a6
.pu_got_bk:
        ; === STEP A: Strict Reverse-LIFO Erase of Backbuffer's old HUD + Sprites + Radar ===
        bsr.w   ste_bk_erase_hud
        bsr.w   ste_bk_erase_spr
        bsr.w   ste_bk_erase_rad

        ; === STEP B: Update Backbuffer's Dirty Edge Tiles (14 rows x 21 cols, UNMIRRORED!) ===
        move.w  d2,d5
        sub.w   DB_TX(a6),d5            ; dtx
        move.w  d3,d6
        sub.w   DB_TY(a6),d6            ; dty
        move.w  d5,d0
        bpl.s   .adx
        neg.w   d0
.adx:   cmpi.w  #3,d0
        bgt.w   .bk_full
        move.w  d6,d0
        bpl.s   .ady
        neg.w   d0
.ady:   cmpi.w  #3,d0
        bgt.w   .bk_full

        ; Incremental dirty-edge columns & rows on Backbuffer (a6 = DB_*)
        tst.w   d5
        beq.s   .bk_chky
        bgt.s   .bk_sr
        ; Scrolled left: fill columns d2 .. DB_TX-1
        move.w  d2,d0
.bk_sl: bsr.w   ste_bk_draw_col         ; d0=tx_col, d3=ty_top, a6=DB
        addq.w  #1,d0
        cmp.w   DB_TX(a6),d0
        blt.s   .bk_sl
        bra.s   .bk_chky
.bk_sr:
        ; Scrolled right: fill columns DB_TX+21 .. d2+20
        move.w  DB_TX(a6),d0
        addi.w  #21,d0
        move.w  d2,d1
        addi.w  #20,d1
.bk_srl: bsr.w  ste_bk_draw_col
        addq.w  #1,d0
        cmp.w   d1,d0
        ble.s   .bk_srl

.bk_chky:
        tst.w   d6
        beq.s   .bk_tiles_ok
        bgt.s   .bk_sd
        ; Scrolled up: fill rows d3 .. DB_TY-1
        move.w  d3,d0
.bk_su: bsr.w   ste_bk_draw_row         ; d2=tx_left, d0=ty_row, a6=DB
        addq.w  #1,d0
        cmp.w   DB_TY(a6),d0
        blt.s   .bk_su
        bra.s   .bk_tiles_ok
.bk_sd:
        ; Scrolled down: fill rows DB_TY+14 .. d3+13 (14 rows covers 200px @ any wy%16!)
        move.w  DB_TY(a6),d0
        addi.w  #RING_ROWS,d0
        move.w  d3,d1
        addi.w  #(RING_ROWS-1),d1
.bk_sdl: bsr.w  ste_bk_draw_row
        addq.w  #1,d0
        cmp.w   d1,d0
        ble.s   .bk_sdl
        bra.s   .bk_tiles_ok

.bk_full:
        ; Full 21x14 tile fill onto Backbuffer
        move.w  d3,d0
        moveq   #(RING_ROWS-1),d1
.bk_fy: bsr.w   ste_bk_draw_row
        addq.w  #1,d0
        dbra    d1,.bk_fy

.bk_tiles_ok:
        move.w  d2,DB_TX(a6)
        move.w  d3,DB_TY(a6)

        ; === STEP C: Draw Transparent Vector Radar + 23 Dots + Active Player Underlines onto Backbuffer ===
        bsr.w   ste_bk_draw_rad
        bsr.w   ste_bk_draw_ul

        ; === STEP D: Draw ALL Active Sprites + Transparent Bottom HUD onto Backbuffer ===
        bsr.w   ste_bk_draw_spr
        bsr.w   ste_bk_draw_hud

        ; === STEP E: Compute Display Params & Atomically Swap Front <-> Back! ===
        move.l  DB_RING(a6),d0
        add.l   STE_BK_TX8(pc),d0       ; d0 = RING + tx*8 (row 0)
        move.l  d0,DB_WRAP(a6)          ; wrap_addr = RING + tx*8
        move.w  STE_BK_Y0(pc),d1
        move.w  d1,d4
        mulu.w  #RING_STRIDE,d1
        add.l   d0,d1
        move.l  d1,DB_START(a6)         ; start_addr = RING + y0*168 + tx*8
        move.w  #RING_H,d1
        sub.w   d4,d1                   ; wrap_y = 224 - y0 (1..224)
        move.l  d0,d3
        addi.l  #(RING_BYTES-8),d3      ; d3.w = (RING + 224*168 + tx*8 - 8) & $ffff
        ; Always mirror visible Row 0 -> Row 224 whenever a ring wrap is on-screen (wrap_y <= 200)
        cmpi.w  #PITCH_VIS_H,d1
        bgt.s   .pu_wyok
        movea.l d0,a0                   ; src = RING + tx*8 (row 0)
        movea.l d0,a1
        adda.l  #RING_BYTES,a1          ; dst = RING + 224*168 + tx*8 (row 224)
        moveq   #41,d2                  ; 42 longs = 168 bytes (1 full scanline)
.pu_m0: move.l  (a0)+,(a1)+
        dbra    d2,.pu_m0
        cmpi.w  #1,d1
        bne.s   .pu_wyok
        ; y0 == 223 (wrap_y == 1): Row 224 now mirrors Row 0 -> wrap at line 2 to Row 1!
        addi.l  #RING_STRIDE,d0         ; wrap_addr = RING + 168 + tx*8 (row 1)
        move.l  d0,DB_WRAP(a6)
        addi.w  #RING_STRIDE,d3         ; target advances by 1 line (end of Row 224!)
        moveq   #2,d1                   ; wrap_y = 2!
.pu_wyok:
        move.w  d3,DB_WTGT(a6)
        move.w  d1,DB_WRAPY(a6)
        move.w  STE_BK_HSCR(pc),DB_HSCR(a6)

        ; ATOMIC 1-instruction Front <-> Back buffer flip!
        eori.w  #1,STE_SHOW_IDX

        movem.l (sp)+,d0-d7/a0-a3/a5-a6
        rts

; Helpers: draw 1 row (d2=tx_left, d0=ty_row, a6=DB) or 1 col (d0=tx_col, d3=ty_top, a6=DB)
ste_bk_draw_row:
        cmpi.w  #96,d0
        bcc.s   .bdr_ret
        movem.l d0-d2/a0,-(sp)
        move.w  d2,d1                   ; d1 = tx_left
        move.w  d0,d2                   ; d2 = ty_row
        movea.l DB_RING(a6),a0          ; a0 = RING_BASE
        moveq   #8,d0                   ; cmd 8 = unmirrored 21-tile row blit
        trap    #8
        movem.l (sp)+,d0-d2/a0
.bdr_ret:
        rts

ste_bk_draw_col:
        cmpi.w  #80,d0
        bcc.s   .bdc_ret
        movem.l d0-d2/a0,-(sp)
        move.w  d0,d1                   ; d1 = tx_col
        move.w  d3,d2                   ; d2 = ty_top
        movea.l DB_RING(a6),a0          ; a0 = RING_BASE
        moveq   #9,d0                   ; cmd 9 = unmirrored 13-tile col blit
        trap    #8
        movem.l (sp)+,d0-d2/a0
.bdc_ret:
        rts

; ---------------------------------------------------------------------------
; Step A: Reverse-LIFO Erase of Backbuffer's old HUD, Sprites & Radar (ZERO overlap checks!)
; ---------------------------------------------------------------------------
ste_bk_erase_hud:
        tst.w   DB_HUD_H1(a6)
        beq.s   .beh_ret
        movem.l d0/d2-d3/a0-a1,-(sp)
        move.w  DB_HUD_H2(a6),d2
        swap    d2
        move.w  DB_HUD_H1(a6),d2        ; d2 = (h2<<16) | h1
        clr.w   DB_HUD_H1(a6)
        movea.l DB_HUD_T(a6),a0         ; a0 = dst_top
        movea.l DB_HUDSAV(a6),a1        ; a1 = HUD save-under
        move.l  DB_HUD_B(a6),d3         ; d3 = dst_bot (or 0)
        moveq   #10,d0                  ; cmd 10 = restore HUD save-under
        trap    #8
        movem.l (sp)+,d0/d2-d3/a0-a1
.beh_ret:
        rts

ste_bk_draw_hud:
        movem.l d0-d5/a0-a1,-(sp)
        ; Compute yr = (y0 + HUD_SCR_Y) % RING_H
        move.w  STE_BK_Y0(pc),d1
        addi.w  #HUD_SCR_Y,d1
        cmpi.w  #RING_H,d1
        blt.s   .bdh_yr
        subi.w  #RING_H,d1
.bdh_yr:
        move.w  d1,d4
        mulu.w  #RING_STRIDE,d4
        add.l   STE_BK_TX8(pc),d4
        movea.l DB_RING(a6),a0
        adda.l  d4,a0                   ; a0 = dst_top
        ; Check if yr + 16 > RING_H (crosses 224 -> 0 ring seam!)
        move.w  d1,d4
        addi.w  #16,d4
        cmpi.w  #RING_H,d4
        ble.s   .bdh_nowr
        move.w  #RING_H,d4
        sub.w   d1,d4                   ; d4 = h1 (1..15)
        moveq   #16,d5
        sub.w   d4,d5                   ; d5 = h2 (1..15)
        move.l  DB_RING(a6),d3
        add.l   STE_BK_TX8(pc),d3       ; d3 = dst_bot
        bra.s   .bdh_go
.bdh_nowr:
        moveq   #16,d4                  ; h1 = 16
        moveq   #0,d5                   ; h2 = 0
        moveq   #0,d3                   ; dst_bot = 0
.bdh_go:
        move.l  a0,DB_HUD_T(a6)
        move.l  d3,DB_HUD_B(a6)
        move.w  d4,DB_HUD_H1(a6)
        move.w  d5,DB_HUD_H2(a6)
        movea.l DB_HUDSAV(a6),a1        ; a1 = HUD save-under
        move.w  STE_BK_HSCR(pc),d1      ; d1 = hscr (0..15)
        move.w  d5,d2
        swap    d2
        move.w  d4,d2                   ; d2 = (h2<<16) | h1
        moveq   #11,d0                  ; cmd 11 = save-under + transparent HUD composite!
        trap    #8
        movem.l (sp)+,d0-d5/a0-a1
        rts

ste_bk_erase_spr:
        move.w  DB_SCNT(a6),d1
        beq.s   .bes_ret
        clr.w   DB_SCNT(a6)
        movem.l d0-d1/a0-a1,-(sp)
        move.w  d1,d0
        lsl.w   #4,d0
        movea.l DB_STK(a6),a0
        adda.w  d0,a0                   ; a0 = end of Backbuffer's sprite restore stack
        movea.l DB_SAV(a6),a1           ; a1 = Backbuffer's save-under bank base
        moveq   #2,d0                   ; cmd 2 = reverse-LIFO restore of d1 records
        trap    #8
        movem.l (sp)+,d0-d1/a0-a1
.bes_ret:
        rts

ste_bk_erase_rad:
        movem.l d0-d2/a0-a2,-(sp)
        ; 1. Restore Backbuffer's old radar dots (reverse LIFO)
        move.w  DB_RDCNT(a6),d0
        beq.s   .ber_nod
        clr.w   DB_RDCNT(a6)
        move.w  d0,d1
        mulu.w  #12,d0
        movea.l DB_RDR(a6),a0
        adda.l  d0,a0
        subq.w  #1,d1
.ber_dl:
        lea     -12(a0),a0
        movea.l (a0),a1
        move.l  4(a0),(a1)
        move.l  8(a0),4(a1)
        dbra    d1,.ber_dl
.ber_nod:
        ; 2. Restore Backbuffer's old radar lines (batched cmd 6)
        move.w  DB_RLCNT(a6),d2
        beq.s   .ber_ret
        clr.w   DB_RLCNT(a6)
        move.w  d2,d0
        lsl.w   #4,d0
        movea.l DB_RLR(a6),a2
        adda.w  d0,a2
        moveq   #6,d0                   ; cmd 6 = batch-restore d2 line records ending at a2
        trap    #8
.ber_ret:
        movem.l (sp)+,d0-d2/a0-a2
        rts

; ---------------------------------------------------------------------------
; Step C: Draw Transparent Vector Radar + 23 Dots onto Backbuffer (ring-wrap aware!)
; ---------------------------------------------------------------------------
ste_bk_draw_rad:
        tst.w   -$0e10(a4)              ; Radar ON (> 0)?
        ble.w   .bdr_done_ret
        move.w  -$0e0a(a4),d6           ; Radar scale (8, 12, 16, 20, 24)
        ble.w   .bdr_done_ret
        movem.l d0-d7/a0-a3/a5,-(sp)
        ; Rebuild pre-scaled line cache ONLY when scale changes!
        cmp.w   STE_RAD_C_SC(pc),d6
        beq.s   .rc_ok
        move.w  d6,STE_RAD_C_SC
        lea     -$4d78(a4),a3
        lea     STE_RAD_CACHE.l,a0
        moveq   #0,d7
.rc_hl: move.w  (a3)+,d0
        blt.s   .rc_hd
        move.w  (a3)+,d1
        move.w  (a3)+,d2
        ext.l   d0
        divs.w  d6,d0
        add.w   -$0e0e(a4),d0
        move.w  d0,(a0)+
        ext.l   d1
        divs.w  d6,d1
        add.w   -$0e0c(a4),d1
        move.w  d1,(a0)+
        ext.l   d2
        divs.w  d6,d2
        add.w   -$0e0e(a4),d2
        move.w  d2,(a0)+
        addq.w  #1,d7
        bra.s   .rc_hl
.rc_hd: move.w  d7,STE_RAD_C_HCNT
        moveq   #0,d7
.rc_vl: move.w  (a3)+,d0
        blt.s   .rc_vd
        move.w  (a3)+,d1
        move.w  (a3)+,d2
        ext.l   d0
        divs.w  d6,d0
        add.w   -$0e0e(a4),d0
        move.w  d0,(a0)+
        ext.l   d1
        divs.w  d6,d1
        add.w   -$0e0c(a4),d1
        move.w  d1,(a0)+
        ext.l   d2
        divs.w  d6,d2
        add.w   -$0e0c(a4),d2
        move.w  d2,(a0)+
        addq.w  #1,d7
        bra.s   .rc_vl
.rc_vd: move.w  d7,STE_RAD_C_VCNT
.rc_ok:
        lea     STE_RAD_CACHE.l,a3
        movea.l DB_RLR(a6),a2           ; line restore record cursor (max 28)
        movea.l DB_RPOOL(a6),a5         ; radar save pool cursor (2,048B safe for both A & B!)
        move.l  a5,d0
        addi.l  #2040,d0
        move.l  d0,STE_BK_REND
        moveq   #0,d7                   ; line record count

        ; Horizontal radar lines
        move.w  STE_RAD_C_HCNT(pc),d6
        beq.s   .br_vs
        subq.w  #1,d6
.br_hl: move.w  (a3)+,d0
        move.w  (a3)+,d1
        move.w  (a3)+,d2
        bsr.s   .br_hline
        dbra    d6,.br_hl

        ; Vertical radar lines (ring-wrap aware!)
.br_vs: move.w  STE_RAD_C_VCNT(pc),d6
        beq.s   .br_blt
        subq.w  #1,d6
.br_vl: move.w  (a3)+,d0
        move.w  (a3)+,d1
        move.w  (a3)+,d2
        bsr.w   .br_vline
        dbra    d6,.br_vl

.br_blt:
        move.w  d7,DB_RLCNT(a6)
        beq.s   .br_dots
        movea.l DB_RLR(a6),a0
        move.w  d7,d1
        moveq   #7,d0                   ; cmd 7 = batch save+draw transparent black lines!
        trap    #8
.br_dots:
        bsr.w   ste_bk_draw_dots
        movem.l (sp)+,d0-d7/a0-a3/a5
.bdr_done_ret:
        rts

; Horizontal radar line: d0=sx1, d1=sy, d2=sx2 -> ring-wrapped dst in DB_RING(a6)
.br_hline:
        cmpi.w  #PITCH_VIS_H,d1
        bcc.s   .bh_ret
        cmpi.w  #28,d7
        bcc.s   .bh_ret
        add.w   STE_BK_HSCR(pc),d0
        add.w   STE_BK_HSCR(pc),d2
        move.w  d0,d3
        andi.w  #15,d3
        move.w  #$ffff,d4
        lsr.w   d3,d4                   ; ENDMASK1
        move.w  d2,d3
        andi.w  #15,d3
        moveq   #15,d5
        sub.w   d3,d5
        move.w  #$ffff,d3
        lsl.w   d5,d3                   ; ENDMASK3
        lsr.w   #4,d0
        lsr.w   #4,d2
        sub.w   d0,d2
        blt.s   .bh_ret
        addq.w  #1,d2                   ; word_cols
        cmpi.w  #1,d2
        bne.s   .bh_m2
        and.w   d3,d4
.bh_m2:
        move.w  d2,d5
        lsl.w   #3,d5
        lea     0(a5,d5.w),a0
        cmpa.l  STE_BK_REND(pc),a0
        bhi.s   .bh_ret
        ; Ring line yr = (y0 + sy) % 208
        add.w   STE_BK_Y0(pc),d1
        cmpi.w  #RING_H,d1
        blt.s   .bh_yok
        subi.w  #RING_H,d1
.bh_yok:
        mulu.w  #RING_STRIDE,d1
        lsl.w   #3,d0
        ext.l   d0
        add.l   STE_BK_TX8(pc),d0
        add.l   d0,d1
        movea.l DB_RING(a6),a1
        adda.l  d1,a1
        move.l  a1,(a2)+
        move.l  a5,(a2)+
        move.w  d2,(a2)+
        move.w  #1,(a2)+
        move.w  d4,(a2)+
        move.w  d3,(a2)+
        addq.w  #1,d7
        adda.w  d5,a5
.bh_ret:
        rts

; Vertical radar line (Y_STEP=4, ring-wrap splitting!): d0=sx, d1=sy1, d2=sy2
.br_vline:
        cmpi.w  #320,d0
        bcc.w   .bv_ret
        cmpi.w  #PITCH_VIS_H,d1
        bcc.w   .bv_ret
        cmpi.w  #PITCH_VIS_H,d2
        bcs.s   .bv_y2
        move.w  #(PITCH_VIS_H-1),d2
.bv_y2: sub.w   d1,d2
        blt.w   .bv_ret
        addq.w  #4,d2
        lsr.w   #2,d2                   ; d2 = total dots (Y_STEP=4)
        add.w   STE_BK_HSCR(pc),d0
        move.w  d0,d3
        andi.w  #15,d3
        moveq   #15,d5
        sub.w   d3,d5
        moveq   #0,d4
        bset    d5,d4                   ; ENDMASK1 = ENDMASK3 = single bit
        lsr.w   #4,d0
        lsl.w   #3,d0
        ext.l   d0
        add.l   STE_BK_TX8(pc),d0       ; d0.l = x_byte_off
        ; yr1 = (y0 + sy1) % 208
        add.w   STE_BK_Y0(pc),d1
        cmpi.w  #RING_H,d1
        blt.s   .bv_yr1
        subi.w  #RING_H,d1
.bv_yr1:
        ; Check if yr1 + (d2-1)*4 >= 208 (crosses ring seam!)
        move.w  d2,d3
        subq.w  #1,d3
        lsl.w   #2,d3
        add.w   d1,d3
        cmpi.w  #RING_H,d3
        blt.s   .bv_one
        ; Split into top segment (yr1..207) and bottom segment (wrapped..)!
        move.w  #(RING_H-1),d3
        sub.w   d1,d3
        lsr.w   #2,d3
        addq.w  #1,d3                   ; d3 = cnt1
        move.w  d2,d5
        sub.w   d3,d5                   ; d5 = cnt2
        move.w  d5,-(sp)
        move.w  d3,d5
        lsl.w   #2,d5
        add.w   d1,d5
        subi.w  #RING_H,d5              ; d5 = yr2 (0..3)
        move.w  d5,-(sp)
        move.w  d3,d2
        bsr.s   .bv_emit
        move.w  (sp)+,d1                ; yr2
        move.w  (sp)+,d2                ; cnt2
        ble.s   .bv_ret
.bv_one:
        bsr.s   .bv_emit
.bv_ret:
        rts

; Emit 1 vertical radar segment: d0.l=x_off, d1.w=yr, d2.w=cnt, d4.w=mask
.bv_emit:
        cmpi.w  #28,d7
        bcc.s   .be_ret
        move.l  STE_BK_REND(pc),d5
        sub.l   a5,d5
        lsr.l   #3,d5
        ble.s   .be_ret
        cmp.w   d5,d2
        ble.s   .be_ok
        move.w  d5,d2
.be_ok: move.w  d1,d3
        mulu.w  #RING_STRIDE,d3
        add.l   d0,d3
        movea.l DB_RING(a6),a1
        adda.l  d3,a1
        move.l  a1,(a2)+
        move.l  a5,(a2)+
        move.w  #1,(a2)+
        move.w  d2,(a2)+
        move.w  d4,(a2)+
        move.w  d4,(a2)+
        addq.w  #1,d7
        move.w  d2,d5
        lsl.w   #3,d5
        adda.w  d5,a5
.be_ret:
        rts

; Draw 23 transparent 2x1 radar dots onto Backbuffer (ring-wrap aware!)
ste_bk_draw_dots:
        movea.l DB_RDR(a6),a2
        moveq   #0,d7
        movea.l -$5012(a4),a5           ; Home 11 players
        moveq   #10,d5
        moveq   #2,d4                   ; orange
        bsr.s   .bd_team
        movea.l -$4fbc(a4),a5           ; Away 11 players
        moveq   #10,d5
        moveq   #4,d4                   ; red
        bsr.s   .bd_team
        move.w  -$0e14(a4),d0
        blt.s   .bd_done
        move.w  -$0e12(a4),d1
        moveq   #0,d4                   ; white ball
        bsr.s   .bd_dot
.bd_done:
        move.w  d7,DB_RDCNT(a6)
        rts

.bd_team:
        tst.w   $0c(a5)
        beq.s   .bdt_n
        move.w  $20(a5),d0
        blt.s   .bdt_n
        move.w  $22(a5),d1
        bsr.s   .bd_dot
.bdt_n: lea     $186(a5),a5
        dbra    d5,.bd_team
        rts

.bd_dot:
        cmpi.w  #318,d0
        bcc.s   .bdd_r
        cmpi.w  #PITCH_VIS_H,d1
        bcc.s   .bdd_r
        cmpi.w  #48,d7
        bcc.s   .bdd_r
        add.w   STE_BK_HSCR(pc),d0
        move.w  d0,d2
        andi.w  #15,d2
        move.w  #$c000,d3
        lsr.w   d2,d3
        lsr.w   #4,d0
        lsl.w   #3,d0
        ext.l   d0
        add.l   STE_BK_TX8(pc),d0
        add.w   STE_BK_Y0(pc),d1
        cmpi.w  #RING_H,d1
        blt.s   .bdd_y
        subi.w  #RING_H,d1
.bdd_y: mulu.w  #RING_STRIDE,d1
        add.l   d0,d1
        movea.l DB_RING(a6),a0
        adda.l  d1,a0
        move.w  d3,d0
        not.w   d0
        move.l  a0,(a2)+
        move.l  (a0),(a2)+
        move.l  4(a0),(a2)+
        addq.w  #1,d7
        and.w   d0,(a0)
        and.w   d0,2(a0)
        and.w   d0,4(a0)
        or.w    d3,6(a0)
        tst.w   d4
        beq.s   .bdd_r
        cmpi.w  #2,d4
        bne.s   .bdd_c4
        or.w    d3,2(a0)
        rts
.bdd_c4:
        or.w    d3,4(a0)
.bdd_r: rts

; ---------------------------------------------------------------------------
; Active Controlled Player Black Underline (16x1 solid $ffff, target dashed $fc3f)
; Appends 1..2 word entries to DB_RDR(a6) -> works even with Radar OFF, ring-wrap aware!
; ---------------------------------------------------------------------------
ste_bk_draw_ul:
        movem.l d0-d4/d7/a0/a2/a5,-(sp)
        move.w  DB_RDCNT(a6),d7
        move.w  d7,d0
        mulu.w  #12,d0
        movea.l DB_RDR(a6),a2
        adda.l  d0,a2
        ; 1. Home active player (-$5012(a4) -> $12!=0 -> $16=a5)
        lea     -$5012(a4),a0
        tst.l   $12(a0)
        beq.s   .ul_away
        movea.l $16(a0),a5
        move.w  #$ffff,d4
        bsr.s   .ul_one
.ul_away:
        ; 2. Away active player (-$4fbc(a4) -> $12!=0 -> $16=a5)
        lea     -$4fbc(a4),a0
        tst.l   $12(a0)
        beq.s   .ul_dash
        movea.l $16(a0),a5
        move.w  #$ffff,d4
        bsr.s   .ul_one
.ul_dash:
        ; 3. Secondary / pass-target dashed underline ($fc3f)
        move.l  STE_UL_DASH(pc),d0
        beq.s   .ul_done
        clr.l   STE_UL_DASH
        movea.l d0,a5
        move.w  #$fc3f,d4
        bsr.s   .ul_one
.ul_done:
        move.w  d7,DB_RDCNT(a6)
        movem.l (sp)+,d0-d4/d7/a0/a2/a5
        rts

.ul_one:
        tst.l   $b8(a5)                 ; KO2 sprite active / on-screen?
        beq.w   .ul_ret
        cmpi.w  #46,d7                  ; room for up to 2 words in 48-entry DB_RDR?
        bcc.w   .ul_ret
        move.w  (a5),d0                 ; world_x = (a5) + 176 - 8 = (a5) + 168
        addi.w  #168,d0
        sub.w   STE_CUR_WX(pc),d0       ; scr_x (0..304)
        cmpi.w  #305,d0
        bcc.s   .ul_ret
        move.w  4(a5),d1                ; world_y = 4(a5) + 64 + 8 = 4(a5) + 72
        addi.w  #72,d1
        sub.w   STE_CUR_WY(pc),d1       ; scr_y (0..180)
        cmpi.w  #PITCH_VIS_H,d1
        bcc.s   .ul_ret
        add.w   STE_BK_HSCR(pc),d0
        move.w  d0,d2
        andi.w  #15,d2                  ; skew (0..15)
        moveq   #0,d3
        move.w  d4,d3
        swap    d3
        lsr.l   d2,d3                   ; d3.high = word0 mask, d3.low = word1 mask
        lsr.w   #4,d0
        lsl.w   #3,d0
        ext.l   d0
        add.l   STE_BK_TX8(pc),d0
        add.w   STE_BK_Y0(pc),d1
        cmpi.w  #RING_H,d1
        blt.s   .ul_y
        subi.w  #RING_H,d1
.ul_y:  mulu.w  #RING_STRIDE,d1
        add.l   d0,d1
        movea.l DB_RING(a6),a0
        adda.l  d1,a0
        ; Emit left word (word0) in col 9 (pure jet black: P0=1, P1=0, P2=0, P3=1)
        swap    d3
        tst.w   d3
        beq.s   .ul_w2
        bsr.s   .ul_put
.ul_w2: swap    d3
        tst.w   d3
        beq.s   .ul_ret
        addq.l  #8,a0
.ul_put:
        move.w  d3,d0
        not.w   d0
        move.l  a0,(a2)+
        move.l  (a0),(a2)+
        move.l  4(a0),(a2)+
        addq.w  #1,d7
        or.w    d3,(a0)
        and.w   d0,2(a0)
        and.w   d0,4(a0)
        or.w    d3,6(a0)
.ul_ret:
        rts

; ---------------------------------------------------------------------------
; Step D: Draw ALL Active Sprites from STE_SPR_LIST onto Backbuffer!
; Exact world-to-ring projection, clean y=181 clipping, and 208->0 seam split!
; ZERO beam waits! ZERO overlap chains! ZERO flicker!
; ---------------------------------------------------------------------------
ste_bk_draw_spr:
        move.w  STE_SPR_CNT(pc),d7
        beq.w   .bds_ret
        movem.l d0-d7/a0-a3/a5,-(sp)
        lea     STE_SPR_LIST.l,a5       ; active sprite source list
        movea.l DB_STK(a6),a3           ; Backbuffer restore stack write cursor
        moveq   #0,d6                   ; slot_idx & drawn count (0..31)
        subq.w  #1,d7
.bds_lp:
        ; Check vertical visibility: scr_y = world_y - STE_CUR_WY in [0 .. PITCH_VIS_H-1]
        move.w  10(a5),d1               ; world_y
        sub.w   STE_CUR_WY(pc),d1       ; scr_y
        blt.w   .bds_nxt
        cmpi.w  #PITCH_VIS_H,d1
        bge.w   .bds_nxt
        ; Clip height h = min(16, PITCH_VIS_H - scr_y)
        move.w  #PITCH_VIS_H,d3
        sub.w   d1,d3
        cmpi.w  #16,d3
        ble.s   .bds_hok
        moveq   #16,d3                  ; d3 = h (1..16)
.bds_hok:
        ; Check horizontal visibility: rel_col = (world_x >> 4) - DB_TX in [0 .. 19]
        move.w  8(a5),d0                ; world_x
        move.w  d0,d2
        andi.w  #15,d2                  ; d2 = skew (0..15)
        lsr.w   #4,d0                   ; world_col (0..79)
        move.w  d0,d4
        sub.w   DB_TX(a6),d4            ; rel_col
        blt.w   .bds_nxt
        cmpi.w  #20,d4                  ; allow up to col 20 (skew=0 fits in col 20)
        bgt.w   .bds_nxt
        bne.s   .bds_xok
        tst.w   d2
        bne.w   .bds_nxt                ; col 20 with skew > 0 would touch col 21 -> skip!
.bds_xok:
        ; Compute yr = (y0 + scr_y) % 208
        add.w   STE_BK_Y0(pc),d1
        cmpi.w  #RING_H,d1
        blt.s   .bds_yr
        subi.w  #RING_H,d1
.bds_yr:
        ; Compute x_byte_off = world_col * 8 -> d0.l
        lsl.w   #3,d0
        ext.l   d0
        ; Compute dst_top = RING_BASE + yr * 168 + world_col * 8 -> a0
        move.w  d1,d4
        mulu.w  #RING_STRIDE,d4
        add.l   d0,d4
        movea.l DB_RING(a6),a0
        adda.l  d4,a0                   ; a0 = dst_top

        ; Check if yr + h > RING_H (crosses 208 -> 0 ring seam!)
        move.w  d1,d4
        add.w   d3,d4
        cmpi.w  #RING_H,d4
        ble.s   .bds_nowr
        ; Split at ring seam: h1 = 208 - yr, h2 = h - h1, dst_bot = RING_BASE + world_col * 8
        move.w  #RING_H,d4
        sub.w   d1,d4                   ; d4 = h1 (1..15)
        move.w  d3,d5
        sub.w   d4,d5                   ; d5 = h2 (1..15)
        movea.l DB_RING(a6),a1
        adda.l  d0,a1                   ; a1 = dst_bot
        bra.s   .bds_rec
.bds_nowr:
        move.w  d3,d4                   ; h1 = h
        moveq   #0,d5                   ; h2 = 0
        suba.l  a1,a1                   ; dst_bot = 0
.bds_rec:
        ; Push 16-byte restore record onto Backbuffer's stack (a3):
        ; [+0: dst_top.l, +4: dst_bot.l, +8: h1.w, +10: h2.w, +12: slot_idx.w, +14: pad.w]
        move.l  a0,(a3)+
        move.l  a1,(a3)+
        move.w  d4,(a3)+                ; h1
        move.w  d5,(a3)+                ; h2
        move.w  d6,(a3)+                ; slot_idx
        clr.w   (a3)+

        ; Save-under slot a2 = DB_SAV(a6) + d6 * 256
        move.w  d6,d0
        lsl.w   #8,d0
        ext.l   d0
        movea.l DB_SAV(a6),a2
        adda.l  d0,a2
        addq.w  #1,d6

        ; Call TRAP #8 cmd 3: a0=dst_top, a1=KO2_src, a2=slot, d1=skew, d2=(h2<<16)|h1, d3=dst_bot
        move.l  a1,d3                   ; d3.l = dst_bot (or 0)
        movea.l 4(a5),a1                ; a1 = KO2 3bpp sprite src
        move.w  d2,d1                   ; d1.w = skew (0..15)
        move.w  d5,d2
        swap    d2
        move.w  d4,d2                   ; d2 = (h2<<16) | h1
        moveq   #3,d0
        trap    #8

        cmpi.w  #32,d6
        bcc.s   .bds_done
.bds_nxt:
        lea     16(a5),a5
        dbra    d7,.bds_lp
.bds_done:
        move.w  d6,DB_SCNT(a6)
        movem.l (sp)+,d0-d7/a0-a3/a5
.bds_ret:
        rts

; ---------------------------------------------------------------------------
; TRAP #8 ($a0.w) — Supervisor STE Blitter Dispatcher (Official Shared-Bus $80)
;   cmd 2 : reverse-LIFO restore of d1.w sprite records ending at a0 (a1=SAV_BASE)
;   cmd 3 : save+draw 4bpp masked sprite (a0=dst_top, a1=src, a2=slot, d1=skew, d2=h2|h1, d3=dst_bot)
;   cmd 4 : clear STE_RING_A, STE_RING_B, STE_BLACK_LINE
;   cmd 6 : batch reverse-LIFO restore of d2.w radar line records ending at a2
;   cmd 7 : batch save+draw of d1.w transparent black radar lines at a0
;   cmd 8 : unmirrored 21-tile horizontal row blit (a0=RING_BASE, d1=tx_left, d2=ty_row)
;   cmd 9 : unmirrored 14-tile vertical col blit   (a0=RING_BASE, d1=tx_col, d2=ty_top)
;   cmd 10: restore transparent bottom HUD save-under (a0=dst_top, a1=hud_sav, d2=h2|h1, d3=dst_bot)
;   cmd 11: save-under + composite transparent bottom HUD with 1px black drop-shadow
; ---------------------------------------------------------------------------
ste_trap8_handler:
        cmpi.w  #2,d0
        beq.s   .cmd2_rest_lifo
        cmpi.w  #3,d0
        beq.w   .cmd3_spr
        cmpi.w  #4,d0
        beq.w   .cmd4_clr
        cmpi.w  #6,d0
        beq.w   .cmd6_rad_rest
        cmpi.w  #7,d0
        beq.w   .cmd7_rad_draw
        cmpi.w  #8,d0
        beq.w   .cmd8_blit_row
        cmpi.w  #9,d0
        beq.w   .cmd9_blit_col
        cmpi.w  #10,d0
        beq.w   .cmd10_hud_rest
        bra.w   .cmd11_hud_draw

; Official Atari STE Shared-Bus ($80) Blitter trigger: yields every 64 cycles (8 us)
; so 1-line-early HBlank-locked Timer B NEVER misses HBlank, and bset #7 NEVER stalls!
.blt80: move.b  #$80,BLT_LINE.w
.b80_w: bset    #7,BLT_LINE.w
        nop
        bne.s   .b80_w
        rts

; --- cmd 2: Batched Reverse-LIFO sprite restore (d1.w records ending at a0, a1=SAV_BASE) ---
.cmd2_rest_lifo:
        movem.l d2-d3,-(sp)
        move.w  #2,BLT_SRC_XINC.w
        move.w  #2,BLT_SRC_YINC.w
        move.w  #2,BLT_DST_XINC.w
        move.w  #(RING_STRIDE-14),BLT_DST_YINC.w
        moveq   #-1,d0
        move.l  d0,BLT_ENDMASK1.w
        move.w  d0,BLT_ENDMASK3.w
        move.w  #8,BLT_XCOUNT.w
        move.w  #$0203,BLT_HOP.w
        clr.b   BLT_SKEW.w
        subq.w  #1,d1
.c2_lp: lea     -16(a0),a0
        move.w  12(a0),d0               ; slot_idx (0..31)
        lsl.w   #8,d0
        ext.l   d0
        add.l   a1,d0                   ; slot_addr
        move.l  d0,BLT_SRC_ADDR.w
        move.l  (a0),BLT_DST_ADDR.w     ; dst_top
        move.w  8(a0),d2                ; h1
        move.w  d2,BLT_YCOUNT.w
        bsr.w   .blt80
        move.w  10(a0),d3               ; h2 (wrap bottom segment?)
        beq.s   .c2_nxt
        ; Note: BLT_SRC_ADDR already points right after h1*16 bytes in slot!
        move.l  4(a0),BLT_DST_ADDR.w    ; dst_bot
        move.w  d3,BLT_YCOUNT.w
        bsr.w   .blt80
.c2_nxt:
        dbra    d1,.c2_lp
        movem.l (sp)+,d2-d3
        rte

; --- cmd 3: Save-under + Direct NFSR 4bpp Masked Sprite Draw (ring-seam & clip aware!) ---
; a0=dst_top, a1=KO2_src, a2=slot, d1.w=skew, d2.l=(h2<<16)|h1, d3.l=dst_bot
.cmd3_spr:
        movem.l d2-d5/a3-a5,-(sp)
        movea.l a0,a4                   ; a4 = dst_top
        movea.l a2,a5                   ; a5 = slot
        ; 1. Build 16-word 1bpp sprite mask in STE_MASK_BUF (Shared-Bus $80 -> ZERO Hog blits in live play!)
        lea     STE_MASK_BUF.l,a3
        moveq   #-1,d0
        move.l  d0,BLT_ENDMASK1.w
        move.w  d0,BLT_ENDMASK3.w
        clr.w   BLT_SRC_XINC.w
        move.w  #$78,BLT_SRC_YINC.w
        clr.w   BLT_DST_XINC.w
        move.w  #2,BLT_DST_YINC.w
        move.w  #1,BLT_XCOUNT.w
        clr.b   BLT_SKEW.w
        move.w  #$0203,BLT_HOP.w
        move.l  a1,BLT_SRC_ADDR.w
        move.l  a3,BLT_DST_ADDR.w
        move.w  #16,BLT_YCOUNT.w
        bsr.w   .blt80
        move.w  #$0207,BLT_HOP.w
        lea     $28(a1),a2
        move.l  a2,BLT_SRC_ADDR.w
        move.l  a3,BLT_DST_ADDR.w
        move.w  #16,BLT_YCOUNT.w
        bsr.w   .blt80
        lea     $28(a2),a2
        move.l  a2,BLT_SRC_ADDR.w
        move.l  a3,BLT_DST_ADDR.w
        move.w  #16,BLT_YCOUNT.w
        bsr.w   .blt80

        ; 2. Draw Top segment (a4=dst_top, a1=src, a5=slot, a3=mask, d4=h1, d1=skew)
        move.w  d2,d4                   ; d4 = h1 (1..16)
        bsr.s   .c3_seg
        ; 3. Draw Bottom wrap segment if h2 > 0!
        swap    d2
        tst.w   d2
        beq.s   .c3_done
        move.w  d4,d0
        mulu.w  #$78,d0
        adda.l  d0,a1                   ; advance src by h1 lines
        move.w  d4,d0
        lsl.w   #4,d0
        adda.w  d0,a5                   ; advance slot by h1*16 bytes
        move.w  d4,d0
        add.w   d0,d0
        adda.w  d0,a3                   ; advance mask by h1*2 bytes
        movea.l d3,a4                   ; a4 = dst_bot
        move.w  d2,d4                   ; d4 = h2
        bsr.s   .c3_seg
.c3_done:
        movem.l (sp)+,d2-d5/a3-a5
        rte

; Helper: save-under + masked 4bpp draw of d4 lines (a4=dst, a1=src, a5=slot, a3=mask, d1=skew)
.c3_seg:
        ; A. Save-under (a4 -> a5, d4 lines x 8 words)
        moveq   #-1,d0
        move.l  d0,BLT_ENDMASK1.w
        move.w  d0,BLT_ENDMASK3.w
        move.l  a4,BLT_SRC_ADDR.w
        move.l  a5,BLT_DST_ADDR.w
        move.w  #2,BLT_SRC_XINC.w
        move.w  #(RING_STRIDE-14),BLT_SRC_YINC.w
        move.w  #2,BLT_DST_XINC.w
        move.w  #2,BLT_DST_YINC.w
        move.w  #8,BLT_XCOUNT.w
        move.w  d4,BLT_YCOUNT.w
        move.w  #$0203,BLT_HOP.w
        clr.b   BLT_SKEW.w
        bsr.w   .blt80

        ; B. Configure skew
        tst.w   d1
        bne.s   .c3s_sk
        move.w  #1,BLT_XCOUNT.w
        clr.w   BLT_DST_XINC.w
        move.w  #RING_STRIDE,BLT_DST_YINC.w
        clr.b   BLT_SKEW.w
        bra.s   .c3s_m
.c3s_sk:
        move.w  #$ffff,d0
        lsr.w   d1,d0
        move.w  d0,BLT_ENDMASK1.w
        not.w   d0
        move.w  d0,BLT_ENDMASK3.w
        move.w  #2,BLT_XCOUNT.w
        move.w  #8,BLT_DST_XINC.w
        move.w  #(RING_STRIDE-8),BLT_DST_YINC.w
        move.b  d1,d0
        ori.b   #$40,d0                 ; NFSR = 1
        move.b  d0,BLT_SKEW.w
.c3s_m:
        ; Pass 1: Clear mask holes in planes 0, 1, 2 (~SRC & DST, Shared-Bus $80 -> <= 8 us TB latency!)
        clr.w   BLT_SRC_XINC.w
        move.w  #2,BLT_SRC_YINC.w
        move.w  #$0204,BLT_HOP.w
        move.l  a3,BLT_SRC_ADDR.w
        move.l  a4,BLT_DST_ADDR.w
        move.w  d4,BLT_YCOUNT.w
        bsr.w   .blt80
        move.l  a3,BLT_SRC_ADDR.w
        lea     2(a4),a2
        move.l  a2,BLT_DST_ADDR.w
        move.w  d4,BLT_YCOUNT.w
        bsr.w   .blt80
        move.l  a3,BLT_SRC_ADDR.w
        addq.l  #2,a2
        move.l  a2,BLT_DST_ADDR.w
        move.w  d4,BLT_YCOUNT.w
        bsr.w   .blt80
        ; Pass 2: OR mask into plane 3 (sprite colours 9..15)
        move.w  #$0207,BLT_HOP.w
        move.l  a3,BLT_SRC_ADDR.w
        addq.l  #2,a2
        move.l  a2,BLT_DST_ADDR.w
        move.w  d4,BLT_YCOUNT.w
        bsr.w   .blt80
        ; Pass 3: OR sprite planes 0, 1, 2 from KO2 src a1 (stride $78)
        move.w  #$78,BLT_SRC_YINC.w
        move.l  a1,BLT_SRC_ADDR.w
        move.l  a4,BLT_DST_ADDR.w
        move.w  d4,BLT_YCOUNT.w
        bsr.w   .blt80
        lea     $28(a1),a2
        lea     2(a4),a0
        move.l  a2,BLT_SRC_ADDR.w
        move.l  a0,BLT_DST_ADDR.w
        move.w  d4,BLT_YCOUNT.w
        bsr.w   .blt80
        lea     $28(a2),a2
        addq.l  #2,a0
        move.l  a2,BLT_SRC_ADDR.w
        move.l  a0,BLT_DST_ADDR.w
        move.w  d4,BLT_YCOUNT.w
        bsr.w   .blt80
        rts

; --- cmd 4: Zero STE_RING_A & STE_RING_B ---
.cmd4_clr:
        moveq   #-1,d0
        move.l  d0,BLT_ENDMASK1.w
        move.w  d0,BLT_ENDMASK3.w
        move.w  #2,BLT_DST_XINC.w
        move.w  #2,BLT_DST_YINC.w
        clr.w   BLT_HOP.w
        clr.b   BLT_SKEW.w
        move.l  #STE_RING_A,BLT_DST_ADDR.w
        move.w  #84,BLT_XCOUNT.w
        move.w  #456,BLT_YCOUNT.w       ; 456 * 168 = 76,608B ($088e60..$09b99f < $09ba00!)
        move.b  #$c0,BLT_LINE.w
        rte

; --- cmd 6: Batched Reverse-LIFO Radar Line Restore (d2.w records ending at a2) ---
.cmd6_rad_rest:
        move.w  #2,BLT_SRC_XINC.w
        move.w  #2,BLT_SRC_YINC.w
        move.w  #2,BLT_DST_XINC.w
        moveq   #-1,d0
        move.l  d0,BLT_ENDMASK1.w
        move.w  d0,BLT_ENDMASK3.w
        move.w  #$0203,BLT_HOP.w
        clr.b   BLT_SKEW.w
        subq.w  #1,d2
.c6_lp: lea     -16(a2),a2
        move.l  4(a2),BLT_SRC_ADDR.w
        move.l  (a2),BLT_DST_ADDR.w
        move.w  8(a2),d1                ; word_cols
        lsl.w   #2,d1                   ; XCOUNT = word_cols * 4
        move.w  d1,d0
        subq.w  #1,d0
        add.w   d0,d0
        neg.w   d0
        cmpi.w  #4,d1
        bne.s   .c6_s1
        addi.w  #(4*RING_STRIDE),d0
        bra.s   .c6_s2
.c6_s1: addi.w  #RING_STRIDE,d0
.c6_s2: move.w  d0,BLT_DST_YINC.w
        move.w  d1,BLT_XCOUNT.w
        move.w  10(a2),BLT_YCOUNT.w
        bsr.w   .blt80
        dbra    d2,.c6_lp
        rte

; --- cmd 7: Batched Transparent Black Radar Line Save + Draw (d1.w records at a0) ---
.cmd7_rad_draw:
        movem.l d2-d6/a1,-(sp)
        move.w  #2,BLT_SRC_XINC.w
        move.w  #$ffff,BLT_ENDMASK2.w
        clr.b   BLT_SKEW.w
        subq.w  #1,d1
.c7_lp: movea.l (a0)+,a1                ; dst
        move.l  (a0)+,d4                ; save pool ptr
        move.w  (a0)+,d3                ; word_cols
        move.w  (a0)+,d2                ; H
        move.w  d3,d5
        lsl.w   #2,d5
        move.w  d5,d6
        subq.w  #1,d6
        add.w   d6,d6
        neg.w   d6
        cmpi.w  #1,d3
        bne.s   .c7_s1
        addi.w  #(4*RING_STRIDE),d6
        bra.s   .c7_s2
.c7_s1: addi.w  #RING_STRIDE,d6
.c7_s2: move.l  a1,BLT_SRC_ADDR.w
        move.l  d4,BLT_DST_ADDR.w
        move.w  d6,BLT_SRC_YINC.w
        move.w  #2,BLT_DST_XINC.w
        move.w  #2,BLT_DST_YINC.w
        move.w  #$ffff,BLT_ENDMASK1.w
        move.w  #$ffff,BLT_ENDMASK3.w
        move.w  d5,BLT_XCOUNT.w
        move.w  d2,BLT_YCOUNT.w
        move.w  #$0203,BLT_HOP.w
        bsr.w   .blt80
        move.w  (a0)+,BLT_ENDMASK1.w
        move.w  (a0)+,BLT_ENDMASK3.w
        move.w  #8,BLT_DST_XINC.w
        move.w  d3,d6
        subq.w  #1,d6
        lsl.w   #3,d6
        neg.w   d6
        cmpi.w  #1,d3
        bne.s   .c7_d1
        addi.w  #(4*RING_STRIDE),d6
        bra.s   .c7_d2
.c7_d1: addi.w  #RING_STRIDE,d6
.c7_d2: move.w  d6,BLT_DST_YINC.w
        move.w  d3,BLT_XCOUNT.w
        move.w  #$000f,BLT_HOP.w
        move.l  a1,BLT_DST_ADDR.w
        move.w  d2,BLT_YCOUNT.w
        bsr.w   .blt80
        addq.l  #2,a1
        clr.w   BLT_HOP.w
        move.l  a1,BLT_DST_ADDR.w
        move.w  d2,BLT_YCOUNT.w
        bsr.w   .blt80
        addq.l  #2,a1
        move.l  a1,BLT_DST_ADDR.w
        move.w  d2,BLT_YCOUNT.w
        bsr.w   .blt80
        addq.l  #2,a1
        move.w  #$000f,BLT_HOP.w
        move.l  a1,BLT_DST_ADDR.w
        move.w  d2,BLT_YCOUNT.w
        bsr.w   .blt80
        dbra    d1,.c7_lp
        movem.l (sp)+,d2-d6/a1
        rte

; --- cmd 8: Unmirrored 21-tile Horizontal Row Blit (a0=RING_BASE, d1=tx_left, d2=ty_row) ---
.cmd8_blit_row:
        movem.l d3-d7/a2-a4,-(sp)
        move.w  #2,BLT_SRC_XINC.w
        move.w  #2,BLT_SRC_YINC.w
        moveq   #-1,d0
        move.l  d0,BLT_ENDMASK1.w
        move.w  d0,BLT_ENDMASK3.w
        clr.b   BLT_SKEW.w

        ; Map ptr a2 = STE_PIT_MAP + ty_row*80 + tx_left
        move.w  d2,d0
        mulu.w  #80,d0
        add.w   d1,d0
        lea     STE_PIT_MAP.l,a2
        adda.l  d0,a2
        ; Dst a3 = a0 (RING_BASE) + (ty_row % 13)*16*168 + tx_left*8
        moveq   #0,d0
        move.w  d2,d0
        divu.w  #RING_ROWS,d0
        swap    d0
        lsl.w   #4,d0
        mulu.w  #RING_STRIDE,d0
        move.w  d1,d3
        lsl.w   #3,d3
        ext.l   d3
        add.l   d3,d0
        movea.l a0,a3
        adda.l  d0,a3
        lea     STE_PIT_TILES.l,a4

        ; Tile count = min(21, 80 - tx_left)
        moveq   #21,d7
        moveq   #80,d0
        sub.w   d1,d0
        ble.s   .c8_done
        cmp.w   d7,d0
        bge.s   .c8_cnt
        move.w  d0,d7
.c8_cnt:
        ; Clear Plane 3 for the row in ONE call (unmirrored!)
        move.w  d7,d5
        move.w  d7,d4
        subq.w  #1,d4
        lsl.w   #3,d4
        neg.w   d4
        addi.w  #RING_STRIDE,d4
        move.w  #8,BLT_DST_XINC.w
        move.w  d4,BLT_DST_YINC.w
        move.w  d7,BLT_XCOUNT.w
        clr.w   BLT_HOP.w
        lea     6(a3),a1
        move.l  a1,BLT_DST_ADDR.w
        move.w  #16,BLT_YCOUNT.w
        bsr.w   .blt80

        ; Blit 3bpp tiles (unmirrored -> 2x faster!)
        move.w  #2,BLT_DST_XINC.w
        move.w  #(RING_STRIDE-4),BLT_DST_YINC.w
        move.w  #3,BLT_XCOUNT.w
        move.w  #$0203,BLT_HOP.w
        move.w  d5,d7
        subq.w  #1,d7
.c8_lp: moveq   #0,d0
        move.b  (a2)+,d0
        move.w  d0,d3
        lsl.w   #6,d0
        lsl.w   #5,d3
        add.w   d3,d0
        lea     0(a4,d0.w),a1
        move.l  a1,BLT_SRC_ADDR.w
        move.l  a3,BLT_DST_ADDR.w
        move.w  #16,BLT_YCOUNT.w
        bsr.w   .blt80
        addq.l  #8,a3
        dbra    d7,.c8_lp
.c8_done:
        movem.l (sp)+,d3-d7/a2-a4
        rte

; --- cmd 9: Unmirrored 13-tile Vertical Column Blit (a0=RING_BASE, d1=tx_col, d2=ty_top) ---
.cmd9_blit_col:
        movem.l d3-d7/a2-a4,-(sp)
        move.w  #2,BLT_SRC_XINC.w
        move.w  #2,BLT_SRC_YINC.w
        moveq   #-1,d0
        move.l  d0,BLT_ENDMASK1.w
        move.w  d0,BLT_ENDMASK3.w
        clr.b   BLT_SKEW.w

        move.w  d2,d0
        mulu.w  #80,d0
        add.w   d1,d0
        lea     STE_PIT_MAP.l,a2
        adda.l  d0,a2
        moveq   #0,d0
        move.w  d2,d0
        divu.w  #RING_ROWS,d0
        swap    d0
        move.w  d0,d6                   ; cur_row_mod (0..12)
        lsl.w   #4,d0
        mulu.w  #RING_STRIDE,d0
        move.w  d1,d3
        lsl.w   #3,d3
        ext.l   d3
        add.l   d3,d0
        movea.l a0,a3
        adda.l  d0,a3
        lea     STE_PIT_TILES.l,a4

        moveq   #RING_ROWS,d7           ; 13 rows!
        moveq   #96,d0
        sub.w   d2,d0
        ble.w   .c9_done
        cmp.w   d7,d0
        bge.s   .c9_cnt
        move.w  d0,d7
.c9_cnt:
        ; Clear Plane 3 for entire 208-line vertical column in ONE call!
        move.w  d1,d0
        lsl.w   #3,d0
        ext.l   d0
        lea     6(a0),a1
        adda.l  d0,a1
        clr.w   BLT_DST_XINC.w
        move.w  #RING_STRIDE,BLT_DST_YINC.w
        move.w  #1,BLT_XCOUNT.w
        clr.w   BLT_HOP.w
        move.l  a1,BLT_DST_ADDR.w
        move.w  #RING_H,BLT_YCOUNT.w    ; 208 lines (unmirrored -> 2x faster!)
        bsr.w   .blt80

        move.w  #2,BLT_DST_XINC.w
        move.w  #(RING_STRIDE-4),BLT_DST_YINC.w
        move.w  #3,BLT_XCOUNT.w
        move.w  #$0203,BLT_HOP.w
        subq.w  #1,d7
.c9_lp: moveq   #0,d0
        move.b  (a2),d0
        adda.w  #80,a2
        move.w  d0,d3
        lsl.w   #6,d0
        lsl.w   #5,d3
        add.w   d3,d0
        lea     0(a4,d0.w),a1
        move.l  a1,BLT_SRC_ADDR.w
        move.l  a3,BLT_DST_ADDR.w
        move.w  #16,BLT_YCOUNT.w
        bsr.w   .blt80
        addq.w  #1,d6
        cmpi.w  #RING_ROWS,d6
        blt.s   .c9_st
        moveq   #0,d6
        suba.l  #(RING_BYTES-16*RING_STRIDE),a3
        bra.s   .c9_nx
.c9_st: adda.w  #(16*RING_STRIDE),a3
.c9_nx: dbra    d7,.c9_lp
.c9_done:
        movem.l (sp)+,d3-d7/a2-a4
        rte

; --- cmd 10: Restore transparent bottom HUD save-under (a0=dst_top, a1=hud_sav, d2=h2|h1, d3=dst_bot) ---
.cmd10_hud_rest:
        moveq   #-1,d0
        move.l  d0,BLT_ENDMASK1.w
        move.w  d0,BLT_ENDMASK3.w
        move.w  #2,BLT_SRC_XINC.w
        move.w  #2,BLT_SRC_YINC.w
        move.w  #2,BLT_DST_XINC.w
        move.w  #2,BLT_DST_YINC.w       ; 84 words = 168B = RING_STRIDE (contiguous!)
        move.w  #84,BLT_XCOUNT.w
        move.w  #$0203,BLT_HOP.w
        clr.b   BLT_SKEW.w
        move.l  a1,BLT_SRC_ADDR.w
        move.l  a0,BLT_DST_ADDR.w
        move.w  d2,BLT_YCOUNT.w         ; h1
        bsr.w   .blt80
        swap    d2
        tst.w   d2
        beq.s   .c10_done
        move.l  d3,BLT_DST_ADDR.w       ; dst_bot (BLT_SRC_ADDR already continues!)
        move.w  d2,BLT_YCOUNT.w         ; h2
        bsr.w   .blt80
.c10_done:
        rte

; --- cmd 11: Save-under + Transparent Bottom HUD Composite with 1px Black Drop-Shadow ---
; a0=dst_top, a1=hud_sav, d1.w=hscr (0..15), d2.l=(h2<<16)|h1, d3.l=dst_bot
.cmd11_hud_draw:
        movem.l d2-d5/a2-a5,-(sp)
        movea.l a0,a4                   ; a4 = dst_top
        move.l  d2,d5                   ; d5 = (h2<<16)|h1

        ; 1. Save-under 16 x 168B (h1 lines @ dst_top, h2 lines @ dst_bot) -> hud_sav (a1)
        moveq   #-1,d0
        move.l  d0,BLT_ENDMASK1.w
        move.w  d0,BLT_ENDMASK3.w
        move.w  #2,BLT_SRC_XINC.w
        move.w  #2,BLT_SRC_YINC.w       ; 84 words = 168B = RING_STRIDE!
        move.w  #2,BLT_DST_XINC.w
        move.w  #2,BLT_DST_YINC.w
        move.w  #84,BLT_XCOUNT.w
        move.w  #$0203,BLT_HOP.w
        clr.b   BLT_SKEW.w
        move.l  a4,BLT_SRC_ADDR.w
        move.l  a1,BLT_DST_ADDR.w
        move.w  d5,BLT_YCOUNT.w         ; h1
        bsr.w   .blt80
        swap    d5
        tst.w   d5
        beq.s   .c11_msk
        move.l  d3,BLT_SRC_ADDR.w       ; dst_bot (BLT_DST_ADDR already continues!)
        move.w  d5,BLT_YCOUNT.w         ; h2
        bsr.w   .blt80
.c11_msk:
        swap    d5                      ; d5 = (h2<<16)|h1 again

        ; 2. Build 16 x 20-word 1bpp mask (P0 | P1 | P2) in STE_HUD_MASK ($07b600)
        lea     STE_HUD_SRC.l,a5        ; a5 = $07f1c0
        lea     STE_HUD_MASK.l,a3       ; a3 = $07b600
        move.w  #8,BLT_SRC_XINC.w
        move.w  #8,BLT_SRC_YINC.w
        move.w  #2,BLT_DST_XINC.w
        move.w  #2,BLT_DST_YINC.w
        move.w  #20,BLT_XCOUNT.w
        move.w  #$0203,BLT_HOP.w        ; P0 -> mask
        move.l  a5,BLT_SRC_ADDR.w
        move.l  a3,BLT_DST_ADDR.w
        move.w  #16,BLT_YCOUNT.w
        bsr.w   .blt80
        move.w  #$0207,BLT_HOP.w        ; OR P1 -> mask
        lea     2(a5),a2
        move.l  a2,BLT_SRC_ADDR.w
        move.l  a3,BLT_DST_ADDR.w
        move.w  #16,BLT_YCOUNT.w
        bsr.w   .blt80
        addq.l  #2,a2                   ; OR P2 -> mask
        move.l  a2,BLT_SRC_ADDR.w
        move.l  a3,BLT_DST_ADDR.w
        move.w  #16,BLT_YCOUNT.w
        bsr.w   .blt80

        ; 3. Configure Blitter skew & XCOUNT for hscr = d1 (0..15)
        move.w  #$ffff,BLT_ENDMASK2.w
        move.w  #8,BLT_DST_XINC.w
        tst.w   d1
        bne.s   .c11_sk
        move.w  #$ffff,BLT_ENDMASK1.w
        move.w  #$ffff,BLT_ENDMASK3.w
        move.w  #20,BLT_XCOUNT.w
        move.w  #16,BLT_DST_YINC.w      ; 168 - 19*8 = 16
        clr.b   BLT_SKEW.w
        bra.s   .c11_shd
.c11_sk:
        move.w  #$ffff,d0
        lsr.w   d1,d0
        move.w  d0,BLT_ENDMASK1.w
        not.w   d0
        move.w  d0,BLT_ENDMASK3.w
        move.w  #21,BLT_XCOUNT.w
        move.w  #8,BLT_DST_YINC.w       ; 168 - 20*8 = 8
        move.b  d1,d0
        ori.b   #$40,d0                 ; NFSR = 1
        move.b  d0,BLT_SKEW.w

.c11_shd:
        ; 4. Draw 1px downward black drop-shadow (Col 9: P0=1, P1=0, P2=0, P3=1) at y+1 (15 lines)
        move.w  #2,BLT_SRC_XINC.w
        move.w  #2,BLT_SRC_YINC.w
        move.w  d5,d4
        subq.w  #1,d4                   ; sh_h1 = h1 - 1 (0..15)
        beq.s   .c11_sh2
        lea     RING_STRIDE(a4),a2      ; dst = dst_top + 1 line
        bsr.s   .c11_sh_seg
.c11_sh2:
        move.l  d5,d0
        swap    d0                      ; h2 (0..15)
        tst.w   d0
        beq.s   .c11_fg
        ; Advance mask by sh_h1 * 40 bytes for bottom wrap segment
        mulu.w  #40,d4
        lea     0(a3,d4.w),a3
        movea.l d3,a2                   ; dst = dst_bot
        move.w  d0,d4                   ; sh_h2 = h2
        bsr.s   .c11_sh_seg
        lea     STE_HUD_MASK.l,a3       ; restore a3 = STE_HUD_MASK

.c11_fg:
        ; 5. Draw crisp transparent foreground text (Col 8 white, Col 10 Home, Col 12 Away!)
        move.w  d5,d4                   ; h1 (1..16)
        movea.l a4,a2                   ; dst_top
        bsr.s   .c11_fg_seg
        swap    d5                      ; h2 (0..15)
        tst.w   d5
        beq.s   .c11_done
        move.w  d4,d0
        mulu.w  #40,d0
        adda.l  d0,a3                   ; advance mask by h1*40B
        move.w  d4,d0
        mulu.w  #160,d0
        adda.l  d0,a5                   ; advance STE_HUD_SRC by h1*160B
        movea.l d3,a2                   ; dst_bot
        move.w  d5,d4                   ; h2
        bsr.s   .c11_fg_seg
.c11_done:
        movem.l (sp)+,d2-d5/a2-a5
        rte

; Helper: draw d4 lines of 1px black shadow (Col 9: P0=1, P1=0, P2=0, P3=1) from mask a3 -> dst a2
.c11_sh_seg:
        move.w  #$0207,BLT_HOP.w        ; P0 |= mask
        move.l  a3,BLT_SRC_ADDR.w
        move.l  a2,BLT_DST_ADDR.w
        move.w  d4,BLT_YCOUNT.w
        bsr.w   .blt80
        move.w  #$0204,BLT_HOP.w        ; P1 &= ~mask
        move.l  a3,BLT_SRC_ADDR.w
        lea     2(a2),a0
        move.l  a0,BLT_DST_ADDR.w
        move.w  d4,BLT_YCOUNT.w
        bsr.w   .blt80
        move.l  a3,BLT_SRC_ADDR.w       ; P2 &= ~mask
        addq.l  #2,a0
        move.l  a0,BLT_DST_ADDR.w
        move.w  d4,BLT_YCOUNT.w
        bsr.w   .blt80
        move.w  #$0207,BLT_HOP.w        ; P3 |= mask
        move.l  a3,BLT_SRC_ADDR.w
        addq.l  #2,a0
        move.l  a0,BLT_DST_ADDR.w
        move.w  d4,BLT_YCOUNT.w
        bsr.w   .blt80
        rts

; Helper: draw d4 lines of foreground HUD (a3=mask, a5=STE_HUD_SRC, a2=dst)
.c11_fg_seg:
        ; Pass 1: Clear mask in P0, P1, P2 (~mask & DST)
        move.w  #2,BLT_SRC_XINC.w
        move.w  #2,BLT_SRC_YINC.w
        move.w  #$0204,BLT_HOP.w
        move.l  a3,BLT_SRC_ADDR.w
        move.l  a2,BLT_DST_ADDR.w
        move.w  d4,BLT_YCOUNT.w
        bsr.w   .blt80
        move.l  a3,BLT_SRC_ADDR.w
        lea     2(a2),a0
        move.l  a0,BLT_DST_ADDR.w
        move.w  d4,BLT_YCOUNT.w
        bsr.w   .blt80
        move.l  a3,BLT_SRC_ADDR.w
        addq.l  #2,a0
        move.l  a0,BLT_DST_ADDR.w
        move.w  d4,BLT_YCOUNT.w
        bsr.w   .blt80
        ; Pass 2: Set P3 |= mask (Clock/Event hud_P0 is now Col 8 = CRISP WHITE!)
        move.w  #$0207,BLT_HOP.w
        move.l  a3,BLT_SRC_ADDR.w
        addq.l  #2,a0
        move.l  a0,BLT_DST_ADDR.w
        move.w  d4,BLT_YCOUNT.w
        bsr.w   .blt80
        ; Pass 3: OR hud_P2 (Home) -> dst_P1 (Col 10 = Home kit!) & hud_P1 (Away) -> dst_P2 (Col 12 = Away kit!)
        move.w  #8,BLT_SRC_XINC.w
        move.w  #8,BLT_SRC_YINC.w
        lea     4(a5),a0                ; hud_P2 = Home
        move.l  a0,BLT_SRC_ADDR.w
        lea     2(a2),a0                ; dst_P1 = Col 10 (Home!)
        move.l  a0,BLT_DST_ADDR.w
        move.w  d4,BLT_YCOUNT.w
        bsr.w   .blt80
        lea     2(a5),a0                ; hud_P1 = Away
        move.l  a0,BLT_SRC_ADDR.w
        lea     4(a2),a0                ; dst_P2 = Col 12 (Away!)
        move.l  a0,BLT_DST_ADDR.w
        move.w  d4,BLT_YCOUNT.w
        bsr.w   .blt80
        rts
