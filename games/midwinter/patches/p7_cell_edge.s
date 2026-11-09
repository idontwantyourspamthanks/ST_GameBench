; name: p7_cell_edge
; default: yes
; site: $17ca0
; note: P7 cell early-outs (work/notes/p7_cell.md). sub_017c6c (emit path of an all-valid, not-rejected cell) loads the four
; note: corner outcode words into d0-d3 ($17c6c-$17c92), tests their AND (reject), then calls the screen-space edge clipper
; note: sub_017fa0 five times (slots $152/$14/$2/$4/$6 of the cell, $17ca0-$17cc4). Each slot holds the two corner vertices
; note: of an edge of this cell ($17a04); sub_017fa0 returns at $182fa without touching any state when both endpoint
; note: outcodes are 0 (`or` -> beq at $17fc2; the slot's vertices are corners of this cell, shared slots hold the same vertex
; note: pair, and an edge whose endpoints are both inside is never rewritten by a neighbour: only clipped/rejected edges are).
; note: So when d0|d1|d2|d3 == 0 all five calls are no-ops: the first 8 bytes (`lea $152(a5),a4 / bsr.w $17fa0`) become a
; note: jump to the blob, which skips to $17cc8 in that case and otherwise does the original first call.
        org     $17ca0
        jmp     $b5400.l
        nop

        org     $b5400
        move.w  d0,d4
        or.w    d1,d4
        or.w    d2,d4
        or.w    d3,d4
        beq.s   .skip
        lea     $152(a5),a4
        jsr     $17fa0.l
        jmp     $17ca8.l
.skip:  jmp     $17cc8.l
