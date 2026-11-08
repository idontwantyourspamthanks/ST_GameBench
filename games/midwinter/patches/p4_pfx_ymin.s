; name: p4_pfx_ymin
; default: no
; site: $1b1ce
; note: item #5 part 2/4. Fill setup sub_01b1bc (every polygon, terrain and objects): `move.w $1a618.l,d0` loads the
; note: polygon's first row (ymin; $7000 = no spans, skipped by the next compare). Record the frame's smallest in
; note: YMIN ($b4806, reset to 200 by p4_pfx_fill). All pixels a polygon writes are in rows >= its ymin ($1b1ea..: rows
; note: ymin, ymin+1, ...). The following original `cmp.w #$7000,d0` recomputes the flags.
YMIN    equ     $b4806
        org     $1b1ce
        jmp     $b4440.l
        org     $b4440
        move.w  $1a618.l,d0             ; displaced
        cmp.w   YMIN.l,d0
        bge.s   .n
        move.w  d0,YMIN.l
.n:     jmp     $1b1d4.l
