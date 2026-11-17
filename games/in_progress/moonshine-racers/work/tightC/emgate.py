"""Emulator gate: stock vs stock+LIVE, full 1 MB RAM + screens compared after every pass.
python3 emgate.py DUMP NPASS LIVEPREFIX|none [sched] [--neg]   (DUMP in work/extrap/h_*_7a88.bin)"""
import sys, json, time, os
sys.path.insert(0, '/home/ryan/Code/AtariST/gamebench/games/in_progress/moonshine-racers/work/extrap')
import numpy as np
from emu import Emu
from proto import flip

def apply_live(e, prefix):
    spec = json.load(open(prefix + '.json')); img = open(prefix + '.img', 'rb').read()
    e.write(spec['img_base'], img)
    for s in spec['sites']: e.write(s['addr'], bytes.fromhex(s['new']))
    return spec

def schedule(p, kind):
    if kind == 'up': return 0x01
    if kind == 'upleft': return 0x05 if (p // 20) % 2 == 0 else 0x01
    if kind == 'zig': return [0x01, 0x05, 0x01, 0x09][(p // 15) % 4]
    if kind == 'brake': return 0x01 if (p // 40) % 2 == 0 else 0x02
    return None

MASK = [(0xb2700, 0xe8400),        # payload + runtime tables of the patches
        (0x77d00, 0x78000),        # stack
        (0x611a, 0x611c),          # VBL counters
        (0xff8000, 0x100000),
        (0x4724, 0x4f78)]          # road geometry output (rewritten before use; the HUD gate masks the same range)

def main():
    dump, npass, live = sys.argv[1], int(sys.argv[2]), sys.argv[3]
    kind = sys.argv[4] if len(sys.argv) > 4 else None
    a = Emu(dump); b = Emu(dump)
    import os
    if os.environ.get('REF'): apply_live(a, os.environ['REF'])
    spec = apply_live(b, live) if live != 'none' else {'sites': []}
    import os
    for pk in os.environ.get('POKE','').split(','):
        if pk:
            ad, val = pk.split('='); 
            for e in (a, b): e.write(int(ad,16), bytes.fromhex(val))
    mask = np.ones(0x100000, bool)
    for lo, hi in MASK:
        if os.environ.get('UNMASK_GEOM') and (lo, hi) == (0x4724, 0x4f78): continue
        mask[lo:min(hi, 0x100000)] = False
    specs = list(spec['sites']) + (json.load(open(os.environ['REF'] + '.json'))['sites'] if os.environ.get('REF') else [])
    for s in specs:
        mask[s['addr']:s['addr'] + len(bytes.fromhex(s['new']))] = False
    if os.environ.get('REGION'):
        lo, hi = [int(x, 16) for x in os.environ['REGION'].split('-')]
        keep = np.zeros(0x100000, bool); keep[lo:hi] = True; mask &= keep
    nbad = 0; t0 = time.time(); badaddrs = {}
    for p in range(npass):
        v = schedule(p, kind)
        for e in (a, b):
            if v is not None: e.setb(0x6105, v)
            e.run(0x7a88, 0x7b74); flip(e)
        x = np.frombuffer(a.read(0, 0x100000), np.uint8); y = np.frombuffer(b.read(0, 0x100000), np.uint8)
        d = np.nonzero((x != y) & mask)[0]
        if len(d):
            nbad += 1
            if os.environ.get('VERBOSE'): print('pass', p, 'ndiff', len(d), 'range', hex(int(d.min())), hex(int(d.max())))
            for q in d: badaddrs.setdefault(int(q), p)
        for e in (a, b): e.run(0x7b7a, 0x7a88)
    print(f'{dump.split("/")[-1]} {live.split("/")[-1]} sched={kind} passes={npass} passes_with_diff={nbad} differing_addrs={len(badaddrs)} time={time.time()-t0:.0f}s')
    runs = []
    for q in sorted(badaddrs):
        if runs and q - runs[-1][1] <= 1: runs[-1][1] = q
        else: runs.append([q, q])
    print('  first diffs:', [f'{s:x}-{t:x}@{badaddrs[s]}' for s, t in runs[:16]])
if __name__ == "__main__": main()
