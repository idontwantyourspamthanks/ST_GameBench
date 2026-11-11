"""sigcheck.py trace...: render writes into the bytes of the p7_skip signature (must be none: a snapshot taken before the render stays valid)."""
import sys
sys.path.insert(0, '.')
import rdset, chan
rdset.NEXTPC = False
sig = set()
def add(a, n): sig.update(range(a, a + n))
add(0x12c60, 36); add(0x12c98, 2); add(0x157a8, 2); add(0x159a0, 4); add(0x171f0, 46); add(0x19cd4, 4)
add(0x1d418, 2); add(0x1d816, 6); add(0x1cd64, 4); add(0x12d54, 2); add(0x1bbde, 4)
for i in range(4):
    a = 0x1cd7e + 0x2c * i
    add(a, 0x1c); add(a + 0x24, 4)
add(0x70010, 1248)
wr = {}
for path in sys.argv[1:]:
    recs = rdset.parse(path); ENTRY = chan.entries(path)
    phase = 'nr'; isr = []
    for (pc, mn, ops, nxt, line) in recs:
        if pc in ENTRY: isr.append(pc)
        if isr:
            if mn.startswith('rte'): isr.pop()
            continue
        if pc in chan.RS: phase = 'render'
        elif pc in chan.RE: phase = 'nr'
        if phase == 'render':
            for k, ea, sz in rdset.accesses(mn, ops):
                if k == 'W':
                    for b in range(ea, ea + sz):
                        if b in sig: wr.setdefault(b, set()).add(pc)
print('traces', len(sys.argv) - 1, 'render writes into signature bytes:', {hex(b): sorted(hex(p) for p in v)[:3] for b, v in sorted(wr.items())})
