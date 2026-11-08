; name: p4_walk_pro
; default: no
; site: $19ce6
; note: item #3 (render.md s8), part 1/2 (needs p4_walk_test, p4_walk_save, p4_walk_ret_a/b together).
; note: Frame prologue of the painter-list raster sub_019ce2: the 4 moves $19ce6-$19d0d copy the window $12d4a-$12d50
; note: into the walker's edge-test bounds $19f16-$19f1c. The first move (10 bytes) is replaced by a jmp into the blob,
; note: which does the same move, then sets the guard word `walk_fast` = 0 iff the terrain clip window
; note: $171f0-$171f6 (the bounds of every outcode, written only by sub_0128bc at mode set-up) equals $12d4a-$12d50,
; note: i.e. iff "outcode 0" <=> "inside the edge-test bounds". Scratch d0/d1: $19ce2 saved d0-d7/a0-a6 and loads d0 first.
        org     $19ce6
        jmp     $b4200.l
        nop
        nop

        org     $b4200
        move.w  $12d4c.l,$19f18.l       ; the original instruction
        moveq   #-1,d0
        move.w  $12d4a.l,d1
        cmp.w   $171f0.l,d1
        bne.s   .set
        move.w  $12d4c.l,d1
        cmp.w   $171f2.l,d1
        bne.s   .set
        move.w  $12d4e.l,d1
        cmp.w   $171f4.l,d1
        bne.s   .set
        move.w  $12d50.l,d1
        cmp.w   $171f6.l,d1
        bne.s   .set
        moveq   #0,d0
.set:   move.w  d0,$b4300.l
        jmp     $19cf0.l

        org     $b4300
walk_fast: dc.w $ffff                  ; 0 = guard ok (set every frame by the prologue above)
