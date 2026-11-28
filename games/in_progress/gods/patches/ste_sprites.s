; STE Blitter Sprite Engine for Gods ($176d0 32px masked, $17b7a 16px masked, $19634 32px opaque)
; Uses HOG ($c0) per plane (16-48 lines * 2-3 words = <2 scanlines) + lazy 1-plane mask cache.
; Supports both 160B normal mode and 176B STE HW-scroll mode (with spr_fine_x + ste_save_bg!).

BLT_SXINC       equ     $ffff8a20
BLT_SYINC       equ     $ffff8a22
BLT_SADDR       equ     $ffff8a24
BLT_EM1         equ     $ffff8a28
BLT_EM2         equ     $ffff8a2a
BLT_EM3         equ     $ffff8a2c
BLT_DXINC       equ     $ffff8a2e
BLT_DYINC       equ     $ffff8a30
BLT_DADDR       equ     $ffff8a32
BLT_XCNT        equ     $ffff8a36
BLT_YCNT        equ     $ffff8a38
BLT_HOP         equ     $ffff8a3a
BLT_OP          equ     $ffff8a3b
BLT_CTRL        equ     $ffff8a3c
BLT_SKEW        equ     $ffff8a3d

MASK_LUT        equ     $0a4000         ; 768 * 4 = 3072 bytes ($0a4000-$0a4bff)
MASK_POOL       equ     $0a4c00         ; ~29 KB for 1-plane masks ($0a4c00-$0abfff)
MASK_POOL_END   equ     $0abe00

spr_cached_hdr:  dc.l   0
spr_pool_ptr:    dc.l   MASK_POOL
spr_stride:      dc.w   160
spr_scr_base:    dc.l   0
spr_fine_x:      dc.w   0
spr_save_enable: dc.w   0
spr_off_x:       dc.w   0               ; render camera delta X (sim_cam_x - render_cam_x)
spr_off_y:       dc.w   0               ; render camera delta Y (sim_cam_y - render_cam_y)
spr_rec_enable:  dc.w   0               ; 1 = record sprite calls for Phase-2 replay
spr_rec_cnt:     dc.w   0
SPR_REC_MAX      equ    48
spr_rec_buf:     ds.b   SPR_REC_MAX*8   ; {type.w, sx.w, sy.w, id.w} (384 bytes)

; Record sprite call (d0=sx, d1=sy, d2=id, d4=type: 0=32m, 1=16m, 2=32o)
spr_record:
        tst.w   spr_rec_enable
        beq.s   .sr_ret
        movem.l d3/a2,-(a7)
        move.w  spr_rec_cnt(pc),d3
        cmpi.w  #SPR_REC_MAX,d3
        bge.s   .sr_pop
        addq.w  #1,spr_rec_cnt
        lsl.w   #3,d3
        lea     spr_rec_buf(pc),a2
        adda.w  d3,a2
        move.w  d4,(a2)+
        move.w  d0,(a2)+
        move.w  d1,(a2)+
        move.w  d2,(a2)+
.sr_pop:
        movem.l (a7)+,d3/a2
.sr_ret:
        rts

; Non-HOG ($80) STE Blitter trigger + official interrupt-safe restart loop
blt_go_nh:
        move.b  #$80,BLT_CTRL.w
.bnh_w: bset.b  #7,BLT_CTRL.w
        nop
        bne.s   .bnh_w
        rts

spr_check_cache:
        movem.l d0/a0,-(a7)
        move.l  $10e6.w,d0
        cmp.l   spr_cached_hdr(pc),d0
        beq.s   .ok
        move.l  d0,spr_cached_hdr
        move.l  #MASK_POOL,spr_pool_ptr
        lea     MASK_LUT,a0
        move.w  #767,d0
.clr:   clr.l   (a0)+
        dbra    d0,.clr
.ok:    movem.l (a7)+,d0/a0
        rts

spr_get_mask:
        movem.l d0-d1/d4-d5/a5,-(a7)
        cmpi.w  #768,d2
        bcc.w   .fail
        move.w  d2,d0
        add.w   d0,d0
        add.w   d0,d0
        lea     MASK_LUT,a4
        move.l  (a4,d0.w),d1
        bne.s   .hit
        move.l  spr_pool_ptr(pc),d1
        move.w  d3,d4
        add.w   d4,d4
        tst.w   d6
        beq.s   .sz_ok
        add.w   d4,d4
.sz_ok:
        move.l  d1,d5
        ext.l   d4
        add.l   d4,d5
        cmpi.l  #MASK_POOL_END,d5
        bcc.s   .fail
        move.l  d5,spr_pool_ptr
        move.l  d1,(a4,d0.w)
        movea.l d1,a4
        movea.l a0,a5
        move.w  d3,d4
        subq.w  #1,d4
        tst.w   d6
        bne.s   .build32
.build16:
        move.w  (a5)+,d0
        or.w    (a5)+,d0
        or.w    (a5)+,d0
        or.w    (a5)+,d0
        move.w  d0,(a4)+
        dbra    d4,.build16
        movea.l d1,a4
        movem.l (a7)+,d0-d1/d4-d5/a5
        rts
.build32:
        move.w  (a5)+,d0
        or.w    (a5)+,d0
        or.w    (a5)+,d0
        or.w    (a5)+,d0
        move.w  d0,(a4)+
        move.w  (a5)+,d0
        or.w    (a5)+,d0
        or.w    (a5)+,d0
        or.w    (a5)+,d0
        move.w  d0,(a4)+
        dbra    d4,.build32
        movea.l d1,a4
        movem.l (a7)+,d0-d1/d4-d5/a5
        rts
.hit:
        movea.l d1,a4
        movem.l (a7)+,d0-d1/d4-d5/a5
        rts
.fail:
        suba.l  a4,a4
        movem.l (a7)+,d0-d1/d4-d5/a5
        rts

; ---------------------------------------------------------------------------
; $176d0 replacement: 32px-wide MASKED sprite
; ---------------------------------------------------------------------------
ste_spr32_mask:
        tst.l   spr_scr_base
        bne.s   .hw32
        tst.w   d0
        bmi.w   .fallback_left
        cmpi.w  #$120,d0
        bgt.w   .fallback_right
.hw32:
        movem.l d0-d7/a0-a6,-(a7)
        moveq   #0,d4
        bsr.w   spr_record
        ; Apply interpolation camera delta + HW-scroll fine_x offset
        add.w   spr_off_x(pc),d0
        add.w   spr_off_y(pc),d1
        add.w   spr_fine_x(pc),d0
        ; Horizontal bounds check against [0, 320] in 352px HW buffer (or [0, 288] in 160B mode)
        tst.w   d0
        bmi.w   .done32                 ; (left-edge clip handled below if needed; skip if <0 for now)
        cmpi.w  #320,d0
        bgt.w   .done32

        bsr.w   spr_check_cache
        movea.l $10e6.w,a3
        move.w  d2,d4
        asl.w   #3,d4
        adda.w  d4,a3
        movea.l 4(a3),a0
        move.w  2(a3),d3
        addq.w  #1,d3

        moveq   #1,d6
        bsr.w   spr_get_mask
        move.l  a4,d4
        beq.w   .done32

        move.w  d3,d7
        tst.w   d1
        bpl.s   .y_top_ok
        neg.w   d1
        sub.w   d1,d7
        ble.w   .done32
        move.w  d1,d4
        asl.w   #4,d4
        adda.w  d4,a0
        asl.w   #2,d1
        adda.w  d1,a4
        moveq   #0,d1
        bra.s   .y_bot_chk
.y_top_ok:
        cmpi.w  #192,d1
        bge.w   .done32
.y_bot_chk:
        move.w  d1,d4
        add.w   d7,d4
        subi.w  #192,d4
        ble.s   .y_ok
        sub.w   d4,d7
        ble.w   .done32
.y_ok:
        move.l  spr_scr_base(pc),d4
        bne.s   .got_scr32
        move.l  $110a.w,d4
.got_scr32:
        movea.l d4,a1
        move.w  spr_stride(pc),d4
        mulu.w  d4,d1
        adda.l  d1,a1
        move.w  d0,d5
        andi.w  #$fff0,d0
        asr.w   #1,d0
        adda.w  d0,a1
        andi.w  #15,d5

        move.b  #2,BLT_HOP.w
        move.w  #8,BLT_DXINC.w
        tst.w   d5
        bne.s   .skewed32

        moveq   #2,d6
        bsr.w   ste_save_bg
        move.b  #2,BLT_HOP.w
        move.w  #8,BLT_DXINC.w

        move.w  #$ffff,BLT_EM1.w
        move.w  #$ffff,BLT_EM2.w
        move.w  #$ffff,BLT_EM3.w
        move.b  #0,BLT_SKEW.w
        subq.w  #8,d4
        move.w  d4,BLT_DYINC.w

        move.w  #2,BLT_SXINC.w
        move.w  #2,BLT_SYINC.w
        move.b  #4,BLT_OP.w
        bsr.w   blt_4planes_mask

        move.w  #8,BLT_SXINC.w
        move.w  #8,BLT_SYINC.w
        move.b  #7,BLT_OP.w
        bsr.w   blt_4planes_data
        bra.s   .done32

.skewed32:
        moveq   #3,d6
        bsr.w   ste_save_bg
        move.b  #2,BLT_HOP.w
        move.w  #8,BLT_DXINC.w

        moveq   #-1,d0
        lsr.w   d5,d0
        move.w  d0,BLT_EM1.w
        move.w  #$ffff,BLT_EM2.w
        not.w   d0
        move.w  d0,BLT_EM3.w
        move.w  d5,d0
        ori.b   #$40,d0
        move.b  d0,BLT_SKEW.w
        subi.w  #16,d4
        move.w  d4,BLT_DYINC.w

        move.w  #2,BLT_SXINC.w
        move.w  #2,BLT_SYINC.w
        move.b  #4,BLT_OP.w
        bsr.w   blt_4planes_mask3

        move.w  #8,BLT_SXINC.w
        move.w  #8,BLT_SYINC.w
        move.b  #7,BLT_OP.w
        bsr.w   blt_4planes_data3

.done32:
        movem.l (a7)+,d0-d7/a0-a6
        rts
.fallback_left:
        move.w  d1,d4
        jmp     $0177e2
.fallback_right:
        move.w  d1,d4
        jmp     $0179bc

; ---------------------------------------------------------------------------
; $17b7a replacement: 16px-wide MASKED sprite
; ---------------------------------------------------------------------------
ste_spr16_mask:
        cmpi.w  #-16,d0
        ble.w   .ret16
        cmpi.w  #320,d0
        bge.w   .ret16
        cmpi.w  #192,d1
        bge.w   .ret16
        cmpi.w  #-16,d1
        ble.w   .ret16
        tst.l   spr_scr_base
        bne.s   .hw16
        tst.w   d0
        bmi.w   .fb16_left
        cmpi.w  #304,d0
        bgt.w   .fb16_right
.hw16:
        movem.l d0-d7/a0-a6,-(a7)
        moveq   #1,d4
        bsr.w   spr_record
        add.w   spr_off_x(pc),d0
        add.w   spr_off_y(pc),d1
        add.w   spr_fine_x(pc),d0
        tst.w   d0
        bmi.w   .done16
        cmpi.w  #336,d0
        bgt.w   .done16

        bsr.w   spr_check_cache
        movea.l $10e6.w,a3
        move.w  d2,d4
        asl.w   #3,d4
        adda.w  d4,a3
        movea.l 4(a3),a0
        move.w  2(a3),d3
        addq.w  #1,d3

        moveq   #0,d6
        bsr.w   spr_get_mask
        move.l  a4,d4
        beq.w   .done16

        move.w  d3,d7
        tst.w   d1
        bpl.s   .y16_top_ok
        neg.w   d1
        sub.w   d1,d7
        ble.w   .done16
        move.w  d1,d4
        asl.w   #3,d4
        adda.w  d4,a0
        add.w   d1,d1
        adda.w  d1,a4
        moveq   #0,d1
        bra.s   .y16_bot_chk
.y16_top_ok:
        cmpi.w  #192,d1
        bge.w   .done16
.y16_bot_chk:
        move.w  d1,d4
        add.w   d7,d4
        subi.w  #192,d4
        ble.s   .y16_ok
        sub.w   d4,d7
        ble.w   .done16
.y16_ok:
        move.l  spr_scr_base(pc),d4
        bne.s   .got_scr16
        move.l  $110a.w,d4
.got_scr16:
        movea.l d4,a1
        move.w  spr_stride(pc),d4
        mulu.w  d4,d1
        adda.l  d1,a1
        move.w  d0,d5
        andi.w  #$fff0,d0
        asr.w   #1,d0
        adda.w  d0,a1
        andi.w  #15,d5

        tst.w   d5
        bne.s   .skewed16

        moveq   #1,d6
        bsr.w   ste_save_bg
        move.b  #2,BLT_HOP.w
        move.w  #8,BLT_DXINC.w

        move.w  #$ffff,BLT_EM1.w
        move.w  #$ffff,BLT_EM2.w
        move.w  #$ffff,BLT_EM3.w
        move.b  #0,BLT_SKEW.w
        move.w  d4,BLT_DYINC.w

        move.w  #2,BLT_SXINC.w
        move.w  #2,BLT_SYINC.w
        move.b  #4,BLT_OP.w
        bsr.w   blt_4planes_mask1

        move.w  #8,BLT_SXINC.w
        move.w  #8,BLT_SYINC.w
        move.b  #7,BLT_OP.w
        bsr.w   blt_4planes_data1
        bra.s   .done16

.skewed16:
        moveq   #2,d6
        bsr.w   ste_save_bg
        move.b  #2,BLT_HOP.w
        move.w  #8,BLT_DXINC.w

        moveq   #-1,d0
        lsr.w   d5,d0
        move.w  d0,BLT_EM1.w
        move.w  #$ffff,BLT_EM2.w
        not.w   d0
        move.w  d0,BLT_EM3.w
        move.w  d5,d0
        ori.b   #$40,d0
        move.b  d0,BLT_SKEW.w
        subq.w  #8,d4
        move.w  d4,BLT_DYINC.w

        move.w  #2,BLT_SXINC.w
        move.w  #2,BLT_SYINC.w
        move.b  #4,BLT_OP.w
        bsr.w   blt_4planes_mask

        move.w  #8,BLT_SXINC.w
        move.w  #8,BLT_SYINC.w
        move.b  #7,BLT_OP.w
        bsr.w   blt_4planes_data

.done16:
        movem.l (a7)+,d0-d7/a0-a6
.ret16:
        rts
.fb16_left:
        move.w  d1,d4
        jmp     $017ce8
.fb16_right:
        move.w  d1,d4
        jmp     $017c50

; ---------------------------------------------------------------------------
; $19634 replacement: 32px-wide OPAQUE sprite
; ---------------------------------------------------------------------------
ste_spr32_opaq:
        tst.w   d0
        bmi.w   ste_spr32_mask
        cmpi.w  #$120,d0
        bgt.w   ste_spr32_mask
        movem.l d0-d7/a0-a6,-(a7)
        moveq   #2,d4
        bsr.w   spr_record
        add.w   spr_off_x(pc),d0
        add.w   spr_off_y(pc),d1
        add.w   spr_fine_x(pc),d0

        movea.l $10e6.w,a3
        move.w  d2,d4
        asl.w   #3,d4
        adda.w  d4,a3
        movea.l 4(a3),a0
        move.w  2(a3),d7
        addq.w  #1,d7

        tst.w   d1
        bpl.s   .yo_top_ok
        neg.w   d1
        sub.w   d1,d7
        ble.w   .done_op
        asl.w   #4,d1
        adda.w  d1,a0
        moveq   #0,d1
        bra.s   .yo_bot_chk
.yo_top_ok:
        cmpi.w  #192,d1
        bge.w   .done_op
.yo_bot_chk:
        move.w  d1,d4
        add.w   d7,d4
        subi.w  #192,d4
        ble.s   .yo_ok
        sub.w   d4,d7
        ble.w   .done_op
.yo_ok:
        move.l  spr_scr_base(pc),d4
        bne.s   .got_scro
        move.l  $110a.w,d4
.got_scro:
        movea.l d4,a1
        move.w  spr_stride(pc),d4
        mulu.w  d4,d1
        adda.l  d1,a1
        move.w  d0,d5
        andi.w  #$fff0,d0
        asr.w   #1,d0
        adda.w  d0,a1
        andi.w  #15,d5

        tst.w   d5
        bne.s   .skewed_op

        moveq   #2,d6
        bsr.w   ste_save_bg
        move.b  #2,BLT_HOP.w
        move.b  #3,BLT_OP.w
        move.w  #8,BLT_SXINC.w
        move.w  #8,BLT_SYINC.w
        move.w  #8,BLT_DXINC.w
        move.w  #$ffff,BLT_EM1.w
        move.w  #$ffff,BLT_EM2.w
        move.w  #$ffff,BLT_EM3.w
        move.b  #0,BLT_SKEW.w
        subq.w  #8,d4
        move.w  d4,BLT_DYINC.w
        bsr.w   blt_4planes_data
        bra.s   .done_op

.skewed_op:
        moveq   #3,d6
        bsr.w   ste_save_bg
        move.b  #2,BLT_HOP.w
        move.b  #3,BLT_OP.w
        move.w  #8,BLT_SXINC.w
        move.w  #8,BLT_SYINC.w
        move.w  #8,BLT_DXINC.w
        moveq   #-1,d0
        lsr.w   d5,d0
        move.w  d0,BLT_EM1.w
        move.w  #$ffff,BLT_EM2.w
        not.w   d0
        move.w  d0,BLT_EM3.w
        move.w  d5,d0
        ori.b   #$40,d0
        move.b  d0,BLT_SKEW.w
        subi.w  #16,d4
        move.w  d4,BLT_DYINC.w
        bsr.s   blt_4planes_data3

.done_op:
        movem.l (a7)+,d0-d7/a0-a6
        rts

; ---------------------------------------------------------------------------
; Shared 4-plane Blitter loops (NON-HOG $80: zero Timer B HBL jitter!)
; ---------------------------------------------------------------------------
blt_4planes_mask1:
        moveq   #1,d6
        bra.s   blt_4m_go
blt_4planes_mask:
        moveq   #2,d6
        bra.s   blt_4m_go
blt_4planes_mask3:
        moveq   #3,d6
blt_4m_go:
        movea.l a1,a2
        moveq   #3,d0
.lp_m:
        move.l  a4,BLT_SADDR.w
        move.l  a2,BLT_DADDR.w
        move.w  d6,BLT_XCNT.w
        move.w  d7,BLT_YCNT.w
        bsr.w   blt_go_nh
        addq.l  #2,a2
        dbra    d0,.lp_m
        rts

blt_4planes_data1:
        moveq   #1,d6
        bra.s   blt_4d_go
blt_4planes_data:
        moveq   #2,d6
        bra.s   blt_4d_go
blt_4planes_data3:
        moveq   #3,d6
blt_4d_go:
        movea.l a0,a3
        movea.l a1,a2
        moveq   #3,d0
.lp_d:
        move.l  a3,BLT_SADDR.w
        move.l  a2,BLT_DADDR.w
        move.w  d6,BLT_XCNT.w
        move.w  d7,BLT_YCNT.w
        bsr.w   blt_go_nh
        addq.l  #2,a3
        addq.l  #2,a2
        dbra    d0,.lp_d
        rts
