; name: pop_detail
; default: yes
; prog: populous
; site: $14416
; orig: 161a67000010
; data: $bd6c0 16
; note: F5 Detail Level toggle (High / Low) for Populous 1.
;       Data at $bd6c0: +0 DETAIL.w (0 = High, 1 = Low), +2 BANNER.l (VBL stamp + 1 for 2s top-strip flash).
;       In Low Detail: skips decorative trees/rocks ($32..$34 in map_bk2) while keeping all buildings/settlements/people.
;       Companion pop_detail_w freezes water animation; pop_cliff skips stacked cliff faces.  Blob $b6800.

        org     $14416
        jmp     $b6800.l

        org     $b6800
det_obj:
        move.b  (a2)+,d3
        beq.s   .skip
        tst.w   $bd6c0.l                ; Low Detail?
        beq.s   .draw
        cmp.b   #$32,d3                 ; decorative trees/rocks ($32..$34)?
        blo.s   .draw
        cmp.b   #$34,d3
        bls.s   .skip
.draw:  jmp     $01441c.l
.skip:  jmp     $01442a.l
