; name: pm_intro_pal
; default: yes
; stage: 1
; site: $660
; orig: 23c000002ca2
; note: PMTT, work/notes/tt.md.  The intro sets every picture's 16 colours with two `movem.l $table,d0-d4` / `movem.l d0-d4,$ffff8240` and
;       `movem.l d0-d4,$ffff8250` (5 longs = 20 bytes each, the second one overlapping the first and running 4 bytes PAST the palette: the
;       fifth long goes to $ff8260 / $ff8262).  On an ST / STE $ff8260 gets the high byte of that long (0: low resolution) and $ff8262 does not
;       exist; on a TT $ff8262 is the TT shifter mode: the long is the next table's first word, e.g. $0776, and the high byte of the word, the
;       red nibble of that colour, is the TT resolution mode (Hatari: `TTRes = byte($ff8262) & 7`).  A 7 switches to TT high (1280 x 960
;       mono), 4 to TT low: the text and castle pictures are black, the display flashes between modes (user report: weird flashes).
;       Nine stores in stage 1 have that shape (`48f9 001f ffff8250` at $6e4 $71e $a70 $d32 $d6c $da6 $f9a $12a2 $12de).  Fixing them needs nine
;       sites, so this patch has ONE (the first instruction of the intro sequence, `move.l d0,$2ca2.l` at $660, run once): it executes the
;       displaced instruction, then rewrites the register mask word of each of the nine stores from $001f (d0-d4) to $000f (d0-d3: 16 bytes,
;       exactly $ff8250..$ff825f) after checking it is still $001f.  On an ST / STE only the two bytes at $ff8260 are no longer written, with
;       the value they already hold (0), so nothing changes there.
        org     $660
        jmp     $cd800.l

        org     $cd800
pp:     move.l  d0,$2ca2.l              ; the displaced instruction
        movem.l d1/a0-a1,-(a7)
        lea     tbl(pc),a0
.l:     move.w  (a0)+,d1
        beq.s   .d
        movea.w d1,a1                   ; sign-extended: all addresses < $8000
        cmpi.w  #$001f,(a1)
        bne.s   .l
        move.w  #$000f,(a1)
        bra.s   .l
.d:     movem.l (a7)+,d1/a0-a1
        jmp     $666.l                  ; `jmp $660` from $57c: on with the next instruction
tbl:    dc.w    $6e6,$720,$a72,$d34,$d6e,$da8,$f9c,$12a4,$12e0,0
