; name: pop2_save
; default: yes
; site: $2cc58
; orig: 4eb900036efc
; doc: in-game SAVE GAME / LOAD GAME and the saved-games list work: on a hard disk the saves are *.GAM files (56,690 bytes) in the game's FILES folder (or the drawer you type); on the floppy a separate formatted save disk goes in drive A when the game asks (Populous2_save.st: 12 saves)
; note: Part 1 of 3 (read) + the shared blob of the in-game SAVE/LOAD fix; pop2_save_w (write, $2cbe4) and pop2_save_d (directory, $2cb0e) point at the
; note: same blob and ship together.  PP's `jmp $140` replaced the game's whole disk layer $36efc (a command dispatcher, d0 = 0 read / 1 write / 2 delete /
; note: 3 directory / 4 format / 5 raw sectors, a0 = name, a1 = buffer, d1 = length, over a FAT12 + raw-FDC driver) by a stub that only copies "data file N" out of
; note: P2D, so SAVE GAME / LOAD GAME crashed (work/notes/disks.md).  The game calls the layer from exactly four places; $2cd1a is the data-file loader (left to PP's stub),
; note: the other three are retargeted here: $2cb0e (d0 = 3, directory), $2cbe4 (d0 = 1, write 56,690 B from $39630), $2cc58 (d0 = 0, read 56,690 B to $39630).
; note: The blob is the game's disk layer re-done on GEMDOS, same registers in and out (d0 = 0 ok / else error, d1 = bytes or record count, every other
; note: register kept): read = Fopen / Fseek (size must be exactly $dd72) / Fread / Fclose, write = Fcreate / Fwrite / Fclose (a short write deletes the partial file) + Dfree,
; note: directory = Fsfirst / Fsnext of *.GAM with $dd72 bytes, delivered as the game's own 32-byte records ($fd, $0b, 11-char name).  Any error returns d0 != 0, which the
; note: game's own code turns into its "DISK FILE ERROR" box and a return to the requester.  The name is the game's "drawer\NAME.GAM" string, spaces dropped, upper-cased,
; note: 8.3 trimmed, '/' = '\'; with the default empty drawer the file is relative to the current folder: FILES\ (the folder PP's RUNME set, next to P2D) on a hard disk.
; note: TOS is not safe to call raw from the game: HAGA's file service wraps every TOS call in (1) all MFP interrupt enables off, (2) a fade to grey, (3) an EXCHANGE of
; note: low RAM with the TOS state it snapshotted when it was loaded (the game owns that RAM and has trashed TOS's variables, the BCBs, the floppy head position),
; note: (4) a private stack and usp; and the reverse after the call.  This blob does exactly that by calling HAGA's own three routines (HAGA is one identical file in every
; note: PP game, base from the pointer at $328 which PP's stub itself uses): +$17be (save + clear the MFP enables), +$1166 (fade + swap TOS in), +$1372 (swap out + fade back), and
; note: replicates the service's own prologue / epilogue (sr / usp / a7 save, private stacks, MFP restore from HAGA's buffer at +$33c4, IKBD drain).  The three routines are
; note: checked by signature before use (and machine type 4 = Falcon is refused: its swap differs); if they do not match, the call fails with d0 != 0.  A raw `trap #1` from game
; note: context dies with an address error (negative control in work/notes/save.md).  If HAGA's flag byte +$af is set (no-swap mode) the GEMDOS calls are made directly.
; note: LAYOUT: part A (payload $80300, game context) installs part B (position independent, template $80400, <= $700 B) into HAGA's own top region, HAGA+$3900.. (above the
; note: TT's PMMU table, below HAGA's 32 KB end) on first use: B = data block (HAGA+$3900, $d00 B: variables, DTA, path, 64 compact names, usp / ssp stacks), then the code, then an 8 KB
; note: bounce buffer.  Why there: the swapped range is machine dependent ($8..$FA28 STE + Hatari drive, $8..$1B6C8 ACSI + HDDRIVER) and on a TT (machine type 5) the first MB is
; note: remapped through the PMMU (game's RAM visible at +$200000 while TOS runs), so nothing of the blob may live in the first MB; transfers go through the bounce buffer (DMA must not
; note: be aimed at the alias), the directory's 32-byte records are expanded after the swap-out, and a TT's Hatari GEMDOS drive finds the DTA through p_run read from PHYSICAL
; note: memory (the game's RAM, not TOS's): the dir call points that word at a fake basepage for its duration (without it the TT's list is empty, work/notes/save.md).
; note: IKBD: a call that starts inside a mouse reply leaves the game's parser $2022 mid-packet (-> index -9 in the VBL jump, address error at $296f): `clr.b $2022` after the swap-out.
; note: CRITIC: TOS's critical error handler ($404) is replaced during the call by a stub returning the error code (the desktop AES one would open an alert from a suspended AES):
; note: a write-protected disk gives the game's DISK FILE ERROR, no alert box (tested on the floppy).
; note: DURABILITY: GEMDOS keeps the directory entry and FAT of a closed file in dirty buffers until they are reused; after every write Dfree (reads the whole FAT, which evicts them)
; note: makes the save durable at once (killing Hatari 1 / 5 / 20 s after a save: clean without it only in 0 of 3, with it 6 of 6, work/notes/save.md).
; note: FLOPPY MODE (Dgetdrv = A: / B: and no drawer typed): the saves go to the root of the disk in the drive, which must be a separate formatted disk (the boot disk has 43 KB free);
; note: no save disk (the root has HAGA, or no room for a save, or the disk cannot be read) -> the game's own message box (call $14b2e as its DISK FILE ERROR path does) "INSERT SAVE DISK",
; note: OK, the call is repeated once for real (one more silent try: the first access after a swap can fail).  TOS's disk change detection does not run while the game owns the
; note: interrupts, so every floppy-mode call first forgets the BIOS cache buffers of A: / B: ($4b2 lists, b_bufdrv = -1) and reads the disk again.  The save disk is not needed
; note: back-and-forth: the game's data is in RAM after the start.  Blob data $81300-$81FFF region is not used any more (the blob lives in HAGA's top region).
BSZ     equ     $d00                    ; data block below the code (the block is HAGA+BLK .. +BLK+BSZ, the code runs at HAGA+BLK+BSZ)
V_RET   equ     $000-BSZ
V_A7    equ     $004-BSZ
V_USP   equ     $008-BSZ
V_BASE  equ     $00c-BSZ
V_BUF   equ     $010-BSZ
V_LEN   equ     $014-BSZ
V_RES0  equ     $018-BSZ
V_RES1  equ     $01c-BSZ
V_ODTA  equ     $020-BSZ
V_SR    equ     $024-BSZ
V_CMD   equ     $026-BSZ
V_H     equ     $028-BSZ
V_CRIT  equ     $02c-BSZ
V_ALIAS equ     $030-BSZ
V_MAGIC equ     $038-BSZ
V_DTA   equ     $040-BSZ                ; 44 bytes
V_DLEN  equ     V_DTA+26
V_FLAGS equ     $03c-BSZ
V_FLOP  equ     V_FLAGS
V_ASKED equ     V_FLAGS+1
V_PROMPT equ    V_FLAGS+2
V_DF    equ     $06c-BSZ                ; 16 bytes: Dfree result
V_ERR   equ     V_DF+8                  ; dir: the first Fsfirst result
V_PDA   equ     V_DF                    ; the TT DTA workaround (dir only, Dfree unused there)
V_PDS   equ     V_DF+4
V_FPD   equ     $3c0-BSZ                ; 64 bytes: a fake basepage, its +$20 = the DTA pointer
V_DNAME equ     V_DTA+30
V_PATH  equ     $080-BSZ                ; 128 bytes
CB      equ     $100-BSZ                ; 64 compact 11-char names (704 B)
USPTOP  equ     $500-BSZ                ; usp stack 256 B below it
SSPTOP  equ     $d00-BSZ                ; = the code start: 2 KB ssp stack below it
BOUNCE  equ     $1400-BSZ               ; 8 KB transfer buffer above the code
BSIZE   equ     $2000
BLK     equ     $3900                   ; block offset from HAGA's base: above everything HAGA uses (the TT's PMMU table ends at +$382f), below its 32 KB end
TMPL    equ     PB+$400                 ; the template of the swap-safe part in the payload
TMPLLEN equ     $700
SAVE    equ     PB+$300
SIZE    equ     $dd72

        org     $2cc58
        jsr     SAVE.l

; ---- part A (payload, game context): install the swap-safe part B into HAGA's top region on first use, then jump to it with every register as the game's
        org     PB+$300
save:   move.l  (a7),-(a7)               ; a slot for the jump target under the return address
        movem.l d0-d1/a0-a2,-(a7)
        lea     fail(pc),a1              ; default target: report an error
        move.l  $328.w,d0                ; HAGA's base, the pointer PP's stub reads
        cmpi.l  #$100000,d0
        bcs.s   .go
        btst    #0,d0
        bne.s   .go
        movea.l d0,a0
        cmpi.l  #$4dfa1c04,$17be(a0)     ; HAGA's three routines, by signature
        bne.s   .go
        cmpi.l  #$45fa0e1e,$1166(a0)
        bne.s   .go
        cmpi.l  #$123aed0f,$1372(a0)
        bne.s   .go
        cmpi.b  #4,$83(a0)               ; machine type 4 (Falcon) remaps differently: not supported
        beq.s   .go
        lea     BLK(a0),a1
        cmpi.l  #'P2SV',V_MAGIC+BSZ(a1)
        beq.s   .have
        movea.l a1,a2
        move.w  #BSZ/4-1,d0
.z:     clr.l   (a2)+
        dbra    d0,.z
        lea     TMPL.l,a0
        move.w  #TMPLLEN/4-1,d0
.c:     move.l  (a0)+,(a2)+
        dbra    d0,.c
        move.l  #'P2SV',V_MAGIC+BSZ(a1)
.have:  lea     BSZ(a1),a1
.go:    move.l  a1,20(a7)
        movem.l (a7)+,d0-d1/a0-a2
        rts
fail:   moveq   #-1,d0
        rts

; ---- part B (template, copied to HAGA+BLK+BSZ; position independent: a5 = its own start, data at negative offsets)
        org     PB+$400
bstart: movem.l d2-d7/a0-a6,-(a7)
        lea     bstart(pc),a5
        move.w  d0,V_CMD(a5)
        move.l  d1,V_LEN(a5)
        move.l  a1,V_BUF(a5)
        moveq   #-1,d2
        move.l  d2,V_RES0(a5)
        clr.l   V_RES1(a5)
        movea.l $328.w,a2
        move.l  a2,V_BASE(a5)
        moveq   #0,d2
        cmpi.b  #5,$83(a2)               ; TT: the swap is a PMMU remap, the game's low MB is at +$200000 while TOS runs
        bne.s   .na
        move.l  #$200000,d2
.na:    tst.b   $af(a2)                  ; HAGA's no-swap mode: plain traps
        beq.s   .al
        moveq   #0,d2
.al:    move.l  d2,V_ALIAS(a5)
        lea     V_PATH(a5),a1
        lea     V_PATH+$78(a5),a2
        bsr.w   cvt                      ; a0 = the game's name (or drawer) -> V_PATH
        cmpi.w  #3,V_CMD(a5)
        bne.s   .go
        lea     V_PATH(a5),a3            ; directory: drawer + '\' + *.GAM
        cmpa.l  a3,a1
        beq.s   .pat
        cmpi.b  #'\',-1(a1)
        beq.s   .pat
        move.b  #'\',(a1)+
.pat:   lea     pat(pc),a0
.cp:    move.b  (a0)+,(a1)+
        bne.s   .cp
.go:    clr.l   V_FLAGS(a5)              ; V_FLOP (floppy mode), V_ASKED (the save-disk prompt was shown), V_PROMPT (the call wants it)
.try:   moveq   #-1,d2
        move.l  d2,V_RES0(a5)
        clr.l   V_RES1(a5)
        movea.l V_BASE(a5),a2
        tst.b   $af(a2)
        bne.s   .direct
        bsr.w   run
        bra.s   .o1
.direct:bsr.w   body
.o1:    lea     bstart(pc),a5
        tst.b   V_PROMPT(a5)             ; floppy: the save disk is not in the drive -> the game's own message box once, then the call again
        beq.s   .out
        clr.b   V_PROMPT(a5)
        move.b  V_ASKED(a5),d0
        cmpi.b  #2,d0
        bcc.s   .out
        addq.b  #1,d0
        move.b  d0,V_ASKED(a5)           ; 1 = box shown; 2 = one more silent try (the first access after a disk swap can fail)
        cmpi.b  #1,d0
        bne.s   .try
        bsr.w   askdisk
        bra.s   .try
.out:   lea     bstart(pc),a5
        cmpi.w  #3,V_CMD(a5)
        bne.s   .ret
        tst.l   V_RES0(a5)
        bne.s   .ret
        move.l  V_RES1(a5),d4            ; directory: expand the compact names into the game's 32-byte records at its buffer
        ble.s   .ret                     ; (the buffer can be in low RAM, which was TOS's during the call)
        lea     CB(a5),a1
        movea.l V_BUF(a5),a0
        subq.w  #1,d4
.r:     movea.l a0,a2
        moveq   #7,d0
.z:     clr.l   (a2)+
        dbra    d0,.z
        move.b  #$fd,(a0)
        move.b  #$0b,1(a0)
        lea     2(a0),a2
        moveq   #10,d0
.c:     move.b  (a1)+,(a2)+
        dbra    d0,.c
        lea     $20(a0),a0
        dbra    d4,.r
.ret:   move.l  V_RES1(a5),d1
        move.l  V_RES0(a5),d0
        movem.l (a7)+,d2-d7/a0-a6
        rts
pat:    dc.b    '*.GAM',0
        even

; a0 = source string, a1 = destination, a2 = limit; drops spaces, upper-cases, '/' -> '\', 8.3 per component.  Leaves a1 at the NUL.
cvt:    moveq   #0,d3
        moveq   #0,d4
.l:     move.b  (a0)+,d0
        beq.s   .done
        cmpi.b  #' ',d0
        beq.s   .l
        cmpa.l  a2,a1
        bcc.s   .done
        cmpi.b  #'/',d0
        bne.s   .a
        moveq   #'\',d0
.a:     cmpi.b  #'\',d0
        beq.s   .sep
        cmpi.b  #':',d0
        beq.s   .sep
        cmpi.b  #'.',d0
        bne.s   .c
        tst.b   d4
        bne.s   .l
        moveq   #1,d4
        moveq   #0,d3
        move.b  d0,(a1)+
        bra.s   .l
.c:     cmpi.b  #'a',d0
        blt.s   .u
        cmpi.b  #'z',d0
        bgt.s   .u
        subi.b  #$20,d0
.u:     tst.b   d4
        bne.s   .e
        cmpi.w  #8,d3
        bge.s   .l
        bra.s   .s
.e:     cmpi.w  #3,d3
        bge.s   .l
.s:     addq.w  #1,d3
        move.b  d0,(a1)+
        bra.s   .l
.sep:   moveq   #0,d3
        moveq   #0,d4
        move.b  d0,(a1)+
        bra.s   .l
.done:  clr.b   (a1)
        rts

; Run `body` inside HAGA's TOS context (what its file service does around every TOS call): sr / usp / a7 saved, MFP enables off, fade, TOS's low RAM
; swapped in on private stacks at IPL 3; and the reverse.  Called with bsr; returns through V_RET.
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
.k:     btst    #0,$fffffc00.l
        beq.s   .k2
        tst.b   $fffffc02.l
        bra.s   .k
.k2:    clr.b   $2022.l                  ; the game's IKBD parser back to idle: a mouse reply cut by the call must not shift the next packet
        movea.l V_RET(a5),a0
        move.w  V_SR(a5),sr
        jmp     (a0)

; The GEMDOS part: V_CMD 0 read, 1 write, 3 directory; sets V_RES0 (0 ok) and V_RES1.  TOS's critical error handler (etv_critic, $404: the desktop's
; AES installs one that opens an alert box) is replaced for the duration by a stub that just returns the error code, so a write-protected or missing
; disk makes the GEMDOS call fail instead of asking the (suspended) AES for a dialog.
body:   move.l  $404.w,V_CRIT(a5)
        lea     crit(pc),a0
        move.l  a0,$404.w
        bsr.s   body1
        move.l  V_CRIT(a5),$404.w
        rts
crit:   move.w  4(a7),d0
        ext.l   d0
        rts
body1:  bsr.w   flopchk
        move.w  V_CMD(a5),d0
        beq.s   rd
        cmpi.w  #1,d0
        beq.s   wr
        cmpi.w  #3,d0
        beq.w   dir
        rts

rd:     bsr.w   fopen
        ext.l   d0
        bmi.w   e0
        move.w  d0,V_H(a5)
        moveq   #0,d6
        bsr.w   fsize
        move.l  d0,d4
        bpl.s   .s1
        move.l  d0,d6
        bra.s   .cl
.s1:    cmp.l   V_LEN(a5),d4             ; the file must be exactly one save
        beq.s   .s2
        move.l  d4,V_RES1(a5)
        move.l  #$cd,d6
        bra.s   .cl
.s2:    bsr.w   frewind
        tst.l   d0
        bpl.s   .s3
        move.l  d0,d6
        bra.s   .cl
.s3:    bsr.w   rdloop
        cmp.l   V_LEN(a5),d0
        beq.s   .cl
        tst.l   d0
        bmi.s   .re
        move.l  #$dd,d0
.re:    move.l  d0,d6
.cl:    bsr.w   fclose
        bra.s   fin

wr:     tst.b   V_FLOP(a5)
        beq.s   .go
        tst.b   V_ASKED(a5)
        bne.s   .go
        bsr.w   savefree                 ; floppy: no room for a save on the disk in the drive -> ask for the save disk
        tst.l   d0
        bpl.s   .go
        st      V_PROMPT(a5)
        move.l  #$dd,V_RES0(a5)
        rts
.go:    bsr.w   fcreate
        ext.l   d0
        bmi.w   e0
        move.w  d0,V_H(a5)
        bsr.w   wrloop
        moveq   #0,d6
        cmp.l   V_LEN(a5),d0
        beq.s   .cl
        tst.l   d0
        bmi.s   .we
        move.l  #$dd,d0
.we:    move.l  d0,d6
.cl:    bsr.w   fclose
        ext.l   d0
        bpl.s   .nc
        tst.l   d6
        bne.s   .nc
        move.l  d0,d6
.nc:    tst.l   d6
        beq.s   .fl
        bsr.w   fdelete                  ; no half saves
.fl:    bsr.w   flush
fin:    move.l  d6,V_RES0(a5)
        bne.s   .x
        move.l  V_LEN(a5),V_RES1(a5)
.x:     rts
e0:     move.l  d0,V_RES0(a5)
        tst.b   V_FLOP(a5)
        beq.s   .x0
        cmpi.l  #-33,d0                  ; file / path not found (a disk without that save), write protected: the game's DISK FILE ERROR is the answer
        beq.s   .x0
        cmpi.l  #-34,d0
        beq.s   .x0
        cmpi.l  #-13,d0
        beq.s   .x0
        st      V_PROMPT(a5)             ; floppy: no disk / unreadable disk -> ask for the save disk
.x0:    rts

; The game's low MB is not where its address says while TOS runs on a TT (V_ALIAS), and a DMA transfer must not be aimed at the alias anyway:
; the data goes through BOUNCE in 8 KB pieces and is moved by the CPU.  d0 = V_LEN if all of it moved, else an error code or a short count.
rdloop: move.l  V_LEN(a5),d4
        movea.l V_BUF(a5),a4
        adda.l  V_ALIAS(a5),a4
.l:     tst.l   d4
        ble.s   .done
        move.l  d4,d3
        cmpi.l  #BSIZE,d3
        ble.s   .c
        move.l  #BSIZE,d3
.c:     pea     BOUNCE(a5)
        move.l  d3,-(a7)
        move.w  V_H(a5),-(a7)
        move.w  #$3f,-(a7)               ; Fread
        trap    #1
        lea     12(a7),a7
        cmp.l   d3,d0
        bne.s   .bad
        lea     BOUNCE(a5),a0
        movea.l a4,a1
        move.l  d3,d2
        bsr.w   copy
        adda.l  d3,a4
        sub.l   d3,d4
        bra.s   .l
.done:  move.l  V_LEN(a5),d0
        rts
.bad:   move.l  V_LEN(a5),d1
        sub.l   d4,d1
        tst.l   d0
        bmi.s   .r
        move.l  d1,d0                    ; bytes moved so far + this short read (never equal to V_LEN)
        add.l   d0,d0
        addq.l  #1,d0
.r:     rts

wrloop: move.l  V_LEN(a5),d4
        movea.l V_BUF(a5),a4
        adda.l  V_ALIAS(a5),a4
.l:     tst.l   d4
        ble.s   .done
        move.l  d4,d3
        cmpi.l  #BSIZE,d3
        ble.s   .c
        move.l  #BSIZE,d3
.c:     movea.l a4,a0
        lea     BOUNCE(a5),a1
        move.l  d3,d2
        bsr.w   copy
        pea     BOUNCE(a5)
        move.l  d3,-(a7)
        move.w  V_H(a5),-(a7)
        move.w  #$40,-(a7)               ; Fwrite
        trap    #1
        lea     12(a7),a7
        cmp.l   d3,d0
        bne.s   .bad
        adda.l  d3,a4
        sub.l   d3,d4
        bra.s   .l
.done:  move.l  V_LEN(a5),d0
        rts
.bad:   tst.l   d0
        bmi.s   .r
        move.l  #$dd,d0                  ; short write = the disk is full
.r:     rts

; d2 bytes from (a0) to (a1) (even addresses)
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
fcreate:clr.w   -(a7)
        pea     V_PATH(a5)
        move.w  #$3c,-(a7)
        trap    #1
        addq.l  #8,a7
        rts
fclose: move.w  V_H(a5),-(a7)
        move.w  #$3e,-(a7)
        trap    #1
        addq.l  #4,a7
        rts
fdelete:pea     V_PATH(a5)
        move.w  #$41,-(a7)
        trap    #1
        addq.l  #6,a7
        rts
fsize:  move.w  #2,-(a7)                 ; Fseek(0, handle, 2): the size
        move.w  V_H(a5),-(a7)
        clr.l   -(a7)
        move.w  #$42,-(a7)
        trap    #1
        lea     10(a7),a7
        rts

; GEMDOS keeps the directory entry and FAT of a just-closed file in dirty disk buffers (written only when a buffer is reused), so a save followed by
; a power-off could lose it: Dfree reads the whole FAT, which evicts (= writes) every dirty buffer.  The drive is the one of the path ("A:" ...) or the current one.
flush:  moveq   #0,d0
        lea     V_PATH(a5),a0
        cmpi.b  #':',1(a0)
        bne.s   .d
        move.b  (a0),d0
        andi.w  #$df,d0
        subi.w  #'A'-1,d0
.d:     move.w  d0,-(a7)
        pea     V_DF(a5)
        move.w  #$36,-(a7)               ; Dfree(buf, drive)
        trap    #1
        addq.l  #8,a7
        rts
frewind:clr.w   -(a7)
        move.w  V_H(a5),-(a7)
        clr.l   -(a7)
        move.w  #$42,-(a7)
        trap    #1
        lea     10(a7),a7
        rts

dir:    clr.l   V_PDA(a5)
        move.l  V_ALIAS(a5),d0           ; TT (PMMU remap): Hatari's GEMDOS emulation finds the DTA through p_run, read from PHYSICAL memory where the
        beq.s   .pd                      ; game's RAM sits, not TOS's: point the game-side copy of p_run at a fake basepage whose +$20 holds V_DTA (restored below;
        movea.l $4f2.w,a0                ; a real TOS reads its own p_run and never looks at it)
        movea.l $28(a0),a0
        adda.l  d0,a0
        move.l  a0,V_PDA(a5)
        move.l  (a0),V_PDS(a5)
        lea     V_FPD(a5),a1
        move.l  a1,(a0)
        lea     V_DTA(a5),a2
        move.l  a2,$20(a1)
.pd:    move.w  #$2f,-(a7)               ; Fgetdta
        trap    #1
        addq.l  #2,a7
        move.l  d0,V_ODTA(a5)
        pea     V_DTA(a5)
        move.w  #$1a,-(a7)               ; Fsetdta
        trap    #1
        addq.l  #6,a7
        lea     CB(a5),a4
        moveq   #0,d4
        clr.w   -(a7)
        pea     V_PATH(a5)
        move.w  #$4e,-(a7)               ; Fsfirst
        trap    #1
        addq.l  #8,a7
        move.l  d0,V_ERR(a5)
.n:     tst.l   d0
        bne.s   .end
        cmpi.l  #SIZE,V_DLEN(a5)         ; only files of exactly one save
        bne.s   .nx
        bsr.s   rec
        cmpi.w  #64,d4
        bcc.s   .end
.nx:    move.w  #$4f,-(a7)               ; Fsnext
        trap    #1
        addq.l  #2,a7
        bra.s   .n
.end:   tst.w   d4                       ; floppy: no save listed -> ask for the save disk, unless the disk in the drive is a valid disk without saves
        bne.s   .rs                      ; (the first Fsfirst failed with "file not found" and the root has no HAGA = not the game disk)
        tst.b   V_FLOP(a5)
        beq.s   .rs
        move.l  V_ERR(a5),d0
        beq.s   .rs
        cmpi.l  #-33,d0
        bne.s   .pr
        clr.w   -(a7)
        pea     hagas(pc)
        move.w  #$4e,-(a7)               ; Fsfirst("\HAGA")
        trap    #1
        addq.l  #8,a7
        tst.l   d0
        bne.s   .rs
.pr:    st      V_PROMPT(a5)
.rs:    move.l  V_ODTA(a5),-(a7)
        move.w  #$1a,-(a7)
        trap    #1
        addq.l  #6,a7
        move.l  V_PDA(a5),d0             ; the TT's p_run word back as it was
        beq.s   .np
        movea.l d0,a0
        move.l  V_PDS(a5),(a0)
.np:    clr.l   V_RES0(a5)
        move.l  d4,V_RES1(a5)
        rts
hagas:  dc.b    '\HAGA',0
        even

; one compact record at a4: 11-char "NAME    GAM"
rec:    movea.l a4,a0
        moveq   #10,d0
.sp:    move.b  #' ',(a0)+
        dbra    d0,.sp
        lea     V_DNAME(a5),a1
        movea.l a4,a0
        moveq   #7,d0
.b:     move.b  (a1)+,d1
        beq.s   .d
        cmpi.b  #'.',d1
        beq.s   .x
        bsr.s   up
        move.b  d1,(a0)+
        dbra    d0,.b
        move.b  (a1)+,d1
        cmpi.b  #'.',d1
        bne.s   .d
.x:     lea     8(a4),a0
        moveq   #2,d0
.e:     move.b  (a1)+,d1
        beq.s   .d
        bsr.s   up
        move.b  d1,(a0)+
        dbra    d0,.e
.d:     lea     11(a4),a4
        addq.w  #1,d4
        rts
up:     cmpi.b  #'a',d1
        blt.s   .r
        cmpi.b  #'z',d1
        bgt.s   .r
        subi.b  #$20,d1
.r:     rts

; ---- floppy mode: the drive in use is A: or B: and the name has no drawer.  The boot disk is full (43 KB free, a save is 56,690 B), so saves live on the
; ---- root of a separate formatted disk.  The name becomes "\NAME.GAM" (the disk in the drive, not the boot disk's FILES folder); where there is no save disk
; ---- (no room for a save, file or listing missing) the game's own message box "INSERT SAVE DISK" is shown once and the call is repeated.
flopchk:tst.b   V_FLOP(a5)
        bne.s   .tick
        lea     V_PATH(a5),a0
.s:     move.b  (a0)+,d0
        beq.s   .def
        cmpi.b  #'\',d0
        beq.s   .r
        cmpi.b  #':',d0
        bne.s   .s
.r:     rts
.def:   move.w  #$19,-(a7)               ; Dgetdrv
        trap    #1
        addq.l  #2,a7
        cmpi.w  #2,d0
        bcc.s   .r
        lea     V_PATH(a5),a0
.e:     tst.b   (a0)+
        bne.s   .e
        movea.l a0,a1
        addq.l  #1,a1
        lea     V_PATH(a5),a2
.m:     move.b  -(a0),-(a1)
        cmpa.l  a2,a0
        bne.s   .m
        move.b  #'\',(a0)
        st      V_FLOP(a5)
; TOS's own disk change detection (a VBL routine watching the write-protect line, plus a timer) does not run while the game owns the interrupts, so GEMDOS would
; keep answering from its cached FAT / directory sectors after the user swapped disks (and write the new disk with the old disk's FAT).  Every floppy-mode call
; therefore forgets all BIOS cache buffers (the two lists at _bufl $4b2, BCB: link.l, drive.w at +4) of drives A: and B: (b_bufdrv = -1) and reads the disk again.
.tick:  lea     $4b2.w,a0
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

; d0 < 0 if the disk in the drive has fewer free bytes than one save (a failing Dfree = 0: the real call will report it)
savefree:clr.w  -(a7)                    ; Dfree(buf, 0 = the current drive)
        pea     V_DF(a5)
        move.w  #$36,-(a7)
        trap    #1
        addq.l  #8,a7
        tst.l   d0
        bne.s   .ok
        lea     V_DF(a5),a0
        move.l  8(a0),d1                 ; bytes per sector
        mulu.w  14(a0),d1                ; x sectors per cluster
        move.l  (a0),d0                  ; free clusters
        mulu.w  d1,d0
        cmp.l   V_LEN(a5),d0
        bcc.s   .ok
        moveq   #-1,d0
        rts
.ok:    moveq   #0,d0
        rts

; game context: the game's own message box ($14b2e, as its DISK FILE ERROR path $15874 calls it: a1 = box layout $1a9bc, a2 = table of text pointers) with an OK button
askdisk:movem.l d0-d7/a0-a6,-(a7)
        clr.l   -(a7)
        lea     msg(pc),a0
        move.l  a0,-(a7)
        movea.l a7,a2
        lea     $1a9bc.l,a1
        jsr     $14b2e.l
        addq.l  #8,a7
        movem.l (a7)+,d0-d7/a0-a6
        rts
msg:    dc.b    'INSERT SAVE DISK',0
        even
