"""outputs.py trace... : render-written bytes that non-render code (or an ISR) later reads before writing them.
These are the render's side effects that a skip would have to reproduce (or prove unused)."""
import sys, collections
sys.path.insert(0, '.')
import rdset, chan
rdset.NEXTPC = False
WRR = {}                       # byte -> pc of render writer (any pass, latest)
out = {}
for path in sys.argv[1:]:
    ENTRY = chan.entries(path)
    recs = rdset.parse(path)
    isr = []; phase = 'nr'
    Wnr = set()                # written by non-render since the last render write of the byte
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
            for b in range(ea, ea + size):
                if chan.is_screen(b): continue
                if ph == 'render':
                    if kind == 'W':
                        WRR[b] = pc; Wnr.discard(b)
                else:
                    if kind == 'W': Wnr.add(b)
                    elif b in WRR and b not in Wnr and b not in out:
                        out[b] = (pc, WRR[b])
iv = rdset.intervals(sorted(out))
for s, e in iv:
    print(f'{s:06x}-{e:06x} {e-s+1:4d} read by nr pc {sorted({hex(out[b][0]) for b in range(s,e+1) if b in out})[:4]} written by render pc {sorted({hex(out[b][1]) for b in range(s,e+1) if b in out})[:4]}')
