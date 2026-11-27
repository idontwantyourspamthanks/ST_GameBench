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

BR_STATE        equ     $0b6800
BR_HOME_SC      equ     $0b6800         ; .w
BR_AWAY_SC      equ     $0b6802         ; .w
BR_HOME_HUM     equ     $0b6804         ; .w
BR_AWAY_HUM     equ     $0b6806         ; .w
BR_FAST         equ     $0b6808         ; .w (0=Normal 5m, 1=Fast 3m)
BR_CUP_ET       equ     $0b680a         ; .w (0=League, 1=Cup Extra Time)
BR_PM_A4        equ     $0b680c         ; .l
BR_PM_84        equ     $0b6810         ; .l
BR_TOS_84       equ     $0b6814         ; .l
BR_KICK_DIR     equ     $0b6818         ; .w (bit0=up/down, bit1=kickoff team)
BR_WEEK_SEED    equ     $0b681a         ; .w (week number for ref/weather variety)
BR_SAV_70       equ     $0b681c         ; .l saved $70.w VBL
BR_SAV_118      equ     $0b6820         ; .l saved $118.w IKBD
BR_KBDVBASE     equ     $0b6824         ; .l saved Kbdvbase()
BR_SAV_MVEC     equ     $0b6828         ; .l saved Kbdvbase+$10 (mousevec)
BR_SAV_JVEC     equ     $0b682c         ; .l saved Kbdvbase+$18 (joyvec)
BR_OLD_SSP      equ     $0b6830         ; .l saved old SSP across .rs_d!
BR_OLD_SR       equ     $0b6834         ; .w saved old SR across .rs_d!
BR_LINEA_BASE   equ     $0b6838         ; .l saved Line-A base ptr from $a000!
BR_RESULTS      equ     $0b6840         ; 26 x 10 bytes = 260 bytes ($0b6840..$0b6943)
BR_LINEA_SAVE   equ     $0b6950         ; 8 bytes ($2e..$35 of Line-A vars)
BR_MFP_SAVE     equ     $0b6960         ; 24 bytes: $110,$114,$120,$134 + IERA/IERB/IMRA/IMRB
BR_IS_STE       equ     $0b6978         ; .w: 1 = Atari STE/Mega STE detected, 0 = plain ST
BR_SAV_A0       equ     $0b697c         ; .l: saved $a0.w (TRAP #8) vector for STE Blitter call
BR_RNG_SEED     equ     $0b6980         ; .l: live VBL counter ($466.w) captured before KO2 PRNG seed!

KO2_STE_BASE    equ     $0ae940         ; $0ae940..$0b02ff (6.5 KB) for KO2STE.BIN (above FILES.CR $09d000..$0ae940!)

KO2_HOME_TEAM   equ     $0b6a00         ; $41e bytes
KO2_AWAY_TEAM   equ     $0b6e20         ; $41e bytes
PM_HND_SAVE     equ     $0b7240         ; $850 bytes
KO2_HND_BUF     equ     $0b7a90         ; $820 bytes
PM_DATA1_SAVE   equ     $0b8300         ; $740 bytes ($0219c0..$022100 -> $0b8a40)
PM_DATA2_SAVE   equ     $0b8a40         ; $3e00 bytes ($025900..$029700 -> $0bc840, well below 1MB HDDRIVER $0c4000 / TOS2.06 $0bdde4!)
KO2_REPLAY_BUF  equ     $0bc900         ; $6014 bytes ($0bc900..$0c2914 < $0c4000; 4 KB TOS 2.06 ring -> $0bd900 < $0bdde4!)
KO2_SCRATCH_BUF equ     $099000         ; $2c00 bytes temp depack scratch during $015f4c ($099000..$09bc00 < $09d000!)
KO2_FILES_CR    equ     $09d000         ; $11940 bytes ($09d000..$0ae940 < KO2_STE_BASE $0ae940!)

KO2_A4          equ     $0284aa
PM_HUM_KIT_OFF  equ     -$24c8          ; saved in every PM savegame & DEMO92.DAT (unused gap before -$24c2!)

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

        ; Look up authentic 1989-90 kits (human club uses PM_HUM_KIT_OFF; AI clubs match team_names_92!)
        ; Format of kit word: bit15=1, bits12..10=style(0..5), bits9..5=col1(0..19), bits4..0=col2(0..19)
        bsr.w   lookup_team_kit         ; a0 = home team -> d0.w = home kit word
        move.w  d0,d6                   ; d6 = home kit word
        movea.l -$1ee8(a4),a0
        bsr.w   lookup_team_kit         ; a0 = away team -> d0.w = away kit word
        move.w  d0,d4                   ; d4 = away kit word

        ; Smart perceptual colour-family clash resolution!
        move.w  d6,d0
        lsr.w   #5,d0
        andi.w  #31,d0                  ; home col1
        lea     kit_family_tbl(pc),a3
        move.b  0(a3,d0.w),d2           ; home family (0..6)
        move.w  d4,d1
        lsr.w   #5,d1
        andi.w  #31,d1                  ; away col1
        cmp.b   0(a3,d1.w),d2
        bne.s   .no_clash
        ; Clashing primary shirts! First try swapping Away col1 <-> col2 (away strip!)
        move.w  d4,d3
        andi.w  #31,d3                  ; away col2
        cmp.b   0(a3,d3.w),d2
        beq.s   .clash_alt
        ; Swap col1 <-> col2 on Away kit while keeping Away style!
        move.w  d4,d0
        andi.w  #$fc00,d0               ; keep bit15 + style
        lsl.w   #5,d3
        or.w    d3,d0                   ; new col1 = old col2
        or.w    d1,d0                   ; new col2 = old col1
        move.w  d0,d4
        bra.s   .no_clash
.clash_alt:
        ; Both Away colours clash with Home -> switch Away to crisp Plain Yellow/Navy or RoyalBlue/White!
        move.w  #$8180,d4               ; style 0 (Plain), Yellow(12) / Navy(0)
        cmpi.b  #4,d2                   ; is Home already Yellow?
        bne.s   .no_clash
        move.w  #$8024,d4               ; style 0 (Plain), RoyalBlue(1) / White(4)
.no_clash:
        ; Pack Home & Away teams into KO2 $41e structs
        movea.l -$1eec(a4),a0
        lea     KO2_HOME_TEAM.l,a2
        move.w  d6,d0                   ; packed home kit word
        bsr.w   pack_pm_to_ko2_team
        movea.l -$1ee8(a4),a0
        lea     KO2_AWAY_TEAM.l,a2
        move.w  d4,d0                   ; packed away kit word
        bsr.w   pack_pm_to_ko2_team

        ; Load KO2HND.BIN ($820 bytes) into KO2_HND_BUF via PP HD mode
        jsr     $006946.w               ; PP HD mode
        lea     ko2_hnd_fname(pc),a0
        lea     KO2_HND_BUF.l,a1
        move.l  #$820,d0
        bsr.w   load_hd_file
        tst.l   d0
        ble.w   .abort_restore_prd

        ; Save ONLY PM's live mutable data regions (17.3 KB -> $0b7300..$0bb840, well below 1MB HDDRIVER!)
        ; Static code+tables ($010000..$025900) are reloaded cleanly from PMCODE.BIN on match exit.
        lea     $0219c0.l,a0
        lea     PM_DATA1_SAVE.l,a1
        move.w  #($740/4-1),d0
.sv_d1: move.l  (a0)+,(a1)+
        dbra    d0,.sv_d1
        lea     $025900.l,a0
        lea     PM_DATA2_SAVE.l,a1
        move.w  #($3e00/4-1),d0
.sv_d2: move.l  (a0)+,(a1)+
        dbra    d0,.sv_d2

        ; Load KO2ENG.BIN ($14000 bytes) directly into $010000!
        lea     ko2_eng_fname(pc),a0
        lea     $010000.l,a1
        move.l  #$14000,d0
        bsr.w   load_hd_file
        move.l  d0,-(sp)
        ; Also preload KO2STE.BIN into $0ae940 (AMIGASND.BIN is loaded directly into KO2 heap after $013450!)
        clr.w   KO2_STE_BASE.l          ; clear header magic so missing KO2STE.BIN falls back cleanly!
        lea     ko2_ste_fname(pc),a0
        lea     KO2_STE_BASE.l,a1
        move.l  #$19c0,d0               ; max 6,592 bytes ($0ae940..$0b02ff)
        bsr.w   load_hd_file
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
        ; using the upper tail of HAGA's 200 KB cache buffer (shrunk to $18000 = 96 KB)!
        move.w  #$4ef9,$014c80.l
        move.l  #ko2_files_alloc,$014c82.l
        ; Route KO2's $01564c replay buffer ($6014) to KO2_REPLAY_BUF ($0bb900..$0c1914) with 1MB HDDRIVER guard!
        move.w  #$4ef9,$01564c.l
        move.l  #ko2_replay_alloc,$01564e.l
        ; Route KO2's $01adb8 temporary $2c00 sprite-depack scratch buffer to KO2_SCRATCH_BUF ($099000..$09bc00)
        ; (used only during $015f4c before STE rings init, and skip its Mfree at $01ae1a!)
        move.w  #$2c7c,$01adb8.l        ; movea.l #KO2_SCRATCH_BUF,a6
        move.l  #KO2_SCRATCH_BUF,$01adba.l
        move.w  #$6010,$01adbe.l        ; bra.s $01add0
        move.w  #$6006,$01ae1a.l        ; bra.s $01ae22 (skip Mfree(a6))
        ; Route KO2's $01ffb8 temporary $1600 depack scratch buffer to KO2_SCRATCH_BUF ($099000..$09a600)!
        move.w  #$2c7c,$01ffb8.l        ; movea.l #KO2_SCRATCH_BUF,a6
        move.l  #KO2_SCRATCH_BUF,$01ffba.l
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
        move.l  $466.w,BR_RNG_SEED.l    ; live 50Hz VBL counter for match PRNG seed!
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
        move.l  #$00018000,$6c6e.w      ; 96 KB KRD cache ($81000..$99000), leaving $99000..$9d000 scratch & $9d000..$ae940 FILES.CR!
        clr.w   $6c68.w                 ; force chunked cache mode
        move.l  $60c.w,$6c6a.w
        move.l  #-1,$6c72.w             ; invalidate KRD cache so $81000 reloads KRD!
        ; Fix PP's uncached Fread ($6ba0) which forgot to add Fseek offset $6c64.w to d4!
        move.w  #$4ef9,$6ba0.w
        move.l  #ko2_uncached_fix,$6ba2.w
        move.w  #$4e71,$6ba6.w
        move.l  BR_TOS_84.l,$6916.w
        ; Snapshot patched $6800..$7020 BACK into KO2_HND_BUF so .swap_to_ko2_hnd preserves all dynamic pointers (4MB/ACSI fix!)
        lea     $6800.w,a0
        lea     KO2_HND_BUF.l,a1
        move.w  #($820/4-1),d0
.sv_kh: move.l  (a0)+,(a1)+
        dbra    d0,.sv_kh
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
        move.w  #-1,-$df0(a4)           ; initialize Joystick 1 centered (-1, NOT 0=Up!)
        move.w  #-1,-$df8(a4)           ; initialize Joystick 0 centered
        jsr     $014c6a.l               ; KO2 load FILES.CR (tactics/fonts/data -> $09d000)
        jsr     $0139aa.l               ; KO2 Line-A menu graphics & font init (-$7724/-$7720)!
        jsr     $015f4c.l               ; KO2 Malloc($1c138) + KRD sprites + replay buf ($0c8b00)
        jsr     $014e54.l               ; KO2 string/name table init
        jsr     $010044.l               ; KO2 default match options

        ; Seed KO2's 48-bit LFSR PRNG (-$4cf6(a4), zeroed by BSS clear!) BEFORE $013450 / $0128a4
        ; so Pitch Condition (NORMAL/WET/SOGGY/PLASTIC), Wind, and Referee genuinely randomize!
        move.l  BR_RNG_SEED.l,d0
        move.w  BR_WEEK_SEED.l,d1
        mulu.w  #257,d1
        eor.l   d1,d0
        eor.l   #$5a3c91d7,d0
        bne.s   .rng_nz
        move.l  #$13579bdf,d0
.rng_nz:
        move.l  d0,-$4cf6(a4)
        move.w  #$a5c3,-$4cf2(a4)
        moveq   #11,d7
.rng_w: jsr     -$7e54(a4)              ; whiten 48-bit LFSR
        dbra    d7,.rng_w

        ; Configure KO2 match options BEFORE $013450:
        move.w  BR_CUP_ET.l,-$34ca(a4)  ; Extra time if cup tie
        move.w  #4,-$34d0(a4)           ; Pitch type = 4 (random: normal/wet/soggy/plastic!)
        clr.w   -$34c4(a4)              ; Game speed = 0 (FULL 50 FPS! 1=25fps slow mode!)
        moveq   #1,d0                   ; Default 5-min half (PM NORMAL)
        tst.w   BR_FAST.l
        beq.s   .len_ok
        moveq   #0,d0                   ; 3-min half (PM FAST)
.len_ok:
        move.w  d0,-$34ce(a4)
        jsr     -$7e54(a4)
        move.w  -$4cf6(a4),d0
        andi.w  #3,d0                   ; Valid Wind Strength 0..3 (table -$791c has 4 words!)
        move.w  d0,-$34cc(a4)
        jsr     $013450.l               ; randomize pitch (-$4eee), wind, half-length, aftertouch, ET
        clr.w   -$34be(a4)              ; random referee (0..23)
        jsr     $0128a4.l               ; initialize KO2 Referee (-$3a66 name + traits!)

        ; Show Kick Off 2's authentic Pre-Match Screen (ko6.men: clubs, kits, ref, pitch, wind)
        ; with live interactive kit changer (Joystick + Keyboard) BEFORE loading AMIGAPx.BIN!
        bsr.w   ko2_prematch_kits

        ; Preload the chosen Home & Away kit styles (0..5) from KRD NOW while KRD cache ($81000) is active,
        ; BEFORE AMIGAPx.BIN reuses $081000..$088e1f!
        move.w  KO2_HOME_TEAM+$418.l,-$4ec8(a4)
        move.w  KO2_AWAY_TEAM+$418.l,-$4ec6(a4)
        jsr     $01af88.l               ; loads Home/Away sprites into -$1204 heap & sets -$11f4/-$11f2!

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
        move.l  d0,-(sp)                ; save pitch bytes read
        ; Load AMIGASND.BIN directly into KO2's reserved SAMPLES.DAT buffer (STE_SND_BASE = KO2_STE_BASE+$10)!
        move.l  KO2_STE_BASE+$10.l,d0
        beq.s   .skip_asnd
        movea.l d0,a1
        lea     amigasnd_fname(pc),a0
        move.l  #$5a00,d0
        bsr.w   load_hd_file
        move.l  d0,KO2_STE_BASE+8.l
        tst.l   d0
        bgt.s   .skip_asnd
        clr.l   KO2_STE_BASE+$10.l      ; missing AMIGASND.BIN -> silent fallback
.skip_asnd:
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
        ; Deselect floppy drives A & B (PSG reg 14 bits 1..2 = 1 via XBIOS Ongibit)
        ; so the floppy motor stops cleanly during the match and KO2's $0202ac
        ; Giaccess(0,14) motor-off poll never hangs when booting from floppy!
        move.w  #$0006,-(sp)
        move.w  #$1e,-(sp)              ; XBIOS #30 Ongibit(0x06)
        trap    #14
        addq.l  #4,sp

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
        ; 2. Reload unmodified PM code+static data ($010000..$025900 = $15900 bytes) from PMCODE.BIN
        jsr     $006946.w               ; PP HD mode
        lea     pm_code_fname(pc),a0
        lea     $010000.l,a1
        move.l  #$15900,d0
        bsr.w   load_hd_file
        jsr     $006942.w               ; restore PP PRD mode
        move.w  #$0006,-(sp)
        move.w  #$1e,-(sp)              ; XBIOS #30 Ongibit(0x06) - stop floppy motor cleanly
        trap    #14
        addq.l  #4,sp
        ; Re-apply all micro_opt + league92 + ko2_bridge hooks cleanly!
        bsr.w   reapply_pm_hooks

        ; 3. Restore PM's two live mutable data chunks ($0219c0..$022100 & $025900..$029700)
        lea     PM_DATA1_SAVE.l,a0
        lea     $0219c0.l,a1
        move.w  #($740/4-1),d0
.rs_d1: move.l  (a0)+,(a1)+
        dbra    d0,.rs_d1
        lea     PM_DATA2_SAVE.l,a0
        lea     $025900.l,a1
        move.w  #($3e00/4-1),d0
.rs_d2: move.l  (a0)+,(a1)+
        dbra    d0,.rs_d2

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
; Helper: pack_pm_to_ko2_team(a0=PM team, a2=KO2 $41e dst, d0.w=packed kit word)
; Copies team name + up to 24 players (remapping shirt 13 -> 14 for KO2!)
; ---------------------------------------------------------------------------
pack_pm_to_ko2_team:
        movem.l d0-d7/a0-a3/a5-a6,-(sp)
        move.w  d0,-(sp)                ; save packed kit word on stack
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

        ; Set KO2 tactics [0,1,2,3], active=0, unpack kit word -> style($418), col1($41a), col2($41c)
        lea     $406(a2),a3
        move.l  #0,(a3)+
        move.l  #1,(a3)+
        move.l  #2,(a3)+
        move.l  #3,(a3)+
        clr.w   $416(a2)
        move.w  (sp)+,d0                ; packed kit word: bit15=1, 12..10=style, 9..5=col1, 4..0=col2
        move.w  d0,d1
        andi.w  #31,d1                  ; col2 (0..19)
        move.w  d1,$41c(a2)
        lsr.w   #5,d0
        move.w  d0,d1
        andi.w  #31,d1                  ; col1 (0..19)
        move.w  d1,$41a(a2)
        lsr.w   #5,d0
        andi.w  #7,d0                   ; style (0..5)
        cmpi.w  #6,d0
        blt.s   .st_ok
        moveq   #1,d0
.st_ok: move.w  d0,$418(a2)
        movem.l (sp)+,d0-d7/a0-a3/a5-a6
        rts

; ---------------------------------------------------------------------------
; Helper: lookup_team_kit(a0 = PM team ptr, a4 = PM a4) -> d0.w packed kit word
; ---------------------------------------------------------------------------
lookup_team_kit:
        movem.l d1-d3/a0-a3,-(sp)
        ; Human club? Use custom kit saved at PM_HUM_KIT_OFF(a4) if initialized!
        tst.w   $28(a0)
        beq.s   .ltk_ai
        move.w  PM_HUM_KIT_OFF(a4),d0
        bmi.s   .ltk_ret                ; bit 15 set -> valid custom human club kit!
        move.w  #$8024,d0               ; fallback default: style 0 (Plain), Royal Blue(1) / White(4)
        bra.s   .ltk_ret
.ltk_ai:
        ; Match club name against team_names_92 (automatically follows promotion/relegation!)
        lea     team_names_92(pc),a1
        moveq   #0,d1                   ; idx 0..91
.ltk_lp:
        movea.l a0,a2
        movea.l a1,a3
.ltk_cm:
        move.b  (a2)+,d2
        move.b  (a3)+,d3
        cmp.b   d2,d3
        bne.s   .ltk_nx
        tst.b   d2
        bne.s   .ltk_cm
        ; Exact name match at index d1!
        add.w   d1,d1
        lea     team_kits_92(pc),a2
        move.w  0(a2,d1.w),d0
        bra.s   .ltk_ret
.ltk_nx:
        lea     20(a1),a1
        addq.w  #1,d1
        cmpi.w  #92,d1
        blt.s   .ltk_lp
        ; Custom-renamed AI team: use its slot index in team_kits_92
        move.l  a0,d0
        sub.l   -$2e94(a4),d0
        divu.w  #100,d0
        cmpi.w  #92,d0
        bhs.s   .ltk_def
        add.w   d0,d0
        lea     team_kits_92(pc),a2
        move.w  0(a2,d0.w),d0
        bra.s   .ltk_ret
.ltk_def:
        move.w  #$8024,d0
.ltk_ret:
        movem.l (sp)+,d1-d3/a0-a3
        rts

; ---------------------------------------------------------------------------
; Pre-Match Screen (ko6.men): Display teams, kits, referee, pitch condition,
; wind, and allow changing Home/Away kit colours & styles before kickoff!
; Controls:
;   Joystick 1 Fire / Space / Return : KICK OFF!
;   Joystick 1 Up/Down (or Arrow U/D): cycle Home Shirt Colour
;   Joystick 1 L/R    (or Arrow L/R) : cycle Away Shirt Colour
;   Keys 1 / 2 / 3                   : Home Style / Shirt / Trim
;   Keys 4 / 5 / 6                   : Away Style / Shirt / Trim
; ---------------------------------------------------------------------------
ko2_prematch_kits:
        movem.l d0-d7/a0-a3/a5-a6,-(sp)
        lea     KO2_HOME_TEAM.l,a0
        lea     KO2_AWAY_TEAM.l,a1
        jsr     $01338c.l               ; draw authentic Kick Off 2 ko6.men pre-match screen!

        ; Clear unused bottom area (y=132..199: below PITCH/WIND boxes -> zero clipping!)
        lea     $078000+132*160.l,a0
        move.w  #(68*160/4-1),d0
.pm_cb: clr.l   (a0)+
        dbra    d0,.pm_cb

        ; Set col 15 = pure crisp white ($0777) for our control legend (unused in y=0..131!)
        move.w  #$0777,-(sp)
        move.w  #15,-(sp)
        move.w  #7,-(sp)                ; XBIOS Setcolor(15, $0777)
        trap    #14
        addq.l  #6,sp

        ; Draw clean 4-line control legend centred in y=141..188
        lea     $078000+141*160.l,a3
        lea     pm_hint_l0(pc),a0
        moveq   #82,d4                  ; 31*5=155 -> (320-155)/2 = 82
        moveq   #15,d0
        bsr.w   draw_mini_str
        lea     $078000+155*160.l,a3
        lea     pm_hint_l1(pc),a0
        moveq   #55,d4                  ; 42*5=210 -> 55
        moveq   #15,d0
        bsr.w   draw_mini_str
        lea     $078000+165*160.l,a3
        lea     pm_hint_l2(pc),a0
        moveq   #55,d4
        moveq   #15,d0
        bsr.w   draw_mini_str
        lea     $078000+181*160.l,a3
        lea     pm_hint_l3(pc),a0
        moveq   #82,d4                  ; 31*5=155 -> 82
        moveq   #15,d0
        bsr.w   draw_mini_str

        lea     KO2_HOME_TEAM.l,a5
        lea     KO2_AWAY_TEAM.l,a6
        ; NOTE: NEVER keep a2 across trap #1 / trap #14 (TOS clobbers d0-d2/a0-a2)!
        ; Read Joystick 1 directly via a4-relative -$df0(a4) (dir) & -$dee(a4) (fire)!
        ; Wait until fire button released so accidental held fire doesn't skip screen
.pm_wrel:
        move.w  #$25,-(sp)              ; XBIOS Vsync
        trap    #14
        addq.l  #2,sp
        tst.w   -$dee(a4)
        bne.s   .pm_wrel
        ; Flush any stale buffered keypresses
.pm_flsh:
        move.w  #$0b,-(sp)              ; GEMDOS Cconis
        trap    #1
        addq.l  #2,sp
        tst.w   d0
        beq.s   .pm_go
        move.w  #$08,-(sp)              ; GEMDOS Cnecin
        trap    #1
        addq.l  #2,sp
        bra.s   .pm_flsh
.pm_go:
        moveq   #-1,d5                  ; last joy dir (edge-triggered!)
.pm_loop:
        move.w  #$25,-(sp)              ; XBIOS Vsync (50 Hz poll)
        trap    #14
        addq.l  #2,sp

        ; 1. Check Joystick 1 Fire -> Kick Off!
        tst.w   -$dee(a4)
        bne.w   .pm_done

        ; 2. Check Joystick 1 Direction (edge-triggered)
        move.w  -$df0(a4),d0
        cmp.w   d5,d0
        beq.s   .pm_chk_key
        move.w  d0,d5
        cmpi.w  #0,d0                   ; Joy Up -> Home Col1 +1
        beq.s   .h_c1_p
        cmpi.w  #4,d0                   ; Joy Down -> Home Col1 -1
        beq.s   .h_c1_m
        cmpi.w  #2,d0                   ; Joy Right -> Away Col1 +1
        beq.s   .a_c1_p
        cmpi.w  #6,d0                   ; Joy Left -> Away Col1 -1
        beq.s   .a_c1_m
        bra.s   .pm_chk_key

.h_c1_p: moveq  #1,d1
        lea     $41a(a5),a3
        bra.w   .mod_col
.h_c1_m: moveq  #-1,d1
        lea     $41a(a5),a3
        bra.w   .mod_col
.a_c1_p: moveq  #1,d1
        lea     $41a(a6),a3
        bra.w   .mod_col
.a_c1_m: moveq  #-1,d1
        lea     $41a(a6),a3
        bra.w   .mod_col

.pm_chk_key:
        move.w  #$0b,-(sp)              ; GEMDOS Cconis
        trap    #1
        addq.l  #2,sp
        tst.w   d0
        beq.s   .pm_loop
        move.w  #$08,-(sp)              ; GEMDOS Cnecin -> low byte ASCII, high word scancode
        trap    #1
        addq.l  #2,sp
        cmpi.b  #' ',d0                 ; Space -> Kick Off!
        beq.w   .pm_done
        cmpi.b  #$0d,d0                 ; Return -> Kick Off!
        beq.w   .pm_done
        cmpi.b  #'1',d0                 ; 1 = Home Style (0..5)
        beq.s   .h_st
        cmpi.b  #'2',d0                 ; 2 = Home Col1 (0..19)
        beq.s   .h_c1_p
        cmpi.b  #'3',d0                 ; 3 = Home Col2 (0..19)
        beq.s   .h_c2_p
        cmpi.b  #'4',d0                 ; 4 = Away Style (0..5)
        beq.s   .a_st
        cmpi.b  #'5',d0                 ; 5 = Away Col1 (0..19)
        beq.s   .a_c1_p
        cmpi.b  #'6',d0                 ; 6 = Away Col2 (0..19)
        beq.s   .a_c2_p
        swap    d0                      ; scancode in low byte
        cmpi.b  #$48,d0                 ; Up arrow -> Home Col1 +1
        beq.s   .h_c1_p
        cmpi.b  #$50,d0                 ; Down arrow -> Home Col1 -1
        beq.s   .h_c1_m
        cmpi.b  #$4d,d0                 ; Right arrow -> Away Col1 +1
        beq.s   .a_c1_p
        cmpi.b  #$4b,d0                 ; Left arrow -> Away Col1 -1
        beq.s   .a_c1_m
        bra.w   .pm_loop

.h_c2_p: moveq  #1,d1
        lea     $41c(a5),a3
        bra.s   .mod_col
.a_c2_p: moveq  #1,d1
        lea     $41c(a6),a3
        bra.s   .mod_col
.h_st:  lea     $418(a5),a3
        bra.s   .mod_st
.a_st:  lea     $418(a6),a3
.mod_st:
        move.w  (a3),d0
        addq.w  #1,d0
        cmpi.w  #6,d0
        blt.s   .st_sv
        moveq   #0,d0
.st_sv: move.w  d0,(a3)
        bra.s   .pm_redraw
.mod_col:
        move.w  (a3),d0
        add.w   d1,d0
        bpl.s   .mc_hi
        moveq   #19,d0
.mc_hi: cmpi.w  #20,d0
        blt.s   .mc_sv
        moveq   #0,d0
.mc_sv: move.w  d0,(a3)
.pm_redraw:
        movea.l a5,a0
        movea.l a6,a1
        jsr     $01331a.l               ; live-update both visual jerseys & palette slots 11..14!
        bra.w   .pm_loop

.pm_done:
        ; Wait fire release before kicking off
.pm_wr2:
        move.w  #$25,-(sp)
        trap    #14
        addq.l  #2,sp
        tst.w   -$dee(a4)
        bne.s   .pm_wr2
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
        ; Check if full 24 KB KO2_REPLAY_BUF ($0bb900..$0c1914) fits below resident HDDRIVER/TOS ($69a0)!
        ; On 1MB TOS 1.04/1.62 + HDDRIVER: BR_TOS_84 >= $0cd050 (HDDRIVER >= $0c4000 -> 10 KB margin!).
        ; On 1MB TOS 2.06 + HDDRIVER: BR_TOS_84 = $0c6d50 (HDDRIVER @ $0bdde4) -> shrink ring to 6 KB ($1800 -> $0bd100)!
        move.l  #KO2_REPLAY_BUF,-$2b8a(a4)
        cmpi.l  #$0cb000,BR_TOS_84.l
        bhs.s   .rep_full
        ; Shrink KO2 replay ring from $6000 (24 KB) -> $1000 (4 KB, $0bc900..$0bd900 < $0bdde4!)
        move.w  #$07ff,$01568c.l        ; clear 2,048 words ($1000 bytes) instead of $2fff words
        move.w  #$1000,$01567e.l
        move.w  #$1000,$015736.l
        move.w  #$1000,$01a322.l
        move.w  #$1000,$01a36c.l
        move.w  #$1000,$01b270.l
        move.w  #$1000,$01b294.l
        move.w  #$1000,$01b2ba.l
        move.w  #$1000,$01b2e0.l
        move.w  #$1000,$01b4f4.l
        move.w  #$1000,$01f9d6.l
        move.w  #$1000,$01fa6c.l
.rep_full:
        jmp     $015664.l

; Perceptual colour-family table for KO2's 20 kit colours (0..19):
; 0=Blue, 1=White/Grey, 2=Black, 3=Red/Orange/Claret, 4=Yellow, 5=Pink/Purple, 6=Green/Teal
kit_family_tbl:
        dc.b    0,0,0,0, 1,1,1, 2, 3,3,3,3, 4, 5,5,5, 6,6, 0,6
pm_hint_l0:
        dc.b    "MATCH KIT CHECK - AVOID CLASHES",0
pm_hint_l1:
        dc.b    "HOME: JOY U/D OR 1:STYLE 2:SHIRT 3:TRIM",0
pm_hint_l2:
        dc.b    "AWAY: JOY L/R OR 4:STYLE 5:SHIRT 6:TRIM",0
pm_hint_l3:
        dc.b    "PRESS FIRE OR SPACE TO KICK OFF",0
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
pm_code_fname:
        dc.b    "PMCODE.BIN",0
        even
