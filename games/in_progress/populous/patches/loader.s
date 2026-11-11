; loader.s - the Populous launcher, replacing the original AUTO\LOADER.PRG (616 bytes; PP carries it LZ-packed
; inside his POLA program and runs it as the process of RUNME).  Same job (and, for the HD build, the same
; memory footprint: text $240, no data, no bss), plus the patch hook:
;
;   Mshrink own block, black palette, then for DEMO.TOS and POPULOUS.TOS:
;       Pexec(3) (load + relocate, do not start)  ->  payload apply (patches/core.s)  ->  Pexec(4) (start)
;   The original called Pexec(0, "demo.tos") and Pexec(0, "populous.tos") with the command line
;   `$20 "1"` (the second one with the first program's exit code + '0' as its digit).
;
; If the payload (magic 'POPP' at $B3000) is absent, or Pexec(3) fails, the program is started
; with Pexec(0) exactly as the original did.
;
; Assembled by poppatch.py with -Ftos; position independent (no relocations).  FLOPPY equ 1 builds the
; AUTO\LOADER.PRG of the floppy disk (see the FLOPPY parts below); PSPAN = payload span in bytes.
;
; Memory layout: DEMO.TOS / POPULOUS.TOS must get their base page at $ac96 (text base $ad96): the game's
; absolute addresses, and so every patch site, assume it.  In the stock HD game the loader process is RUNME's;
; its block B..B+$340 ends at $ac92, the environment copy takes 4 bytes and the base page follows.  The Mshrink size
; therefore makes the loader's block end exactly at $ac92 whatever B is (RUNME started from the desktop, from an
; AUTO folder, another TOS), as long as B + the minimum size does not pass it; otherwise the minimum is used and
; the payload reports 'POPT' (text base mismatch) instead of patching.
PAYLOAD equ     $b3000
NOMBP   equ     $ac92                   ; end of the loader block in the stock layout (B + $340); the game base page follows at +4: $ac96

start:  movea.l 4(a7),a3                ; base page of this process
        ifd     FLOPPY
        lea     $100(a3),a7             ; stack in the base page's unused command-line area, just below the text
        else
        lea     stack(pc),a7
        endc
        move.l  #NOMBP,d0
        sub.l   a3,d0                   ; block size that ends at the game's base page
        cmpi.l  #MINSIZE,d0
        bge.s   .m1
        move.l  #MINSIZE,d0
.m1:    move.l  d0,-(a7)
        move.l  a3,-(a7)
        clr.w   -(a7)
        move.w  #$4a,-(a7)              ; Mshrink(0, base page, size)
        trap    #1
        lea     12(a7),a7
        moveq   #0,d7
.col:   clr.w   -(a7)
        move.w  d7,-(a7)
        move.w  #7,-(a7)                ; Setcolor(d7, 0)
        trap    #14
        addq.l  #6,a7
        addq.w  #1,d7
        cmpi.b  #$10,d7
        bne.s   .col
        lea     nDemo(pc),a4
        moveq   #0,d3
        bsr.s   run                     ; DEMO.TOS
        addi.b  #$30,d0
        lea     cmd(pc),a0
        move.b  d0,1(a0)                ; its exit code becomes the digit of the command line
        lea     nGame(pc),a4
        moveq   #1,d3
        bsr.s   run                     ; POPULOUS.TOS
        ifd     FLOPPY
        clr.w   -(a7)                   ; the disk's AUTO program: back to TOS instead of a return into nowhere
        trap    #1
        else
        rts
        endc

; run: a4 = file name, d3 = program number (payload table). Returns Pexec's exit code in d0.
run:    pea     env(pc)
        pea     cmd(pc)
        move.l  a4,-(a7)
        move.w  #3,-(a7)                ; load, do not start
        move.w  #$4b,-(a7)
        trap    #1
        lea     16(a7),a7
        tst.l   d0
        ble.w   .mode0                  ; failed: the original call
        movea.l d0,a5                   ; the new base page
        movea.l $2c(a5),a6              ; its environment block (Pexec(3) made a copy)
        ifd     FLOPPY
; The loaded program owns the whole free memory, and Pexec has just cleared it, so the payload can only be
; put in after the load, and its place must be kept away from the game: shrink the program's block to end at
; $b3000, then Malloc the payload block, which GEMDOS gives out at exactly that address.
        moveq   #0,d5                   ; payload block (0 = none)
        move.l  #PAYLOAD,d0
        sub.l   a5,d0
        ble.w   .go
        move.l  d0,-(a7)
        move.l  a5,-(a7)
        clr.w   -(a7)
        move.w  #$4a,-(a7)              ; Mshrink(0, base page, PAYLOAD - base page)
        trap    #1
        lea     12(a7),a7
        tst.l   d0
        bne.w   .go
        move.l  #PSPAN,-(a7)
        move.w  #$48,-(a7)              ; Malloc(span)
        trap    #1
        addq.l  #6,a7
        move.l  d0,d5
        cmpi.l  #PAYLOAD,d0
        beq.s   .got
        tst.l   d0                      ; some other address: give it back, run unpatched
        ble.s   .none
        move.l  d0,-(a7)
        move.w  #$49,-(a7)
        trap    #1
        addq.l  #6,a7
.none:  moveq   #0,d5
        bra.w   .go
.got:   bsr.w   readpay
        endc
        cmpi.l  #'POPP',PAYLOAD.l
        bne.s   .go
        move.w  d3,d0
        movea.l a5,a1
        jsr     PAYLOAD+$10.l           ; apply (all registers kept)
.go:    clr.l   -(a7)
        move.l  a5,-(a7)
        clr.l   -(a7)
        move.w  #4,-(a7)                ; just go
        move.w  #$4b,-(a7)
        trap    #1
        lea     16(a7),a7
        move.l  d0,d4                   ; exit code
        move.l  a5,-(a7)                ; mode 3 leaves the memory to the loader: give it back (Mfree)
        move.w  #$49,-(a7)
        trap    #1
        addq.l  #6,a7
        move.l  a6,d0
        beq.s   .nf
        move.l  a6,-(a7)
        move.w  #$49,-(a7)
        trap    #1
        addq.l  #6,a7
.nf:    ifd     FLOPPY
        move.l  d5,d0
        beq.s   .np
        move.l  d5,-(a7)
        move.w  #$49,-(a7)
        trap    #1
        addq.l  #6,a7
.np:    endc
        move.l  d4,d0
        rts
.mode0: pea     env(pc)
        pea     cmd(pc)
        move.l  a4,-(a7)
        clr.w   -(a7)
        move.w  #$4b,-(a7)
        trap    #1
        lea     16(a7),a7
        rts

        ifd     FLOPPY
; readpay: the payload is stored raw on side 1 of the disk, in the track-sides 52.. that the original disk
; leaves formatted-empty (POM sectors 520-779).  Track 52 holds the directory:
;   'POPD', nseg.w, nseg * {dest.l, len.l, first track.w}
; and every segment occupies whole track-sides (10 sectors) from its first track.  The directory is read into
; the last 512 bytes of the payload block first.  Uses a3, a4, d1, d4, d6, d7 (and what the traps clobber).
readpay:
        movea.l #PAYLOAD+PSPAN-512,a3
        moveq   #52,d6
        moveq   #1,d1
        bsr.s   rd
        cmpi.l  #'POPD',(a3)
        bne.s   .x
        move.w  4(a3),d7                ; segments
        lea     6(a3),a4
.seg:   subq.w  #1,d7
        bmi.s   .x
        movea.l (a4)+,a3                ; dest
        move.l  (a4)+,d4                ; len
        move.w  (a4)+,d6                ; first track
.trk:   tst.l   d4
        ble.s   .seg
        move.l  d4,d1
        addi.l  #511,d1
        lsr.l   #8,d1
        lsr.l   #1,d1                   ; sectors
        cmpi.w  #10,d1
        bls.s   .c
        moveq   #10,d1
.c:     bsr.s   rd
        lea     5120(a3),a3
        addq.w  #1,d6
        subi.l  #5120,d4
        bra.s   .trk
.x:     rts
; rd: Floprd(a3, 0, drive A, sector 1, track d6, side 1, d1 sectors)
rd:     move.w  d1,-(a7)
        move.w  #1,-(a7)
        move.w  d6,-(a7)
        move.w  #1,-(a7)
        clr.w   -(a7)
        clr.l   -(a7)
        move.l  a3,-(a7)
        move.w  #8,-(a7)
        trap    #14
        lea     20(a7),a7
        rts
        endc

nDemo:  dc.b    'demo.tos',0
nGame:  dc.b    'populous.tos',0
cmd:    dc.b    $20,'1',0
env:    dc.b    0,0,0,0
        even
        ifnd    FLOPPY
        ds.b    $240-(*-start)          ; pad to the stock text size
        endc
stack:
MINSIZE equ     stack-start+$100        ; text + base page: the smallest block the loader can live in
