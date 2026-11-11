#!/usr/bin/env python3
"""ab2.py SNAP FLIPS SETA SETB : pixel gate between two live patch sets (visible 32000 B of both buffers), applied at the same flip.
SET = comma list of patch names, or 'none'. Also runs fps over 1000 VBL for each (--fps)."""
import sys, hashlib, argparse
sys.path.insert(0, '/home/ryan/Code/AtariST/gamebench/games/in_progress/midwinter2/work/vehicles_p3b')
from vt import *
from concurrent.futures import ThreadPoolExecutor
VIS = 32000
MHZ = 8
def one(snap, at, names, tag, flips, fps):
    live = None if names == 'none' else build_live(names.split(','), 'ab2_' + hashlib.md5(names.encode()).hexdigest()[:8])
    out = Path('/tmp/ab2') / f'{hashlib.md5((snap+names).encode()).hexdigest()[:8]}_{at}_{flips}'
    h = Hatari(snapshot=str(SNAP / snap), memsize_kb=2048)
    try:
        if MHZ != 8: h.set_cpuclock(MHZ)
        h.capture_frames(str(out), live=live, at_vbl=at, nth_flip=flips)
        f = h.fps(1000) if fps else None
    finally:
        h.close()
    md = {n: hashlib.md5((out / n).read_bytes()[:VIS]).hexdigest() for n in ('buf60000.bin', 'buf70000.bin')}
    return md, f, out
if __name__ == '__main__':
    ap = argparse.ArgumentParser(); ap.add_argument('snap'); ap.add_argument('flips', type=int); ap.add_argument('a'); ap.add_argument('b'); ap.add_argument('--fps', action='store_true'); ap.add_argument('--mhz', type=int, default=8)
    a = ap.parse_args(); MHZ = a.mhz
    h = Hatari(snapshot=str(SNAP / a.snap), memsize_kb=2048)
    try: v = h.vbl()
    finally: h.close()
    at = (v // 100 + 4) * 100
    with ThreadPoolExecutor(2) as ex:
        fa = ex.submit(one, a.snap, at, a.a, 'A', a.flips, a.fps); fb = ex.submit(one, a.snap, at, a.b, 'B', a.flips, a.fps)
        ra, rb = fa.result(), fb.result()
    same = ra[0] == rb[0]
    nd = 0
    if not same:
        for f in ('buf60000.bin', 'buf70000.bin'):
            x, y = (ra[2] / f).read_bytes()[:VIS], (rb[2] / f).read_bytes()[:VIS]
            nd += sum(1 for i in range(VIS) if x[i] != y[i])
    rr=''
    if not same:
        rows=set()
        for f in ('buf60000.bin','buf70000.bin'):
            x, y = (ra[2] / f).read_bytes()[:VIS], (rb[2] / f).read_bytes()[:VIS]
            rows |= {i // 160 for i in range(VIS) if x[i] != y[i]}
        rr=f' rows {min(rows)}-{max(rows)}'
    print(f"RESULT {a.snap} flips {a.flips}: {'IDENTICAL' if same else 'DIFFER (%d bytes%s)' % (nd, rr)}" + (f"  fps A {ra[1]['fps']:.2f} B {rb[1]['fps']:.2f}" if a.fps else ''))
