; campread.s -- SCRATCH PROTOTYPE (MSRCampFloppy): read MSTRACKS.TRK from a FAT12 floppy with the floppy game's OWN FDC driver (sub_00cac0), plus the F10 title hook and the
; swap prompts.  Assembled at ORG = $100000 and loaded into a running game with the Hatari debugger (work/campfloppy/*.py); the final form is a payload patch.
;
; camp_read   in:  d0.w = unit (0 = drive A, 1 = drive B), a0 = destination (even, DMA range < $400000), d1.l = max file size
;             out: d0.w = status, d1.l = file size
;   0 ok | 1 no disk in the drive (no index pulse) | 2 read error | 3 not a FAT floppy this driver reads | 4 no MSTRACKS.TRK in the root dir
;   5 file larger than max | 6 not a campaign file (magic 'MSTK', count 1..15, header length = file size)
; The geometry comes from the disk's BPB (sectors per track 9..11): the game's driver takes the track length from the HIGH word of its device word (9..11, else 10), so the
; 720 KB TOS disk that msrtrack.py makes is read as it is.  FAT chain is NOT followed: the file must be contiguous (the tool writes it that way); a fragmented file fails 6.
ORG     equ     $100000
        org     ORG

ep:     jmp     camp_read(pc)
        jmp     hook_title(pc)
        jmp     camp_ui(pc)

camp_read:
        movem.l d2-d7/a2-a6,-(sp)
        lea     vars(pc),a5
        move.w  d0,v_unit(a5)
        move.l  a0,v_dest(a5)
        move.l  d1,v_max(a5)
        clr.l   v_size(a5)
        move.w  #9,v_spt(a5)
        moveq   #1,d7                   ; status: no disk
        bsr     dpres
        tst.w   d0
        bne     .out
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
        movea.l v_dest(a5),a0
        moveq   #6,d7
        cmpi.l  #'MSTK',(a0)
        bne     .out
        move.w  6(a0),d0
        beq     .out
        cmpi.w  #15,d0
        bhi     .out
        move.l  8(a0),d0
        cmp.l   v_size(a5),d0
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

; ------------------------------------------------------------------------------------------------------- swap prompts (the UI part; the real menu is the shared one)
; showtext: the body of the game's own sub_00735a (fade out, clear, text at the usual place, present, fade in)
showtext:
        movem.l d0-d7/a0-a6,-(sp)       ; the game's routines trash everything (a5 included)
        move.l  a0,-(sp)
        jsr     $d866.l
.f:     tst.w   $3a88.w
        bne.s   .f
        jsr     $d8e0.l
        movea.l (sp)+,a0
        movea.l $1008.w,a5
        lea     $3e91(a5),a3
        move.w  #$78,d4
        jsr     $122a2.l
        jsr     $d1fe.l
        jsr     $d84e.l
        movem.l (sp)+,d0-d7/a0-a6
        rts
; waitkey -> d0.b = scancode ($60ff), the key is consumed
waitkey:
        clr.b   $60ff.w
.k:     move.b  $60ff.w,d0
        beq.s   .k
        clr.b   $60ff.w
        rts
; fadeout: leave the screen the way sub_00735a does
fadeout:
        movem.l d0-d7/a0-a6,-(sp)
        jsr     $d866.l
.f:     tst.w   $3a88.w
        bne.s   .f
        movem.l (sp)+,d0-d7/a0-a6
        rts

; camp_ui: F10 at the title.  Prompt, read, report.  Returns d0.w = 0 loaded / -1 cancelled.  Leaves the screen faded out and cleared (like sub_00735a)
camp_ui:
        movem.l d1-d7/a0-a6,-(sp)
        lea     vars(pc),a5
.ask:   lea     t_ask(pc),a0
        bsr     showtext
.ak:    bsr     waitkey
        cmpi.b  #$01,d0
        beq     .cancel
        moveq   #0,d2
        cmpi.b  #$1e,d0                 ; A
        beq.s   .go
        moveq   #1,d2
        cmpi.b  #$30,d0                 ; B
        bne.s   .ak
.go:    move.w  d2,d6
        lea     t_load(pc),a0
        bsr     showtext
        move.w  d6,d0
        movea.l v_cdest(a5),a0
        move.l  v_cmax(a5),d1
        bsr     camp_read
        move.w  d0,v_status(a5)
        tst.w   d0
        beq.s   .ok
        add.w   d0,d0
        lea     errtab(pc),a0
        move.w  -2(a0,d0.w),d0          ; status 1..6 -> text offset
        lea     errtab(pc),a0
        adda.w  d0,a0
        bsr     showtext
        bsr     waitkey
        bra     .ask
.ok:    clr.b   v_act(a5)
        move.b  #1,v_act(a5)
        movea.l v_cdest(a5),a0
        move.w  6(a0),v_count(a5)
        lea     t_done(pc),a0
        bsr     showtext
        bsr     waitkey
        bsr     fadeout
        moveq   #0,d0
        bra.s   .x
.cancel: bsr    fadeout
        moveq   #-1,d0
.x:     movem.l (sp)+,d1-d7/a0-a6
        rts

; F10 hook for the title: replaces the `jsr $73b8` at $7252 (start of a game).  F10 = scancode $44 left in $60ff by the title loop.
hook_title:
        cmpi.b  #$44,$60ff.w
        bne.s   .go
        movem.l d0-d7/a0-a6,-(sp)
        bsr     camp_ui
        movem.l (sp)+,d0-d7/a0-a6
        addq.l  #4,sp                   ; drop the return address into $7258
        jmp     $723c.l                 ; the title again
.go:    jmp     $73b8.l

fname:  dc.b    "MSTRACKSTRK"
t_ask:  dc.b    "LOAD A CAMPAIGN",13,13,"Insert the campaign disk,",13,"then press A for drive A,",13,"B for drive B, ESC to cancel.",0
t_load: dc.b    "Loading campaign...",0
t_done: dc.b    "Campaign loaded.",13,13,"Press a key.",0
t_e1:   dc.b    "No disk in that drive.",13,13,"Press a key.",0
t_e2:   dc.b    "Disk read error.",13,13,"Press a key.",0
t_e3:   dc.b    "Not a campaign disk.",13,13,"Press a key.",0
t_e4:   dc.b    "No MSTRACKS.TRK on the disk.",13,13,"Press a key.",0
t_e5:   dc.b    "Campaign file too large.",13,13,"Press a key.",0
t_e6:   dc.b    "Not a valid campaign file.",13,13,"Press a key.",0
        even
; status 1..6 -> offset of the text from errtab
errtab: dc.w    t_e1-errtab,t_e2-errtab,t_e3-errtab,t_e4-errtab,t_e5-errtab,t_e6-errtab
vars:   dc.w    0               ; v_unit
        dc.w    9               ; v_spt
        dc.w    2               ; v_spc
        dc.w    7               ; v_nroot
        dc.l    0               ; v_dest
        dc.l    0               ; v_max
        dc.l    0               ; v_size
        dc.l    0               ; v_root
        dc.l    0               ; v_data0
        dc.l    $110000         ; v_cdest: where camp_ui puts the file
        dc.l    $20000          ; v_cmax
        dc.w    0               ; v_status
        dc.w    0               ; v_count
        dc.b    0               ; v_act
        even
v_unit equ 0
v_spt equ 2
v_spc equ 4
v_nroot equ 6
v_dest equ 8
v_max equ 12
v_size equ 16
v_root equ 20
v_data0 equ 24
v_cdest equ 28
v_cmax equ 32
v_status equ 36
v_count equ 38
v_act equ 40
