; name: cp_title
; default: yes
; site: $74fe
; orig: 4fef000e6106
; gate: ram2mb
; requires: cp_wrap cp_fetch cp_ptr cp_end cp_start cp_hiscore
; conflicts: mx_pre mf_pre sb_bar
; himem: $100000-$1003FF CRC-32 table (256 longs, built on every load)
; himem: $100400-$1007FF campaign menu scratch (item vectors, line buffer, track texts)
; himem: $110000-$12FFFF campaign file as read (MSTRACKS.TRK, at most 123,496 B)
; himem: $130000-$13FFFF track editor overlay (FILES\MSEDIT.OVL, HD build, read on first use)
; himem: $140000-$1C7FFF track editor work RAM (variables, track model, per-unit arrays, undo history, checkpoints, encode buffer, two screens)
; doc: Campaigns (ST family with 2 MB or more only): F10 on the title screen opens the campaign menu (Original game / Load campaign from the hard disk or from a disk in drive A in the HD release, from a disk in drive A or B in the floppy release / Play from track N); the campaign replaces the 15 tracks.
; note: Campaign feature (HD and floppy builds, one source: `FLOPPY` = 0 / 1 is predefined by msrpatch.py; work/notes/campaign_hd.md, campaign_floppy.md).  This patch holds the menu, the file reader and the validator; the redirect sites are cp_wrap ($72c4), cp_fetch ($77da), cp_ptr ($fda2), cp_end ($731e), cp_start ($7252), cp_hiscore ($8418).
; note: Site $74fe = the shared key exit of the title screen's face/text loop ($7446-$74fc: any key or joystick fire starts the game): `lea $e(a7),a7 / bsr.b $750a` (6 bytes) -> `jmp e1`.  e1 replays both
; note: instructions for every key but F10 (scancode $44 in $60ff).  F10 runs the menu: cp_menu returns 1 = start the game (the exit replayed as the game does it: fade out, carry set), 0 = back to the title
; note: (the title routine $73e6 is entered again with its return address on the stack).  The stack at $74fe holds d7.w and a1/a2/a6 (14 bytes) in the sprite loop but only the return address ($7246) in the
; note: final wait loop ($74dc-$74fc), where the original `lea $e(a7),a7` pops 14 bytes too many: the F10 path tests that and does not pop.
; note: The menu screens use the game's own text routine $12268 (a0 = x,y,text,0; a5 = screen; d4 = colour code $b8; font $190be), the buffer clear $d8e0, the vertical sync $d206 and the palette registers directly.  The
; note: selected row is shown by inverting its 8 pixel rows (palette: black background, white text; inverted: white bar, black text), the headings by clearing bitplane 0 (yellow).  Keys: up/down, Return / Enter / Space, Esc /
; note: Backspace / Left; joystick port 1: up, down, fire.  The campaign file is read by `trk_read`: in the HD build with the HAGA-window reader (a port of Populous 2's part A/B, work/trackloader/trkread.s), in the floppy build with the game's own FDC driver ($cac0, FAT12 root directory, MSTRACKS.TRK stored contiguously) and a disk-present probe; both are validated before anything is used:
; note: magic, version 1, count 1..15, file length, table CRC-32, per entry flags/base/offset/length/name and the block CRC-32; anything else rejects the file with a message (the game stays original).

FL_FAIL equ     CPWORK+$2B0     ; w  floppy reader: unit+1 of the last attempt that found no disk
V_ACT   equ     CPV             ; b  campaign active: the races use it
V_LOADED equ    CPV+1           ; b  a validated campaign is in the store
V_COUNT equ     CPV+2           ; w  number of tracks (1..15)
V_START equ     CPV+6           ; w  position (0-based) of the next new game
V_EDOK  equ     CPV+12          ; b  the track editor overlay is loaded and checked (HD build)
V_WELC  equ     CPV+13          ; b  the welcome screen's hint line is drawn (cleared when the screen is left)
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
        jmp     e3.l            ; $B9F0C: "WELCOME PARTNERS ... PRESS A KEY" screen key wait (cp_welcome, site $7c04)
        jmp     e4.l            ; $B9F12: floppy title screen (cp_flhint, site $7446): the displaced loop-body instructions, then the hint line on both screens

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

; ---- welcome screen key wait (cp_welcome, site $7c04 = `tst.b $60ff.w / beq.b $7c02` of the manual-question routine $7bd0, whose first screen is WELCOME PARTNERS ... PRESS A KEY; any key continues, d0 counts up
; meanwhile as the question's random seed).  First pass of a showing: the hint line F10 = CAMPAIGNS under PRESS A KEY.  F10 opens the campaign menu (not while the screen is still fading in: it stays in $60ff until the fade is
; over); a game start continues as a key does ($7c0a), back shows the screen again (the routine starts over: its pushed d7 is dropped).
e3:     tst.b   IB+4.l                  ; the 2 MB gate: open = the campaigns are in
        bne     .g2
        movea.l $2dc.w,a0               ; closed: a 1 MB ST family machine, or >= 2 MB on a TT / Falcon (HAGA's machine type 4 / 5)
        move.b  $83(a0),d0
        subq.b  #2,d0
        cmpi.b  #1,d0
        bls     .mb1
        bra     .stock
.g2:
        tst.b   V_WELC.l
        bne.s   .h
        st      V_WELC.l
        bsr     hint
.h:     tst.b   $60ff.w
        beq.s   .none
        cmpi.b  #$44,$60ff.w
        bne.s   .key
        tst.w   $3a88.w
        bne.s   .none
        clr.b   $60ff.w
        move.w  d0,-(a7)
        bsr     cp_menu
        tst.w   d0
        beq.s   .back
        move.w  (a7)+,d0
        clr.b   V_WELC.l
        jmp     $7c0a.l
.back:  addq.l  #2,a7
        addq.l  #2,a7
        clr.b   V_WELC.l
        jmp     $7bd0.l
.key:   clr.b   V_WELC.l
        jmp     $7c0a.l
.none:  jmp     $7c02.l
        ; ---- 1 MB: the screen says what 2 MB adds; any key (F10 too) continues as the stock key wait does
.mb1:   tst.b   V_WELC.l
        bne.s   .w1
        st      V_WELC.l
        lea     t_w1mb(pc),a0
        movea.l $1004.w,a5
        move.w  #$78,d4
        jsr     $12268.l
.w1:    tst.b   $60ff.w
        beq.s   .n1
        clr.b   V_WELC.l
        jmp     $7c0a.l
.n1:    jmp     $7c02.l
        ; ---- closed by the machine type (TT / Falcon): the stock key wait, no hint
.stock: tst.b   $60ff.w
        beq.s   .n2
        jmp     $7c0a.l
.n2:    jmp     $7c02.l

; ---- the hint line F10 = CAMPAIGNS (text row 23, the game's text routine) on the screen $1004 points to.  Registers kept.
hint:   movem.l d0-d7/a0-a6,-(a7)
        lea     t_whint(pc),a0
        movea.l $1004.w,a5
        move.w  #$78,d4
        jsr     $12268.l
        movem.l (a7)+,d0-d7/a0-a6
        rts

; ---- floppy title screen (cp_flhint, site $7446 = the first two instructions of the face / text loop body `move.l (a2),$10e8.w / movea.l (a2)+,a0`, executed once per message).  Between two messages the loop clears
; both screens from line 64 down (`jsr $d8ca` at $74c8), so the hint line is drawn at the start of every message, into both screens (they are flipped while the text is typed).  The floppy flow never shows the WELCOME
; PARTNERS screen, so this is where F10 = CAMPAIGNS is told there (the title key exit e1 opens the menu on F10).
e4:     move.l  (a2),$10e8.w            ; the displaced instructions
        movea.l (a2)+,a0
        movem.l d0-d7/a0-a6,-(a7)
        lea     t_whint(pc),a0
        movea.l $1004.w,a5
        move.w  #$78,d4
        jsr     $12268.l
        lea     t_whint(pc),a0
        movea.l $1008.w,a5
        move.w  #$78,d4
        jsr     $12268.l
        movem.l (a7)+,d0-d7/a0-a6
        rts

; ---- the menu.  Returns d0.w = 1 start a game (V_ACT / V_START set), 0 back to the title.
cp_menu:
        movem.l d1-d7/a0-a6,-(a7)
        move.b  $6105.w,M_PJOY.l
        clr.l   M_MSG.l
        clr.w   M_SEL.l
        ifne    FLOPPY
        clr.w   FL_FAIL.l
        endc
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
        ifeq    FLOPPY
        subq.w  #1,d0
        bne.s   .edit                   ; 5 track editor
        endc
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
        ifeq    FLOPPY
.edit:  bsr     ed_load                 ; the overlay, read on first use
        bne     .main                   ; message set
        jsr     EDBASE+16.l             ; the editor: own screen and palette, both given back when it returns; d0 = 0 back, n = play track n-1 of the campaign in memory
        tst.w   d0
        beq     .main
        subq.w  #1,d0
        move.w  d0,V_START.l
        st      V_ACT.l
        moveq   #1,d0
        bra     .out
        endc
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
.nl:
        ifeq    FLOPPY
        lea     t_edit(pc),a0
        moveq   #5,d0
        bsr     addit
        endc
        lea     t_back(pc),a0
        moveq   #4,d0
        bsr     addit
        move.w  d5,M_CNT.l
        move.w  #6,M_ROW0.l
        move.w  #2,M_STEP.l
        cmp.w   M_SEL.l,d5
        bhi.s   .sok
        clr.w   M_SEL.l
.sok:
        ifne    FLOPPY
        lea     t_ins(pc),a0            ; the campaign disk goes in before an item is chosen
        moveq   #2,d0
        moveq   #20,d1
        bsr     putline
        endc
        lea     t_origon(pc),a0         ; status line
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

        ifeq    FLOPPY
; ---- the track editor (HD build; work/notes/editor_design.md): FILES\MSEDIT.OVL (patches/ovl/msedit.s, built by msrpatch.py) is read to EDBASE on first use and checked
; (magic, interface version EDVER, length, CRC-32) before it is ever called.  -> d0 = 0 ready / 1 M_MSG set (Z accordingly)
ed_load:
        tst.b   V_EDOK.l
        bne.s   .ok
        lea     m_lded(pc),a0
        bsr     msg
        lea     p_ed(pc),a0
        lea     EDBASE.l,a1
        move.l  #$10000,d1
        bsr     trk_read                ; d0 = 0 / error, d1 = bytes
        lea     e_ednf(pc),a0
        tst.l   d0
        bne.s   .err
        lea     EDBASE.l,a2
        cmpi.l  #'MSED',(a2)
        bne.s   .bad
        cmpi.w  #EDVER,4(a2)
        bne.s   .bad
        cmp.l   8(a2),d1
        bne.s   .bad
        cmpi.l  #32,d1
        bcs.s   .bad
        bsr     crc_tab                 ; keeps d1
        lea     CPTAB.l,a6
        moveq   #-1,d0
        lea     16(a2),a1
        move.l  d1,d3
        subi.l  #17,d3
        bsr     crc_upd                 ; the image is at most 64 KB
        not.l   d0
        cmp.l   12(a2),d0
        bne.s   .bad
        st      V_EDOK.l
.ok:    moveq   #0,d0
        rts
.bad:   lea     e_edbad(pc),a0
.err:   move.l  a0,M_MSG.l
        moveq   #1,d0
        rts
        endc

; ---- strings
h_main: dc.b    13,1,"CAMPAIGN MENU",0
h_play: dc.b    5,3,"PLAY FROM TRACK:",0
t_orig: dc.b    "ORIGINAL GAME",0
        ifne    FLOPPY
t_hd:   dc.b    "LOAD CAMPAIGN FROM DRIVE A",0
t_a:    dc.b    "LOAD CAMPAIGN FROM DRIVE B",0
        else
t_hd:   dc.b    "LOAD CAMPAIGN FROM HARD DISK",0
t_a:    dc.b    "LOAD CAMPAIGN FROM DRIVE A",0
        endc
t_back: dc.b    "BACK TO THE TITLE",0
t_back2: dc.b   "< BACK",0
t_whint: dc.b   13,23,"F10 = CAMPAIGNS",0
t_w1mb: dc.b    4,23,"2 MB: CAMPAIGNS + TRACK EDITOR",0
t_loaded: dc.b  "LOADED CAMPAIGN: ",0
t_tracks: dc.b  " TRACKS",0
t_camp: dc.b    "CAMPAIGN: ",0
t_tracks2: dc.b " TRACKS",0
t_origon: dc.b  "NEXT GAME: THE ORIGINAL 15 TRACKS",0
t_campon: dc.b  "NEXT GAME: THE LOADED CAMPAIGN",0
        ifne    FLOPPY
t_ins:  dc.b    "INSERT THE CAMPAIGN DISK, THEN CHOOSE",0
        endc
t_hint: dc.b    "UP/DOWN + RETURN     ESC = BACK",0
        ifne    FLOPPY
m_ldhd: dc.b    "LOADING CAMPAIGN FROM DRIVE A...",0
m_lda:  dc.b    "LOADING CAMPAIGN FROM DRIVE B...",0
        else
m_ldhd: dc.b    "LOADING CAMPAIGN FROM HARD DISK...",0
m_lda:  dc.b    "LOADING CAMPAIGN FROM DRIVE A...",0
        endc
m_chk:  dc.b    "CHECKING CAMPAIGN...",0
        ifne    FLOPPY
e_nf:   dc.b    "NO CAMPAIGN DISK IN DRIVE A",0
e_nfa:  dc.b    "NO CAMPAIGN DISK IN DRIVE B",0
        else
e_nf:   dc.b    "MSTRACKS.TRK NOT FOUND IN FILES",0
e_nfa:  dc.b    "NO CAMPAIGN DISK IN DRIVE A",0
        endc
e_io:   dc.b    "DISK READ ERROR",0
e_big:  dc.b    "CAMPAIGN FILE IS TOO BIG",0
e_na:   dc.b    "FILE ACCESS NOT AVAILABLE HERE",0
e_bad:  dc.b    "NOT A VALID CAMPAIGN FILE",0
e_crc:  dc.b    "CAMPAIGN FILE IS DAMAGED (CRC)",0
        ifne    FLOPPY
p_hd:   dc.b    "A:",0
p_a:    dc.b    "B:",0
        else
p_hd:   dc.b    "MSTRACKS.TRK",0
p_a:    dc.b    "A:\MSTRACKS.TRK",0
p_ed:   dc.b    "MSEDIT.OVL",0
t_edit: dc.b    "TRACK EDITOR",0
m_lded: dc.b    "LOADING THE TRACK EDITOR...",0
e_ednf: dc.b    "MSEDIT.OVL NOT FOUND IN FILES",0
e_edbad: dc.b   "EDITOR FILE DAMAGED OR WRONG VERSION",0
        endc
        even
pal:    dc.w    $000,$777,$777,$777,$333,$777,$777,$333,$444,$777,$440,$555,$777,$777,$771,$777

        ifne    FLOPPY
; ---- the floppy reader (work/campfloppy/campread2.s; notes work/notes/campaign_floppy.md): the game's own FDC driver sub_00cac0, FAT12 root directory, MSTRACKS.TRK contiguous
;   trk_read: a0 = "A:" / "B:" (the drive letter picks the unit), a1 = destination, d1 = maximum bytes
;   -> d0 = 0 ok | -33 no usable disk / not a FAT floppy / no MSTRACKS.TRK | 1 read error | $cd too big; d1 = bytes.  Same contract as the HAGA reader of the HD build.
trk_read:
        movem.l d2-d4/a2,-(a7)
        moveq   #0,d0
        cmpi.b  #'B',(a0)
        bne.s   .u
        moveq   #1,d0
.u:     move.w  d0,d3                   ; unit
        lea     FL_FAIL.l,a2
        move.w  (a2),d2
        subq.w  #1,d2
        cmp.w   d0,d2
        seq     d2
        andi.w  #$ff,d2                 ; the previous attempt on THIS drive found no disk: do not probe, let the driver try
        movea.l a1,a0
        bsr.s   camp_read               ; d0.w status 0..5, d1.l size
        clr.w   (a2)
        moveq   #0,d4
        tst.w   d0
        beq.s   .x
        moveq   #1,d4                   ; 2 read error
        cmpi.w  #2,d0
        beq.s   .x
        move.l  #$cd,d4                 ; 5 too big
        cmpi.w  #5,d0
        beq.s   .x
        moveq   #-33,d4                 ; 1 no disk (probe), 3 not a FAT floppy, 4 no MSTRACKS.TRK
        cmpi.w  #1,d0
        bne.s   .x
        addq.w  #1,d3
        move.w  d3,(a2)
.x:     move.l  d4,d0
        movem.l (a7)+,d2-d4/a2
        rts

vars:   dc.w    0               ; v_unit
        dc.w    9               ; v_spt
        dc.w    2               ; v_spc
        dc.w    7               ; v_nroot
        dc.l    0               ; v_dest
        dc.l    0               ; v_max
        dc.l    0               ; v_size
        dc.l    0               ; v_root
        dc.l    0               ; v_data0
v_unit equ 0
v_spt equ 2
v_spc equ 4
v_nroot equ 6
v_dest equ 8
v_max equ 12
v_size equ 16
v_root equ 20
v_data0 equ 24

camp_read:
        movem.l d2-d7/a2-a6,-(sp)
        lea     vars(pc),a5
        move.w  d0,v_unit(a5)
        move.l  a0,v_dest(a5)
        move.l  d1,v_max(a5)
        clr.l   v_size(a5)
        move.w  #9,v_spt(a5)
        moveq   #1,d7                   ; status: no disk
        tst.w   d2
        bne.s   .skp                    ; a retry after status 1: the probe may be wrong on this hardware, let the driver try (its own bounded waits, 13 s at worst)
        bsr     dpres
        tst.w   d0
        bne     .out
.skp:
        moveq   #2,d7                   ; status: read error
        moveq   #0,d0                   ; boot sector
        moveq   #1,d1
        movea.l v_dest(a5),a0
        bsr     rdsec
        bne     .out
        moveq   #3,d7                   ; status: not a FAT floppy
        movea.l v_dest(a5),a1
        tst.b   11(a1)                  ; bytes per sector = $0200 (little endian)
        bne     .out
        cmpi.b  #2,12(a1)
        bne     .out
        moveq   #0,d0
        move.b  25(a1),d0
        lsl.w   #8,d0
        move.b  24(a1),d0               ; sectors per track
        cmpi.w  #9,d0
        blt     .out
        cmpi.w  #11,d0
        bgt     .out
        move.w  d0,v_spt(a5)
        moveq   #0,d2
        move.b  13(a1),d2               ; sectors per cluster
        beq     .out
        move.w  d2,v_spc(a5)
        moveq   #0,d3
        move.b  15(a1),d3
        lsl.w   #8,d3
        move.b  14(a1),d3               ; reserved sectors
        moveq   #0,d4
        move.b  16(a1),d4               ; FATs
        beq     .out
        moveq   #0,d5
        move.b  23(a1),d5
        lsl.w   #8,d5
        move.b  22(a1),d5               ; sectors per FAT
        mulu.w  d5,d4
        add.l   d4,d3                   ; root directory LBA
        move.l  d3,v_root(a5)
        moveq   #0,d6
        move.b  18(a1),d6
        lsl.w   #8,d6
        move.b  17(a1),d6               ; root entries
        add.w   #15,d6
        lsr.w   #4,d6                   ; root directory sectors
        move.w  d6,v_nroot(a5)
        add.l   d6,d3
        move.l  d3,v_data0(a5)          ; first data sector (cluster 2)
        moveq   #4,d7                   ; status: file not found
        move.l  v_root(a5),d5
        move.w  v_nroot(a5),d6
        beq     .out
        subq.w  #1,d6
.rs:    move.l  d5,d0
        moveq   #1,d1
        movea.l v_dest(a5),a0
        bsr     rdsec
        beq.s   .rok
        moveq   #2,d7
        bra     .out
.rok:   movea.l v_dest(a5),a1
        moveq   #15,d2
.re:    tst.b   (a1)
        beq     .nf                     ; end of the directory
        cmpi.b  #$e5,(a1)
        beq.s   .nx
        move.b  11(a1),d0
        andi.b  #$18,d0                 ; volume label / directory
        bne.s   .nx
        lea     fname(pc),a2
        movea.l a1,a3
        moveq   #10,d1
.cm:    cmpm.b  (a2)+,(a3)+
        dbne    d1,.cm
        beq.s   .found
.nx:    lea     32(a1),a1
        dbra    d2,.re
        addq.l  #1,d5
        dbra    d6,.rs
.nf:    moveq   #4,d7
        bra     .out
.found: moveq   #0,d0
        move.b  27(a1),d0
        lsl.w   #8,d0
        move.b  26(a1),d0               ; first cluster
        moveq   #0,d1
        move.b  31(a1),d1
        lsl.l   #8,d1
        move.b  30(a1),d1
        lsl.l   #8,d1
        move.b  29(a1),d1
        lsl.l   #8,d1
        move.b  28(a1),d1               ; size
        moveq   #5,d7
        cmp.l   v_max(a5),d1
        bhi     .out
        moveq   #4,d7
        cmpi.l  #16,d1
        bcs     .out
        subq.w  #2,d0
        bcs     .out
        move.l  d1,v_size(a5)
        mulu.w  v_spc(a5),d0
        add.l   v_data0(a5),d0          ; file LBA
        addi.l  #511,d1
        lsr.l   #8,d1
        lsr.l   #1,d1                   ; sectors
        movea.l v_dest(a5),a0
        moveq   #2,d7
        bsr     rdsec
        bne     .out
        moveq   #0,d7
.out:
cr_exit: move.w d7,d0
        move.l  v_size(a5),d1
        movem.l (sp)+,d2-d7/a2-a6
        rts

; rdsec: d0.l = LBA (TOS order: track*sides*spt + side*spt + sector), d1.l = sector count, a0 = buffer -> d0 = 0 ok / nonzero error (Z set accordingly); one driver call per track side
rdsec:  movem.l d1-d7/a0-a2,-(sp)
        lea     vars(pc),a2
        move.l  d0,d5
        move.l  d1,d6
.l:     move.l  d5,d0
        divu.w  v_spt(a2),d0            ; low = track*2+side, high = sector in the track
        move.l  d0,d2
        swap    d2
        andi.l  #$ffff,d2               ; sector (0-based)
        andi.l  #$ffff,d0               ; track*2+side
        move.w  v_spt(a2),d4
        sub.w   d2,d4                   ; sectors left on this track side
        cmp.l   d6,d4
        bls.s   .c
        move.l  d6,d4
.c:     move.w  d0,d3
        lsr.w   #1,d3                   ; track
        mulu.w  v_spt(a2),d3
        add.w   d2,d3                   ; the driver's linear sector on this side (track*spt + sector)
        andi.w  #1,d0
        lsl.w   #2,d0
        or.w    v_unit(a2),d0           ; bit 2 = side 1, bit 0 = unit
        moveq   #0,d1
        move.w  v_spt(a2),d1
        swap    d1
        or.l    d1,d0                   ; high word = sectors per track
        moveq   #0,d1
        move.w  d3,d1
        moveq   #0,d2
        move.w  d4,d2
        moveq   #0,d3                   ; command: read
        movem.l d4-d6/a2,-(sp)
        jsr     $cac0.l                 ; the game's FDC driver (the one sole entry sub_00d6fa jumps to)
        movem.l (sp)+,d4-d6/a2
        tst.l   d0
        bne.s   .x
        move.l  d4,d0
        lsl.l   #8,d0
        add.l   d0,d0
        adda.l  d0,a0
        add.l   d4,d5
        sub.l   d4,d6
        bne.s   .l
        moveq   #0,d0
.x:     movem.l (sp)+,d1-d7/a0-a2
        tst.l   d0
        rts

; dpres: is there a disk spinning in drive `v_unit`?  (the logic of fl_driveb's bpres, for either drive)  d0.w = 0 yes, 1 no.  1: restore (no spin-up wait) reaches TR00 without seek error
; within ~1.2 s, 2: an INDEX pulse shows within ~1.5 s.  Without it a drive with no disk would sit in the game's own waits ($60000 / $60000 / $40000 loops: 13 s in Hatari).
dpres:  move.l  d1,-(sp)
        move.w  $43e.w,-(sp)
        st.b    $43e.w
        moveq   #5,d0                   ; PSG port A: drive A, side 0 (active low)
        lea     vars(pc),a0
        tst.w   v_unit(a0)
        beq.s   .a
        moveq   #3,d0                   ; drive B, side 0
.a:     jsr     $cf0e.l
        move.w  #$80,$ff8606.l
        moveq   #$0b,d0                 ; restore, h=1, V=0, 3 ms
        jsr     $cf8e.l
        move.l  #$38000,d1
.w:     btst.b  #5,$fffffa01.w          ; GPIP bit 5 low = FDC interrupt
        beq.s   .d
        subq.l  #1,d1
        bne.s   .w
        jsr     $cf5a.l
        moveq   #1,d0
        bra.s   .o
.d:     jsr     $cf78.l
        btst    #4,d0                   ; seek error
        bne.s   .no
        btst    #2,d0                   ; TR00
        beq.s   .no
        move.l  #$2d00,d1
.ix:    jsr     $cf78.l
        btst    #1,d0                   ; index pulse
        bne.s   .y
        subq.l  #1,d1
        bne.s   .ix
        bra.s   .no
.y:     moveq   #0,d0
        bra.s   .o
.no:    moveq   #1,d0
.o:     move.l  d0,-(sp)
        moveq   #7,d0                   ; deselect
        jsr     $cf0e.l
        move.l  (sp)+,d0
        move.w  (sp)+,$43e.w
        move.l  (sp)+,d1
        rts

fname:  dc.b    "MSTRACKSTRK"
        even
        else
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
        endc
