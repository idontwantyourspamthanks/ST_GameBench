; core.s -- Hunter patch delivery mechanism (always installed by huntpatch.py).  Evidence: work/notes/loading.md.
;
; Four segments, assembled separately:
;   org $0      stub     position independent, 142 bytes, lives in the dead zero run of the patched START.TOS
;                        (text offset $7f20).  START's tail `lea $7e800,a7` (just before `jmp $800.w`) became
;                        `jmp stub`.  It reads FILES\P (the payload image) to $8BA00 with the GAME'S OWN loader
;                        (D15R: $c0100+4 -> $c0152, 70000-byte chunks, file offset in $c0736), checks the magic
;                        'HNPA', calls hnentry (PAYLOAD+4), then restores every register and SR and does the original
;                        `lea $7e800,a7 / jmp $800.w`.  File missing / short: the game starts unpatched, no marker.
;   org $8ba00  hnentry  verify ALL boot sites, then apply them (all or nothing); 'HNPO'/'HNPF' at MARKER;
;                        STE DMA sound hardware probe -> FLAGS; instruction/data cache flush (68020+).
;   org $8bb60  hookexit replaces `jmp $d60a.l` at $1a6 (the single exit of the game's file hook $150) when
;                        any phase=deferred site exists; runs `apply` for the file that has just been read.
;   org $7fc0   mchfix   TT only, 64 bytes in the same dead zone of START's text (see below): START's `jsr (a0)` that runs
;                        the hard disk's root sector (text $590) became `bsr.w mchfix`.
; Site table (written by huntpatch.py): entries {addr.l len.w phase.w orig[len] new[len]}, addr 0 ends.
;   phase 0 = boot site (applied by entry), phase 1 = deferred (applied by apply when the finished file read
;   [$c073e dest, $c0358 byte count] covers the whole site; idempotent: orig -> write new; new -> done; else HNPF).
;
; Interface for the other patch authors (fixed addresses):
;   $8BFF0.l FLAGS   bit0 = STE-class DMA sound hardware answers (bus-error safe probe + register read-back)
;                    bit1 = the probe ran (so bit0 == 0 means a plain ST), bit2 = probe took a bus error,
;                    bit3 = Falcon (bit0 set, the _MCH cookie in the jar at $5a0 is $0003xxxx AND a read of the SCU $ff8e01 bus-errors: the
;                    jar alone said Falcon on a TT HD boot, where D15R_F5's own jar is already installed)
;   $8BFF8.l MARKER  'HNPO' every boot site applied, 'HNPF' refused (a verified original differed; nothing
;                    from the boot phase was written), all zero = the payload never ran
TABLE   equ $8bc00
MARKER  equ $8bff8
FLAGS   equ $8bff0
PAYLOAD equ $8ba00
PSIZE   equ $23600                  ; payload image capacity: $8ba00..$aeffff (HDDRIVER's pool starts $af100 on 1 MB)

        org     $0
stub:   movem.l d0-d7/a0-a6,-(a7)
        move.w  sr,-(a7)
        clr.l   PAYLOAD.l               ; so a failed read cannot look like a payload
        lea     PAYLOAD.l,a2            ; destination of the next chunk
        moveq   #0,d3                   ; file offset
.loop:  move.l  #PSIZE,d4
        sub.l   d3,d4                   ; capacity left
        bls.s   .done
        cmpi.l  #$11170,d4              ; D15R reads at most 70000 bytes per call
        bls.s   .go
        move.l  #$11170,d4
.go:    move.l  d3,$c0736.l             ; Fseek offset
        move.l  d4,$c073a.l             ; byte count
        move.l  a2,$c073e.l             ; destination
        move.w  #$5000,$c0752.l         ; file name "P",0 (relative to \FILES)
        lea     $c0100.l,a0             ; D15R: +4 = file read entry ($c0152)
        moveq   #0,d0
        move.w  4(a0),d0
        adda.l  d0,a0
        jsr     (a0)
        clr.w   $c0734.l                ; first-call drive/path setup was done (the game's $150 hook does this too)
        move.l  $c0358.l,d0             ; Fread result: bytes, negative = error
        ble.s   .done
        adda.l  d0,a2
        add.l   d0,d3
        cmp.l   d4,d0
        beq.s   .loop                   ; full chunk: there may be more
.done:  cmpi.l  #'HNPA',PAYLOAD.l
        bne.s   .out
        jsr     PAYLOAD+4.l
.out:   move.w  (a7)+,sr
        movem.l (a7)+,d0-d7/a0-a6
        lea     $7e800.l,a7             ; START's own instruction that the splice replaced
        jmp     $800.w

        org     $7fc0
; TT only.  The game's own cookie jar (D15R_F5.FIC, used on every TT/Falcon) says _MCH = Falcon.  START runs the root
; sector of the disk (HDDRIVER) a second time inside that world; HDDRIVER trusts the jar and, on a "Falcon", does not scan
; ACSI, so on a TT with an ACSI disk it found no drive and the game started on garbage (work/notes/ttfalcon.md).  START's
; machine type byte (text $693) is 5 on a TT: put the real _MCH ($00020000) into the jar for the duration of that run only.
mchfix: move.l  a1,-(a7)               ; a1 may matter to the root sector: keep it
        lea     $693(pc),a1             ; START's machine type byte: 5 = TT
        cmpi.b  #5,(a1)
        movea.l (a7)+,a1                ; (movea leaves the flags)
        bne.s   .plain
        cmpi.l  #'_MCH',$d0ee4.l        ; D15R_F5's jar: _CPU,$1e,_MCH,$00030000
        bne.s   .plain
        move.l  $d0ee8.l,-(a7)
        move.l  #$00020000,$d0ee8.l
        jsr     (a0)                    ; the root sector (a0, d4, d5, d7 as START set them)
        move.l  (a7)+,$d0ee8.l
        bra.s   .out
.plain: jsr     (a0)
.out:   moveq   #$1c,d7                 ; START's instruction behind the jsr
        rts

        org     $8ba00
        dc.l    'HNPA'
hnentry: movem.l d0-d7/a0-a6,-(a7)
        move.l  #'HNPF',MARKER.l        ; preset failure marker
        bsr.w   probe
        ; pass 1: verify the ORIGINAL bytes of every boot site; nothing is written yet
        lea     TABLE.l,a0
.v1:    move.l  (a0)+,d0                ; site addr, 0 = end
        beq.s   .pass2
        move.w  (a0)+,d1                ; len
        move.w  (a0)+,d2                ; phase
        movea.l a0,a1                   ; orig bytes
        adda.w  d1,a0
        adda.w  d1,a0                   ; next entry (orig + new)
        tst.w   d2
        bne.s   .v1                     ; deferred: the file hook applies those
        movea.l d0,a3
        subq.w  #1,d1
.v2:    cmpm.b  (a1)+,(a3)+
        bne.s   .tfail                  ; any mismatch: write nothing, keep HNPF
        dbra    d1,.v2
        bra.s   .v1
        ; pass 2: all boot sites matched
.pass2: lea     TABLE.l,a0
.a1:    move.l  (a0)+,d0
        beq.s   .tok
        move.w  (a0)+,d1
        move.w  (a0)+,d2
        adda.w  d1,a0                   ; skip orig
        movea.l a0,a2                   ; new bytes
        adda.w  d1,a0                   ; next entry
        tst.w   d2
        bne.s   .a1
        movea.l d0,a3
        subq.w  #1,d1
.a2:    move.b  (a2)+,(a3)+
        dbra    d1,.a2
        bra.s   .a1
.tok:   move.l  #'HNPO',MARKER.l
.tfail: bsr.w   cflush                 ; every exit: START and the sites wrote code with data writes
        movem.l (a7)+,d0-d7/a0-a6
        rts

; Cache flush before the game runs (68020 and up; 68000/68010: nothing to do).  START depacks the game, applies PP's RAM
; patches and copies the file hook with ordinary data writes, then we patch more; an instruction cache that still holds
; lines of whatever ran at those addresses before (HDDRIVER's resident code on a TT/Falcon lives right there) would execute
; stale bytes.  The CPU is found by executing instructions under temporary illegal/line-F handlers:
;   movec cacr,d0   68020/030/040/060 execute it, 68000/68010 raise illegal instruction
;   cpusha bc       68040/060 push + invalidate both caches; 68020/030 raise line F ($2c) -> clear CI + CD in the CACR
; d0-d1/a0-a3 scratch.
cflush: movea.l a7,a2                   ; the exception handler resets the stack here
        movea.l $10.w,a1
        movea.l $2c.w,a3
        lea     .ctrap(pc),a0
        move.l  a0,$10.w
        move.l  a0,$2c.w
        moveq   #0,d1                   ; stage 0: movec
        dc.w    $4e7a,$0002             ; movec cacr,d0
        moveq   #1,d1                   ; stage 1: cpusha
        dc.w    $f4f8                   ; cpusha bc
        bra.s   .cdone
.ctrap: movea.l a2,a7                   ; drop the exception frame
        tst.w   d1
        beq.s   .cdone                  ; no CACR: 68000/68010
        ori.w   #$0808,d0               ; 68020/030: CI (bit 3) + CD (bit 11): clear both caches
        dc.w    $4e7b,$0002             ; movec d0,cacr
.cdone: move.l  a1,$10.w
        move.l  a3,$2c.w
        rts

; STE-class DMA sound probe (cookies are unreliable under Gamex).  d0-d3/a0-a2 scratch.
; A plain ST/Mega ST bus-errors on $ff8901; STE, Mega STE, TT and Falcon answer, and the frame start
; (mid byte $ff8905) must read back what is written (only tried while the DMA is stopped).
probe:  move.l  FLAGS.l,d3              ; bit3 (Falcon) is sticky: the floppy stage 2 probes first, while TOS's jar still exists; the
        andi.w  #8,d3                   ; game later overwrites it, and the payload entry probes again (FLAGS is zero before the first call)
        ori.w   #2,d3                   ; bit1: probe ran
        movea.l a7,a2                   ; the bus error handler resets the stack here
        movea.l $8.w,a1
        lea     .berr(pc),a0
        move.l  a0,$8.w
        move.b  $ffff8901.w,d0            ; DMA control; bus error on a plain ST
        btst    #0,d0
        bne.s   .yes                    ; DMA already running: it exists
        move.b  $ffff8905.w,d1            ; frame start mid byte
        move.b  #$5a,$ffff8905.w
        cmpi.b  #$5a,$ffff8905.w
        bne.s   .no
        move.b  #$a5,$ffff8905.w
        cmpi.b  #$a5,$ffff8905.w
        bne.s   .no
        move.b  d1,$ffff8905.w
.yes:   bset    #0,d3
        bra.s   .no
.berr:  movea.l a2,a7
        bset    #2,d3
.no:    move.l  a1,$8.w
        btst    #0,d3
        beq.s   .fin
        move.l  $5a0.w,d0               ; Falcon: _MCH cookie = $0003xxxx in TOS's own jar (STE/Mega STE $0001, TT $0002).  Read here, in
        beq.s   .fin                    ; the payload entry / floppy stage 2, before the game's own jar (D15R_F5's says Falcon on a TT too)
        movea.l d0,a0                   ; exists; Hatari's STE/TT do not bus-error on the Falcon registers, so no register probe
.ck:    move.l  (a0)+,d0
        beq.s   .fin
        move.l  (a0)+,d1
        cmpi.l  #'_MCH',d0
        bne.s   .ck
        swap    d1
        cmpi.w  #3,d1
        bne.s   .fin
        movea.l a7,a2                   ; The jar can lie: on a TT HD boot it is D15R_F5's (_MCH = Falcon) and bit3 came out set.  The TT (and the
        movea.l $8.w,a1                 ; Mega STE) have the SCU at $ff8e01, a Falcon has not: a bus error there confirms the Falcon.
        lea     .nscu(pc),a0
        move.l  a0,$8.w
        tst.b   $ffff8e01.w
        move.l  a1,$8.w                 ; it answered: a TT, not a Falcon
        bra.s   .fin
.nscu:  movea.l a2,a7                   ; (entered by the bus error)
        move.l  a1,$8.w
        bset    #3,d3
.fin:   move.l  d3,FLAGS.l
        rts

        org     $8bb60
hookexit:                               ; replaces `jmp $d60a.l` (4ef9 0000d60a) at $1a6
        movem.l d0-d7/a0-a6,-(a7)
        bsr.s   apply
        movem.l (a7)+,d0-d7/a0-a6
        jmp     $d60a.l                 ; the original exit: back into the game
apply:  move.l  $c073e.l,d0             ; destination of the read that just finished
        move.l  $c0358.l,d1             ; bytes read (negative: Fopen/Fread failed)
        ble.s   .adone
        add.l   d0,d1                   ; d1 = end
        lea     TABLE.l,a0
.aloop: move.l  (a0)+,d2                ; addr, 0 = end
        beq.s   .adone
        move.w  (a0)+,d3                ; len
        move.w  (a0)+,d4                ; phase
        movea.l a0,a1                   ; orig
        adda.w  d3,a0
        movea.l a0,a2                   ; new
        adda.w  d3,a0                   ; next entry
        cmpi.w  #1,d4
        bne.s   .aloop                  ; boot site: not ours
        cmp.l   d0,d2
        blt.s   .aloop                  ; below the file
        moveq   #0,d5
        move.w  d3,d5
        add.l   d2,d5
        cmp.l   d1,d5
        bgt.s   .aloop                  ; beyond the file
        movea.l d2,a3                   ; compare against orig
        move.w  d3,d6
        subq.w  #1,d6
        movea.l a1,a4
.av:    cmpm.b  (a4)+,(a3)+
        bne.s   .trynew
        dbra    d6,.av
        bra.s   .aapply                 ; orig matched: write new
.trynew:movea.l d2,a3                   ; compare against new (already applied?)
        move.w  d3,d6
        subq.w  #1,d6
        movea.l a2,a4
.an:    cmpm.b  (a4)+,(a3)+
        bne.s   .afail
        dbra    d6,.an
        bra.s   .aloop                  ; already applied
.aapply:movea.l d2,a3
        move.w  d3,d6
        subq.w  #1,d6
        movea.l a2,a4
.aw:    move.b  (a4)+,(a3)+
        dbra    d6,.aw
        bra.s   .aloop
.afail: move.l  #'HNPF',MARKER.l
.adone: rts
