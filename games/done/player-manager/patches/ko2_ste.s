; ---------------------------------------------------------------------------
; Player Manager v1.1 — Atari STE True Double-Buffered Amiga Engine (KO2STE.BIN)
;
; Loaded at $0ae940..$0b0eff (max 9,664 bytes) ONLY on Atari STE / Mega STE
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
STE_HUD_SAV_A   equ     $07a000         ; $07a000..$07a7ff (2,048B save-under A)
STE_HUD_SAV_B   equ     $07a800         ; $07a800..$07afff (2,048B save-under B)
STE_HUD_MASK    equ     $07b000         ; $07b000..$07bbff (3,072B HUD box/draw headers + 1bpp planes < $07bc00!)
STE_HUD_SRC     equ     $07f1c0         ; KO2 hidden bottom HUD (16 lines x 160B)
STE_RPOOL_A     equ     $07fd00         ; $07fd00..$0804ff (2 KB, cleanly above $07fcff screen!)
STE_RPOOL_B     equ     $080500         ; $080500..$080cff (2 KB, cleanly above $07fcff screen!)

; Double-buffer metadata in 100% KO2-untouched RAM ($09ba00..$09c460 & $0b2400..$0b2d00!)
STE_STK_A       equ     $09ba00         ; 32 x 16B = 512B -> $09bc00
STE_STK_B       equ     $09bc00         ; 32 x 16B = 512B -> $09be00
STE_RLR_A       equ     $09be00         ; 28 x 16B = 448B -> $09bfc0
STE_RLR_B       equ     $09bfc0         ; 28 x 16B = 448B -> $09c180
STE_SPR_LIST    equ     $09c180         ; 32 x 16B = 512B -> $09c380
STE_RAD_CACHE   equ     $09c380         ; 24 x 8B  = 192B -> $09c440
STE_MASK_BUF    equ     $09c440         ; 32B             -> $09c460
STE_RDR_A       equ     $09c460         ; 48 x 12B = 576B -> $09c6a0
STE_RDR_B       equ     $09c6a0         ; 48 x 12B = 576B -> $09c8e0
STE_Y168_TBL    equ     $09c8e0         ; 224 x 2B = 448B y*168 LUT -> $09caa0 (< $09d000 FILES.CR!)

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
STE_BIG_RAM:    dc.w    0               ; 1 = >= 2 MB STE (triple-buffered 448-line linear rings, 0 Timer B, $c0 HOG!)
STE_SHOW_IDX:   dc.w    0               ; newest completed buffer index (0..1 on 1MB, 0..2 on 2MB+)
STE_DISP_IDX:   dc.w    0               ; buffer index currently being scanned out by Shifter
STE_PEND_IDX:   dc.w    0               ; 2MB+ triple-buf: buffer index queued in $8201/$03/$0d for next VSync!
STE_PEND_HSCR:  dc.w    0               ; 2MB+ triple-buf: hscr matching $8201/$03/$0d (applied after VSync!)
STE_BK_IDX:     dc.w    0               ; temp backbuffer index being rendered in ste_pitch_update
STE_VBL_SEQ:    dc.w    0               ; seqlock counter incremented in ste_vbl_end (atomic .pu_pick3!)
STE_HUD_TICK:   dc.w    0               ; HUD cache refresh counter
STE_HUD_CCNT:   dc.w    0               ; cached non-empty HUD box count (0..3)
STE_HUD_HASH:   dc.l    -1              ; rolling dirty hash of STE_HUD_SRC (skips ste_hud_scan when unchanged!)
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
STE_TB_WH:      dc.b    0               ; pre-split Timer B wrap HI ($8205)
STE_TB_WM:      dc.b    0               ; pre-split Timer B wrap MID ($8207)
STE_TB_WL:      dc.b    0               ; pre-split Timer B wrap LOW ($8209)
                dc.b    0
STE_RAD_C_SC:   dc.w    0               ; cached radar scale
STE_RAD_C_HCNT: dc.w    0
STE_RAD_C_VCNT: dc.w    0
STE_BK_HSCR:    dc.w    0               ; temp backbuffer hscr during draw
STE_BK_Y0:      dc.w    0               ; temp backbuffer y0 (0..223) during draw
STE_BK_TX8:     dc.l    0               ; temp backbuffer tx*8 during draw
STE_BK_REND:    dc.l    0               ; temp backbuffer radar pool end during draw
STE_UL_DASH:    dc.l    0               ; secondary/pass-target player struct ptr ($fc3f dashed bar)
STE_FRM_CNT:    dc.l    0               ; published STE frames counter (incremented every ste_pitch_update!)

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
DB_C:                                   ; 3rd buffer (2 MB+ STE triple-buffering -> ZERO $8205 writes!)
        dc.l    0, 0, 0, 0, 0, 0
        dc.w    -999, -999, 0, 0, 0, 0
        dc.l    0, 0
        dc.w    224, 0
        dc.l    0, 0, 0
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
        clr.w   STE_DISP_IDX
        clr.w   STE_PEND_IDX
        clr.w   STE_PEND_HSCR
        clr.w   STE_VBL_SEQ
        moveq   #-1,d0
        move.l  d0,STE_HUD_HASH
        clr.w   STE_STATS_DIRTY
        clr.l   STE_ORIG_TB
        clr.l   STE_ORIG_VBL
        clr.l   STE_ORIG_TC
        clr.l   STE_ORIG_IKBD
        clr.w   STE_SPR_CNT
        clr.w   STE_RAD_C_SC
        clr.l   STE_UL_DASH

        ; Prebuild 224-entry y*168 LUT ($0b2400..$0b25bf) for zero-mulu pitch rendering
        lea     STE_Y168_TBL.l,a0
        moveq   #0,d0
        move.w  #223,d1
.y168:  move.w  d0,(a0)+
        addi.w  #RING_STRIDE,d0
        dbra    d1,.y168

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

        ; 5. Skip ALL KO2 hidden $078000 radar line ($01fae8), dot ($01fbb4/$01fbf8/$01fc3c/$01fca0) & underline ($01f9e0/$01fa76) drawers!
        move.w  #$4e75,d1
        move.w  d1,$01fae8.l            ; rts (radar pitch lines)
        move.w  d1,$01fbb4.l            ; rts (radar dot plot 1; keeps $20(a5)/$22(a5) updates intact!)
        move.w  d1,$01fbf8.l            ; rts (radar dot plot 2)
        move.w  d1,$01fc3c.l            ; rts (radar dot erase — protects STE_SAV_B @ $078000!)
        move.w  d1,$01fca0.l            ; rts (radar ball dot — protects STE_SAV_B @ $078000!)
        move.l  #$60000036,$01f9e0.l    ; bra.w $01fa18 (skip $078000 solid underline; keeps replay record!)
        move.w  d0,$01fa76.l            ; jmp ste_rec_ul_dash (skip $078000 dashed underline + capture ptr!)
        move.l  #ste_rec_ul_dash,$01fa78.l
        ; 6. Replace KO2 $01780e Newton-Raphson sqrt (initial guess $ffff -> 11 divus) with exact seeded sqrt (3 divus)!
        move.w  d0,$01780e.l
        move.l  #ste_fast_sqrt,$017810.l
        rts

ste_rec_ul_dash:
        move.l  a5,STE_UL_DASH
        jmp     $01faae.l

ste_fast_sqrt:
        cmpi.l  #1,d0
        bls.s   .sq_ret
        movem.l d1-d2,-(sp)
        moveq   #32,d2                  ; clears d2[31:16] = 0 for all word-load paths below!
        cmpi.l  #$1000,d0
        bcc.s   .sq_hi
        cmpi.l  #$100,d0
        bcs.s   .sq_lp
        move.w  #128,d2
        bra.s   .sq_lp
.sq_hi: cmpi.l  #$100000,d0
        bcc.s   .sq_vhi
        move.w  #512,d2
        cmpi.l  #$10000,d0
        bcs.s   .sq_lp
        move.w  #2048,d2
        bra.s   .sq_lp
.sq_vhi:
        move.w  #8192,d2
        cmpi.l  #$1000000,d0
        bcs.s   .sq_lp
        move.w  #$ffff,d2
.sq_lp: move.l  d2,d1
        move.l  d0,d2
        divu.w  d1,d2
        ext.l   d2
        add.l   d1,d2
        lsr.l   #1,d2
        sub.l   d2,d1
        cmpi.w  #-1,d1
        blt.s   .sq_lp
        cmpi.w  #1,d1
        bgt.s   .sq_lp
        move.l  d2,d0
        movem.l (sp)+,d1-d2
.sq_ret:
        rts

ste_inst_trap8:
        movem.l d3-d6/a3,-(sp)
        move.l  #ste_trap8_handler,$a0.w
        move.l  $70.w,STE_ORIG_VBL
        move.l  #ste_vbl_irq,$70.w
        clr.w   STE_BIG_RAM
        move.l  #STE_RING_A,d0
        move.l  #STE_RING_B,d1
        ; HAGA overwrites $42e.w = $80000 and saves real top-$8000 in $608.w ($0f8000/$1f8000/$3f8000)!
        cmpi.l  #$180000,$42e.w         ; non-HAGA >= 1.5 MB?
        bge.s   .it8_probe
        cmpi.l  #$178000,$608.w         ; HAGA >= 2 MB ($1f8000/$3f8000)?
        blt.w   .it8_1m
.it8_probe:
        ; Belt-and-suspenders Bus-Error + anti-alias probe at $116800 (protects MEM1M!)
        move.w  sr,d3
        move.w  #$2700,sr
        move.l  $8.w,a2
        move.l  sp,a3
        lea     .it8_pfail(pc),a0
        move.l  a0,$8.w
        moveq   #0,d4
        move.l  $116800.l,d5
        move.l  $016800.l,d6
        move.l  #$5a3c96e1,$116800.l
        nop
        cmpi.l  #$5a3c96e1,$116800.l
        bne.s   .it8_prest
        cmp.l   $016800.l,d6            ; must not alias low RAM!
        bne.s   .it8_prest
        move.l  #$a5c3691e,$116800.l
        nop
        cmpi.l  #$a5c3691e,$116800.l
        bne.s   .it8_prest
        moveq   #1,d4
.it8_prest:
        move.l  d5,$116800.l
        bra.s   .it8_pdone
.it8_pfail:
        moveq   #0,d4
.it8_pdone:
        move.l  a3,sp
        move.l  a2,$8.w
        move.w  d3,sr
        tst.w   d4
        beq.s   .it8_1m
        move.w  #1,STE_BIG_RAM
        ; Triple-buffered 448-line linear rings in safe 2MB+ gap ($0d0000..$112800):
        ; >50 KB above KO2_REPLAY_BUF ($0c2c14), >600 KB below 2MB HDDRIVER ($1a8c37)!
        move.l  #$0d0000,d0             ; DB_A = $0d0000..$0e27ff (74 KB)
        move.l  #$0e2800,d1             ; DB_B = $0e2800..$0f4fff (74 KB)
        lea     DB_A(pc),a0
        move.l  #$10b640,DB_RLR(a0)     ; 256 x 4B fast radar restore ptrs -> $10ba40
        lea     DB_B(pc),a0
        move.l  #$10ba40,DB_RLR(a0)     ; 256 x 4B fast radar restore ptrs -> $10be40
        lea     DB_C(pc),a0
        move.l  #$0f5000,DB_RING(a0)    ; DB_C = $0f5000..$1077ff (74 KB)
        move.l  #$107800,DB_SAV(a0)     ; +$0000 (8 KB)
        move.l  #$109800,DB_HUDSAV(a0)  ; +$2000 (4 KB)
        move.l  #$10a800,DB_RPOOL(a0)   ; +$3000 (2 KB)
        move.l  #$10b000,DB_STK(a0)     ; +$3800 (512B)
        move.l  #$10be40,DB_RLR(a0)     ; 256 x 4B fast radar restore ptrs -> $10c240
        move.l  #$10b400,DB_RDR(a0)     ; +$3c00 (576B -> $10b640)
.it8_1m:
        lea     DB_A(pc),a0
        move.l  d0,DB_RING(a0)
        lea     DB_B(pc),a0
        move.l  d1,DB_RING(a0)
        movem.l (sp)+,d3-d6/a3
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
        clr.w   STE_DISP_IDX
        clr.w   STE_PEND_IDX
        clr.w   STE_PEND_HSCR
        clr.w   STE_VBL_SEQ
        clr.w   STE_HUD_TICK
        clr.w   STE_HUD_CCNT
        moveq   #-1,d1
        move.l  d1,STE_HUD_HASH
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
        clr.l   $080d00.l
        clr.l   $080dc0.l
        lea     DB_A(pc),a0
        bsr.s   .rb_one
        lea     DB_B(pc),a0
        bsr.s   .rb_one
        lea     DB_C(pc),a0
.rb_one:
        move.w  #-999,DB_TX(a0)
        move.w  #-999,DB_TY(a0)
        clr.w   DB_SCNT(a0)
        clr.w   DB_RLCNT(a0)
        clr.w   DB_RDCNT(a0)
        move.l  DB_RING(a0),DB_START(a0)
        move.l  DB_RING(a0),DB_WRAP(a0)
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
; VBL IRQ ($70.w): Minimal stats-screen detector; actual STE Shifter/HScroll
; programming runs in ste_vbl_end (AFTER TOS VBL -> ~5+ scanlines past VSync,
; completely outside the Atari STE GSTMCU VSync reload window -> ZERO judder!)
; ---------------------------------------------------------------------------
ste_vbl_skip:
        movem.l d0-d1,-(sp)             ; $018d6e expects d0-d1 on stack (original $018d06)!
        jmp     $018d6e.l

ste_vbl_irq:
        tst.w   STE_PITCH_OK
        beq.s   .vt_chain_fast
        tst.l   $0231c8.l               ; KO2 -$52e2(a4): KO2 VBL active? (0 = Half-Time/Full-Time/Exit!)
        beq.s   .vt_stats_mark
        tst.w   $02356a.l               ; KO2 -$4f40(a4): Half-Time/Full-Time/Stats on $078000?
        bne.s   .vt_stats_mark
.vt_chain_fast:
        move.l  STE_ORIG_VBL(pc),-(sp)
        rts

.vt_stats_mark:
        clr.w   STE_SHOW_IDX
        clr.w   STE_DISP_IDX
        clr.w   STE_PEND_IDX
        clr.w   STE_PEND_HSCR
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
        bra.s   .vt_chain_fast

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
; Lean Video-Counter-Locked Timer B ISR (1 MB STE -> <100 cyc setup!):
; Pre-split STE_TB_WH/WM/WL bytes + min regs fit cleanly inside 176-cyc HBlank!
; ---------------------------------------------------------------------------
ste_tb_wrap:
        clr.b   $fffffa1b.w
        bclr    #7,BLT_LINE.w           ; pause active $80 Blitter FIRST (Z=0 if was active)
        movem.l d0-d2/a0,-(sp)          ; movem preserves CCR!
        sne     d1                      ; d1.b = $ff if Blitter was running
        move.w  STE_TB_TGT_W(pc),d2     ; d2.w = (TARGET - 8) & $ffff
        lea     $ffff8205.w,a0
.tw_wt: movep.w 2(a0),d0                ; atomic 16-bit read of $8207 (MID) + $8209 (LOW)
        sub.w   d2,d0
        blt.s   .tw_wt
.tw_hb: move.b  4(a0),d0                ; wait for DE=0 (HBlank)
        nop
        cmp.b   4(a0),d0
        bne.s   .tw_hb
        nop
        nop
        move.b  STE_TB_WH(pc),(a0)      ; $ffff8205 HIGH
        move.b  STE_TB_WM(pc),2(a0)     ; $ffff8207 MID
        move.b  STE_TB_WL(pc),4(a0)     ; $ffff8209 LOW
        tst.b   d1
        beq.s   .tw_no_res
        bset    #7,BLT_LINE.w
.tw_no_res:
        movem.l (sp)+,d0-d2/a0
        bclr    #0,$fffffa0f.w
        rte

; ---------------------------------------------------------------------------
; VBL End ($018e0a): Runs inside TOS VBL queue (~5+ scanlines AFTER VSync,
; ~55 scanlines BEFORE active display!) -> Official Atari STE Shifter update!
; Programs $8201/$03/$0d + $8205/$07/$09 + $820f + $8265 cleanly outside VSync!
; ---------------------------------------------------------------------------
ste_vbl_end:
        tst.w   STE_PITCH_OK
        beq.w   .ve_novid
        tst.w   $02356a.l               ; Half-Time/Full-Time/Stats active?
        bne.w   .ve_novid
        movem.l d0-d2/a0-a1,-(sp)
        bclr    #7,BLT_LINE.w           ; pause Blitter briefly if active (1 MB $80)
        sne     d2
        clr.b   $fffffa1b.w             ; stop Timer B
        tst.l   STE_ORIG_TB
        bne.s   .ve_tb_ok
        move.l  $0120.w,STE_ORIG_TB
.ve_tb_ok:
        tst.w   STE_BIG_RAM
        bne.s   .ve_pal                 ; 2 MB+ STE: no Timer B, no TC/IKBD wrap needed!
        move.l  $0114.w,d0
        beq.s   .ve_tc_ok
        cmpi.l  #ste_tc_wrap,d0
        beq.s   .ve_tc_ok
        move.l  d0,STE_ORIG_TC
        move.l  #ste_tc_wrap,$0114.w
.ve_tc_ok:
        move.l  $0118.w,d0
        beq.s   .ve_pal
        cmpi.l  #ste_ikbd_wrap,d0
        beq.s   .ve_pal
        move.l  d0,STE_ORIG_IKBD
        move.l  #ste_ikbd_wrap,$0118.w
.ve_pal:
        ; Load STE 12-bit Amiga pitch palette (0..7)
        lea     STE_PIT_PAL.l,a0
        lea     $ffff8240.w,a1
        move.l  (a0)+,(a1)+
        move.l  (a0)+,(a1)+
        move.l  (a0)+,(a1)+
        move.l  (a0)+,(a1)+

        ; Branch: 2 MB+ STE (Triple-Buffered PURE VBASE — NEVER writes $8205/$07/$09 -> ZERO judder!)
        ; vs 1 MB STE (Double-Buffered + Timer B wrap).
        tst.w   STE_BIG_RAM
        beq.s   .ve_1m

        ; 2 MB+ STE:
        ; 1. Apply HSCROLL/LINEWID for STE_PEND_IDX (the VBASE GSTMCU JUST latched at VSync!)
        move.w  STE_PEND_HSCR(pc),d0
        beq.s   .ve_bh0
        clr.b   $ffff820f.w
        move.b  d0,$ffff8265.w
        bra.s   .ve_b2
.ve_bh0:
        move.b  #4,$ffff820f.w
        clr.b   $ffff8265.w
.ve_b2:
        move.w  STE_PEND_IDX(pc),STE_DISP_IDX
        ; 2. Queue newest completed buffer (STE_SHOW_IDX) into VBASE ($8201/$03/$0d) ONLY!
        move.w  STE_SHOW_IDX(pc),d0
        move.w  d0,STE_PEND_IDX
        addq.w  #1,STE_VBL_SEQ          ; notify .pu_pick3 seqlock that (DISP, PEND) rotated!
        lsl.w   #6,d0                   ; * 64 (DB_SIZE)
        lea     DB_A(pc),a0
        adda.w  d0,a0
        move.w  DB_HSCR(a0),STE_PEND_HSCR
        move.l  DB_START(a0),d0
        move.l  d0,d1
        swap    d1
        move.b  d1,$ffff8201.w          ; VBASE HI
        move.w  d0,d1
        lsr.w   #8,d1
        move.b  d1,$ffff8203.w          ; VBASE MID
        move.b  d0,$ffff820d.w          ; VBASE LO (latched cleanly by GSTMCU at next VSync!)
        bra.w   .ve_done

.ve_1m:
        ; 1 MB STE: Select active Front buffer descriptor & latch STE_DISP_IDX!
        lea     DB_A(pc),a0
        move.w  STE_SHOW_IDX(pc),d0
        move.w  d0,STE_DISP_IDX
        beq.s   .ve_buf
        lea     DB_B(pc),a0
.ve_buf:
        ; Program VBASE ($8201/$03/$0d) + live VCOUNT ($8205/$07/$09) safely past VSync!
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

        ; Official Atari STE order: write LINEWID ($820f) BEFORE HSCROLL ($8265)!
        move.w  DB_HSCR(a0),d0
        beq.s   .ve_h0
        clr.b   $ffff820f.w             ; hscroll != 0 -> LINEWID = 0 (+8B auto = 168B!)
        move.b  d0,$ffff8265.w          ; HSCROLL = 1..15
        bra.s   .ve_tb
.ve_h0:
        move.b  #4,$ffff820f.w          ; hscroll == 0 -> LINEWID = 4 words (+8B = 168B!)
        clr.b   $ffff8265.w             ; HSCROLL = 0
.ve_tb:
        move.b  DB_WRAP+1(a0),STE_TB_WH
        move.b  DB_WRAP+2(a0),STE_TB_WM
        move.b  DB_WRAP+3(a0),STE_TB_WL
        move.w  DB_WTGT(a0),STE_TB_TGT_W
        move.w  DB_WRAPY(a0),d0
        move.w  d0,STE_TB_WRAP_Y
        cmpi.w  #PITCH_VIS_H,d0
        bge.s   .ve_done
        subq.w  #1,d0
        move.l  #ste_tb_wrap,$0120.w
        move.b  d0,$fffffa21.w
        move.b  #8,$fffffa1b.w
        bset    #0,$fffffa07.w
        bset    #0,$fffffa13.w
.ve_done:
        tst.b   d2
        beq.s   .ve_nr
        bset    #7,BLT_LINE.w
.ve_nr: movem.l (sp)+,d0-d2/a0-a1
.ve_novid:
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
; Always scans STE_SPR_LIST by a3 (guarantees 0 duplicate slots!) and marks
; (a3) = 1 on draw / 0 on erase; ste_bk_draw_spr also purges any slot whose
; (a3) was cleared directly by KO2 ($01a342/$0162b2/$01a826/kickoff reset)!
; ---------------------------------------------------------------------------
ste_draw_spr_core:
        ; Input: d0.w = x_scr, d1.w = y_scr, a1 = KO2 3bpp src, a3 = KO2 save record
        ; Caller pushed movem.l d0-d2/d4/d7/a0-a1/a3,-(sp)
        move.l  #1,(a3)                 ; mark entity active in KO2's save record
        add.w   STE_CUR_WX(pc),d0       ; world_x (0..1279)
        add.w   STE_CUR_WY(pc),d1       ; world_y (0..1535)
        lea     STE_SPR_LIST.l,a0
        moveq   #0,d4
        move.w  STE_SPR_CNT(pc),d2
        beq.s   .dsc_add
        subq.w  #1,d2
.dsc_fnd:
        cmpa.l  (a0),a3
        beq.s   .dsc_upd
        lea     16(a0),a0
        dbra    d2,.dsc_fnd
.dsc_add:
        cmpi.w  #32,STE_SPR_CNT
        bcc.s   .dsc_ret
        move.l  a3,(a0)
        moveq   #1,d4
.dsc_upd:
        move.l  a1,4(a0)
        move.w  d0,8(a0)                ; world_x
        move.w  d1,10(a0)               ; world_y
        add.w   d4,STE_SPR_CNT          ; publish new slot LAST (atomic!)
.dsc_ret:
        movem.l (sp)+,d0-d2/d4/d7/a0-a1/a3
        rts

ste_erase_spr:
        ; Input: a3 = KO2 save record (unconditional scan — KO2 may clear (a3) first!)
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
        clr.w   STE_SHOW_IDX
        clr.w   STE_DISP_IDX
        clr.w   STE_PEND_IDX
        clr.w   STE_PEND_HSCR
        moveq   #-1,d0
        move.l  d0,STE_HUD_HASH
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

        ; Compute y0 = wy % 224 -> d4.w
        moveq   #0,d4
        move.w  d1,d4
        divu.w  #RING_H,d4
        swap    d4                      ; d4.w = y0 (0..223)
        move.w  d4,STE_BK_Y0
        move.w  d2,d5
        lsl.w   #3,d5
        ext.l   d5
        move.l  d5,STE_BK_TX8

        ; Select INVISIBLE Backbuffer descriptor a6:
        ;   2 MB+ STE: Triple-buffered -> NEVER pick DISP, PEND, OR SHOW (spin if all 3 busy!)
        ;   1 MB  STE: Double-buffered -> wait until VBL latches STE_SHOW_IDX
        tst.w   STE_BIG_RAM
        beq.s   .pu_wait_disp
.pu_pick3:
        move.w  STE_VBL_SEQ(pc),d0
        move.w  STE_DISP_IDX(pc),d1
        move.w  STE_PEND_IDX(pc),d4
        move.w  STE_SHOW_IDX(pc),d5
        cmp.w   STE_VBL_SEQ(pc),d0
        bne.s   .pu_pick3               ; VBL rotated buffers mid-read -> re-read atomically!
        moveq   #0,d0
.pb_lp: cmp.w   d1,d0
        beq.s   .pb_nx
        cmp.w   d4,d0
        beq.s   .pb_nx
        cmp.w   d5,d0
        bne.s   .pb_got
.pb_nx: addq.w  #1,d0
        cmpi.w  #3,d0
        blt.s   .pb_lp
        bra.s   .pu_pick3               ; all 3 in use (50Hz game ahead of VBL) -> VSync pace!
.pb_got:
        move.w  d0,STE_BK_IDX
        lsl.w   #6,d0                   ; * 64 (DB_SIZE)
        lea     DB_A(pc),a6
        adda.w  d0,a6
        bra.s   .pu_got_bk

.pu_wait_disp:
        move.w  STE_SHOW_IDX(pc),d0
        cmp.w   STE_DISP_IDX(pc),d0
        bne.s   .pu_wait_disp

        ; Select INVISIBLE Backbuffer descriptor a6 = (STE_SHOW_IDX == 0) ? DB_B : DB_A
        lea     DB_B(pc),a6
        tst.w   d0
        beq.s   .pu_got_bk
        lea     DB_A(pc),a6
.pu_got_bk:
        ; === STEP A: Restore 1MB y0==223 Row-224 tail (if any), then Reverse-LIFO Erase ===
        tst.w   STE_BIG_RAM
        bne.s   .pu_er_go
        lea     $080d00.l,a0
        cmpi.l  #STE_RING_A,DB_RING(a6)
        beq.s   .pu_mr1
        lea     192(a0),a0
.pu_mr1:
        move.l  (a0),d0
        beq.s   .pu_er_go
        clr.l   (a0)+
        movea.l d0,a1
        moveq   #41,d1
.pu_mrl:
        move.l  (a0)+,(a1)+
        dbra    d1,.pu_mrl
.pu_er_go:
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

        ; Precompute DB_WRAP = RING + tx*8 and DB_START = RING + y0*168 + tx*8 BEFORE Step C
        ; so Radar/Dots/UL/Sprites/HUD use DB_START(a6) directly with ZERO mulu!
        move.l  DB_RING(a6),d0
        add.l   STE_BK_TX8(pc),d0
        move.l  d0,DB_WRAP(a6)
        move.w  STE_BK_Y0(pc),d1
        add.w   d1,d1
        lea     STE_Y168_TBL.l,a0
        moveq   #0,d4
        move.w  0(a0,d1.w),d4
        add.l   d0,d4
        move.l  d4,DB_START(a6)

        ; === STEP C: Draw Transparent Vector Radar + 23 Dots + Active Player Underlines onto Backbuffer ===
        bsr.w   ste_bk_draw_rad
        bsr.w   ste_bk_draw_ul

        ; === STEP D: Draw ALL Active Sprites + Transparent Bottom HUD onto Backbuffer ===
        bsr.w   ste_bk_draw_spr
        bsr.w   ste_bk_draw_hud

        ; === STEP E: 1MB Seam Mirror + Atomic Front <-> Back Swap! ===
        move.l  DB_WRAP(a6),d0          ; RING + tx*8
        move.w  #RING_H,d1
        sub.w   STE_BK_Y0(pc),d1        ; wrap_y = 224 - y0 (1..224)
        tst.w   STE_BIG_RAM
        bne.s   .pu_wyok                ; 2 MB+ STE: linear 448-line buffer -> no wrap mirror needed!
        move.l  d0,d3
        addi.l  #(RING_BYTES-104),d3    ; +64B into row 223: zero movep.w page-boundary slip!
        cmpi.w  #1,d1
        bne.s   .pu_wyok                ; ONLY y0 == 223 (wrap_y == 1) needs Row 224 mirror!
        movea.l d0,a0                   ; src = RING + tx*8 (row 0)
        movea.l d0,a1
        adda.l  #RING_BYTES,a1          ; dst = RING + 224*168 + tx*8 (row 224)
        lea     $080d00.l,a2
        cmpi.l  #STE_RING_A,DB_RING(a6)
        beq.s   .pu_msv
        lea     192(a2),a2
.pu_msv:
        move.l  a1,(a2)+
        moveq   #41,d2                  ; 42 longs = 168 bytes (1 full scanline)
.pu_m0: move.l  (a1),(a2)+
        move.l  (a0)+,(a1)+
        dbra    d2,.pu_m0
        ; y0 == 223 (wrap_y == 1): Row 224 now mirrors Row 0 -> wrap at line 2 to Row 1!
        addi.l  #RING_STRIDE,d0         ; wrap_addr = RING + 168 + tx*8 (row 1)
        move.l  d0,DB_WRAP(a6)
        addi.w  #RING_STRIDE,d3
        moveq   #2,d1                   ; wrap_y = 2!
.pu_wyok:
        move.w  d3,DB_WTGT(a6)
        move.w  d1,DB_WRAPY(a6)
        move.w  STE_BK_HSCR(pc),DB_HSCR(a6)

        ; ATOMIC 1-instruction Front <-> Back buffer publish!
        tst.w   STE_BIG_RAM
        beq.s   .pu_flip1m
        move.w  STE_BK_IDX(pc),STE_SHOW_IDX
        bra.s   .pu_ret
.pu_flip1m:
        eori.w  #1,STE_SHOW_IDX
.pu_ret:
        addq.l  #1,STE_FRM_CNT
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
; Helper: ste_sy_ptr(d1.w=sy 0..199, d0.l=rel_x_byte_off, a6=DB) -> a0=ring ptr
; Preserves d0, d2-d7, a1-a6! Clobbers d1.
; ---------------------------------------------------------------------------
ste_sy_ptr:
        movea.l DB_START(a6),a0
        tst.w   STE_BIG_RAM
        bne.s   .ssp_t
        add.w   STE_BK_Y0(pc),d1
        cmpi.w  #RING_H,d1
        blt.s   .ssp_1
        subi.w  #RING_H,d1
.ssp_1: movea.l DB_WRAP(a6),a0
.ssp_t: add.w   d1,d1
        move.l  a0,-(sp)
        lea     STE_Y168_TBL.l,a0
        move.w  0(a0,d1.w),d1
        andi.l  #$ffff,d1
        add.l   d0,d1
        movea.l (sp)+,a0
        adda.l  d1,a0
        rts

; ---------------------------------------------------------------------------
; Step A: Reverse-LIFO Blitter Restore of Backbuffer's old HUD (cmd 7)
; ---------------------------------------------------------------------------
ste_bk_erase_hud:
        move.w  DB_HUD_H1(a6),d1
        beq.s   .beh_ret
        clr.w   DB_HUD_H1(a6)
        movem.l d0-d1/a0,-(sp)
        movea.l DB_HUDSAV(a6),a0        ; restore records [dst.l, sav.l, xcnt.w, ycnt.w]
        moveq   #7,d0                   ; cmd 7 = batch Blitter HUD restore
        trap    #8
        movem.l (sp)+,d0-d1/a0
.beh_ret:
        rts

; ---------------------------------------------------------------------------
; Fast Blitter-Accelerated 3-Box Transparent Bottom HUD:
;   Rebuild 3 tight 1bpp boxes (TOTMASK, SHAD, P2_HOME, P1_AWAY) once per 8 frames;
;   each frame runs 1 TRAP #8 (cmd 6) for hardware-barrel-shifted save + blit!
; ---------------------------------------------------------------------------
STE_HUD_Q       equ     STE_HUD_MASK+64 ; 8 draw queue entries x 16B = 128B ($07b040..$07b0bf)
STE_HUD_PDATA   equ     STE_HUD_MASK+192 ; packed 1bpp planes ($07b0c0..$07bbff = 2,880B)

ste_hud_regions:
        dc.b    0,9,0,7                 ; Box 0: Top-Left (player/card)
        dc.b    10,16,0,7               ; Box 1: Top-Mid-Right (Home score)
        dc.b    17,19,0,7               ; Box 2: Top-Far-Right (Away score)
        dc.b    0,19,8,15               ; Box 3: Bottom-Mid (clock/status)

ste_hud_scan:
        movem.l d0-d7/a0-a5,-(sp)
        lea     STE_HUD_MASK.l,a2       ; 4 x 16B box headers
        lea     STE_HUD_PDATA.l,a4      ; packed 1bpp plane arena
        lea     ste_hud_regions(pc),a5
        clr.w   STE_HUD_CCNT
        moveq   #3,d7                   ; 4 regions
.hs_reg:
        moveq   #0,d0
        move.b  (a5)+,d0                ; c0
        moveq   #0,d1
        move.b  (a5)+,d1                ; c1
        moveq   #0,d2
        move.b  (a5)+,d2                ; y0
        moveq   #0,d3
        move.b  (a5)+,d3                ; y1
        moveq   #99,d4                  ; min_c
        moveq   #-1,d5                  ; max_c
        move.w  #99,-(sp)               ; (sp) = min_y
        move.w  #-1,-(sp)               ; (sp) = max_y -> +0(sp)=max_y, +2(sp)=min_y
        move.w  d2,d6                   ; y = y0..y1
        lsl.w   #5,d2
        move.w  d2,d3
        add.w   d2,d2
        add.w   d2,d2
        add.w   d3,d2                   ; y0 * 160
        move.w  d0,d3
        lsl.w   #3,d3
        add.w   d3,d2
        lea     STE_HUD_SRC.l,a1
        adda.w  d2,a1
.hs_ylp:
        movea.l a1,a0
        move.w  d0,d2
.hs_xlp:
        move.l  (a0)+,d3
        or.w    (a0)+,d3
        addq.l  #2,a0
        tst.l   d3
        beq.s   .hs_nx
        cmp.w   d4,d2
        bge.s   .hs_mxc
        move.w  d2,d4                   ; min_c
.hs_mxc:
        cmp.w   d5,d2
        ble.s   .hs_my
        move.w  d2,d5                   ; max_c
.hs_my: cmp.w   2(sp),d6
        bge.s   .hs_mxy
        move.w  d6,2(sp)                ; min_y
.hs_mxy:
        cmp.w   (sp),d6
        ble.s   .hs_nx
        move.w  d6,(sp)                 ; max_y
.hs_nx: addq.w  #1,d2
        cmp.w   d1,d2
        ble.s   .hs_xlp
        lea     160(a1),a1
        addq.w  #1,d6
        cmp.b   -1(a5),d6
        ble.s   .hs_ylp

        move.w  (sp)+,d6                ; max_y
        move.w  (sp)+,d2                ; min_y
        tst.w   d6
        bge.s   .hs_got
        clr.w   6(a2)                   ; h = 0 (empty box)
        lea     16(a2),a2
        bra.w   .hs_nr
.hs_got:
        sub.w   d2,d6
        addq.w  #1,d6                   ; d6 = h (1..8)
        move.w  d5,d1
        sub.w   d4,d1
        addq.w  #1,d1                   ; d1 = w_src (1..20)
        move.w  d1,d0
        addq.w  #1,d0                   ; d0 = w_buf = w_src + 1
        mulu.w  d6,d0
        add.w   d0,d0                   ; d0 = plane_sz = w_buf * h * 2
        ; Guard: a4 + 4*plane_sz <= $07bc00
        move.l  d0,d3
        lsl.l   #2,d3
        add.l   a4,d3
        cmpi.l  #$07bc00,d3
        bhi.w   .hs_skip
        addq.w  #1,STE_HUD_CCNT
        addi.w  #HUD_SCR_Y,d2
        move.w  d2,(a2)+                ; +0: y_off (183..198)
        move.w  d4,d2
        lsl.w   #3,d2
        move.w  d2,(a2)+                ; +2: col8
        move.w  d1,(a2)+                ; +4: w_src
        move.w  d6,(a2)+                ; +6: h
        move.w  d5,(a2)+                ; +8: hi=flags(bit0=has_p2, bit1=has_p1), lo=max_c(0..19)
        move.w  d0,(a2)+                ; +10: plane_sz
        move.l  a4,(a2)+                ; +12: pdata

        ; Pack 4 planes sequentially: TOTMASK(a4), SHAD(+d0), P2(+2*d0), P1(+3*d0)
        movea.l a4,a0                   ; TOTMASK cursor
        movea.l a4,a1
        adda.w  d0,a1                   ; SHAD cursor
        lea     0(a1,d0.w),a3           ; P2 cursor
        move.l  d3,-(sp)                ; +6(sp): end of 4 planes (next a4)
        move.l  a5,-(sp)                ; +2(sp): saved regions ptr
        move.w  d7,-(sp)                ; +0(sp): saved region dbra
        lea     0(a3,d0.w),a4           ; P1 cursor
        move.w  -16(a2),d2
        subi.w  #HUD_SCR_Y,d2
        mulu.w  #160,d2
        add.w   -14(a2),d2
        lea     STE_HUD_SRC.l,a5
        adda.w  d2,a5                   ; a5 = box top-left in STE_HUD_SRC
        move.w  d1,d2
        lsl.w   #3,d2
        move.w  #160,d3
        sub.w   d2,d3                   ; d3 = row advance = 160 - w_src*8
        subq.w  #1,d6                   ; row dbra
.hp_y:  moveq   #0,d5                   ; cross-word shadow carry ($0000 or $8000)
        move.w  -12(a2),d4              ; w_src
        subq.w  #1,d4
.hp_x:  move.w  (a5)+,d0                ; P0
        move.w  (a5)+,d1                ; P1 (Away)
        beq.s   .hp_np1
        bset    #1,-8(a2)               ; mark box has_p1!
.hp_np1:
        move.w  (a5)+,d2                ; P2 (Home)
        beq.s   .hp_np2
        bset    #0,-8(a2)               ; mark box has_p2!
.hp_np2:
        addq.l  #2,a5                   ; skip P3
        move.w  d1,(a4)+                ; P1
        move.w  d2,(a3)+                ; P2
        or.w    d1,d0
        or.w    d2,d0                   ; mask = P0 | P1 | P2
        move.w  d0,d7
        lsr.w   #1,d7                   ; X = bit0(mask)
        or.w    d5,d7                   ; carry into bit15 (X preserved!)
        move.w  d0,d1
        not.w   d1
        and.w   d1,d7                   ; shad = ((mask>>1)|carry) & ~mask (X preserved!)
        or.w    d7,d0                   ; totmask = mask | shad (X preserved!)
        move.w  d0,(a0)+
        move.w  d7,(a1)+
        moveq   #0,d5
        roxr.w  #1,d5                   ; next carry = old bit0 << 15
        dbra    d4,.hp_x
        move.w  d5,(a0)+                ; extra word (w_buf-1): carry shadow only
        move.w  d5,(a1)+
        clr.w   (a3)+
        clr.w   (a4)+
        adda.w  d3,a5
        dbra    d6,.hp_y
        move.w  (sp)+,d7
        movea.l (sp)+,a5
        movea.l (sp)+,a4                ; advance plane arena ptr to end of 4 planes
        bra.s   .hs_nr
.hs_skip:
        clr.w   6(a2)
        lea     16(a2),a2
.hs_nr: dbra    d7,.hs_reg
        movem.l (sp)+,d0-d7/a0-a5
        rts

ste_bk_draw_hud:
        movem.l d0-d7/a0-a5,-(sp)
        move.w  STE_HUD_TICK(pc),d0
        addq.w  #1,STE_HUD_TICK
        andi.w  #7,d0
        bne.s   .bdh_go
        ; Fast 4-row dirty hash over STE_HUD_SRC (rows 2,5 & 10,13 -> 4x lighter!)
        lea     (STE_HUD_SRC+2*160).l,a0
        moveq   #-1,d0
        bsr.s   .bh_hrow
        lea     (2*160)(a0),a0
        bsr.s   .bh_hrow
        lea     (4*160)(a0),a0
        bsr.s   .bh_hrow
        lea     (2*160)(a0),a0
        bsr.s   .bh_hrow
        cmp.l   STE_HUD_HASH(pc),d0
        beq.s   .bdh_go
        move.l  d0,STE_HUD_HASH
        bsr.w   ste_hud_scan
        bra.s   .bdh_go

.bh_hrow:
        moveq   #9,d3
.bh_hc: add.l   (a0)+,d0
        add.w   (a0)+,d0
        addq.l  #2,a0
        rol.l   #3,d0
        add.l   (a0)+,d0
        add.w   (a0)+,d0
        addq.l  #2,a0
        dbra    d3,.bh_hc
        rts

.bdh_go:
        tst.w   STE_HUD_CCNT
        beq.w   .bdh_done
        lea     STE_HUD_MASK.l,a2       ; 4 box headers
        movea.l DB_HUDSAV(a6),a3        ; restore records [0..95]
        lea     96(a3),a4               ; save pixel pool cursor
        lea     STE_HUD_Q.l,a5          ; draw queue entries
        move.w  STE_BK_HSCR(pc),d5      ; hscr (0..15)
        moveq   #0,d7                   ; seg_count (0..8)
        moveq   #3,d6                   ; 4 boxes
.bdh_bx:
        move.w  6(a2),d4                ; h (0 = skip)
        beq.w   .bdh_nb
        move.w  4(a2),d3                ; w_src
        ; Compute xcnt, src_yinc, em1, em3 for hscr == 0 vs hscr > 0 and max_c == 19 vs < 19:
        tst.w   d5
        bne.s   .bh_sk
        moveq   #-1,d1                  ; em1 = $ffff
        moveq   #-1,d2                  ; em3 = $ffff
        move.w  #2,STE_HUD_TMP_SY       ; default src_yinc = 2
        cmpi.b  #19,9(a2)
        beq.s   .bh_019
        addq.w  #1,d3                   ; xcnt = w_src + 1
        bra.s   .bh_wok
.bh_019:
        move.w  #4,STE_HUD_TMP_SY       ; src_yinc = 4 (skip unused extra word)
        bra.s   .bh_wok
.bh_sk:
        moveq   #-1,d1
        lsr.w   d5,d1                   ; em1 = $ffff >> hscr
        move.w  d1,d2
        not.w   d2                      ; em3 = ~em1
        addq.w  #1,d3                   ; +1 for hscr
        move.w  #4,STE_HUD_TMP_SY
        cmpi.b  #19,9(a2)
        beq.s   .bh_wok
        addq.w  #1,d3                   ; max_c < 19 -> xcnt = w_src + 2
        move.w  #2,STE_HUD_TMP_SY
.bh_wok:
        move.w  d1,STE_HUD_TMP_E1
        move.w  d2,STE_HUD_TMP_E3
        move.w  d3,d4                   ; wait save xcnt cleanly!
        move.w  d4,STE_HUD_TMP_XC
        move.w  6(a2),d4                ; d4 = h
        move.w  4(a2),d3
        addq.w  #1,d3
        add.w   d3,d3                   ; d3 = src row stride in bytes = (w_src+1)*2

        ; Compute dst_top via ste_sy_ptr and check 1 MB seam split
        move.w  (a2),d1                 ; y_off (183..198)
        moveq   #0,d0
        move.w  2(a2),d0                ; col8
        bsr.w   ste_sy_ptr              ; a0 = dst_top
        tst.w   STE_BIG_RAM
        bne.s   .bh_one
        move.w  (a2),d1
        add.w   STE_BK_Y0(pc),d1
        cmpi.w  #RING_H,d1
        blt.s   .bh_yok
        subi.w  #RING_H,d1
.bh_yok:
        move.w  d1,d2
        add.w   d4,d2
        cmpi.w  #RING_H,d2
        ble.s   .bh_one
        ; Split at 224 seam: h1 = 224 - yr, h2 = h - h1
        move.w  #RING_H,d2
        sub.w   d1,d2                   ; d2 = h1
        sub.w   d2,d4                   ; d4 = h2
        move.l  12(a2),d1               ; pdata
        move.w  d2,-(sp)                ; save h1
        move.w  d4,-(sp)                ; save h2
        move.w  STE_HUD_TMP_XC(pc),d4
        bsr.s   .bh_emit
        movea.l DB_WRAP(a6),a0
        adda.w  2(a2),a0
        move.w  2(sp),d0                ; h1
        mulu.w  d3,d0
        move.l  12(a2),d1
        add.l   d0,d1
        move.w  (sp)+,d2                ; h2
        addq.l  #2,sp                   ; pop h1
        move.w  STE_HUD_TMP_XC(pc),d4
        bsr.s   .bh_emit
        bra.s   .bdh_nb
.bh_one:
        move.w  d4,d2                   ; h
        move.l  12(a2),d1               ; pdata
        move.w  STE_HUD_TMP_XC(pc),d4
        bsr.s   .bh_emit
.bdh_nb:
        lea     16(a2),a2
        dbra    d6,.bdh_bx

        move.w  d7,DB_HUD_H1(a6)
        beq.s   .bdh_done
        move.w  d5,d2
        beq.s   .bdh_tr
        ori.w   #$0040,d2               ; NFSR=1 | hscr
.bdh_tr:
        movea.l DB_HUDSAV(a6),a0        ; restore records
        move.w  d7,d1                   ; seg count
        moveq   #6,d0                   ; cmd 6 = HUD save+blit
        trap    #8
.bdh_done:
        movem.l (sp)+,d0-d7/a0-a5
        rts

; Helper: emit 1 HUD draw+restore segment (a0=dst, d1.l=pdata, d2.w=h, d4.w=xcnt)
.bh_emit:
        cmpi.w  #8,d7
        bcc.s   .bhe_r
        move.w  d4,d0
        mulu.w  d2,d0
        lsl.l   #3,d0                   ; sav bytes = xcnt * h * 8
        move.l  a4,d5
        add.l   d0,d5
        sub.l   DB_HUDSAV(a6),d5
        cmpi.l  #2048,d5
        bhi.s   .bhe_r
        move.l  a0,(a3)+                ; restore +0: dst
        move.l  a4,(a3)+                ; restore +4: sav
        move.w  d4,(a3)+                ; restore +8: xcnt
        move.w  d2,(a3)+                ; restore +10: ycnt (h)
        move.l  d1,(a5)+                ; Q +0: pdata
        move.w  10(a2),(a5)+            ; Q +4: plane_sz
        move.w  d4,(a5)+                ; Q +6: xcnt
        move.w  STE_HUD_TMP_SY(pc),(a5)+ ; Q +8: src_yinc
        move.w  STE_HUD_TMP_E1(pc),(a5)+ ; Q +10: em1
        move.w  STE_HUD_TMP_E3(pc),(a5)+ ; Q +12: em3
        move.w  8(a2),(a5)+             ; Q +14: bit8=has_p2, bit9=has_p1
        adda.l  d0,a4
        addq.w  #1,d7
.bhe_r: move.w  STE_BK_HSCR(pc),d5
        rts

STE_HUD_TMP_SY: dc.w    0
STE_HUD_TMP_E1: dc.w    0
STE_HUD_TMP_E3: dc.w    0
STE_HUD_TMP_XC: dc.w    0


ste_bk_erase_spr:
        move.w  DB_SCNT(a6),d1
        beq.s   .bes_ret
        clr.w   DB_SCNT(a6)
        movem.l d0-d1/a0-a1,-(sp)
        move.w  d1,d0
        lsl.w   #4,d0
        movea.l DB_STK(a6),a0
        adda.w  d0,a0                   ; a0 = end of Backbuffer's sprite restore stack
        move.w  d1,d0
        lsl.w   #8,d0
        ext.l   d0
        movea.l DB_SAV(a6),a1
        adda.l  d0,a1                   ; a1 = end of Backbuffer's save-under slots
        moveq   #2,d0                   ; cmd 2 = reverse-LIFO restore of d1 records
        trap    #8
        movem.l (sp)+,d0-d1/a0-a1
.bes_ret:
        rts

; Reverse-LIFO CPU restore of radar dots/UL + CPU radar horizontal/vertical lines
ste_bk_erase_rad:
        movem.l d0-d3/a0-a2,-(sp)
        ; 1. Restore Backbuffer's old radar dots + underlines (reverse LIFO)
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
        ; 2. Restore Backbuffer's old radar lines (2MB+ flat disjoint list vs 1MB reverse LIFO)
        move.w  DB_RLCNT(a6),d0
        beq.w   .ber_ret
        clr.w   DB_RLCNT(a6)
        tst.w   STE_BIG_RAM
        beq.s   .ber_1m
        movea.l DB_RLR(a6),a0
        movea.l DB_RPOOL(a6),a2
        move.w  d0,d1
        andi.w  #3,d1
        beq.s   .ber_f4
        subq.w  #1,d1
.ber_fr:
        movea.l (a0)+,a1
        move.l  (a2)+,(a1)+
        move.l  (a2)+,(a1)
        dbra    d1,.ber_fr
.ber_f4:
        lsr.w   #2,d0
        subq.w  #1,d0
        blt.s   .ber_ret
.ber_flp:
        movea.l (a0)+,a1
        move.l  (a2)+,(a1)+
        move.l  (a2)+,(a1)
        movea.l (a0)+,a1
        move.l  (a2)+,(a1)+
        move.l  (a2)+,(a1)
        movea.l (a0)+,a1
        move.l  (a2)+,(a1)+
        move.l  (a2)+,(a1)
        movea.l (a0)+,a1
        move.l  (a2)+,(a1)+
        move.l  (a2)+,(a1)
        dbra    d0,.ber_flp
        bra.s   .ber_ret
.ber_1m:
        move.w  d0,d1
        mulu.w  #12,d0
        movea.l DB_RLR(a6),a0
        adda.l  d0,a0
        move.w  #(4*RING_STRIDE-4),d3
        subq.w  #1,d1
.ber_ll:
        lea     -12(a0),a0
        movea.l (a0),a1                 ; dst
        movea.l 4(a0),a2                ; sav pool
        move.w  8(a0),d2                ; count >= 1
        tst.w   10(a0)                  ; 0=horiz, !=0=vert (stride 672)
        bne.s   .ber_vl0
        subq.w  #1,d2
.ber_hl:
        move.l  (a2)+,(a1)+
        move.l  (a2)+,(a1)+
        dbra    d2,.ber_hl
        dbra    d1,.ber_ll
        bra.s   .ber_ret
.ber_vl0:
        lsr.w   #1,d2
        bcc.s   .ber_vle
        move.l  (a2)+,(a1)+
        move.l  (a2)+,(a1)
        adda.w  d3,a1
.ber_vle:
        subq.w  #1,d2
        blt.s   .ber_vln
.ber_vl:
        move.l  (a2)+,(a1)+
        move.l  (a2)+,(a1)
        adda.w  d3,a1
        move.l  (a2)+,(a1)+
        move.l  (a2)+,(a1)
        adda.w  d3,a1
        dbra    d2,.ber_vl
.ber_vln:
        dbra    d1,.ber_ll
.ber_ret:
        movem.l (sp)+,d0-d3/a0-a2
        rts

; ---------------------------------------------------------------------------
; Step C: Direct 68000 CPU Transparent Vector Radar + 23 Dots (ZERO Blits, ZERO mulu!)
; ---------------------------------------------------------------------------
ste_bk_draw_rad:
        tst.w   -$0e10(a4)              ; Radar ON (> 0)?
        ble.w   .bdr_done_ret
        move.w  -$0e0a(a4),d6           ; Radar scale (8, 12, 16, 20, 24)
        ble.w   .bdr_done_ret
        movem.l d0-d7/a0-a3/a5,-(sp)
        ; Rebuild pre-scaled line cache ONLY when scale changes!
        cmp.w   STE_RAD_C_SC(pc),d6
        beq.w   .rc_ok
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
        tst.w   STE_BIG_RAM
        beq.w   .rc_ok
        bsr.w   ste_rad_bake_big
.rc_ok:
        movea.l DB_RLR(a6),a2           ; line restore record cursor
        movea.l DB_RPOOL(a6),a5         ; radar save pool cursor (2,048B safe)
        tst.w   STE_BIG_RAM
        beq.w   .br_1m_go
        ; === 2 MB+ STE: Pre-baked 8-byte [delta.w, m.w, inv_m_l.l] list ($10e800 + hscr*2048) ===
        moveq   #0,d0
        move.w  STE_BK_HSCR(pc),d0
        lsl.l   #8,d0
        lsl.l   #3,d0                   ; hscr * 2048
        lea     $10e800.l,a3
        adda.l  d0,a3
        move.w  (a3)+,d7                ; count of non-zero radar words
        beq.w   .br_dots
        addq.l  #2,a3                   ; skip pad.w
        movea.l DB_START(a6),a1
        move.w  d7,d6
        andi.w  #3,d6
        beq.s   .br_f4
        subq.w  #1,d6
.br_rem:
        adda.w  (a3)+,a1
        move.w  (a3)+,d4
        move.l  (a3)+,d5
        move.l  a1,(a2)+
        move.l  (a1),(a5)+
        move.l  4(a1),(a5)+
        or.w    d4,(a1)
        and.l   d5,2(a1)
        or.w    d4,6(a1)
        dbra    d6,.br_rem
.br_f4: move.w  d7,d6
        lsr.w   #2,d6
        subq.w  #1,d6
        blt.w   .br_dots
.br_f0: adda.w  (a3)+,a1
        move.w  (a3)+,d4
        move.l  (a3)+,d5
        move.l  a1,(a2)+
        move.l  (a1),(a5)+
        move.l  4(a1),(a5)+
        or.w    d4,(a1)
        and.l   d5,2(a1)
        or.w    d4,6(a1)
        adda.w  (a3)+,a1
        move.w  (a3)+,d4
        move.l  (a3)+,d5
        move.l  a1,(a2)+
        move.l  (a1),(a5)+
        move.l  4(a1),(a5)+
        or.w    d4,(a1)
        and.l   d5,2(a1)
        or.w    d4,6(a1)
        adda.w  (a3)+,a1
        move.w  (a3)+,d4
        move.l  (a3)+,d5
        move.l  a1,(a2)+
        move.l  (a1),(a5)+
        move.l  4(a1),(a5)+
        or.w    d4,(a1)
        and.l   d5,2(a1)
        or.w    d4,6(a1)
        adda.w  (a3)+,a1
        move.w  (a3)+,d4
        move.l  (a3)+,d5
        move.l  a1,(a2)+
        move.l  (a1),(a5)+
        move.l  4(a1),(a5)+
        or.w    d4,(a1)
        and.l   d5,2(a1)
        or.w    d4,6(a1)
        dbra    d6,.br_f0
        bra.w   .br_dots

.br_1m_go:
        lea     STE_RAD_CACHE.l,a3
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
        beq.s   .br_dots
        subq.w  #1,d6
.br_vl: move.w  (a3)+,d0
        move.w  (a3)+,d1
        move.w  (a3)+,d2
        bsr.w   .br_vline
        dbra    d6,.br_vl

.br_dots:
        move.w  d7,DB_RLCNT(a6)
        bsr.w   ste_bk_draw_dots
        movem.l (sp)+,d0-d7/a0-a3/a5
.bdr_done_ret:
        rts

; Direct CPU Horizontal radar line: d0=sx1, d1=sy, d2=sx2 -> save+draw black col 9
.br_hline:
        cmpi.w  #PITCH_VIS_H,d1
        bcc.w   .bh_ret
        cmpi.w  #28,d7
        bcc.w   .bh_ret
        add.w   STE_BK_HSCR(pc),d0
        add.w   STE_BK_HSCR(pc),d2
        move.w  d0,d3
        andi.w  #15,d3
        move.w  #$ffff,d4
        lsr.w   d3,d4                   ; m0 (left endmask)
        move.w  d2,d3
        andi.w  #15,d3
        moveq   #15,d5
        sub.w   d3,d5
        move.w  #$ffff,d3
        lsl.w   d5,d3                   ; m2 (right endmask)
        lsr.w   #4,d0
        lsr.w   #4,d2
        sub.w   d0,d2
        blt.s   .bh_ret
        addq.w  #1,d2                   ; word_cols (>= 1)
        move.w  d2,d5
        lsl.w   #3,d5
        lea     0(a5,d5.w),a0
        cmpa.l  STE_BK_REND(pc),a0
        bhi.s   .bh_ret
        lsl.w   #3,d0
        ext.l   d0                      ; rel_x_byte_off
        bsr.w   ste_sy_ptr              ; a0 = dst on ring
        move.l  a0,(a2)+                ; RLR +0: dst
        move.l  a5,(a2)+                ; RLR +4: sav
        move.w  d2,(a2)+                ; RLR +8: cnt
        clr.w   (a2)+                   ; RLR +10: stride_flag = 0 (horiz)
        addq.w  #1,d7
        cmpi.w  #1,d2
        bne.s   .bh_multi
        and.w   d3,d4                   ; single word: m0 & m2
        bra.s   .bh_last
.bh_multi:
        ; First word with m0 = d4
        move.w  d4,d0
        not.w   d0
        move.l  (a0),(a5)+
        move.l  4(a0),(a5)+
        or.w    d4,(a0)+
        and.w   d0,(a0)+
        and.w   d0,(a0)+
        or.w    d4,(a0)+
        subq.w  #2,d2
        ble.s   .bh_tail
        subq.w  #1,d2
.bh_mid:
        move.l  (a0),(a5)+
        move.l  4(a0),(a5)+
        move.l  #$ffff0000,(a0)+
        move.l  #$0000ffff,(a0)+
        dbra    d2,.bh_mid
.bh_tail:
        move.w  d3,d4                   ; last word uses m2
.bh_last:
        move.w  d4,d0
        not.w   d0
        move.l  (a0),(a5)+
        move.l  4(a0),(a5)+
        or.w    d4,(a0)+
        and.w   d0,(a0)+
        and.w   d0,(a0)+
        or.w    d4,(a0)
.bh_ret:
        rts

; Direct CPU Vertical radar line (Y_STEP=4, ring-wrap splitting!): d0=sx, d1=sy1, d2=sy2
.br_vline:
        cmpi.w  #320,d0
        bcc.s   .bv_ret
        cmpi.w  #PITCH_VIS_H,d1
        bcc.s   .bv_ret
        cmpi.w  #PITCH_VIS_H,d2
        bcs.s   .bv_y2
        move.w  #(PITCH_VIS_H-1),d2
.bv_y2: sub.w   d1,d2
        blt.s   .bv_ret
        addq.w  #4,d2
        lsr.w   #2,d2                   ; d2 = total dots (Y_STEP=4)
        add.w   STE_BK_HSCR(pc),d0
        move.w  d0,d3
        andi.w  #15,d3
        moveq   #15,d5
        sub.w   d3,d5
        moveq   #0,d4
        bset    d5,d4                   ; d4 = single-bit mask
        lsr.w   #4,d0
        lsl.w   #3,d0
        ext.l   d0                      ; d0.l = rel_x_byte_off
        tst.w   STE_BIG_RAM
        bne.s   .bv_big
        add.w   STE_BK_Y0(pc),d1
        cmpi.w  #RING_H,d1
        blt.s   .bv_yr1
        subi.w  #RING_H,d1
.bv_yr1:
        move.w  d2,d3
        subq.w  #1,d3
        lsl.w   #2,d3
        add.w   d1,d3
        cmpi.w  #RING_H,d3
        blt.s   .bv_1m_one
        move.w  #(RING_H-1),d3
        sub.w   d1,d3
        lsr.w   #2,d3
        addq.w  #1,d3                   ; cnt1
        move.w  d2,d5
        sub.w   d3,d5                   ; cnt2
        move.w  d5,-(sp)
        move.w  d3,d5
        lsl.w   #2,d5
        add.w   d1,d5
        subi.w  #RING_H,d5              ; yr2
        move.w  d5,-(sp)
        move.w  d3,d2
        bsr.s   .bv_1m_emit
        move.w  (sp)+,d1
        move.w  (sp)+,d2
        ble.s   .bv_ret
.bv_1m_one:
        bsr.s   .bv_1m_emit
.bv_ret:
        rts

.bv_big:
        bsr.w   ste_sy_ptr              ; a0 = DB_START + sy1*168 + rel_x
        bra.s   .bv_emit_ptr
.bv_1m_emit:
        add.w   d1,d1
        lea     STE_Y168_TBL.l,a0
        move.w  0(a0,d1.w),d1
        andi.l  #$ffff,d1
        add.l   d0,d1
        movea.l DB_WRAP(a6),a0
        adda.l  d1,a0
.bv_emit_ptr:
        cmpi.w  #28,d7
        bcc.s   .be_ret
        move.l  STE_BK_REND(pc),d5
        sub.l   a5,d5
        lsr.l   #3,d5
        ble.s   .be_ret
        cmp.w   d5,d2
        ble.s   .be_ok
        move.w  d5,d2
.be_ok: move.l  a0,(a2)+                ; RLR +0: dst
        move.l  a5,(a2)+                ; RLR +4: sav
        move.w  d2,(a2)+                ; RLR +8: cnt
        move.w  #1,(a2)+                ; RLR +10: stride_flag = 1 (vert 4 lines)
        addq.w  #1,d7
        move.w  d4,d5
        not.w   d5                      ; d5 = ~mask
        subq.w  #1,d2
.be_lp: move.l  (a0),(a5)+
        move.l  4(a0),(a5)+
        or.w    d4,(a0)+
        and.w   d5,(a0)+
        and.w   d5,(a0)+
        or.w    d4,(a0)
        lea     (4*RING_STRIDE-6)(a0),a0
        dbra    d2,.be_lp
.be_ret:
        rts

; Pre-bake 16 merged radar word lists ($10e800..$1127ff) once per radar scale change (2 MB+ STE)!
ste_rad_bake_big:
        movem.l d0-d7/a0-a5,-(sp)
        moveq   #0,d5                   ; hscr = 0..15
.rbk_hs:
        ; 1. Clear 200 x 21-word (8,400B = 2,100 longs) 1bpp scratch bitmap at $10c400
        lea     $10c400.l,a0
        move.w  #2099,d0
.rbk_cl:
        clr.l   (a0)+
        dbra    d0,.rbk_cl
        lea     $10c400.l,a1
        lea     STE_RAD_CACHE.l,a3
        ; 2. Plot HCNT horizontal lines
        move.w  STE_RAD_C_HCNT(pc),d6
        beq.s   .rbk_vs
        subq.w  #1,d6
.rbk_hl:
        move.w  (a3)+,d0                ; sx1
        move.w  (a3)+,d1                ; sy
        move.w  (a3)+,d2                ; sx2
        cmpi.w  #PITCH_VIS_H,d1
        bcc.s   .rbk_hn
        add.w   d5,d0
        add.w   d5,d2
        mulu.w  #42,d1                  ; sy * 42B (21 words/row)
        lea     0(a1,d1.l),a0
.rbk_hx:
        cmp.w   d2,d0
        bgt.s   .rbk_hn
        cmpi.w  #336,d0
        bcc.s   .rbk_hn
        move.w  d0,d3
        lsr.w   #4,d3
        add.w   d3,d3
        move.w  d0,d4
        not.w   d4
        andi.w  #15,d4
        move.w  0(a0,d3.w),d7
        bset    d4,d7
        move.w  d7,0(a0,d3.w)
        addq.w  #1,d0
        bra.s   .rbk_hx
.rbk_hn:
        dbra    d6,.rbk_hl
        ; 3. Plot VCNT vertical dotted lines (Y_STEP=4)
.rbk_vs:
        move.w  STE_RAD_C_VCNT(pc),d6
        beq.s   .rbk_pk
        subq.w  #1,d6
.rbk_vl:
        move.w  (a3)+,d0                ; sx
        move.w  (a3)+,d1                ; sy1
        move.w  (a3)+,d2                ; sy2
        cmpi.w  #320,d0
        bcc.s   .rbk_vn
        cmpi.w  #PITCH_VIS_H,d2
        bcs.s   .rbk_vy2
        move.w  #(PITCH_VIS_H-1),d2
.rbk_vy2:
        add.w   d5,d0
        move.w  d0,d3
        lsr.w   #4,d3
        add.w   d3,d3                   ; word col byte offset
        move.w  d0,d4
        not.w   d4
        andi.w  #15,d4                  ; bit index (15 - (x&15))
.rbk_vy:
        cmp.w   d2,d1
        bgt.s   .rbk_vn
        move.w  d1,d7
        mulu.w  #42,d7
        add.w   d3,d7
        move.w  0(a1,d7.l),d0
        bset    d4,d0
        move.w  d0,0(a1,d7.l)
        addq.w  #4,d1
        bra.s   .rbk_vy
.rbk_vn:
        dbra    d6,.rbk_vl
        ; 4. Pack non-zero words into $10e800 + hscr*2048 as [count.w, pad.w, (delta.w, m.w, inv_m_l.l)...]
.rbk_pk:
        moveq   #0,d0
        move.w  d5,d0
        lsl.l   #8,d0
        lsl.l   #3,d0                   ; hscr * 2048
        lea     $10e800.l,a4
        adda.l  d0,a4
        movea.l a4,a5                   ; header ptr for count.w
        clr.l   (a4)+                   ; [count.w=0, pad.w=0]
        movea.l a1,a0                   ; $10c400
        moveq   #0,d2                   ; prev_off = 0
        moveq   #0,d3                   ; rel_off = 0, +8 per word (< 32,767!)
        moveq   #0,d7                   ; emitted word count (cap <= 254)
        move.w  #(194*21-1),d6
.rbk_sc:
        move.w  (a0)+,d0
        beq.s   .rbk_sn
        cmpi.w  #254,d7
        bcc.s   .rbk_sd
        move.w  d3,d1
        sub.w   d2,d1                   ; delta = rel_off - prev_off (>= 0, < 32,767!)
        move.w  d3,d2                   ; prev_off = rel_off
        move.w  d1,(a4)+                ; +0: delta.w
        move.w  d0,(a4)+                ; +2: m.w
        not.w   d0
        move.w  d0,(a4)+                ; +4: ~m.w
        move.w  d0,(a4)+                ; +6: ~m.w
        addq.w  #1,d7
.rbk_sn:
        addq.w  #8,d3
        dbra    d6,.rbk_sc
.rbk_sd:
        move.w  d7,(a5)
        addq.w  #1,d5
        cmpi.w  #16,d5
        blt.w   .rbk_hs
        movem.l (sp)+,d0-d7/a0-a5
        rts

; 128-byte pre-shifted radar dot LUT: [inv_m_long.l, m_long.l] for sub_x = 0..15
ste_dot_lut:
        dc.l    $3fff3fff,$c000c000, $9fff9fff,$60006000, $cfffcfff,$30003000, $e7ffe7ff,$18001800
        dc.l    $f3fff3ff,$0c000c00, $f9fff9ff,$06000600, $fcfffcff,$03000300, $fe7ffe7f,$01800180
        dc.l    $ff3fff3f,$00c000c0, $ff9fff9f,$00600060, $ffcfffcf,$00300030, $ffe7ffe7,$00180018
        dc.l    $fff3fff3,$000c000c, $fff9fff9,$00060006, $fffcfffc,$00030003, $fffefffe,$00010001

; Draw 23 transparent 2x1 radar dots onto Backbuffer
ste_bk_draw_dots:
        movea.l DB_RDR(a6),a2
        lea     STE_Y168_TBL.l,a3
        moveq   #0,d7
        tst.w   STE_BIG_RAM
        beq.w   .bd_1m
        ; === 2 MB+ STE Inlined LUT Dot Drawer (zero bsr, zero variable shifts, 32-bit plane ops!) ===
        movem.l a1/a4,-(sp)
        move.l  -$0e14(a4),-(sp)        ; +4(sp): ball_x.w | ball_y.w
        move.l  -$4fbc(a4),-(sp)        ; +0(sp): Away 11 players ptr
        movea.l -$5012(a4),a5           ; Home 11 players ptr
        movea.l DB_START(a6),a1
        lea     ste_dot_lut(pc),a4
        move.w  STE_BK_HSCR(pc),d6
        moveq   #10,d5
.bd2_hl:
        tst.w   $0c(a5)
        beq.s   .bd2_hn
        move.w  $20(a5),d0
        cmpi.w  #318,d0
        bcc.s   .bd2_hn
        move.w  $22(a5),d1
        cmpi.w  #194,d1
        bcc.s   .bd2_hn
        add.w   d6,d0
        move.w  d0,d2
        andi.w  #15,d2
        lsl.w   #3,d2
        andi.w  #$fff0,d0
        lsr.w   #1,d0
        add.w   d1,d1
        add.w   0(a3,d1.w),d0
        lea     0(a1,d0.w),a0
        move.l  a0,(a2)+
        move.l  (a0),(a2)+
        move.l  4(a0),(a2)+
        addq.w  #1,d7
        move.w  0(a4,d2.w),d0           ; ~m
        move.w  4(a4,d2.w),d3           ;  m
        and.w   d0,(a0)
        or.w    d3,2(a0)
        and.w   d0,4(a0)
        or.w    d3,6(a0)
.bd2_hn:
        lea     $186(a5),a5
        dbra    d5,.bd2_hl

        movea.l (sp)+,a5                ; Away 11 players ptr
        moveq   #10,d5
.bd2_al:
        tst.w   $0c(a5)
        beq.s   .bd2_an
        move.w  $20(a5),d0
        cmpi.w  #318,d0
        bcc.s   .bd2_an
        move.w  $22(a5),d1
        cmpi.w  #194,d1
        bcc.s   .bd2_an
        add.w   d6,d0
        move.w  d0,d2
        andi.w  #15,d2
        lsl.w   #3,d2
        andi.w  #$fff0,d0
        lsr.w   #1,d0
        add.w   d1,d1
        add.w   0(a3,d1.w),d0
        lea     0(a1,d0.w),a0
        move.l  a0,(a2)+
        move.l  (a0),(a2)+
        move.l  4(a0),(a2)+
        addq.w  #1,d7
        move.l  0(a4,d2.w),d0           ; ~m : ~m
        move.l  4(a4,d2.w),d3           ;  m :  m
        and.l   d0,(a0)                 ; P0 &= ~m, P1 &= ~m!
        or.l    d3,4(a0)                ; P2 |=  m, P3 |=  m!
.bd2_an:
        lea     $186(a5),a5
        dbra    d5,.bd2_al

        move.w  (sp)+,d0                ; ball_x
        move.w  (sp)+,d1                ; ball_y
        cmpi.w  #318,d0
        bcc.s   .bd2_dn
        cmpi.w  #194,d1
        bcc.s   .bd2_dn
        add.w   d6,d0
        move.w  d0,d2
        andi.w  #15,d2
        lsl.w   #3,d2
        andi.w  #$fff0,d0
        lsr.w   #1,d0
        add.w   d1,d1
        add.w   0(a3,d1.w),d0
        lea     0(a1,d0.w),a0
        move.l  a0,(a2)+
        move.l  (a0),(a2)+
        move.l  4(a0),(a2)+
        addq.w  #1,d7
        move.l  0(a4,d2.w),d0           ; ~m : ~m
        move.w  4(a4,d2.w),d3           ;  m
        and.l   d0,(a0)
        and.w   d0,4(a0)
        or.w    d3,6(a0)
.bd2_dn:
        movem.l (sp)+,a1/a4
        move.w  d7,DB_RDCNT(a6)
        rts

.bd_1m:
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
        movea.l DB_START(a6),a0
        tst.w   STE_BIG_RAM
        bne.s   .bdd_lu
        add.w   STE_BK_Y0(pc),d1
        cmpi.w  #RING_H,d1
        blt.s   .bdd_1m
        subi.w  #RING_H,d1
.bdd_1m:
        movea.l DB_WRAP(a6),a0
.bdd_lu:
        add.w   d1,d1
        moveq   #0,d2
        move.w  0(a3,d1.w),d2
        add.l   d0,d2
        adda.l  d2,a0
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
; ---------------------------------------------------------------------------
ste_bk_draw_ul:
        movem.l d0-d4/d7/a0/a2/a5,-(sp)
        move.w  DB_RDCNT(a6),d7
        move.w  d7,d0
        mulu.w  #12,d0
        movea.l DB_RDR(a6),a2
        adda.l  d0,a2
        lea     -$5012(a4),a0
        tst.l   $12(a0)
        beq.s   .ul_away
        movea.l $16(a0),a5
        move.w  #$ffff,d4
        bsr.s   .ul_one
.ul_away:
        lea     -$4fbc(a4),a0
        tst.l   $12(a0)
        beq.s   .ul_dash
        movea.l $16(a0),a5
        move.w  #$ffff,d4
        bsr.s   .ul_one
.ul_dash:
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
        tst.l   $b8(a5)
        beq.s   .ul_ret
        cmpi.w  #46,d7
        bcc.s   .ul_ret
        move.w  (a5),d0
        addi.w  #168,d0
        sub.w   STE_CUR_WX(pc),d0
        cmpi.w  #305,d0
        bcc.s   .ul_ret
        move.w  4(a5),d1
        addi.w  #72,d1
        sub.w   STE_CUR_WY(pc),d1
        cmpi.w  #PITCH_VIS_H,d1
        bcc.s   .ul_ret
        add.w   STE_BK_HSCR(pc),d0
        move.w  d0,d2
        andi.w  #15,d2
        moveq   #0,d3
        move.w  d4,d3
        swap    d3
        lsr.l   d2,d3
        lsr.w   #4,d0
        lsl.w   #3,d0
        ext.l   d0
        bsr.w   ste_sy_ptr
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
; Step D: Batched Active Sprites (pushes ALL visible sprites -> ONE TRAP #8 cmd 3!)
; ---------------------------------------------------------------------------
ste_bk_draw_spr:
        tst.w   STE_SPR_CNT
        beq.w   .bds_ret
        movem.l d0-d7/a0-a3/a5,-(sp)
        lea     STE_SPR_LIST.l,a5       ; active sprite source list
        movea.l DB_STK(a6),a3           ; Backbuffer sprite draw/restore stack
        moveq   #0,d6                   ; drawn count (0..31)
        moveq   #0,d7                   ; current slot index (0..STE_SPR_CNT-1)
.bds_lp:
        cmp.w   STE_SPR_CNT(pc),d7
        bcc.w   .bds_done
        movea.l (a5),a0                 ; KO2 save-record ptr (a3)
        tst.l   (a0)                    ; did KO2 clear (a3) directly ($1a342/$162b2/$1a826/reset)?
        bne.s   .bds_alive
        ; Purge dead sprite slot in-place (swap with last, re-test a5!)
        move.w  STE_SPR_CNT(pc),d0
        subq.w  #1,d0
        move.w  d0,STE_SPR_CNT
        cmp.w   d7,d0
        beq.w   .bds_done
        lsl.w   #4,d0
        lea     STE_SPR_LIST.l,a0
        adda.w  d0,a0
        movea.l a5,a1
        move.l  (a0)+,(a1)+
        move.l  (a0)+,(a1)+
        move.l  (a0)+,(a1)+
        move.l  (a0)+,(a1)+
        bra.s   .bds_lp
.bds_alive:
        move.w  10(a5),d1               ; world_y
        sub.w   STE_CUR_WY(pc),d1       ; scr_y
        blt.w   .bds_nxt
        cmpi.w  #PITCH_VIS_H,d1
        bge.w   .bds_nxt
        move.w  #PITCH_VIS_H,d3
        sub.w   d1,d3
        cmpi.w  #16,d3
        ble.s   .bds_hok
        moveq   #16,d3                  ; d3 = h (1..16)
.bds_hok:
        move.w  8(a5),d0                ; world_x
        move.w  d0,d2
        andi.w  #15,d2                  ; d2 = skew (0..15)
        lsr.w   #4,d0                   ; world_col (0..79)
        sub.w   DB_TX(a6),d0            ; rel_col
        blt.s   .bds_nxt
        cmpi.w  #20,d0
        bgt.s   .bds_nxt
        bne.s   .bds_xok
        tst.w   d2
        bne.s   .bds_nxt
.bds_xok:
        lsl.w   #3,d0
        ext.l   d0                      ; rel_x_byte_off = rel_col * 8
        move.w  d1,d4                   ; save scr_y
        bsr.w   ste_sy_ptr              ; a0 = dst_top (clobbers d1)
        tst.w   STE_BIG_RAM
        bne.s   .bds_nowr
        move.w  d4,d1
        add.w   STE_BK_Y0(pc),d1
        cmpi.w  #RING_H,d1
        blt.s   .bds_y1m
        subi.w  #RING_H,d1
.bds_y1m:
        move.w  d1,d4
        add.w   d3,d4
        cmpi.w  #RING_H,d4
        ble.s   .bds_nowr
        move.w  #RING_H,d4
        sub.w   d1,d4                   ; h1 (1..15)
        move.w  d3,d5
        sub.w   d4,d5                   ; h2 (1..15)
        movea.l DB_WRAP(a6),a1
        adda.l  d0,a1                   ; dst_bot = RING + tx*8 + rel_col*8
        bra.s   .bds_rec
.bds_nowr:
        move.w  d3,d4                   ; h1 = h
        moveq   #0,d5                   ; h2 = 0
        suba.l  a1,a1                   ; dst_bot = 0
.bds_rec:
        ; Push 16-byte sprite record onto DB_STK:
        ; [+0: dst_top.l, +4: dst_bot.l, +8: h1.b, +9: h2.b, +10: skew.w, +12: src.l]
        move.l  a0,(a3)+
        move.l  a1,(a3)+
        move.b  d4,(a3)+
        move.b  d5,(a3)+
        move.w  d2,(a3)+
        move.l  4(a5),(a3)+
        addq.w  #1,d6
        cmpi.w  #32,d6
        bcc.s   .bds_done
.bds_nxt:
        lea     16(a5),a5
        addq.w  #1,d7
        bra.w   .bds_lp
.bds_done:
        move.w  d6,DB_SCNT(a6)
        beq.s   .bds_fin
        movea.l DB_STK(a6),a0
        movea.l DB_SAV(a6),a1
        move.w  d6,d1
        moveq   #3,d0                   ; ONE batched TRAP #8 cmd 3 for ALL sprites!
        trap    #8
.bds_fin:
        movem.l (sp)+,d0-d7/a0-a3/a5
.bds_ret:
        rts

; ---------------------------------------------------------------------------
; TRAP #8 ($a0.w) — Supervisor STE Blitter Dispatcher ($c0 HOG on 2MB+, $80 on 1MB)
;   cmd 2 : reverse-LIFO restore of d1.w sprite records (a0=STK_END, a1=SAV_END)
;   cmd 3 : batched save+draw of d1.w sprites (a0=DB_STK, a1=DB_SAV)
;   cmd 4 : clear STE_RING_A, STE_RING_B[, DB_C]
;   cmd 6 : batched 3-box HUD save+draw (d1.w=segs, d2.w=skew, a0=DB_HUDSAV)
;   cmd 7 : reverse-LIFO HUD restore (d1.w=segs, a0=DB_HUDSAV)
;   cmd 8 : 21-tile horizontal row blit (mirrored +RING_BYTES on 2 MB+ STE)
;   cmd 9 : 14-tile vertical col blit   (mirrored +RING_BYTES on 2 MB+ STE)
; ---------------------------------------------------------------------------
ste_trap8_handler:
        cmpi.w  #2,d0
        beq.s   .cmd2_rest_lifo
        cmpi.w  #3,d0
        beq.w   .cmd3_spr
        cmpi.w  #4,d0
        beq.w   .cmd4_clr
        cmpi.w  #6,d0
        beq.w   .cmd6_hud_draw
        cmpi.w  #7,d0
        beq.w   .cmd7_hud_rest
        cmpi.w  #8,d0
        beq.w   .cmd8_blit_row
        bra.w   .cmd9_blit_col

.blt80: tst.w   STE_BIG_RAM
        beq.s   .b80_sh
        move.b  #$c0,BLT_LINE.w
        rts
.b80_sh: move.b #$80,BLT_LINE.w
.b80_w: bset    #7,BLT_LINE.w
        nop
        bne.s   .b80_w
        rts

; --- cmd 2: Batched Reverse-LIFO sprite restore (d1.w records ending at a0, SAV_END in a1) ---
.cmd2_rest_lifo:
        movem.l d2-d3/a2,-(sp)
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
        tst.w   STE_BIG_RAM
        beq.s   .c2_lp
        moveq   #-$40,d2                ; $c0 HOG inline (4w on skew==0, 8w on skew!=0!)
        lea     BLT_SRC_ADDR.w,a2
.c2_blp:
        lea     -16(a0),a0
        lea     -256(a1),a1
        moveq   #0,d0
        move.b  8(a0),d0
        beq.s   .c2_bsk
        tst.w   10(a0)
        bne.s   .c2_w8
        move.w  #(RING_STRIDE-6),12(a2)
        move.w  #4,18(a2)
        bra.s   .c2_go
.c2_w8: move.w  #(RING_STRIDE-14),12(a2)
        move.w  #8,18(a2)
.c2_go: move.l  a1,(a2)
        move.l  (a0),14(a2)
        move.w  d0,20(a2)
        move.b  d2,24(a2)
.c2_bsk:
        dbra    d1,.c2_blp
        movem.l (sp)+,d2-d3/a2
        rte
.c2_lp: lea     -16(a0),a0
        lea     -256(a1),a1
        move.l  a1,BLT_SRC_ADDR.w
        move.l  (a0),BLT_DST_ADDR.w
        moveq   #0,d2
        move.b  8(a0),d2                ; h1 (1..16)
        move.w  d2,BLT_YCOUNT.w
        bsr.w   .b80_sh
        moveq   #0,d3
        move.b  9(a0),d3                ; h2 (0..15)
        beq.s   .c2_nxt
        move.l  4(a0),BLT_DST_ADDR.w
        move.w  d3,BLT_YCOUNT.w
        bsr.w   .b80_sh
.c2_nxt:
        dbra    d1,.c2_lp
        movem.l (sp)+,d2-d3/a2
        rte

; --- cmd 3: Batched Save-under + Direct NFSR 4bpp Masked Sprite Draw (d1.w sprites, a0=STK, a1=SAV) ---
.cmd3_spr:
        movem.l d2-d7/a2-a6,-(sp)
        movea.l a0,a6                   ; a6 = DB_STK cursor
        movea.l a1,a5                   ; a5 = DB_SAV slot
        lea     STE_MASK_BUF.l,a3
        move.w  #-1,BLT_ENDMASK2.w
        move.w  d1,d6
        subq.w  #1,d6
        tst.w   STE_BIG_RAM
        beq.w   .c3_sp
        ; === Fast 2 MB+ STE Inline HOG Sprite Loop (CPU 1-pass mask+trim + empty plane skip!) ===
        lea     BLT_SRC_ADDR.w,a0
        moveq   #-$40,d7                ; $c0 = HOG
.c3_bsp:
        movea.l 12(a6),a1               ; KO2 3bpp sprite src
        movea.l (a6),a4                 ; dst_top
        moveq   #0,d4
        move.b  8(a6),d4                ; h1 (1..16)
        subq.w  #1,d4
.c3b_tt:
        move.w  (a1),d0
        or.w    $28(a1),d0
        or.w    $50(a1),d0
        bne.s   .c3b_tf
        lea     $78(a1),a1
        lea     RING_STRIDE(a4),a4
        dbra    d4,.c3b_tt
        clr.b   8(a6)                   ; 100% transparent frame -> skip draw & cmd 2 restore!
        bra.w   .c3b_nx
.c3b_tf:
        move.l  a4,(a6)                 ; cmd 2 restores trimmed dst_top!
        lea     STE_MASK_BUF.l,a3
        movea.l a1,a2
        moveq   #0,d2                   ; any_p0
        moveq   #0,d3                   ; any_p1
        moveq   #0,d5                   ; any_p2
        move.w  d4,d1
.c3b_mb:
        move.w  (a2),d0
        or.w    d0,d2
        move.w  $28(a2),d4
        or.w    d4,d3
        or.w    d4,d0
        move.w  $50(a2),d4
        or.w    d4,d5
        or.w    d4,d0
        move.w  d0,(a3)+
        lea     $78(a2),a2
        dbra    d1,.c3b_mb
.c3b_bl:
        tst.w   -(a3)
        beq.s   .c3b_bl
        addq.l  #2,a3
        move.l  a3,d4
        lea     STE_MASK_BUF.l,a3
        sub.l   a3,d4
        lsr.w   #1,d4                   ; d4 = exact trimmed height (1..16)
        move.b  d4,8(a6)                ; cmd 2 restores trimmed height!

        ; Save-under (4 words on skew==0, 8 words on skew!=0; ENDMASK1/3=$ffff, SKEW=0!)
        moveq   #-1,d0
        move.w  d0,4(a0)                ; ENDMASK1 = $ffff
        move.w  d0,8(a0)                ; ENDMASK3 = $ffff
        clr.b   25(a0)                  ; SKEW = 0
        move.w  #2,-4(a0)               ; SRC_XINC = 2
        move.w  #2,10(a0)               ; DST_XINC = 2
        move.w  #2,12(a0)               ; DST_YINC = 2
        move.w  #$0203,22(a0)
        move.l  a4,(a0)
        move.l  a5,14(a0)
        move.w  d4,20(a0)
        move.w  10(a6),d1               ; skew (0..15)
        bne.s   .c3b_s8
        move.w  #(RING_STRIDE-6),-2(a0) ; SRC_YINC = 162 (4 words)
        move.w  #4,18(a0)               ; XCOUNT = 4
        move.b  d7,24(a0)               ; HOG save-under (4w)
        move.w  #1,18(a0)
        clr.w   10(a0)
        move.w  #RING_STRIDE,12(a0)
        bra.s   .c3b_m
.c3b_s8:
        move.w  #(RING_STRIDE-14),-2(a0) ; SRC_YINC = 154 (8 words)
        move.w  #8,18(a0)               ; XCOUNT = 8
        move.b  d7,24(a0)               ; HOG save-under (8w)
        moveq   #-1,d0
        lsr.w   d1,d0
        move.w  d0,4(a0)                ; ENDMASK1
        not.w   d0
        move.w  d0,8(a0)                ; ENDMASK3
        move.w  #2,18(a0)               ; XCOUNT = 2
        move.w  #8,10(a0)               ; DST_XINC = 8
        move.w  #(RING_STRIDE-8),12(a0) ; DST_YINC = 160
        ori.b   #$40,d1
        move.b  d1,25(a0)               ; SKEW = NFSR | skew
.c3b_m:
        clr.w   -4(a0)                  ; SRC_XINC = 0
        move.w  #2,-2(a0)               ; SRC_YINC = 2
        move.w  #$0204,22(a0)           ; AND ~MASK on P0, P1, P2
        move.l  a3,(a0)
        move.l  a4,14(a0)
        move.w  d4,20(a0)
        move.b  d7,24(a0)
        move.l  a3,(a0)
        lea     2(a4),a2
        move.l  a2,14(a0)
        move.w  d4,20(a0)
        move.b  d7,24(a0)
        move.l  a3,(a0)
        addq.l  #2,a2
        move.l  a2,14(a0)
        move.w  d4,20(a0)
        move.b  d7,24(a0)
        move.w  #$0207,22(a0)           ; OR MASK->P3, then ONLY non-empty P0/P1/P2!
        move.l  a3,(a0)
        addq.l  #2,a2
        move.l  a2,14(a0)
        move.w  d4,20(a0)
        move.b  d7,24(a0)
        move.w  #$78,-2(a0)             ; SRC_YINC = $78
        tst.w   d2
        beq.s   .c3b_np0
        move.l  a1,(a0)
        move.l  a4,14(a0)
        move.w  d4,20(a0)
        move.b  d7,24(a0)
.c3b_np0:
        tst.w   d3
        beq.s   .c3b_np1
        lea     $28(a1),a2
        move.l  a2,(a0)
        lea     2(a4),a2
        move.l  a2,14(a0)
        move.w  d4,20(a0)
        move.b  d7,24(a0)
.c3b_np1:
        tst.w   d5
        beq.s   .c3b_nx
        lea     $50(a1),a2
        move.l  a2,(a0)
        lea     4(a4),a2
        move.l  a2,14(a0)
        move.w  d4,20(a0)
        move.b  d7,24(a0)
.c3b_nx:
        lea     16(a6),a6
        lea     256(a5),a5
        dbra    d6,.c3_bsp
        movem.l (sp)+,d2-d7/a2-a6
        rte

.c3_sp:
        movea.l 12(a6),a1               ; KO2 3bpp sprite src
        ; 1. Build 16-word 1bpp sprite mask in STE_MASK_BUF
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

        movea.l (a6),a4                 ; dst_top
        moveq   #0,d4
        move.b  8(a6),d4                ; h1
        move.w  10(a6),d1               ; skew
        move.l  a5,-(sp)
        move.l  a3,-(sp)
        bsr.w   .c3_seg
        movea.l (sp)+,a3
        movea.l (sp)+,a5
        moveq   #0,d2
        move.b  9(a6),d2                ; h2
        beq.s   .c3_nx
        move.w  d4,d0
        mulu.w  #$78,d0
        adda.l  d0,a1
        move.w  d4,d0
        lsl.w   #4,d0
        move.l  a5,-(sp)
        adda.w  d0,a5
        move.w  d4,d0
        add.w   d0,d0
        move.l  a3,-(sp)
        adda.w  d0,a3
        movea.l 4(a6),a4                ; dst_bot
        move.w  d2,d4                   ; h2
        bsr.w   .c3_seg
        movea.l (sp)+,a3
        movea.l (sp)+,a5
.c3_nx: lea     16(a6),a6
        lea     256(a5),a5
        dbra    d6,.c3_sp
        movem.l (sp)+,d2-d7/a2-a6
        rte

.c3_seg:
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
        ori.b   #$40,d0
        move.b  d0,BLT_SKEW.w
.c3s_m:
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
        move.w  #$0207,BLT_HOP.w
        move.l  a3,BLT_SRC_ADDR.w
        addq.l  #2,a2
        move.l  a2,BLT_DST_ADDR.w
        move.w  d4,BLT_YCOUNT.w
        bsr.w   .blt80
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

; --- cmd 4: Zero Rings ---
.cmd4_clr:
        moveq   #-1,d0
        move.l  d0,BLT_ENDMASK1.w
        move.w  d0,BLT_ENDMASK3.w
        move.w  #2,BLT_DST_XINC.w
        move.w  #2,BLT_DST_YINC.w
        clr.w   BLT_HOP.w
        clr.b   BLT_SKEW.w
        move.w  #84,BLT_XCOUNT.w
        tst.w   STE_BIG_RAM
        bne.s   .c4_big
        move.l  #STE_RING_A,BLT_DST_ADDR.w
        move.w  #456,BLT_YCOUNT.w
        move.b  #$c0,BLT_LINE.w
        rte
.c4_big:
        lea     DB_A(pc),a0
        move.l  DB_RING(a0),BLT_DST_ADDR.w
        move.w  #(2*RING_H+3),BLT_YCOUNT.w
        move.b  #$c0,BLT_LINE.w
        lea     DB_B(pc),a0
        move.l  DB_RING(a0),BLT_DST_ADDR.w
        move.w  #(2*RING_H+3),BLT_YCOUNT.w
        move.b  #$c0,BLT_LINE.w
        lea     DB_C(pc),a0
        move.l  DB_RING(a0),BLT_DST_ADDR.w
        move.w  #(2*RING_H+3),BLT_YCOUNT.w
        move.b  #$c0,BLT_LINE.w
        rte

; --- cmd 6: Batched 3-Box HUD Save-Under + Transparent 4bpp Draw (d1.w=segs, d2.w=skew, a0=DB_HUDSAV) ---
.cmd6_hud_draw:
        movem.l d2-d7/a2-a6,-(sp)
        lea     STE_HUD_Q.l,a3          ; draw Q [pdata.l, plane_sz.w, xcnt.w, sy.w, e1.w, e3.w]
        move.w  d2,d7                   ; skew_val
        move.w  d1,d6
        subq.w  #1,d6
.c6_lp:
        movea.l (a0)+,a4                ; dst
        movea.l (a0)+,a5                ; sav
        move.w  (a0)+,d3                ; xcnt (4bpp words)
        move.w  (a0)+,d4                ; ycnt (h)
        ; A. Save-under xcnt*4 words
        moveq   #-1,d0
        move.l  d0,BLT_ENDMASK1.w
        move.w  d0,BLT_ENDMASK3.w
        move.w  #2,BLT_SRC_XINC.w
        move.w  d3,d0
        lsl.w   #3,d0
        move.w  #170,d5
        sub.w   d0,d5
        move.w  d5,BLT_SRC_YINC.w
        move.w  #2,BLT_DST_XINC.w
        move.w  #2,BLT_DST_YINC.w
        move.w  d3,d5
        lsl.w   #2,d5
        move.w  d5,BLT_XCOUNT.w
        move.w  #$0203,BLT_HOP.w
        clr.b   BLT_SKEW.w
        move.l  a4,BLT_SRC_ADDR.w
        move.l  a5,BLT_DST_ADDR.w
        move.w  d4,BLT_YCOUNT.w
        bsr.w   .blt80

        ; B. Draw 4 planes from draw Q a3
        movea.l (a3)+,a1                ; TOTMASK pdata
        moveq   #0,d5
        move.w  (a3)+,d5                ; plane_sz
        addq.l  #2,a3                   ; skip xcnt (already d3)
        move.w  #2,BLT_SRC_XINC.w
        move.w  (a3)+,BLT_SRC_YINC.w    ; 2 or 4
        move.w  (a3)+,BLT_ENDMASK1.w    ; em1
        move.w  #-1,BLT_ENDMASK2.w
        move.w  (a3)+,BLT_ENDMASK3.w    ; em3
        move.w  (a3)+,d2                ; Q +14: bit8=has_p2, bit9=has_p1
        move.w  #8,BLT_DST_XINC.w
        move.w  #176,d1
        sub.w   d0,d1                   ; 176 - xcnt*8
        move.w  d1,BLT_DST_YINC.w
        move.w  d3,BLT_XCOUNT.w
        move.b  d7,BLT_SKEW.w

        ; Clear TOTMASK in P0, P1, P2; OR TOTMASK in P3
        tst.w   STE_BIG_RAM
        beq.w   .c6_1m
        moveq   #-$40,d1                ; $c0 HOG inline on 2MB+ STE!
        move.w  #$0204,BLT_HOP.w
        move.l  a1,BLT_SRC_ADDR.w
        move.l  a4,BLT_DST_ADDR.w
        move.w  d4,BLT_YCOUNT.w
        move.b  d1,BLT_LINE.w
        move.l  a1,BLT_SRC_ADDR.w
        lea     2(a4),a2
        move.l  a2,BLT_DST_ADDR.w
        move.w  d4,BLT_YCOUNT.w
        move.b  d1,BLT_LINE.w
        move.l  a1,BLT_SRC_ADDR.w
        addq.l  #2,a2
        move.l  a2,BLT_DST_ADDR.w
        move.w  d4,BLT_YCOUNT.w
        move.b  d1,BLT_LINE.w
        move.w  #$0207,BLT_HOP.w
        move.l  a1,BLT_SRC_ADDR.w
        addq.l  #2,a2
        move.l  a2,BLT_DST_ADDR.w
        move.w  d4,BLT_YCOUNT.w
        move.b  d1,BLT_LINE.w
        adda.l  d5,a1
        move.l  a1,BLT_SRC_ADDR.w
        move.l  a4,BLT_DST_ADDR.w
        move.w  d4,BLT_YCOUNT.w
        move.b  d1,BLT_LINE.w
        adda.l  d5,a1
        btst    #8,d2
        beq.s   .c6b_np2
        move.l  a1,BLT_SRC_ADDR.w
        lea     2(a4),a2
        move.l  a2,BLT_DST_ADDR.w
        move.w  d4,BLT_YCOUNT.w
        move.b  d1,BLT_LINE.w
.c6b_np2:
        adda.l  d5,a1
        btst    #9,d2
        beq.w   .c6_np1
        move.l  a1,BLT_SRC_ADDR.w
        lea     4(a4),a2
        move.l  a2,BLT_DST_ADDR.w
        move.w  d4,BLT_YCOUNT.w
        move.b  d1,BLT_LINE.w
        bra.w   .c6_np1

.c6_1m:
        move.w  #$0204,BLT_HOP.w
        move.l  a1,BLT_SRC_ADDR.w
        move.l  a4,BLT_DST_ADDR.w
        move.w  d4,BLT_YCOUNT.w
        bsr.w   .blt80
        move.l  a1,BLT_SRC_ADDR.w
        lea     2(a4),a2
        move.l  a2,BLT_DST_ADDR.w
        move.w  d4,BLT_YCOUNT.w
        bsr.w   .blt80
        move.l  a1,BLT_SRC_ADDR.w
        addq.l  #2,a2
        move.l  a2,BLT_DST_ADDR.w
        move.w  d4,BLT_YCOUNT.w
        bsr.w   .blt80
        move.w  #$0207,BLT_HOP.w
        move.l  a1,BLT_SRC_ADDR.w
        addq.l  #2,a2
        move.l  a2,BLT_DST_ADDR.w
        move.w  d4,BLT_YCOUNT.w
        bsr.w   .blt80
        ; OR SHAD->P0, and skip P2_HOME->P1 / P1_AWAY->P2 when box has no colored pixels!
        adda.l  d5,a1
        move.l  a1,BLT_SRC_ADDR.w
        move.l  a4,BLT_DST_ADDR.w
        move.w  d4,BLT_YCOUNT.w
        bsr.w   .blt80
        adda.l  d5,a1
        btst    #8,d2
        beq.s   .c6_np2
        move.l  a1,BLT_SRC_ADDR.w
        lea     2(a4),a2
        move.l  a2,BLT_DST_ADDR.w
        move.w  d4,BLT_YCOUNT.w
        bsr.w   .blt80
.c6_np2:
        adda.l  d5,a1
        btst    #9,d2
        beq.s   .c6_np1
        move.l  a1,BLT_SRC_ADDR.w
        lea     4(a4),a2
        move.l  a2,BLT_DST_ADDR.w
        move.w  d4,BLT_YCOUNT.w
        bsr.w   .blt80
.c6_np1:
        dbra    d6,.c6_lp
        movem.l (sp)+,d2-d7/a2-a6
        rte

; --- cmd 7: Reverse-LIFO Batched HUD Save-Under Restore (d1.w=segs, a0=DB_HUDSAV) ---
.cmd7_hud_rest:
        movem.l d2-d3,-(sp)
        move.w  d1,d0
        lsl.w   #2,d0
        move.w  d0,d2
        add.w   d0,d0
        add.w   d2,d0                   ; d1 * 12
        adda.w  d0,a0                   ; end of d1 12-byte restore records (strict reverse LIFO!)
        moveq   #-1,d0
        move.l  d0,BLT_ENDMASK1.w
        move.w  d0,BLT_ENDMASK3.w
        move.w  #2,BLT_SRC_XINC.w
        move.w  #2,BLT_SRC_YINC.w
        move.w  #2,BLT_DST_XINC.w
        move.w  #$0203,BLT_HOP.w
        clr.b   BLT_SKEW.w
        subq.w  #1,d1
.c7_lp:
        lea     -12(a0),a0
        move.l  (a0),BLT_DST_ADDR.w     ; dst
        move.l  4(a0),BLT_SRC_ADDR.w    ; sav
        move.w  8(a0),d2                ; xcnt
        move.w  d2,d3
        lsl.w   #3,d3
        move.w  #170,d0
        sub.w   d3,d0
        move.w  d0,BLT_DST_YINC.w
        lsl.w   #2,d2
        move.w  d2,BLT_XCOUNT.w
        move.w  10(a0),BLT_YCOUNT.w
        bsr.w   .blt80
        dbra    d1,.c7_lp
        movem.l (sp)+,d2-d3
        rte

; --- cmd 8: Unmirrored 21-tile Horizontal Row Blit (+ 1-blit 2MB+ strip mirror!) ---
.cmd8_blit_row:
        movem.l d3-d7/a2-a4,-(sp)
        move.w  #2,BLT_SRC_XINC.w
        move.w  #2,BLT_SRC_YINC.w
        move.w  #2,BLT_DST_XINC.w
        move.w  #(RING_STRIDE-4),BLT_DST_YINC.w
        moveq   #-1,d0
        move.l  d0,BLT_ENDMASK1.w
        move.w  d0,BLT_ENDMASK3.w
        move.w  #3,BLT_XCOUNT.w
        move.w  #$0203,BLT_HOP.w
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
        lsl.w   #4,d0
        add.w   d0,d0
        lea     STE_Y168_TBL.l,a1
        move.w  0(a1,d0.w),d0
        andi.l  #$ffff,d0
        move.w  d1,d3
        lsl.w   #3,d3
        ext.l   d3
        add.l   d3,d0
        movea.l a0,a3
        adda.l  d0,a3
        lea     STE_PIT_TILES.l,a4

        moveq   #21,d7
        moveq   #80,d0
        sub.w   d1,d0
        ble.w   .c8_done
        cmp.w   d7,d0
        bge.s   .c8_cnt
        move.w  d0,d7
.c8_cnt:
        move.w  d7,d6                   ; save n_tiles (1..21)
        move.l  a3,d5                   ; save row strip start
        subq.w  #1,d7
        tst.w   STE_BIG_RAM
        beq.s   .c8_lp
.c8_blp:
        moveq   #0,d0
        move.b  (a2)+,d0
        move.w  d0,d3
        lsl.w   #6,d0
        lsl.w   #5,d3
        add.w   d3,d0
        lea     0(a4,d0.w),a1
        move.l  a1,BLT_SRC_ADDR.w
        move.l  a3,BLT_DST_ADDR.w
        move.w  #16,BLT_YCOUNT.w
        move.b  #$c0,BLT_LINE.w
        addq.l  #8,a3
        dbra    d7,.c8_blp
        ; Mirror entire 16-scanline strip to +RING_BYTES in ONE HOG blit!
        move.w  d6,d0
        lsl.w   #3,d0
        move.w  #170,d3
        sub.w   d0,d3                   ; 170 - n_tiles*8
        move.w  d3,BLT_SRC_YINC.w
        move.w  d3,BLT_DST_YINC.w
        lsl.w   #2,d6                   ; n_tiles * 4 words
        move.w  d6,BLT_XCOUNT.w
        move.l  d5,BLT_SRC_ADDR.w
        addi.l  #RING_BYTES,d5
        move.l  d5,BLT_DST_ADDR.w
        move.w  #16,BLT_YCOUNT.w
        move.b  #$c0,BLT_LINE.w
        bra.s   .c8_done

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
        bsr.w   .b80_sh
        addq.l  #8,a3
        dbra    d7,.c8_lp
.c8_done:
        movem.l (sp)+,d3-d7/a2-a4
        rte

; --- cmd 9: Unmirrored 14-tile Vertical Column Blit (+ 1-blit 224-line 2MB+ mirror!) ---
.cmd9_blit_col:
        movem.l d3-d7/a2-a4,-(sp)
        move.w  #2,BLT_SRC_XINC.w
        move.w  #2,BLT_SRC_YINC.w
        move.w  #2,BLT_DST_XINC.w
        move.w  #(RING_STRIDE-4),BLT_DST_YINC.w
        moveq   #-1,d0
        move.l  d0,BLT_ENDMASK1.w
        move.w  d0,BLT_ENDMASK3.w
        move.w  #3,BLT_XCOUNT.w
        move.w  #$0203,BLT_HOP.w
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
        move.w  d0,d6
        lsl.w   #4,d0
        add.w   d0,d0
        lea     STE_Y168_TBL.l,a1
        move.w  0(a1,d0.w),d0
        andi.l  #$ffff,d0
        move.w  d1,d3
        lsl.w   #3,d3
        ext.l   d3
        move.l  a0,d5
        add.l   d3,d5                   ; d5 = DB_RING + tx_col*8 (row 0 of col!)
        add.l   d3,d0
        movea.l a0,a3
        adda.l  d0,a3
        lea     STE_PIT_TILES.l,a4

        moveq   #RING_ROWS,d7
        moveq   #96,d0
        sub.w   d2,d0
        ble.w   .c9_done
        cmp.w   d7,d0
        bge.s   .c9_cnt
        move.w  d0,d7
.c9_cnt:
        subq.w  #1,d7
        tst.w   STE_BIG_RAM
        beq.s   .c9_lp
.c9_blp:
        moveq   #0,d0
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
        move.b  #$c0,BLT_LINE.w
        addq.w  #1,d6
        cmpi.w  #RING_ROWS,d6
        blt.s   .c9_bst
        moveq   #0,d6
        suba.l  #(RING_BYTES-16*RING_STRIDE),a3
        bra.s   .c9_bnx
.c9_bst:
        adda.w  #(16*RING_STRIDE),a3
.c9_bnx:
        dbra    d7,.c9_blp
        ; Copy all 224 scanlines of column tx_col to +RING_BYTES in ONE HOG blit!
        move.w  #(RING_STRIDE-4),BLT_SRC_YINC.w
        move.l  d5,BLT_SRC_ADDR.w
        addi.l  #RING_BYTES,d5
        move.l  d5,BLT_DST_ADDR.w
        move.w  #RING_H,BLT_YCOUNT.w
        move.b  #$c0,BLT_LINE.w
        bra.s   .c9_done

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
        bsr.w   .b80_sh
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

