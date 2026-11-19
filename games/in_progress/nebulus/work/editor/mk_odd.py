#!/usr/bin/env python3
"""Odd-aligned level records (NebOddFix): fixtures for e180.py -> /tmp/ne/odd/ (and work/editor/fixtures/odd2.ovl, the regression fixture).
A level record is 20 + len bytes, len = 2*rows + number of non-zero cells, and records are packed back to back, so every level with an odd number of
non-zero cells makes the NEXT record start at an odd address in RAM ($BC000 + 272 + ...).  The fixture set: odd2 (two odd levels + a campaign that mixes
custom and original entries), looks (the NebLooks file: ten 159 B levels), stress01..stress12 (seeded: 1..6 levels, random odd/even sizes, 1..3 campaigns)."""
import random, sys, shutil
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import ovl
OUT = Path("/tmp/ne/odd"); FIX = Path(__file__).resolve().parent / "fixtures"

def mk_level(rng, parity, name=None, mission=None, tower=None):
    """random level whose record size parity is `parity` (0 even, 1 odd): parity of record = parity of the number of non-zero cells"""
    rows = rng.randrange(16, 41)
    grid = [[0] * rows for _ in range(16)]
    for a in range(16): grid[a][1] = 0x81            # ledge ring on row 1 = safe frog start (as the editor's new level)
    n = rng.randrange(6, 80)
    if (16 + n) % 2 != parity: n += 1
    cells = [(a, r) for a in range(16) for r in range(3, rows - 1)]
    for a, r in rng.sample(cells, n): grid[a][r] = rng.choice((0x80, 0x81, 0x81, 0x82))
    nm = name or "".join(rng.choice("ABCDEFGHJKLMNPRSTUVWXYZ0123456789") for _ in range(rng.randrange(1, 12)))
    tm = rng.choice((0, 0, 0x0200, 0x0350, 0x0480, 0x0600))
    return ovl.level(mission or rng.choice((1, 2)), tower if tower is not None else rng.randrange(8), rows, grid, tm, nm)

def mk_file(seed):
    rng = random.Random(seed)
    nl = rng.randrange(1, 7)
    mode = seed % 3                                   # 0 all odd, 1 random, 2 alternating even/odd starting odd
    lv = [mk_level(rng, 1 if mode == 0 else rng.randrange(2) if mode == 1 else (1 + i) % 2) for i in range(nl)]
    camps = []
    for c in range(rng.randrange(1, 4)):
        ent = [rng.choice([rng.randrange(nl)] * 2 + [ovl.orig(rng.choice((1, 2)), rng.randrange(8))]) for _ in range(rng.randrange(2, 6))]
        camps.append(ovl.camp(f"CAMP{c+1}", ent))
    return ovl.build(lv, camps)

def main():
    OUT.mkdir(parents=True, exist_ok=True); FIX.mkdir(exist_ok=True)
    rng = random.Random(1801)
    a = mk_level(rng, 1, "ODD ONE", 1, 3); b = mk_level(rng, 1, "ODD TWO", 2, 5)
    odd2 = ovl.build([a, b], [ovl.camp("ODD2", [0x80 | 0, 0, ovl.orig(1, 2), 1]), ovl.camp("ODD2 REV", [1, 0])])
    assert not ovl.validate(odd2) and len(a) % 2 == 1 and len(b) % 2 == 1, (len(a), len(b))
    (FIX / "odd2.ovl").write_bytes(odd2); (OUT / "odd2.ovl").write_bytes(odd2)
    # flags.b gate fixture: three odd records with flags $ca / $35 / $ff (reserved field: readers ignore it, the editor must preserve all 8 bits)
    fl = []
    for i, f in enumerate((0xca, 0x35, 0xff)):
        r = bytearray(mk_level(rng, 1, f"FLAGS {i}", 1 + i % 2, i)); r[3] = f; fl.append(bytes(r))
    flags = ovl.build(fl, [ovl.camp("FLAGS", [0, 1, 2])]); assert not ovl.validate(flags)
    (FIX / "flags35.ovl").write_bytes(flags); (OUT / "flags35.ovl").write_bytes(flags)
    shutil.copy("/tmp/looks/looks.ovl", OUT / "looks.ovl") if Path("/tmp/looks/looks.ovl").exists() else None
    for i in range(1, 13):
        d = mk_file(7000 + i); assert not ovl.validate(d), ovl.validate(d)
        (OUT / f"stress{i:02d}.ovl").write_bytes(d)
    for f in sorted(OUT.glob("*.ovl")):
        if f.name.startswith('flags'): continue
        lv, cs = ovl.parse(f.read_bytes())
        print(f.name, "levels", [(l["size"], l["name"]) for l in lv], "odd-size records:", sum(l["size"] % 2 for l in lv), "campaigns", [(n, e) for n, e in cs])

if __name__ == "__main__": main()
