#!/usr/bin/env python3
"""latency.py CONFIG SNAP MHZ [TRIALS]: input-to-display latency. A heading input (-300 counts on $6fb6) is poked at known VBLs (different
phases of the 5 Hz tick); latency = VBL of the first presented flip whose live heading $6742 differs from the pre-poke heading, minus the poke VBL.
CONFIG: orig (unpatched) | cand (the shipping candidate: defaults + p3cp_head + p3c_sim + p7_skip_render)."""
import sys, re, subprocess, json, statistics
sys.path.insert(0, '/home/ryan/Code/AtariST/gamebench/games/in_progress/midwinter2/work/vehicles_p3b')
from vt import *
cfg, snap, mhz = sys.argv[1], sys.argv[2], int(sys.argv[3]); trials = int(sys.argv[4]) if len(sys.argv) > 4 else 8
if cfg == 'orig': live = None
elif cfg == 'cand': live = build_live(cand_names(), 'lat_cand')
else: raise SystemExit('CONFIG: orig | cand')
h = Hatari(snapshot=str(SNAP/snap), memsize_kb=2048)
try:
    if mhz != 8: h.set_cpuclock(mhz)
    v = h.vbl()
    flipf = h.R/'flip.txt'; flipf.write_text('e VBL\nm $6742 2\nm $66e6 8\n')
    base = v + 200
    t0s = [base + 130*i + 3*i for i in range(trials)]
    if live: at_flip(h, apply_cmds(live), v + 100)
    # trials: poke at t0, zero at t0+60
    start = len(h._logtext())
    h.debug('b all', 0.3)
    for i, t0 in enumerate(t0s):
        f1 = h.R/f'p{i}.txt'; f1.write_text('w $6fb6 $fe $d4 $00 $00\n')
        f2 = h.R/f'z{i}.txt'; f2.write_text('w $6fb6 $00 $00 $00 $00\n')
        h.cmd(f"hatari-debug b VBL > {t0} :trace :once :file {f1}"); time.sleep(0.15)
        h.cmd(f"hatari-debug b VBL > {t0+70} :trace :once :file {f2}"); time.sleep(0.15)
    h.cmd(f"hatari-debug b pc = ${h.FLIP:x} :trace :file {flipf}")
    end = t0s[-1] + 110
    while h.vbl() < end: time.sleep(1.0)
    h.debug('b all', 0.5)
    txt = h._logtext()[start:]
    rows = []
    for m in re.finditer(r'#(\d+) \(dec\)[^\n]*\n> m \$6742 2\n0*6742:\s+([0-9a-f]{2}) ([0-9a-f]{2})', txt, re.I):
        rows.append((int(m.group(1)), int(m.group(2) + m.group(3), 16)))
    res = []; extra = []
    def wrap(d): return ((d + 512) & 1023) - 512
    for t0 in t0s:
        pre = [r for r in rows if r[0] <= t0]
        if not pre: continue
        h0 = pre[-1][1]
        traj = [(r[0] - t0, wrap(r[1] - h0)) for r in rows if t0 < r[0] <= t0 + 60]
        first = next((x for x in traj if abs(x[1]) >= 2), None)
        res.append(first[0] * 20 if first else None)
        fin = [wrap(r[1] - h0) for r in rows if t0 + 55 <= r[0] <= t0 + 65]
        D = fin[-1] if fin else 0
        if first and abs(D) >= 8 and cfg != 'orig':
            t90 = next((x[0] for x in traj if abs(x[1]) >= 0.9 * abs(D)), None)
            over = max(abs(x[1]) for x in traj) / abs(D) - 1
            extra.append((first[0] * 20, abs(first[1]) / abs(D), None if t90 is None else t90 * 20, over, D))
    fl = [r for r in rows if t0s[0] <= r[0] <= t0s[0] + 65]
    ok = [x for x in res if x is not None]
    print(f"RESULT {cfg} {snap} {mhz}MHz first-change latency ms {res}  mean {statistics.mean(ok):.0f} max {max(ok)} min {min(ok)}")
    if extra:
        t90 = [e[2] for e in extra if e[2] is not None]
        print(f"EXTRA {cfg} {snap} {mhz}MHz impulse trials {len(extra)}: first-frame fraction of the tick's turn mean {statistics.mean(e[1] for e in extra):.2f}; time to 90% of the turn mean {statistics.mean(t90):.0f} ms max {max(t90)}; max overshoot beyond the final heading mean {statistics.mean(e[3] for e in extra):.2f} max {max(e[3] for e in extra):.2f}; D {[e[4] for e in extra]}")
finally:
    h.close()
