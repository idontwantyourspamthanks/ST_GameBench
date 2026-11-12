#!/usr/bin/env python3
"""shots.py SNAP OUT [N]: restore a snapshot, wait, screenshot N times (3 s apart) into work/shots/."""
import sys, time
from pathlib import Path
GAME = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(GAME / "tools"))
from mw2harness import Hatari
snap, out = sys.argv[1], sys.argv[2]
mem = int(sys.argv[3]) if len(sys.argv) > 3 else 1024
h = Hatari(snapshot=str(GAME / "work/snapshots" / snap), memsize_kb=mem)
try:
    time.sleep(3)
    p = h.shot(str(GAME / "work/shots" / out))
    print(p)
finally:
    h.close()
