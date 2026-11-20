; core_floppy.s - Moonshine Racers FLOPPY patch delivery mechanism (always installed by msrpatch.py build --floppy).  Assembled at IB (the payload image base, `IB equ $B2700`,
; supplied by the tool together with TABLE).
;   IB+0      marker: 'MSPO' = every site matched and was applied, 'MSPF' = a site's original bytes did not match, nothing was applied
;             (absent / zero = the trampoline never ran).
;   IB+8      trampoline: entered by the `jmp IB+8.l` that replaces PP's patcher tail in RUNME's stack-phase block (text $45c: `jmp $1000.w`;
;             disk A \$C350 = RAM \$6f50 = the game's own entry stub `move.l #$6f5a,$88.w / trap #2`), i.e. the game is loaded and about to start (supervisor, IPL 3, every patch site
;             loaded).  VERIFIES every site's original bytes (pass 1), APPLIES all of them only if every site matched (pass 2), writes the marker,
;             flushes the 68020+ caches, and ends with the displaced `jmp $1000.w` (-> `bra.w $6f50`, the game).
;   IB+4      stage 0 (the boot-sector loader, msrpatch.py floppy_loader) stores here, after the payload is read, TOS' phystop ($42e) on an ST / Mega ST / STE / Mega STE (TT and Falcon: 0, from the
;             `_MCH` cookie): the game's own loader wipes $400-$66000 at VBL ~99, so $42e is gone when the trampoline runs.  The trampoline reads it for the gate, then clears it: 0 = list 2 not
;             applied, $ff = applied.
;   TABLE     site table list 1 {addr.l len.w rsv.w orig.l new.l} (16 B per site, a zero 16-byte slot ends it), then list 2 at TABLE2 (the sites of the patches marked `; gate: ram2mb`),
;             then the orig/new byte pool.  List 2 is verified and applied only if phystop >= 2 MB (and stage 0 let the machine through); everything else runs the stock game after list 1.
MARKER  equ IB

        org     IB+8
trampoline:
        movem.l d0-d7/a0-a6,-(a7)
        move.w  sr,-(a7)                ; flags/mode exactly as PP's tail left them
        move.l  #'MSPF',MARKER.l        ; preset failure marker
        lea     TABLE.l,a4              ; list 1: every machine
        suba.l  a5,a5                   ; list 2 (the `; gate: ram2mb` sites): a5 = 0 = gate closed
        cmpi.l  #$200000,MARKER+4.l     ; gate: phystop >= 2 MB (0 on a TT / Falcon: stage 0 stored nothing there)
        scc     d0
        clr.l   MARKER+4.l              ; IB+4 is the 'list 2 applied' flag from here on
        tst.b   d0
        beq.s   .g
        lea     TABLE2.l,a5             ; gate open
.g:     movea.l a4,a0
        bsr.s   verify                  ; pass 1: verify every site of both lists
        bne.s   .done
        move.l  a5,d0
        beq.s   .a
        movea.l a5,a0
        bsr.s   verify
        bne.s   .done
.a:     movea.l a4,a0                   ; pass 2: apply all
        bsr.s   apply
        move.l  a5,d0
        beq.s   .ok
        movea.l a5,a0
        bsr.s   apply
        st      MARKER+4.l              ; list 2 applied
.ok:    move.l  #'MSPO',MARKER.l
.done:  bsr.s   cflush
        move.w  (a7)+,sr
        movem.l (a7)+,d0-d7/a0-a6
        move.l  #$6f5a,$88.w            ; the displaced game entry: install the trap #2 handler
        trap    #2                      ; ... and enter the game exactly as the original stub did

verify: move.l  (a0)+,d0                ; a0 = list; addr 0 = end (returns Z = 1); a mismatch returns Z = 0
        beq.s   .r
        move.w  (a0)+,d1                ; length
        addq.l  #2,a0                   ; reserved
        movea.l (a0)+,a1                ; orig bytes
        addq.l  #4,a0                   ; new bytes (pass 2)
        movea.l d0,a3
        subq.w  #1,d1
.vc:    cmpm.b  (a1)+,(a3)+
        dbne    d1,.vc
        beq.s   verify                  ; whole site matched
.r:     rts

apply:  move.l  (a0)+,d0
        beq.s   .r
        move.w  (a0)+,d1
        addq.l  #2,a0
        addq.l  #4,a0                   ; orig bytes
        movea.l (a0)+,a2                ; new bytes
        movea.l d0,a3
        subq.w  #1,d1
.aw:    move.b  (a2)+,(a3)+
        dbra    d1,.aw
        bra.s   apply
.r:     rts

; cflush: flush the instruction/data caches of a 68020+ (the patched code and the blobs were just written as data).  A 68000/68010 does nothing.
;   020+ is found by the index-register scale factor: a 68000/68010 ignores the scale bits of a brief extension word, a 68020+ applies them
;   (same test as midwinter2 cpulib.s `cl_detect`).  020/030: CACR |= CI+CD (clear bits, write-only).  040/060 (cookie _CPU >= 40, the jar may be
;   absent: then 020/030): cpusha bc.  Trashes d0-d2/a0-a1 (the caller saved them).
cflush: moveq   #1,d0
        dc.w    $41fb,$0200             ; lea     (0,pc,d0.w*2),a0
        dc.w    $43fb,$0000             ; lea     (0,pc,d0.w),a1   (4 bytes behind the first: a1-a0 = 4 with the scale ignored, 3 with scale 2)
        suba.l  a0,a1
        move.l  a1,d1
        cmp.l   #4,d1
        beq.s   .r                      ; 68000/68010: nothing to flush
        move.l  $5a0.w,d1
        beq.s   .c030                   ; no cookie jar: 68020/68030
        movea.l d1,a0
.ck:    move.l  (a0)+,d1
        beq.s   .c030
        move.l  (a0)+,d2
        cmp.l   #'_CPU',d1
        bne.s   .ck
        cmp.l   #40,d2
        blt.s   .c030
        dc.w    $f4f8                   ; cpusha  bc
        rts
.c030:  dc.w    $4e7a,$1002             ; movec   cacr,d1
        ori.l   #$0808,d1               ; CI + CD
        dc.w    $4e7b,$1002             ; movec   d1,cacr
.r:     rts
