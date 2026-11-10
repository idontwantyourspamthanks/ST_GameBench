#!/usr/bin/env python3
"""fpsrun.py CONFIG SNAP MHZ [SCEN]: fps over 1000 VBL after applying the patch set at a flip. CONFIG: orig | cand (defaults + p3cp_head + p3c_sim + p7_skip_render) | cand_nsk (cand without p7_skip_*)
SCEN: stand (default) | move (forward + turn pokes as runtype)."""
import sys, subprocess
sys.path.insert(0, '/home/ryan/Code/AtariST/gamebench/games/midwinter2/work/vehicles_p3b')
from vt import *
import runtype
cfg, snap, mhz = sys.argv[1], sys.argv[2], int(sys.argv[3]); scen = sys.argv[4] if len(sys.argv) > 4 else 'stand'
if cfg == 'orig': names = None
elif cfg == 'cand': names = cand_names()
elif cfg == 'cand_nsk': names = [n for n in cand_names() if not n.startswith('p7_skip')]
live = build_live(names, 'fps_' + cfg) if names else None
h = Hatari(snapshot=str(SNAP/snap), memsize_kb=2048)
try:
    if mhz != 8: h.set_cpuclock(mhz)
    v = h.vbl()
    st = {k: v for k, v in runtype.SNAPS.items()}
    ty = h.peekw(0x6220)
    pk = []
    if scen == 'move':
        pk = ['w $%x ' % int(p.split('=')[0], 16) + ' '.join('$%02x' % b for b in bytes.fromhex(p.split('=')[1])) for p in runtype.pokes(ty, 'movturn')]
    cmds = (apply_cmds(live) if live else []) + pk
    if cmds: at_flip(h, cmds, v + 100)
    else: time.sleep(1)
    time.sleep(3)
    d0 = memb(h, 0xb6000, 64) if live else b''
    f = h.fps(1000)
    d1 = memb(h, 0xb6000, 64) if live else b''
    sk = (uw(d1[0x14:0x18]) - uw(d0[0x14:0x18])) if live and len(d1) >= 0x18 else None
    print(f"FPS {cfg} {snap} type {ty} {mhz}MHz {scen}: {f['fps']:.2f} fps ({f['flips']} flips/1000 VBL, {f['vbls_per_frame']:.1f} VBL/frame) skip-count {sk}")
finally:
    h.close()
