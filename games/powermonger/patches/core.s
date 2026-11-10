; core.s -- Powermonger patch delivery mechanism (always installed by pmpatch.py).  Evidence: work/notes/loading.md.
;
; Segments, assembled separately (pmpatch.py CORE_ORGS; hook1 and hook2 are in the "hook" segment, which `apply` shares):
;   org $0      front    position independent.  First thing in the data segment that pmpatch.py appends to
;                        AUTO\WAR.PRG (TOS loads text+data).  The first 8 bytes of WAR.PRG's text (the original
;                        `Super(0)` call) became `jmp front.l; nop` (one relocation entry).  front copies the payload
;                        image that follows it to IMG ($B8000), calls the payload's `uinit` (user mode), repeats the
;                        Super call, calls `init` (supervisor; STE probe, init routines of other patches) and then
;                        resumes the original program at text offset 8.
;   org $b8000  entry    'PMPA', init.
;   org HOOK1..   hook1/hook2/apply.  Each stage of the game ends in a 32-byte copy routine that its plaintext stub
;                        pushes on the stack (WAR.PRG text $1e4, DATA\SPRITE40.DAT file $124): copy the depacked text, clear
;                        the tail, restore the registers and `rts` to the text ($576 / $10A6).  pmpatch.py rewrites that
;                        routine so it ends in `jmp hook1` / `jmp hook2` instead.  A hook verifies the ORIGINAL bytes of
;                        every site of its stage, then applies all of them or none and jumps where the `rts` would have
;                        gone, with the exact register file and SR the original `rts` would have produced.  hook2 (the
;                        game proper in place) is always installed; hook1 only if a patch has `; stage: 1`.
; Site table (written by pmpatch.py): entries {addr.l len.w class.w orig[len] new[len]}, addr 0 ends; class = stage-1 + 2*mandatory.
; Mandatory sites (`; mandatory: yes`, the hd_* loader patches: the game cannot run without them) are verified and applied as
; their own all-or-nothing group before the optional ones, so a refused optional patch leaves a runnable game.
;
; Interface for the other patch authors (fixed addresses):
;   $B87F0.l FLAGS   bit0 = STE-class DMA sound hardware answers (bus-error safe probe + register read-back)
;                    bit1 = the probe ran (so bit0 == 0 means a plain ST), bit2 = probe took a bus error
;   $B87F8.l MARKER  'PMPO' every site applied, 'PMPF' refused (a verified original differed; nothing written),
;                    'PMP1' stage 1 applied, stage 2 pending; all zero = no hook ran
;   $B87C0.. INITTBL up to 11 longs (0 ends): routines called by `init` (supervisor mode, TOS's vectors and state
;                    still intact: WAR.PRG has not run a single instruction of its own yet).  `; init: $addr` header.
;   $B8790.. UINITTBL up to 11 longs: same, called earlier by `uinit` in USER mode (GEMDOS calls are safe there).
;                    `; uinit: $addr` header.  Routines get no arguments and may use every register.
;   $B87BF.b ICMODE  0 (default) = the CPU caches stay off in the game; 1 = hook2 switches the INSTRUCTION cache back on (68020+; experiments only)
;   $B87EC.l ICVAL    what hook2 writes to CACR for that (0 on a 68000/68010 or when TOS had its instruction cache off): $19 on a 68020/030, $8000 on a 68040/060
; CPU caches (68020 and up, TT/Falcon): the game's two in-place depackers `rts` into addresses the decoder has just overwritten with data writes
; (stage 0 -> stage 1 at $576, stage 1 -> stage 2 at $10A6), so a 68030 instruction cache runs stale decoder lines (Line-F at $672 on a TT, then
; TOS hangs; work/notes/regression.md).  `init` (supervisor, before the game's first instruction) switches every cache off; the data cache stays off
; for the whole run (the 030 does not snoop the game's raw FDC DMA, and HD loads go through GEMDOS); hook2 may re-enable the instruction cache.
TABLE   equ $b8250
FALCON  equ $b87bd                      ; byte: non-zero on a Falcon (_MCH cookie high word 3), set by `init`; hook1 then applies the `; falcon: yes` sites (class 4)
ICMODE  equ $b87bf                      ; byte
ICVAL   equ $b87ec
UINITTBL equ $b8790
INITTBL equ $b87c0
FLAGS   equ $b87f0
MARKER  equ $b87f8
IMG     equ $b8000
HOOK1   equ $b8140
HOOK2   equ $b8190
APPLY   equ $b81f0

        org     $0
front:  lea     img(pc),a0              ; the payload records: right behind this stub
.rec:   movea.l (a0)+,a1                ; record = {dest.l, len.l [, len bytes]}; dest 0 ends; len bit 31 = zero-fill, no bytes
        move.l  a1,d1
        beq.s   .done
        move.l  (a0)+,d0                ; all lengths are multiples of 4, > 0
        bmi.s   .zero
        lsr.l   #2,d0
.cp:    move.l  (a0)+,(a1)+
        subq.l  #1,d0
        bne.s   .cp
        bra.s   .rec
.zero:  andi.l  #$7fffffff,d0
        lsr.l   #2,d0
.zl:    clr.l   (a1)+
        subq.l  #1,d0
        bne.s   .zl
        bra.s   .rec
.done:
        cmpi.l  #'PMPA',IMG.l
        bne.s   .sup
        jsr     IMG+8.l                 ; uinit: user mode, TOS fully alive
.sup:   clr.l   -(a7)                   ; the program's own first instruction, verbatim: Super(0)
        move.w  #$20,-(a7)
        trap    #1
        cmpi.l  #'PMPA',IMG.l
        bne.s   .out
        jsr     IMG+4.l                 ; init: supervisor, TOS's vectors still installed
.out:   lea     front(pc),a0
        suba.l  #TEXTLEN-8,a0           ; TEXTLEN = original text size: this is text offset 8 (the rest of the Super code)
        jmp     (a0)
img:                                    ; payload records start here (not assembled; pmpatch.py appends them)

        org     $b8000
        dc.l    'PMPA'
        bra.w   init                    ; IMG+4: supervisor init
        bra.w   uinit                   ; IMG+8: user-mode init
init:   movem.l d0-d7/a0-a6,-(a7)
        bsr.w   probe
        bsr.w   cacroff
        bsr.w   falcon
        lea     INITTBL.l,a2
        bra.s   tbl
uinit:  movem.l d0-d7/a0-a6,-(a7)
        lea     UINITTBL.l,a2
tbl:    move.l  (a2)+,d0
        beq.s   .id
        movea.l d0,a0
        jsr     (a0)                    ; may use d0-d7/a0-a6 freely
        bra.s   tbl
.id:    movem.l (a7)+,d0-d7/a0-a6
        rts

; STE-class DMA sound probe.  A plain ST/Mega ST bus-errors on $ff8901; STE, Mega STE, TT and Falcon answer, and the
; frame start (mid byte $ff8905) must read back what is written (only tried while the DMA is stopped).
probe:  moveq   #2,d3                   ; bit1: probe ran
        movea.l a7,a2                   ; the bus error handler resets the stack here
        movea.l $8.w,a1
        lea     .berr(pc),a0
        move.l  a0,$8.w
        move.b  $ffff8901.w,d0          ; DMA control; bus error on a plain ST
        btst    #0,d0
        bne.s   .yes                    ; DMA already running: it exists
        move.b  $ffff8905.w,d1          ; frame start mid byte
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

; Caches off (68020+; the 68000/68010 have none).  The CPU is found by executing instructions under temporary illegal / line-F handlers:
;   movec cacr,d0   68020/030/040/060 execute it, 68000/68010 raise illegal instruction ($10)
;   cpusha bc       68040/060 push + invalidate both caches; 68020/030 raise line F ($2c) -> CACR = CI + CD (clear both, EI/ED = 0)
; d0-d2/a0-a3 scratch.  ICVAL gets what hook2 would need to write to switch the instruction cache back on.
cacroff: movea.l a7,a2                  ; the exception handler resets the stack here
        movea.l $10.w,a1
        movea.l $2c.w,a3
        lea     .ctrap(pc),a0
        move.l  a0,$10.w
        move.l  a0,$2c.w
        moveq   #0,d1                   ; stage 0: movec
        dc.w    $4e7a,$0002             ; movec cacr,d0
        moveq   #1,d1                   ; stage 1: cpusha
        dc.w    $f4f8                   ; cpusha bc
        move.l  d0,d2                   ; 68040/060: caches pushed and invalidated; IE (bit 15) was TOS's instruction cache switch
        andi.l  #$8000,d2
        move.l  d2,ICVAL.l
        moveq   #0,d0
        dc.w    $4e7b,$0002             ; movec d0,cacr: everything off
        bra.s   .cdone
.ctrap: movea.l a2,a7                   ; drop the exception frame
        tst.w   d1
        beq.s   .cdone                  ; no CACR: 68000/68010
        moveq   #0,d2                   ; 68020/030: d0 = TOS's CACR; EI is bit 0
        btst    #0,d0
        beq.s   .noi
        moveq   #$19,d2                 ; EI + IBE + CI
.noi:   move.l  d2,ICVAL.l
        move.l  #$0808,d0               ; CI + CD: clear both caches, EI/ED = 0 -> off
        dc.w    $4e7b,$0002             ; movec d0,cacr
.cdone: move.l  a1,$10.w
        move.l  a3,$2c.w
        rts

; Falcon? _MCH cookie ($5a0 -> list of {tag, value}) high word 3.  FALCON byte stays 0 elsewhere (the zero-fill record covers it).
falcon: move.l  $5a0.w,d0
        beq.s   .r
        movea.l d0,a0
.l:     move.l  (a0)+,d0
        beq.s   .r
        move.l  (a0)+,d1
        cmpi.l  #'_MCH',d0
        bne.s   .l
        swap    d1
        cmpi.w  #3,d1
        bne.s   .r
        st      FALCON.l
.r:     rts

        org     $b8140
; hook1 -- stage 1 hand-over.  Only installed when a patch has `; stage: 1` (WAR.PRG's copy routine then ends in
; `jmp hook1` instead of `rts`).  Applies the stage-1 sites (all or nothing) and continues at $576.
hook1:  movem.l d0-d7/a0-a6,-(a7)
        move.w  sr,-(a7)
        move.l  #'PMPF',MARKER.l        ; preset failure marker
        moveq   #2,d7                   ; mandatory sites of stage 1 (the HD loader): a refusal skips everything
        bsr.w   APPLY
        bne.s   .o1
        moveq   #0,d7                   ; optional sites of stage 1
        bsr.w   APPLY
        bne.s   .o1                     ; refused: marker stays PMPF, stage 2's optional sites are skipped too
        tst.b   FALCON.l
        beq.s   .nf
        moveq   #4,d7                   ; Falcon-only stage 1 sites (class 4)
        bsr.w   APPLY
        bne.s   .o1
.nf:    move.l  #'PMP1',MARKER.l        ; stage 1 applied, stage 2 pending
.o1:    move.w  (a7)+,sr
        movem.l (a7)+,d0-d7/a0-a6
        jmp     $576.l                  ; what the original stub's `rts` did

        org     $b81f0
; apply -- d7 = site class = (stage - 1) + 2 * mandatory.  Pass 1 verifies the ORIGINAL bytes of every site of that class
; (nothing is written yet), pass 2 writes them.  Returns Z set if applied, Z clear if a mismatch refused the class.
; Clobbers d0-d6/a0-a4.
apply:  lea     TABLE.l,a0
.v1:    move.l  (a0)+,d0                ; site addr, 0 = end
        beq.s   .pass2
        move.w  (a0)+,d1                ; len
        move.w  (a0)+,d2                ; stage - 1
        movea.l a0,a1                   ; orig bytes
        adda.w  d1,a0
        adda.w  d1,a0                   ; next entry (orig + new)
        cmp.w   d7,d2
        bne.s   .v1
        movea.l d0,a3
        subq.w  #1,d1
.v2:    cmpm.b  (a1)+,(a3)+
        bne.s   .bad                    ; any mismatch: write nothing
        dbra    d1,.v2
        bra.s   .v1
.pass2: lea     TABLE.l,a0
.a1:    move.l  (a0)+,d0
        beq.s   .good
        move.w  (a0)+,d1
        move.w  (a0)+,d2
        adda.w  d1,a0                   ; skip orig
        movea.l a0,a2                   ; new bytes
        adda.w  d1,a0                   ; next entry
        cmp.w   d7,d2
        bne.s   .a1
        movea.l d0,a3
        subq.w  #1,d1
.a2:    move.b  (a2)+,(a3)+
        dbra    d1,.a2
        bra.s   .a1
.good:  moveq   #0,d0
        rts
.bad:   moveq   #1,d0
        rts

        org     $b8190
; hook2 -- stage 2 hand-over: the game proper is in place at $10A6 (WAR.PRG's stage 2 = DATA\SPRITE40.DAT's copy
; routine ends in `jmp hook2`).  Same register file and SR as the original `rts` to $10A6 gave.
hook2:  movem.l d0-d7/a0-a6,-(a7)
        move.w  sr,-(a7)
        cmpi.l  #'PMPF',MARKER.l
        beq.s   .o2                     ; stage 1 refused: leave the game untouched
        move.l  #'PMPF',MARKER.l
        moveq   #3,d7                   ; mandatory sites of stage 2
        bsr.w   APPLY
        bne.s   .o2
        moveq   #1,d7                   ; optional sites of stage 2
        bsr.w   APPLY
        bne.s   .o2                     ; refused: nothing optional written, the mandatory ones are in, marker stays PMPF
        move.l  #'PMPO',MARKER.l
.o2:    bsr.w   cacron                  ; (caches are off since init; the game proper is in place)
        move.w  (a7)+,sr
        movem.l (a7)+,d0-d7/a0-a6
        jmp     $10a6.l
; hook2: the instruction cache back on if ICMODE says so (only ever a non-zero ICVAL on a 68020+, so never executed on a 68000)
cacron: tst.b   ICMODE.l
        beq.s   .r
        move.l  ICVAL.l,d0
        beq.s   .r
        dc.w    $4e7b,$0002             ; movec d0,cacr
.r:     rts
