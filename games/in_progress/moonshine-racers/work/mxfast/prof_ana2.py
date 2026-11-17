"""Category totals of a prof_mx.py output.  python3 prof_ana2.py OUT.txt X|M|G"""
import sys, re, collections
from mflib import *
f, v = sys.argv[1], sys.argv[2]
pf = GAME + {'X': '/patches/mx_sync.s', 'M': '/patches/mf_sync.s', 'G': '/patches/mg_sync.s'}[v]
txt = open(f).read(); ci = txt.index('profile counts'); cy = txt.index('profile cycles')
TXT = {}
def tab(t):
    d = {}
    for m in re.finditer(r'^0x([0-9a-f]{6})\s+[\d.]+%\s+(\d+)\s+(.*)$', t, re.M): d[int(m.group(1), 16)] = int(m.group(2)); TXT[int(m.group(1), 16)] = m.group(3).strip()
    return d
cnt = tab(txt[ci:cy]); cyc = tab(txt[cy:])
lm = labelmap(pf); sy = symbols(pf)
def lab(a):
    best = None
    for x, l in lm:
        if x <= a: best = l
        else: break
    return best
groups = cnt.get(sy['saveundo'], 0)
extras = cnt.get(sy.get('prerestore', sy.get('slotreset')), 0) if v != 'G' else None
# frames drawn = executions of the first instruction after `.frame` flip counter: use jsr $17c42 count in the blob = executions of label extras.go
frames = cnt.get(dict((l, a) for a, l in lm)['extras.go'], 0)
ticks = cnt.get(sy['extras'], 0)
cat = collections.Counter()
def category(a):
    l = lab(a) or ''
    if a < 0xb8100: return 'mt_clock'
    if 0xb8200 <= a < 0xb8300: return 'latch wait of the main pass (mt_pre, idle)'
    if l == 'extras.g': return 'latch wait of the extra frame (idle)'
    if v != 'G' and 0xb8300 <= a < 0xb8380: return 'pre copy (mx_pre/mf_pre)'
    if (v == 'G' and 0xb8180 <= a < 0xb8200) or l.startswith('newsync.rd') : return 'sleep loop (idle)'
    if l.startswith('saveundo'): return 'saveundo'
    if l.startswith('restoreundo'): return 'restoreundo'
    if l.startswith('prerestore') or l.startswith('slotreset'): return 'slot reset per extra'
    if l.startswith('carstep'): return 'carstep'
    if l.startswith('hud'): return 'hud glue (ticker state copies)'
    return 'other glue (scheduler, setlat, flip log, entry)'
tot = 0
for a, c in cyc.items():
    if 0xb8000 <= a < 0xba000: cat[category(a)] += c; tot += c
copies = max([cnt[a] for a in cnt if 0xb8300 <= a < 0xb8380 and 'move.b' in TXT.get(a, '') and '#$1' in TXT.get(a, '')] or [0])
print(f'{f}: set {v}: pre copies executed {copies}, extras-entry (ticks) {ticks}, groups (saveundo) {groups}, extra frames drawn {frames}')
for k, c in sorted(cat.items(), key=lambda kv: -kv[1]):
    if 'idle' in k: print(f'   {k:48s} {c:10d}'); continue
    if k.startswith('pre copy'): print(f'   {k:48s} {c:10d}   per copy {c/max(copies,1):8.0f}'); continue
    print(f'   {k:48s} {c:10d}   per group {c/max(groups,1):8.0f}   per extra frame {c/max(frames,1):8.0f}')
nonsleep = sum(c for k, c in cat.items() if 'idle' not in k and k != 'mt_clock' and not k.startswith('pre copy'))
print(f'   per group, excl. idle loops, clock and the pre copy: {nonsleep/max(groups,1):.0f} cycles ({nonsleep/max(groups,1)/160256:.3f} VBL); pre copy per tick that wants an extra: {cat["pre copy (mx_pre/mf_pre)"]/max(copies,1):.0f}')
