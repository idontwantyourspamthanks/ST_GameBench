"""Stress cell: N saves in a row through the requester (HD media), crash detection.  python3 cell_loop.py --tag X --build DIR --n 25 [--media acsi]"""
import argparse, shutil, sys, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from sv import *

ap = argparse.ArgumentParser()
ap.add_argument("--tag", required=True); ap.add_argument("--build", default="build/Pop2Save"); ap.add_argument("--media", default="acsi")
ap.add_argument("--machine", default="ste"); ap.add_argument("--tos", default=None); ap.add_argument("--mem", type=int, default=2048)
ap.add_argument("--n", type=int, default=25); ap.add_argument("--load", action="store_true", help="alternate save and load")
a = ap.parse_args()
P = lambda *x: print(*x, flush=True)
OUT = SD / f"out_{a.tag}"; OUT.mkdir(exist_ok=True)
h, info = make(a.media, a.build, a.machine, a.tos, a.mem, a.tag)
try:
    ok = h.boot_to_game(); P(f"CELL {a.tag}: {info} in_play={ok} marker={h.marker()!r} turn={turn(h)}")
    time.sleep(5)
    nbad0 = len(logbad(h)); crashed = None
    for i in range(a.n):
        t0 = time.time()
        nm = "l%d" % (i % 4)
        try:
            if a.load and i % 2 == 1 and i >= 3:
                arm(h, 0x2cc5e, OUT / f"L{i}.bin", tag=f"L{i}")
                assert open_req(h); choose(h, "load"); name(h, "l%d" % ((i - 1) % 4)); confirm(h)
                okf = waitfile(OUT / f"L{i}.bin", 40); r = wait_running(h, 60)
                what = "load"
            else:
                assert open_req(h); choose(h, "save"); name(h, nm); confirm(h)
                r = wait_running(h, 60); okf = True; what = "save"
        except Exception as e:
            r = False; what = "EXC " + repr(e)
        bad = logbad(h)
        st = "ok" if (r and okf and len(bad) == nbad0) else "FAIL"
        P(f"{i:2d} {what} {nm} running={r} turn={turn(h) if r else None} t={time.time()-t0:.0f}s new_log_errors={len(bad)-nbad0} {st}")
        if st != "ok":
            crashed = i; break
        time.sleep(1)
    bad = logbad(h)
    P(f"LOG lines: {len(bad)}"); [P("  ", l) for l in bad[:8]]
    P(f"RESULT {a.tag}: " + ("PASS %d/%d" % (a.n, a.n) if crashed is None else f"CRASH at call #{crashed}"))
except Exception as e:
    import traceback; traceback.print_exc(); P("EXCEPTION", repr(e))
finally:
    shutil.copy(h.logpath, SD / f"{a.tag}.log")
    h.close()
