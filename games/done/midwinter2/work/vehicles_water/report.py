"""Print the group-end comparison table from a saved run (logs/<tag>.pkl): report.py tag [...]"""
import pickle, sys
from vw import *
src = open('cmp.py').read().split("def main")[0]
exec(src)
for tag in sys.argv[1:]:
    ctl, pat = pickle.load(open(OUT / 'logs' / (tag + '.pkl'), 'rb'))
    bad = 0; lines = []
    for k in range(1, min(len(ctl), len(pat))):
        d = diff(ctl[k], pat[k]); c = ctl[k]
        fmt = ' '.join(f"{name(a)}:{v[0]}/{v[1]}" for a, v in sorted(d.items()))
        lines.append(f"{k:2d} T={c.w(0x6220)} X={c.l(0x66e6)} Y={c.l(0x66ea)} H={c.w(0x6742)} bank={c.sw(0x6746)} alt={c.sw(0x764c)} thr={c.sw(0x6750)} spd={c.sw(0x6772)} SUB={pat[k].w(0xb42e8)} " + ('EQ' if not d else 'DIFF ' + fmt))
        bad += bool(d)
    nb = sum(len(r) for r in [ctl[1]])
    lines.append(f'{tag}: groups {len(lines)} mismatching {bad}; compared bytes per group {len(ctl[1])}')
    (OUT / 'logs' / (tag + '.txt')).write_text('\n'.join(lines) + '\n')
    print('\n'.join(lines[-1:]))
