; name: pop2_save
; default: no
; site: $2cc58
; orig: 4eb900036efc
; doc: in-game LOAD GAME / SAVE GAME and the saved-game list work on the hard disk: the saves are *.GAM files (56,690 bytes) in the game's folder
; note: Part 1 of 3 (read) + the shared blob of the in-game SAVE/LOAD fix; pop2_save_w (write, $2cbe4) and pop2_save_d (directory, $2cb0e) point at the
; note: same blob and ship together.  PP's `jmp $140` replaced the game's whole disk layer $36efc (a command dispatcher, d0 = 0 read / 1 write / 2 delete /
; note: 3 directory / 4 format / 5 raw sectors, a0 = name, a1 = buffer, d1 = length, over a FAT12 + raw-FDC driver) by a stub that only copies "data file N" out of
; note: P2D, so SAVE GAME / LOAD GAME crashed (work/notes/disks.md).  The game calls the layer from exactly four places; $2cd1a is the data-file loader (left to PP's stub),
; note: the other three are retargeted here: $2cb0e (d0 = 3, directory), $2cbe4 (d0 = 1, write 56,690 B from $39630), $2cc58 (d0 = 0, read 56,690 B to $39630).
; note: The blob is the game's disk layer re-done on GEMDOS, same registers in and out (d0 = 0 ok / else error, d1 = bytes or record count, every other
; note: register kept): read = Fopen / Fseek (size must be exactly $dd72) / Fread / Fclose, write = Fcreate / Fwrite / Fclose (a short write deletes the partial file),
; note: directory = Fsfirst / Fsnext of *.GAM with $dd72 bytes, delivered as the game's own 32-byte records ($fd, $0b, 11-char name).  Any error returns d0 != 0, which the
; note: game's own code turns into its "DISK FILE ERROR" box and a return to the requester.  The name is the game's "drawer\NAME.GAM" string, spaces dropped, upper-cased,
; note: 8.3 trimmed, '/' = '\'; with the default empty drawer the file is relative to the current folder: FILES\ (next to P2D).
; note: TOS is not safe to call raw from the game: HAGA's file service wraps every TOS call in (1) all MFP interrupt enables off, (2) a fade to grey, (3) an EXCHANGE of
; note: low RAM $8..~$10500 with the TOS state it snapshotted when it was loaded (the game owns that RAM and has trashed TOS's variables, the BCBs, the floppy head position),
; note: (4) a private stack and usp; and the reverse after the call.  This blob does exactly that by calling HAGA's own three routines (HAGA is one identical file in every
; note: PP game, base from the pointer at $328 which PP's stub itself uses): +$17be (save + clear the MFP enables), +$1166 (fade + swap TOS in), +$1372 (swap out + fade back), and
; note: replicates the service's own prologue / epilogue (sr / usp / a7 save, private stacks, MFP restore from HAGA's buffer at +$33c4, IKBD drain).  The three routines are
; note: checked by signature before use; if they do not match, the call fails with d0 != 0.  Because the swap goes through TOS's own state, the floppy drive-head
; note: bookkeeping that pop2_floppy_head fixes is unaffected (the game's raw FDC driver is no longer reached by any save/load).  If HAGA's flag byte +$af is set
; note: (HAGA's no-swap mode) the GEMDOS calls are made directly.  Blob $80300.., data $81300-$81FFF (variables, DTA, path, 64 compact names at $81400, usp stack top $81800, ssp stack top $82000: 2 KB).
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
.go:    movea.l V_BASE(a5),a2
        tst.b   $af(a2)
        bne.s   .direct
        bsr.w   run
        bra.s   .out
.direct:bsr.w   body
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
body1:  move.w  V_CMD(a5),d0
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

wr:     bsr.w   fcreate
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
        beq.s   fin
        bsr.w   fdelete                  ; no half saves
fin:    move.l  d6,V_RES0(a5)
        bne.s   .x
        move.l  V_LEN(a5),V_RES1(a5)
.x:     rts
e0:     move.l  d0,V_RES0(a5)
        rts

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
frewind:clr.w   -(a7)
        move.w  V_H(a5),-(a7)
        clr.l   -(a7)
        move.w  #$42,-(a7)
        trap    #1
        lea     10(a7),a7
        rts

dir:    move.w  #$2f,-(a7)               ; Fgetdta
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
.end:   move.l  V_ODTA(a5),-(a7)
        move.w  #$1a,-(a7)
        trap    #1
        addq.l  #6,a7
        clr.l   V_RES0(a5)
        move.l  d4,V_RES1(a5)
        rts

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
