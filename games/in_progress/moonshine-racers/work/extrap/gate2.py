"""Emulator gate of the real blob: stock vs mx (X_TEST=n) state equality at $7b7a, per pass.
python3 gate2.py DUMP NPASS NTEST [key=hex ...]"""
import sys, json
from proto import *
LIVE = '/home/ryan/Code/AtariST/gamebench/games/in_progress/moonshine-racers/work/extrap/live/mx'

def apply_live(e, prefix=LIVE):
    spec = json.load(open(prefix + '.json')); img = open(prefix + '.img', 'rb').read()
    e.write(spec['img_base'], img)
    for s in spec['sites']: e.write(s['addr'], bytes.fromhex(s['new']))

MASK = [(0x1004, 0x100c), (0x100c, 0x100e), (0x12f0, 0x1308), (0x12fe, 0x1302), (0x1302, 0x1308), (0x1300, 0x1302),
        (0x29c8, 0x2c68),                # clouds: x,y restored; $28/$2a are display history
        (0x36e8, 0x3750), (0x37c0, 0x37cc),   # object order list + scratch
        (0x4500, 0x5000),                # road geometry / span tables (output of 100b4)
        (0x3cb0, 0x3d40),                # raster table (VBL ISR)
        (0x611a, 0x611c), (0x9300, 0x9500), (0x77000, 0x80000),
        ]
def masked(a): return any(lo <= a < hi for lo, hi in MASK)

def run(dump, npass, ntest, patched, pokes=()):
    e = Emu(dump)
    if patched:
        apply_live(e)
        e.setb(0xB8F21, ntest)
        for a, v in pokes: e.setb(a, v)
    states = []
    for p in range(npass):
        if patched:
            e.setb(0xB8F08, 0); e.setl(0xB8F00, 36 * (p + 1))
            e.run(0x7a88, 0x7b7a)
        else:
            e.run(0x7a88, 0x7b74); flip(e)
        states.append(snap_ram(e))
        e.run(0x7b7a, 0x7a88)
    return e, states

if __name__ == "__main__":
    dump = sys.argv[1]; npass = int(sys.argv[2]); ntest = int(sys.argv[3])
    es, S = run(dump, npass, 0, False)
    ep, P = run(dump, npass, ntest, True)
    print("extra frames", ep.l(0xB8F38), "groups", ep.l(0xB8F3C), "ticks", ep.l(0xB8F40))
    bad = {}
    for p in range(npass):
        for a in range(0x1000, 0x7000):
            if S[p][a] != P[p][a] and not masked(a):
                bad.setdefault(a, []).append(p)
    print("differing logic bytes:", len(bad))
    for s, t in region_runs(sorted(bad)):
        print(f"  {s:05x}-{t:05x} ({t-s+1}) first pass {min(bad[s])}")
