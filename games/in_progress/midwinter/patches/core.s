; core.s — MW1 patch delivery mechanism (always installed by mw1patch.py).
; Assembled into the $B3000 image in three fixed-org segments.  The trampoline is two-pass:
; every boot site is verified first, only then are they written (all or nothing).
;   $B3000 trampoline: entered from PP's patcher tail (RAM = stack-phase copy $B2072,
;            text $482 of RUNME: it replaced `jmp $800.w`, the game entry), or for the
;            floppy build from the stage-2 stub (build --floppy).  Verifies+applies all
;            phase=boot sites, writes 'MWPO'/'MWPF' to $B2FF8, then jmp $800.w.
;   $B3070 hookexit:   entered from the $10D6C splice (the single success exit of the game's
;            file loader sub_010cd2); restores exactly like the original exit, then runs apply.
;   $B3090 apply:      applies phase=deferred sites whose address range is covered by the
;            file load that just finished (dest [$2c34a].l, length [$2db02].l).
;            Idempotent: orig bytes -> apply; new bytes -> already done;
;            anything else -> 'MWPF' marker, site left untouched.
; Site table at $BA000-$BAFFF (4 KB): entries {addr.l len.w phase.w orig.l new.l}, addr 0 ends.
; $B9F00 cpufix:    (68020+ only, work/notes/tt.md) called first thing by the trampoline: finds the CPU class (cpulib.s, spliced in at the
;            marker line), writes it to CPUFLAG ($B2FF4), switches the caches off and, on the floppy build, widens the game's own FDC
;            waits (FDCTAB below).  On a 68000/68010 it returns at once, so ST/STE/Mega STE behave exactly as before.
TABLE   equ $ba000
MARKER  equ $b2ff8
apply   equ $b3090
cpufix  equ $b9f00
CPUFLAG equ $b2ff4

        org     $b3000
trampoline:
        movem.l d0-d7/a0-a6,-(a7)
        move.w  sr,-(a7)                ; keep flags/mode exactly as PP's patcher left them
        jsr     cpufix.l                ; registers are all saved above; returns immediately on a 68000
        move.l  #'MWPF',MARKER.l        ; preset failure marker
        ; pass 1: verify the ORIGINAL bytes of every boot site; nothing is written yet
        lea     TABLE.l,a0
.v1:    move.l  (a0)+,d0                ; site addr; 0 = end of table
        beq.s   .pass2
        move.w  (a0)+,d1                ; length
        move.w  (a0)+,d2                ; phase: 0 boot / 1 deferred
        move.l  (a0)+,a1                ; orig bytes
        addq.l  #4,a0                   ; skip new-bytes pointer
        tst.w   d2
        bne.s   .v1                     ; deferred sites: the load hook handles them
        movea.l d0,a3
        subq.w  #1,d1
.v2:    cmpm.b  (a1)+,(a3)+
        bne.s   .tfail                  ; any mismatch: apply nothing, keep MWPF
        dbra    d1,.v2
        bra.s   .v1
        ; pass 2: all boot sites matched, apply them
.pass2: lea     TABLE.l,a0
.a1:    move.l  (a0)+,d0
        beq.s   .tok
        move.w  (a0)+,d1
        move.w  (a0)+,d2
        addq.l  #4,a0                   ; skip orig pointer
        move.l  (a0)+,a2                ; new bytes
        tst.w   d2
        bne.s   .a1
        movea.l d0,a3
        subq.w  #1,d1
.a2:    move.b  (a2)+,(a3)+
        dbra    d1,.a2
        bra.s   .a1
.tok:   move.l  #'MWPO',MARKER.l
.tfail: move.w  (a7)+,sr
        movem.l (a7)+,d0-d7/a0-a6
        jmp     $800.w

        org     $b3070
hookexit:                               ; replaces 33df 000062b8 at $10D6C
        movem.l d0-d7/a0-a6,-(a7)       ; work FIRST on the unchanged exit frame
        jsr     apply.l
        movem.l (a7)+,d0-d7/a0-a6
        move.w  (a7)+,$62b8.l           ; original exit sequence from here on
        movem.l (a7)+,d0-d7/a0-a6
        rts                             ; -> caller of sub_010cd2

        org     $b3090
        move.l  $2c34a.l,d0             ; dest of the load that just finished
        move.l  $2db02.l,d1             ; its length
        add.l   d0,d1                   ; d1 = end
        lea     TABLE.l,a0
.aloop: move.l  (a0)+,d2                ; addr; 0 = end
        beq.s   .adone
        move.w  (a0)+,d3                ; len
        move.w  (a0)+,d4                ; phase
        move.l  (a0)+,a1                ; orig
        move.l  (a0)+,a2                ; new
        cmpi.w  #1,d4
        bne.s   .aloop                  ; boot site: not ours
        cmp.l   d0,d2
        blt.s   .aloop                  ; below load range
        move.l  d2,d5
        add.l   d3,d5
        cmp.l   d1,d5
        bgt.s   .aloop                  ; beyond load range
        movea.l d2,a3                   ; compare against orig
        move.w  d3,d6
        subq.w  #1,d6
.av:    move.b  (a1)+,d7
        cmp.b   (a3)+,d7
        bne.s   .trynew
        dbra    d6,.av
        bra.s   .aapply                 ; orig matched: write new
.trynew:movea.l d2,a3                   ; compare against new (already applied?)
        move.w  d3,d6
        subq.w  #1,d6
.an:    move.b  (a2)+,d7
        cmp.b   (a3)+,d7
        bne.s   .afail
        dbra    d6,.an
        bra.s   .aloop                  ; already applied
.aapply:movea.l d2,a3
        move.w  d3,d6
        subq.w  #1,d6
.aw:    move.b  (a2)+,(a3)+
        dbra    d6,.aw
        bra.s   .aloop
.afail: move.l  #'MWPF',MARKER.l
.adone: rts

        org     $b9f00
cpufix_entry:
        ifnd    FLOPPY
        rts                             ; HD: nothing to do, and HAGA remaps low RAM on a TT ($5a0 is not TOS's jar there): never read it
        endc
        movem.l d0-d2/a0-a1,-(a7)
        bsr.w   cl_detect
        move.b  d0,CPUFLAG.l
        beq.s   .x                      ; 68000/68010: nothing at all
        ifd     FLOPPY
        bsr.w   cl_cacheoff             ; floppy: no TOS caches policy; HD: PP's HAGA owns CACR on a TT, leave it alone
        endc
        lea     fdctab(pc),a0
        bsr.w   cl_patch
.x:     movem.l (a7)+,d0-d2/a0-a1
        rts
;@CPULIB
fdctab:
        ifd     FLOPPY
        ; the game's own FDC driver (floppy build: PP's HD patches bypass it): timeout and three dbra delays, ~x32 / x4
        dc.l    $11304
        dc.w    4
        dc.l    $00800000               ; was $40000   (sub_d3c0-style wait for the FDC interrupt)
        dc.l    $112c4
        dc.w    2
        dc.l    $0600                   ; was $0180
        dc.l    $110a6
        dc.w    2
        dc.l    $0400                   ; was $0100
        dc.l    $1133a
        dc.w    2
        dc.l    $0080                   ; was $0020
        endc
        dc.l    0
