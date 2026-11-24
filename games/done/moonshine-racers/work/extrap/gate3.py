"""emulator gate: stock vs mx per pass state equality over many passes, with input patterns. python3 gate3.py DUMP NPASS NTEST [input-schedule]"""
import sys
from gate2 import *
def schedule(p, kind):
    if kind == 'up': return 0x01
    if kind == 'upleft': return 0x05 if (p // 20) % 2 == 0 else 0x01
    if kind == 'zig': return [0x01, 0x05, 0x01, 0x09][(p // 15) % 4]
    return None
def runs_(dump, npass, ntest, patched, kind):
    e = Emu(dump)
    if patched:
        apply_live(e); e.setb(0xB8F21, ntest)
    S = []
    for p in range(npass):
        v = schedule(p, kind)
        if v is not None: e.setb(0x6105, v)
        if patched:
            e.setb(0xB8F08, 0); e.setl(0xB8F00, 36 * (p + 1)); e.run(0x7a88, 0x7b7a)
        else:
            e.run(0x7a88, 0x7b74); flip(e)
        S.append(snap_ram(e)); e.run(0x7b7a, 0x7a88)
    return e, S
if __name__ == "__main__":
    dump, npass, ntest = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]); kind = sys.argv[4] if len(sys.argv) > 4 else None
    es, S = runs_(dump, npass, ntest, False, kind)
    ep, P = runs_(dump, npass, ntest, True, kind)
    bad = {}
    for p in range(npass):
        for a in list(range(0x1000, 0x7000)) + list(range(0x7000, 0x19000)):
            if S[p][a] != P[p][a] and not masked(a): bad.setdefault(a, []).append(p)
    vs = sorted(set(P[p][0x130c] * 256 + P[p][0x130d] for p in range(npass)))
    print(f"{dump} {npass} passes ntest={ntest} input={kind}: groups {ep.l(0xB8F3C)}/{ep.l(0xB8F40)} ticks; speeds seen {vs[:12]}; differing logic bytes: {len(bad)}",
          [f"{s:x}-{t:x}@{min(bad[s])}" for s, t in region_runs(sorted(bad))][:12])
