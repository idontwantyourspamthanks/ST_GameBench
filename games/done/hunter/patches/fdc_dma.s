; name: fdc_dma
; default: yes
; floppyonly: yes
; site: $d50e
; orig: 610cdc034a03
; note: Paper Bag floppy only (the loader copied to $d30e).  The loader's DMA sector read ends in `bsr.b $d51c` (wait for the FDC
; note: command) / `add.b d3,d6` / `tst.b d3` at $d50e..$d513.  On a 68020/030 (TT, Falcon) the data cache does not see the DMA
; note: that filled the buffer, and this loader never cleared it.  core_floppy.s therefore switched the 68030 data cache OFF for the
; note: whole run (work/notes/tt_v12.md: the 3D view ran at 5-10 VBL per frame instead of 1).  Now the cache stays ON and this hook
; note: clears it (CACR CD) after every FDC command, as TOS's own drivers do.  The three displaced instructions run first and
; note: last, in the same order, so the flags the `bne.b $d49e` behind the site tests are the original's.
; note: FLAGS bit 4 = "68020/030 with the data cache on" (set by core_floppy.s stage 2 only after the payload applied every site,
; note: so the hook is certainly in place); everywhere else (68000/68010, 68040/060, no hook) the hook is the original code plus
; note: one flag test.  d0 (the loader's sector number) is preserved.
FLAGS3  equ     $8bff3

        org     $d50e
        jsr     $8d360.l

        org     $8d360
fdc_dma:
        jsr     $d51c.l                 ; the displaced `bsr.b $d51c`: wait for the command; d3.b = error flag
        add.b   d3,d6                   ; the displaced `add.b d3,d6`
        btst    #4,FLAGS3.l
        beq.s   .out                    ; 68000/68010, 68040/060 or no flush wanted
        move.l  d0,-(a7)
        dc.w    $4e7a,$0002             ; movec cacr,d0
        ori.w   #$0800,d0               ; CD: clear the data cache (the DMA wrote the buffer behind its back)
        dc.w    $4e7b,$0002             ; movec d0,cacr
        move.l  (a7)+,d0
.out:   tst.b   d3                      ; the displaced `tst.b d3` (flags for the `bne.b $d49e` that follows)
        rts
