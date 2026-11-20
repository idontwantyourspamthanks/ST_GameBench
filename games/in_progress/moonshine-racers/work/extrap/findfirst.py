import sys
from pix3 import *
dump, ntest, kind = sys.argv[1], int(sys.argv[2]), sys.argv[3]
A = run_frames(dump, 200, ntest, False, kind); B = run_frames(dump, 200, ntest, True, kind)
first = next(p for p in range(200) if A[p] != B[p])
d = [(i//160, i%160) for i in range(0x7d00) if A[first][i] != B[first][i]]
print("first differing pass", first, len(d), "bytes; rows", d[0][0], "-", d[-1][0], "bytes x", min(x for r,x in d), "-", max(x for r,x in d))
def prep(patched, n):
    e = Emu(dump)
    if patched: apply_live(e); e.setb(0xB8F21, ntest)
    for p in range(n):
        v = schedule(p, kind)
        if v is not None: e.setb(0x6105, v)
        if patched: e.setb(0xB8F08,0); e.setl(0xB8F00,36*(p+1)); e.run(0x7a88,0x7b7a)
        else: e.run(0x7a88,0x7b74); flip(e)
        e.run(0x7b7a,0x7a88)
    return e
es = prep(False, first); ep = prep(True, first)
RS = snap_ram(es); RP = snap_ram(ep)
v = schedule(first, kind); es.setb(0x6105, v); es.run(0x7a88,0x7b74); FS = es.read(es.l(0x1008),0x7d00)
alld = [a for a in range(0, 0x80000) if RS[a] != RP[a] and not (0x70000 <= a < 0x78000) and not (0x78000 <= a < 0x7d000)]
print("pre-pass differing bytes (all RAM except screens):", len(alld))
for s, t in region_runs(alld)[:60]: print(f"  {s:05x}-{t:05x}")
