; ---------------------------------------------------------------------------
; Task 1 (Milestones 1B + 1C): 1989-90 Football League 92-Team Expansion
;   - 92 teams: Div 1 = 20, Div 2 = 24, Div 3 = 24, Div 4 = 24
;   - 2,600-player pool ($1aa90 bytes)
;   - 38-week (Div 1) / 46-week (Div 2-4) Berger round-robin fixture generator
;   - 3 up / 3 down promotion & relegation
;   - Updated Save/Load buffer sizes & 92-team club-byte sentinel ($60/$64)
; ---------------------------------------------------------------------------

TEAM_COUNT      equ     92
TEAM_BYTES      equ     92*100          ; $23f0 (9,200 bytes)
PLAYER_COUNT    equ     2600
PLAYER_BYTES    equ     2600*42         ; $1aa90 (109,200 bytes)

; Called from boot_entry (after micro_opt verifications); returns d0=0 ok, d0!=0 fail
init_league92:
        ; Verify key 1B/1C original bytes before writing
        cmpi.l  #$2f3c0000,$010150.l    ; Malloc($1130)
        bne.w   .l92_fail
        cmpi.w  #$1130,$010154.l
        bne.w   .l92_fail
        cmpi.l  #$2f3c0000,$0102ee.l    ; Malloc($f618)
        bne.w   .l92_fail
        cmpi.w  #$f618,$0102f2.l
        bne.w   .l92_fail
        cmpi.l  #$48e78d04,$013560.l    ; fixture generator
        bne.w   .l92_fail
        cmpi.w  #$7e2b,$0149e2.l        ; moveq #$2b,d7
        bne.w   .l92_fail

        ; 1. Division sizes table at a4-$70b2 ($0225e8): [20, 24, 24, 24]
        move.w  #20,$0225e8.l
        move.w  #24,$0225ea.l
        move.w  #24,$0225ec.l
        move.w  #24,$0225ee.l

        ; 2. Bucket quotas at a4-$7d22 ($021978): 16 bytes
        ;    Div 1 (20): [40, 140, 140, 100]  (420)
        ;    Div 2 (24): [48, 144, 144, 120]  (456)
        ;    Div 3 (24): [48, 144, 144,  96]  (432)
        ;    Div 4 (24): [48, 144, 120,  96]  (408) -> total min = 1,716
        lea     quotas_92(pc),a0
        lea     $021978.l,a1
        moveq   #15,d0
.cp_q:  move.b  (a0)+,(a1)+
        dbra    d0,.cp_q

        ; 3. Team Malloc ($1130 -> $23f0) & division boundaries (10/20/32/44 -> 20/44/68/92)
        move.l  #TEAM_BYTES,$010152.l
        move.w  #20,$0101c6.l           ; div 2 start
        move.w  #44,$0101d4.l           ; div 3 start
        move.w  #68,$0101e2.l           ; div 4 start
        move.w  #92,$0101f0.l           ; total teams

        ; Hook team name loader at $0101ae (10 bytes: jsr -$7f4a / lea (a5),a3 / jsr -$7f7a)
        move.w  #$4eb9,$0101ae.l        ; jsr load_team_name_92.l
        move.l  #load_team_name_92,$0101b0.l
        move.w  #$4e71,$0101b4.l
        move.w  #$4e71,$0101b6.l

        ; 4. Player pool Malloc ($f618 -> $1aa90) & clear/scan ($5db -> 2599)
        move.l  #PLAYER_BYTES,$0102f0.l
        move.w  #$4ef9,$014c36.l
        move.l  #clear_player_pool_2600,$014c38.l
        move.w  #(PLAYER_COUNT-1),$014c64.l

        ; 5. All 44-team loops ($2c -> $5c, $2b -> $5b)
        move.w  #92,$010a48.l           ; initial squad assignment
        move.w  #$7e5b,$01236c.l        ; AI squad/tactic update
        move.w  #$7e5b,$012388.l        ; AI transfer/training
        move.w  #$7e5b,$012a20.l        ; home gate receipts
        move.w  #$7e5b,$012f80.l        ; team name dup check
        move.w  #$7e5b,$014462.l        ; load league names
        move.w  #$7e5b,$0144da.l        ; save league names
        move.w  #$7e5b,$0149e2.l        ; end-of-season reset
        move.w  #$7e5b,$01746c.l        ; weekly wages
        move.w  #$7e5b,$0174ae.l        ; random club finance events
        move.w  #$7e5b,$017532.l        ; initial club cash
        move.w  #$7e5b,$01756a.l        ; initial stadium capacity

        ; 6. Club-byte sentinel ($40 -> $64 / $60) so teams 64..91 aren't mistaken for PM
        move.b  #$64,$0108a3.l          ; move.b #$64,$7(a2)
        move.b  #$60,$010b95.l          ; cmpi.b #$60,$7(a1)

        ; 7. Redirect 3 squad_counts table refs (a4-$77f4) to squad_counts_92
        move.w  #$4ef9,$010b78.l
        move.l  #squad_cnt_10b78,$010b7a.l
        move.w  #$4ef9,$016bae.l
        move.l  #squad_cnt_16bae,$016bb0.l
        move.w  #$4ef9,$016d30.l
        move.l  #squad_cnt_16d30,$016d32.l

        ; 8. Berger round-robin fixture generator ($013560)
        move.w  #$4ef9,$013560.l
        move.l  #berger_fixture_92,$013562.l

        ; 9. Season week thresholds: 22->46 ($16->$2e), 18->38 ($12->$26), 11->23 ($0b->$17), 10->20 ($0a->$14)
        move.w  #46,$0112e4.l
        move.w  #46,$0117ac.l
        move.w  #46,$01181e.l
        move.w  #46,$0119d2.l
        move.w  #46,$011e14.l
        move.w  #38,$012a4c.l
        move.w  #23,$012db4.l
        move.w  #20,$0123a6.l
        move.w  #20,$016fa4.l

        ; 10. Promotion / Relegation: 2 up/down -> 3 up/down ($014a96: moveq #1,d6 -> moveq #2,d6)
        move.w  #$7c02,$014a96.l

        ; 11. Save / Load buffer sizes ($1130 -> $23f0, $f618 -> $1aa90)
        move.l  #TEAM_BYTES,$014630.l
        move.l  #TEAM_BYTES,$01464a.l
        move.l  #PLAYER_BYTES,$01465a.l
        move.l  #PLAYER_BYTES,$014674.l
        move.l  #TEAM_BYTES,$014684.l
        move.l  #TEAM_BYTES,$01469e.l
        move.l  #PLAYER_BYTES,$0146ae.l
        move.l  #PLAYER_BYTES,$0146c8.l

        ; 12. Milestone 1D: Scrolling / Paging UI hooks
        ;     - League Names screen ($012fd8)
        move.w  #$4ef9,$012fd8.l
        move.l  #league_names_92,$012fda.l
        ;     - Division Tables screen ($0137c2)
        move.w  #$4ef9,$0137c2.l
        move.l  #div_tables_92,$0137c4.l
        ;     - Weekly Fixtures ($0133ac) & Results ($013460) paging
        move.w  #$4ef9,$0133ac.l
        move.l  #fixtures_paged_92,$0133ae.l
        move.w  #$4ef9,$013460.l
        move.l  #results_paged_92,$013462.l

        ; 13. Milestone 1E: 92-team Cup schedule (weeks 6,14,22,30,38,45) & R0/R1 draws
        lea     cup_weeks_92(pc),a0
        lea     $0219e9.l,a1            ; a4 - $7cb1
        moveq   #5,d0
.cp_cw: move.b  (a0)+,(a1)+
        dbra    d0,.cp_cw
        move.w  #$4ef9,$013b36.l
        move.l  #cup_draw_r0_92,$013b38.l
        move.w  #$4ef9,$013b92.l
        move.l  #cup_draw_r1_92,$013b94.l

        ; 14. Demo Game & Restart Game ($0105b0): load 92-team FILES/DEMO92.DAT from HD
        move.w  #$4ef9,$0105b0.l
        move.l  #demo_load_92,$0105b2.l

        moveq   #0,d0
        rts
.l92_fail:
        moveq   #1,d0
        rts

; ---------------------------------------------------------------------------
; Load team d7 (0..91) name from 20-byte fixed-stride table into (a5)
; ---------------------------------------------------------------------------
load_team_name_92:
        movem.l d0/a0-a1,-(sp)
        move.w  d7,d0
        mulu.w  #20,d0
        lea     team_names_92(pc),a0
        adda.w  d0,a0
        movea.l a5,a1
.cp:    move.b  (a0)+,(a1)+
        bne.s   .cp
        movem.l (sp)+,d0/a0-a1
        rts

; ---------------------------------------------------------------------------
; Clear 2,600-player pool ($1aa90 bytes) & mark all 2,600 slots free ($ff)
; ---------------------------------------------------------------------------
clear_player_pool_2600:
        movea.l -$2e80(a4),a0
        move.w  #(PLAYER_BYTES/4-1),d1
.clr:   clr.l   (a0)+
        dbra    d1,.clr
        movea.l -$2e80(a4),a0
        move.w  #(PLAYER_COUNT-1),d1
.ff:    move.b  #$ff,$7(a0)
        adda.l  #$2a,a0
        dbra    d1,.ff
        rts

; ---------------------------------------------------------------------------
; Redirects for squad_counts_92 (92 x 4 bytes)
; ---------------------------------------------------------------------------
squad_cnt_10b78:
        lea     squad_counts_92(pc),a0
        move.b  (a0,d4.w),d0
        jmp     $010b80.l

squad_cnt_16bae:
        lea     squad_counts_92(pc),a2
        lea     (a2,d0.w),a2
        jmp     $016bb6.l

squad_cnt_16d30:
        lea     squad_counts_92(pc),a2
        lea     (a2,d0.w),a2
        jmp     $016d38.l

; ---------------------------------------------------------------------------
; Berger round-robin fixture generator (replaces $013560..$0135ae)
; In:  d2 = div (0..3), d3 = week (0..2*(N-1)-1), d4 = match idx (0..N/2-1)
; Out: d6 = N/2 (or 0 if d3 >= 2*(N-1)), a0 = home team ptr, a1 = away team ptr
; Preserves: d0-d5, d7, a2-a6 (same as original $013560!)
; ---------------------------------------------------------------------------
berger_fixture_92:
        movem.l d0-d1/d3-d5/d7/a5,-(sp)
        move.w  d2,d0
        add.w   d0,d0
        lea     -$70b2(a4),a0
        move.w  (a0,d0.w),d5            ; d5 = N (20 or 24)
        moveq   #0,d6                   ; default: no match
        move.w  d5,d7
        subq.w  #1,d7                   ; d7 = rounds = N - 1 (19 or 23)
        move.w  d7,d0
        add.w   d0,d0                   ; d0 = 2 * (N - 1) (38 or 46)
        cmp.w   d0,d3
        bge.s   .done                   ; week >= total_weeks -> d6=0!

        move.w  d5,d6
        lsr.w   #1,d6                   ; d6 = half = N / 2 (10 or 12)

        ; leg (d1) = 0 if d3 < rounds else 1; r (d3) = d3 % rounds
        moveq   #0,d1
        cmp.w   d7,d3
        blt.s   .leg_ok
        sub.w   d7,d3
        moveq   #1,d1
.leg_ok:
        tst.w   d4
        bne.s   .other_match
        ; match 0: tA = r, tB = N - 1; swap if (r & 1) ^ leg
        move.w  d3,d0                   ; tA = r
        move.w  d7,d5                   ; tB = N - 1
        move.w  d3,d4
        andi.w  #1,d4
        eor.w   d1,d4
        beq.s   .lookup
        exg     d0,d5
        bra.s   .lookup

.other_match:
        ; tA = (r + d4) % rounds
        move.w  d3,d0
        add.w   d4,d0
        cmp.w   d7,d0
        blt.s   .ta_ok
        sub.w   d7,d0
.ta_ok:
        ; tB = (r + rounds - d4) % rounds
        move.w  d3,d5
        add.w   d7,d5
        sub.w   d4,d5
        cmp.w   d7,d5
        blt.s   .tb_ok
        sub.w   d7,d5
.tb_ok:
        ; swap if (d4 & 1) ^ leg
        andi.w  #1,d4
        eor.w   d1,d4
        beq.s   .lookup
        exg     d0,d5

.lookup:
        ; d0 = home slot (0..N-1), d5 = away slot (0..N-1)
        jsr     $0135b0.l               ; a1 = team with fixture_slot == d0+1
        movea.l a1,a0
        move.w  d5,d0
        jsr     $0135b0.l               ; a1 = team with fixture_slot == d5+1
.done:
        movem.l (sp)+,d0-d1/d3-d5/d7/a5
        rts

; ---------------------------------------------------------------------------
; Milestone 1D-1: Scrolling League Names screen (replaces $012fd8..$0130ee)
; Clicking active Div 1..4 tab or pressing Up/Down/Space toggles page 0 <-> 12
; ---------------------------------------------------------------------------
league_names_92:
        moveq   #0,d7                   ; current div (0..3)
        clr.w   ui_scroll
.hl_div:
        move.w  d7,d0
        addq.w  #1,d0
        jsr     $017bca.l               ; highlight div button
.redraw:
        move.w  d7,d0
        lsl.w   #2,d0
        lea     -$2e94(a4),a5
        movea.l (a5,d0.w),a5            ; a5 = div base team ptr
        move.w  d7,d0
        add.w   d0,d0
        lea     -$70b2(a4),a3
        move.w  (a3,d0.w),d6            ; d6 = div team count (20 or 24)

        move.w  ui_scroll(pc),d4        ; starting team index (0 or 12)
        move.w  d4,d0
        mulu.w  #$64,d0
        lea     (a5,d0.w),a6            ; a6 = first visible team
        moveq   #0,d5                   ; visual slot 0..11
.draw_row:
        move.w  d5,d0
        addq.w  #8,d0
        jsr     $017f3a.l               ; select widget
        lea     (a6),a3
        jsr     -$7ffe(a4)              ; clear widget box
        move.w  d4,d0
        add.w   d5,d0
        cmp.w   d6,d0
        bge.s   .skip_row
        tst.w   $28(a6)
        beq.s   .norm_row
        moveq   #6,d2
        jsr     $017ad6.l
        bra.s   .skip_row
.norm_row:
        jsr     $017b14.l
.skip_row:
        adda.l  #$64,a6
        addq.w  #1,d5
        cmpi.w  #12,d5
        blt.s   .draw_row

.wait:
        jsr     -$7ff8(a4)              ; d1=0 -> key, d1=-1 -> mouse widget in d0
        tst.w   d1
        beq.s   .got_key
        tst.w   d0
        beq.s   .wait
        cmpi.w  #4,d0
        bgt.s   .not_div
        cmpi.w  #1,d0
        blt.s   .wait
        ; Clicked Div 1..4 tab
        subq.w  #1,d0
        cmp.w   d7,d0
        beq.s   .toggle_page            ; clicking active tab toggles page 0 <-> 12!
        ; Switch division
        move.w  d0,-(sp)
        move.w  d7,d0
        addq.w  #1,d0
        jsr     $017bca.l               ; unhighlight old tab
        move.w  (sp)+,d7
        clr.w   ui_scroll
        bra.w   .hl_div

.got_key:
        ; Check Up ($48), Down ($50), Space ($20)
        cmpi.b  #$20,d0
        beq.s   .toggle_page
        swap    d0
        cmpi.b  #$48,d0
        beq.s   .page0
        cmpi.b  #$50,d0
        beq.s   .page12
        bra.s   .wait
.page0:
        clr.w   ui_scroll
        bra.w   .redraw
.page12:
        move.w  #12,ui_scroll
        bra.w   .redraw
.toggle_page:
        eori.w  #12,ui_scroll
        bra.w   .redraw

.not_div:
        cmpi.w  #8,d0
        blt.s   .other_btn
        cmpi.w  #$13,d0
        bgt.s   .other_btn
        ; Clicked a team name box (8..19) -> edit team (ui_scroll + d0 - 8)
        subq.w  #8,d0
        add.w   ui_scroll(pc),d0
        cmp.w   d6,d0
        bge.w   .wait
        mulu.w  #$64,d0
        move.w  d0,-$3862(a4)
        lea     (a5,d0.w),a2
        lea     -$2f94(a4),a3
        jsr     -$7f7a(a4)
        lea     (a5,d0.w),a6
        move.w  -$3162(a4),d0
        jsr     $017f3a.l
        moveq   #$14,d0
        tst.w   $28(a6)
        beq.s   .ed_norm
        move.b  $1c(a2),d2
        move.b  #6,$1c(a2)
        jsr     -$7ff2(a4)
        move.b  d2,$1c(a2)
        bra.s   .ed_chk
.ed_norm:
        jsr     -$7ff2(a4)
.ed_chk:
        move.w  -$3862(a4),d0
        lea     (a5,d0.w),a3
        jsr     $012f78.l
        beq.w   .redraw
        lea     -$2f94(a4),a2
        jsr     -$7f7a(a4)
        bra.w   .wait

.other_btn:
        cmpi.w  #6,d0
        beq.s   .done
        cmpi.w  #5,d0
        beq.s   .do_load
        cmpi.w  #7,d0
        beq.s   .do_save
        jmp     $012fd0.l
.do_load:
        jsr     $014434.l
        jmp     $012fd0.l
.do_save:
        jsr     $0144aa.l
        jmp     $012fd0.l
.done:
        rts

; ---------------------------------------------------------------------------
; Milestone 1D-2: Scrolling Division Tables (replaces $0137c2..$0137fc)
; Clicking active Div 1..4 tab toggles top 12 <-> bottom 12;
; Up/Down keys scroll by 4 rows; Space toggles top/bottom; Esc exits.
; ---------------------------------------------------------------------------
div_tables_92:
        lea     -$7cf1(a4),a2
        jsr     $017d0c.l
        movea.l -$2e78(a4),a0
        move.w  $16(a0),d7              ; d7 = human club's division (1..4)
        ; Auto-scroll to show human club if ranked >= 12
        clr.w   ui_scroll
        cmpi.w  #12,$24(a0)
        blt.s   .hl_tab
        move.w  d7,d0
        subq.w  #1,d0
        add.w   d0,d0
        lea     -$70b2(a4),a1
        move.w  (a1,d0.w),d0
        subi.w  #12,d0
        move.w  d0,ui_scroll
.hl_tab:
        move.w  d7,d0
        jsr     $017bca.l
.draw_tbl:
        bsr.w   draw_table_window_92
.wait:
        jsr     -$7ff8(a4)
        tst.w   d1
        beq.s   .key
        tst.w   d0
        beq.s   .wait
        cmpi.w  #5,d0
        beq.w   .exit
        cmpi.w  #1,d0
        blt.s   .wait
        cmpi.w  #4,d0
        bgt.s   .wait
        cmp.w   d7,d0
        beq.s   .toggle_tb              ; clicking active Div tab toggles top <-> bottom!
        exg     d7,d0
        jsr     $017bca.l               ; unhighlight old tab
        clr.w   ui_scroll
        bra.s   .hl_tab

.key:
        cmpi.b  #$1b,d0                 ; Esc -> exit
        beq.w   .exit
        cmpi.b  #$20,d0                 ; Space -> toggle top/bottom
        beq.s   .toggle_tb
        swap    d0
        cmpi.b  #$48,d0                 ; Up arrow -> scroll up 4
        beq.s   .scr_up
        cmpi.b  #$50,d0                 ; Down arrow -> scroll down 4
        beq.s   .scr_dn
        bra.s   .wait
.scr_up:
        move.w  ui_scroll(pc),d0
        beq.s   .wait
        subq.w  #4,d0
        bpl.s   .set_scr
        moveq   #0,d0
        bra.s   .set_scr
.scr_dn:
        bsr.s   .max_scroll
        move.w  ui_scroll(pc),d1
        cmp.w   d0,d1
        bge.s   .wait
        addq.w  #4,d1
        cmp.w   d0,d1
        ble.s   .set_scr_d1
        move.w  d0,d1
.set_scr_d1:
        move.w  d1,d0
        bra.s   .set_scr
.toggle_tb:
        bsr.s   .max_scroll
        tst.w   ui_scroll
        beq.s   .set_scr
        moveq   #0,d0
.set_scr:
        move.w  d0,ui_scroll
        bra.w   .draw_tbl
.max_scroll:
        move.w  d7,d0
        subq.w  #1,d0
        add.w   d0,d0
        lea     -$70b2(a4),a0
        move.w  (a0,d0.w),d0
        subi.w  #12,d0
        rts
.exit:
        rts

; Draw 12 visible rows of division d7 (1..4) starting at rank ui_scroll
draw_table_window_92:
        movem.l d0-d7/a0-a3/a5-a6,-(sp)
        move.w  d7,d4
        subq.w  #1,d4
        add.w   d4,d4
        lea     -$70b2(a4),a0
        move.w  (a0,d4.w),d6            ; d6 = div team count (20 or 24)
        add.w   d4,d4
        lea     -$2e94(a4),a0
        movea.l (a0,d4.w),a5            ; a5 = first team in div
        move.w  ui_scroll(pc),d3        ; d3 = first visible rank (0..N-12)
.team_loop:
        move.w  $24(a5),d5              ; d5 = team's league rank (0..N-1)
        sub.w   d3,d5                   ; visual row = rank - ui_scroll
        bmi.s   .next_team
        cmpi.w  #12,d5
        bge.s   .next_team
        lsl.w   #3,d5                   ; row * 8
        addi.w  #10,d5                  ; widget ID = 10 + row * 8
        move.w  d5,d0
        jsr     $017f3a.l
        jsr     -$7ffe(a4)              ; clear name cell
        lea     (a5),a3
        jsr     $017b14.l               ; draw team name
        lea     -$7cba(a4),a3
        move.w  $18(a5),d1              ; P
        bsr.s   .col
        move.w  $1a(a5),d1              ; W
        bsr.s   .col
        move.w  $1c(a5),d1              ; D
        bsr.s   .col
        move.w  $18(a5),d1              ; L = P - W - D
        sub.w   $1a(a5),d1
        sub.w   $1c(a5),d1
        bsr.s   .col
        move.w  $20(a5),d1              ; F
        bsr.s   .col
        move.w  $22(a5),d1              ; A
        bsr.s   .col
        move.w  $1e(a5),d1              ; Pts
        bsr.s   .col
.next_team:
        adda.l  #$64,a5
        subq.w  #1,d6
        bgt.s   .team_loop
        movem.l (sp)+,d0-d7/a0-a3/a5-a6
        rts
.col:
        addq.w  #1,d5
        move.w  d5,d0
        jsr     $017b9c.l
        rts

; ---------------------------------------------------------------------------
; Milestone 1D-3: Paged Weekly Fixtures ($0133ac) & Results ($013460)
; Shows Page 0 (first 5/5/6/6), Page 1 (next 5/5/6/6), Page 2 (last 2 Div 2)
; ---------------------------------------------------------------------------
fixtures_paged_92:
        moveq   #0,d7                   ; d7 = 0 (fixtures, no scores)
        bsr.s   show_paged_matches_92
        rts

results_paged_92:
        subq.w  #1,-$2d7c(a4)
        moveq   #1,d7                   ; d7 = 1 (results, with scores)
        bsr.s   show_paged_matches_92
        addq.w  #1,-$2d7c(a4)
        rts

show_paged_matches_92:
        movem.l d2-d6/a0-a3,-(sp)
        moveq   #0,d5                   ; page = 0, 1, 2
.page_loop:
        lea     -$7cfb(a4),a2
        jsr     $017d0c.l               ; fresh fixtures/results screen
        ; Draw header ("Week N Fixtures" / "Week N Results")
        clr.b   -$2f94(a4)
        move.w  #$a9,d0
        jsr     -$7f9e(a4)
        move.w  -$2d7c(a4),d0
        addq.w  #1,d0
        jsr     -$7f98(a4)
        move.w  #$d0,d0
        tst.w   d7
        beq.s   .hdr_ok
        move.w  #$d1,d0
.hdr_ok:
        jsr     -$7f9e(a4)
        moveq   #$64,d0
        jsr     $017f3a.l
        lea     -$2f94(a4),a3
        jsr     $017b14.l

        ; Draw each division's slice for page d5:
        ; Div 0 (max 5 slots @ 1):  start = d5*5,  count = 5
        ; Div 1 (max 5 slots @ 11): start = d5*5,  count = 5
        ; Div 2 (max 6 slots @ 21): start = d5*6,  count = 6
        ; Div 3 (max 6 slots @ 33): start = d5*6,  count = 6
        moveq   #0,d2
        moveq   #1,d1
        move.w  d5,d4
        mulu.w  #5,d4
        moveq   #5,d6
        bsr.s   .draw_div_slice

        moveq   #1,d2
        moveq   #$b,d1
        move.w  d5,d4
        mulu.w  #5,d4
        moveq   #5,d6
        bsr.s   .draw_div_slice

        moveq   #2,d2
        moveq   #$15,d1
        move.w  d5,d4
        mulu.w  #6,d4
        moveq   #6,d6
        bsr.s   .draw_div_slice

        moveq   #3,d2
        moveq   #$21,d1
        move.w  d5,d4
        mulu.w  #6,d4
        moveq   #6,d6
        bsr.s   .draw_div_slice

.wait_pg:
        jsr     -$7ff8(a4)              ; returns on any mouse click or keypress
        addq.w  #1,d5
        cmpi.w  #3,d5
        blt.w   .page_loop
        movem.l (sp)+,d2-d6/a0-a3
        rts

; Draw up to d6 matches for div d2 starting at match index d4, UI slot d1
.draw_div_slice:
        movem.l d3-d6,-(sp)
        move.w  d6,d3                   ; d3 = remaining slots to draw
        add.w   d4,d3                   ; d3 = end match index
.sl_loop:
        cmp.w   d3,d4
        bge.s   .sl_done
        move.w  d3,-(sp)
        move.w  -$2d7c(a4),d3
        bsr.w   berger_fixture_92       ; out: d6 = N/2 (0 if no match), a0=home, a1=away
        tst.w   d6
        beq.s   .sl_skip
        cmp.w   d6,d4
        bge.s   .sl_skip
        move.w  d1,d0
        jsr     $017f3a.l
        lea     (a0),a3
        jsr     $017b14.l
        lea     (a1),a3
        addq.w  #1,d1
        move.w  d1,d0
        jsr     $017f3a.l
        jsr     $017b14.l
        tst.w   d7
        beq.s   .sl_noscore
        move.w  d1,d0
        move.w  d1,-(sp)
        addi.w  #$31,d0
        move.w  $2a(a0),d1
        lea     -$7cba(a4),a3
        jsr     $017b9c.l
        move.w  (sp),d0
        addi.w  #$32,d0
        move.w  $2a(a1),d1
        jsr     $017b9c.l
        move.w  (sp)+,d1
.sl_noscore:
        addq.w  #1,d1
        bra.s   .sl_next
.sl_skip:
        addq.w  #2,d1
.sl_next:
        move.w  (sp)+,d3
        addq.w  #1,d4
        bra.s   .sl_loop
.sl_done:
        movem.l (sp)+,d3-d6
        rts

; ---------------------------------------------------------------------------
; Milestone 1E: 92-team Cup R0 & R1 draws (guaranteed human club inclusion!)
;   R0 ($013b36): 24 teams from Div 3 & Div 4 (indices 44..91) -> 12 ties
;   R1 ($013b92): 20 teams from Div 1 & Div 2 (indices 0..43) + 12 R0 winners -> 16 ties
; ---------------------------------------------------------------------------
cup_draw_r0_92:
        ; Clear 172-byte cup bracket at -$2d72(a4) to $ffff
        lea     -$2d72(a4),a2
        moveq   #$55,d7
.clr_c: move.w  #$ffff,(a2)+
        dbra    d7,.clr_c

        ; Fill temp pool with 48 teams (44..91), shuffle, ensure human club in first 24
        lea     cup_pool_tmp(pc),a0
        moveq   #44,d0
        moveq   #47,d1
.f48:   move.b  d0,(a0)+
        addq.w  #1,d0
        dbra    d1,.f48

        ; Fisher-Yates shuffle 48 bytes
        lea     cup_pool_tmp(pc),a0
        moveq   #47,d6
        moveq   #48,d3
        bsr.s   cup_shuffle_bytes

        ; If human team is in 44..91, guarantee it is in first 24!
        move.w  -$2e42(a4),d0           ; human team index (0..91)
        cmpi.w  #44,d0
        blt.s   .copy_r0
        moveq   #24,d1
        bsr.s   cup_ensure_in_first_n

.copy_r0:
        lea     cup_pool_tmp(pc),a0
        lea     -$2d72(a4),a6
        moveq   #23,d5
.c24:   move.b  (a0)+,(a6)+
        move.b  #$ff,(a6)+
        dbra    d5,.c24
        rts

cup_draw_r1_92:
        ; Fill temp pool with 44 teams (0..43), shuffle, ensure human club in first 20
        lea     cup_pool_tmp(pc),a0
        moveq   #0,d0
        moveq   #43,d1
.f44:   move.b  d0,(a0)+
        addq.w  #1,d0
        dbra    d1,.f44

        lea     cup_pool_tmp(pc),a0
        moveq   #43,d6
        moveq   #44,d3
        bsr.s   cup_shuffle_bytes

        move.w  -$2e42(a4),d0
        cmpi.w  #44,d0
        bge.s   .copy_r1
        moveq   #20,d1
        bsr.s   cup_ensure_in_first_n

.copy_r1:
        ; Copy first 20 Div 1/2 teams into -$2d42(a4), then jump to original $013bac
        ; (which appends the 12 R0 winners and shuffles all 32 teams!)
        lea     cup_pool_tmp(pc),a0
        lea     -$2d42(a4),a6
        moveq   #19,d5
.c20:   move.b  (a0)+,(a6)+
        move.b  #$ff,(a6)+
        dbra    d5,.c20
        jmp     $013bac.l

; Shuffle d3 bytes at (a0), d6 = d3 - 1
cup_shuffle_bytes:
        bsr.w   fast_lfsr
        moveq   #0,d5
        move.w  -$38da(a4),d5
        divu.w  d3,d5
        swap    d5
        move.b  (a0,d6.w),d0
        move.b  (a0,d5.w),(a0,d6.w)
        move.b  d0,(a0,d5.w)
        dbra    d6,cup_shuffle_bytes
        rts

; Ensure byte d0 is within first d1 entries of cup_pool_tmp (48 bytes)
cup_ensure_in_first_n:
        lea     cup_pool_tmp(pc),a0
        moveq   #0,d2
.find:  cmp.b   (a0,d2.w),d0
        beq.s   .found
        addq.w  #1,d2
        cmpi.w  #48,d2
        blt.s   .find
        rts
.found: cmp.w   d1,d2
        blt.s   .ok_in
        ; Swap with entry 0
        move.b  (a0),d3
        move.b  d0,(a0)
        move.b  d3,(a0,d2.w)
.ok_in: rts

; ---------------------------------------------------------------------------
; Demo Game & Restart Game ($0105b0): load 92-team FILES/DEMO92.DAT via PP HD mode
; ---------------------------------------------------------------------------
demo_load_92:
        jsr     $006946.w               ; PP set_hd_mode ($6cba = 7)
        lea     demo92_fname(pc),a2
        jsr     $014554.l               ; load_game
        move.w  d0,-(sp)
        jsr     $006942.w               ; PP set_prd_mode ($6cba = 0)
        move.w  (sp)+,d0
        tst.w   d0
        beq.s   .demo_fail
        jmp     $0105bc.l               ; start game!
.demo_fail:
        jmp     $010534.l

; Re-populate all 92 team names from team_names_92 (called at start of New Game)
reset_team_names_92:
        movem.l d0/d7/a0-a1/a5,-(sp)
        movea.l -$2e94(a4),a5
        moveq   #0,d7
.rst_loop:
        bsr.w   load_team_name_92
        adda.l  #$64,a5
        addq.w  #1,d7
        cmpi.w  #92,d7
        blt.s   .rst_loop
        movem.l (sp)+,d0/d7/a0-a1/a5
        rts

demo92_fname:
        dc.b    "DEMO92.DAT",0
        even

cup_weeks_92:
        dc.b    6,14,22,30,38,45
ui_scroll:
        dc.w    0
cup_pool_tmp:
        ds.b    48
        even

; ---------------------------------------------------------------------------
; 92-team data tables (generated by pmpatch.py into work/league92_data.inc)
; ---------------------------------------------------------------------------
quotas_92:
        dc.b    40,140,140,100          ; Div 1 (20 teams)
        dc.b    48,144,144,120          ; Div 2 (24 teams)
        dc.b    48,144,144,96           ; Div 3 (24 teams)
        dc.b    48,144,120,96           ; Div 4 (24 teams)

        include "work/league92_data.inc"
        even
