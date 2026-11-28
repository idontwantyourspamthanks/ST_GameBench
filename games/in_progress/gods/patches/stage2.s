; Gods (Atari ST/STE) Stage 2 Patcher — loaded to $084000 by START.TOS stub
; Runs at $084008 right before START.TOS jumps to $140.w (game fully unpacked in $1000-$21000).
;
; Memory map in free upper RAM ($084000-$0abfff = 160 KB on 1 MB STE):
;   $084000-$087fff (16 KB): GODSPAT.BIN (Stage 2 patcher + STE engine code + state)
;   $088000-$092fff (44 KB): STE HW-scroll ring buffer 0 (176 B/line * 256 lines)
;   $093000-$09dfff (44 KB): STE HW-scroll ring buffer 1 (176 B/line * 256 lines)
;   $09e000-$0a1fff (16 KB): Dirty-rect save buffers (8 KB per screen buffer)
;   $0a2000-$0abfff (40 KB): Lazy 1-plane inverted sprite mask cache

        org     $084000

hdr_magic:
        dc.l    $47445350               ; 'GDSP' (checked by START.TOS loader stub)
hdr_marker:
        dc.l    0                       ; 'GDPO' on success, 'GDPF' on verify mismatch
entry_stage2:                           ; $084008: called via jsr $084008 from START.TOS +$0748
        movem.l d0-d7/a0-a6,-(a7)

        ; --- Detect STE hardware (Blitter at $ff8a3c + STE Shifter at $ff8265) ---
        clr.w   ste_present
        move.l  $8.w,a2
        lea     .no_ste(pc),a0
        move.l  a0,$8.w
        move.l  a7,a3
        tst.b   $ffff8a3c.w             ; Blitter control reg (STE / Mega ST)
        tst.b   $ffff8265.w             ; STE HSCROLL reg (STE / Mega STE only)
        move.w  #1,ste_present
.no_ste:
        move.l  a3,a7
        move.l  a2,$8.w

        ; --- Pass 1: Verify every site matches ORIG (or already NEW for idempotency) ---
        lea     patch_table(pc),a0
.v_loop:
        move.l  (a0)+,d0                ; target addr (0 = end)
        beq.s   .v_ok
        move.w  (a0)+,d1                ; flags: bit 0 = STE-only
        move.w  (a0)+,d2                ; byte length
        movea.l d0,a1                   ; target RAM
        movea.l a0,a2                   ; orig bytes
        lea     (a0,d2.w),a3            ; new bytes
        add.w   d2,a0
        add.w   d2,a0
        move.l  a0,d3
        addq.l  #1,d3
        bclr    #0,d3
        movea.l d3,a0

        move.w  d2,d3
        subq.w  #1,d3
        movea.l a1,a4
        movea.l a2,a5
.chk_orig:
        cmpm.b  (a4)+,(a5)+
        bne.s   .try_new
        dbra    d3,.chk_orig
        bra.s   .v_loop

.try_new:
        move.w  d2,d3
        subq.w  #1,d3
        movea.l a1,a4
        movea.l a3,a5
.chk_new:
        cmpm.b  (a4)+,(a5)+
        bne.s   .v_fail
        dbra    d3,.chk_new
        bra.s   .v_loop

.v_fail:
        move.l  #$47445046,hdr_marker   ; 'GDPF'
        bra.s   .done

.v_ok:
        ; --- Pass 2: Apply all matching sites ---
        lea     patch_table(pc),a0
.a_loop:
        move.l  (a0)+,d0
        beq.s   .a_done
        move.w  (a0)+,d1                ; flags: bit 0 = STE-only
        move.w  (a0)+,d2                ; byte length
        movea.l d0,a1
        lea     (a0,d2.w),a3            ; new bytes
        add.w   d2,a0
        add.w   d2,a0
        move.l  a0,d3
        addq.l  #1,d3
        bclr    #0,d3
        movea.l d3,a0

        btst    #0,d1
        beq.s   .do_write
        tst.w   ste_present
        beq.s   .a_loop

.do_write:
        move.w  d2,d3
        subq.w  #1,d3
.wr_byte:
        move.b  (a3)+,(a1)+
        dbra    d3,.wr_byte
        bra.s   .a_loop

.a_done:
        move.l  #$4744504f,hdr_marker   ; 'GDPO'

.done:
        movem.l (a7)+,d0-d7/a0-a6
        ; Execute the 6 bytes displaced at START.TOS +$0748:
        lea     $2c58.w,a1
        move.w  #$4ef9,(a1)+
        rts

ste_present:
        dc.w    0

        even
patch_table:
        ; --- 1. Neutralize Rob Northen Copylock trap #1 ($00fec8): monster AI overwrite ---
        dc.l    $00fec8
        dc.w    0
        dc.w    4
        dc.b    $87,$3b,$49,$53
        dc.b    $00,$00,$00,$00

        ; --- 2. Neutralize Rob Northen Copylock trap #2 ($00d864): Level 4/NG+ weapon dmg nerf ---
        dc.l    $00d864
        dc.w    0
        dc.w    4
        dc.b    $87,$3b,$49,$53
        dc.b    $00,$00,$00,$00

        ; --- 3. Neutralize Rob Northen Copylock trap #3 ($010ffe): Power Potion upgrade block ---
        dc.l    $010ffe
        dc.w    0
        dc.w    4
        dc.b    $87,$3b,$49,$53
        dc.b    $00,$00,$00,$00

        ; --- 4. Neutralize Rob Northen Copylock trap #4 ($00b4ee): Guardian boss 121M HP ---
        dc.l    $00b4ee
        dc.w    0
        dc.w    4
        dc.b    $87,$3b,$4f,$2f
        dc.b    $00,$00,$05,$dc

        ; --- 5. STE Blitter Sprites: $176d0 (32px masked) ---
        dc.l    $0176d0
        dc.w    1                       ; STE only
        dc.w    6
        dc.b    $38,$01,$4a,$40,$6b,$00
        dc.w    $4ef9
        dc.l    ste_spr32_mask

        ; --- 6. STE Blitter Sprites: $17b7a (16px masked) ---
        dc.l    $017b7a
        dc.w    1                       ; STE only
        dc.w    6
        dc.b    $38,$01,$0c,$40,$ff,$f0
        dc.w    $4ef9
        dc.l    ste_spr16_mask

        ; --- 7. STE Blitter Sprites: $19634 (32px opaque) ---
        dc.l    $019634
        dc.w    1                       ; STE only
        dc.w    6
        dc.b    $38,$01,$4a,$40,$6a,$04
        dc.w    $4ef9
        dc.l    ste_spr32_opaq

        ; --- 8. STE HW-Scroll Tilemap Diff Renderer ($18036) ---
        dc.l    $018036
        dc.w    1                       ; STE only
        dc.w    6
        dc.b    $0c,$78,$00,$02,$04,$fa
        dc.w    $4ef9
        dc.l    ste_tile_draw

        ; --- 9. STE HUD Copy Hook ($00331c: jsr $3cc6.l) ---
        dc.l    $00331c
        dc.w    1                       ; STE only
        dc.w    6
        dc.b    $4e,$b9,$00,$00,$3c,$c6
        dc.w    $4eb9
        dc.l    ste_hud_hook

        ; --- 10. STE Frame Flip Hook ($01ecba..$01ecd9) ---
        dc.l    $01ecba
        dc.w    1                       ; STE only
        dc.w    8
        dc.b    $20,$38,$11,$0e,$22,$38,$11,$0a
        dc.w    $4eb9
        dc.l    ste_flip
        dc.w    $6018                   ; bra.s $01ecda

        ; --- 11. STE VBL Shifter Hook ($0171b4) ---
        dc.l    $0171b4
        dc.w    1                       ; STE only
        dc.w    6
        dc.b    $4a,$78,$04,$70,$66,$06
        dc.w    $4ef9
        dc.l    ste_vbl_hook

        ; --- 12. Frame Cap: 2 VBLs = 25 fps ($003056: move.w #2,$35a.w -> #1) ---
        dc.l    $003056
        dc.w    1                       ; STE only
        dc.w    6
        dc.b    $31,$fc,$00,$02,$03,$5a
        dc.b    $31,$fc,$00,$01,$03,$5a

        ; --- 14. Unlinked 16.67 Hz World Tick + 25 fps Smooth Scroll Hook ($0030f0) ---
        dc.l    $0030f0
        dc.w    1                       ; STE only
        dc.w    6
        dc.b    $4e,$b9,$00,$01,$74,$f6
        dc.w    $4ef9
        dc.l    ste_loop_hook

        ; End of table
        dc.l    0

        include "ste_sprites.s"
        include "ste_scroll.s"
