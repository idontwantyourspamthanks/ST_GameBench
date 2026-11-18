; name: mr_negctl
; default: no
; site: $1058e
; orig: 2204
; doc: Gate negative control only (never shipped): breaks the road edge colour expansion on purpose.
; note: Negative control for tools/msrabtest.py: `$1058e move.l d4,d1` (first source of the edge colour routine $1058a) becomes `move.l d3,d1`:
; note: wrong on purpose, so every pixel gate must report DIFFER.  Used alone (`--only mr_negctl`).
        org     $1058e
        move.l  d3,d1
