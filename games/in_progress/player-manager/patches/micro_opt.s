; Player Manager (PLAYERME) - New Game Setup Micro-Optimisations + Option A Early Rejection
; Assembled at $b3000 (free RAM above HAGA chunk cache $81000-$b1d40).
; Entered from PMLA+$01de (replaces jmp $10000.l) after PMLA depacks to $10000
; and applies PP's own RAM patches.
;
; Patches applied (all original bytes verified before any write; marker PMOK/PMFL at $b2ff8):
;   1. $01863e (sum_rng_mod): 100% bit-exact 16-bit + 8-bit + 4-bit LFSR steps + popcount
;      for d1 == 2, and register-inlined LFSR for d1 != 2.
;   2. $021792 (LFSR jump table -> $021656): 100% bit-exact faster 1-bit LFSR.
;   3. $0155f2 (calc_pos_ratings): 100% bit-exact fast arithmetic (reciprocal mulu/shifts + LUTs).
;   4. $0156f2 (pick_best_pos): 100% bit-exact register-inlined LFSR across all 4 iterations.
;   5. $015758 (train_one_skill): 100% bit-exact inlined LFSR.
;   6. $0153ee & $01545e (sim_season_matches): 100% bit-exact hoist of rating_lookup + mulu.
;   7. $010cc0 / $010cfe / $01528e / $014ce2 (New Game setup):
;      - skip dead intermediate-season match sims (run once on accepted player at $014ce2)
;      - batch VDI bucket-counter redraws (every 8th + quota/full + final pass)
;      - redraw d7 only when it decrements
;   8. $014c96 & $014cbe (Option A - Early Position Rejection):
;      - if all 4 divisions for candidate's current position are full in d6 AND no open
;        position is within 40 rating points, reject immediately instead of simulating
;        remaining adult seasons.

        org     $b3000

MARKER  equ     $b2ff8

; ---------------------------------------------------------------------------
; Boot entry: verify original bytes at all patch sites, apply all or none
; ---------------------------------------------------------------------------
boot_entry:
        movem.l d0-d7/a0-a6,-(sp)
        bsr.s   reapply_pm_hooks
        tst.w   d0
        bne.s   .b_fail
        move.l  #'PMOK',MARKER.l
        bra.s   .b_done
.b_fail:
        move.l  #'PMFL',MARKER.l
.b_done:
        movem.l (sp)+,d0-d7/a0-a6
        jmp     $010000.l

; Callable from boot_entry AND from ko2_bridge.s after reloading PMCODE.BIN ($010000..$025900)!
; Returns d0.w = 0 ok, 1 fail.
reapply_pm_hooks:
        movem.l d1-d7/a0-a6,-(sp)

        ; Verify original bytes at every patch site
        cmpi.l  #$53407400,$01863e.l
        bne.w   .fail
        cmpi.w  #$4eac,$018642.l
        bne.w   .fail
        cmpi.l  #$4ef90002,$021792.l
        bne.w   .fail
        cmpi.w  #$1656,$021796.l
        bne.w   .fail
        cmpi.l  #$244d47ec,$0155f2.l
        bne.w   .fail
        cmpi.l  #$4ebafefe,$0156f2.l
        bne.w   .fail
        cmpi.l  #$4eac80f8,$015758.l
        bne.w   .fail
        cmpi.l  #$422d0021,$0153ee.l
        bne.w   .fail
        cmpi.w  #$7c00,$0153f2.l
        bne.w   .fail
        cmpi.l  #$70034eba,$01545e.l
        bne.w   .fail
        cmpi.l  #$45ec8137,$010cc0.l
        bne.w   .fail
        cmpi.l  #$52360000,$010cfe.l
        bne.w   .fail
        cmpi.w  #$4e75,$010d42.l
        bne.w   .fail
        cmpi.l  #$4eba010a,$01528e.l
        bne.w   .fail
        cmpi.l  #$48a7e000,$014ce2.l
        bne.w   .fail
        cmpi.l  #$4eba04c2,$014c96.l
        bne.w   .fail
        cmpi.l  #$4eba05ac,$014cbe.l
        bne.w   .fail

        clr.b   skip_matches

        ; 1. Hook $01863e (sum_rng_mod)
        move.w  #$4ef9,$01863e.l
        move.l  #fast_sum_rng_mod,$018640.l

        ; 2. Hook $021792 (LFSR jump table)
        move.l  #fast_lfsr,$021794.l

        ; 3. Hook $0155f2 (calc_pos_ratings)
        move.w  #$4ef9,$0155f2.l
        move.l  #fast_calc_pos_ratings,$0155f4.l

        ; 4. Hook $0156f2 (pick_best_pos)
        move.w  #$4ef9,$0156f2.l
        move.l  #fast_pick_best_pos,$0156f4.l

        ; 5. Hook $015758 (train_one_skill)
        move.w  #$4ef9,$015758.l
        move.l  #fast_train_one_skill,$01575a.l

        ; 6. Hoist rating_lookup in sim_season_matches ($0153ee & $01545e)
        move.w  #$4ef9,$0153ee.l
        move.l  #hoist_match_entry,$0153f0.l
        move.w  #$3407,$01545e.l        ; move.w d7,d2
        move.w  #$6012,$015460.l        ; bra.s  $015474

        ; 7. New Game setup hooks
        move.w  #$4ef9,$010cc0.l
        move.l  #setup_enter,$010cc2.l
        move.w  #$4ef9,$010cfe.l
        move.l  #setup_bucket_inc,$010d00.l
        move.w  #$4ef9,$01528e.l
        move.l  #cond_sim_matches,$015290.l
        move.w  #$4ef9,$014ce2.l
        move.l  #accepted_final_matches,$014ce4.l

        ; 8. Option A: early position rejection at $014c96 and $014cbe
        move.w  #$4ef9,$014c96.l
        move.l  #early_rej_after_create,$014c98.l
        move.w  #$4ef9,$014cbe.l
        move.l  #early_rej_after_season,$014cc0.l

        ; 9. Task 1 (1B+1C+1D+1E): 92-team 1989-90 league expansion
        bsr.w   init_league92
        tst.w   d0
        bne.s   .fail

        ; 10. Task 2 (2B): Kick Off 2 match engine overlay bridge
        bsr.w   init_ko2_bridge
        tst.w   d0
        bne.s   .fail

        ; 11. v1.1 Title Screen discreet credit ("v1.1 enhanced by dad_prg") on scr2.men & scr3.men
        cmpi.l  #$4eba77c6,$010544.l
        bne.s   .fail
        cmpi.l  #$4eac8008,$010548.l
        bne.s   .fail
        cmpi.l  #$4eba77ba,$010550.l
        bne.s   .fail
        cmpi.l  #$4eac8008,$010554.l
        bne.s   .fail
        move.w  #$4ef9,$010544.l
        move.l  #title_scr2_credit,$010546.l
        move.w  #$4e71,$01054a.l
        move.w  #$4ef9,$010550.l
        move.l  #title_scr3_credit,$010552.l
        move.w  #$4e71,$010556.l

        moveq   #0,d0
        movem.l (sp)+,d1-d7/a0-a6
        rts
.fail:
        moveq   #1,d0
        movem.l (sp)+,d1-d7/a0-a6
        rts

; ---------------------------------------------------------------------------
; Patch 1: fast_sum_rng_mod ($01863e) - 100% bit-exact (16/8/4/1-bit LFSR)
; ---------------------------------------------------------------------------
fast_sum_rng_mod:
        cmpi.w  #2,d1
        bne.w   .general

        movem.l d4-d7/a0,-(sp)
        move.w  -$38da(a4),d4           ; w0
        move.w  -$38d8(a4),d5           ; w1
        move.w  -$38d6(a4),d6           ; w2
        moveq   #0,d2                   ; sum = 0
        lea     popcnt_tbl(pc),a0

        move.w  d0,d3
        lsr.w   #4,d3                   ; N >> 4
        beq.s   .rem8
        subq.w  #1,d3

.loop16:
        move.w  d5,d1
        ror.w   #4,d1
        andi.w  #$f000,d1
        move.w  d4,d7
        lsr.w   #4,d7
        or.w    d7,d1
        lsr.w   #1,d6
        move.w  d5,d7
        roxr.w  #1,d7
        eor.w   d7,d1
        move.w  d5,d6
        move.w  d4,d5
        move.w  d1,d4
        moveq   #0,d7
        move.b  d1,d7
        move.b  (a0,d7.w),d7
        add.w   d7,d2
        lsr.w   #8,d1
        move.b  (a0,d1.w),d7
        add.w   d7,d2
        dbra    d3,.loop16

.rem8:
        andi.w  #$f,d0
        beq.w   .done2
        btst    #3,d0
        beq.s   .rem4
        ; 8-bit LFSR step:
        ; tap1 = ((w1 << 4) | (w0 >> 12)) & $ff
        move.w  d5,d1
        lsl.w   #4,d1
        move.w  d4,d7
        rol.w   #4,d7
        andi.w  #$f,d7
        or.w    d7,d1
        ; tap2 = ((w2 << 7) | (w1 >> 9)) & $ff
        move.w  d6,d7
        lsr.w   #1,d7                   ; X = bit0(w2)
        move.w  d5,d3
        roxr.w  #1,d3                   ; bit15 = bit0(w2), bits 14..8 = w1[15..9]
        lsr.w   #8,d3                   ; low byte = tap2!
        eor.b   d3,d1
        andi.w  #$ff,d1                 ; d1 = fb8
        ; shift w2,w1,w0 left by 8
        lsl.w   #8,d6
        move.w  d5,d7
        lsr.w   #8,d7
        or.w    d7,d6
        lsl.w   #8,d5
        move.w  d4,d7
        lsr.w   #8,d7
        or.w    d7,d5
        lsl.w   #8,d4
        or.w    d1,d4
        moveq   #0,d7
        move.b  (a0,d1.w),d7
        add.w   d7,d2
        subq.w  #8,d0
        beq.s   .done2

.rem4:
        btst    #2,d0
        beq.s   .rem1_chk
        ; 4-bit LFSR step:
        ; fb4 = (w1 ^ ((w2 << 3) | (w1 >> 13))) & $f
        move.w  d6,d7
        lsr.w   #1,d7                   ; X = bit0(w2)
        move.w  d5,d1
        roxr.w  #1,d1                   ; bit15 = bit0(w2), bits 14..12 = w1[15..13]
        rol.w   #4,d1                   ; bits 3..0 = (w2[0]<<3) | (w1>>13)
        eor.w   d5,d1
        andi.w  #$f,d1                  ; d1 = fb4
        ; shift w2,w1,w0 left by 4
        lsl.w   #4,d6
        move.w  d5,d7
        rol.w   #4,d7
        andi.w  #$f,d7
        or.w    d7,d6
        lsl.w   #4,d5
        move.w  d4,d7
        rol.w   #4,d7
        andi.w  #$f,d7
        or.w    d7,d5
        lsl.w   #4,d4
        or.w    d1,d4
        moveq   #0,d7
        move.b  (a0,d1.w),d7
        add.w   d7,d2
        subq.w  #4,d0
        beq.s   .done2

.rem1_chk:
        subq.w  #1,d0
.rem1:
        move.w  d5,d1
        lsr.w   #3,d1
        eor.w   d6,d1
        roxr.w  #1,d1
        roxl.w  #1,d4
        roxl.w  #1,d5
        roxl.w  #1,d6
        moveq   #1,d7
        and.w   d4,d7
        add.w   d7,d2
        dbra    d0,.rem1

.done2:
        move.w  d4,-$38da(a4)
        move.w  d5,-$38d8(a4)
        move.w  d6,-$38d6(a4)
        moveq   #2,d1
        movem.l (sp)+,d4-d7/a0
        rts

.general:
        movem.l d4-d6,-(sp)
        move.w  -$38da(a4),d4
        move.w  -$38d8(a4),d5
        move.w  -$38d6(a4),d6
        subq.w  #1,d0
        moveq   #0,d2
.gen_loop:
        move.w  d5,d3
        lsr.w   #3,d3
        eor.w   d6,d3
        roxr.w  #1,d3
        roxl.w  #1,d4
        roxl.w  #1,d5
        roxl.w  #1,d6
        moveq   #0,d3
        move.w  d4,d3
        divu.w  d1,d3
        swap    d3
        add.w   d3,d2
        dbra    d0,.gen_loop
        move.w  d4,-$38da(a4)
        move.w  d5,-$38d8(a4)
        move.w  d6,-$38d6(a4)
        movem.l (sp)+,d4-d6
        rts

; ---------------------------------------------------------------------------
; Patch 2: fast_lfsr ($021792 -> replaces $021656) - 100% bit-exact
; ---------------------------------------------------------------------------
fast_lfsr:
        move.w  d0,-(sp)
        move.w  d1,-(sp)
        move.b  -$38d7(a4),d1
        lsr.b   #3,d1
        move.b  -$38d5(a4),d0
        eor.b   d0,d1
        roxr.b  #1,d1
        roxl.w  -$38da(a4)
        roxl.w  -$38d8(a4)
        roxl.w  -$38d6(a4)
        move.w  (sp)+,d1
        move.w  (sp)+,d0
        rts

; ---------------------------------------------------------------------------
; Patch 3: fast_calc_pos_ratings (replaces $0155f2..$0156f0) - 100% bit-exact
; In:  a5 = player struct, a4 = $02969a
; Out: a2 = a5, a3 = -$35ee(a4), fills 4 words at 0(a3)..6(a3)
; Clobbers: d0, d1, d3, a2, a3 (preserves d2, d4-d7, a0-a1, a4-a6)
; ---------------------------------------------------------------------------
fast_calc_pos_ratings:
        movea.l a5,a2
        lea     -$35ee(a4),a3
        moveq   #0,d0
        moveq   #0,d1
        ; d0 = (c * d) / 100  (max 200*200 = 40000 <= 43698 -> exact mulu #5243 >> 19!)
        move.b  $c(a2),d0
        move.b  $d(a2),d1
        mulu.w  d1,d0
        mulu.w  #5243,d0
        swap    d0
        lsr.w   #3,d0
        ; d0 = (d0 * a) / 100
        move.b  $a(a2),d1
        mulu.w  d1,d0
        cmpi.l  #43698,d0
        bhi.s   .d100_a
        mulu.w  #5243,d0
        swap    d0
        lsr.w   #3,d0
        bra.s   .d100_a_ok
.d100_a:
        divu.w  #100,d0
.d100_a_ok:
        ; d0 = (d0 * b) / 100
        move.b  $b(a2),d1
        mulu.w  d1,d0
        cmpi.l  #43698,d0
        bhi.s   .d100_b
        mulu.w  #5243,d0
        swap    d0
        lsr.w   #3,d0
        bra.s   .d100_b_ok
.d100_b:
        divu.w  #100,d0
.d100_b_ok:
        move.w  d0,d3                   ; d3 = base multiplier!

        ; --- Forward rating -> 6(a3): (4*$11 + 2*$10 + $c) / 7 * d3 / 100 ---
        moveq   #0,d1
        moveq   #0,d0
        move.b  $11(a2),d1
        lsl.w   #2,d1
        move.b  $10(a2),d0
        add.w   d0,d1
        add.w   d0,d1
        move.b  $c(a2),d0
        add.w   d0,d1
        mulu.w  #9363,d1                ; exact / 7 for 0..1600!
        swap    d1
        mulu.w  d3,d1
        cmpi.l  #43698,d1
        bhi.s   .d100_f
        mulu.w  #5243,d1
        swap    d1
        lsr.w   #3,d1
        bra.s   .d100_f_ok
.d100_f:
        divu.w  #100,d1
.d100_f_ok:
        move.w  d1,6(a3)

        ; --- Midfield rating -> 4(a3): (4*$10 + 2*$12 + $11 + $c + $a) / 9 * d3 / 100 ---
        moveq   #0,d1
        moveq   #0,d0
        move.b  $10(a2),d1
        lsl.w   #2,d1
        move.b  $12(a2),d0
        add.w   d0,d1
        add.w   d0,d1
        move.b  $11(a2),d0
        add.w   d0,d1
        move.b  $c(a2),d0
        add.w   d0,d1
        move.b  $a(a2),d0
        add.w   d0,d1
        mulu.w  #7282,d1                ; exact / 9 for 0..2000!
        swap    d1
        mulu.w  d3,d1
        cmpi.l  #43698,d1
        bhi.s   .d100_m
        mulu.w  #5243,d1
        swap    d1
        lsr.w   #3,d1
        bra.s   .d100_m_ok
.d100_m:
        divu.w  #100,d1
.d100_m_ok:
        move.w  d1,4(a3)

        ; --- Defender rating -> 2(a3): (4*$12 + 2*$10 + $b + tbl_1333[$9]) / 8 * d3 / 100 ---
        moveq   #0,d1
        moveq   #0,d0
        move.b  $12(a2),d1
        lsl.w   #2,d1
        move.b  $10(a2),d0
        add.w   d0,d1
        add.w   d0,d1
        move.b  $b(a2),d0
        add.w   d0,d1
        move.b  $9(a2),d0
        add.w   d0,d0
        lea     tbl_1333(pc),a2
        add.w   (a2,d0.w),d1            ; exact (weight * 1333) / 1000!
        movea.l a5,a2
        lsr.w   #3,d1                   ; exact / 8!
        mulu.w  d3,d1
        cmpi.l  #43698,d1
        bhi.s   .d100_d
        mulu.w  #5243,d1
        swap    d1
        lsr.w   #3,d1
        bra.s   .d100_d_ok
.d100_d:
        divu.w  #100,d1
.d100_d_ok:
        move.w  d1,2(a3)

        ; --- Keeper rating -> 0(a3): (4*$13 + tbl_1750[$8]) / 5 * d3 / 100 ---
        moveq   #0,d1
        moveq   #0,d0
        move.b  $13(a2),d1
        lsl.w   #2,d1
        move.b  $8(a2),d0
        lea     tbl_1750(pc),a2
        move.b  (a2,d0.w),d0            ; exact (height * 1000) / 1750!
        movea.l a5,a2
        add.w   d0,d1
        mulu.w  #13108,d1               ; exact / 5 for 0..1200!
        swap    d1
        mulu.w  d3,d1
        cmpi.l  #43698,d1
        bhi.s   .d100_k
        mulu.w  #5243,d1
        swap    d1
        lsr.w   #3,d1
        bra.s   .d100_k_ok
.d100_k:
        divu.w  #100,d1
.d100_k_ok:
        move.w  d1,(a3)
        rts

; ---------------------------------------------------------------------------
; Patch 4: fast_pick_best_pos (replaces $0156f2..$015736) - 100% bit-exact
; Preserves d5-d7, a0-a1, a4-a6. Clobbers d0-d4, a2-a3.
; ---------------------------------------------------------------------------
fast_pick_best_pos:
        bsr.w   fast_calc_pos_ratings
        movem.l d5-d7,-(sp)
        move.w  -$38da(a4),d5           ; w0
        move.w  -$38d8(a4),d6           ; w1
        move.w  -$38d6(a4),d7           ; w2
        moveq   #0,d0                   ; best_val = 0
        moveq   #1,d1                   ; best_pos = 1
        moveq   #3,d2                   ; pos = 3..0
.loop:
        ; inline 1-bit LFSR step
        move.w  d6,d4
        lsr.w   #3,d4
        eor.w   d7,d4
        roxr.w  #1,d4
        roxl.w  #1,d5
        roxl.w  #1,d6
        roxl.w  #1,d7
        moveq   #0,d4
        move.w  d5,d4
        divu.w  #40,d4
        swap    d4
        subi.w  #20,d4
        move.w  d2,d3
        add.w   d3,d3
        add.w   (a3,d3.w),d4
        cmp.w   d4,d0
        bgt.s   .next
        move.w  d4,d0
        move.w  d2,d1
.next:
        dbra    d2,.loop
        move.w  d5,-$38da(a4)
        move.w  d6,-$38d8(a4)
        move.w  d7,-$38d6(a4)
        movem.l (sp)+,d5-d7
        cmpi.w  #50,d0
        bge.s   .ok
        moveq   #-1,d1
.ok:
        move.w  d1,8(a3)
        addq.w  #1,d1
        rts

; ---------------------------------------------------------------------------
; Patch 5: fast_train_one_skill (replaces $015758..$01579e) - 100% bit-exact
; In:  a0 = &skill_byte, a2 = player, d1.w = threshold (/150)
; Clobbers: d0, d1, d2, d3 (same as original)
; ---------------------------------------------------------------------------
fast_train_one_skill:
        ; inline 1-bit LFSR step
        move.b  -$38d7(a4),d0
        lsr.b   #3,d0
        move.b  -$38d5(a4),d2
        eor.b   d2,d0
        roxr.b  #1,d0
        roxl.w  -$38da(a4)
        roxl.w  -$38d8(a4)
        roxl.w  -$38d6(a4)
        moveq   #0,d0
        move.w  -$38da(a4),d0
        divu.w  #150,d0
        swap    d0
        cmp.w   d1,d0
        bge.s   .ret
        moveq   #0,d0
        move.w  #200,d1
        move.b  (a0),d0
        sub.w   d0,d1
        move.b  $d(a2),d0
        mulu.w  d0,d1
        divu.w  #1333,d1
        tst.w   d1
        beq.s   .ret
        addq.w  #1,d1
        moveq   #2,d0
        bsr.w   fast_sum_rng_mod
        add.b   d2,(a0)
        cmpi.b  #200,(a0)
        bcs.s   .ret
        move.b  #200,(a0)
.ret:
        rts

; ---------------------------------------------------------------------------
; Patch 6: hoist rating_lookup ($01530e) + mulu out of match loop ($0153ee)
; ---------------------------------------------------------------------------
hoist_match_entry:
        clr.b   $21(a5)
        moveq   #0,d6
        tst.w   d4
        ble.s   .skip_hoist
        moveq   #3,d0
        jsr     $01530e.l
        moveq   #0,d0
        move.b  $5(a5),d0
        subq.w  #1,d0
        lsl.w   #1,d0
        lea     $0154e6.l,a0
        mulu.w  (a0,d0.w),d2
        move.w  d2,d7
.skip_hoist:
        jmp     $0153f4.l

; ---------------------------------------------------------------------------
; Patch 7: New Game setup hooks + batched VDI redraws
; ---------------------------------------------------------------------------
setup_enter:
        bsr.w   reset_team_names_92
        st.b    skip_matches
        lea     -$7ec9(a4),a2
        jsr     $017d0c.l
        jmp     $010cc8.l

; Replaces $010cfe..$010d42 (increment count, batched redraw, quota/full check)
setup_bucket_inc:
        addq.b  #1,(a6,d0.w)
        move.b  (a6,d0.w),d1
        ; Check if quota reached, full reached, or (count & 7) == 0
        moveq   #0,d2                   ; flag: need redraw?
        cmp.b   (a3,d0.w),d1
        bne.s   .not_quota
        subq.w  #1,d7
        ble.s   .setup_done
        ; Redraw d7 only when it decrements
        movem.l d0-d7/a0-a3/a5-a6,-(sp)
        moveq   #$12,d0
        move.w  d7,d1
        lea     -$7dd1(a4),a3
        jsr     $017b9c.l
        movem.l (sp)+,d0-d7/a0-a3/a5-a6
        moveq   #1,d2                   ; also redraw this bucket!
.not_quota:
        moveq   #0,d3
        move.b  d1,d3
        cmpi.w  #$f,d3
        bcs.s   .not_full
        subi.w  #$f,d3
        moveq   #0,d2
        move.b  (a3,d0.w),d2
        cmp.w   d2,d3
        bcs.s   .not_full
        bset    d0,d6
        moveq   #1,d2
        bra.s   .do_redraw
.not_full:
        moveq   #0,d2
        cmp.b   (a3,d0.w),d1
        beq.s   .do_redraw
        move.b  d1,d3
        andi.b  #7,d3
        bne.s   .next
.do_redraw:
        movem.l d0-d7/a0-a3/a5-a6,-(sp)
        addq.w  #2,d0
        moveq   #0,d1
        move.b  -2(a6,d0.w),d1
        lea     -$7dd1(a4),a3
        jsr     $017b9c.l
        movem.l (sp)+,d0-d7/a0-a3/a5-a6
.next:
        jmp     $010cde.l

.setup_done:
        ; Redraw all 16 final bucket counts + d7=0 before returning
        movem.l d0-d7/a0-a3/a5-a6,-(sp)
        moveq   #0,d4
.fin_loop:
        move.w  d4,d0
        addq.w  #2,d0
        moveq   #0,d1
        move.b  (a6,d4.w),d1
        lea     -$7dd1(a4),a3
        jsr     $017b9c.l
        addq.w  #1,d4
        cmpi.w  #16,d4
        blt.s   .fin_loop
        moveq   #$12,d0
        moveq   #0,d1
        lea     -$7dd1(a4),a3
        jsr     $017b9c.l
        movem.l (sp)+,d0-d7/a0-a3/a5-a6
        clr.b   skip_matches
        rts

cond_sim_matches:
        tst.b   skip_matches
        bne.s   .skip
        jsr     $01539a.l
.skip:
        jsr     $015830.l
        jmp     $015296.l

accepted_final_matches:
        tst.b   skip_matches
        beq.s   .orig
        movem.l d0-d7/a0-a3/a6,-(sp)
        jsr     $01539a.l
        movem.l (sp)+,d0-d7/a0-a3/a6
.orig:
        movem.w d0-d2,-(sp)
        moveq   #2,d0
        jmp     $014ce8.l

; ---------------------------------------------------------------------------
; Patch 8: Option A - Early Position Rejection (zero distribution distortion)
; Checks if all 4 divisions for candidate's current position are full in -$35da(a4)
; AND no still-open position is within 40 rating points of current position's rating.
; ---------------------------------------------------------------------------
check_early_reject:
        tst.b   skip_matches
        beq.s   .keep
        move.w  -$35da(a4),d0           ; d6 = 16-bit full-buckets mask
        beq.s   .keep                   ; nothing full yet!
        moveq   #0,d1
        move.b  $5(a5),d1               ; current position (1..4)
        beq.s   .keep
        subq.w  #1,d1                   ; 0..3
        move.w  #$1111,d3
        lsl.w   d1,d3                   ; mask for all 4 divs of current position
        move.w  d0,d4
        and.w   d3,d4
        cmp.w   d3,d4
        bne.s   .keep                   ; at least 1 div still open for this position!

        ; All 4 divs of current pos are full! Check if any open pos is within 40 pts
        lea     -$35ee(a4),a0
        add.w   d1,d1
        move.w  (a0,d1.w),d4            ; current position's rating
        subi.w  #40,d4                  ; threshold = cur_rating - 40
        move.w  #$1111,d3               ; mask for pos p=0..3
        moveq   #3,d1
.chk_p:
        move.w  d0,d5
        and.w   d3,d5
        cmp.w   d3,d5
        beq.s   .next_p                 ; pos p is also completely full
        ; pos p has an open division: can player plausibly switch to it?
        cmp.w   (a0),d4                 ; if (cur_rating - 40) <= rating[p] -> keep!
        ble.s   .keep
.next_p:
        addq.l  #2,a0
        add.w   d3,d3                   ; shift mask left 1
        dbra    d1,.chk_p
        ; No open position is within 40 pts -> reject!
        moveq   #1,d0
        rts
.keep:
        moveq   #0,d0
        rts

; Replaces $014c96: jsr $1515a(pc) / jsr -$7f08(a4) (8 bytes)
early_rej_after_create:
        jsr     $01515a.l               ; create_player
        movem.l d2-d5/a0,-(sp)
        bsr.w   check_early_reject
        movem.l (sp)+,d2-d5/a0
        tst.w   d0
        bne.s   .rej
        bsr.w   fast_lfsr               ; displaced jsr -$7f08(a4)
        jmp     $014c9e.l
.rej:
        clr.b   $4(a5)
        bra.s   early_rej_after_create

; Replaces $014cbe: jsr $1526c(pc) / beq.b $14cb2 (6 bytes)
early_rej_after_season:
        jsr     $01526c.l               ; sim_season (Z=1 if not retired)
        bne.s   .retired
        movem.l d2-d5/a0,-(sp)
        bsr.w   check_early_reject
        movem.l (sp)+,d2-d5/a0
        tst.w   d0
        bne.s   .retired                ; reject early!
        jmp     $014cb2.l               ; continue career loop
.retired:
        jmp     $014cc4.l               ; clr.b $4(a5) / bra $14c96

; ---------------------------------------------------------------------------
; Patch 11: Discreet Title Screen credit ("v1.1 enhanced by dad_prg")
; Drawn centred in 4x6 font on BOTH scr2.men (Program by Dino Dini, y=178, col 4)
; and scr3.men (Main Title Menu, y=184, col 13 dim slate on dark green).
; ---------------------------------------------------------------------------
title_scr2_credit:
        jsr     $017d0c.l               ; draw scr2.men
        movem.l d0-d7/a0-a3,-(sp)
        lea     $078000+186*160.l,a3
        moveq   #4,d0                   ; col 4 ($004 discreet dark blue on teal)
        bsr.s   draw_credit_line
        movem.l (sp)+,d0-d7/a0-a3
        jsr     -$7ff8(a4)              ; wait click/key
        jmp     $01054c.l

title_scr3_credit:
        jsr     $017d0c.l               ; draw scr3.men
        movem.l d0-d7/a0-a3,-(sp)
        lea     $078000+194*160.l,a3
        moveq   #13,d0                  ; col 13 ($324 discreet dim slate on dark green)
        bsr.s   draw_credit_line
        movem.l (sp)+,d0-d7/a0-a3
        jsr     -$7ff8(a4)              ; wait menu click
        jmp     $010558.l

; Input: a3 = screen row base ($078000 + y*160), d0.b = 4-bit colour index (0..15)
draw_credit_line:
        move.w  d0,-(sp)                ; save colour index on stack
        lea     .cr_txt(pc),a0
        moveq   #100,d4                 ; x = (320 - 24*5) / 2 = 100 (centred!)
.cr_ch: moveq   #0,d0
        move.b  (a0)+,d0
        beq.w   .cr_end
        lea     .cr_chr(pc),a1
        moveq   #0,d1
.cr_fn: move.b  (a1)+,d2
        beq.s   .cr_nx
        cmp.b   d2,d0
        beq.s   .cr_gt
        addq.w  #1,d1
        bra.s   .cr_fn
.cr_gt: mulu    #6,d1
        lea     .cr_fnt(pc),a1
        adda.w  d1,a1
        movea.l a3,a2
        moveq   #5,d3
.cr_rw: move.b  (a1)+,d0
        move.w  d4,d5
        moveq   #3,d6
.cr_cl: btst    d6,d0
        beq.s   .cr_np
        move.w  d5,d7
        lsr.w   #4,d7
        lsl.w   #3,d7
        move.w  d5,d1
        andi.w  #15,d1
        move.w  #$8000,d2
        lsr.w   d1,d2
        not.w   d2
        and.w   d2,0(a2,d7.w)
        and.w   d2,2(a2,d7.w)
        and.w   d2,4(a2,d7.w)
        and.w   d2,6(a2,d7.w)
        not.w   d2
        move.w  (sp),d1                 ; 4-bit colour index
        btst    #0,d1
        beq.s   .p1
        or.w    d2,0(a2,d7.w)
.p1:    btst    #1,d1
        beq.s   .p2
        or.w    d2,2(a2,d7.w)
.p2:    btst    #2,d1
        beq.s   .p3
        or.w    d2,4(a2,d7.w)
.p3:    btst    #3,d1
        beq.s   .cr_np
        or.w    d2,6(a2,d7.w)
.cr_np: addq.w  #1,d5
        dbra    d6,.cr_cl
        lea     160(a2),a2
        dbra    d3,.cr_rw
.cr_nx: addq.w  #5,d4
        bra.w   .cr_ch
.cr_end:
        addq.l  #2,sp
        rts

.cr_txt: dc.b   "v1.1 enhanced by dad_prg",0
.cr_chr: dc.b   " .1_abcdeghnprvy",0
.cr_fnt:
        dc.b    %0000,%0000,%0000,%0000,%0000,%0000    ; ' '
        dc.b    %0000,%0000,%0000,%0000,%1000,%0000    ; '.'
        dc.b    %0100,%1100,%0100,%0100,%1110,%0000    ; '1'
        dc.b    %0000,%0000,%0000,%0000,%0000,%1111    ; '_'
        dc.b    %0000,%0110,%0001,%0111,%1011,%0000    ; 'a'
        dc.b    %1000,%1110,%1001,%1001,%1110,%0000    ; 'b'
        dc.b    %0000,%0111,%1000,%1000,%0111,%0000    ; 'c'
        dc.b    %0001,%0111,%1001,%1001,%0111,%0000    ; 'd'
        dc.b    %0000,%0110,%1001,%1111,%0111,%0000    ; 'e'
        dc.b    %0000,%0111,%1001,%0111,%0001,%0110    ; 'g'
        dc.b    %1000,%1110,%1001,%1001,%1001,%0000    ; 'h'
        dc.b    %0000,%1110,%1001,%1001,%1001,%0000    ; 'n'
        dc.b    %0000,%1110,%1001,%1001,%1110,%1000    ; 'p'
        dc.b    %0000,%1011,%1100,%1000,%1000,%0000    ; 'r'
        dc.b    %0000,%1001,%1001,%1001,%0110,%0000    ; 'v'
        dc.b    %0000,%1001,%1001,%0111,%0001,%0110    ; 'y'
        even

; ---------------------------------------------------------------------------
; Data tables
; ---------------------------------------------------------------------------
skip_matches:
        dc.b    0
        even

popcnt_tbl:
        dc.b 0,1,1,2,1,2,2,3,1,2,2,3,2,3,3,4
        dc.b 1,2,2,3,2,3,3,4,2,3,3,4,3,4,4,5
        dc.b 1,2,2,3,2,3,3,4,2,3,3,4,3,4,4,5
        dc.b 2,3,3,4,3,4,4,5,3,4,4,5,4,5,5,6
        dc.b 1,2,2,3,2,3,3,4,2,3,3,4,3,4,4,5
        dc.b 2,3,3,4,3,4,4,5,3,4,4,5,4,5,5,6
        dc.b 2,3,3,4,3,4,4,5,3,4,4,5,4,5,5,6
        dc.b 3,4,4,5,4,5,5,6,4,5,5,6,5,6,6,7
        dc.b 1,2,2,3,2,3,3,4,2,3,3,4,3,4,4,5
        dc.b 2,3,3,4,3,4,4,5,3,4,4,5,4,5,5,6
        dc.b 2,3,3,4,3,4,4,5,3,4,4,5,4,5,5,6
        dc.b 3,4,4,5,4,5,5,6,4,5,5,6,5,6,6,7
        dc.b 2,3,3,4,3,4,4,5,3,4,4,5,4,5,5,6
        dc.b 3,4,4,5,4,5,5,6,4,5,5,6,5,6,6,7
        dc.b 3,4,4,5,4,5,5,6,4,5,5,6,5,6,6,7
        dc.b 4,5,5,6,5,6,6,7,5,6,6,7,6,7,7,8

        include "patches/league92.s"
        include "patches/ko2_bridge.s"
        include "work/luts.inc"
        even
payload_end:
