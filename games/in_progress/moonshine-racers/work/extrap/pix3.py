"""emulator pixel gate: main frames of mx (with extras) vs stock, every tick. python3 pix3.py DUMP NPASS NTEST [input]"""
import sys
from gate3 import *
def run_frames(dump, npass, ntest, patched, kind):
    e = Emu(dump)
    if patched: apply_live(e); e.setb(0xB8F21, ntest)
    F = []
    for p in range(npass):
        v = schedule(p, kind)
        if v is not None: e.setb(0x6105, v)
        if patched:
            e.setb(0xB8F08, 0); e.setl(0xB8F00, 36 * (p + 1))
            e.run(0x7a88, 0xb8100)
            F.append(e.read(e.l(0x1008), 0x7d00))
            e.run(0xb8100, 0x7b7a)
        else:
            e.run(0x7a88, 0x7b74); F.append(e.read(e.l(0x1008), 0x7d00)); flip(e)
        e.run(0x7b7a, 0x7a88)
    return F
if __name__ == "__main__":
    dump, npass, ntest = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]); kind = sys.argv[4] if len(sys.argv) > 4 else None
    A = run_frames(dump, npass, ntest, False, kind); B = run_frames(dump, npass, ntest, True, kind)
    nd = 0; worst = 0
    for p in range(npass):
        d = sum(1 for i in range(0x7d00) if A[p][i] != B[p][i])
        if d:
            nd += 1; worst = max(worst, d)
            rows = diffrows(A[p], B[p])
            print(f"  pass {p}: {d} bytes, rows {rows[0][0]}..{rows[-1][0]} ({len(rows)} rows)")
    print(f"{dump} {npass} main frames, ntest={ntest}, input={kind}: frames differing {nd}, worst {worst} bytes")
