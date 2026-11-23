; name: pm_noprot_box
; default: yes
; site: $bbd2
; orig: 43f90000bbe8
; note: copy protection, part 2 of 2 (needs pm_noprot).  Port of master's pm_noprot_box (master $bee0 -> WW1 $bbd2).  $bbd2 is the "Please Wait For The
;       Protection Check" box (`lea $bbe8,a1 ; jsr $759a`), opened once from the new-conquest start; only the check ($acc4 -> $a5d4) ever closes it again.
;       With pm_noprot the check never runs, so the box is simply not opened (`rts`; the 4 bytes that follow in the 6-byte site are padded with nops).
        org     $bbd2
        rts
