; name: mr_map
; default: yes
; site: $126d4
; orig: 044000065347
; doc: Faster minimap bitmap draw $12690 (pixel-identical): the per-plane btst/branch of the inner loop is resolved once per call by a jump into one of 16 unrolled row loops.
; note: Moonshine Racers render speed-up 2 (work/notes/render_patches.md).  $12690 (one caller, the minimap $f22c, with d2 = 1) copies a 1-bit shape (a1) over 3 sixteen-pixel groups x d7 rows into
; note: the four planes of the screen: plane n gets `or.w d1,(a0)+` if bit n of d2 is set, else `and.w ~d1,(a0)+`, decided by `btst`/branch per plane and group (about 176 cycles per group).
; note: Site: $126d4 `subi.w #6,d0 / subq.w #1,d7` (the last two instructions of the setup; the loop top $126da is not touched) -> `jmp $B3400.l`.  The blob replays them, indexes
; note: a table with d2 & 15 and jumps into one of 16 row loops (plane ops fixed per variant, the 3 groups unrolled), which end like the stock routine (d6 = $0000ffff, d7.w = $ffff,
; note: a0 after the last group, a1, a3, d1 = last shape word, d3 = its complement).  Every d2 value is implemented: no fallback to the stock loop.
        org     $126d4
        jmp     $B3400.l

        org     $B3400
PLANE   macro
        ifne    \1
        or.w    d1,(a0)+
        else
        and.w   d3,(a0)+
        endif
        endm
VAR     macro
.row:   movea.l a3,a0
        rept    3
        move.w  (a1)+,d1
        move.w  d1,d3
        not.w   d3
        PLANE   \1
        PLANE   \2
        PLANE   \3
        PLANE   \4
        endr
        lea     $a0(a3),a3
        adda.w  d0,a1
        dbra    d7,.row
        moveq   #0,d6
        subq.w  #1,d6
        rts
        endm
map:    subi.w  #6,d0
        subq.w  #1,d7
        moveq   #15,d6
        and.w   d2,d6
        add.w   d6,d6
        move.w  jt(pc,d6.w),d6
        jmp     jt(pc,d6.w)
jt:     dc.w    v0-jt,v1-jt,v2-jt,v3-jt,v4-jt,v5-jt,v6-jt,v7-jt,v8-jt,v9-jt,v10-jt,v11-jt,v12-jt,v13-jt,v14-jt,v15-jt
v0:     VAR     0,0,0,0
v1:     VAR     1,0,0,0
v2:     VAR     0,1,0,0
v3:     VAR     1,1,0,0
v4:     VAR     0,0,1,0
v5:     VAR     1,0,1,0
v6:     VAR     0,1,1,0
v7:     VAR     1,1,1,0
v8:     VAR     0,0,0,1
v9:     VAR     1,0,0,1
v10:    VAR     0,1,0,1
v11:    VAR     1,1,0,1
v12:    VAR     0,0,1,1
v13:    VAR     1,0,1,1
v14:    VAR     0,1,1,1
v15:    VAR     1,1,1,1
