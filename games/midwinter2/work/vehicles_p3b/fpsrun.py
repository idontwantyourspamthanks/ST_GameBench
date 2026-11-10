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
    import os, re as _re
    slk = os.environ.get('FPS_SLK')       # tuning word of p3cp_head ($b8fb2): -6 strict rule, 0 middle ground (default), 1000 no rule
    if slk is not None: pk.append('w $b8fb2 ' + ' '.join('$%02x' % b for b in (int(slk) & 0xffff).to_bytes(2, 'big')))
    cmds = (apply_cmds(live) if live else []) + pk
    if cmds: at_flip(h, cmds, v + 100)
    else: time.sleep(1)
    time.sleep(3)
    d0 = memb(h, 0xb6000, 64) if live else b''
    f = h.fps(1000)
    d1 = memb(h, 0xb6000, 64) if live else b''
    sk = (uw(d1[0x14:0x18]) - uw(d0[0x14:0x18])) if live and len(d1) >= 0x18 else None
    # side measurement: ticks per second (hits of $31586, once per 5 Hz tick) over 500 VBL
    lf = h.R / 'tk.txt'; lf.write_text('e VBL\n'); h.debug('b all', 0.3); st = len(h._logtext()); v0 = h.vbl()
    h.cmd(f'hatari-debug b pc = $31586 :trace :file {lf}'); time.sleep(0.2)
    h.cmd(f'hatari-debug b VBL > {v0 + 500} :trace :once'); time.sleep(0.2)
    t0 = time.time()
    while 'Removed CPU breakpoint' not in h._logtext()[st:] and time.time() - t0 < 120: time.sleep(0.5)
    vb = [int(x) for x in _re.findall(r'#(\d+) \(dec\)', h._logtext()[st:])]; h.debug('b all', 0.3)
    tps = round((len(vb) - 1) * 50.0 / max(1, vb[-1] - vb[0]), 2) if len(vb) > 2 else None
    print(f"FPS {cfg} {snap} type {ty} {mhz}MHz {scen}: {f['fps']:.2f} fps ({f['flips']} flips/1000 VBL, {f['vbls_per_frame']:.1f} VBL/frame) skip-count {sk} ticks/s {tps} slk {slk}")
finally:
    h.close()
