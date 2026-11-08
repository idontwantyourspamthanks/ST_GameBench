#!/usr/bin/env python3
"""P7 cockpit-cull gate tooling (patches p7_ck_*).

  python3 work/p7_ck/ck.py ident <snap> <setA|-> <setB> <flips,flips,...> [tag]
  python3 work/p7_ck/ck.py cyc   <snap> <set|-> <k1> <k2> [tag]

Sets are names of 'mw2patch.py live' prefixes under /tmp/ck/ (or '-' = nothing live-applied).
ident: both screen buffers ($60000/$70000, $8000 bytes each) captured after each flip count for
       A and B (two Hatari instances), reports visible-area (32000 B) and dead-area ($7d00-$7fff) diffs.
cyc:   total 68000 cycles between the k1-th and k2-th flip after the (live) apply flip: same game
       frames in every run (per-frame simulation, no tick/p3b/p5 patches).
"""
import sys, json, time, hashlib, re
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'tools'))
from mw2harness import Hatari
from concurrent.futures import ThreadPoolExecutor
FLIP = 0x26E98

def live_cmds(prefix):
    if not prefix:
        return []
    spec = json.loads(Path(prefix + '.json').read_text())
    c = [f"loadbin {Path(prefix + '.img').resolve()} ${spec['img_base']:x}"]
    for s in spec['sites']:
        c.append(f"w ${s['addr']:x} " + " ".join(f"${b:02x}" for b in bytes.fromhex(s['new'])))
    return c

def at_vbl(h):
    v = h.vbl()
    return (v // 100 + 4) * 100

def cap_run(snap, prefix, ks, out, at):
    h = Hatari(snapshot=snap)
    try:
        od = Path(out); od.mkdir(parents=True, exist_ok=True)
        cmds = live_cmds(prefix)
        for k in ks:
            cf = h.R / f"cap{k}.txt"
            cf.write_text(f"savebin {od}/b60_{k}.bin $60000 $8000\nsavebin {od}/b70_{k}.bin $70000 $8000\nsavebin {od}/ptr_{k}.bin $67a6 8\n")
            cnt = f" :{k}" if k > 1 else ""
            cmds.append(f"b pc = ${FLIP:x}{cnt} :trace :once :file {cf}")
        app = h.R / "apply.txt"; app.write_text("\n".join(cmds) + "\n")
        if h.vbl() >= at: raise ValueError('at_vbl passed')
        h.cmd(f"hatari-debug b VBL > {at} && pc = ${FLIP:x} :trace :once :file {app}")
        t = time.time()
        while not (od / f"ptr_{ks[-1]}.bin").exists():
            if time.time() - t > 1500: raise TimeoutError("cap")
            time.sleep(0.5)
        time.sleep(1.0)
        # counters block (if any)
        cnt = h.debug("m $b5000 48", 0.8)
        (od / 'counters.txt').write_text(cnt)
    finally:
        h.close()

def ident(snap, a, b, ks, tag='x'):
    h = Hatari(snapshot=snap)
    try:
        at = at_vbl(h)
    finally:
        h.close()
    base = f"/tmp/ck/id/{tag}/A"; pat = f"/tmp/ck/id/{tag}/B"
    for d in (base, pat):
        import shutil; shutil.rmtree(d, ignore_errors=True)
    with ThreadPoolExecutor(2) as ex:
        fa = ex.submit(cap_run, snap, a, ks, base, at)
        fb = ex.submit(cap_run, snap, b, ks, pat, at)
        fa.result(); fb.result()
    allok = True; rows = []
    for k in ks:
        vis = 0; dead = 0; full = True
        for n in ('b60', 'b70'):
            x = (Path(base) / f"{n}_{k}.bin").read_bytes(); y = (Path(pat) / f"{n}_{k}.bin").read_bytes()
            vis += sum(1 for i in range(32000) if x[i] != y[i])
            dead += sum(1 for i in range(32000, 32768) if x[i] != y[i])
        rows.append((k, vis, dead))
        allok &= (vis == 0)
    print(Path(snap).stem, 'flips', ks, 'VISIBLE IDENTICAL' if allok else 'VISIBLE DIFF', rows)
    return allok

def cyc(snap, prefix, k1, k2, tag='x'):
    h = Hatari(snapshot=snap)
    try:
        at = at_vbl(h)
        cmds = live_cmds(prefix)
        st = h.R / "pst.txt"; st.write_text("profile on\n")
        en = h.R / "pen.txt"; en.write_text("profile cycles 30000\n")
        cmds.append(f"b pc = ${FLIP:x} :{k1} :trace :once :file {st}")
        cmds.append(f"b pc = ${FLIP:x} :{k2} :trace :once :file {en}")
        app = h.R / "apply.txt"; app.write_text("\n".join(cmds) + "\n")
        start = len(h._logtext())
        h.cmd(f"hatari-debug b VBL > {at} && pc = ${FLIP:x} :trace :once :file {app}")
        t = time.time()
        while "profile cycles" not in h._logtext()[start:] and "0x" not in h._logtext()[start:]:
            time.sleep(0.5)
            if time.time() - t > 1500: raise TimeoutError
        t = time.time()
        while time.time() - t < 600:
            txt = h._logtext()[start:]
            if re.search(r"^0x[0-9a-f]+\s+[\d.]+%\s+\d+", txt, re.M) and txt.count("Removed CPU breakpoint") >= 3:
                break
            time.sleep(0.5)
        time.sleep(1.0)
        txt = h._logtext()[start:]
        rows = [(int(a, 16), int(c)) for a, c in re.findall(r"^0x([0-9a-f]+)\s+[\d.]+%\s+(\d+)", txt, re.M)]
        tot = sum(c for _, c in rows)
        per = tot / (k2 - k1)
        print(Path(snap).stem, prefix or 'base', f"cycles {tot} over {k2-k1} frames = {per:.0f} cy/frame ({len(rows)} addrs)")
        Path(f"/tmp/ck/cyc_{tag}.json").write_text(json.dumps(rows))
        return per
    finally:
        h.close()

if __name__ == '__main__':
    m = sys.argv[1]
    snap = sys.argv[2]
    def pre(x): return None if x == '-' else f"/tmp/ck/{x}"
    if m == 'ident':
        ok = ident(snap, pre(sys.argv[3]), pre(sys.argv[4]), [int(x) for x in sys.argv[5].split(',')], sys.argv[6] if len(sys.argv) > 6 else 'x')
        sys.exit(0 if ok else 1)
    elif m == 'cyc':
        cyc(snap, pre(sys.argv[3]), int(sys.argv[4]), int(sys.argv[5]), sys.argv[6] if len(sys.argv) > 6 else 'x')
