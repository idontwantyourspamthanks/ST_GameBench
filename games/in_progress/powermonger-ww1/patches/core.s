; core.s -- Powermonger WW1 patch delivery mechanism (always installed by tools/wwpatch.py).  Evidence: work/notes/delivery.md.
; Modelled on games/done/powermonger/patches/core.s; differences: ONE hand-over (WW1 has a single packed program, no second stage), the
; payload lives at $72000 (work/notes/placement.md), no DMA-sound probe.  Falcon class (4): sites of `; falcon: yes` patches, applied only when `init` found a Falcon (master's fal_ym mechanism).
;
; Segments, assembled separately (wwpatch.py CORE_ORGS):
;   org $0      front    position independent.  First thing in the data segment that wwpatch.py appends to AUTO\WW1.PRG (TOS loads
;                        text+data).  The first 8 bytes of WW1.PRG's text (the original `Super(0)` call) became `jmp front.l; nop`
;                        (one relocation entry).  front copies the payload records that follow it to IMG ($72000), calls the payload's
;                        `uinit` (user mode), repeats the Super call, calls `init` (supervisor: caches off, init routines of other
;                        patches) and then resumes the original program at text offset 8.
;   org $72000  entry    'PMPA', init.
;   org $72140  hook     The packed program ends in a 32-byte copy routine that its plaintext stub pushes on the stack (WW1.PRG text
;                        $2cc): copy the unpacked game to $576, clear the tail, restore the registers, `rts` to $576.  wwpatch.py
;                        rewrites that routine so it ends in `jmp hook`.  The hook verifies the ORIGINAL bytes of every site, applies
;                        all of them or none and jumps to $576 with the exact register file, SR and a7 the original `rts` produced.
;   org $721f0  apply
; Site table (written by wwpatch.py): entries {addr.l len.w class.w orig[len] new[len]}, addr 0 ends; class = 2*mandatory.
; Mandatory sites (`; mandatory: yes`) are verified and applied as their own all-or-nothing group before the optional ones, so a refused
; optional patch still leaves a runnable game.
;
; Interface for the other patch authors (fixed addresses):
;   $727F8.l MARKER  'PMPO' every site applied, 'PMPF' refused (a verified original differed; nothing optional written), all zero = no hook ran
;   $727C0.. INITTBL up to 11 longs (0 ends): routines called by `init` (supervisor mode, TOS's vectors and state still intact: WW1.PRG has
;                    not run a single instruction of its own yet).  `; init: $addr` header.
;   $72790.. UINITTBL up to 11 longs: same, called earlier by `uinit` in USER mode (GEMDOS calls are safe there).  `; uinit: $addr` header.
;                    Routines get no arguments and may use every register.
; CPU caches (68020 and up, TT/Falcon): the unpacker's final `rts` runs into addresses the copy has just written with data writes, so a 68030
; instruction cache runs stale lines (master: Line-F at $672 on a TT).  WW1 uses the same stub.  `init` (supervisor, before the game's first
; instruction) switches every cache off [INFERENCE for WW1: copied from master where it was verified on TT 3.06; not run on WW1 yet].
TABLE   equ $72250
UINITTBL equ $72790
INITTBL equ $727c0
MARKER  equ $727f8
FALCON  equ $727f4                      ; byte: $ff on a Falcon (_MCH cookie high word 3), set by `init`; the hook then also applies the `; falcon: yes` sites (class 4)
IMG     equ $72000
HOOK    equ $72140
APPLY   equ $721f0
TPAMIN  equ $f8000                      ; minimum p_hitpa to install the payload: LOW area $72000-$77fff + HIGH area $b0000-$f6fff + the start-up stack below $f8000
PUSHOFF equ $2cc                        ; text offset of the original copy-routine pushes (wwpatch.py PUSH_OFF)
GAME    equ $576                        ; where the unpacked game starts: the copy routine's destination and the original `rts` target

        org     $0
front:  movea.l 4(a7),a0                ; TOS's basepage (the program's initial stack: return address, basepage pointer)
        cmpi.l  #TPAMIN,4(a0)           ; p_hitpa: the end of the program's TPA.  1 MB machine: $f8000 (TOS's screen), the program's start-up stack
        bcs.s   .refuse                 ; sits right below it.  Below that (512 KB: $78000) the payload area $72000.. would be the stack and the screen
        lea     img(pc),a0              ; the payload records: right behind this stub
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
; not enough RAM: install nothing.  The original copy routine (the 8 `move.l #imm,-(a7)` that build it on the stack, text offset PUSHOFF)
; goes back in place, so the game runs exactly as the original program does (on 512 KB without its resource cache); MARKER stays 0.
.refuse:lea     front(pc),a0
        suba.l  #TEXTLEN,a0             ; the program's text
        lea     PUSHOFF(a0),a0
        lea     .push(pc),a1
        moveq   #11,d0
.rl:    move.l  (a1)+,(a0)+
        dbra    d0,.rl
        clr.l   -(a7)                   ; the program's own first instruction, verbatim: Super(0)
        move.w  #$20,-(a7)
        trap    #1
        bra.s   .out
.push:  dc.l    $2f3c005c,$4e752f3c,$00204fef,$2f3c4cef,$7fff2f3c,$538166fa,$2f3c66fa,$42192f3c,$12d85380,$2f3c2549,$005c2f3c,$45fafffe
img:                                    ; payload records start here (not assembled; wwpatch.py appends them)

        org     $72000
        dc.l    'PMPA'
        bra.w   init                    ; IMG+4: supervisor init
        bra.w   uinit                   ; IMG+8: user-mode init
init:   movem.l d0-d7/a0-a6,-(a7)
        bsr.w   cacroff
        bsr.w   falcon
        bsr.w   ttlow
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

; Caches off (68020+; the 68000/68010 have none).  The CPU is found by executing instructions under temporary illegal / line-F handlers:
;   movec cacr,d0   68020/030/040/060 execute it, 68000/68010 raise illegal instruction ($10)
;   cpusha bc       68040/060 push + invalidate both caches; 68020/030 raise line F ($2c) -> CACR = CI + CD (clear both, EI/ED = 0)
; d0-d2/a0-a3 scratch.
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
        moveq   #0,d0
        dc.w    $4e7b,$0002             ; movec d0,cacr: everything off
        bra.s   .cdone
.ctrap: movea.l a2,a7                   ; drop the exception frame
        tst.w   d1
        beq.s   .cdone                  ; no CACR: 68000/68010
        cmpi.w  #2,d1
        beq.s   .cdone                  ; pmove below took line F: no PMMU (68020), the caches are already off
        move.l  #$0808,d0               ; 68020/030: CI + CD: clear both caches, EI/ED = 0 -> off
        dc.w    $4e7b,$0002             ; movec d0,cacr
; 68030 PMMU: TOS 3.x keeps its translation tables in low RAM (TT TOS 3.06: root table at $700, CRP = $80000002_00000700) and the game's stage-0
; copy overwrites them, so the next table walk faults (master notes/tt_mmu.md).  TOS's map of $0..$ffffff is the identity (I/O through TT1), so
; clearing TC.E (bit 31) leaves the game's address space as it is.  Caches are off (above); flush the ATC.
        moveq   #2,d1                   ; a line F from here on ends the routine (.ctrap above)
        subq.l  #4,a7
        dc.w    $f017,$4200             ; pmove tc,(a7)
        bclr    #7,(a7)                 ; TC.E = 0
        dc.w    $f017,$4000             ; pmove (a7),tc
        addq.l  #4,a7
        dc.w    $f000,$2400             ; pflusha
.cdone: move.l  a1,$10.w
        move.l  a3,$2c.w
        rts

; Falcon? _MCH cookie ($5a0 -> list of {tag, value}) high word 3 (ST 0, STE 1, TT 2, Falcon 3).  FALCON = 0 elsewhere (and without a cookie jar).
falcon: clr.b   FALCON.l
        move.l  $5a0.w,d0
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
        ; Falcon: the desktop may be a VGA 640 x 480 (or other) mode: Vsetmode(-1) reads the mode, Vsetmode(ST-compatible, 16 colours, 320 x 200, keeping the VGA / PAL bits)
        move.w  #-1,-(a7)
        move.w  #88,-(a7)               ; Vsetmode
        trap    #14
        addq.l  #4,a7
        andi.w  #$30,d0                 ; keep VGA ($10) and PAL ($20)
        ori.w   #$82,d0                 ; ST compatible, 4 bit planes, 40 columns
        move.w  d0,-(a7)
        move.w  #88,-(a7)
        trap    #14
        addq.l  #4,a7
.r:     rts

; TT: TOS 3.06's default desktop is TT medium (640 x 480, 4 bit): the ST-low game would be shown 2 x 2 tiled.  `ttlow` (_MCH cookie high word 2) writes the TT shifter mode
; $ffff8262 = 0 = ST low before the game's first instruction; the game then sets its own screen base and palette ($ff8240).
ttlow:  move.l  $5a0.w,d0
        beq.s   .r
        movea.l d0,a0
.l:     move.l  (a0)+,d0
        beq.s   .r
        move.l  (a0)+,d1
        cmpi.l  #'_MCH',d0
        bne.s   .l
        swap    d1
        cmpi.w  #2,d1
        bne.s   .r
        clr.b   $ffff8262.w
.r:     rts

        org     $72140
; hook -- the hand-over: WW1.PRG's copy routine ends in `jmp hook` instead of `rts`.  Applies the sites (all or nothing per group) and
; continues at $576.
hook:   movem.l d0-d7/a0-a6,-(a7)
        move.w  sr,-(a7)
        move.l  #'PMPF',MARKER.l        ; preset failure marker
        moveq   #2,d7                   ; mandatory sites: a refusal skips everything
        bsr.w   APPLY
        bne.s   .o
        moveq   #0,d7                   ; optional sites
        bsr.w   APPLY
        bne.s   .o                      ; refused: nothing optional written, the mandatory ones are in, marker stays PMPF
        tst.b   FALCON.l
        beq.s   .nf
        moveq   #4,d7                   ; Falcon-only sites (class 4)
        bsr.w   APPLY
        bne.s   .o
.nf:
        move.l  #'PMPO',MARKER.l
.o:     move.w  (a7)+,sr
        movem.l (a7)+,d0-d7/a0-a6
        jmp     GAME.l                  ; what the original stub's `rts` did

        org     $721f0
; apply -- d7 = site class = 2 * mandatory.  Pass 1 verifies the ORIGINAL bytes of every site of that class (nothing is written yet),
; pass 2 writes them.  Returns Z set if applied, Z clear if a mismatch refused the class.  Clobbers d0-d6/a0-a4.
apply:  lea     TABLE.l,a0
.v1:    move.l  (a0)+,d0                ; site addr, 0 = end
        beq.s   .pass2
        move.w  (a0)+,d1                ; len
        move.w  (a0)+,d2                ; class
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
