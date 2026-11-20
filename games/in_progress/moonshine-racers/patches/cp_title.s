; name: cp_title
; default: yes
; site: $74fe
; orig: 4fef000e6106
; media: hd
; gate: ram2mb
; requires: cp_wrap cp_fetch cp_ptr cp_end cp_start cp_hiscore
; conflicts: mx_pre mf_pre sb_bar
; himem: $100000-$1003FF CRC-32 table (256 longs, built on every load)
; himem: $100400-$1007FF campaign menu scratch (item vectors, line buffer, track texts)
; himem: $110000-$12FFFF campaign file as read (MSTRACKS.TRK, at most 123,496 B)
; doc: Campaigns (ST family with 2 MB or more only): F10 on the title screen opens the campaign menu (Original game / Load campaign from the hard disk or from a disk in drive A / Play from track N); the campaign replaces the 15 tracks.
; note: Campaign feature, HD build (work/notes/campaign_hd.md).  This patch holds the menu, the file reader and the validator; the redirect sites are cp_wrap ($72c4), cp_fetch ($77da), cp_ptr ($fda2), cp_end ($731e), cp_start ($7252), cp_hiscore ($8418).
; note: Site $74fe = the shared key exit of the title screen's face/text loop ($7446-$74fc: any key or joystick fire starts the game): `lea $e(a7),a7 / bsr.b $750a` (6 bytes) -> `jmp e1`.  e1 replays both
; note: instructions for every key but F10 (scancode $44 in $60ff).  F10 runs the menu: cp_menu returns 1 = start the game (the exit replayed as the game does it: fade out, carry set), 0 = back to the title
; note: (the title routine $73e6 is entered again with its return address on the stack).  The stack at $74fe holds d7.w and a1/a2/a6 (14 bytes) in the sprite loop but only the return address ($7246) in the
; note: final wait loop ($74dc-$74fc), where the original `lea $e(a7),a7` pops 14 bytes too many: the F10 path tests that and does not pop.
; note: The menu screens use the game's own text routine $12268 (a0 = x,y,text,0; a5 = screen; d4 = colour code $b8; font $190be), the buffer clear $d8e0, the vertical sync $d206 and the palette registers directly.  The
; note: selected row is shown by inverting its 8 pixel rows (palette: black background, white text; inverted: white bar, black text), the headings by clearing bitplane 0 (yellow).  Keys: up/down, Return / Enter / Space, Esc /
; note: Backspace / Left; joystick port 1: up, down, fire.  The campaign file is read with the HAGA-window reader (a port of Populous 2's part A/B, work/trackloader/trkread.s) and validated before anything is used:
; note: magic, version 1, count 1..15, file length, table CRC-32, per entry flags/base/offset/length/name and the block CRC-32; anything else rejects the file with a message (the game stays original).

V_ACT   equ     CPV             ; b  campaign active: the races use it
V_LOADED equ    CPV+1           ; b  a validated campaign is in the store
V_COUNT equ     CPV+2           ; w  number of tracks (1..15)
V_START equ     CPV+6           ; w  position (0-based) of the next new game
M_CNT   equ     CPWORK+$00      ; w  menu: item count
M_ROW0  equ     CPWORK+$02      ; w  first item row
M_STEP  equ     CPWORK+$04      ; w  rows between items
M_SEL   equ     CPWORK+$06      ; w  selected item
M_PJOY  equ     CPWORK+$08      ; b  joystick bits of the previous poll
M_MSG   equ     CPWORK+$0A      ; l  message to show on the next main screen (0 = none)
M_ITEMS equ     CPWORK+$10      ; 18 longs: item texts
M_ACTS  equ     CPWORK+$58      ; 18 bytes: item actions of the main screen
M_LINE  equ     CPWORK+$70      ; 48 bytes: x,y,text line for $12268
M_TXT   equ     CPWORK+$A0      ; 15 x 32 bytes: track list texts (+ the loaded-campaign line)
M_TXT2  equ     CPWORK+$280     ; 40 bytes

        org     $74fe
        jmp     $B9F00.l

        org     $B9F00
        jmp     e1.l            ; $B9F00: title exit (site $74fe)
        jmp     e2.l            ; $B9F06: hi-score screen exit (cp_hiscore, site $8418)

; ---- title exit
e1:     cmpi.b  #$44,$60ff.w            ; F10
        beq.s   .f10
        lea     $e(a7),a7               ; the displaced instructions
        jsr     $750a.l
        jmp     $7504.l                 ; move.w #$ff,ccr / rts
.f10:   cmpi.l  #$7246,(a7)             ; final wait loop: only the return address is on the stack
        beq.s   .m
        lea     $e(a7),a7
.m:     bsr     cp_menu
        clr.b   $60ff.w
        tst.w   d0
        beq.s   .t
        jsr     $750a.l                 ; as the key exit does: fade out ...
        jmp     $7504.l                 ; ... carry set = start
.t:     jmp     $73e6.l                 ; the title again

; ---- hi-score screen exit (site $8418: `bsr.b $8420 / move.w #$ff,ccr` = key pressed)
e2:     cmpi.b  #$44,$60ff.w
        bne.s   .k
        bsr     cp_menu
        clr.b   $60ff.w
        tst.w   d0
        bne.s   .k
        jsr     $8420.l                 ; back: the screen is faded out and cleared, carry clear = the title loop goes on
        move.w  #0,ccr
        rts
.k:     jsr     $8420.l
        move.w  #$ff,ccr
        rts

; ---- the menu.  Returns d0.w = 1 start a game (V_ACT / V_START set), 0 back to the title.
cp_menu:
        movem.l d1-d7/a0-a6,-(a7)
        move.b  $6105.w,M_PJOY.l
        clr.l   M_MSG.l
        clr.w   M_SEL.l
        lea     pal(pc),a0
        lea     $ffff8240.l,a1
        moveq   #15,d0
.p:     move.w  (a0)+,(a1)+
        dbra    d0,.p
.main:  bsr     main_screen             ; d0 = action 0..4 or -1
        tst.w   d0
        bmi.s   .title
        beq.s   .orig                   ; 0 original game
        subq.w  #2,d0
        bmi.s   .hd                     ; 1
        beq.s   .drva                   ; 2
        subq.w  #1,d0
        beq.s   .list                   ; 3 loaded campaign
        bra.s   .title                  ; 4 back
.hd:    lea     p_hd(pc),a0
        lea     m_ldhd(pc),a1
        lea     e_nf(pc),a2
        bra.s   .ld
.drva:  lea     p_a(pc),a0
        lea     m_lda(pc),a1
        lea     e_nfa(pc),a2
.ld:    bsr     load
        bne.s   .main                   ; message set
.list:  bsr     list_screen             ; d0 = track (0-based) or -1 back
        tst.w   d0
        bmi.s   .main
        move.w  d0,V_START.l
        st      V_ACT.l
        moveq   #1,d0
        bra.s   .out
.orig:  clr.b   V_ACT.l
        clr.w   V_START.l
        moveq   #1,d0
        bra.s   .out
.title: moveq   #0,d0
.out:   move.w  d0,-(a7)
.fr:    jsr     $d206.l                 ; wait for the joystick fire to be released (it must not skip the next screen)
        btst    #7,$6105.w
        bne.s   .fr
        move.w  (a7)+,d0
        movem.l (a7)+,d1-d7/a0-a6
        rts

; ---- screen 1: Original game / hard disk / drive A / loaded campaign / back.  -> d0.w action or -1
main_screen:
        jsr     $d8e0.l
        lea     h_main(pc),a0
        bsr     dstr
        moveq   #1,d1
        bsr     tint_row
        lea     M_ITEMS.l,a2
        lea     M_ACTS.l,a3
        moveq   #0,d5
        lea     t_orig(pc),a0
        moveq   #0,d0
        bsr     addit
        lea     t_hd(pc),a0
        moveq   #1,d0
        bsr     addit
        lea     t_a(pc),a0
        moveq   #2,d0
        bsr     addit
        tst.b   V_LOADED.l
        beq.s   .nl
        lea     M_TXT2.l,a1
        lea     t_loaded(pc),a0
.c1:    move.b  (a0)+,(a1)+
        bne.s   .c1
        subq.l  #1,a1
        moveq   #0,d0
        move.w  V_COUNT.l,d0
        bsr     dec2
        lea     t_tracks(pc),a0
.c2:    move.b  (a0)+,(a1)+
        bne.s   .c2
        lea     M_TXT2.l,a0
        moveq   #3,d0
        bsr     addit
.nl:    lea     t_back(pc),a0
        moveq   #4,d0
        bsr     addit
        move.w  d5,M_CNT.l
        move.w  #6,M_ROW0.l
        move.w  #2,M_STEP.l
        cmp.w   M_SEL.l,d5
        bhi.s   .sok
        clr.w   M_SEL.l
.sok:   lea     t_origon(pc),a0         ; status line
        tst.b   V_ACT.l
        beq.s   .st
        lea     t_campon(pc),a0
.st:    moveq   #2,d0
        moveq   #22,d1
        bsr     putline
        lea     t_hint(pc),a0
        moveq   #2,d0
        moveq   #23,d1
        bsr     putline
        move.l  M_MSG.l,d0
        beq.s   .nm
        movea.l d0,a0
        clr.l   M_MSG.l
        bsr     msg
.nm:    bsr     menu_run
        bmi.s   .x
        lea     M_ACTS.l,a0
        move.b  (a0,d0.w),d0
        andi.w  #$ff,d0
.x:     rts

addit:  move.l  a0,(a2)+                ; a0 = text, d0 = action
        move.b  d0,(a3)+
        addq.w  #1,d5
        rts

; ---- screen 2: the loaded campaign's tracks.  -> d0.w track (0-based) or -1 (back)
list_screen:
        jsr     $d8e0.l
        lea     M_LINE.l,a1             ; heading "CAMPAIGN: NN TRACKS"
        move.b  #10,(a1)+
        move.b  #1,(a1)+
        lea     t_camp(pc),a0
.h1:    move.b  (a0)+,(a1)+
        bne.s   .h1
        subq.l  #1,a1
        moveq   #0,d0
        move.w  V_COUNT.l,d0
        bsr     dec2
        lea     t_tracks2(pc),a0
.h2:    move.b  (a0)+,(a1)+
        bne.s   .h2
        lea     M_LINE.l,a0
        bsr     dstr
        moveq   #1,d1
        bsr     tint_row
        lea     h_play(pc),a0
        bsr     dstr
        lea     M_ITEMS.l,a2
        lea     M_TXT.l,a3              ; item texts
        lea     CPSTORE+16.l,a4         ; entries
        move.w  V_COUNT.l,d5
        moveq   #0,d6                   ; index
.t:     move.l  a3,(a2)+
        move.w  d6,d0
        addq.w  #1,d0
        movea.l a3,a1
        bsr     dec2
        move.b  #' ',(a1)+
        move.b  #' ',(a1)+
        moveq   #23,d1
        movea.l a4,a0
.nm:    move.b  (a0)+,d0
        beq.s   .ne
        cmpi.b  #'a',d0                 ; the font's lower case is poor (no descenders): show names in capitals
        bcs.s   .u
        cmpi.b  #'z',d0
        bhi.s   .u
        subi.b  #$20,d0
.u:     move.b  d0,(a1)+
        dbra    d1,.nm
.ne:    clr.b   (a1)
        lea     32(a3),a3
        lea     40(a4),a4
        addq.w  #1,d6
        cmp.w   d5,d6
        bcs.s   .t
        lea     t_back2(pc),a0
        move.l  a0,(a2)+
        addq.w  #1,d6
        move.w  d6,M_CNT.l
        move.w  #5,M_ROW0.l
        move.w  #1,M_STEP.l
        cmpi.w  #8,d6                   ; up to 7 tracks + back: two rows per item
        bhi.s   .s1
        move.w  #2,M_STEP.l
.s1:
        clr.w   M_SEL.l
        lea     t_hint(pc),a0
        moveq   #2,d0
        moveq   #23,d1
        bsr     putline
        bsr     menu_run
        bmi.s   .x
        cmp.w   V_COUNT.l,d0
        bcs.s   .x
        moveq   #-1,d0                  ; "< back"
.x:     rts

; ---- the generic menu: M_CNT items (M_ITEMS), first row M_ROW0, row step M_STEP, selection M_SEL.  -> d0.w index or -1 (Esc)
menu_run:
        bsr     draw_items
        bsr     hilite
.k:     bsr     getkey
        cmpi.b  #$48,d0
        beq.s   .up
        cmpi.b  #$50,d0
        beq.s   .dn
        cmpi.b  #$1c,d0
        beq.s   .ok
        cmpi.b  #$72,d0
        beq.s   .ok
        cmpi.b  #$39,d0
        beq.s   .ok
        cmpi.b  #$01,d0
        beq.s   .esc
        cmpi.b  #$0e,d0
        beq.s   .esc
        cmpi.b  #$4b,d0
        beq.s   .esc
        bra.s   .k
.up:    bsr     hilite
        move.w  M_SEL.l,d0
        bne.s   .u1
        move.w  M_CNT.l,d0
.u1:    subq.w  #1,d0
        move.w  d0,M_SEL.l
        bra.s   .re
.dn:    bsr     hilite
        move.w  M_SEL.l,d0
        addq.w  #1,d0
        cmp.w   M_CNT.l,d0
        bcs.s   .d1
        moveq   #0,d0
.d1:    move.w  d0,M_SEL.l
.re:    bsr     hilite
        bra.s   .k
.ok:    move.w  M_SEL.l,d0
        rts
.esc:   moveq   #-1,d0
        rts

hilite: move.w  M_SEL.l,d1              ; invert the selected item's row
        mulu    M_STEP.l,d1
        add.w   M_ROW0.l,d1
        movea.l $1004.w,a0
        mulu    #1280,d1
        adda.l  d1,a0
        lea     8(a0),a0                ; 16-pixel groups 1..18
        moveq   #7,d1
.r:     moveq   #35,d2
        movea.l a0,a1
.l:     not.l   (a1)+
        dbra    d2,.l
        lea     160(a0),a0
        dbra    d1,.r
        rts

tint_row:                               ; d1 = text row: clear bitplane 0 (white -> yellow)
        movea.l $1004.w,a0
        mulu    #1280,d1
        adda.l  d1,a0
        moveq   #7,d1
.r:     moveq   #19,d2
        movea.l a0,a1
.g:     clr.w   (a1)
        addq.l  #8,a1
        dbra    d2,.g
        lea     160(a0),a0
        dbra    d1,.r
        rts

draw_items:
        moveq   #0,d6
.l:     cmp.w   M_CNT.l,d6
        bcc.s   .x
        move.w  d6,d0
        lsl.w   #2,d0
        lea     M_ITEMS.l,a1
        movea.l (a1,d0.w),a0
        move.w  d6,d1
        mulu    M_STEP.l,d1
        add.w   M_ROW0.l,d1
        moveq   #5,d0
        move.w  d6,-(a7)
        bsr     putline
        move.w  (a7)+,d6
        addq.w  #1,d6
        bra.s   .l
.x:     rts

getkey:                                 ; -> d0.b: scancode, or $48 / $50 / $1c from the joystick
.w:     jsr     $d206.l
        move.b  $60ff.w,d0
        beq.s   .j
        clr.b   $60ff.w
        rts
.j:     move.b  $6105.w,d1
        move.b  M_PJOY.l,d2
        move.b  d1,M_PJOY.l
        not.b   d2
        and.b   d2,d1
        btst    #0,d1
        beq.s   .j1
        moveq   #$48,d0
        rts
.j1:    btst    #1,d1
        beq.s   .j2
        moveq   #$50,d0
        rts
.j2:    tst.b   d1
        bpl.s   .w
        moveq   #$1c,d0
        rts

; ---- text
putline:                                ; d0 = x, d1 = y, a0 = text -> drawn with the game's routine
        lea     M_LINE.l,a1
        move.b  d0,(a1)+
        move.b  d1,(a1)+
.c:     move.b  (a0)+,(a1)+
        bne.s   .c
        lea     M_LINE.l,a0
dstr:   movea.l $1004.w,a5              ; a0 = x,y,text,0
        move.w  #$b8,d4
        jmp     $12268.l

clrrow: lea     M_LINE.l,a1             ; d1 = row: 40 spaces
        clr.b   (a1)+
        move.b  d1,(a1)+
        moveq   #39,d0
.s:     move.b  #' ',(a1)+
        dbra    d0,.s
        clr.b   (a1)
        lea     M_LINE.l,a0
        bra.s   dstr

msg:    move.l  a0,-(a7)                ; a0 = text: message row 21
        moveq   #20,d1
        bsr     clrrow
        movea.l (a7)+,a0
        moveq   #2,d0
        moveq   #20,d1
        bra.s   putline

dec2:   andi.l  #$ffff,d0               ; d0.w 0..99 -> two characters (leading space) at (a1)+
        divu    #10,d0
        tst.w   d0
        bne.s   .t
        move.b  #' ',(a1)+
        bra.s   .u
.t:     addi.b  #'0',d0
        move.b  d0,(a1)+
.u:     swap    d0
        addi.b  #'0',d0
        move.b  d0,(a1)+
        rts

; ---- load: a0 = path, a1 = "loading" text, a2 = "not found" text -> d0 = 0 loaded (V_ACT = V_LOADED = 1), else M_MSG set
load:   clr.b   V_ACT.l
        clr.b   V_LOADED.l
        move.l  a2,-(a7)
        move.l  a0,-(a7)
        movea.l a1,a0
        bsr     msg
        movea.l (a7)+,a0
        lea     CPSTORE.l,a1
        move.l  #$1F000,d1
        bsr     trk_read                ; d0 = 0 / error, d1 = bytes
        movea.l (a7)+,a2
        tst.l   d0
        beq.s   .rd
        lea     e_io(pc),a0
        cmpi.l  #-1,d0
        bne.s   .e1
        lea     e_na(pc),a0             ; HAGA not recognised
        bra.s   .err
.e1:    cmpi.l  #$cd,d0
        bne.s   .e2
        lea     e_big(pc),a0
        bra.s   .err
.e2:    cmpi.l  #-33,d0                 ; file / path not found
        beq.s   .nf
        cmpi.l  #-34,d0
        beq.s   .nf
        cmpa.l  #e_nfa,a2               ; drive A: any other GEMDOS error = no usable disk (an empty drive A answers after about 17 s)
        bne.s   .err
        tst.l   d0
        bpl.s   .err
.nf:    movea.l a2,a0
.err:   move.l  a0,M_MSG.l
        moveq   #1,d0
        rts
.rd:    move.l  d1,-(a7)
        lea     m_chk(pc),a0
        bsr     msg
        move.l  (a7)+,d1
        bsr     validate                ; d0 = 0 / 1 structure / 2 CRC
        beq.s   .good
        lea     e_bad(pc),a0
        subq.w  #1,d0
        beq.s   .err
        lea     e_crc(pc),a0
        bra.s   .err
.good:  st      V_LOADED.l
        st      V_ACT.l
        moveq   #0,d0
        rts

; ---- validate the file in CPSTORE (d1 = its size) -> d0.w 0 ok / 1 not a valid campaign file / 2 CRC error; sets V_COUNT
validate:
        lea     CPSTORE.l,a2
        cmpi.l  #'MSTK',(a2)
        bne     .bad
        cmpi.w  #1,4(a2)
        bne     .bad
        moveq   #0,d2
        move.w  6(a2),d2                ; count 1..15
        beq     .bad
        cmpi.w  #15,d2
        bhi     .bad
        cmp.l   8(a2),d1                ; file length
        bne     .bad
        move.w  d2,V_COUNT.l
        bsr     crc_tab
        lea     CPTAB.l,a6
        moveq   #-1,d0
        movea.l a2,a1
        moveq   #11,d3
        bsr     crc_upd                 ; header bytes 0..11 ...
        lea     16(a2),a1
        move.w  V_COUNT.l,d3
        mulu    #40,d3
        subq.w  #1,d3
        bsr     crc_upd                 ; ... and the entry table
        not.l   d0
        cmp.l   12(a2),d0
        bne     .crc
        moveq   #0,d4
        move.w  V_COUNT.l,d4
        move.w  d4,d5
        subq.w  #1,d5                   ; entry counter
        mulu    #40,d4
        addi.l  #16,d4                  ; d4 = offset the next block must have
        lea     16(a2),a3
.e:     tst.w   26(a3)                  ; flags
        bne     .bad
        cmpi.w  #14,24(a3)              ; base level
        bhi     .bad
        cmp.l   28(a3),d4               ; blocks follow each other
        bne     .bad
        move.l  32(a3),d6               ; block length: even, 2..8192
        btst    #0,d6
        bne     .bad
        cmpi.l  #2,d6
        bcs     .bad
        cmpi.l  #8192,d6
        bhi     .bad
        tst.b   (a3)                    ; name: 1..24 characters $20..$7e, NUL padded
        beq     .bad
        movea.l a3,a0
        moveq   #23,d7
.nm:    move.b  (a0)+,d0
        beq.s   .nn
        cmpi.b  #$20,d0
        bcs     .bad
        cmpi.b  #$7e,d0
        bhi     .bad
.nn:    dbra    d7,.nm
        move.l  d4,d0
        add.l   d6,d0
        cmp.l   d1,d0                   ; the block lies inside the file
        bhi     .bad
        movea.l a2,a1
        adda.l  d4,a1
        move.l  d6,d3
        subq.w  #1,d3
        moveq   #-1,d0
        bsr     crc_upd                 ; block CRC-32
        not.l   d0
        cmp.l   36(a3),d0
        bne     .crc
        add.l   d6,d4
        lea     40(a3),a3
        dbra    d5,.e
        cmp.l   d1,d4                   ; no bytes after the last block
        bne     .bad
        moveq   #0,d0
        rts
.bad:   moveq   #1,d0
        rts
.crc:   moveq   #2,d0
        rts

crc_tab:                                ; CRC-32 (reflected, $edb88320) table at CPTAB; trashes d0, d2, d3, a0 (not d1: the file size)
        lea     CPTAB.l,a0
        moveq   #0,d3
.i:     move.l  d3,d0
        moveq   #7,d2
.b:     lsr.l   #1,d0
        bcc.s   .n
        eori.l  #$edb88320,d0
.n:     dbra    d2,.b
        move.l  d0,(a0)+
        addq.w  #1,d3
        cmpi.w  #256,d3
        bne.s   .i
        rts

crc_upd:                                ; d0 = crc state, a1 = data, d3.w = length - 1, a6 = CPTAB; trashes d2, a1, d3
.l:     moveq   #0,d2
        move.b  (a1)+,d2
        eor.b   d0,d2
        lsr.l   #8,d0
        lsl.w   #2,d2
        move.l  (a6,d2.w),d2
        eor.l   d2,d0
        dbra    d3,.l
        rts

; ---- strings
h_main: dc.b    13,1,"CAMPAIGN MENU",0
h_play: dc.b    5,3,"PLAY FROM TRACK:",0
t_orig: dc.b    "ORIGINAL GAME",0
t_hd:   dc.b    "LOAD CAMPAIGN FROM HARD DISK",0
t_a:    dc.b    "LOAD CAMPAIGN FROM DRIVE A",0
t_back: dc.b    "BACK TO THE TITLE",0
t_back2: dc.b   "< BACK",0
t_loaded: dc.b  "LOADED CAMPAIGN: ",0
t_tracks: dc.b  " TRACKS",0
t_camp: dc.b    "CAMPAIGN: ",0
t_tracks2: dc.b " TRACKS",0
t_origon: dc.b  "NEXT GAME: THE ORIGINAL 15 TRACKS",0
t_campon: dc.b  "NEXT GAME: THE LOADED CAMPAIGN",0
t_hint: dc.b    "UP/DOWN + RETURN     ESC = BACK",0
m_ldhd: dc.b    "LOADING CAMPAIGN FROM HARD DISK...",0
m_lda:  dc.b    "LOADING CAMPAIGN FROM DRIVE A...",0
m_chk:  dc.b    "CHECKING CAMPAIGN...",0
e_nf:   dc.b    "MSTRACKS.TRK NOT FOUND IN FILES",0
e_nfa:  dc.b    "NO CAMPAIGN DISK IN DRIVE A",0
e_io:   dc.b    "DISK READ ERROR",0
e_big:  dc.b    "CAMPAIGN FILE IS TOO BIG",0
e_na:   dc.b    "FILE ACCESS NOT AVAILABLE HERE",0
e_bad:  dc.b    "NOT A VALID CAMPAIGN FILE",0
e_crc:  dc.b    "CAMPAIGN FILE IS DAMAGED (CRC)",0
p_hd:   dc.b    "MSTRACKS.TRK",0
p_a:    dc.b    "A:\MSTRACKS.TRK",0
        even
pal:    dc.w    $000,$777,$777,$777,$333,$777,$777,$333,$444,$777,$440,$555,$777,$777,$771,$777

; ---- the HAGA-window file reader (work/trackloader/trkread.s, a port of Populous 2 part A/B, work/notes/trackloader.md section 5.2)
;   trk_read: a0 = path (NUL terminated), a1 = destination, d1 = maximum bytes (supervisor mode, any game context)
;   -> d0 = 0 ok | GEMDOS error (negative) | $cd too long | $dd short read | -1 HAGA not recognised (nothing done), d1 = bytes read; every other register preserved
BSZ     equ     $d00
V_RET   equ     $000-BSZ
V_A7    equ     $004-BSZ
V_USP   equ     $008-BSZ
V_BASE  equ     $00c-BSZ
V_BUF   equ     $010-BSZ
V_LEN   equ     $014-BSZ
V_RES0  equ     $018-BSZ
V_RES1  equ     $01c-BSZ
V_SR    equ     $024-BSZ
V_H     equ     $028-BSZ
V_CRIT  equ     $02c-BSZ
V_MAGIC equ     $038-BSZ
V_PATH  equ     $080-BSZ
USPTOP  equ     $500-BSZ
SSPTOP  equ     $d00-BSZ
BOUNCE  equ     $1400-BSZ
BSIZE   equ     $2000
BLK     equ     $3900           ; offset from HAGA's base: above everything HAGA uses

trk_read:
        movem.l d2/a2-a4,-(a7)
        movea.l a0,a3
        movea.l $2dc.w,a2               ; HAGA's base
        move.l  a2,d2
        cmpi.l  #$100000,d2
        bcs.s   .fail
        btst    #0,d2
        bne.s   .fail
        cmpi.l  #$4dfa1c04,$17be(a2)    ; HAGA's three routines, by signature
        bne.s   .fail
        cmpi.l  #$45fa0e1e,$1166(a2)
        bne.s   .fail
        cmpi.l  #$123aed0f,$1372(a2)
        bne.s   .fail
        cmpi.b  #4,$83(a2)              ; machine type 4 (Falcon) swaps differently: refused
        beq.s   .fail
        lea     BLK(a2),a4
        cmpi.l  #'MSTK',V_MAGIC+BSZ(a4)
        beq.s   .have
        movea.l a4,a2
        move.w  #BSZ/4-1,d2
.z:     clr.l   (a2)+
        dbra    d2,.z
        lea     bstart(pc),a0
        move.w  #(bend-bstart)/4+1,d2
.c:     move.l  (a0)+,(a2)+
        dbra    d2,.c
        move.l  #'MSTK',V_MAGIC+BSZ(a4)
.have:  lea     BSZ(a4),a4
        movea.l a3,a0
        jsr     (a4)
        movem.l (a7)+,d2/a2-a4
        rts
.fail:  moveq   #-1,d0
        moveq   #0,d1
        movem.l (a7)+,d2/a2-a4
        rts

        even
bstart: movem.l d2-d7/a0-a6,-(a7)
        lea     bstart(pc),a5
        move.l  d1,V_LEN(a5)
        move.l  a1,V_BUF(a5)
        moveq   #-1,d2
        move.l  d2,V_RES0(a5)
        clr.l   V_RES1(a5)
        movea.l $2dc.w,a2
        move.l  a2,V_BASE(a5)
        lea     V_PATH(a5),a1
        lea     V_PATH+$78(a5),a2
.cp:    move.b  (a0)+,d0
        cmpa.l  a2,a1
        bcc.s   .cpd
        move.b  d0,(a1)+
        bne.s   .cp
        bra.s   .go
.cpd:   clr.b   (a1)
.go:    movea.l V_BASE(a5),a2
        tst.b   $af(a2)                 ; HAGA's no-swap flag: plain traps
        bne.s   .direct
        bsr.w   run
        bra.s   .o1
.direct:bsr.w   body
.o1:    lea     bstart(pc),a5
        move.l  V_RES1(a5),d1
        move.l  V_RES0(a5),d0
        movem.l (a7)+,d2-d7/a0-a6
        rts

run:    move.l  (a7)+,V_RET(a5)
        move.w  sr,V_SR(a5)
        move.w  #$2700,sr
        move.l  a7,V_A7(a5)
        move    usp,a0
        move.l  a0,V_USP(a5)
        lea     USPTOP(a5),a0
        move    a0,usp
        lea     SSPTOP(a5),a7
        movea.l V_BASE(a5),a0
        jsr     $17be(a0)
        lea     bstart(pc),a5
        movea.l V_BASE(a5),a0
        jsr     $1166(a0)
        lea     bstart(pc),a5
        bsr.w   body
        lea     bstart(pc),a5
        move.w  #$2700,sr
        movea.l V_BASE(a5),a0
        jsr     $1372(a0)
        lea     bstart(pc),a5
        movea.l V_BASE(a5),a6
        lea     $33c4(a6),a6
        lea     $fffffa07.l,a1
        move.b  (a6)+,(a1)
        addq.l  #2,a1
        move.b  (a6)+,(a1)
        lea     $a(a1),a1
        move.b  (a6)+,(a1)
        addq.l  #2,a1
        move.b  (a6),(a1)
        movea.l V_USP(a5),a0
        move    a0,usp
        movea.l V_A7(a5),a7
.k:     btst    #0,$fffffc00.l          ; drain the IKBD ACIA
        beq.s   .k2
        tst.b   $fffffc02.l
        bra.s   .k
.k2:    clr.b   $6102.l                 ; Moonshine's IKBD parser ($cfb4) back to idle
        clr.b   $6103.l
        clr.b   $610e.l
        movea.l V_RET(a5),a0
        move.w  V_SR(a5),sr
        jmp     (a0)

body:   move.l  $404.w,V_CRIT(a5)
        lea     crit(pc),a0
        move.l  a0,$404.w
        bsr.s   body1
        move.l  V_CRIT(a5),$404.w
        rts
crit:   move.w  4(a7),d0
        ext.l   d0
        rts

body1:  bsr.w   forget
        bsr.w   fopen
        ext.l   d0
        bmi.w   e0
        move.w  d0,V_H(a5)
        moveq   #0,d6
        bsr.w   fsize
        move.l  d0,d4
        bpl.s   .s1
        move.l  d0,d6
        bra.s   .cl
.s1:    cmp.l   V_LEN(a5),d4
        bls.s   .s2
        move.l  d4,V_RES1(a5)
        move.l  #$cd,d6
        bra.s   .cl
.s2:    move.l  d4,V_RES1(a5)
        bsr.w   frewind
        tst.l   d0
        bpl.s   .s3
        move.l  d0,d6
        bra.s   .cl
.s3:    bsr.w   rdloop
        cmp.l   d4,d0
        beq.s   .cl
        tst.l   d0
        bmi.s   .re
        move.l  #$dd,d0
.re:    move.l  d0,d6
.cl:    bsr.w   fclose
        move.l  d6,V_RES0(a5)
        rts
e0:     move.l  d0,V_RES0(a5)
        rts

rdloop: move.l  d4,d5
        movea.l V_BUF(a5),a4
.l:     tst.l   d5
        ble.s   .done
        move.l  d5,d3
        cmpi.l  #BSIZE,d3
        ble.s   .c
        move.l  #BSIZE,d3
.c:     pea     BOUNCE(a5)
        move.l  d3,-(a7)
        move.w  V_H(a5),-(a7)
        move.w  #$3f,-(a7)              ; Fread
        trap    #1
        lea     12(a7),a7
        cmp.l   d3,d0
        bne.s   .bad
        lea     BOUNCE(a5),a0
        movea.l a4,a1
        move.l  d3,d2
        bsr.w   copy
        adda.l  d3,a4
        sub.l   d3,d5
        bra.s   .l
.done:  move.l  d4,d0
        rts
.bad:   tst.l   d0
        bmi.s   .r
        move.l  d4,d1
        sub.l   d5,d1
        move.l  d1,d0
        add.l   d0,d0
        addq.l  #1,d0
.r:     rts

copy:   move.l  d2,d0
        lsr.l   #2,d0
        beq.s   .t
        subq.l  #1,d0
.q:     move.l  (a0)+,(a1)+
        dbra    d0,.q
.t:     andi.w  #3,d2
        beq.s   .x
        subq.w  #1,d2
.b:     move.b  (a0)+,(a1)+
        dbra    d2,.b
.x:     rts

fopen:  clr.w   -(a7)
        pea     V_PATH(a5)
        move.w  #$3d,-(a7)
        trap    #1
        addq.l  #8,a7
        rts
fclose: move.w  V_H(a5),-(a7)
        move.w  #$3e,-(a7)
        trap    #1
        addq.l  #4,a7
        rts
fsize:  move.w  #2,-(a7)
        move.w  V_H(a5),-(a7)
        clr.l   -(a7)
        move.w  #$42,-(a7)
        trap    #1
        lea     10(a7),a7
        rts
frewind:clr.w   -(a7)
        move.w  V_H(a5),-(a7)
        clr.l   -(a7)
        move.w  #$42,-(a7)
        trap    #1
        lea     10(a7),a7
        rts

; TOS's disk change detection does not run while the game owns the interrupts: forget every BIOS cache buffer of drives A: and B: so GEMDOS re-reads the FAT / directory of the disk in the drive now.
forget: lea     $4b2.w,a0
        moveq   #1,d1
.l1:    movea.l (a0)+,a1
.l2:    move.l  a1,d0
        beq.s   .l4
        cmpi.w  #1,4(a1)
        bhi.s   .l3
        move.w  #-1,4(a1)
.l3:    movea.l (a1),a1
        bra.s   .l2
.l4:    dbra    d1,.l1
        rts
        even
bend:   dc.w    0
