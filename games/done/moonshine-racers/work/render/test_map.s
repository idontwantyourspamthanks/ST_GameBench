; Unit test: stock minimap bitmap draw $12690 vs mr_map ($126d4 -> jmp $B3400), 16 values of d2 x 8 random geometries, into a scratch screen at $C8000.
; Phase 0 restores the original bytes at $126d4 and runs every case, phase 1 writes the patch's jmp and runs the same cases; for each case the
; 15 registers (movem d0-d7/a0-a6) and a checksum of the 8 KB scratch screen are stored (64 B/case at $CA000 / $CC000) and compared.
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
        move.w  #$0440,$126d4.l
        move.w  #$0006,$126d6.l
        move.w  #$5347,$126d8.l
        move.l  #$CA000,$C5110.l
        bsr.s   runall
        ; phase 1: patch
        move.w  #$4ef9,$126d4.l
        move.w  #$000b,$126d6.l
        ifd     NEG
        move.w  #$3404,$126d8.l                 ; negative control: enter the blob late
        else
        move.w  #$3400,$126d8.l
        endif
        move.l  #$CC000,$C5110.l
        bsr.s   runall
        ; compare the two result tables
        lea     $CA000.l,a0
        lea     $CC000.l,a1
        move.w  #(128*16)-1,d0
        moveq   #0,d1
.cm:    cmpm.l  (a0)+,(a1)+
        beq.s   .eq
        addq.l  #1,d1
.eq:    dbra    d0,.cm
        move.l  d1,$C5104.l
        move.l  #128,$C5100.l
        move.l  #'DONE',$C5114.l
        move.w  #$4eb9,$7b74.w
        move.l  #$d1e4,$7b76.w
        movem.l (a7)+,d0-d7/a0-a6
        jmp     $d1e4.l

; runall: 128 cases, case c: d2 = c & 15, random geometry from the case number
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
        bsr     rnd
        move.l  d6,$C513C.l
        bsr     rnd
        move.l  d6,$C5140.l
        bsr     rnd
        move.l  d6,$C5144.l
        move.l  $C5130.l,d3
        and.w   #$00f0,d3              ; d3 = source x offset (multiple of 16 px)
        move.l  $C5134.l,d0
        and.w   #$00f0,d0              ; d0 = dest x (pixels)
        move.l  $C5138.l,d1
        and.w   #$000f,d1              ; d1 = dest y
        move.l  $C513C.l,d5
        and.w   #$0030,d5
        add.w   #$30,d5                ; d5 = width 48..96 (pushed by the routine, becomes d0 after its prelude)
        move.l  $C5140.l,d7
        and.w   #$000f,d7
        addq.w  #1,d7                  ; d7 = rows 1..16
        move.l  $C5144.l,d4
        and.w   #$000f,d4              ; d4 = source row offset
        move.w  $C5120.l,d2
        and.w   #$000f,d2              ; d2 = c & 15
        move.w  #$0010,d6              ; pushed with d5: becomes d1
        lea     $C6000.l,a1
        lea     $C8000.l,a5
        movea.l #$55555555,a0
        movea.l #$66666666,a2
        movea.l #$77777777,a3
        movea.l #$88888888,a4
        movea.l #$99999999,a6
        jsr     $12690.l
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
        cmp.w   #128,d4
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
