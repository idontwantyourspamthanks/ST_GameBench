"""Real IKBD joystick input (host arrow keys via --joy1 keys): python3 joy_test.py stock|PATCHLIST  -> $6105 samples and world advance while keys are held"""
import sys, re, time, os
GAME = '/home/ryan/Code/AtariST/gamebench/games/in_progress/moonshine-racers'
sys.path.insert(0, GAME + '/tools')
os.environ.setdefault('MSRPATCH_TOOL', GAME + '/work/tightA/msrpatch_priv.py'); os.environ.setdefault('MSR_LIVETAG', '_tA')
import msrabtest as ab
from msr import Moonshine
plist = sys.argv[1]
names = None if plist == 'stock' else plist.split(',')
live = ab.live_build(names) if names else None
h = Moonshine(snapshot=ab.snap_path('race_start'), extra=['--joy1', 'keys'])
def rd(a, n=2):
    o = h.debug(f"m ${a:x} {n}", 0.6)
    m = re.findall(rf"{a:08x}:\s+((?:[0-9a-f]{{2}} ?)+)", o, re.I)
    return bytes.fromhex(m[-1].replace(' ', ''))[:n].hex() if m else None
try:
    time.sleep(1.5)
    if live: ab.apply_live(h, live, 0x7A88)
    time.sleep(0.5)
    h.debug("w $6105 $00")
    out = []
    def sample(tag): out.append((tag, rd(0x6105, 1), rd(0x5ff8, 2), rd(0x130c, 2), rd(0x1318, 2)))
    time.sleep(1); sample('idle')
    h._xdo("keydown", "--window", h.win, "Up"); time.sleep(4); sample('Up held 4s'); time.sleep(3); sample('Up held 7s')
    h._xdo("keydown", "--window", h.win, "Left"); time.sleep(2); sample('Up+Left'); 
    h._xdo("keyup", "--window", h.win, "Left"); h._xdo("keydown", "--window", h.win, "Right"); time.sleep(2); sample('Up+Right')
    h._xdo("keyup", "--window", h.win, "Right"); h._xdo("keyup", "--window", h.win, "Up"); time.sleep(2); sample('released')
    for o in out: print(plist[:30], o)
finally:
    h.close()
