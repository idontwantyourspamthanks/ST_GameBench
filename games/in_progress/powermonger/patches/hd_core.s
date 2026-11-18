; name: hd_core
; default: no
; init: $bb000
; uinit: $bb004
; data: $bc000 4096
; note: HD build only (pmpatch.py build --hd adds every hd_* patch).  The game loads DATA\*.DAT and saves games with its
;       own FAT12 + FDC driver (work/notes/loading.md section 4).  This blob replaces both with real GEMDOS calls, which
;       works with Hatari's GEMDOS emulation AND with TOS's own GEMDOS + a resident hard-disk driver (ACSI + HDDRIVER).
;         hd_load   ($bb008)  replaces the by-name file loader $d574 (stage 2) and $57032 (stage 1, one call at $1356):
;                             a0 = "DATA\X.DAT" (0-terminated), a1 = destination; d0 = 0 / Z = ok.  Fopen, Fseek to
;                             the end for the size, Fseek back, Fread, Fclose, relative to the folder the program was
;                             started from (Dgetdrv/Dgetpath in `uinit`, USER mode, before anything is touched).
;         hd_sector ($bb00c)  replaces the sector driver $d9fc, now only used by the save-game disk code
;                             ($1ba72 format, $1bd52 check, $1bd70 load, $1bdfe save): d1 = first sector, d2 = count,
;                             d3.b = 0 read / 1 write / 2 format, a0 = buffer.  The save disk is the file SAVEDISK.DAT
;                             (800 sectors, sector 0 = the game's own "POWE..." boot block) next to DATA\.
;       THE TOS REGION.  The game overwrites everything TOS and the driver keep in low RAM: the vectors, the OS variables,
;       the GEMDOS pool, the resident driver, the current-basepage variable and the program's own basepage, i.e. R = [$8,
;       BP + $100) (BP = **(_sysbase + $28) = the basepage of the program started from the AUTO folder; 78640 B on STE /
;       TOS 1.62, 87760 B on Mega STE / TOS 2.06: work/notes/loading.md section 7.1).  `init` (supervisor, before the
;       program ran an instruction of its own) copies R to the swap buffer S ($dd000.., SMAX bytes at most, up to $f6000;
;       $f0000..$f7f45 is never touched by the game or TOS: free-RAM proof, loading.md section 5).  Around every GEMDOS call
;       tos_in EXCHANGES R and S (S then holds the game's bytes), runs with SR $2500 (only the MFP levels), the MFP masked
;       but timer C (so _hz_200 advances for the driver) and the keyboard ACIA (hd_acia queues its bytes, `replay` gives them
;       to the game afterwards: the game's own handler cannot run during a call and the ACIA holds one byte) and a private
;       stack, and tos_out exchanges back and restores the game's MFP state, stack and SR.  TOS's world therefore persists
;       between the calls and the game never sees it.
;       THE OVERLAY.  The first call, stage 1's DATA\SPRITE40.DAT (101608 B), has its destination $13ba inside R: it is read
;       into OVL = $bd000.. (the p4_ / test_ / snd_ range) while TOS's world is in, copied to the destination with a plain
;       copy after tos_out, and then every payload byte that lives in $bd000..$dcfff (the file PMLATE.DAT next to DATA\,
;       written by pmpatch.py: records {dest.l, len.l [bit 31 = zero fill], bytes}, dest 0 ends) is read back straight to
;       its address.  Interrupts stay masked during the whole call, so nothing runs while the overlay holds the file.
SBASE   equ $dd000                      ; swap buffer S
SMAX    equ $19000                      ; its capacity (up to $f6000)
OVL     equ $bd000                      ; overlay for destinations inside R
OVLMAX  equ $20000                      ; $bd000..$dcfff
V       equ $bc000                      ; variables ($bc000..$bc1ff), private stack below STKTOP
READY   equ V+0                         ; long: 'HDSW' = `init` has the TOS snapshot, swapping works
RHI     equ V+4                         ; long: R's end (exclusive) = (BP + $100) & -4
RLEN    equ V+8                         ; long: R's length (RHI - 8)
GSP     equ V+12                        ; long: the game's a7
SMFP    equ V+16                        ; 6 B: the game's IERB, IMRA, IMRB, TCDCR, IERA, 'timer C was reprogrammed'
GV118   equ V+$30                      ; long: the game's keyboard vector $118 while a call runs
TV118   equ V+24                       ; long: TOS's keyboard vector $118, while hd_acia replaces it
FIFOW   equ V+28                       ; word: bytes in the keyboard FIFO
FIFO    equ V+$100                     ; 128 B: keyboard / mouse bytes received during a call
LHDR    equ V+32                        ; 8 B: late record header
HDBASE  equ V+$40                       ; 64 B: "C:\" or "C:\GAMES\PM\" (drive + Dgetpath of the start folder)
PATHBUF equ V+$80                       ; 128 B: full path of the file in progress
STKTOP  equ $bd000                      ; private stack: $bc200..$bcfff grows down (3.5 KB)
MFP     equ $fffffa00

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

; ---- supervisor mode, TOS's world intact, nothing of the game run yet: snapshot R into S.  READY stays 0 (every hd_load /
; hd_sector then fails) if the basepage cannot be found or R does not fit.
hd_init:
        movem.l d0-d7/a0-a6,-(a7)
        clr.l   READY.l
        movea.l $4f2.w,a0               ; _sysbase: the OS header
        move.l  a0,d0
        btst    #0,d0
        bne.s   .out
        cmpi.l  #$400,d0
        blo.s   .out
        movea.l $28(a0),a0              ; p_run: the address of the variable that holds the current basepage
        move.l  a0,d0
        btst    #0,d0
        bne.s   .out
        cmpi.l  #$400,d0
        blo.s   .out
        cmpi.l  #$20000,d0
        bhs.s   .out
        movea.l (a0),a0                 ; BP
        move.l  a0,d0
        btst    #0,d0
        bne.s   .out
        cmpi.l  #$8000,d0
        blo.s   .out
        cmp.l   $42e.w,d0               ; phystop
        bhs.s   .out
        addi.l  #$100,d0
        andi.l  #-4,d0
        move.l  d0,RHI.l
        subq.l  #8,d0
        cmpi.l  #SMAX,d0
        bhi.s   .out                    ; does not fit
        move.l  d0,RLEN.l
        lsr.l   #2,d0
        subq.l  #1,d0
        lea     $8.w,a0
        lea     SBASE.l,a1
.c:     move.l  (a0)+,(a1)+
        dbra    d0,.c
        move.l  #'HDSW',READY.l
        bra.s   .ok
.out:   pea     nomsg(pc)               ; TOS is intact: say why every load will fail, and wait for a key (the game then asks for its disk, forever)
        move.w  #9,-(a7)                ; Cconws
        trap    #1
        addq.l  #6,a7
        move.w  #1,-(a7)                ; Cconin
        trap    #1
        addq.l  #2,a7
.ok:    movem.l (a7)+,d0-d7/a0-a6
        rts
nomsg:  dc.b    13,10,'POWERMONGER HD: cannot swap the',13,10        ; (40 columns in low resolution)
        dc.b    'low RAM of TOS (basepage not found',13,10
        dc.b    'or region too big): files cannot',13,10
        dc.b    'be loaded. Press a key.',13,10,0
        even

; ---- enter / leave TOS's world.  Called with bsr from the entry code (SR $2700 already, the game's registers saved on
; its stack).  tos_in switches to the private stack: the caller's return address is moved over.
; The exchange of R takes ~0.1 s (78 KB; 8 MHz) and a call can take seconds: the keyboard ACIA must stay serviced all that
; time (it holds ONE byte; the game's mouse protocol, a 6-byte packet per event, is mis-assembled into a wild pointer position
; when bytes are lost, and the game then crashes drawing the pointer).  The game's handler cannot run (its code and its
; vector are in R), so vector $118 holds hd_acia in BOTH worlds (the game's slot in R and TOS's slot in S are patched before
; the exchange and restored after it) and the ACIA interrupt is the only one open while R is being exchanged.
tos_in: move.l  (a7)+,a6                ; return address
        move.l  a7,GSP.l
        lea     STKTOP.l,a7
        clr.w   FIFOW.l
        bsr.w   drain                   ; a keyboard byte that is already waiting goes to the FIFO
        lea     MFP.l,a0
        lea     SMFP.l,a1
        move.b  9(a0),(a1)+             ; IERB
        move.b  $13(a0),(a1)+           ; IMRA
        move.b  $15(a0),(a1)+           ; IMRB
        move.b  $1d(a0),(a1)+           ; TCDCR
        move.b  7(a0),(a1)+             ; IERA
        clr.b   (a1)                    ; timer C untouched
        clr.b   $13(a0)                 ; IMRA = 0: no game / timer A interrupt
        move.b  #$40,$15(a0)            ; IMRB = the keyboard ACIA only
        lea     hd_acia(pc),a2
        move.l  $118.w,GV118.l          ; the game's keyboard vector (its slot in R) ...
        move.l  a2,$118.w
        move.l  SBASE+$110.l,TV118.l    ; ... and TOS's (its slot in S)
        move.l  a2,SBASE+$110.l
        move.b  #$bf,$d(a0)             ; IPRB: drop a stale ACIA pending bit (the FIFO has the byte)
        move.w  #$2500,sr               ; MFP levels only: no VBL / HBL
        bsr.w   xchg                    ; TOS's world is in
        move.w  #$2700,sr
        lea     MFP.l,a0
        move.b  SMFP+3.l,d0             ; TCDCR
        move.b  d0,d1
        andi.b  #$70,d1
        cmpi.b  #$50,d1                 ; timer C already /64?
        beq.s   .tc
        move.b  #192,$23(a0)            ; TCDR: 2457600 / 64 / 192 = 200 Hz, TOS's _hz_200
        andi.b  #$0f,d0
        ori.b   #$50,d0
        move.b  d0,$1d(a0)
        st      SMFP+5.l
.tc:    bset    #5,9(a0)                ; IERB: timer C on
        move.b  #$df,$11(a0)            ; ISRB: drop the in-service bit of timer C (the game's rte stubs never clear it)
        move.b  #$60,$15(a0)            ; IMRB = timer C + the keyboard ACIA
        move.w  #$2500,sr
        jmp     (a6)

tos_out:move.l  (a7)+,a6
        lea     MFP.l,a0
        move.b  #$40,$15(a0)            ; IMRB = the keyboard ACIA only: no TOS timer C handler while R is half exchanged
        bsr.w   xchg                    ; (SR $2500) the game's world is back
        move.w  #$2700,sr
        move.l  GV118.l,$118.w
        move.l  TV118.l,SBASE+$110.l
        bsr.w   drain
        lea     MFP.l,a0
        lea     SMFP.l,a1
        move.b  (a1)+,d2                ; IERB
        move.b  (a1)+,$13(a0)           ; IMRA
        move.b  (a1)+,$15(a0)           ; IMRB
        move.b  (a1)+,d1                ; TCDCR
        move.b  (a1)+,d0                ; IERA (not changed: only read)
        tst.b   (a1)
        beq.s   .tc
        move.b  d1,$1d(a0)              ; timer C was not running the way TOS wants it
.tc:    move.b  d2,9(a0)                ; IERB
        movea.l GSP.l,a7
        jmp     (a6)

; the keyboard interrupt of a call: queue every byte (FIFO, 128 B); `replay` hands them to the game after tos_out.
hd_acia:movem.l d0-d1/a0-a1,-(a7)
        bsr.w   drain
        bclr    #6,$fffffa11.l
        movem.l (a7)+,d0-d1/a0-a1
        rte

; drain: move every byte the keyboard ACIA has received to the FIFO (d0-d1/a0-a1 clobbered)
drain:  lea     $fffffc00.l,a0
.l:     btst    #0,(a0)                 ; RDRF
        beq.s   .o
        move.b  2(a0),d0
        move.w  FIFOW.l,d1
        cmpi.w  #128,d1
        bhs.s   .l                      ; full: dropped (it had to be read all the same)
        lea     FIFO.l,a1
        move.b  d0,0(a1,d1.w)
        addq.w  #1,FIFOW.l
        bra.s   .l
.o:     rts

; replay: the game's own byte processor ($18e8: `tst.b $1c48e` after the `move.b 2(a1),d0` that reads the ACIA, checked by
; the site of hd_kbd.s; d0 = the byte, d0-d1/a0 clobbered) gets the queued bytes in order.  Game context, SR $2700.  The ACIA is
; drained between the bytes: a long replay must not overrun it either.
replay: movem.l d3/a3,-(a7)
        moveq   #0,d3
.l:     bsr.w   drain
        cmp.w   FIFOW.l,d3
        bhs.s   .o
        lea     FIFO.l,a3
        move.b  0(a3,d3.w),d0
        addq.w  #1,d3
        jsr     $18e8.l
        bra.s   .l
.o:     clr.w   FIFOW.l
        movem.l (a7)+,d3/a3
        rts

; exchange R = [$8, RHI) and S.  d0-d1/a0-a1 clobbered, no stack use.
xchg:   lea     $8.w,a0
        lea     SBASE.l,a1
        move.l  RLEN.l,d1
        lsr.l   #2,d1
        subq.l  #1,d1
.l:     move.l  (a0),d0
        move.l  (a1),(a0)+
        move.l  d0,(a1)+
        dbra    d1,.l
        rts

; ---- hd_load: a0 = name, a1 = destination -> d0 = 0 / Z set on success
hd_load:
        movem.l d1-d7/a0-a6,-(a7)
        move.w  sr,-(a7)
        ori.w   #$700,sr
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
        moveq   #-1,d5                  ; result: nonzero until proven
        moveq   #0,d4                   ; 1 = the destination overlaps R: read into the overlay
        cmpi.l  #'HDSW',READY.l
        bne.w   .ret
        bsr.w   tos_in
        movea.l a5,a4                   ; where Fread puts the file
        clr.w   -(a7)                   ; Fopen(path, 0)
        pea     PATHBUF.l
        move.w  #$3d,-(a7)
        trap    #1
        addq.l  #8,a7
        move.l  d0,d6                   ; handle (negative: error)
        bmi.w   .end
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
        move.l  a5,d0                   ; does [dest, dest + size) overlap R = [8, RHI)?
        cmp.l   RHI.l,d0
        bhs.s   .rd
        add.l   d7,d0
        cmpi.l  #8,d0
        bls.s   .rd
        cmpi.l  #OVLMAX,d7
        bhi.s   .cl                     ; does not fit the overlay
        movea.l #OVL,a4
        moveq   #1,d4
.rd:    move.l  a4,-(a7)                ; Fread(handle, size, buffer)
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
        tst.b   d4
        bne.s   .nor
        bsr.w   replay                  ; (stage 1's overlay case drops the bytes: the intro has no mouse)
.nor:
        tst.l   d5
        bne.w   .ret
        tst.b   d4
        beq.w   .ret
; the file is in the overlay and TOS's world is out: plain copy to the destination inside R
        moveq   #-1,d5
        movea.l #OVL,a0
        movea.l a5,a1
        move.l  d7,d0
        lsr.l   #2,d0
        beq.s   .cpt
.cpl:   move.l  (a0)+,(a1)+
        subq.l  #1,d0
        bne.s   .cpl
.cpt:   move.l  d7,d0
        andi.l  #3,d0
        beq.s   .cpd
        subq.l  #1,d0
.cpb:   move.b  (a0)+,(a1)+
        dbra    d0,.cpb
.cpd:
; the overlay held payload bytes (blobs, zeroed data) of the patches: read them back from PMLATE.DAT
        lea     PATHBUF.l,a2
        lea     HDBASE.l,a3
.lb:    move.b  (a3)+,(a2)+
        bne.s   .lb
        subq.l  #1,a2
        lea     latename(pc),a3
.ln:    move.b  (a3)+,(a2)+
        bne.s   .ln
        bsr.w   tos_in
        clr.w   -(a7)
        pea     PATHBUF.l
        move.w  #$3d,-(a7)
        trap    #1
        addq.l  #8,a7
        move.l  d0,d6
        bmi.s   .lend
.rec:   pea     LHDR.l                  ; Fread(handle, 8, header)
        move.l  #8,-(a7)
        move.w  d6,-(a7)
        move.w  #$3f,-(a7)
        trap    #1
        lea     12(a7),a7
        moveq   #8,d1
        cmp.l   d1,d0
        bne.s   .lcl
        move.l  LHDR.l,d3
        beq.s   .lok                    ; dest 0 ends the file
        movea.l d3,a3
        move.l  LHDR+4.l,d7
        bclr    #31,d7
        bne.s   .zero
        move.l  a3,-(a7)                ; Fread(handle, len, dest)
        move.l  d7,-(a7)
        move.w  d6,-(a7)
        move.w  #$3f,-(a7)
        trap    #1
        lea     12(a7),a7
        cmp.l   d7,d0
        bne.s   .lcl
        bra.s   .rec
.zero:  move.l  a3,d0                   ; zero-fill record (a `; data:` span of a patch): longs when aligned, else bytes
        btst    #0,d0
        bne.s   .zb
.zl:    cmpi.l  #4,d7
        blo.s   .zb
        clr.l   (a3)+
        subq.l  #4,d7
        bra.s   .zl
.zb:    tst.l   d7
        beq.w   .rec
        clr.b   (a3)+
        subq.l  #1,d7
        bra.s   .zb
.lok:   moveq   #0,d5
.lcl:   move.w  d6,-(a7)                ; Fclose
        move.w  #$3e,-(a7)
        trap    #1
        addq.l  #4,a7
.lend:  bsr.w   tos_out
.ret:   move.w  (a7)+,sr
        move.l  d5,d0
        tst.l   d0
        movem.l (a7)+,d1-d7/a0-a6
        rts
latename:dc.b   'PMLATE.DAT',0
sdname: dc.b    'SAVEDISK.DAT',0
        even

; ---- hd_sector: the save-game disk as a file.  d1 = sector, d2 = count, d3.b = mode, a0 = buffer -> d0 = 0 / Z ok
hd_sector:
        movem.l d1-d7/a0-a6,-(a7)
        move.w  sr,-(a7)
        ori.w   #$700,sr
        moveq   #0,d5
        cmpi.b  #2,d3
        beq.w   .ret                    ; format: the game rewrites sector 0 (with the slot flags) right after it
        moveq   #-1,d5
        cmpi.l  #'HDSW',READY.l
        bne.w   .ret
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
        move.l  a5,d0                   ; the buffer must not be inside R (every buffer of the save code is above it)
        cmp.l   RHI.l,d0
        blo.w   .ret
        andi.l  #$ff,d3                 ; mode (GEMDOS keeps d3-d7 / a3-a7 over a call, nothing else)
        bsr.w   tos_in
        moveq   #0,d0                   ; Fopen mode: 0 read, 2 read/write
        tst.b   d3
        beq.s   .op
        moveq   #2,d0
.op:    move.w  d0,-(a7)
        pea     PATHBUF.l
        move.w  #$3d,-(a7)
        trap    #1
        addq.l  #8,a7
        move.l  d0,d6
        bpl.s   .opened
        tst.b   d3
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
        tst.b   d3
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
        bsr.w   replay
.ret:   move.w  (a7)+,sr
        move.l  d5,d0
        tst.l   d0
        movem.l (a7)+,d1-d7/a0-a6
        rts
