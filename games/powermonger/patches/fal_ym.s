; name: fal_ym
; default: yes
; stage: 1
; site: $b60c
; orig: 0dc9000022bb7018
; note: Falcon (work/notes/regression.md).  The title/intro program's sound interrupt (stage 1, $b5ee..$b624) writes the YM with
;       `movep.l d6,0(a1)` = four writes to $ff8800/02/04/06 (the ST decodes the mirrors as the same two registers), then a long
;       write of the next table entry to $ff8800.  A Falcon (Hatari) bus-errors on $ff8804/$ff8806 -> TOS bomb -> double bus error.
;       Replacement on EVERY machine: the same register writes in the same order through $ff8800/$ff8802 only
;       (two movep.w; the long write as its two live bytes: select = byte 0, data = byte 2).  d6 and a1 end as before;
;       a0 is saved.  The ST YM sees the identical register sequence; the IRQ costs about 70 cycles more [INFERENCE: not measured].
        org     $b60c
        jsr     $dc000.l
        nop
        org     $dc000
        swap    d6
        movep.w d6,0(a1)                ; bytes 3,2 of the original movep.l: select, data
        swap    d6
        movep.w d6,0(a1)                ; bytes 1,0: select, data (the original wrote them to the mirror $ff8804/06)
        move.l  a0,-(a7)
        lea     $b62a.l,a0              ; the table the original addressed pc-relative
        move.b  0(a0,d7.w),(a1)
        move.b  2(a0,d7.w),2(a1)
        movea.l (a7)+,a0
        rts
