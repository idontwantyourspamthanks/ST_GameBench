#!/usr/bin/env python3
"""Per-tick exactness gate: option A (5 Hz) vs a p3c / p3b set, group end vs tick.
  vgate.py run  SNAP NAME SET [--ticks 41] [--poke 6fba=01900000 ...] [--mhz 8]   -> /tmp/vg/NAME.pkl
  vgate.py cmp  NAMEA NAMEB
SET: 'A' (tick_vbl tick_head tick_render) | 'P' (tick_vbl p3cp_head p3c_sim p3c_render) | 'C' (p3c_head alternative) | 'S:p1,p2,..' explicit
Sample point pc=$31586 (jsr $32ee0, once per world tick in A and at PH5 in p3c; not reached by sub-passes)."""
import sys, pickle, re, time, argparse
sys.path.insert(0, '/home/ryan/Code/AtariST/gamebench/games/midwinter2/work/vehicles_p3b')
from vt import *
from pathlib import Path
OUT = Path('/tmp/vg'); OUT.mkdir(exist_ok=True)
SETS = {'P': ['tick_vbl', 'p3cp_head', 'p3c_sim', 'p3c_render'], 'A': ['tick_vbl', 'tick_head', 'tick_render'],
        'C': ['tick_vbl', 'p3c_head', 'p3c_sim', 'p3c_render'], 'A2': ['tick_vbl', 'tick_head', 'tick_render'], 'P2': ['tick_vbl', 'p3cp_head', 'p3c_sim', 'p3c_render']}   # A2 = A again (reproducibility of the harness)
# regions dumped at every sample: (addr, bytes)
REG = [(0x6600, 0x1200), (0x6220, 0x10), (0x1877c, 4), (0x5380, 0x80), (0x53d0, 0x20), (0xeb80, 0x20), (0xefa0, 0x40), (0xf960, 0x40), (0x34930, 0x10),
       (0x7580, 0x40), (0x18100, 0x80), (0x3530, 0x7d0), (0x3cec, 0x2e0), (0x40b0, 0x400), (0x6880, 0x40), (0x6900, 0x60), (0x1a700, 0x10), (0x1dfba, 4)]

def parse(txt):
    rows = []; cur = {}; first = REG[0][0]
    for m in re.finditer(r'^([0-9A-F]{8}):((?: [0-9a-f]{2})+)', txt, re.M | re.I):
        a = int(m.group(1), 16)
        if a == first and cur.get('open'):
            rows.append(cur); cur = {}
        if a == first:
            cur['open'] = True
        for i, b in enumerate(bytes.fromhex(m.group(2).replace(' ', ''))):
            cur[a + i] = b
    if cur: rows.append(cur)
    return rows

def run(snap, name, sset, ticks, pokes, mhz=8, mem=2048, flips_after=100, extra_cmds=(), late=(), sync=None):
    if sset.startswith('S:'):
        only = sset[2:].split(',')
    else:
        only = SETS[sset]
    live = build_live(only, 'g_' + sset.replace(':', '_').replace(',', '_')[:40])
    h = Hatari(snapshot=str(SNAP / snap) if '/' not in snap else snap, memsize_kb=mem)
    try:
        if mhz != 8: h.set_cpuclock(mhz)
        v = h.vbl()
        if sync:
            # A and P must apply their patch set at the SAME flip: the VBL read over the fifo depends on wall-clock start-up time, so one flip earlier or later
            # starts the two runs one logic step apart.  The A run publishes its reading, the other runs use it (emulation is deterministic in VBL numbers).
            sp = Path(sync)
            if sset == 'A':
                sp.write_text(str(v))
            else:
                t0 = time.time()
                while not sp.exists() or not sp.read_text().strip():
                    if time.time() - t0 > 120: raise TimeoutError('sync file')
                    time.sleep(0.05)
                v = int(sp.read_text())
        hit = h.R / 'hit.txt'
        hit.write_text('e VBL\n' + '\n'.join(f'm ${a:x} {n}' for a, n in REG) + '\n')
        # live patch at a flip: the clock starts at 0 now. A's first tick is due at CLOCK 60; P's first PH 1 at ACC >= 12 -> ACC = -48 makes it 60 too (same tick phase as A)
        align = ['w $b42e4 $ff $d0'] if ('p3cp_head' in only or 'p3c_head' in only) else []
        # late pokes (dv VBL after v + flips_after) are armed INSIDE the apply file: registered over the fifo afterwards they fire at a wall-clock dependent VBL
        latecmds = []
        for i, (dv, lc) in enumerate(late):
            lf = h.R / f'late{i}.txt'; lf.write_text(lc + '\n')
            latecmds.append(f"b VBL > {v + flips_after + dv} :trace :once :file {lf}")
        cmds = apply_cmds(live) + align + list(pokes) + list(extra_cmds) + latecmds + [f'b pc = $31586 :trace :file {hit}']
        start = len(h._logtext())
        at_flip(h, cmds, v + flips_after)
        t = time.time()
        while True:
            txt = h._logtext()[start:]
            n = len(re.findall(r'^00006600:', txt, re.M | re.I))
            if n >= ticks: break
            if time.time() - t > 1500: raise TimeoutError(txt[-800:])
            time.sleep(0.5)
        h.debug('b all', 0.5)
        txt = h._logtext()[start:]
        (OUT / (name + '.log')).write_text(txt)
        rows = parse(txt)
        pickle.dump(rows, open(OUT / (name + '.pkl'), 'wb'))
        return rows
    finally:
        h.close()

def pk(s):
    a, v = s.split('=')
    a = int(a, 16); b = bytes.fromhex(v)
    return f"w ${a:x} " + ' '.join(f'${x:02x}' for x in b)

if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest='cmd')
    r = sub.add_parser('run'); r.add_argument('snap'); r.add_argument('name'); r.add_argument('set')
    r.add_argument('--ticks', type=int, default=41); r.add_argument('--poke', nargs='*', default=[]); r.add_argument('--mhz', type=int, default=8); r.add_argument('--late', nargs='*', default=[]); r.add_argument('--sync', default=None)
    c = sub.add_parser('cmp'); c.add_argument('a'); c.add_argument('b'); c.add_argument('--off', type=int, default=0)
    a = ap.parse_args()
    if a.cmd == 'run':
        rows = run(a.snap, a.name, a.set, a.ticks, [pk(p) for p in a.poke], a.mhz, late=[(int(x.split(':',1)[0]), pk(x.split(':',1)[1])) for x in a.late], sync=a.sync)
        print(a.name, 'samples', len(rows))
