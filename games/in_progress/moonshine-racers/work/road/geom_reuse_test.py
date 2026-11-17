"""Standing-frame reuse: for each scene frame with speed 0, run patched twice (first: full + save; second: reuse) from the same stage-a RAM and compare both with stock (whole RAM)."""
import sys
from rdlib import *
prefix = sys.argv[1]
SITES = [(0x100b4, 0x100c0)]
def masked(m):
    m = bytearray(m)
    for a, b in SITES: m[a:b] = bytes(b - a)
    return bytes(m)
bad = 0; n = 0; cyc = []
for sc, plist in [('grid', range(0, 60, 7)), ('drive', range(55, 60))]:
    for p in plist:
        f = load(sc, p); ram = ram_for(f, 'a')
        if int.from_bytes(f['a_lo'][0x30c:0x30e], 'big') != 0: continue
        e1 = Emu(ram); e1.call(0x17c24); e1.call(0x100b4); m1 = masked(e1.rd(0, 0xB2700))
        e2 = Emu(ram); apply_live(e2, prefix); e2.call(0x17c24); c_full = e2.call(0x100b4); m2 = masked(e2.rd(0, 0xB2700))
        keep = e2.rd(0xC0000, 0xB000)
        # second call: same stage-a state, patched tables + saved result present
        e3 = Emu(ram); apply_live(e3, prefix); e3.wr(0xC0000, keep); e3.call(0x17c24); c_re = e3.call(0x100b4); m3 = masked(e3.rd(0, 0xB2700))
        n += 1
        for tag, m in (('full', m2), ('reuse', m3)):
            if m != m1:
                bad += 1; d = [i for i in range(0xB2700) if m1[i] != m[i]]; print('MISMATCH', sc, p, tag, len(d), [hex(x) for x in d[:8]])
        cyc.append((c_full, c_re))
print('standing frames', n, 'mismatches', bad, 'cycles (full+save, reuse):', cyc[:3])
