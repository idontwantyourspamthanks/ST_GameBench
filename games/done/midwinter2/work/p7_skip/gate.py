#!/usr/bin/env python3
"""Gate runner for p7_skip.  Two Hatari instances (A and B) restore the same snapshot, apply live patch sets A and B
at the same flip, optionally poke RAM at given flips (same flip index in both runs), and save both screen buffers
(+ palette + the skip counters) after the requested flip counts.

  gate.py ident SNAP A|- B FLIPS [--mem 1024] [--poke 'K:cmd;cmd' ...] [--tag T] [--png]

A/B are `mw2patch.py live` prefixes ('-' = nothing).  Per flip K: visible-area (32000 B/buffer) differences
between A and B and B's counters.  Pokes are debugger commands run at the K-th flip after the apply flip."""
import sys, json, time, argparse, shutil
from pathlib import Path
sys.path.insert(0, '/home/ryan/Code/AtariST/midwinter2/tools')
from mw2harness import Hatari
from concurrent.futures import ThreadPoolExecutor
FLIP = 0x26E98
CNT = ['VAL0', 'VAL1', 'WV0', 'WV1', 'WP0', 'WP1', 'WAVE', 'NSKIP', 'NREND', 'NINV', 'WPTMP', 'NUNS', 'NSC', 'NOBJ', 'NWAV']

def live_cmds(prefix):
    if not prefix or prefix == '-':
        return []
    spec = json.loads(Path(prefix + '.json').read_text())
    c = [f"loadbin {Path(prefix + '.img').resolve()} ${spec['img_base']:x}"]
    for s in spec['sites']:
        c.append(f"w ${s['addr']:x} " + " ".join(f"${b:02x}" for b in bytes.fromhex(s['new'])))
    return c

def counters(raw):
    import struct
    d = struct.unpack('>HHHHLLHxxLLLLLLLL', raw[:0x34]) if False else None
    w = lambda o: int.from_bytes(raw[o:o+2], 'big')
    l = lambda o: int.from_bytes(raw[o:o+4], 'big')
    return dict(VAL=(w(0), w(2)), WV=(w(4), w(6)), WAVE=w(0x10), NSKIP=l(0x14), NREND=l(0x18), NINV=l(0x1c),
                NUNS=l(0x24), NSC=l(0x28), NOBJ=l(0x2c), NWAV=l(0x30))

def run(snap, prefix, flips, out, mem, pokes, at, final_extra=()):
    h = Hatari(snapshot=snap, memsize_kb=mem)
    try:
        od = Path(out); od.mkdir(parents=True, exist_ok=True)
        cmds = live_cmds(prefix)
        for k in flips:
            cf = h.R / f"cap{k}.txt"
            lines = [f"savebin {od}/b60_{k}.bin $60000 $8000", f"savebin {od}/b70_{k}.bin $70000 $8000",
                     f"savebin {od}/ptr_{k}.bin $67a6 8", f"savebin {od}/cnt_{k}.bin $b6000 $40",
                     f"savebin {od}/pal_{k}.bin $ff8240 32", f"savebin {od}/pos_{k}.bin $66e6 8", f"savebin {od}/npc_{k}.bin $3538 16"]
            lines += [f"savebin {od}/{n}_{k}.bin {a} {l}" for n, a, l in final_extra]
            cf.write_text("\n".join(lines) + "\n")
            cnt = f" :{k}" if k > 1 else ""
            cmds.append(f"b pc = ${FLIP:x}{cnt} :trace :once :file {cf}")
        for k, cs in pokes:
            pf = h.R / f"poke{k}.txt"
            pf.write_text("\n".join(cs) + "\n")
            cnt = f" :{k}" if k > 1 else ""
            cmds.append(f"b pc = ${FLIP:x}{cnt} :trace :once :file {pf}")
        app = h.R / "apply.txt"; app.write_text("\n".join(cmds) + "\n")
        if h.vbl() >= at: raise ValueError('at_vbl passed')
        h.cmd(f"hatari-debug b VBL > {at} && pc = ${FLIP:x} :trace :once :file {app}")
        t = time.time()
        while not (od / f"ptr_{flips[-1]}.bin").exists():
            if time.time() - t > 400: raise TimeoutError("cap")
            time.sleep(0.5)
        time.sleep(1.0)
    finally:
        h.close()

def to_png(od, k, name):
    from PIL import Image
    pal = (Path(od) / f"pal_{k}.bin").read_bytes()
    cols = []
    for i in range(16):
        v = int.from_bytes(pal[2*i:2*i+2], 'big')
        r, g, b = ((v >> 8) & 15), ((v >> 4) & 15), (v & 15)
        f = lambda x: (((x & 7) << 1) | (x >> 3)) * 17
        cols.append((f(r), f(g), f(b)))
    out = Image.new('RGB', (320, 200))
    px = out.load()
    for which in ('b60', 'b70'):
        pass
    return cols

def png(od, k, which, dst):
    from PIL import Image
    cols = to_png(od, k, which)
    d = (Path(od) / f"{which}_{k}.bin").read_bytes()[:32000]
    im = Image.new('RGB', (320, 200))
    px = im.load()
    for y in range(200):
        for g in range(20):
            o = y * 160 + g * 8
            pl = [int.from_bytes(d[o + 2*p:o + 2*p + 2], 'big') for p in range(4)]
            for x in range(16):
                bit = 15 - x
                c = sum(((pl[p] >> bit) & 1) << p for p in range(4))
                px[g * 16 + x, y] = cols[c]
    im = im.resize((640, 400), Image.NEAREST)
    im.save(dst)

def ident(snap, a, b, flips, mem, pokes, tag, wantpng):
    h = Hatari(snapshot=snap, memsize_kb=mem)
    try:
        v = h.vbl(); at = (v // 100 + 4) * 100
    finally:
        h.close()
    base = f"/tmp/sk/g/{tag}/A"; pat = f"/tmp/sk/g/{tag}/B"
    for d in (base, pat): shutil.rmtree(d, ignore_errors=True)
    with ThreadPoolExecutor(2) as ex:
        fa = ex.submit(run, snap, a, flips, base, mem, pokes, at)
        fb = ex.submit(run, snap, b, flips, pat, mem, pokes, at)
        fa.result(); fb.result()
    ok = True; rows = []
    for k in flips:
        vis = 0
        for n in ('b60', 'b70'):
            x = (Path(base) / f"{n}_{k}.bin").read_bytes()[:32000]; y = (Path(pat) / f"{n}_{k}.bin").read_bytes()[:32000]
            vis += sum(1 for i in range(32000) if x[i] != y[i])
        c = counters((Path(pat) / f"cnt_{k}.bin").read_bytes())
        ptr = (Path(pat) / f"ptr_{k}.bin").read_bytes().hex()
        pos = (Path(pat) / f"pos_{k}.bin").read_bytes().hex()
        npc = (Path(pat) / f"npc_{k}.bin").read_bytes()
        npcs = 'npc0 x=%d y=%d' % (int.from_bytes(npc[0:4],'big',signed=True), int.from_bytes(npc[4:8],'big',signed=True))
        rows.append((k, vis, c, pos))
        ok &= (vis == 0)
        print(f"flip {k:4d}: visible differing bytes (both buffers) = {vis:6d}   B counters {c}   pos {pos} {npcs}")
        if wantpng:
            png(pat, k, 'b60', f"/tmp/sk/g/{tag}/B_{k}_60000.png"); png(base, k, 'b60', f"/tmp/sk/g/{tag}/A_{k}_60000.png")
    print(Path(snap).stem, tag, 'IDENTICAL' if ok else 'DIFFER')
    return ok

if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('mode'); ap.add_argument('snap'); ap.add_argument('A'); ap.add_argument('B'); ap.add_argument('flips')
    ap.add_argument('--mem', type=int, default=1024); ap.add_argument('--poke', action='append', default=[])
    ap.add_argument('--tag', default='x'); ap.add_argument('--png', action='store_true')
    a = ap.parse_args()
    pokes = []
    for p in a.poke:
        k, cs = p.split(':', 1)
        pokes.append((int(k), [c.strip() for c in cs.split(';') if c.strip()]))
    ok = ident(a.snap, a.A, a.B, [int(x) for x in a.flips.split(',')], a.mem, pokes, a.tag, a.png)
    sys.exit(0 if ok else 1)
