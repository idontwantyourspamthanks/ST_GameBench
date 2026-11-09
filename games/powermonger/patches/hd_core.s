; name: hd_core
; default: no
; init: $bb000
; uinit: $bb004
; data: $bc000 4096
; note: HD build only (pmpatch.py build --hd adds every hd_* patch).  The game loads DATA\*.DAT and saves games with its
;       own FAT12 + FDC driver (work/notes/loading.md section 4).  This blob replaces both with GEMDOS file calls:
;         hd_load   ($bb008)  replaces the by-name file loader $d574 (stage 2) and $57032 (stage 1, one call at $1356):
;                             a0 = "DATA\X.DAT" (0-terminated), a1 = destination; d0 = 0 / Z = ok.  Fopen, Fseek to
;                             the end for the size, Fseek back, Fread, Fclose, relative to the folder the program was
;                             started from (Dgetdrv/Dgetpath in `uinit`, USER mode, before anything is touched).
;         hd_sector ($bb00c)  replaces the sector driver $d9fc, now only used by the save-game disk code
;                             ($1ba72 format, $1bd52 check, $1bd70 load, $1bdfe save): d1 = first sector, d2 = count,
;                             d3.b = 0 read / 1 write / 2 format, a0 = buffer.  The save disk is the file SAVEDISK.DAT
;                             (800 sectors, sector 0 = the game's own "POWE..." boot block) next to DATA\.
;       Around every GEMDOS call: interrupts masked (SR $2700), a private stack in this blob, and TOS's vector table
;       ($8..$3ff, saved by `init` before WAR.PRG ran an instruction of its own) swapped in, the game's swapped out.
;       NOT handled: TOS's own low-RAM state (OS variables, GEMDOS pool, the current-basepage variable p_run is at $5662
;       on TOS 1.62, i.e. inside the first file's destination) and any resident driver code that the game overwrites.
;       Hatari's GEMDOS emulation does not need any of it (it only reads the stacked arguments and warns about the
;       trashed basepage variable); real TOS GEMDOS + hard-disk driver is untested (see work/notes/loading.md section 7).
TVEC    equ $bc000                      ; $3f8 bytes: TOS's vectors $8..$3ff
GVEC    equ $bc400                      ; $3f8 bytes: the game's, while a call is in progress
GSR     equ $bc800                      ; word: the game's SR
GSP     equ $bc804                      ; long: the game's a7
HDBASE  equ $bc840                      ; 64 B: "C:\" or "C:\GAMES\PM\" (drive + Dgetpath of the start folder)
PATHBUF equ $bc880                      ; 128 B: full path of the file in progress
STKTOP  equ $bd000                      ; private stack: $bcc00..$bcfff grows down

        org     $bb000
        bra.w   hd_init                 ; $bb000  init  (supervisor)
        bra.w   hd_uinit                ; $bb004  uinit (user)
        bra.w   hd_load                 ; $bb008
        bra.w   hd_sector               ; $bb00c

; ---- user mode, TOS alive: HDBASE = drive letter, ':' and Dgetpath of the start directory, ending in $5c
hd_uinit:
        movem.l d0-d7/a0-a6,-(a7)
        lea     HDBASE.l,a3
        move.w  #$19,-(a7)              ; Dgetdrv
        trap    #1
        addq.l  #2,a7
        add.b   #'A',d0
        move.b  d0,(a3)+
        move.b  #':',(a3)+
        clr.w   -(a7)                   ; Dgetpath(PATHBUF, 0 = default drive)
        pea     PATHBUF.l
        move.w  #$47,-(a7)
        trap    #1
        addq.l  #8,a7
        lea     PATHBUF.l,a0
        cmpi.b  #$5c,(a0)
        beq.s   .cp
        move.b  #$5c,(a3)+              ; relative or empty path: make it absolute
.cp:    move.b  (a0)+,d0
        beq.s   .tail
        move.b  d0,(a3)+
        bra.s   .cp
.tail:  cmpi.b  #$5c,-1(a3)
        beq.s   .z
        move.b  #$5c,(a3)+
.z:     clr.b   (a3)
        movem.l (a7)+,d0-d7/a0-a6
        rts

; ---- supervisor mode, TOS's vectors installed, nothing of the game run yet: snapshot TOS's world
hd_init:
        movem.l d0-d7/a0-a6,-(a7)
        lea     $8.w,a0
        lea     TVEC.l,a1
        move.w  #(($400-8)/4)-1,d0
.v:     move.l  (a0)+,(a1)+
        dbra    d0,.v
.out:   movem.l (a7)+,d0-d7/a0-a6
        rts

; ---- enter / leave TOS's world.  Called with bsr from the entry code, which has just saved its registers.
; tos_in switches to the private stack: the caller's return address is moved over.
tos_in: move.l  (a7)+,a6                ; return address
        move.w  sr,GSR.l
        ori.w   #$700,sr
        move.l  a7,GSP.l
        lea     STKTOP.l,a7
        lea     $8.w,a0
        lea     GVEC.l,a1
        lea     TVEC.l,a2
        move.w  #(($400-8)/4)-1,d0
.v:     move.l  (a0),(a1)+              ; game's vector -> GVEC
        move.l  (a2)+,(a0)+             ; TOS's vector -> live
        dbra    d0,.v
        jmp     (a6)

tos_out:move.l  (a7)+,a6
        lea     $8.w,a0
        lea     GVEC.l,a1
        move.w  #(($400-8)/4)-1,d0
.v:     move.l  (a1)+,(a0)+
        dbra    d0,.v
        movea.l GSP.l,a7
        move.w  GSR.l,sr
        jmp     (a6)

; ---- hd_load: a0 = name, a1 = destination -> d0 = 0 / Z set on success
hd_load:
        movem.l d1-d7/a0-a6,-(a7)
        movea.l a1,a5                   ; destination (a1 may be the name's own address: stage 1 loads over it)
        lea     PATHBUF.l,a2
        lea     HDBASE.l,a3
.cb:    move.b  (a3)+,(a2)+
        bne.s   .cb
        subq.l  #1,a2
.cn:    move.b  (a0)+,d0
        cmpi.b  #'a',d0
        blo.s   .st
        cmpi.b  #'z',d0
        bhi.s   .st
        subi.b  #$20,d0                 ; the folder holds the names as on the disk: upper case
.st:    move.b  d0,(a2)+
        bne.s   .cn
        bsr.w   tos_in
        moveq   #-1,d5                  ; result: nonzero until proven
        clr.w   -(a7)                   ; Fopen(path, 0)
        pea     PATHBUF.l
        move.w  #$3d,-(a7)
        trap    #1
        addq.l  #8,a7
        move.l  d0,d6                   ; handle (negative: error)
        bmi.s   .end
        move.w  #2,-(a7)                ; Fseek(0, handle, 2): the file size
        move.w  d6,-(a7)
        clr.l   -(a7)
        move.w  #$42,-(a7)
        trap    #1
        lea     10(a7),a7
        move.l  d0,d7
        bmi.s   .cl
        clr.w   -(a7)                   ; Fseek(0, handle, 0)
        move.w  d6,-(a7)
        clr.l   -(a7)
        move.w  #$42,-(a7)
        trap    #1
        lea     10(a7),a7
        move.l  a5,-(a7)                ; Fread(handle, size, destination)
        move.l  d7,-(a7)
        move.w  d6,-(a7)
        move.w  #$3f,-(a7)
        trap    #1
        lea     12(a7),a7
        cmp.l   d7,d0
        bne.s   .cl
        moveq   #0,d5
.cl:    move.w  d6,-(a7)                ; Fclose
        move.w  #$3e,-(a7)
        trap    #1
        addq.l  #4,a7
.end:   bsr.w   tos_out
        move.l  d5,d0
        tst.l   d0
        movem.l (a7)+,d1-d7/a0-a6
        rts

; ---- hd_sector: the save-game disk as a file.  d1 = sector, d2 = count, d3.b = mode, a0 = buffer -> d0 = 0 / Z ok
hd_sector:
        movem.l d1-d7/a0-a6,-(a7)
        moveq   #0,d5
        cmpi.b  #2,d3
        beq.w   .done                   ; format: the game rewrites sector 0 (with the slot flags) right after it
        movea.l a0,a5
        lea     PATHBUF.l,a2
        lea     HDBASE.l,a3
.cb:    move.b  (a3)+,(a2)+
        bne.s   .cb
        subq.l  #1,a2
        lea     sdname(pc),a3
.cn:    move.b  (a3)+,(a2)+
        bne.s   .cn
        andi.l  #$ffff,d2
        andi.l  #$ffff,d1               ; the game's driver only looks at the low words
        move.l  d1,d4
        lsl.l   #8,d4
        add.l   d4,d4                   ; byte offset = sector * 512
        move.l  d2,d7
        lsl.l   #8,d7
        add.l   d7,d7                   ; byte count
        move.b  d3,d1                   ; mode (d1 is free now)
        andi.w  #$ff,d1
        bsr.w   tos_in
        moveq   #-1,d5
        moveq   #0,d0                   ; Fopen mode: 0 read, 2 read/write
        tst.b   d1
        beq.s   .op
        moveq   #2,d0
.op:    move.w  d0,-(a7)
        pea     PATHBUF.l
        move.w  #$3d,-(a7)
        trap    #1
        addq.l  #8,a7
        move.l  d0,d6
        bpl.s   .opened
        tst.b   d1
        beq.s   .end                    ; read of a disk that does not exist
        clr.w   -(a7)                   ; write: Fcreate(path, 0)
        pea     PATHBUF.l
        move.w  #$3c,-(a7)
        trap    #1
        addq.l  #8,a7
        move.l  d0,d6
        bmi.s   .end
.opened:clr.w   -(a7)                   ; Fseek(offset, handle, 0)
        move.w  d6,-(a7)
        move.l  d4,-(a7)
        move.w  #$42,-(a7)
        trap    #1
        lea     10(a7),a7
        tst.l   d0
        bmi.s   .cl
        move.l  a5,-(a7)                ; Fread / Fwrite(handle, count, buffer)
        move.l  d7,-(a7)
        move.w  d6,-(a7)
        move.w  #$3f,d0
        tst.b   d1
        beq.s   .rw
        move.w  #$40,d0
.rw:    move.w  d0,-(a7)
        trap    #1
        lea     12(a7),a7
        cmp.l   d7,d0
        bne.s   .cl
        moveq   #0,d5
.cl:    move.w  d6,-(a7)                ; Fclose
        move.w  #$3e,-(a7)
        trap    #1
        addq.l  #4,a7
.end:   bsr.w   tos_out
.done:  move.l  d5,d0
        tst.l   d0
        movem.l (a7)+,d1-d7/a0-a6
        rts
sdname: dc.b    'SAVEDISK.DAT',0
        even
