#!/usr/bin/env python3
"""Track editor: the 1 MB absence check (HD build, one machine).
   work/edgate/env.sh python3 work/edgate/abs1m.py --machine ste [--build DIR] [--ref DIR]
  1. static: RUNME.TOS of the new build against the shipped v1.1 RUNME.TOS: where they differ (expected: only inside cp_title's blob, which holds the new menu item and ed_load);
  2. cold boot at 1 MB with `--trace gemdos`: marker MSPO, IB+4 = 0 (gate closed), the eight campaign sites hold the stock bytes, F10 on the title starts the game like any key,
     a race runs; execution breakpoints over the whole cp_title blob never fire; no GEMDOS call ever names MSEDIT.OVL."""
import argparse, sys, os
from pathlib import Path
HERE = Path(__file__).resolve().parent
os.environ.setdefault("CG_LOGS", str(HERE / "logs"))
sys.path.insert(0, str(HERE.parent / "campgate"))
from cg import *
import msrpatch as P

ap = argparse.ArgumentParser(); ap.add_argument("--machine", default="ste"); ap.add_argument("--build", default="/tmp/msred/hd"); ap.add_argument("--ref", default="/tmp/msred/v11/MOONSHR")
a = ap.parse_args()
tag = f"abs1m_{ {'ste': 'ste', 'megaste': 'mste', 'st': 'st', 'megast': 'mst'}[a.machine] }"
logopen(tag)
SITES = {0x7c04: "4a3860ff67f8", 0x72c4: "4eb9000076f4", 0x77da: "41f900058c004eb90000d6fa", 0xfda2: "41f900058c00", 0x731e: "0c40000f6408", 0x7252: "4eb9000073b8", 0x74fe: "4fef000e6106", 0x8418: "610644fc00ff"}
new, ref = (Path(a.build) / "RUNME.TOS").read_bytes(), (Path(a.ref) / "RUNME.TOS").read_bytes()
blob = [f for f in P.footprint(next(p for p in P.load_patches() if p.name == "cp_title")) if f[2] == "blob"][0]
anchor = new.find(bytes.fromhex("4ef9000b9f12"))                      # cp_title's first bytes (jmp e1.l, now at $B9F12 behind the three-entry jump table) = address $B9F00 in the file
diffs = [i for i in range(min(len(new), len(ref))) if new[i] != ref[i]]
addrs = [i - anchor + 0xb9f00 for i in diffs]
lo, hi = (addrs[0], addrs[-1]) if diffs else (0, 0)
outside = [x for x in addrs if not (blob[0] <= x < blob[1] or P.IB <= x < P.TABLE_END)]
log(f"== {tag}: RUNME.TOS new {len(new)} B, v1.1 {len(ref)} B; {len(diffs)} differing bytes, payload addresses ${lo:x}..${hi:x}; cp_title blob ${blob[0]:x}-${blob[1] - 1:x}")
log(f"differing bytes outside cp_title's blob and the trampoline (core + site tables, ${P.IB:x}-${P.TABLE_END - 1:x}): {len(outside)}")
check("RUNME.TOS differs from v1.1 only inside cp_title's blob and the trampoline's own core / site tables", len(new) == len(ref) and diffs and not outside)
for f in ("HAGA", "FILES/MS1", "FILES/MS2", "FILES/MSR_S1.FIC"):
    check(f"{f} identical to v1.1", (Path(a.build) / f).read_bytes() == (Path(a.ref) / f).read_bytes())
r = Run("hd", a.machine, 1024, tag, build=a.build, sound=True, extra_args=["--trace", "gemdos"])
try:
    ok = r.boot_title(); log(f"title reached: {ok} vbl {r.vbl()}"); check("title reached", ok)
    mk = r.mem(0xb2700, 5); st = {ad: r.mem(ad, len(o) // 2).hex() for ad, o in SITES.items()}
    log(f"marker {mk[:4]} IB+4 {mk[4]:#x} $42e {r.l(0x42e):#x} sites {st}")
    check("marker MSPO, gate closed (IB+4 = 0)", mk[:4] == b"MSPO" and mk[4] == 0)
    check("the eight campaign sites hold the stock bytes", all(st[ad] == o for ad, o in SITES.items()))
    r.h.cmd(f"hatari-debug b pc >= ${blob[0]:x} && pc < ${blob[1]:x} :trace"); time.sleep(0.5); n0 = len(r.h._logtext())
    r.h.cmd("hatari-event keypress 0x44"); time.sleep(4)                  # F10 at the title
    res = r.wait_race(tmo=300)
    check("F10 on the title starts the game like any key: race 1 (stock block at $58c00)", res is not None and res[2] >> 8 == 0x58c, f"{res}")
    r.poke(0x6105, 0x01); time.sleep(20); p = r.w(0x5ff8); r.poke(0x6105, 0x00)
    check("the race runs", p > 100, f"$5ff8 {p}")
    t = r.h._logtext()
    check("no instruction of cp_title's blob was executed (title, F10, race)", "pc >= $" not in t[n0:].replace("b pc >=", ""), "")
    check("no GEMDOS call names MSEDIT.OVL", "MSEDIT" not in t.upper(), f"GEMDOS trace lines: {t.count('GEMDOS')}")
    log(f"Bus/Address error lines: {r.errlines()}")
except Exception:
    import traceback; log("EXCEPTION", traceback.format_exc()); FAILS.append("exception")
finally:
    r.close()
log(f"RESULT {tag}: {'ALL CHECKS PASS' if not FAILS else 'FAILED: ' + ', '.join(FAILS)}")
