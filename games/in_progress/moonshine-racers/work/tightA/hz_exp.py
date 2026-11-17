"""Horizon strip skip study in the Unicorn model.  python3 hz_exp.py LIVEPREFIX LEVELS KINDS NPASS
Per pass: key at $18318 entry, pre/post strip rows 0..199 diff, sprite-dirty rows (post-strip vs flip)."""
import sys, collections, json
sys.path.insert(0, '/home/ryan/Code/AtariST/gamebench/games/in_progress/moonshine-racers/work/hud/build')
from emuhud import *
live = sys.argv[1]; levels = [int(x) for x in sys.argv[2].split(',')]; kinds = sys.argv[3].split(','); npass = int(sys.argv[4])
def run(dump, kind):
    e = Emu(dump); apply_live_p(e, live)
    st = {}; rec = []
    def at_strip(uc, a, s, u):
        st['key'] = (e.l(0x12f0), e.w(0x12f6), e.w(0x12f8), e.w(0x1304), e.l(0x1008))
        st['pre'] = e.read(e.l(0x1008), 0x7d00)
        st['kraw'] = (e.w(0x12f8),)
    def at_post(uc, a, s, u):
        st['post'] = e.read(e.l(0x1008), 0x7d00)
    def at_flip(uc, a, s, u):
        b = e.l(0x1008)
        fin = e.read(b, 0x7d00)
        rec.append(dict(key=st['key'], pre=st['pre'], post=st['post'], fin=fin, p=e.w(0x100e)))
    e.uc.hook_add(UC_HOOK_CODE, at_strip, begin=0x18318, end=0x18318)
    e.uc.hook_add(UC_HOOK_CODE, at_post, begin=0x7b46, end=0x7b46)
    e.uc.hook_add(UC_HOOK_CODE, at_flip, begin=0xd1ca, end=0xd1ca)
    for p in range(npass):
        v = schedule(p, kind)
        if v is not None: e.setb(0x6105, v)
        e.run(0x7a88, 0x7b74); flip(e); e.run(0x7b7a, 0x7a88)
    return rec
def rows_diff(a, b):
    A = np.frombuffer(a, np.uint8).reshape(200, 160); B = np.frombuffer(b, np.uint8).reshape(200, 160)
    return np.nonzero((A != B).any(axis=1))[0]
out = []
for L in levels:
    for kind in kinds:
        rec = run(DUMPS % L, kind)
        last = {}
        for i, r in enumerate(rec):
            k = r['key']; b = k[4]
            kk = (k[0], k[1], k[2] & 0x1fc if False else (k[2] & 0xfc), k[3])
            same = (b in last and last[b] == kk)
            last[b] = kk
            d_strip = rows_diff(r['pre'], r['post'])
            d_strip = d_strip[(d_strip >= 40) & (d_strip < 130)]
            d_spr = rows_diff(r['post'], r['fin'])
            d_spr_h = d_spr[(d_spr >= 40) & (d_spr < 125)]
            out.append(dict(L=L, kind=kind, i=i, same=bool(same), key=[k[0], k[1], k[2], k[3]], strip_rows=[int(d_strip.min()), int(d_strip.max()), len(d_strip)] if len(d_strip) else None,
                            spr_rows=[int(d_spr_h.min()), int(d_spr_h.max()), len(d_spr_h)] if len(d_spr_h) else None, alld=[int(x) for x in rows_diff(r['post'], r['fin'])[:3]]))
        print('level', L, kind, 'passes', len(rec), 'same', sum(1 for o in out if o['L'] == L and o['kind'] == kind and o['same']), flush=True)
json.dump(out, open('hz_exp_%s.json' % sys.argv[5] if len(sys.argv) > 5 else 'hz_exp.json', 'w'))
