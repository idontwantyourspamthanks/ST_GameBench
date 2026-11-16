#!/usr/bin/env python3
"""gate.py TAG SNAP MHZ TICKS [--type N] [--poke addr=hex ...] [--sets A P L N] : group-end state equality.
A = option A (tick_vbl tick_head tick_render: the unmodified tick at 5 Hz), P = shipped p3cp, L = scratch p3cp with the level rule, N = L with the pose restore broken (negative control).
Every run restores SNAP (2 MB STE), applies its live set and the pokes at the first flip after the SAME absolute VBL, then dumps the regions at every pc=$31586 (once per tick / group).
Prints for each non-A set: ticks compared, ticks with any difference, and the differing ranges."""
import sys, argparse, pickle, collections, concurrent.futures as cf
from cs import *
ap = argparse.ArgumentParser(); ap.add_argument('tag'); ap.add_argument('snap'); ap.add_argument('mhz', type=int); ap.add_argument('ticks', type=int)
ap.add_argument('--type', type=int, default=None); ap.add_argument('--poke', nargs='*', default=[]); ap.add_argument('--sets', nargs='*', default=['A', 'P', 'L']); ap.add_argument('--at', type=int, default=154400)
a = ap.parse_args()
REG = [(0x6600, 0x1200), (0x6220, 0x10), (0x1877c, 4), (0x5380, 0x80), (0x53d0, 0x20), (0xeb80, 0x20), (0xefa0, 0x40), (0xf960, 0x40), (0x34930, 0x10),
       (0x7580, 0x40), (0x18100, 0x80), (0x3530, 0x7d0), (0x3cec, 0x2e0), (0x40b0, 0x400), (0x6880, 0x40), (0x6900, 0x60), (0x1a700, 0x10), (0x1dfba, 4)]
IGN = '5380-53af 6776-6777 67a6-67ac 67c0-67ff 6808-6809 6900-695f 6a00-6eff 7020-7021 7706-7707 770c-7714 77c0-77d0 18124-18140 672e-6733 6840-6860 7710-7750 53c0-53ff 682a-686f 6f7a-6fcf 7682-7683 71c0-71c3'.split()
ign = [(0x3532 + n*0x42 + 0x36, 0x3532 + n*0x42 + 0x3b) for n in range(30)] + [tuple(int(x, 16) for x in s.split('-')) for s in IGN]
PN = ['tick_vbl', 'p3cp_head', 'p3c_sim', 'p3c_render']
def pk(e):
    ad, val = e.split('='); return f"w ${int(ad,16):x} " + ' '.join(f'${b:02x}' for b in bytes.fromhex(val))
def run(s):
    if s == 'A': live = build_live(['tick_vbl', 'tick_head', 'tick_render'], 'gA')
    elif s == 'P': live = build_scratch('gP', PN)          # CrawlerApply: P = the shipped-before build (git HEAD p3cp_head.s in the scratch patch dir)
    else: live = build_live(PN, 'gL')                       # L, N = the real patches/ tree (new p3cp_head.s)
    extra = []
    if s != 'A': extra.append('w $b42e4 $ff $d0')          # ACC = -48: the first PH 1 is due at clock 60, like A's first tick
    if s == 'N':                                           # negative control: cut the restore table before the $764c entry (predicted altitude and view words leak into the tick)
        img = Path(live + '.img').read_bytes(); i = img.find(bytes.fromhex('0001764a0001764c'))
        assert i > 0; extra.append(f'w ${0xb3000 + i + 4:x} $00 $00')
    h = Hatari(snapshot=str(SNAP / a.snap), memsize_kb=2048)
    try:
        if a.mhz != 8: h.set_cpuclock(a.mhz)
        assert h.vbl() < a.at - 20, 'at_vbl already passed'
        hit = h.R / 'hit.txt'; hit.write_text('e VBL\n' + '\n'.join(f'm ${ad:x} {n}' for ad, n in REG) + '\n')
        cmds = apply_cmds(live) + extra + [pk(e) for e in a.poke] + ([pokew(0x6220, a.type)] if a.type is not None else []) + [f'b pc = $31586 :trace :file {hit}']
        start = len(h._logtext())
        at_flip(h, cmds, a.at)
        t = time.time()
        while len(re.findall(r'^00006600:', h._logtext()[start:], re.M | re.I)) < a.ticks + 1:
            if time.time() - t > 900: raise TimeoutError
            time.sleep(0.5)
        h.debug('b all', 0.5)
        rows = [r for r in parse_hits(h._logtext()[start:], 0x6600)][:a.ticks]
        ex = 'n/a'
        return s, rows, ex
    finally:
        h.close()
with cf.ThreadPoolExecutor(1) as ex:
    res = {s: (rows, n) for s, rows, n in ex.map(run, a.sets)}
A = res['A'][0]
def pose(r): return f"X {rd(r,0x66e6,4)} Y {rd(r,0x66ea,4)} H {rd(r,0x6742)} alt {rd(r,0x764c,2,True)} type {rd(r,0x6220)} spd {rd(r,0x6772,2,True)}"
print(f'## {a.tag}: {a.snap} {a.mhz} MHz type {a.type} pokes {a.poke}; A tick 1: {pose(A[0])}; tick {len(A)}: {pose(A[-1])}')
pairs = [(s, 'A', s) for s in a.sets if s != 'A'] + ([('PL', 'P', 'L')] if 'P' in a.sets and 'L' in a.sets else [])   # PL: shipped-before vs new, directly
for lab, sa, s in pairs:
    A = res[sa][0]
    B = res[s][0]; n = min(len(A), len(B)); bad = 0; tot = collections.Counter(); first = {}
    for k in range(n):
        d = sorted(x for x in A[k] if x != 'vbl' and x in B[k] and A[k][x] != B[k][x] and not any(lo <= x <= hi for lo, hi in ign))
        bad += bool(d)
        rng = []
        for x in d:
            if rng and x <= rng[-1][1] + 2: rng[-1][1] = x
            else: rng.append([x, x])
        for lo, hi in rng: tot[(lo, hi)] += 1; first.setdefault((lo, hi), k + 1)
    print(f'GATE {a.tag} {sa} vs {s}: ticks compared {n}, ticks with any difference {bad}' + (' IDENTICAL' if not bad else '') + f' (level-rule calls in the run: {res[s][1]})')
    for (lo, hi), c in sorted(tot.items())[:12]: print(f'    {lo:x}-{hi:x}: {c} ticks, first at tick {first[(lo, hi)]}')
