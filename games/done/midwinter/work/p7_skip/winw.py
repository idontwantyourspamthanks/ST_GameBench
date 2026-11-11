"""winw.py trace... : non-render (and render) writes into the three screen buffers, by row range / byte-column range."""
import sys, collections
sys.path.insert(0, '.')
import rdset, chan
rdset.NEXTPC = False
for path in sys.argv[1:]:
    ENTRY = chan.entries(path)
    recs = rdset.parse(path)
    isr = []; phase = 'nr'
    nr = collections.defaultdict(set); rr = collections.defaultdict(set)
    for (pc, mn, ops, nxt, line) in recs:
        if pc in ENTRY: isr.append(pc)
        inisr = bool(isr)
        if inisr:
            if mn.startswith('rte'): isr.pop()
            ph = 'isr'
        else:
            if pc in chan.RS: phase = 'render'
            elif pc in chan.RE: phase = 'nr'
            ph = phase
        for kind, ea, size in rdset.accesses(mn, ops):
            if kind != 'W': continue
            for b in range(ea, ea + size):
                if chan.is_screen(b) and b < 0x80000 and b != 0:
                    off = (b - 0x58000) % 0x10000
                    if off >= 32000: continue
                    row, col = divmod(off, 160)
                    (rr if ph == 'render' else nr)[(b - 0x58000) // 0x10000].add((row, col, pc))
    print(path)
    for name, d in (('non-render', nr), ('render', rr)):
        for buf, s in sorted(d.items()):
            rows = sorted({r for r, c, p in s})
            cols = sorted({c for r, c, p in s})
            pcs = sorted({hex(p) for r, c, p in s})[:6]
            print(f'  {name} buf{buf}: rows {rows[0]}..{rows[-1]} ({len(rows)} distinct) cols {cols[0]}..{cols[-1]} bytes {len(s)} pcs {pcs}')
