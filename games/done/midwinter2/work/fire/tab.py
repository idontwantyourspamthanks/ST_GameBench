#!/usr/bin/env python3
"""Recompute the per-press counts from out/<label>.raw with the window = [down, next down) (a latched key can be fetched after the release).
usage: tab.py label ...   prints one line per press length: counts per press, mean, plus total over the held press."""
import re, sys, json
from pathlib import Path
O = Path('/home/ryan/Code/AtariST/gamebench/games/in_progress/midwinter2/work/fire/out')
BPS = {'TICK': 0x3148e, 'KEYC': 0x1aaa4, 'FIRE': 0x1ab8e, 'SPAWN': 0x35152, 'SPAWN2': 0x2a474}
def load(label):
    lg = (O / f'{label}.raw').read_text()
    js = json.loads((O / f'{label}.json').read_text())
    mm = list(re.finditer(r'> e VBL\n= [^\n]*#(\d+) \(dec\)[^\n]*\n> e CycleCounter\n= [^\n]*#(\d+)[^\n]*\(dec\)', lg))
    ev = js['events']
    assert len(mm) >= len(ev), (label, len(mm), len(ev))
    rows = []
    for k in range(len(ev) - 1):
        if not ev[k][1].startswith('down'): continue
        # next down (or end)
        j = k + 1
        while j < len(ev) - 1 and not ev[j][1].startswith('down'): j += 1
        seg = lg[mm[k].start(): mm[j].start()]
        cnt = {n: 0 for n in BPS}
        for m in re.finditer(r'\n\tpc = \$([0-9a-f]+) :trace', seg):
            for n, adr in BPS.items():
                if int(m.group(1), 16) == adr: cnt[n] += 1
        # ticks inside the held part only
        seg_h = lg[mm[k].start(): mm[k+1].start()]
        th = sum(1 for m in re.finditer(r'\n\tpc = \$3148e :trace', seg_h))
        am = [re.search(r'> m \$[0-9a-f]+ 1\n[0-9A-Fa-f]{8}: ([0-9a-f]{2})', lg[mm[q].start(): mm[q].start() + 600]) for q in (k, j)]
        if all(am):
            cnt['FIRE'] = int(am[0].group(1), 16) - int(am[1].group(1), 16)     # ammo byte is authoritative
        rows.append((ev[k][1], cnt, th, ev[k+1][0] - ev[k][0]))
    return js, rows
def lenms(js, name):
    return js['press_ms'][name]
def summary(label):
    js, rows = load(label)
    out = {}
    for name, cnt, th, vb in rows:
        out.setdefault(name, []).append((cnt['FIRE'], cnt['SPAWN'] + cnt['SPAWN2'], th))
    s = f"{label:16s} {js['machine']:8s} {js['mode']} w{js['weapon']:<2d} "
    parts = []
    for name, v in out.items():
        fires = [a for a, _, _ in v]
        parts.append(f"{lenms(js, name):6.0f}ms n={len(v)} fire/press={fires} mean={sum(fires)/len(fires):.2f} ticks/press={sum(t for *_, t in v)/len(v):.1f}")
    return s + '\n    ' + '\n    '.join(parts)
if __name__ == '__main__':
    for l in sys.argv[1:]:
        print(summary(l))
