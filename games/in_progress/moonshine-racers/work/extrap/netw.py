"""union of net-changed low-RAM bytes of extra frames (k = v/3, 2v/3, v cumulative) over scenes/passes"""
import sys
from proto import *
union = {}
for dump in sys.argv[2:]:
    e = Emu(dump)
    for p in range(int(sys.argv[1])):
        e.run(0x7a88, 0x7b74)
        A = snap_ram(e); v = e.w(0x130c)
        flip(e)
        pre = snap_ram(e)
        for k in (max(1, v//3), v):
            extra_frame(e, k)
        post = snap_ram(e)
        for a in range(0, 0x70000):
            if pre[a] != post[a] and not (0x70000 <= a < 0x80000):
                union[a] = union.get(a, 0) + 1
        # continue stock: restore A and go on
        load_ram(e, A)
        flip(e); e.run(0x7b7a, 0x7a88)
print(len(union), "bytes")
for s, t in region_runs(sorted(union)):
    print(f"{s:05x}-{t:05x} ({t-s+1}) max-count {max(union[a] for a in range(s,t+1))}")
