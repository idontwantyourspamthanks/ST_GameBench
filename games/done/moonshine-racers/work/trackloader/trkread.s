; trkread.s -- SCRATCH PROTOTYPE (stage-2 study, MSRLoaderStudy): read a file through the HAGA TOS window from game context.
; Derived from games/done/populous-2/patches/pop2_save.s part A + part B (same HAGA, md5 b34607ed.. before pp_bigram_cache), reduced to ONE command (read a file into RAM).
;
;   entry  trk_read  (supervisor mode, any game context, interrupts as the game has them)
;       a0 = path (NUL terminated, e.g. "A:\MSTRACKS.TRK" or "MSTRACKS.TRK" = relative to HAGA's current dir FILES\)
;       a1 = destination (even; anywhere the game owns, outside the swapped low-RAM range or inside: the copy runs after the swap-out)
;       d1 = maximum bytes (longer file -> error $cd, nothing read)
;   exit   d0 = 0 ok | GEMDOS error (negative) | $cd too long | $dd short read | -1 HAGA not recognised (nothing done, no side effect)
;          d1 = bytes read; every other register preserved
;
; Differences from Pop2: only Fopen/Fseek/Fread/Fclose; the floppy BCB forget (drives A:,B:) runs for EVERY call (a campaign disk can be swapped between calls:
; TOS's media-change detection does not run while the game owns the interrupts); HAGA base from $2dc (Moonshine's PP stub keeps it there, Pop2 uses $328);
; the IKBD parser state after the call is Moonshine's ($6102 $6103 $610e of handler $cfb4, Pop2's was $2022); no TT PMMU alias (STE / Mega STE only, machine type 4 refused).
; Assemble:  vasmm68k_mot -Fbin -m68000 -nosym -o trkread.bin trkread.s      (org $100000: a scratch address that is free at >= 2 MB)

BSZ     equ     $d00
V_RET   equ     $000-BSZ
V_A7    equ     $004-BSZ
V_USP   equ     $008-BSZ
V_BASE  equ     $00c-BSZ
V_BUF   equ     $010-BSZ
V_LEN   equ     $014-BSZ        ; max bytes
V_RES0  equ     $018-BSZ
V_RES1  equ     $01c-BSZ
V_SR    equ     $024-BSZ
V_H     equ     $028-BSZ
V_CRIT  equ     $02c-BSZ
V_MAGIC equ     $038-BSZ
V_PATH  equ     $080-BSZ        ; 128 bytes
USPTOP  equ     $500-BSZ
SSPTOP  equ     $d00-BSZ
BOUNCE  equ     $1400-BSZ
BSIZE   equ     $2000
BLK     equ     $3900           ; offset from HAGA's base: above everything HAGA uses, below its 32 KB end (Pop2: same)

        org     $100000

; ---- part A (game context): install part B into HAGA's top region on first use, then call it
trk_read:
        movem.l d2/a2-a4,-(a7)
        movea.l a0,a3                   ; the path
        movea.l $2dc.w,a2               ; HAGA's base (Moonshine's PP stub reads it from $2dc)
        move.l  a2,d2
        cmpi.l  #$100000,d2
        bcs.s   .fail
        btst    #0,d2
        bne.s   .fail
        cmpi.l  #$4dfa1c04,$17be(a2)    ; HAGA's three routines, by signature (the same bytes in the patched HAGA: the patch is at +$3228)
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
        move.w  #(bend-bstart)/4+1,d2   ; whole longs (the template is padded to a multiple of 4)
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

; ---- part B (template, copied to HAGA+BLK+BSZ; position independent: a5 = its own start, data at negative offsets)
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
.cp:    move.b  (a0)+,d0                ; path -> V_PATH (no case folding: the caller passes the 8.3 upper-case name)
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
.k:     btst    #0,$fffffc00.l          ; drain the IKBD ACIA
        beq.s   .k2
        tst.b   $fffffc02.l
        bra.s   .k
.k2:    clr.b   $6102.l                 ; Moonshine's IKBD parser ($cfb4) back to idle: a packet cut by the call must not shift the next one
        clr.b   $6103.l
        clr.b   $610e.l
        movea.l V_RET(a5),a0
        move.w  V_SR(a5),sr
        jmp     (a0)

; The GEMDOS part.  TOS's critical-error vector $404 is replaced for the duration by a stub that returns the error code (a missing / unreadable disk must
; fail the call, not open the desktop's alert from a suspended AES).
body:   move.l  $404.w,V_CRIT(a5)
        lea     crit(pc),a0
        move.l  a0,$404.w
        bsr.s   body1
        move.l  V_CRIT(a5),$404.w
        rts
crit:   move.w  4(a7),d0
        ext.l   d0
        rts

body1:  bsr.w   forget                  ; drives A: and B: re-read (a campaign disk may have been swapped since the last call)
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
.s1:    cmp.l   V_LEN(a5),d4            ; longer than the caller's buffer
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

; Fread in 8 KB pieces into BOUNCE, then copied by the CPU to the caller's buffer (V_BUF + offset).  d4 = file size.  d0 = d4 if all of it moved.
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
        addq.l  #1,d0                   ; a short count (odd, never equal to d4 when d4 is even; the caller compares to d4 anyway)
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
fsize:  move.w  #2,-(a7)                ; Fseek(0, handle, 2): the size
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

; TOS's disk change detection does not run while the game owns the interrupts: forget every BIOS cache buffer (the two lists at _bufl $4b2, BCB: link.l,
; drive.w at +4) of drives A: and B: (b_bufdrv = -1), so GEMDOS re-reads the FAT / directory of whatever disk is in the drive now.  (Pop2's .tick.)
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
