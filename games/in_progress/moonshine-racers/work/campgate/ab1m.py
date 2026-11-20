#!/usr/bin/env python3
"""1 MB A/B of the campaign build against the shipped v1.0.1 (HD or floppy), one machine.
   env.sh python3 ab1m.py --kind hd|fl --machine ste|megaste|st|megast [--build DIR] [--passes 160]
  1. cold boots to the title: marker, IB+4 (must be 0: gate closed), every campaign site byte vs the v1.0.1 RAM (identical);
  2. the NEW build: F10 at the title behaves as any key, exec breakpoints over every campaign code range through title, F10, race and 2000 VBL of driving: zero hits;
  3. per-pass STATE A/B from the v1.0.1 race memstate: v1.0.1 as is (A) vs v1.0.1 + the new payload image loaded at $B2700 (B), over N passes, plus all of RAM below the payload at pass N."""
import argparse, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from cg import *
import msrpatch as P

ap = argparse.ArgumentParser()
ap.add_argument("--kind", default="hd"); ap.add_argument("--machine", default="ste"); ap.add_argument("--build"); ap.add_argument("--passes", type=int, default=160)
a = ap.parse_args()
KIND, M = a.kind, a.machine
V101 = Path("/tmp/msrc2/v101")
ref_build = V101 / "MOONSHR" if KIND == "hd" else V101 / "MOONSHR_floppy"
new_build = Path(a.build or ("/tmp/msrc2/hd_a" if KIND == "hd" else "/tmp/msrc2/fl_a"))
tag = f"ab1m_{KIND}_{ {'ste': 'ste', 'megaste': 'mste', 'st': 'st', 'megast': 'mst'}[M] }"
logopen(tag)
SITES = [(0x72c4, 6), (0x77da, 12), (0xfda2, 6), (0x731e, 6), (0x7252, 6), (0x74fe, 6), (0x8418, 6)]
# campaign code of the new build: hooks A $B8022.., B $B8070.., D $B8220.., start $B8240.., menu/reader $B9F00..+3068 (HD) / +3132 (floppy), the variables CPV $B8E00
RANGES = [(0xb8022, 0xb80c2), (0xb8220, 0xb8260), (0xb9f00, 0xb9f00 + (3132 if KIND == "fl" else 3068))]
STATE = [(0x1000, 0x400), (0x29C8, 0xB38), (0x4500, 0xB00), (0xDAE6, 4)]
SNAP = Path(f"/tmp/msrc2/snap/ab1m_{KIND}_{M}_ref.sav")

def mk(build, name, snap=None):
    if KIND == "hd":
        return Run("hd", M, 1024, f"{tag}_{name}", build=build, snap=snap)
    return Run("fl", M, 1024, f"{tag}_{name}", build=build, snap=snap, disk_a=Path(build) / "disk_a.st", d2=Path(build) / "disk_b.st")

def cold(build, name, f10=False, save=False):
    r = mk(build, name)
    try:
        r.ff(False)
        ok = r.boot_title(); log(f"[{name}] title reached {ok} vbl {r.vbl()} $1021 {r.b(0x1021):#x}")
        mk_ = r.mem(0xb2700, 8)
        info = {"marker": mk_[:4].decode("latin1"), "IB+4": mk_[4], "sites": {hex(ad): r.mem(ad, n).hex() for ad, n in SITES}}
        if KIND == "hd":
            base = r.l(0x2dc); info.update({"$2dc": hex(base), "$42e": hex(r.l(0x42e)), "HAGA+$83": r.b(base + 0x83)})
        log(f"[{name}] {info}")
        if name == "new":
            r.h.debug("b all", 0.3)
            for lo, hi in RANGES: r.h.cmd(f"hatari-debug b pc >= ${lo:x} && pc < ${hi:x} :trace"); time.sleep(0.2)
            n0 = len(r.h._logtext())
        if f10:
            r.key(0x44); time.sleep(4)
            log(f"[{name}] after F10 at the title: $1021 {r.b(0x1021):#x} $100e {r.w(0x100e)}"); r.shot("after_f10")
        res = r.wait_race(tmo=400, shop=False)
        log(f"[{name}] race ready {res is not None} vbl {r.vbl()} marker {r.mem(0xb2700, 4)}")
        if res is None: return info
        r.poke(0x6105, 0x01)
        v = r.vbl()
        while r.vbl() < v + 2000: time.sleep(2)
        log(f"[{name}] driving: $5ff8 {r.w(0x5ff8)} $130c {r.w(0x130c)} $100e {r.w(0x100e)}")
        if name == "new":
            lg = r.h._logtext()[n0:]
            nh = len([l for l in lg.splitlines() if "pc >=" in l or ("pc =" in l and ":trace" in l)])
            r.h.debug("b all", 0.3)
            log(f"[{name}] EXEC BREAKPOINT HITS in the campaign code ranges (title incl. F10, race, 2000 VBL driving): {nh}")
            check("no campaign code executed at 1 MB", nh == 0)
        r.poke(0x6105, 0x00)
        if save:
            r.h.cmd("hatari-debug b all"); time.sleep(1)
            sav = Path(os.environ["HOME"]) / ".config/hatari/hatari.sav"; sav.unlink(missing_ok=True); r.h.state = sav
            r.h.savemem(str(SNAP)); sav.unlink(missing_ok=True)
        return info
    finally:
        r.close()

def state_run(image, npass, dump_at=None):
    """npass per-pass STATE dumps (pass boundary $7b86), or with dump_at: the CPU halts at the first pass boundary where $100e == dump_at (a breakpoint without :trace stops the CPU
    in the debugger, after the command file ran) and all of RAM $400-$B1F00 is saved: both runs stop at the same pass"""
    r = mk(ref_build, "dumpB" if image and dump_at else "dumpA" if dump_at else "stateB" if image else "stateA", snap=SNAP)
    h = r.h; ramf = f"/tmp/msrc2/ab1m_{KIND}_{M}_{'B' if image else 'A'}.bin"; lg = ""
    try:
        time.sleep(1.5)
        if image: h.debug(f"loadbin {image} $b2700", 1.5)
        h.debug("b all", 0.3); n0 = len(h._logtext())
        if dump_at:
            Path(ramf).unlink(missing_ok=True)
            dump = h.R / "dump.txt"; dump.write_text(f"savebin {ramf} $400 $b1f00\n")
            h.cmd(f"hatari-debug b pc = $7b86 && ($100e).w = {dump_at} :once :file {dump}")
            t0 = time.time()
            while not Path(ramf).exists() and time.time() - t0 < 600: time.sleep(1)
            time.sleep(2)
            return None, ramf
        f = h.R / "state.txt"; f.write_text("e VBL\n" + "".join(f"m ${a_:x} {n}\n" for a_, n in STATE))
        h.cmd(f"hatari-debug b pc = $7b86 :trace :file {f}")
        t0 = time.time()
        while h._logtext()[n0:].count("> e VBL") < npass + 2 and time.time() - t0 < 1800: time.sleep(1)
        time.sleep(1); h.debug("b all", 0.5); lg = h._logtext()[n0:]
    finally:
        r.close()
    res = {}
    for ht in lg.split("> e VBL")[1:]:
        d = {}
        for ln in ht.splitlines():
            m = re.match(r"([0-9a-f]{8}):\s+((?:[0-9a-f]{2} ?){1,16})", ln, re.I)
            if m:
                ad = int(m.group(1), 16)
                for i, x in enumerate(bytes.fromhex(m.group(2).replace(" ", ""))): d[ad + i] = x
        if 0x100E in d: res[(d[0x100E] << 8) | d[0x100F]] = d
    return res, ramf

ia = cold(ref_build, "ref", save=True)
ib = cold(new_build, "new", f10=True)
check("marker MSPO in both", ia["marker"] == ib["marker"] == "MSPO")
check("IB+4 = 0: the gate is closed (list 2 not applied)", ib["IB+4"] == 0, f"IB+4={ib['IB+4']:#x}")
check("every campaign site holds the v1.0.1 bytes", ia["sites"] == ib["sites"], f"{ib['sites']}")
sel, fsel = P.default_selection(P.load_patches(), P.load_file_patches(), KIND == "fl")
sel = [p for p in sel if p.site is not None]
if KIND == "fl":
    P.set_flavour(True); tb = P.IB + 0x120
    img, _ = P.build_image(sel, table=tb, min_end=tb + 0x100, floppy=True)
else:
    P.set_flavour(False); img, _ = P.build_image(sel, fnames=[p.name for p in fsel])
imgf = Path(f"/tmp/msrc2/ab1m_{KIND}_image.bin"); imgf.write_bytes(img)
A, _ = state_run(None, a.passes); B, _ = state_run(imgf, a.passes)
tgt = min(set(A) & set(B)) + a.passes
_, ramA = state_run(None, 0, dump_at=tgt); _, ramB = state_run(imgf, 0, dump_at=tgt)
common = sorted(set(A) & set(B)); diff = 0; cmp_ = 0
for k in common:
    for ad, x in A[k].items():
        if ad in B[k]:
            cmp_ += 1; diff += B[k][ad] != x
log(f"STATE A/B ({KIND} {MACH[M]} 1 MB): passes A {len(A)} B {len(B)} common {len(common)}  bytes compared {cmp_}  different {diff}")
check("per-pass state identical", diff == 0 and len(common) >= a.passes * 0.9)
try:
    ba, bb = Path(ramA).read_bytes(), Path(ramB).read_bytes()
    nd = [i for i in range(min(len(ba), len(bb))) if ba[i] != bb[i]]
    runs = []
    for i in nd:
        if runs and i - runs[-1][1] <= 16: runs[-1][1] = i
        else: runs.append([i, i])
    log(f"RAM $400-$B1EFF at the pass boundary with $100e == {tgt}: {len(ba)} B vs {len(bb)} B, {len(nd)} differing bytes; runs: {[(hex(x + 0x400), hex(y + 0x400)) for x, y in runs[:12]]}")
    check("RAM below the payload identical at pass N", len(nd) == 0 and len(ba) == len(bb) > 0)
except Exception as e:
    log("RAM compare failed:", e); FAILS.append("ram compare")
log(f"== {tag} done: {'ALL CHECKS PASS' if not FAILS else 'FAILED: ' + ', '.join(FAILS)}")
sys.exit(1 if FAILS else 0)
