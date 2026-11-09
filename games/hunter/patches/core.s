; core.s -- Hunter patch delivery mechanism (always installed by huntpatch.py).  Evidence: work/notes/loading.md.
;
; Three segments, assembled separately:
;   org $0      stub     position independent, 142 bytes, lives in the dead zero run of the patched START.TOS
;                        (text offset $7f20).  START's tail `lea $7e800,a7` (just before `jmp $800.w`) became
;                        `jmp stub`.  It reads FILES\P (the payload image) to $8BA00 with the GAME'S OWN loader
;                        (D15R: $c0100+4 -> $c0152, 70000-byte chunks, file offset in $c0736), checks the magic
;                        'HNPA', calls hnentry (PAYLOAD+4), then restores every register and SR and does the original
;                        `lea $7e800,a7 / jmp $800.w`.  File missing / short: the game starts unpatched, no marker.
;   org $8ba00  hnentry  verify ALL boot sites, then apply them (all or nothing); 'HNPO'/'HNPF' at MARKER;
;                        STE DMA sound hardware probe -> FLAGS.
;   org $8bb00  hookexit replaces `jmp $d60a.l` at $1a6 (the single exit of the game's file hook $150) when
;                        any phase=deferred site exists; runs `apply` for the file that has just been read.
; Site table (written by huntpatch.py): entries {addr.l len.w phase.w orig[len] new[len]}, addr 0 ends.
;   phase 0 = boot site (applied by entry), phase 1 = deferred (applied by apply when the finished file read
;   [$c073e dest, $c0358 byte count] covers the whole site; idempotent: orig -> write new; new -> done; else HNPF).
;
; Interface for the other patch authors (fixed addresses):
;   $8BFF0.l FLAGS   bit0 = STE-class DMA sound hardware answers (bus-error safe probe + register read-back)
;                    bit1 = the probe ran (so bit0 == 0 means a plain ST), bit2 = probe took a bus error
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
.tfail: movem.l (a7)+,d0-d7/a0-a6
        rts

; STE-class DMA sound probe (cookies are unreliable under Gamex).  d0-d3/a0-a2 scratch.
; A plain ST/Mega ST bus-errors on $ff8901; STE, Mega STE, TT and Falcon answer, and the frame start
; (mid byte $ff8905) must read back what is written (only tried while the DMA is stopped).
probe:  moveq   #2,d3                   ; bit1: probe ran
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
        move.l  d3,FLAGS.l
        rts

        org     $8bb00
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
