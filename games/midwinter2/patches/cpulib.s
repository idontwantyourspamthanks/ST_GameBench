; cpulib.s — 68020+ helpers (identical copy of games/midwinter/patches/cpulib.s: keep both in step).  NOT a patch: the patch tool splices this text
; into two places: the boot-sector block of FFA (patches/floppy_cpu.s) and the cpufix segment of core.s at $B9F00; the boot sector and stub run before the payload exists.
; Everything here is position independent and uses no exceptions, so it is safe on a plain 68000 (cl_detect returns 0 and nothing else is called).
; Written for the TT / Falcon / any 68020+ (work/notes/tt.md): the boot chain carries copies of an FDC driver whose waits are fixed loop counts tuned
; for an 8 MHz 68000, and a 68030 does not snoop DMA / the loaders write code that its caches may hold.
;
; cl_detect: d0.b = 0 68000/68010, 1 68020/68030, 2 68040/68060.  Trashes d1,d2,a0,a1.
;   020+ is found by the index-register scale factor: a 68000/68010 ignores the scale bits of a brief extension word, a 68020+ applies it.
;   040/060 (vs 020/030) is read from the _CPU cookie ($5a0 jar) when TOS has one; no jar = 020/030.
cl_detect:
        moveq   #1,d0
        dc.w    $41fb,$0200             ; lea     (0,pc,d0.w*2),a0
        dc.w    $43fb,$0000             ; lea     (0,pc,d0.w),a1   (4 bytes behind the first: a1-a0 = 4 with scale ignored, 3 with scale 2)
        suba.l  a0,a1
        move.l  a1,d1
        moveq   #0,d0
        cmp.l   #4,d1
        beq.s   .r                      ; 68000/68010
        moveq   #1,d0
        move.l  $5a0.w,d1
        beq.s   .r                      ; no cookie jar: 68020/68030
        movea.l d1,a0
.ck:    move.l  (a0)+,d1
        beq.s   .r
        move.l  (a0)+,d2
        cmp.l   #'_CPU',d1
        bne.s   .ck
        cmp.l   #40,d2
        blt.s   .r
        moveq   #2,d0
.r:     rts

; cl_cacheoff: d0.b = class from cl_detect (>= 1): switch every cache off and flush it.  Trashes d1.
;   020/030: CACR = $0808 (CI + CD, EI = ED = 0).  040/060: cpusha bc, CACR = 0.
cl_cacheoff:
        cmp.b   #2,d0
        bcs.s   .c030
        dc.w    $f4f8                   ; cpusha  bc
        moveq   #0,d1
        dc.w    $4e7b,$1002             ; movec   d1,cacr
        rts
.c030:  move.l  #$0808,d1
        dc.w    $4e7b,$1002             ; movec   d1,cacr
        rts

; cl_patch: a0 -> table of {addr.l, size.w (2 or 4), value.l}, addr 0 ends.  Writes value (word or long) at addr.  Trashes d1,d2,a0,a1.
cl_patch:
.n:     move.l  (a0)+,d1
        beq.s   .e
        movea.l d1,a1
        move.w  (a0)+,d2
        move.l  (a0)+,d1
        cmp.w   #4,d2
        beq.s   .l
        move.w  d1,(a1)
        bra.s   .n
.l:     move.l  d1,(a1)
        bra.s   .n
.e:     rts
