; name: p6_slope
; default: yes
; stage: 2
; note: PMPerf2, work/notes/hotpaths2.md.  Data only (no site): the edge-slope table used by p6_tri, 64 x 64 longs at $d5000.
;       T[dy][mag] = the value the triangle setup `$ef62` computes with `divu` for an edge with |dx| = mag and dy rows:
;         dy >  mag :  (mag << 16) / dy                (the `swap d4 ; divu.w d1,d4 ; andi.l #$ffff,d4` branch, $f00e)
;         dy <= mag : ((mag << 8) / dy) << 8           (the `lsl.l #8,d4 ; divu.w d1,d4 ; bvc ; andi.l #$ffff ; lsl.l #8` branch, $f01a)
;       Both quotients fit 16 bits for mag <= 255 (so the `bvc` overflow branch `move.l #$10000` cannot be taken) and divu truncates, as `/` does
;       here.  dy = 0 is never looked up (the setup rejects equal y).  Row dy at $d5000 + dy * 256, column mag at + mag * 4.
        org     $d5000
dy      set     0
        rept    64
mag     set     0
        rept    64
        if      dy=0
        dc.l    0
        else
        if      dy>mag
        dc.l    (mag<<16)/dy
        else
        dc.l    ((mag<<8)/dy)<<8
        endif
        endif
mag     set     mag+1
        endr
dy      set     dy+1
        endr
