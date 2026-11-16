"""f=1 oracle over N passes: extra frame (k=v) vs the stock frame n+1, per pass."""
import sys
from proto import *
dump = sys.argv[1]; N = int(sys.argv[2]); stages = STAGES_EXTRA
e = Emu(dump)
tot = 0
for p in range(N):
    e.run(0x7a88, 0x7b74)
    A = snap_ram(e); v = e.w(0x130c); pos = e.w(0x5ff8); cnt = e.w(0x100e)
    stock_next(e)
    S1 = buf(e, 0x78000 if A[0x1008:0x100c] == b'\x00\x07\x00\x00' else 0x70000)
    base = 0x78000 if A[0x1008:0x100c] == b'\x00\x07\x00\x00' else 0x70000
    stock_post = snap_ram(e)
    lat1 = e.w(0x1318)
    load_ram(e, A); flip(e)
    extra_frame(e, v, lat=(lat1 if len(sys.argv) > 3 else None))
    X1 = buf(e, base)
    d = diffrows(S1, X1)
    nb = sum(n for r, n in d)
    tot += nb
    print(f"pass {cnt} v={v} 5ff8={pos} rows={len(d)} bytes={nb} {d[:12]}")
    # continue the stock run
    load_ram(e, stock_post)
    e.uc.reg_write(UC_M68K_REG_PC, 0x7b74)
    # we are at 7b74 of pass n+1: loop continues via run(0x7a88..)? emulate: flip+tail+head happen at loop top via run below
    e.run(0x7b74, 0x7b74+0) if False else None
    # re-enter: after pass n+1 body (at 7b74), do flip/tail/head so the next iteration starts at 7a88 of pass n+2
    flip(e); e.run(0x7b7a, 0x7a88)
print("total differing bytes", tot)
