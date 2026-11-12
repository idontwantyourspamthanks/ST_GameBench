import sys, re, time
sys.path.insert(0, '/home/ryan/Code/AtariST/gamebench/games/in_progress/midwinter2/work/vehicles_p3b')
from vt import *
import vgate
snap, sset, mhz = sys.argv[1], sys.argv[2], int(sys.argv[3])
names = cand_names() if sset == 'cand' else vgate.SETS[sset]
live = build_live(names, 'gaps_' + sset)
h = Hatari(snapshot=str(SNAP / snap), memsize_kb=2048)
try:
    if mhz != 8: h.set_cpuclock(mhz)
    v = h.vbl(); f = h.R / 'g.txt'; f.write_text('e VBL\n')
    import os
    slk = os.environ.get('FPS_SLK'); pk = (['w $b8fb2 ' + ' '.join('$%02x' % b for b in (int(slk) & 0xffff).to_bytes(2, 'big'))] if slk is not None else []) + (['w $b42e4 $ff $d0'] if sset in ('cand', 'P') else [])
    st = len(h._logtext()); at_flip(h, apply_cmds(live) + pk + [f'b pc = $31586 :trace :file {f}'], v + 100)
    time.sleep(19)
    h.debug('b all', 0.5)
    vb = [int(x) for x in re.findall(r'#(\d+) \(dec\)', h._logtext()[st:])]
    iv = [b - a for a, b in zip(vb, vb[1:])]
    dev = [x - vb[0] - 10 * i for i, x in enumerate(vb)]
    print(sset, mhz, 'slk', slk, snap, 'ticks', len(vb), 'lateness VBL vs 10-VBL grid from tick 0: max', max(dev), 'min', min(dev), 'late >1:', sum(1 for d in dev if d > 1), 'late >0:', sum(1 for d in dev if d > 0), '/', len(dev), '| old:', len(vb), 'span', vb[-1] - vb[0], 'max interval', max(iv))
finally:
    h.close()
