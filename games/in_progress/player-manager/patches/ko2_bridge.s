; ---------------------------------------------------------------------------
; Task 2 (Milestone 2B): Kick Off 2 Match Engine Overlay Bridge (1 MB RAM!)
;
; Replaces PM's live match path ($018ebe..$018f10) with the genuine Kick Off 2
; match engine running natively at $010000 (zero relocation!).
; AI-vs-AI quick sim ($018f12) stays 100% untouched.
;
; 1 MB RAM Layout during a match:
;   $0b3000..$0b4fff : resident patches (micro_opt + league92 + ko2_bridge)
;   $0b5000..$0b51ff : bridge state + 26 compact player results
;   $0b5200..$0b561f : Home team KO2 $41e struct
;   $0b5620..$0b5a3f : Away team KO2 $41e struct
;   $0b5a40..$0b628f : Saved PM $6800..$7050 PP PRD handler
;   $0b6290..$0b6a9f : Loaded KO2 $6800..$7020 PP KRD handler (KO2HND.BIN)
;   $0b6b00..$0bf97f : Saved PM management code ($010000..$018e80, 36 KB)
;   $0bf980..$0c82ff : Saved PM data+bss ($02169c..$02a000, 35 KB)
;   (Ends at $c8300 — 15 KB below VDI/screen at $cc000!)
; ---------------------------------------------------------------------------

BR_STATE        equ     $0b5800
BR_HOME_SC      equ     $0b5800         ; .w
BR_AWAY_SC      equ     $0b5802         ; .w
BR_HOME_HUM     equ     $0b5804         ; .w
BR_AWAY_HUM     equ     $0b5806         ; .w
BR_FAST         equ     $0b5808         ; .w (0=Normal 5m, 1=Fast 3m)
BR_CUP_ET       equ     $0b580a         ; .w (0=League, 1=Cup Extra Time)
BR_PM_A4        equ     $0b580c         ; .l
BR_PM_84        equ     $0b5810         ; .l
BR_TOS_84       equ     $0b5814         ; .l
BR_KICK_DIR     equ     $0b5818         ; .w (bit0=up/down, bit1=kickoff team)
BR_WEEK_SEED    equ     $0b581a         ; .w (week number for ref/weather variety)
BR_SAV_70       equ     $0b581c         ; .l saved $70.w VBL
BR_SAV_118      equ     $0b5820         ; .l saved $118.w IKBD
BR_KBDVBASE     equ     $0b5824         ; .l saved Kbdvbase()
BR_SAV_MVEC     equ     $0b5828         ; .l saved Kbdvbase+$10 (mousevec)
BR_SAV_JVEC     equ     $0b582c         ; .l saved Kbdvbase+$18 (joyvec)
BR_OLD_SSP      equ     $0b5830         ; .l saved old SSP across .rs_d!
BR_OLD_SR       equ     $0b5834         ; .w saved old SR across .rs_d!
BR_LINEA_BASE   equ     $0b5838         ; .l saved Line-A base ptr from $a000!
BR_RESULTS      equ     $0b5840         ; 26 x 10 bytes = 260 bytes ($0b5840..$0b5943)
BR_LINEA_SAVE   equ     $0b5950         ; 8 bytes ($2e..$35 of Line-A vars)
BR_MFP_SAVE     equ     $0b5960         ; 24 bytes: $110,$114,$120,$134 + IERA/IERB/IMRA/IMRB
BR_IS_STE       equ     $0b5978         ; .w: 1 = Atari STE/Mega STE detected, 0 = plain ST
BR_SAV_A0       equ     $0b597c         ; .l: saved $a0.w (TRAP #8) vector for STE Blitter call

KO2_STE_BASE    equ     $0ae940         ; $0ae940..$0b2ff7 (17.7 KB) for KO2STE.BIN (above FILES.CR $09d000..$0ae940!)
KO2_STE_SND_STG equ     $0c8b00         ; temporary staging in KO2_REPLAY_BUF ($6014 = 24.6 KB) before $01564c!

KO2_HOME_TEAM   equ     $0b5a00         ; $41e bytes
KO2_AWAY_TEAM   equ     $0b5e20         ; $41e bytes
PM_HND_SAVE     equ     $0b6240         ; $850 bytes
KO2_HND_BUF     equ     $0b6a90         ; $820 bytes
PM_CODE_SAVE    equ     $0b7300         ; $8e80 bytes ($010000..$018e80)
PM_DATA_SAVE    equ     $0c0180         ; $8964 bytes ($02169c..$02a000 -> $0c8ae4)
KO2_REPLAY_BUF  equ     $0c8b00         ; $6014 bytes ($0c8b00..$0ceb14 < $0d0000!)
KO2_FILES_CR    equ     $09d000         ; $11940 bytes ($09d000..$0ae940 < KO2_STE_BASE $0ae940!)

KO2_A4          equ     $0284aa

; Called from boot_entry; returns d0=0 ok, d0!=0 fail
init_ko2_bridge:
        cmpi.l  #$2f3c0001,$01d042.l    ; Malloc($1d4c0)
        bne.s   .k2_fail
        cmpi.w  #$d4c0,$01d046.l
        bne.s   .k2_fail
        cmpi.l  #$396cd28a,$018ebe.l    ; move.w -$2d76(a4),-$192c(a4)
        bne.s   .k2_fail

        ; 1. Shrink PM's boot match Malloc from $1d4c0 (120KB) -> $2800 (10KB)
        ;    Only allocates the two 13-player structs for AI-vs-AI quick sim,
        ;    freeing 110 KB of TOS heap for KO2's 139 KB match buffers in 1 MB RAM!
        move.w  #$4ef9,$01d042.l
        move.l  #pm_slim_match_init,$01d044.l

        ; 2. Hook PM's live human match path ($018ebe) -> ko2_bridge_match
        move.w  #$4ef9,$018ebe.l
        move.l  #ko2_bridge_match,$018ec0.l

        moveq   #0,d0
        rts
.k2_fail:
        moveq   #1,d0
        rts

; Replaces $01d042..$01d086: allocate 10 KB for AI-vs-AI quick sim structs only
pm_slim_match_init:
        move.l  #$2800,-(sp)
        move.w  #$48,-(sp)
        trap    #1
        addq.l  #6,sp
        tst.l   d0
        ble.s   .oom
        movea.l d0,a5
        move.l  d0,-$192a(a4)
        jsr     -$7f32(a4)              ; $020e68: sets -$3d6a(a4) and -$3d26(a4)!
        rts
.oom:
        jmp     -$7f38(a4)

; ---------------------------------------------------------------------------
; Main Bridge: entered at $018ebe in User mode with PM's a4 = $02969a
; ---------------------------------------------------------------------------
ko2_bridge_match:
        ; Save PM state & flags
        move.l  a4,BR_PM_A4.l
        movea.l -$1eec(a4),a0           ; PM home team
        movea.l -$1ee8(a4),a1           ; PM away team
        move.w  $28(a0),BR_HOME_HUM.l
        move.w  $28(a1),BR_AWAY_HUM.l
        move.w  -$2d76(a4),BR_FAST.l    ; 0=Normal (5m), 1=Fast (3m)
        move.w  -$1766(a4),BR_CUP_ET.l  ; 0=League, 1=Cup Extra Time (from d0!)
        move.w  -$1ee4(a4),BR_KICK_DIR.l ; bit0=up/down, bit1=kickoff (from d1!)
        move.w  -$336c(a4),BR_WEEK_SEED.l ; current week for referee variety

        ; Pick non-clashing club kit colours from team names (KO2 palette indices)
        ; Palette: 1=Blue, 4=White, 9=DarkRed, 10=Red, 11=Orange, 12=Yellow, 15=Purple
        moveq   #0,d2
        move.b  (a0),d2
        add.b   2(a0),d2
        andi.w  #7,d2
        lea     kit_palette_tbl(pc),a3
        move.b  0(a3,d2.w),d0           ; home shirt colour
        ext.w   d0
        moveq   #0,d3
        move.b  (a1),d3
        add.b   2(a1),d3
        andi.w  #7,d3
        move.b  0(a3,d3.w),d4           ; away shirt colour
        ext.w   d4
        cmp.w   d0,d4
        bne.s   .no_clash
        addq.w  #3,d3
        andi.w  #7,d3
        move.b  0(a3,d3.w),d4
        ext.w   d4
.no_clash:
        ; Pack Home & Away teams into KO2 $41e structs
        lea     KO2_HOME_TEAM.l,a2
        moveq   #1,d1                   ; kit style 1 (matches KO2 preloaded sprites!)
        bsr.w   pack_pm_to_ko2_team
        movea.l -$1ee8(a4),a0
        lea     KO2_AWAY_TEAM.l,a2
        move.w  d4,d0                   ; away shirt colour
        moveq   #3,d1                   ; kit style 3 (matches KO2 preloaded sprites!)
        bsr.w   pack_pm_to_ko2_team

        ; Load KO2HND.BIN ($820 bytes) into KO2_HND_BUF via PP HD mode
        jsr     $006946.w               ; PP HD mode
        lea     ko2_hnd_fname(pc),a0
        lea     KO2_HND_BUF.l,a1
        move.l  #$820,d0
        bsr.w   load_hd_file
        tst.l   d0
        ble.w   .abort_restore_prd

        ; Save PM management code ($010000..$018e80 -> PM_CODE_SAVE)
        lea     $010000.l,a0
        lea     PM_CODE_SAVE.l,a1
        move.w  #($8e80/4-1),d0
.sv_c:  move.l  (a0)+,(a1)+
        dbra    d0,.sv_c

        ; Save PM data+bss ($02169c..$02a000 -> PM_DATA_SAVE)
        lea     $02169c.l,a0
        lea     PM_DATA_SAVE.l,a1
        move.w  #($8964/4-1),d0
.sv_d:  move.l  (a0)+,(a1)+
        dbra    d0,.sv_d

        ; Load KO2ENG.BIN ($14000 bytes) directly into $010000!
        lea     ko2_eng_fname(pc),a0
        lea     $010000.l,a1
        move.l  #$14000,d0
        bsr.w   load_hd_file
        move.l  d0,-(sp)
        ; Also preload KO2STE.BIN into $0ae940 and AMIGASND.BIN into KO2_REPLAY_BUF staging ($0c8b00)
        clr.w   KO2_STE_BASE.l          ; clear header magic so missing KO2STE.BIN falls back cleanly!
        lea     ko2_ste_fname(pc),a0
        lea     KO2_STE_BASE.l,a1
        move.l  #$19c0,d0               ; max 6,592 bytes ($0ae940..$0b02ff)
        bsr.w   load_hd_file
        tst.l   d0
        ble.s   .no_ste_bin
        lea     amigasnd_fname(pc),a0
        lea     KO2_STE_SND_STG.l,a1
        move.l  #$5c00,d0
        bsr.w   load_hd_file
        move.l  d0,KO2_STE_BASE+8.l     ; store AMIGASND.BIN byte size in STE_SND_SIZE!
.no_ste_bin:
        jsr     $006942.w               ; restore PP PRD mode (before swap)
        move.l  (sp)+,d0
        tst.l   d0
        ble.w   .restore_pm_only

        ; Zero KO2 BSS ($024000..$028500)
        lea     $024000.l,a0
        move.w  #($4500/4-1),d0
.clr_b: clr.l   (a0)+
        dbra    d0,.clr_b

        ; Route KO2's $014c80 FILES.CR ($11940 = 72 KB) to KO2_FILES_CR ($09d000..$0ae940)
        ; using the upper tail of HAGA's 200 KB cache buffer (shrunk to $1c000 = 114 KB)!
        move.w  #$4ef9,$014c80.l
        move.l  #ko2_files_alloc,$014c82.l
        ; Route KO2's $01564c replay buffer ($6014) to static KO2_REPLAY_BUF (1 MB RAM!)
        move.w  #$4ef9,$01564c.l
        move.l  #ko2_replay_alloc,$01564e.l
        ; Also route KO2's $01adb8 temporary $2c00 sprite-depack scratch buffer to KO2_REPLAY_BUF
        ; (used only during $015f4c before replay init, and skip its Mfree at $01ae1a!)
        move.w  #$2c7c,$01adb8.l        ; movea.l #KO2_REPLAY_BUF,a6
        move.l  #KO2_REPLAY_BUF,$01adba.l
        move.w  #$6010,$01adbe.l        ; bra.s $01add0
        move.w  #$6006,$01ae1a.l        ; bra.s $01ae22 (skip Mfree(a6))
        ; Also route KO2's $01ffb8 temporary $1600 depack scratch buffer to KO2_REPLAY_BUF!
        move.w  #$2c7c,$01ffb8.l        ; movea.l #KO2_REPLAY_BUF,a6
        move.l  #KO2_REPLAY_BUF,$01ffba.l
        move.w  #$6010,$01ffbe.l        ; bra.s $01ffd0
        move.w  #$6006,$01fffa.l        ; bra.s $020002 (skip Mfree(a6))
        ; Route KO2's $010a2e ($20f0 = 8.4 KB) Malloc to static $0b0300..$0b23f0 (prevents Week 2+ 1 MB OOM!)
        move.w  #$297c,$010a2e.l        ; move.l #$000b0300,-$4450(a4)
        move.l  #$000b0300,$010a30.l
        move.w  #$bbb0,$010a34.l        ; -$4450
        move.w  #$600a,$010a36.l        ; bra.s $010a42 (skip Malloc + beq $1189a)
        ; Skip KO2's $100000 dummy floppy spin-up delay at $01aaee (instant KRD load!)
        move.l  #1,$01aaf0.l
        ; Disable KO2's standalone Esc match-abort key ($01b64c: bra.w $1b75e -> bra.w $1b556)!
        move.l  #$6000ff08,$01b64c.l

        ; Save Kbdvbase() mousevec/joyvec BEFORE KO2's $01fd92 installs its own!
        move.w  #$22,-(sp)              ; XBIOS Kbdvbase()
        trap    #14
        addq.l  #2,sp
        movea.l d0,a0
        move.l  a0,BR_KBDVBASE.l
        move.l  $10(a0),BR_SAV_MVEC.l
        move.l  $18(a0),BR_SAV_JVEC.l

        ; Enter Supervisor briefly to swap $6800 handler + $84.w vector
        clr.l   -(sp)
        move.w  #$20,-(sp)
        trap    #1
        addq.l  #6,sp
        move.l  d0,-(sp)                ; save old SSP

        move.l  $70.w,BR_SAV_70.l
        move.l  $118.w,BR_SAV_118.l
        move.l  $a0.w,BR_SAV_A0.l
        lea     BR_MFP_SAVE.l,a0
        move.l  $110.w,(a0)+            ; Timer D
        move.l  $114.w,(a0)+            ; Timer C (KO2 hooks this at $018602!)
        move.l  $120.w,(a0)+            ; Timer B (HBL raster stripes!)
        move.l  $134.w,(a0)+            ; Timer A
        move.b  $00fffa07.l,(a0)+       ; IERA
        move.b  $00fffa09.l,(a0)+       ; IERB
        move.b  $00fffa13.l,(a0)+       ; IMRA
        move.b  $00fffa15.l,(a0)+       ; IMRB
        move.l  $84.w,BR_PM_84.l
        move.l  $69a0.w,BR_TOS_84.l     ; original TOS TRAP #1 saved by PMLA!
        ; Save PM $6800..$7050
        lea     $6800.w,a0
        lea     PM_HND_SAVE.l,a1
        move.w  #($850/4-1),d0
.sv_h:  move.l  (a0)+,(a1)+
        dbra    d0,.sv_h
        ; Install KO2 $6800..$7020 handler & patch dynamic HAGA/TOS pointers
        lea     KO2_HND_BUF.l,a0
        lea     $6800.w,a1
        move.w  #($820/4-1),d0
.ld_h:  move.l  (a0)+,(a1)+
        dbra    d0,.ld_h
        move.l  $608.w,$6cb8.w
        move.l  #$0001c000,$6c6e.w      ; 114 KB KRD cache ($81000..$9d000), leaving $9d000..$ae940 for FILES.CR!
        clr.w   $6c68.w                 ; force chunked cache mode
        move.l  $60c.w,$6c6a.w
        move.l  #-1,$6c72.w             ; invalidate KRD cache so $81000 reloads KRD!
        ; Fix PP's uncached Fread ($6ba0) which forgot to add Fseek offset $6c64.w to d4!
        move.w  #$4ef9,$6ba0.w
        move.l  #ko2_uncached_fix,$6ba2.w
        move.w  #$4e71,$6ba6.w
        move.l  BR_TOS_84.l,$6916.w
        move.l  #$000068c8,$84.w        ; KO2 TRAP #1 handler!

        ; Detect Atari STE (DMA Sound $ff8901 + Blitter $ff8a3c) via Bus Error probe
        clr.w   BR_IS_STE.l
        move.w  sr,d3
        move.w  #$2700,sr
        move.l  $8.w,a2
        move.l  sp,a3
        lea     .not_ste(pc),a0
        move.l  a0,$8.w
        tst.b   $00ff8901.l             ; STE DMA sound control (Bus Error on plain ST)
        tst.b   $00ff8a3c.l             ; STE Blitter control
        move.w  #1,BR_IS_STE.l
.not_ste:
        move.l  a3,sp
        move.l  a2,$8.w
        move.w  d3,sr

        ; Return to User mode
        move.w  #$20,-(sp)
        trap    #1
        addq.l  #6,sp

        ; If Atari STE detected AND KO2STE.BIN loaded cleanly (header $6000 = bra.w),
        ; install STE Amiga Audio & Visuals hooks into KO2ENG!
        tst.w   BR_IS_STE.l
        beq.s   .skip_ste_init
        cmpi.w  #$6000,KO2_STE_BASE.l
        beq.s   .do_ste_init
        clr.w   BR_IS_STE.l             ; KO2STE.BIN missing -> graceful Classic ST fallback!
        bra.s   .skip_ste_init
.do_ste_init:
        jsr     KO2_STE_BASE.l          ; ste_install_hooks
.skip_ste_init:

        ; Save Line-A base & fill pattern (PATPTR $2e(a0), PATMSK $32(a0), MFILL $34(a0))!
        dc.w    $a000                   ; Line-A init -> a0 = Line-A base
        move.l  a0,BR_LINEA_BASE.l
        move.l  $2e(a0),BR_LINEA_SAVE.l
        move.l  $32(a0),BR_LINEA_SAVE+4.l

        ; --- Run Kick Off 2 natively at $010000 with a4 = $0284aa ---
        lea     KO2_A4.l,a4
        jsr     $01fd92.l               ; KO2 system/screen/IKBD init
        jsr     $014c6a.l               ; KO2 load FILES.CR (tactics/fonts/data -> $09d000)
        jsr     $015f4c.l               ; KO2 Malloc($1c138) + KRD sprites + replay buf ($0c8b00)
        jsr     $014e54.l               ; KO2 string/name table init
        jsr     $010044.l               ; KO2 default match options

        ; Configure KO2 match options BEFORE $013450:
        move.w  BR_CUP_ET.l,-$34ca(a4)  ; Extra time if cup tie
        move.w  #4,-$34d0(a4)           ; Pitch type = 4 (random: normal/wet/soggy/artificial!)
        clr.w   -$34c4(a4)              ; Game speed = 0 (FULL 50 FPS! 1=25fps slow mode!)
        moveq   #1,d0                   ; Default 5-min half (PM NORMAL)
        tst.w   BR_FAST.l
        beq.s   .len_ok
        moveq   #0,d0                   ; 3-min half (PM FAST)
.len_ok:
        move.w  d0,-$34ce(a4)
        move.w  BR_WEEK_SEED.l,d0
        andi.w  #7,d0
        move.w  d0,-$34cc(a4)           ; Referee variety across weeks
        jsr     $013450.l               ; apply pitch/ref/half-length/aftertouch/ET

        ; On Atari STE: now that KRD loading is finished ($081000..$09d000 is 100% free!)
        ; and pitch condition -$4eee(a4) (0..3) is chosen, load AMIGAP0..3.BIN via proven PM HD mode!
        tst.w   BR_IS_STE.l
        beq.w   .skip_ste_pit
        ; Patch '0'..'3' in "AMIGAP0.BIN"
        move.w  -$4eee(a4),d0
        andi.w  #3,d0
        addi.b  #'0',d0
        lea     amigapit_fname(pc),a0
        move.b  d0,6(a0)
        ; Briefly swap PM_HND ($6800 + $84.w) in to load AMIGAPx.BIN via proven load_hd_file!
        pea     .swap_to_pm_hnd(pc)
        move.w  #$26,-(sp)
        trap    #14
        addq.l  #6,sp
        jsr     $006946.w               ; PP HD mode ON
        lea     amigapit_fname(pc),a0
        lea     $081000.l,a1            ; STE_PIT_PAL ($081000..$088e1f)
        move.l  #32288,d0
        bsr.w   load_hd_file
        move.l  d0,-(sp)                ; save bytes read
        jsr     $006942.w               ; PP PRD mode restored
        pea     .swap_to_ko2_hnd(pc)
        move.w  #$26,-(sp)
        trap    #14
        addq.l  #6,sp
        move.l  (sp)+,d0                ; bytes read (32288 = ok!)
        jsr     KO2_STE_BASE+12.l       ; ste_init_pitch(d0 = bytes_read)
        bra.s   .skip_ste_pit

.swap_to_pm_hnd:
        lea     PM_HND_SAVE.l,a0
        lea     $6800.w,a1
        move.w  #($850/4-1),d0
.sp1:   move.l  (a0)+,(a1)+
        dbra    d0,.sp1
        move.l  BR_PM_84.l,$84.w
        rts

.swap_to_ko2_hnd:
        lea     KO2_HND_BUF.l,a0
        lea     $6800.w,a1
        move.w  #($820/4-1),d0
.sk1:   move.l  (a0)+,(a1)+
        dbra    d0,.sk1
        move.l  #$000068c8,$84.w
        rts
.skip_ste_pit:

        ; Configure Home/Away controller & kickoff direction AFTER $013450
        clr.l   -$4f62(a4)
        clr.l   -$4f5e(a4)
        tst.w   BR_HOME_HUM.l
        beq.s   .away_hum
        lea     -$df0(a4),a2            ; Joystick 1 for Home
        move.l  a2,-$4f62(a4)
        bra.s   .ctrl_ok
.away_hum:
        lea     -$df0(a4),a2            ; Joystick 1 for Away
        move.l  a2,-$4f5e(a4)
.ctrl_ok:
        move.w  BR_KICK_DIR.l,d0
        move.w  d0,d1
        andi.w  #1,d1
        move.w  d1,-$4f50(a4)           ; Up Pitch (0) / Down Pitch (1)
        lsr.w   #1,d0
        andi.w  #1,d0
        move.w  d0,-$4f52(a4)           ; Kickoff team (0=Home, 1=Away)
        clr.l   -$4f4e(a4)
        lea     KO2_HOME_TEAM.l,a0
        lea     KO2_AWAY_TEAM.l,a1
        jsr     $0131b2.l               ; apply tactics
        lea     KO2_HOME_TEAM.l,a0
        lea     KO2_AWAY_TEAM.l,a1
        jsr     $0160c8.l               ; === PLAY KICK OFF 2 MATCH! ===

        ; Save scores & 13+13 player results from KO2 structs
        move.w  d0,BR_HOME_SC.l
        move.w  d1,BR_AWAY_SC.l
        lea     BR_RESULTS.l,a2
        movea.l -$5012(a4),a0           ; KO2 home 13 players (stride $186)
        bsr.w   extract_ko2_results
        movea.l -$4fbc(a4),a0           ; KO2 away 13 players (stride $186)
        bsr.w   extract_ko2_results

        ; Free KO2's $1c138 Malloc block -> zero memory leak!
        move.l  -$1170(a4),d0
        beq.s   .f_done
        move.l  d0,-(sp)
        move.w  #$49,-(sp)
        trap    #1
        addq.l  #6,sp
.f_done:

        ; 1. Restore PM's $6800 handler, $84.w, VBL/IKBD/Kbdvbase vectors, and Line-A PATPTR
        clr.l   -(sp)
        move.w  #$20,-(sp)
        trap    #1
        addq.l  #6,sp
        move.l  d0,BR_OLD_SSP.l

        move.w  sr,BR_OLD_SR.l
        move.w  #$2700,sr
        tst.w   BR_IS_STE.l
        beq.s   .skip_ste_clean
        jsr     KO2_STE_BASE+4.l        ; ste_cleanup (stop STE DMA + reset STE shifter)
.skip_ste_clean:
        move.l  BR_SAV_70.l,$70.w
        move.l  BR_SAV_118.l,$118.w
        move.l  BR_SAV_A0.l,$a0.w
        lea     BR_MFP_SAVE.l,a0
        move.l  (a0)+,$110.w            ; restore Timer D
        move.l  (a0)+,$114.w            ; restore Timer C (unhook KO2 $018602!)
        move.l  (a0)+,$120.w            ; restore Timer B
        move.l  (a0)+,$134.w            ; restore Timer A
        move.b  (a0)+,$00fffa07.l       ; IERA
        move.b  (a0)+,$00fffa09.l       ; IERB
        move.b  (a0)+,$00fffa13.l       ; IMRA
        move.b  (a0)+,$00fffa15.l       ; IMRB
        clr.b   $00fffa0f.l             ; clear pending ISRA
        clr.b   $00fffa11.l             ; clear pending ISRB
        movea.l BR_KBDVBASE.l,a0
        move.l  BR_SAV_MVEC.l,$10(a0)
        move.l  BR_SAV_JVEC.l,$18(a0)
        lea     PM_HND_SAVE.l,a0
        lea     $6800.w,a1
        move.w  #($850/4-1),d0
.rs_h:  move.l  (a0)+,(a1)+
        dbra    d0,.rs_h
        clr.b   $612f.w                 ; invalidate PM PRD cache (KO2 used $81000 for KRD!)
        move.l  BR_PM_84.l,$84.w
        movea.l BR_LINEA_BASE.l,a0
        move.l  BR_LINEA_SAVE.l,$2e(a0)
        move.l  BR_LINEA_SAVE+4.l,$32(a0)
        move.w  BR_OLD_SR.l,sr

        move.l  BR_OLD_SSP.l,-(sp)
        move.w  #$20,-(sp)
        trap    #1
        addq.l  #6,sp

.restore_pm_only:
        ; 2. Reload PM's $018e80..$02169c FIRST (before restoring PM_CODE/PM_DATA!)
        jsr     $006946.w               ; PP HD mode
        lea     pm_match_fname(pc),a0
        lea     $018e80.l,a1
        move.l  #$881c,d0
        bsr.w   load_hd_file
        jsr     $006942.w               ; restore PP PRD mode
        ; Re-install our 6-byte live match hook at $018ebe
        move.w  #$4ef9,$018ebe.l
        move.l  #ko2_bridge_match,$018ec0.l

        ; 3. Restore PM management code ($010000..$018e80) & data+bss ($02169c..$02a000)
        lea     PM_CODE_SAVE.l,a0
        lea     $010000.l,a1
        move.w  #($8e80/4-1),d0
.rs_c:  move.l  (a0)+,(a1)+
        dbra    d0,.rs_c
        lea     PM_DATA_SAVE.l,a0
        lea     $02169c.l,a1
        move.w  #($8964/4-1),d0
.rs_d:  move.l  (a0)+,(a1)+
        dbra    d0,.rs_d

        movea.l BR_PM_A4.l,a4

        ; Write scores & 13+13 player results back into PM's structs & commit via $018f5e!
        move.w  BR_HOME_SC.l,-$3ce2(a4)
        move.w  BR_AWAY_SC.l,-$3ce0(a4)
        lea     BR_RESULTS.l,a2
        movea.l -$3d6a(a4),a0           ; PM home 13 players (stride $182)
        bsr.w   inject_pm_results
        movea.l -$3d26(a4),a0           ; PM away 13 players (stride $182)
        bsr.w   inject_pm_results
        jsr     $018f5e.l               ; commit goals/cards/injuries/played to 2600-player pool!

        ; Restore IKBD mouse handler & enable mouse reporting (just like PM $018ef8)
        pea     $01b77e.l
        move.w  #$26,-(sp)              ; Supexec
        trap    #14
        addq.l  #6,sp

        ; Return d0 = home score, d1 = away score to $0166cc
        move.w  -$3ce2(a4),d0
        move.w  -$3ce0(a4),d1
        movem.l (sp)+,d2-d7/a0-a6
        rts

.abort_restore_prd:
        jsr     $006942.w
        moveq   #0,d0
        moveq   #0,d1
        movem.l (sp)+,d2-d7/a0-a6
        rts

; ---------------------------------------------------------------------------
; Helper: load_hd_file(a0=filename, a1=dest, d0.l=maxlen) -> d0.l bytes read
; ---------------------------------------------------------------------------
load_hd_file:
        movem.l d1-d3/a1-a2,-(sp)
        move.l  d0,d3
        movea.l a1,a2
        move.w  #0,-(sp)
        move.l  a0,-(sp)
        move.w  #$3d,-(sp)              ; Fopen
        trap    #1
        addq.l  #8,sp
        tst.w   d0
        bmi.s   .lf_err
        move.w  d0,d2                   ; handle
        move.l  a2,-(sp)
        move.l  d3,-(sp)
        move.w  d2,-(sp)
        move.w  #$3f,-(sp)              ; Fread
        trap    #1
        adda.l  #12,sp
        move.l  d0,d3
        move.w  d2,-(sp)
        move.w  #$3e,-(sp)              ; Fclose
        trap    #1
        addq.l  #4,sp
        move.l  d3,d0
        movem.l (sp)+,d1-d3/a1-a2
        rts
.lf_err:
        moveq   #-1,d0
        movem.l (sp)+,d1-d3/a1-a2
        rts

; ---------------------------------------------------------------------------
; Helper: pack_pm_to_ko2_team(a0=PM team, a2=KO2 $41e dst, d0.w=shirt, d1.w=style)
; Copies team name + up to 24 players (remapping shirt 13 -> 14 for KO2!)
; ---------------------------------------------------------------------------
pack_pm_to_ko2_team:
        movem.l d0-d7/a0-a3/a5-a6,-(sp)
        move.w  d0,d6                   ; shirt colour index
        move.w  d1,-(sp)                ; save kit style on stack
        ; Clear $41e bytes
        movea.l a2,a3
        move.w  #($41e/2-1),d1
.clr:   clr.w   (a3)+
        dbra    d1,.clr
        ; Copy 20-byte team name
        movea.l a0,a5
        movea.l a2,a3
        moveq   #19,d1
.cnm:   move.b  (a5)+,(a3)+
        dbra    d1,.cnm
        ; Copy squad players from $2c(a0) (25 word indices)
        lea     $2c(a0),a5
        lea     $16(a2),a3              ; dst player array
        moveq   #0,d5                   ; count copied (max 24)
        moveq   #0,d4                   ; bitmask of shirt numbers 1..14 seen
.pl_lp:
        cmpi.w  #24,d5
        bge.s   .pl_done
        move.w  (a5)+,d0
        bmi.s   .pl_done
        mulu.w  #$2a,d0
        add.l   -$2e80(a4),d0
        movea.l d0,a6                   ; src 42-byte PM player
        movea.l a3,a1
        moveq   #41,d1
.cp42:  move.b  (a6)+,(a1)+
        dbra    d1,.cp42
        ; Remap shirt 13 -> 14 for KO2's $015d0c (which looks for 1..12, 14!)
        move.b  $15(a3),d0
        move.b  d0,d1
        andi.w  #$f,d1
        cmpi.w  #13,d1
        bne.s   .sh_ok
        andi.b  #$f0,d0
        ori.b   #14,d0
        move.b  d0,$15(a3)
        moveq   #14,d1
.sh_ok:
        bset    d1,d4
        adda.l  #$2a,a3
        addq.w  #1,d5
        bra.s   .pl_lp
.pl_done:
        move.w  d5,$14(a2)              ; squad count
        ; Ensure shirts 1..12 & 14 all exist (fallback: assign unnumbered players)
        lea     $16(a2),a3
        moveq   #1,d7
.chk_sh:
        cmpi.w  #13,d7
        bne.s   .chk_bit
        moveq   #14,d7
.chk_bit:
        btst    d7,d4
        bne.s   .nxt_sh
        ; Find first player with ($15 & $f) == 0 and assign d7
        movea.l a3,a1
        move.w  d5,d2
        subq.w  #1,d2
        bmi.s   .nxt_sh
.f0:    move.b  $15(a1),d0
        andi.b  #$f,d0
        beq.s   .asg
        adda.l  #$2a,a1
        dbra    d2,.f0
        bra.s   .nxt_sh
.asg:   or.b    d7,$15(a1)
        bset    d7,d4
.nxt_sh:
        addq.w  #1,d7
        cmpi.w  #14,d7
        ble.s   .chk_sh

        ; Set KO2 tactics [0,1,2,3], active=0, kit style=(sp)+, shirt=d6, shorts=4 (white)
        lea     $406(a2),a3
        move.l  #0,(a3)+
        move.l  #1,(a3)+
        move.l  #2,(a3)+
        move.l  #3,(a3)+
        clr.w   $416(a2)
        move.w  (sp)+,$418(a2)          ; kit style (1 or 3)
        move.w  d6,$41a(a2)             ; shirt colour index
        move.w  #4,$41c(a2)             ; shorts: white ($777)
        movem.l (sp)+,d0-d7/a0-a3/a5-a6
        rts

; ---------------------------------------------------------------------------
; Extract 13 KO2 player results (stride $186) -> 13 x 10 bytes at (a2)+
; ---------------------------------------------------------------------------
extract_ko2_results:
        moveq   #12,d7
.ex_lp:
        move.w  $14(a0),d0              ; shirt 0..13 (remap 13 -> 12 for PM!)
        cmpi.w  #13,d0
        bne.s   .sh_ok
        moveq   #12,d0
.sh_ok:
        move.w  d0,(a2)+
        move.w  $34(a0),(a2)+           ; played
        move.w  $a0(a0),(a2)+           ; cards
        move.w  $a8(a0),(a2)+           ; goals
        move.w  $aa(a0),(a2)+           ; injury
        adda.l  #$186,a0
        dbra    d7,.ex_lp
        rts

; Inject 13 x 10 bytes at (a2)+ -> PM 13 player structs (stride $182)
inject_pm_results:
        moveq   #12,d7
.in_lp:
        move.w  (a2)+,$14(a0)
        move.w  (a2)+,$34(a0)
        move.w  (a2)+,$a0(a0)
        move.w  (a2)+,$a8(a0)
        move.w  (a2)+,$aa(a0)
        adda.l  #$182,a0
        dbra    d7,.in_lp
        rts

ko2_uncached_fix:
        add.l   $6c64.w,d4              ; include Fseek file position!
        move.l  d4,$4(a0)
        move.l  d1,$8(a0)
        jmp     $006ba8.w

ko2_files_alloc:
        move.l  #KO2_FILES_CR,-$327e(a4)
        jmp     $014c96.l

ko2_replay_alloc:
        move.l  #KO2_REPLAY_BUF,-$2b8a(a4)
        jmp     $015664.l

kit_palette_tbl:
        dc.b    10,1,4,12,11,9,15,2     ; Red, Blue, White, Yellow, Orange, DarkRed, Purple, Cyan
        even
ko2_hnd_fname:
        dc.b    "KO2HND.BIN",0
ko2_eng_fname:
        dc.b    "KO2ENG.BIN",0
ko2_ste_fname:
        dc.b    "KO2STE.BIN",0
amigasnd_fname:
        dc.b    "AMIGASND.BIN",0
amigapit_fname:
        dc.b    "AMIGAP0.BIN",0
pm_match_fname:
        dc.b    "PMMATCH.BIN",0
        even
