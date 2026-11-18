import sys, time, pickle
from gate3 import *
union = {}
def hk(uc, access, addr, size, value, ud):
    for i in range(size): union[addr + i] = union.get(addr + i, 0) + 1
t = time.time()
for dump, kind, n in (('h_start_7a88.bin', 'zig', 1700),):
    e = Emu(dump)
    h = e.uc.hook_add(UC_HOOK_MEM_WRITE, hk, begin=0x7000, end=0x19000)
    for p in range(n):
        v = schedule(p, kind)
        if v is not None: e.setb(0x6105, v)
        try:
            e.run(0x7a88, 0x7b74)
        except Exception as ex:
            print("stopped at pass", p, ex); break
        flip(e); e.run(0x7b7a, 0x7a88)
        if p % 200 == 0: print(p, len(union), time.time() - t, flush=True)
skip = lambda a: (0x7b00 <= a < 0x7b90) or (0xd100 <= a < 0xd140) or (0xdae0 <= a < 0xdb10)
u = {a: c for a, c in union.items() if not skip(a)}
pickle.dump(u, open('kern_union.pkl', 'wb'))
rr = region_runs(sorted(u))
print(len(u), "bytes", len(rr), "runs")
print(" ".join(f"{s:x}-{t:x}" for s, t in rr))
