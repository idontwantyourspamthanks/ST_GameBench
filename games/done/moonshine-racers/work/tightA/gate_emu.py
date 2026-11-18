"""Exact 68000 model gate: reference (live prefix A) vs candidate (live prefix B): per pass full RAM below $70000 + both screen buffers.
python3 gate_emu.py LIVE_A LIVE_B LEVELS KINDS NPASS [mask=ranges 'lo-hi,lo-hi'] [xtest N] [neg]
Reports pass/frames compared, differing pixels (bytes) and RAM addresses (after masks)."""
import sys, collections, json
sys.path.insert(0, '/home/ryan/Code/AtariST/gamebench/games/in_progress/moonshine-racers/work/hud/build')
from emuhud import *
A, B = sys.argv[1], sys.argv[2]; levels = [int(x) for x in sys.argv[3].split(',')]; kinds = sys.argv[4].split(','); npass = int(sys.argv[5])
opts = sys.argv[6:]
mask = []
pokes = []; counts = []
counted = collections.Counter()
xtest = 0
for o in opts:
    if o.startswith('mask='):
        for r in o[5:].split(','):
            lo, hi = r.split('-'); mask.append((int(lo, 16), int(hi, 16)))
    if o.startswith('xtest='): xtest = int(o[6:])
    if o.startswith('poke='): pokes.append((int(o[5:].split('=')[0],16), bytes.fromhex(o.split('=')[2])))
    if o.startswith('count='): counts.append(int(o[6:],16))
TICK = 30
def run(dump, kind, live):
    e = Emu(dump); apply_live_p(e, live)
    if xtest: e.setb(0xB8F21, xtest)
    if live == B:
        for a, v in pokes: e.write(a, v)
        for c in counts: e.uc.hook_add(UC_HOOK_CODE, lambda uc, ad, sz, u: counted.__setitem__(ad, counted[ad] + 1), begin=c, end=c)
    fl = []
    def at_flip(uc, a, s, u):
        b = e.l(0x1008)
        fl.append((bytes(uc.mem_read(b, 0x7d00)), bytes(uc.mem_read(0x78000 if b == 0x70000 else 0x70000, 0x7d00)), e.w(0x100e), b))
    e.uc.hook_add(UC_HOOK_CODE, at_flip, begin=0xd1ca, end=0xd1ca)
    rams = []
    for p in range(npass):
        v = schedule(p, kind)
        if v is not None: e.setb(0x6105, v)
        if xtest:
            e.setb(0xB8F08, 0); e.setl(0xB8F00, TICK * (p + 1)); e.run(0x7a88, 0xb8100); e.run(0xb8100, 0x7b7a)
        else:
            e.run(0x7a88, 0x7b74); flip(e)
        rams.append(bytes(e.uc.mem_read(0, 0x70000)))
        e.run(0x7b7a, 0x7a88)
    return fl, rams
tot = collections.Counter(); badaddr = collections.Counter()
for L in levels:
    for kind in kinds:
        d = DUMPS % L
        fa, ra = run(d, kind, A); fb, rb = run(d, kind, B)
        tot['frames'] += min(len(fa), len(fb)); tot['passes'] += min(len(ra), len(rb))
        for x, y in zip(fa, fb):
            if x[0] != y[0]: tot['frames_differ'] += 1; tot['pixel_bytes_differ'] += sum(1 for i in range(0x7d00) if x[0][i] != y[0][i])
            if x[1] != y[1]: tot['other_buffer_differs'] += 1
        for pa, pb in zip(ra, rb):
            if pa != pb:
                a = np.frombuffer(pa, np.uint8); b = np.frombuffer(pb, np.uint8)
                idx = np.nonzero(a != b)[0]
                for i in idx:
                    if any(lo <= i <= hi for lo, hi in mask): tot['masked_bytes'] += 1; continue
                    badaddr[int(i)] += 1
        print('level', L, kind, dict(tot), 'bad RAM addrs', len(badaddr), flush=True)
print('RESULT frames compared %d, frames differing %d (pixel bytes %d), other-buffer differing %d, RAM passes %d, RAM differing addresses %d (masked bytes %d)' % (tot['frames'], tot['frames_differ'], tot['pixel_bytes_differ'], tot['other_buffer_differs'], tot['passes'], len(badaddr), tot['masked_bytes']))
print('executions in candidate:', {hex(k): v for k, v in counted.items()})
for a, n in sorted(badaddr.items())[:40]: print('  RAM $%05x differs in %d passes' % (a, n))
