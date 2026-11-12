#!/usr/bin/env python3
"""Flips per N VBL (default 3000 = 0.4 % resolution) for a snapshot, optionally live-patched.

    python3 work/cockpit/fps_long.py <snapshot.sav> <live prefix | -> [vbls]
abtest's 1000-VBL window has 1.2-1.6 % resolution and the unpatched/patched runs drift apart in game time,
so small gains need this longer window (run the base and the patched call side by side)."""
import json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'tools'))
from mw2harness import Hatari

snap, live = sys.argv[1], sys.argv[2] if sys.argv[2] != '-' else None
n = int(sys.argv[3]) if len(sys.argv) > 3 else 3000
h = Hatari(snapshot=snap)
try:
    if live:
        spec = json.loads(Path(live + '.json').read_text())
        h.debug(f"loadbin {Path(live + '.img').resolve()} ${spec['img_base']:x}", 1.5)
        for s in spec['sites']:
            h.debug(f"w ${s['addr']:x} " + ' '.join(f'${b:02x}' for b in bytes.fromhex(s['new'])), 0.4)
    print(Path(snap).stem, live or 'base', h.fps(n))
finally:
    h.close()
