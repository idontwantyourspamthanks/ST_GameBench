#!/usr/bin/env python3
"""Empty drive A, HD build: time from 'LOAD CAMPAIGN FROM DRIVE A' (Return) to the message, in VBL (fine polling of M_MSG, normal speed), plus a PC histogram.
   env.sh python3 emptya.py --machine ste|megaste [--mem 2048] [--build DIR]"""
import argparse, sys, collections
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from cg import *
ap = argparse.ArgumentParser(); ap.add_argument("--machine", default="ste"); ap.add_argument("--mem", type=int, default=2048); ap.add_argument("--build", default="/tmp/msrc3/hd_a"); ap.add_argument("--item", type=int, default=2); ap.add_argument("--sample", action="store_true", help="also sample PC once a second (slows the run: off for the timing)")
a = ap.parse_args()
tag = f"emptya_{a.machine}{a.mem // 1024}m"; logopen(tag)
r = Run("hd", a.machine, a.mem, tag, build=a.build)
try:
    r.ff(False)
    assert r.boot_title(); r.ff(False)
    r.menu_open(); time.sleep(1)
    for _ in range(8):
        s = r.w(0x100406)
        if s == a.item: break
        r.key(0x50 if s < a.item else 0x48); time.sleep(0.6)
    log("menu item", r.w(0x100406), "msg before", hex(r.l(0x10040a)))
    texts_start(r); r.key(0x1c); v0 = r.vbl(); t0 = time.time(); hist = collections.Counter(); samples = []
    while time.time() - t0 < 400:
        time.sleep(0.2)
        if any(t[1] == 20 and t[2].strip() and '...' not in t[2] for t in texts_peek(r)):
            v1 = r.vbl(); break
        if a.sample and int(time.time() * 5) % 5 == 0:
            try:
                o = r.h.debug("r", 0.15); m = re.search(r"PC[: =]+\s*([0-9a-fA-F]{6,8})", o)
                if m: pc = int(m.group(1), 16); hist[pc >> 12] += 1; samples.append((round(time.time() - t0, 1), hex(pc)))
            except Exception as e: pass
    else: v1 = None
    tx = [t[2] for t in texts_stop(r) if t[1] == 20]; log('row-20 texts:', tx)
    hz = 60.0 if a.machine == "megaste" else 50.0
    log(f"RESULT {tag}: Return at vbl {v0}; message at vbl {v1}; " + ("NO MESSAGE within 400 s wall" if v1 is None else f"delta {v1 - v0} VBL = {(v1 - v0) / hz:.1f} s at {hz:.0f} Hz") + f"; wall {time.time() - t0:.1f} s")
    log("PC histogram (4 KB pages):", {hex(k << 12): v for k, v in sorted(hist.items(), key=lambda kv: -kv[1])[:12]})
    log("PC samples:", samples[:60])
    texts = None
finally:
    r.close()
