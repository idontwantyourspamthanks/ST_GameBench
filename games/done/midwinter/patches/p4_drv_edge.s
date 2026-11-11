; name: p4_drv_edge
; default: yes
; site: $19d8c
; note: item #10 (render.md s8). Terrain polygon driver sub_019d6a, per edge: $19d8c-$19de3 (88 bytes, 14 word loads
; note: through ring a1 / edge a2 / vertex a3 tables) resolves the edge (d5 = edge offset (a1,d6.w)) into its two
; note: end points d1,d2 / d3,d4, ordered by comparing the edge's 2nd vertex v2 = 2(a2,d5) with both vertices of the NEXT
; note: ring edge (nv1 = (a2,e'), nv2 = 2(a2,e'), e' = (a1,(2(a1,d6)))): if v2 == nv1 or v2 == nv2 the order is
; note: (v1,v2) (orig $19dcc), else (v2,v1) (orig $19db0). Same decision, fewer loads: each vertex/edge pair is fetched
; note: with one move.l (word pair is contiguous: v1,v2 at (a2,e) and x,y at (a3,v)); d1/d3 get x:y as a long, the
; note: unpack gives x in the low word of d1/d3 and y in d2/d4. Upper words of d1-d4 are dead: the walker only
; note: uses word ops on them ($19f20..: cmp.w, sub.w, ext.l d3, swap d1 + move.w d5,d1). d5 stays the edge offset
; note: (p4_walk_test reads (a2,d5.w) / 2(a2,d5.w)); d0 is dead (reloaded by the next edge). The loop branch
; note: `bne.w $19d8c` and the original tail at $19de4 are unchanged. The block is shorter than 88 bytes: the rest is
; note: never-executed padding between the B path's bra.s and the A path.
        org     $19d8c
        move.w  (a1,d6.w),d5
        move.w  2(a1,d6.w),d4
        move.w  (a1,d4.w),d4
        move.l  (a2,d4.w),d3            ; nv1:nv2
        move.l  (a2,d5.w),d0            ; v1:v2
        cmp.w   d0,d3                   ; nv2 == v2 ?
        beq.s   pa
        swap    d3
        cmp.w   d0,d3                   ; nv1 == v2 ?
        beq.s   pa
        move.l  (a3,d0.w),d1            ; B: p1 = v2
        swap    d0
        move.l  (a3,d0.w),d3            ;    p2 = v1
        bra.s   pu
        nop
        nop
        nop
        nop
        nop
        nop
        nop
        nop
        nop
        nop
        nop
        nop
        nop
pa:     swap    d0                      ; A: p1 = v1
        move.l  (a3,d0.w),d1
        swap    d0
        move.l  (a3,d0.w),d3            ;    p2 = v2
pu:     move.w  d1,d2
        swap    d1
        move.w  d3,d4
        swap    d3
