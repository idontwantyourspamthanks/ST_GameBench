"""emulator gate: stock vs (extras then stock) per-pass state; restore policy given as list of ranges restored from A"""
import sys
from proto import *

def runs(addrs):
    return [(s, t) for s, t in region_runs(sorted(addrs))]

def gate(dump, npass, ks_frac=(1/3, 2/3), restore=(), mask=(), verbose=True, lo=0, hi=0x70000):
    e = Emu(dump)
    e.run(0x7a88, 0x7b74)                      # pass n body done
    A0 = snap_ram(e)
    # stock reference run
    stock = []
    load_ram(e, A0)
    for p in range(npass + 1):
        stock.append(snap_ram(e))
        flip(e); e.run(0x7b7a, 0x7a88); e.run(0x7a88, 0x7b74)
    # extras run
    load_ram(e, A0)
    diffs = {}
    for p in range(npass + 1):
        A = snap_ram(e)
        for a in range(lo, hi):
            if A[a] != stock[p][a]:
                if any(m0 <= a < m1 for m0, m1 in mask): continue
                diffs.setdefault(a, []).append(p)
        v = e.w(0x130c)
        flip(e)
        e2 = None
        kprev = 0
        if v:
            for f in ks_frac:
                k = int(round(f * v))
                if k > kprev:
                    extra_frame(e, k - kprev); kprev = k
        # restore from A
        for (a, n) in restore:
            e.write(a, A[a:a+n])
        # state at this point corresponds to "after flip", compare with stock[p] after flip? stock[p] is before flip; do the same flip on a copy
        e.run(0x7b7a, 0x7a88); e.run(0x7a88, 0x7b74)
    return diffs

if __name__ == "__main__":
    d = gate(sys.argv[1], int(sys.argv[2]))
    print(len(d), "differing bytes")
    for s, t in runs(d):
        print(f"{s:05x}-{t:05x} ({t-s+1}) in {len(set(p for a in range(s,t+1) for p in d.get(a,[])))} passes")
