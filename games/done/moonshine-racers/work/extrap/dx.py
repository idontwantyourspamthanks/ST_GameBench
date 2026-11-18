import sys
from gate3 import *
def run(dump, npass, ntest, patched, kind):
    e = Emu(dump)
    if patched: apply_live(e); e.setb(0xB8F21, ntest)
    F = []; R = []
    for p in range(npass):
        R.append(snap_ram(e))
        v = schedule(p, kind)
        if v is not None: e.setb(0x6105, v)
        if patched:
            e.setb(0xB8F08, 0); e.setl(0xB8F00, 36 * (p + 1))
            e.run(0x7a88, 0xb8100); F.append(e.read(e.l(0x1008), 0x7d00)); e.run(0xb8100, 0x7b7a)
        else:
            e.run(0x7a88, 0x7b74); F.append(e.read(e.l(0x1008), 0x7d00)); flip(e)
        e.run(0x7b7a, 0x7a88)
    return F, R
dump, npass, ntest, kind = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), sys.argv[4]
FA, RA = run(dump, npass, ntest, False, kind); FX, RX = run(dump, npass, ntest, True, kind)
first = next((p for p in range(npass) if FA[p] != FX[p]), None)
print("first differing frame", first)
if first is not None:
    p = first
    for q in range(max(0, p - 2), p + 1):
        bad = [a for a in range(0x1000, 0x70000) if RA[q][a] != RX[q][a]] + [a for a in range(0x80000, 0xb0000) if RA[q][a] != RX[q][a]]
        print("pass-start RAM diff at pass", q, ":", [f"{s:x}-{t:x}" for s, t in region_runs(bad)][:30])
if first is not None:
    import struct
    w = lambda R, a: struct.unpack(">H", R[a:a+2])[0]
    for q in (first-1, first):
        for n in range(12):
            b = 0x29c8 + n * 0x38
            print(q, n, "stock x,y,$28,$2a:", [hex(w(RA[q], b + o)) for o in (0, 2, 0x28, 0x2a)], " mx:", [hex(w(RX[q], b + o)) for o in (0, 2, 0x28, 0x2a)])
    print("bad bytes in frame:", [(i // 160, i % 160) for i in range(0x7d00) if FA[first][i] != FX[first][i]], "buffers", hex(struct.unpack(">I", RA[first][0x1008:0x100c])[0]))
if first is not None:
    q = first
    off = 63 * 160 + 49
    print("pass-start B0 byte (stock/mx) at row63 off49:", hex(RA[q][0x70000 + off]), hex(RX[q][0x70000 + off]), "B1:", hex(RA[q][0x78000 + off]), hex(RX[q][0x78000 + off]), "final frame:", hex(FA[q][off]), hex(FX[q][off]))
    print("bg $6f000 byte:", hex(RA[q][0x6f000 + off // 4 * 0]), "; $1008 =", hex(struct.unpack(">I", RA[q][0x1008:0x100c])[0]))
    # rows 55..70, groups 4..8: differences at pass start in buffer 0x70000
    d = [(i // 160, i % 160) for i in range(0x7d00) if RA[q][0x70000 + i] != RX[q][0x70000 + i] and 54 <= i // 160 <= 72 and 24 <= i % 160 < 80]
    print("pre-state B0 diffs rows54-72 bytes 24-79:", d[:40], len(d))
if first is not None:
    for q in range(first - 3, first + 1):
        bad = [a for a in range(0x6e000, 0x70000) if RA[q][a] != RX[q][a]]
        print("layer $6f000 area diff at pass-start", q, [f"{s:x}-{t:x}" for s, t in region_runs(bad)][:10])
