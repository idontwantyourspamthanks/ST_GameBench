"""Compare two Hatari profiles per function (call-target buckets): usage cmp_prof.py DUMP PROF_A PROF_B [--top N]
Reports cycles/frame (frames = flip $3868e entry count) per function for A and B and the difference B-A."""
import re, sys, bisect, struct
sys.path.insert(0, '/home/ryan/Code/AtariST/gamebench/tools')
import m68dis
dump, pa, pb = sys.argv[1:4]
top = int(sys.argv[sys.argv.index('--top') + 1]) if '--top' in sys.argv else 25
ram = open(dump, 'rb').read()
m68dis.CODE_LO, m68dis.CODE_HI = 0x33b00, 0x76000
t = set(m68dis.call_targets(ram))
for x in range(0x33b00, 0x76000 - 6, 2):
    if struct.unpack_from('>H', ram, x)[0] == 0x4EF9:
        y = struct.unpack_from('>I', ram, x + 2)[0]
        if 0x33b00 <= y < 0x76000 and y % 2 == 0: t.add(y)
tg = sorted(t)
def load(p):
    prof = {}
    for ln in open(p):
        m = re.match(r'^\$([0-9a-f]+)\s.*?([\d.]+)% \((\d+), (\d+),', ln)
        if m: prof[int(m.group(1), 16)] = (int(m.group(3)), int(m.group(4)))
    frames = prof.get(0x3868e, (0, 0))[0]
    b = {}
    for ad, (n, c) in prof.items():
        i = bisect.bisect_right(tg, ad) - 1
        f = tg[i] if i >= 0 and ad >= 0x33b00 else ad
        b[f] = b.get(f, 0) + c
    tot = sum(c for n, c in prof.values())
    idle = sum(c for ad, (n, c) in prof.items() if 0x3822c <= ad < 0x3827c)
    return b, frames, tot, idle
A, fa, ta, ia = load(pa); B, fb, tb, ib = load(pb)
print(f'A frames {fa} busy/frame {(ta-ia)/fa:.0f} spin {ia/fa:.0f} | B frames {fb} busy/frame {(tb-ib)/fb:.0f} spin {ib/fb:.0f}')
keys = set(A) | set(B)
rows = sorted(keys, key=lambda k: -abs(B.get(k, 0) / fb - A.get(k, 0) / fa))
print('func     A/frame   B/frame     diff')
for k in rows[:top]:
    a, b = A.get(k, 0) / fa, B.get(k, 0) / fb
    print(f'{k:06x} {a:9.0f} {b:9.0f} {b-a:+9.0f}')
