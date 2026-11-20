"""lateral prediction quality at f=1: extra frame (k=v) vs the stock next frame: no lat extrapolation / predicted (cur+delta) / exact"""
import sys
from proto import *
from gate3 import schedule
dump, kind, NP = sys.argv[1], sys.argv[2], int(sys.argv[3])
e = Emu(dump)
tot = {'none': 0, 'pred': 0, 'exact': 0}; nz = {'none': 0, 'pred': 0, 'exact': 0}; n = 0
prev = None
for p in range(NP):
    v = schedule(p, kind)
    if v is not None: e.setb(0x6105, v)
    e.run(0x7a88, 0x7b74)
    A = snap_ram(e); cur = e.w(0x1318); vv = e.w(0x130c)
    base = 0x78000 if A[0x1008:0x100c] == b'\x00\x07\x00\x00' else 0x70000
    # stock next frame
    if v is not None: pass
    stock_next(e)
    S1 = buf(e, base); lat1 = e.w(0x1318); post = snap_ram(e)
    if prev is not None and vv and not (A[0x11b0] or A[0x11b1] or A[0x11b2]):
        n += 1
        d = (cur - prev) if abs(cur - prev) <= 12 else 0
        for name, lat in (('none', cur), ('pred', cur + d), ('exact', lat1)):
            load_ram(e, A); flip(e); extra_frame(e, vv, lat=lat)
            X = buf(e, base); df = sum(n_ for r, n_ in diffrows(S1, X)); tot[name] += df; nz[name] += (df > 60)
    prev = cur
    load_ram(e, A); flip(e); e.run(0x7b7a, 0x7a88)
print(f"{dump} {kind}: {n} passes; mean differing bytes of 32000 at f=1: " + ", ".join(f"{k} {tot[k]/max(n,1):.1f} (frames >60 bytes: {nz[k]})" for k in tot))
