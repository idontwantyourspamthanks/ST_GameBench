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

        ; 4. Player pool Malloc ($f618 -> $1aa90) & scan limit ($5db -> 2599)
        move.l  #PLAYER_BYTES,$0102f0.l
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

        ; 7. Season week thresholds: 22->46 ($16->$2e), 18->38 ($12->$26), 11->23 ($0b->$17), 10->20 ($0a->$14)
        move.w  #46,$0112e4.l
        move.w  #46,$0117ac.l
        move.w  #46,$01181e.l
        move.w  #46,$0119d2.l
        move.w  #46,$011e14.l
        move.w  #38,$012a4c.l
        move.w  #23,$012db4.l
        move.w  #20,$0123a6.l
        move.w  #20,$016fa4.l

        ; 8. Promotion / Relegation: 2 up/down -> 3 up/down ($014a96: moveq #1,d6 -> moveq #2,d6)
        move.w  #$7c02,$014a96.l

        ; 9. Save / Load buffer sizes ($1130 -> $23f0, $f618 -> $1aa90)
        move.l  #TEAM_BYTES,$014630.l
        move.l  #TEAM_BYTES,$01464a.l
        move.l  #PLAYER_BYTES,$01465a.l
        move.l  #PLAYER_BYTES,$014674.l
        move.l  #TEAM_BYTES,$014684.l
        move.l  #TEAM_BYTES,$01469e.l
        move.l  #PLAYER_BYTES,$0146ae.l
        move.l  #PLAYER_BYTES,$0146c8.l

        ; 10. Milestone 1E: 92-team Cup schedule (weeks 6,14,22,30,38,45)
        lea     cup_weeks_92(pc),a0
        lea     $0219e9.l,a1            ; a4 - $7cb1
        moveq   #5,d0
.cp_cw: move.b  (a0)+,(a1)+
        dbra    d0,.cp_cw

        ; 11. Install all 12 6-byte jmp hooks via compact table
        lea     l92_jmp_tbl(pc),a0
        moveq   #11,d0
.l92_jh:
        movea.l (a0)+,a1
        move.w  #$4ef9,(a1)+
        move.l  (a0)+,(a1)
        dbra    d0,.l92_jh

        moveq   #0,d0
        rts
.l92_fail:
        moveq   #1,d0
        rts

l92_jmp_tbl:
        dc.l    $014c36,clear_player_pool_2600
        dc.l    $010b78,squad_cnt_10b78
        dc.l    $016bae,squad_cnt_16bae
        dc.l    $016d30,squad_cnt_16d30
        dc.l    $013560,berger_fixture_92
        dc.l    $012fd8,league_names_92
        dc.l    $0137c2,div_tables_92
        dc.l    $0133ac,fixtures_paged_92
        dc.l    $013460,results_paged_92
        dc.l    $013b36,cup_draw_r0_92
        dc.l    $013b92,cup_draw_r1_92
        dc.l    $0105b0,demo_load_92

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
; Milestone 1D-2 & 1D-3 (v1.1 Upgrade):
;   - Full Single-Screen Division Tables (all 20 or 24 clubs on ONE screen,
;     zero scrolling, human club highlighted, promotion/relegation lines)
;   - Division-Tabbed This Week's Fixtures & Last Week's Results (opens on
;     human club's current division with native Div 1..4 & Done buttons at
;     the bottom!)
; ---------------------------------------------------------------------------

; Mode codes in l92_view_mode: 0 = Fixtures, 1 = Results, 2 = Division Tables
div_tables_92:
        moveq   #2,d0
        bra.s   l92_run_tabbed_view

fixtures_paged_92:
        moveq   #0,d0
        bra.s   l92_run_tabbed_view

results_paged_92:
        subq.w  #1,-$2d7c(a4)
        moveq   #1,d0
        bsr.s   l92_run_tabbed_view
        addq.w  #1,-$2d7c(a4)
        rts

l92_run_tabbed_view:
        movem.l d2-d7/a0-a3/a5-a6,-(sp)
        move.w  d0,l92_view_mode
        ; Cache ui_logbase & hold mouse hidden, then load scr22.men WITHOUT drawing
        ; its 100 obsolete 12x8 table-cell widgets (saves ~350ms on every open!)
        move.w  #3,-(sp)
        trap    #14
        addq.l  #2,sp
        move.l  d0,ui_logbase
        tst.b   ui_mouse_held
        bne.s   .mh_ok
        st      ui_mouse_held
        jsr     -$7f26(a4)
.mh_ok:
        jsr     $0176ba.l               ; clear screen (Setscreen)
        jsr     $017ece.l               ; free previous screen's widgets
        lea     -$7cf1(a4),a2
        jsr     $017d28.l               ; load scr22.men widgets (skip $017eb4!)

        ; Disable old 12-row table cell widgets (wid > 5) so they never intercept clicks
        movea.l -$3166(a4),a2
.dis_w: move.l  a2,d0
        beq.s   .dis_done
        cmpi.w  #5,$10(a2)
        ble.s   .dis_nx
        clr.w   $10(a2)
.dis_nx:
        movea.l (a2),a2
        bra.s   .dis_w
.dis_done:

        ; Grab native bright yellow text colour ($1c) & royal-blue button bg ($17) from widget 1
        moveq   #1,d0
        jsr     $017f3a.l
        moveq   #15,d1
        moveq   #7,d2
        move.l  a2,d0
        beq.s   .hl_def
        move.b  $1c(a2),d1
        andi.w  #15,d1
        move.b  $17(a2),d2
        andi.w  #15,d2
.hl_def:
        move.w  d1,l92_hl_col
        move.w  d2,l92_btn_col

        ; Clear entire 320x200 screen to dark purple background (col 0)
        moveq   #0,d0
        moveq   #0,d1
        move.w  #319,d2
        move.w  #199,d3
        moveq   #0,d4
        bsr.w   l92_fill_rect

        ; Reposition & redraw native buttons wid 1..4 & wid 5 in PM's exact 3D style!
        ;   Division Tables (mode=2): Div 1..4 at y=18 (h=11), Done at y=187 (h=11)
        ;   Fixtures/Results (0/1):   Div 1..4 at y=165 (h=12), Done at y=182 (h=13)
        move.w  #165,d5                 ; Div 1..4 y
        moveq   #12,d6                  ; Div 1..4 h
        move.w  #182,d3                 ; Done y
        moveq   #13,d4                  ; Done h
        cmpi.w  #2,l92_view_mode
        bne.s   .pos_btns
        moveq   #18,d5
        moveq   #11,d6
        move.w  #187,d3
        moveq   #11,d4
.pos_btns:
        moveq   #1,d2
.btn_lp:
        move.w  d2,d0
        jsr     $017f3a.l
        move.l  a2,d0
        beq.s   .btn_nx
        move.w  d5,$a(a2)
        move.w  d6,$e(a2)
        jsr     $017f52.l               ; native 3D widget draw
.btn_nx:
        addq.w  #1,d2
        cmpi.w  #4,d2
        ble.s   .btn_lp

        moveq   #5,d0
        jsr     $017f3a.l
        move.l  a2,d0
        beq.s   .done_ok
        move.w  d3,$a(a2)
        move.w  d4,$e(a2)
        jsr     $017f52.l               ; native Done button
.done_ok:
        ; Default to human club's current division (1..4)
        movea.l -$2e78(a4),a0
        move.w  $16(a0),d7
        cmpi.w  #1,d7
        blt.s   .d7_fix
        cmpi.w  #4,d7
        ble.s   .d7_ok
.d7_fix:
        moveq   #1,d7
.d7_ok:
        move.w  d7,d0
        jsr     $017bca.l               ; highlight active division tab

.redraw_content:
        jsr     -$7f26(a4)              ; hide mouse during panel redraw
        cmpi.w  #2,l92_view_mode
        beq.s   .do_table
        bsr.w   l92_draw_matches_panel
        bra.s   .draw_done
.do_table:
        bsr.w   l92_draw_table_panel
.draw_done:
        jsr     -$7f20(a4)              ; release local hide (wait_event releases outer hold!)

.wait_ev:
        jsr     -$7ff8(a4)              ; wait_event (shows mouse ONCE via fast_wait_event!)
        tst.w   d1
        beq.s   .got_key
        tst.w   d0
        beq.s   .wait_ev
        cmpi.w  #5,d0                   ; Done button
        beq.s   .exit_view
        cmpi.w  #1,d0
        blt.s   .wait_ev
        cmpi.w  #4,d0
        bgt.s   .wait_ev
        bra.s   .switch_div

.got_key:
        cmpi.b  #$1b,d0                 ; Esc -> exit
        beq.s   .exit_view
        subi.b  #'0',d0                 ; '1'..'4' -> quick division switch
        cmpi.b  #1,d0
        blt.s   .wait_ev
        cmpi.b  #4,d0
        bgt.s   .wait_ev
        andi.w  #7,d0

.switch_div:
        cmp.w   d7,d0
        beq.s   .wait_ev                ; already viewing this division
        jsr     -$7f26(a4)
        exg     d7,d0
        jsr     $017bca.l               ; unhighlight old tab
        move.w  d7,d0
        jsr     $017bca.l               ; highlight new tab
        jsr     -$7f20(a4)
        bra.s   .redraw_content

.exit_view:
        movem.l (sp)+,d2-d7/a0-a3/a5-a6
        rts

; ---------------------------------------------------------------------------
; Full Single-Screen Division Table Panel (20 or 24 teams at 6px pitch!)
; In: d7.w = division (1..4)
; ---------------------------------------------------------------------------
l92_draw_table_panel:
        movem.l d0-d6/a0-a3/a5-a6,-(sp)
        ; Title banner at y=2..14
        lea     l92_str_divtbl(pc),a3
        moveq   #2,d1
        moveq   #14,d3
        bsr.w   l92_draw_banner

        ; Clear interior table area y=31..185
        moveq   #0,d0
        moveq   #31,d1
        move.w  #319,d2
        move.w  #185,d3
        moveq   #0,d4
        bsr.w   l92_fill_rect

        ; Header bar y=32..39 (native royal blue) + yellow column labels
        moveq   #4,d0
        moveq   #32,d1
        move.w  #315,d2
        moveq   #39,d3
        move.w  l92_btn_col(pc),d4
        bsr.w   l92_fill_rect
        lea     l92_str_tblhdr(pc),a3
        moveq   #8,d0
        moveq   #33,d1
        move.w  l92_hl_col(pc),d2
        bsr.w   l92_draw_str

        ; Look up division team count (d6 = 20 or 24) and base team ptr (a5)
        move.w  d7,d4
        subq.w  #1,d4
        add.w   d4,d4
        lea     -$70b2(a4),a0
        move.w  (a0,d4.w),d6
        move.w  d6,l92_cur_cnt
        add.w   d4,d4
        lea     -$2e94(a4),a0
        movea.l (a0,d4.w),a5

.tbl_lp:
        move.w  $24(a5),d5              ; rank (0..N-1)
        move.w  d5,d1
        mulu.w  #6,d1
        addi.w  #41,d1                  ; row_y = 41 + rank * 6

        ; Alternating dark navy (col 1) / dark slate (col 2) row background
        moveq   #1,d4
        btst    #0,d5
        beq.s   .t_bg
        moveq   #2,d4
.t_bg:
        moveq   #4,d0
        move.w  #315,d2
        move.w  d1,d3
        addq.w  #5,d3
        bsr.w   l92_fill_rect

        ; Text colour: bright yellow for human club, bright white (15) otherwise
        moveq   #15,d2
        cmpa.l  -$2e78(a4),a5
        bne.s   .t_col
        move.w  l92_hl_col(pc),d2
.t_col:
        ; POS (rank + 1) right-aligned at x=8 (10..24) or x=14 (1..9)
        move.w  d5,d3
        addq.w  #1,d3
        moveq   #8,d0
        cmpi.w  #10,d3
        bge.s   .pos_x
        moveq   #14,d0
.pos_x:
        bsr.w   l92_draw_num
        ; CLUB name at x=26
        lea     (a5),a3
        moveq   #26,d0
        bsr.w   l92_draw_str
        ; Draw P, W, D, L, GF, GA, PTS via compact loop (saves ~60 bytes!)
        move.w  #152,d0
        lea     l92_stat_offs(pc),a0
        moveq   #6,d4
.t_st:  moveq   #0,d3
        move.b  (a0)+,d3
        bpl.s   .t_ld
        move.w  $18(a5),d3              ; L = P - W - D
        sub.w   $1a(a5),d3
        sub.w   $1c(a5),d3
        bra.s   .t_pr
.t_ld:  move.w  0(a5,d3.w),d3
.t_pr:  bsr.w   l92_draw_num
        addi.w  #24,d0
        dbra    d4,.t_st

        adda.l  #$64,a5
        subq.w  #1,d6
        bgt.w   .tbl_lp

        ; Promotion line (after 3rd place, Div 2-4) & Relegation line (before bottom 3, Div 1-3)
        cmpi.w  #1,d7
        ble.s   .chk_rel
        moveq   #4,d0
        moveq   #58,d1                  ; 41 + 3*6 - 1
        move.w  #315,d2
        move.w  d1,d3
        move.w  l92_hl_col(pc),d4
        bsr.w   l92_fill_rect
.chk_rel:
        cmpi.w  #4,d7
        bge.s   .tbl_done
        move.w  l92_cur_cnt(pc),d1
        subq.w  #3,d1
        mulu.w  #6,d1
        addi.w  #40,d1                  ; 41 + (N-3)*6 - 1
        moveq   #4,d0
        move.w  #315,d2
        move.w  d1,d3
        move.w  l92_hl_col(pc),d4
        bsr.w   l92_fill_rect
.tbl_done:
        movem.l (sp)+,d0-d6/a0-a3/a5-a6
        rts

; ---------------------------------------------------------------------------
; Division-Tabbed Weekly Fixtures (mode=0) & Results (mode=1) Panel
; In: d7.w = division (1..4)
; ---------------------------------------------------------------------------
l92_draw_matches_panel:
        movem.l d0-d6/a0-a3/a5-a6,-(sp)
        ; Build title: "Week N Fixtures - Div X" or "Week N Results - Div X"
        clr.b   -$2f94(a4)
        move.w  #$a9,d0                 ; "Week "
        jsr     -$7f9e(a4)
        move.w  -$2d7c(a4),d0
        addq.w  #1,d0
        jsr     -$7f98(a4)
        move.w  #$d0,d0                 ; " Fixtures"
        tst.w   l92_view_mode
        beq.s   .m_hdr
        move.w  #$d1,d0                 ; " Results"
.m_hdr:
        jsr     -$7f9e(a4)
        ; Append " - Div X"
        lea     -$2f94(a4),a0
.m_end: tst.b   (a0)+
        bne.s   .m_end
        subq.l  #1,a0
        lea     l92_str_div_sfx(pc),a1
.m_cat: move.b  (a1)+,(a0)+
        bne.s   .m_cat
        move.w  d7,d0
        addi.b  #'0',d0
        move.b  d0,-2(a0)               ; replace 'X' with '1'..'4'

        ; Draw top title banner y=4..18
        lea     -$2f94(a4),a3
        moveq   #4,d1
        moveq   #18,d3
        bsr.w   l92_draw_banner

        ; Clear match list area y=22..160
        moveq   #0,d0
        moveq   #22,d1
        move.w  #319,d2
        move.w  #160,d3
        moveq   #0,d4
        bsr.w   l92_fill_rect

        ; Draw all 10 (Div 1) or 12 (Div 2/3/4) matches for division d7
        move.w  d7,d2
        subq.w  #1,d2                   ; d2 = div (0..3)
        move.w  -$2d7c(a4),d3           ; d3 = week
        moveq   #0,d4                   ; d4 = match idx
.m_lp:
        bsr.w   berger_fixture_92       ; out: d6 = N/2 (0 if no match), a0=home, a1=away
        tst.w   d6
        beq.w   .m_none
        cmp.w   d6,d4
        bge.w   .m_done

        movea.l a0,a5                   ; a5 = home club
        movea.l a1,a6                   ; a6 = away club
        move.w  d4,d1
        mulu.w  #10,d1
        addi.w  #28,d1                  ; row_y = 28 + idx * 10 (h=9)

        ; Alternating dark navy (col 1) / dark slate (col 2) match strip
        move.w  d4,d0
        andi.w  #1,d0
        addq.w  #1,d0                   ; col 1 or 2
        movem.l d1-d4,-(sp)
        move.w  d0,d4
        moveq   #6,d0
        move.w  #313,d2
        move.w  d1,d3
        addq.w  #8,d3
        bsr.w   l92_fill_rect
        movem.l (sp)+,d1-d4

        ; Highlight human club's fixture in bright yellow!
        movem.l d2-d3,-(sp)
        moveq   #15,d2
        cmpa.l  -$2e78(a4),a5
        beq.s   .m_hl
        cmpa.l  -$2e78(a4),a6
        bne.s   .m_col
.m_hl:
        move.w  l92_hl_col(pc),d2
.m_col:
        addq.w  #2,d1                   ; text_y = row_y + 2
        ; Home team at x=12
        moveq   #12,d0
        movea.l a5,a3
        bsr.w   l92_draw_str
        ; Away team at x=186
        move.w  #186,d0
        movea.l a6,a3
        bsr.w   l92_draw_str
        ; Center: "v" for Fixtures, "H - A" for Results (in bright yellow!)
        move.w  l92_hl_col(pc),d2
        tst.w   l92_view_mode
        bne.s   .m_score
        move.w  #157,d0
        lea     l92_str_v(pc),a3
        bsr.w   l92_draw_str
        bra.s   .m_row_end
.m_score:
        move.w  #143,d0
        move.w  $2a(a5),d3              ; home goals
        bsr.w   l92_draw_num
        move.w  #157,d0
        lea     l92_str_dash(pc),a3
        bsr.w   l92_draw_str
        move.w  #167,d0
        move.w  $2a(a6),d3              ; away goals
        bsr.w   l92_draw_num
.m_row_end:
        movem.l (sp)+,d2-d3
        addq.w  #1,d4
        bra.w   .m_lp

.m_none:
        lea     l92_str_nomatch(pc),a3
        move.w  #100,d0
        moveq   #84,d1
        move.w  l92_hl_col(pc),d2
        bsr.w   l92_draw_str
.m_done:
        movem.l (sp)+,d0-d6/a0-a3/a5-a6
        rts

; ---------------------------------------------------------------------------
; Compact Native-Styled UI Drawing Helpers (all use fast_draw_str!)
; ---------------------------------------------------------------------------
; l92_fill_rect(d0=x1, d1=y1, d2=x2, d3=y2, d4=col) — preserves all regs
l92_fill_rect:
        movem.l d0-d4/a0-a2,-(sp)
        move.w  d0,-(sp)
        move.w  d1,-(sp)
        move.w  d4,d0
        jsr     $0175fa.l               ; set Line-A colour (clobbers d0/d1)
        movea.l -$7656(a4),a0
        clr.w   $24(a0)                 ; WRT_MODE = 0 (Replace)
        move.w  (sp)+,$28(a0)           ; y1
        move.w  (sp)+,$26(a0)           ; x1
        move.w  d2,$2a(a0)              ; x2
        move.w  d3,$2c(a0)              ; y2
        dc.w    $a005                   ; Line-A filled rect
        movem.l (sp)+,d0-d4/a0-a2
        rts

; l92_draw_banner(a3=title, d1=y1, d3=y2) — centered native blue banner + yellow text
l92_draw_banner:
        movem.l d0-d4/a0/a3,-(sp)
        ; Outer white border (x=28..291)
        moveq   #28,d0
        move.w  #291,d2
        moveq   #15,d4
        bsr.s   l92_fill_rect
        ; Inner royal-blue fill (matches Division 1..4 & Done buttons!)
        addq.w  #1,d0
        addq.w  #1,d1
        subq.w  #1,d2
        subq.w  #1,d3
        move.w  l92_btn_col(pc),d4
        bsr.s   l92_fill_rect
        ; Center title string horizontally (6px per char)
        movea.l a3,a0
        moveq   #0,d0
.bn_ln: tst.b   (a0)+
        beq.s   .bn_ok
        addq.w  #6,d0
        bra.s   .bn_ln
.bn_ok:
        neg.w   d0
        addi.w  #320,d0
        asr.w   #1,d0                   ; x = (320 - len*6) / 2
        add.w   d3,d1
        subq.w  #6,d1
        asr.w   #1,d1                   ; vertically centered
        ; Drop shadow (col 0) at (x+1, y+1) then bright yellow text at (x, y)
        addq.w  #1,d0
        addq.w  #1,d1
        moveq   #0,d2
        bsr.s   l92_draw_str
        subq.w  #1,d0
        subq.w  #1,d1
        move.w  l92_hl_col(pc),d2
        bsr.s   l92_draw_str
        movem.l (sp)+,d0-d4/a0/a3
        rts

; l92_draw_str(d0=x, d1=y, d2=col, a3=str) — preserves all regs
l92_draw_str:
        movem.l d0-d2/a0,-(sp)
        clr.w   -$764e(a4)              ; font 0 (6x6)
        clr.w   -$764c(a4)              ; STYLE = 0 (always hits fast_draw_str!)
        movea.l -$7656(a4),a0
        move.w  #1,$24(a0)              ; WRT_MODE = 1 (Transparent)
        move.w  d2,$6a(a0)              ; TEXT_FG = col
        jsr     $017a38.l               ; fast_draw_str!
        movem.l (sp)+,d0-d2/a0
        rts

; l92_draw_num(d0=x, d1=y, d2=col, d3=val) — preserves all regs
l92_draw_num:
        movem.l d0/a2-a3,-(sp)
        move.w  d0,-(sp)
        move.w  d3,d0
        lea     -$313a(a4),a2
        jsr     -$7f86(a4)              ; itoa(d0) -> -$313a(a4)
        movea.l a2,a3
        move.w  (sp)+,d0
        bsr.s   l92_draw_str
        movem.l (sp)+,d0/a2-a3
        rts

l92_view_mode:  dc.w    0
l92_hl_col:     dc.w    15
l92_btn_col:    dc.w    7
l92_cur_cnt:    dc.w    24
l92_stat_offs:  dc.b    $18,$1a,$1c,$ff,$20,$22,$1e,0
l92_str_divtbl: dc.b    "Division Tables",0
l92_str_tblhdr: dc.b    "POS CLUB                 P   W   D   L  GF  GA  PTS",0
l92_str_div_sfx: dc.b   " - Div X",0
l92_str_v:      dc.b    "v",0
l92_str_dash:   dc.b    "-",0
l92_str_nomatch: dc.b   "No matches this week",0
                even

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
