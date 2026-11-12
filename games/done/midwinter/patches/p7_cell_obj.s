; name: p7_cell_obj
; default: yes
; site: $1748c
; note: P7 cell early-outs (work/notes/p7_cell.md), part 2/2 of the object-cell filter (needs p7_cell_pre, which fills the
; note: table and sets VALID; without it VALID is 0 and the original sub_01d41e always runs).
; note: sub_017444 (one call per terrain cell) does `jsr $1d41e.l` (6 bytes, $1748c) before the corner-outcode test:
; note: sub_01d41e scans the in-range object list for the cell (`cmp.w (a6)+,d0 / bne / dbra`, ~28 cy per entry, 262 cy per call
; note: on average) and pushes (`$1743a`, `$c6(a6)`) on the painter list for every match. With no match it only reloads
; note: and stores $18bda unchanged. The blob looks up the cell in the per-frame table p7_cell_pre filled (byte at
; note: ((a5.w >> 6) & $ff), 0 = cell cannot be in the list, same hash for every list entry) and returns at once; any other
; note: case runs the original routine (`jmp $1d41e.l`, its rts returns to $17492).
; note: Registers at $1748c: d1-d4 = corner words (live), d5-d7 dead, d0 dead (sub_01d41e clobbers it too). The blob uses d0 only.
TBL     equ     $b5200
VALID   equ     $b5300

        org     $1748c
        jsr     $b51a0.l

        org     $b51a0
        move.w  VALID(pc),d0
        beq.s   .orig
        move.w  a5,d0
        lsr.w   #6,d0
        and.w   #$ff,d0
        move.b  TBL(pc,d0.w),d0
        bne.s   .orig
        rts
.orig:  jmp     $1d41e.l
