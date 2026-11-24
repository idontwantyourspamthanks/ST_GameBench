"""Palette-write trace: python3 rb_trace.py SNAP PATCHLIST|stock OUT.txt [VBLS]  (Hatari --trace video_color)"""
import sys, re, time, os
GAME = '/home/ryan/Code/AtariST/gamebench/games/in_progress/moonshine-racers'
sys.path.insert(0, GAME + '/tools')
os.environ.setdefault('MSRPATCH_TOOL', GAME + '/work/tightA/msrpatch_priv.py'); os.environ.setdefault('MSR_LIVETAG', '_tA')
import msrabtest as ab
from msr import Moonshine
snap, plist = sys.argv[1], sys.argv[2]; out = next(a for a in sys.argv[3:] if not a.startswith("poke="))
vbls = next((int(a) for a in sys.argv[3:] if a.isdigit()), 60)
names = None if plist == 'stock' else plist.split(',')
live = ab.live_build(names) if names else None
poke = next((a[5:] for a in sys.argv[3:] if a.startswith('poke=')), None)
if poke and live: live = ab.with_pokes(live, [poke], 'tA_rbneg')
h = Moonshine(snapshot=ab.snap_path(snap), extra=['--trace', 'video_color'])
try:
    time.sleep(1.5)
    if live: ab.apply_live(h, live, 0x7A88)
    time.sleep(0.4)
    n0 = len(h._logtext())
    v0 = h.vbl(); t0 = time.time()
    while h.vbl() < v0 + vbls and time.time() - t0 < 120: time.sleep(0.5)
    lg = h._logtext()[n0:]
    open(out, 'w').write(lg)
    print(plist[:50], 'log bytes', len(lg), 'color lines', lg.count('col'))
finally:
    h.close()
