import sys, json; sys.path.insert(0,'.')
from tlib import *
from live import *
from msr import flips_pc, peeks
variant, snap, mhz, vbls = sys.argv[1], sys.argv[2], int(sys.argv[3]), int(sys.argv[4])
NOP2 = bytes.fromhex("4e714e71")
blobs, sites = [], []
if variant == "B":      # no post-flip wait at all
    sites = [(0xd1f2, NOP2)]
elif variant == "C":    # post-flip wait moved to just before the first back-buffer write ($17c42); floor removed
    blob = assemble(0xb8000, """
sync:   jsr     $d1ca.l
        move.b  $611b.w,$b8100.l
        rts
wait:   move.w  d0,-(a7)
        move.b  $b8100.l,d0
.l:     cmp.b   $611b.w,d0
        beq.s   .l
        clr.b   $611a.l
        move.w  (a7)+,d0
        jmp     $17c42.l
""")
    # sync at $b8000 (len 18), wait at $b8000+len(sync)
    import re
    blobs = [(0xb8000, blob)]
    # compute wait address: sync = jsr.l(6) + move.b abs.w,abs.l (8) + rts(2) = 16
    sites = [(0xd1e4, bytes.fromhex("4ef9") + (0xb8000).to_bytes(4, "big")), (0x7b0a, bytes.fromhex("4eb9") + (0xb8000 + 16).to_bytes(4, "big"))]
h = open_snap(snap, mhz)
try:
    if sites: apply_live(h, blobs, sites)
    time.sleep(1)
    v0 = h.vbl()
    while h.vbl() < v0 + 100: time.sleep(0.4)
    w0, vb0 = peeks(h), h.vbl()
    f = flips_pc(h, vbls)
    w1, vb1 = peeks(h), h.vbl()
    d = {k: ((w1[k] - w0[k] + 0x8000) & 0xFFFF) - 0x8000 for k in w0}
    print(json.dumps(dict(variant=variant, snap=snap, clock=mhz, **f, vbl_elapsed=vb1 - vb0, delta=d, per_sec={k: round(v * 50.0 / (vb1 - vb0), 2) for k, v in d.items()})), flush=True)
finally:
    h.close()
