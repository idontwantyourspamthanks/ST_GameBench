"""Compare two scripted runs flip by flip at the SAME loop (matched by the timer triple): variable block $33900..$33a4f (336 B: player, creatures, shot slot, flags, energy, scan pointer), grid cells in the capture
windows, and captured frame buffers.  Expected for np_shot vs the same build without it: identical unless a shot overlaps a creature."""
import sys, re, json
from pathlib import Path
sys.path.insert(0, '/home/ryan/Code/AtariST/gamebench/games/in_progress/nebulus/work/input')
import scripted2 as S
EQ = Path('/home/ryan/Code/AtariST/gamebench/games/in_progress/nebulus/work/shotmiss/eq')
S.W = EQ
def load(tag):
    txt = (EQ / 'sc' / tag / 'log.txt').read_text()
    fl = S.parse_flips(txt)
    d = {}
    for i, f in enumerate(fl):
        d.setdefault(f['timer'], []).append(f)
    return fl, d, txt
def frames(tag, txt):
    d = EQ / 'sc' / tag
    bases = re.findall(r'00038758:\s+([0-9a-f]{2}) ([0-9a-f]{2}) ([0-9a-f]{2}) ([0-9a-f]{2})', txt, re.I)
    caps = sorted(int(p.stem.split('_')[1]) for p in d.glob('fb_*_a.bin'))
    out = {}
    for k, b in zip(caps, bases):
        addr = int(''.join(b), 16)
        out[k] = (d / f'fb_{k}_{"b" if addr == 0x78000 else "a"}.bin').read_bytes()
    return out
def cmp(a, b):
    fa, da, ta = load(a); fb, db, tb = load(b)
    n = diff = 0; addrs = {}; first = None
    for t, lst in da.items():
        if len(lst) != 1 or t not in db or len(db[t]) != 1 or t == (32, 0, 0): continue
        n += 1
        x, y = lst[0], db[t][0]
        d = [0x33900 + i for i in range(len(x['blk'])) if x['blk'][i] != y['blk'][i]]
        if x['g1'] != y['g1'] or x['g2'] != y['g2']: d.append('grid')
        if d:
            diff += 1; first = first or t
            for ad in d: addrs[ad] = addrs.get(ad, 0) + 1
    fra, frb = frames(a, ta), frames(b, tb)
    ncap = sum(1 for k in fra if k in frb); ndiffcap = sum(1 for k in fra if k in frb and fra[k] != frb[k])
    px = sum(sum(1 for p, q in zip(fra[k], frb[k]) if p != q) for k in fra if k in frb)
    print(f'{a} vs {b}: {n} loops compared (matched by timer), {diff} differ; frame captures compared {ncap}, differing {ndiffcap} ({px} bytes)'
          + ('' if not addrs else '  differing addrs: ' + ', '.join(f'{(hex(k) if isinstance(k, int) else k)}x{v}' for k, v in sorted(addrs.items(), key=lambda kv: str(kv[0]))[:14]) + f' first at timer {first}'))
if __name__ == '__main__':
    for sc in sys.argv[2:]:
        cmp(f'{sc}_{sys.argv[1].split(":")[0]}', f'{sc}_{sys.argv[1].split(":")[1]}')
