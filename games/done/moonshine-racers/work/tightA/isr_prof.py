"""Interrupt costs per VBL in Hatari: python3 isr_prof.py SNAP 'patchlist|stock' VBLS OUT   (Hatari profile: exact cycles per address)"""
import sys, re, time, os
GAME = '/home/ryan/Code/AtariST/gamebench/games/in_progress/moonshine-racers'
sys.path.insert(0, GAME + '/tools')
os.environ.setdefault('MSRPATCH_TOOL', GAME + '/work/tightA/msrpatch_priv.py'); os.environ.setdefault('MSR_LIVETAG', '_tA')
import msrabtest as ab
from msr import Moonshine, prof
snap, plist, vbls, out = sys.argv[1], sys.argv[2], int(sys.argv[3]), sys.argv[4]
names = None if plist == 'stock' else plist.split(',')
live = ab.live_build(names) if names else None
h = Moonshine(snapshot=ab.snap_path(snap))
try:
    time.sleep(1.5)
    if live: ab.apply_live(h, live, 0x7A88)
    time.sleep(0.4)
    prof(h, vbls, out)
finally:
    h.close()
