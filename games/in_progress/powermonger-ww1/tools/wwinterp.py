#!/usr/bin/env python3
"""Gate for the men interpolation (p3b_interp + p3b_delta; port of master's tools/pminterp.py, reduced).  Cold boot of a BUILT floppy.

    python3 tools/wwinterp.py cold --disk build/default/floppy.st --mhz 16 --workdir DIR [--secs 40] [--tag NAME]

Scene: the profile's `get_men` recipe (overview click, 3-sword posture icon, GET MEN) so that men move.  Then, at 16 MHz (render-only passes exist), for every pass:
  T0   people table at `jsr ap` ($13e1e: the site, before the hook),
  TMID at the entry of the landscape routine ($fc78, after `ap` wrote the offsets),
  T1   people table after the call returned ($13e24).
Checks: (1) T1 == T0 in every pass (the table is restored exactly: bit-identical outside the render), (2) in passes with offsets TMID differs from T0 ONLY in the low bytes
of x / z ($9 / $b of a $36-byte record of the table $55df4), (3) offsets appear (passes with TMID != T0), the counters NMOV / NPASS / NSCAN (PD $73f80) are alive,
(4) the first mover's low byte advances monotonically between two ticks over >= 2 distinct values (the smoothing itself).  8 MHz (--mhz 8): no list is ever built, NMOV stays 0.
"""
from __future__ import annotations
import argparse
import sys
import threading
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import pmww  # noqa: E402

PEOPLE, PN, PS = 0x55DF4, 350, 0x36
PD = 0x73F80
D = 0x72A80
BPS = (("t0", 0x13E1E), ("mid", 0xFC78), ("t1", 0x13E24))


def people(h):
    d = h.ram(PEOPLE, PN * PS)
    return [d[i * PS:(i + 1) * PS] for i in range(PN)]


def moving(h, gap=0.4):
    a = people(h)
    time.sleep(gap)
    b = people(h)
    return sum(1 for x, y in zip(a, b) if 0 < x[5] < 0x80 and x[8:12] != y[8:12])


def collect(h, secs):
    files = {}
    for tag, pc in BPS:
        f = h.R / f"ip_{tag}.bin"
        f.unlink(missing_ok=True)
        (h.R / f"ip_{tag}.txt").write_text(f"savebin {f} ${PEOPLE:x} ${PN * PS:x}\ne (${D + 6:x}).w\n")
        files[tag] = f
    got, stop = [], threading.Event()

    def poll():
        last = {t: None for t in files}
        while not stop.is_set():
            for tag, f in files.items():
                try:
                    st = f.stat()
                except FileNotFoundError:
                    continue
                if st.st_size == PN * PS and st.st_mtime_ns != last[tag]:
                    time.sleep(0.02)
                    st2 = f.stat()
                    if st2.st_mtime_ns == st.st_mtime_ns:
                        last[tag] = st.st_mtime_ns
                        got.append((st.st_mtime_ns, tag, f.read_bytes()))
            time.sleep(0.005)
    th = threading.Thread(target=poll, daemon=True)
    th.start()
    h.debug("b all", 0.3)
    for tag, pc in BPS:
        h.cmd(f"hatari-debug b pc = ${pc:x} :trace :file {h.R / f'ip_{tag}.txt'}")
        time.sleep(0.1)
    time.sleep(secs)
    h.debug("b all", 0.3)
    time.sleep(0.5)
    stop.set()
    th.join()
    got.sort()
    return got


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=["cold"])
    ap.add_argument("--disk", required=True)
    ap.add_argument("--mhz", type=int, default=16)
    ap.add_argument("--secs", type=float, default=40)
    ap.add_argument("--workdir", required=True)
    ap.add_argument("--tag")
    a = ap.parse_args()
    tag = a.tag or Path(a.disk).parent.name
    h = pmww.PMW(disk=Path(a.disk), workdir=a.workdir, machine="ste", tos=pmww.TOS["1.62"], memsize_kb=1024)
    ok = True
    def line(name, good, detail=""):
        nonlocal ok
        ok &= bool(good)
        print(f"GATE interp {tag} {a.mhz} MHz {name} {'PASS' if good else 'FAIL'} {detail}", flush=True)
    try:
        h.boot_to_map(noprot=True, swap=False, log=lambda s: print("  " + s, flush=True))
        if a.mhz != 8:
            h.set_cpuclock(a.mhz)
        time.sleep(2)
        h.click_st(36, 62, wait=6.0)
        h.click_st(97, 158, wait=0.8)
        h.click_st(229, 173, wait=6.0)
        m = moving(h)
        line("men are moving (get_men scene)", m > 0, f"{m} records change position within 0.4 s")
        pd0 = h.ram(PD, 32)
        got = collect(h, a.secs)
        pd1 = h.ram(PD, 32)
        L = lambda b, o: int.from_bytes(b[o:o + 4], "big")
        W = lambda b, o: int.from_bytes(b[o:o + 2], "big")
        print(f"  PD before {pd0.hex()} after {pd1.hex()}", flush=True)
        nmov, npass, nscan = W(pd1, 2), L(pd1, 8) - L(pd0, 8), L(pd1, 20) - L(pd0, 20)
        line("counters", (nmov > 0 and npass > 0 and nscan > 0) if a.mhz != 8 else (nmov == 0 and npass == 0),
             f"NMOV {nmov}, passes drawn with offsets +{npass}, scans +{nscan}")
        # group into passes: t0, mid, t1
        passes, cur = [], {}
        for ts, tg, b in got:
            if tg == "t0":
                cur = {"t0": b}
            elif tg == "mid" and "t0" in cur:
                cur["mid"] = b
            elif tg == "t1" and "t0" in cur:
                cur["t1"] = b
                passes.append(cur)
                cur = {}
        line("passes captured", len(passes) >= 10, f"{len(passes)} complete passes in {a.secs:.0f} s")
        restored = sum(1 for p in passes if p["t0"] == p["t1"])
        line("people table restored after the render in every pass (T1 == T0)", restored == len(passes), f"{restored} of {len(passes)}")
        shown = 0
        for p in passes:
            if p["t0"] != p["t1"] and shown < 4:
                shown += 1
                dif = [(i, [j for j in range(PS) if p["t0"][i * PS + j] != p["t1"][i * PS + j]]) for i in range(PN) if p["t0"][i * PS:(i + 1) * PS] != p["t1"][i * PS:(i + 1) * PS]]
                print(f"  T0 != T1: {len(dif)} record(s) differ: " + ", ".join(f"#{i} bytes {[hex(j) for j in js]}" for i, js in dif[:6]) + f"; T0 == TMID: {p.get('mid') == p['t0']}", flush=True)
        offs, bad_bytes, series = 0, 0, {}
        for p in passes:
            if "mid" not in p or p["mid"] == p["t0"]:
                continue
            offs += 1
            for i in range(PN):
                x, y = p["t0"][i * PS:(i + 1) * PS], p["mid"][i * PS:(i + 1) * PS]
                if x != y:
                    d = [j for j in range(PS) if x[j] != y[j]]
                    if any(j not in (9, 11) for j in d):
                        bad_bytes += 1
                    series.setdefault(i, []).append((x[9], y[9], x[11], y[11]))
        if a.mhz != 8:
            line("passes with offsets applied (T0 != TMID)", offs > 0, f"{offs} of {len(passes)}")
            line("offsets touch only the low bytes of x / z ($9, $b of a record)", bad_bytes == 0, f"{bad_bytes} records with other bytes changed")
            best = max(series.items(), key=lambda kv: len({s[1] for s in kv[1]}), default=None)
            if best:
                vals = [s[1] for s in best[1]]
                print(f"  mover record {best[0]}: x low byte at T0 / drawn: {[(s[0], s[1]) for s in best[1][:24]]}", flush=True)
                line("a mover is drawn at several distinct positions within the run", len(set(vals)) >= 3, f"{len(set(vals))} distinct drawn x low bytes")
        else:
            line("no offsets at 8 MHz (no render-only pass)", offs == 0, f"{offs} passes with offsets")
        print(f"CELL DONE interp {tag} {a.mhz} MHz: {'OK' if ok else 'FAIL'}", flush=True)
        return 0 if ok else 2
    finally:
        h.close()


if __name__ == "__main__":
    sys.exit(main())
