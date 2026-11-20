import sys, re
LINE = re.compile(r"^\$([0-9a-f]+)\s.*% \((\d+), (\d+), \d+, \d+\)\s*$", re.I)
d = {}
for ln in open(sys.argv[1]):
    m = LINE.match(ln)
    if m: d[int(m.group(1), 16)] = (int(m.group(3)), int(m.group(2)))
vbls = int(sys.argv[2])
def rng(lo, hi): return sum(c for a, (c, n) in d.items() if lo <= a < hi), sum(n for a, (c, n) in d.items() if lo <= a < hi)
print('flips', d.get(0xd1ca))
for nm, lo, hi in (('VBL d11e-d138', 0xd11e, 0xd138), ('d486-d616 (VBL body: palette setup, d138/d19a)', 0xd486, 0xd616), ('d138-d1a8 (ikbd cmd)', 0xd138, 0xd1ca), ('TimerB d616-d6fa', 0xd616, 0xd6fa), ('YM 8bf0-9100', 0x8bf0, 0x9100), ('ACIA cfb4-d060', 0xcfb4, 0xd060), ('d2d4-d486 fades/etc', 0xd2d4, 0xd486), ('mt_clock b8000', 0xb8000, 0xb8030), ('ta blobs BE000-BEFFF', 0xbe000, 0xbf000)):
    c, n = rng(lo, hi)
    print('%-48s cycles/VBL %9.0f  insn/VBL %8.1f' % (nm, c / vbls, n / vbls))
tot = sum(c for c, n in d.values()); print('total cycles/VBL', tot / vbls)
