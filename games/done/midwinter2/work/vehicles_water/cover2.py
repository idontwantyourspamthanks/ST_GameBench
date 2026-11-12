"""render-read bytes that the logic ('pre'/'post'/ISR) writes: all of them, grouped, with reader/writer pcs.  usage: cover2.py trace.txt"""
import sys
sys.path.insert(0, '../p7_skip')
import rdset
rdset.NEXTPC = False
ENTRY = {0x263de, 0x26298, 0x26882}
Wnr = {}; R = {}
for path in sys.argv[1:]:
    recs = rdset.parse(path)
    isr = []; phase = 'pre'; Wr = set()
    for (pc, mn, ops, nxt, line) in recs:
        inisr = False
        if pc in ENTRY: isr.append(pc)
        if isr:
            inisr = True
            if mn.startswith('rte'): isr.pop()
        if not inisr:
            if pc == 0x31486: phase = 'pre'; Wr = set()
            elif pc == 0x5056: phase = 'render'
            elif pc == 0x315a8: phase = 'post'
        ph = 'isr' if inisr else phase
        for kind, ea, size in rdset.accesses(mn, ops):
            for b in range(ea, ea + size):
                if 0x60000 <= b < 0x80300 or 0x7d00 <= b < 0x8100: continue
                if ph == 'render':
                    if kind == 'W': Wr.add(b)
                    elif b not in Wr: R.setdefault(b, pc)
                elif kind == 'W': Wnr.setdefault(b, (ph, pc))
ch = sorted(b for b in R if b in Wnr)
def isobj(b):
    return 0x3532 <= b < 0x3532 + 30 * 0x42 or 0x3cee <= b < 0x3cee + 30 * 0x18 or 0x4bfa8 <= b < 0x4bfa8 + 90 * 16
iv = rdset.intervals([b for b in ch if not isobj(b)])
for s, e in iv:
    print(f'  {s:06x}-{e:06x} {e-s+1:3d}  read pc {R[s]:x}  written {Wnr[s][0]} pc {Wnr[s][1]:x}')
print('object-record bytes (NPC/effects/markers):', sum(1 for b in ch if isobj(b)))
