import sys, re; sys.path.insert(0,'.')
from tlib import *
from live import *
src=open('c.s').read() if False else """
sync:   jsr     $d1ca.l
        move.b  $611b.w,$b8100.l
        rts
wait:   move.w  d0,-(a7)
.w:     move.b  $b8100.l,d0
        cmp.b   $611b.w,d0
        beq.s   .w
        clr.b   $611a.l
        move.w  (a7)+,d0
        jmp     $17c42.l
"""
blob, sy = assemble(0xb8000, src, syms=True)
sites=[(0xd1e4, b"\x4e\xf9"+sy["sync"].to_bytes(4,"big")), (0x7b0a, b"\x4e\xb9"+sy["wait"].to_bytes(4,"big"))]
h = open_snap("ste1m_race_start.sav", 8)
try:
    apply_live(h, [(0xb8000, blob)], sites)
    time.sleep(1)
    pcs=[0x7b74, sy["wait"], 0x17c42, 0x7a88]
    log = chain(h, pcs, ["e VBL","e FrameCycles","m $611b 2","m $b8100 2"], 6)
finally:
    h.close()
print(log[-2500:])
