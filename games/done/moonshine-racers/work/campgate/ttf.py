#!/usr/bin/env python3
"""TT and Falcon stay stock: cold boot of the campaign build (HD or floppy) on a TT (TOS 3.06) or Falcon (TOS 4.04), wait for the payload marker, print marker / IB+4 / HAGA machine type / every campaign site.
   env.sh python3 ttf.py --kind hd|fl --machine tt|falcon --mem 4096   (TT: Hatari --mmu true; binary: $HATARI_TTF else $HATARI)"""
import argparse, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from cg import *
ap = argparse.ArgumentParser()
ap.add_argument("--kind", default="hd"); ap.add_argument("--machine", default="tt"); ap.add_argument("--mem", type=int, default=4096); ap.add_argument("--build"); ap.add_argument("--wait", type=int, default=240)
a = ap.parse_args()
build = a.build or ("/tmp/msrc3/hd_a" if a.kind == "hd" else "/tmp/msrc3/fl_a")
tag = f"ttf_{a.kind}_{a.machine}{a.mem // 1024}m"
logopen(tag)
tos = {"tt": "3.06", "falcon": "4.04"}[a.machine]
r = Run(a.kind, a.machine, a.mem, tag, build=build, disk_a=(Path(build) / "disk_a.st") if a.kind == "fl" else None,
        extra_args=["--mmu", "true"] if a.machine == "tt" else [], tos=tos)
try:
    t0 = time.time(); mk = b""
    r.ff(True)
    while time.time() - t0 < a.wait:
        time.sleep(1.0)
        try: mk = r.mem(0xb2700, 8)
        except Exception: continue
        if mk[:4] in (b"MSPO", b"MSPF"): break
    r.ff(False); time.sleep(5)
    mk = r.mem(0xb2700, 8)
    log(f"== {tag}: vbl {r.vbl()} marker {mk[:4]!r} IB+4 {mk[4]:#04x}")
    if a.kind == "hd":
        base = r.l(0x2dc); log(f"$2dc={base:#x} $42e={r.l(0x42e):#x} HAGA+$83={r.b(base + 0x83):#04x}")
    SITES = ((0x72c4, 6), (0x77da, 12), (0xfda2, 6), (0x731e, 6), (0x7252, 6), (0x74fe, 6), (0x8418, 6))
    sites = {hex(x): r.mem(x, n).hex() for x, n in SITES}
    log("sites", sites)
    stock = {'0x72c4': '4eb9000076f4', '0x77da': '41f900058c004eb90000d6fa', '0xfda2': '41f900058c00', '0x731e': '0c40000f6408', '0x7252': '4eb9000073b8', '0x74fe': '4fef000e6106', '0x8418': '610644fc00ff'}
    check("marker present (the payload ran)", mk[:4] == b"MSPO", f"{mk[:4]!r}")
    check("gate closed: IB+4 == 0", mk[4] == 0)
    check("every campaign site holds the stock bytes", sites == stock)
    r.shot("boot")
finally:
    r.close()
sys.exit(1 if FAILS else 0)
