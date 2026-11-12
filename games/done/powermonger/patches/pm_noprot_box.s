; name: pm_noprot_box
; default: yes
; site: $bee0
; orig: 43f90000bef6
; note: copy protection, part 2 of 2 (needs pm_noprot).  $bee0 is the "Please Wait For The Protection Check" box, called
;       once from the new-conquest start ($12fd2, after the first $13b9a); only the check ($b2d4 -> abcc at $b440) ever
;       closes it again.  With pm_noprot the check never runs, so the box is simply not opened (`rts`; the 4 bytes that
;       follow in the 6-byte site are padded with nops by pmpatch).
        org     $bee0
        rts
