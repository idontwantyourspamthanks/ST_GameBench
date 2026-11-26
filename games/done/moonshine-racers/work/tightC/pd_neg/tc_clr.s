; name: tc_clr
; default: no
; site: $17c24
; orig: 41f900004ff8
; doc: Span-buffer clear $17c24 trimmed to the terminator: the 1136-byte clear (3.7 k cycles per pass) becomes 16 bytes.
; note: Moonshine Racers tighten-C (work/notes/tighten_c.md).  Stock $17c24 zeroes $4b78-$4ff7 every pass.  The only consumer of the zeros is the end test of the road draw
; note: (rd_draw `$B5004` rd_end and the stock loop `$18052`: `move.l 2(a1),d0 / dbeq`, the long after the last record).  The record stream is written downwards from $4f78 by $100b4,
; note: so the first record after the stream sits at $4f78 and its A:B long at $4f7a-$4f7d; $4f78-$4ff7 is never written by anything else (checked by a write trace over 200 passes).
; note: Site $17c24 (`lea.l $4ff8.l,a0`, 6 bytes) -> `jmp $B6800.l`; the blob zeroes $4f78-$4f87 and returns.  Registers left differ from stock (d0 = 0 only); no caller reads them.
        org     $17c24
        jmp     $B6800.l

        org     $B6800
tc_clr:
        moveq   #0,d0
        move.l  d0,$4f78.w
        move.l  d0,$4f7c.w
        move.l  d0,$4f80.w
        move.l  d0,$4f84.w
        rts
