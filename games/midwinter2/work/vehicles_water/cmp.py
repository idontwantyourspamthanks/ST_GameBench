"""Control (unpatched) vs sub-stepped run, group-end equality.
python3 cmp.py <tag> <snap> <ngroups> <ycnt> <xcnt> <typemask-hex> [patch list csv] [extra poke csv ';' sep]"""
import sys
from vw import *
NAMES = {0x1877c:'wavephase',0x1dfba:'waveptr',0x66e6:'X',0x66ea:'Y',0x6742:'H',0x6294:'H94',0x764a:'H4a',0x674e:'lean',0x6746:'bank',0x674a:'pitch',0x6750:'thr',0x6752:'r52',0x6756:'r56',0x675a:'r5a',
 0x6740:'d40',0x6772:'spd',0x764c:'alt',0x66e2:'r2',0x66e4:'r4',0x6290:'cd',0xf984:'f984',0xf986:'f986',0x6888:'b888',0x34936:'g36',0x34938:'g38',0x3493a:'g3a',
 0x676e:'p76e',0x66ee:'sv_x',0x66f2:'sv_y',0x66fe:'sv_alt',0x7646:'v46',0x7648:'v48',0x7652:'v52',0x7654:'v54',0x7680:'v80',0x688e:'b88e',0x6892:'b892',
 0x6766:'in66',0x6768:'in68',0x6774:'p74',0x6776:'p76',0x7642:'v42',0x7644:'v44',0x763e:'v3e',0x7640:'v40',0xeb8c:'clk',0xefb4:'efb4',0x6fb6:'mx',0x6fba:'my',0x6220:'type'}
IGN = set(range(0xb42e0, 0xb4300))
def name(a):
    for k in range(a - (a & 1), a - (a & 1) + 1):
        pass
    base = a & ~1
    for b in (a, base, a & ~3):
        if b in NAMES: return NAMES[b]
    return '%x' % base
def diff(c, p, ign=()):
    d = {}
    for a in c:
        if a in p and c[a] != p[a] and a not in IGN and (a & ~1) not in ign: d[a & ~1] = (c.w(a & ~1) if (a & ~1) + 1 in c else 0, p.w(a & ~1))
    return d
def main():
    tag, snap, n, yc, xc, mask = sys.argv[1], sys.argv[2], int(sys.argv[3]), int(sys.argv[4]), int(sys.argv[5]), int(sys.argv[6], 16)
    pl = sys.argv[7].split(',') if len(sys.argv) > 7 and sys.argv[7] else ['sw_head','sw_post','sw_ramp','sw_range','sw_probe2','sw_depth','sw_tail','sw_alt','p3b_pos','p3b_hdg','p3b_bank','p3b_save','p3b_probe']
    ex = [s for s in (sys.argv[8].split(';') if len(sys.argv) > 8 else []) if s]
    pokes = [wb(0x6fba, (yc & 0xffff) << 16, 4), wb(0x6fb6, (xc & 0xffff) << 16, 4)] + ex
    live = live_build(tag, OUT / 'patches', pl)
    ctl = run(SNAP / snap, tag + '_ctl', n, pokes=pokes)
    subren = any('b4e04' in e for e in ex)
    pat = run(SNAP / snap, tag + '_pat', n * 5 if subren else n, live=live, pokes=pokes + [wb(0xb4e00, mask, 4)])
    if subren:
        pat = [pat[0]] + [r for r in pat[1:] if r.w(0xb42e6) == 5]
    pickle.dump((ctl, pat), open(OUT / 'logs' / (tag + '.pkl'), 'wb'))
    bad = 0
    for k in range(1, min(len(ctl), len(pat))):
        d = diff(ctl[k], pat[k])
        fmt = ' '.join(f"{name(a)}:{v[0]}/{v[1]}" for a, v in sorted(d.items()))
        c = ctl[k]
        print(k, f"X={c.l(0x66e6)} Y={c.l(0x66ea)} H={c.w(0x6742)} T={c.w(0x6220)} bank={c.sw(0x6746)} alt={c.sw(0x764c)} SUB={pat[k].w(0xb42e8)}", 'EQ' if not d else 'DIFF ' + fmt)
        bad += bool(d)
    print('groups', min(len(ctl), len(pat)) - 1, 'mismatching', bad)
main()
