import sys
from proto import *
e = Emu(sys.argv[1])
for p in range(int(sys.argv[2])):
    e.run(0x7a88, 0x7b74)
    if p % 5: flip(e); e.run(0x7b7a, 0x7a88); continue
    flip(e)
    outs = []
    prev = snap_ram(e)
    for c in range(4):
        set_a5(e); e.call(0xef7a)
        cur = snap_ram(e)
        ch = [a for a in range(0, 0x7000) if cur[a] != prev[a]]
        outs.append(ch)
        prev = cur
        flip(e)
    print("pass", e.w(0x100e), "v", e.w(0x130c))
    for c, ch in enumerate(outs):
        print("  call", c, " ".join(f"{s:x}" + (f"-{t:x}" if t != s else "") for s, t in region_runs(ch)))
    flip(e)  # restore buffers parity (even number of flips total above: 4 + this 1 = odd), ignore
    e.run(0x7b7a, 0x7a88)
