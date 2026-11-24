; name: p6_slope
; default: yes
; data: $b8000 16384
; init: $77100
; note: no site: the edge-slope table used by p6_tri (master p6_slope / hotpaths2.md), 64 x 64 longs at $b8000 (HIGH area).  NOT a disk blob (16 KB would not fit the floppy's 26 free clusters, build/s5_tri failed to boot for that reason): the span is zero-filled by the stub's records and `init` (supervisor, once, ~0.1 s) computes it with the same divu the setup uses; the gate (wwgate hi@) compares it with a Python model.
;       T[dy][mag] = the value the triangle setup `$f342` computes with `divu` for an edge with |dx| = mag and dy rows:
;         dy >  mag :  (mag << 16) / dy                (the `swap d4 ; divu.w d1,d4 ; andi.l #$ffff,d4` branch)
;         dy <= mag : ((mag << 8) / dy) << 8           (the `lsl.l #8,d4 ; divu.w d1,d4 ; bvc ; andi.l #$ffff ; lsl.l #8` branch)
;       Both quotients fit 16 bits for mag <= 255 (so the `bvc` overflow branch `move.l #$10000` cannot be taken) and divu truncates, as `/` does here.  dy = 0 is never looked up (the setup rejects
;       equal y).  Row dy at $b8000 + dy * 256, column mag at + mag * 4.
        org     $77100
SLOPE   equ     $b8000
init:   movem.l d0-d2/a0,-(a7)
        lea     SLOPE+256.l,a0          ; row 0 (dy = 0) is never looked up: stays zero
        moveq   #1,d1                   ; dy
.row:   moveq   #0,d0                   ; mag
.col:   move.l  d0,d2
        cmp.w   d1,d0
        bge.s   .le
        swap    d2                      ; mag << 16
        divu.w  d1,d2
        andi.l  #$ffff,d2
        bra.s   .st
.le:    lsl.l   #8,d2                   ; mag << 8
        divu.w  d1,d2
        andi.l  #$ffff,d2
        lsl.l   #8,d2
.st:    move.l  d2,(a0)+
        addq.w  #1,d0
        cmp.w   #64,d0
        bne.s   .col
        addq.w  #1,d1
        cmp.w   #64,d1
        bne.s   .row
        movem.l (a7)+,d0-d2/a0
        rts
