; Unit test: stock glyph kernel $14d98 vs mr_digit ($14d98 -> jmp $B3C00), d4 = every value 0..255 (random upper bits) x random rows, into a scratch screen at $C8000.
; Phase 0 restores the original bytes at $126d4 and runs every case, phase 1 writes the patch's jmp and runs the same cases; for each case the
; 15 registers (movem d0-d7/a0-a6) and a checksum of the 8 KB scratch screen are stored (64 B/case at $CA000 / $CE000) and compared.
; Results: $C5100 = cases compared, $C5104 = mismatching 32-bit words (0 = identical), $C5114 = 'DONE'.  Load at $C0000 (code < $C4000).
        org     $C0000
test:   movem.l d0-d7/a0-a6,-(a7)
        clr.l   $C5100.l
        clr.l   $C5104.l
        ; source bitmap: 8 KB pseudo-random at $C6000
        move.l  #$13572468,d6
        lea     $C6000.l,a0
        move.w  #2047,d5
.fs:    bsr     rnd
        move.l  d6,(a0)+
        dbra    d5,.fs
        ; phase 0: original bytes
        move.w  #$5347,$14d98.l
        move.w  #$284b,$14d9a.l
        move.w  #$1219,$14d9c.l
        move.l  #$CA000,$C5110.l
        bsr.s   runall
        ; phase 1: patch
        move.w  #$4ef9,$14d98.l
        move.w  #$000b,$14d9a.l
        ifd     NEG
        move.w  #$3c02,$14d9c.l                 ; negative control: enter the blob late
        else
        move.w  #$3c00,$14d9c.l
        endif
        move.l  #$CE000,$C5110.l
        bsr.s   runall
        ; compare the two result tables
        lea     $CA000.l,a0
        lea     $CE000.l,a1
        move.w  #(256*16)-1,d0
        moveq   #0,d1
.cm:    cmpm.l  (a0)+,(a1)+
        beq.s   .eq
        addq.l  #1,d1
.eq:    dbra    d0,.cm
        move.l  d1,$C5104.l
        move.l  #256,$C5100.l
        move.l  #'DONE',$C5114.l
        move.w  #$4eb9,$7b74.w
        move.l  #$d1e4,$7b76.w
        movem.l (a7)+,d0-d7/a0-a6
        jmp     $d1e4.l

; runall: 256 cases, case c: d2 = c & 15, random geometry from the case number
runall: moveq   #0,d4                  ; case counter (kept in d4 only between cases: saved in memory around the call)
.case:  move.w  d4,$C5120.l
        ; rng seeded by the case number
        move.l  #$9E3779B1,d6
        move.w  d4,d0
        addq.w  #1,d0
        mulu.w  #$2545,d0
        eor.l   d0,d6
        ; fill the scratch screen $C8000.. (8 KB) with pseudo-random data
        lea     $C8000.l,a0
        move.w  #2047,d5
.fd:    bsr     rnd
        move.l  d6,(a0)+
        dbra    d5,.fd
        bsr     rnd
        move.l  d6,$C5130.l
        bsr     rnd
        move.l  d6,$C5134.l
        bsr     rnd
        move.l  d6,$C5138.l
        move.l  $C5130.l,d4
        move.w  $C5120.l,d4            ; d4 low word = case number 0..255, upper random
        and.l   #$ffff00ff,d4          ; (the case number is < 256)
        move.l  $C5134.l,d7
        and.w   #$000f,d7
        addq.w  #1,d7                  ; rows 1..16
        move.l  $C5138.l,d0
        move.l  d0,d1
        move.l  d0,d2
        move.l  d0,d3
        move.l  d0,d5
        move.l  d0,d6
        lea     $C6000.l,a1
        lea     $C8000.l,a3
        movea.l #$55555555,a0
        movea.l #$66666666,a2
        movea.l #$77777777,a4
        movea.l #$99999999,a5
        movea.l #$aaaaaaaa,a6
        jsr     $14d98.l
        movem.l d0-d7/a0-a6,$C5200.l
        ; checksum of the scratch screen
        lea     $C8000.l,a0
        move.w  #2047,d1
        moveq   #0,d0
.sm:    add.l   (a0)+,d0
        rol.l   #3,d0
        dbra    d1,.sm
        move.l  d0,$C5240.l
        ; store 64 bytes: 15 regs + checksum
        movea.l $C5110.l,a0
        lea     $C5200.l,a1
        moveq   #15,d1
.cp:    move.l  (a1)+,(a0)+
        dbra    d1,.cp
        move.l  a0,$C5110.l
        move.w  $C5120.l,d4
        addq.w  #1,d4
        cmp.w   #256,d4
        bne     .case
        rts

rnd:    move.l  d6,d0
        lsl.l   #8,d0
        lsl.l   #5,d0
        eor.l   d0,d6
        move.l  d6,d0
        lsr.l   #8,d0
        lsr.l   #8,d0
        lsr.l   #1,d0
        eor.l   d0,d6
        move.l  d6,d0
        lsl.l   #8,d0
        lsl.l   #5,d0
        eor.l   d0,d6
        rts
