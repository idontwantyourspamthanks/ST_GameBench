; name: p4_walk_test
; default: yes
; site: $19de4
; note: item #3 (render.md s8), part 2/2 (needs p4_walk_pro, p4_walk_save, p4_walk_ret_a/b together).
; note: Terrain polygon driver sub_019d6a calls the walker (`bsr $19f20`, whose first act is the edge-window test
; note: $19ed4: 8 compares, 197 cy, reject => the whole polygon is dropped via $19f1e) and then does
; note: `tst.w $19f1e / bne.w $19e06`. Those 14 bytes become `jsr blob / bra.s $19df2`.
; note: The blob skips the test only when it is provably redundant: both endpoints of the edge ((a2,d5.w) and
; note: 2(a2,d5.w) = vertex offsets, as the driver itself loaded them at $19da0/$19dbc) have outcode word
; note: $6(a3,vertex) == 0. The outcode is computed against $171f0-$171f6 ($15d0a-$15d32: bit0 x<xmin, bit1 x>xmax,
; note: bit2 y<ymin, bit3 y>ymax; clipped vertices store x,y,0 at $182c4-$182f2 after the Cohen-Sutherland
; note: re-test; the 4 window corners of $17f20 are the bounds themselves). With the frame guard `walk_fast` == 0
; note: ($171f0.. == $12d4a.. == test bounds) outcode 0 => the test passes. Otherwise (outcode != 0, stale slot, guard
; note: failed) the original walker entry runs, test included, and its $19f1e verdict is honoured as before.
; note: Object polygons (driver $19e08, list $1db80) are NOT touched: they keep the test.
        org     $19de4
        jsr     $b4310.l
        bra.s   $19df2
        nop
        nop
        nop

        org     $b4310
        tst.w   $b4300.l
        bne.s   slow
        move.w  (a2,d5.w),d0
        tst.w   6(a3,d0.w)
        bne.s   slow
        move.w  2(a2,d5.w),d0
        tst.w   6(a3,d0.w)
        bne.s   slow
        movem.l a0-a1,-(a7)             ; the walker's (trimmed) save
        jmp     $19f2c.l                ; walker body past the test; its rts returns to $19dea (bra.s)
slow:   jsr     $19f20.l                ; original entry: save, test, body
        tst.w   $19f1e.l
        bne.s   rej
        rts
rej:    addq.l  #4,a7                   ; drop the return into the site
        jmp     $19e06.l                ; = the driver's rts, as the original `bne.w $19e06`
