#!/usr/bin/env python3
"""Baseline measurements per scenario snapshot and CPU clock: fps, profile (per-address counts+cycles), loop-stage cycles.
    python3 pm_measure.py map_idle 8 16     -> work/prof/<scn>_<clk>mhz.txt, work/prof/<scn>_<clk>mhz_stages.json, work/dumps/<scn>.bin
"""
import json, sys, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import pm
from pm import PM, LOOP_SITES

scn, clocks = sys.argv[1], [int(c) for c in sys.argv[2:]] or [8, 16]
G = pm.GAME
for clk in clocks:
    h = PM(snapshot=str(pm.SNAP / f"{scn}.sav"), cpuclock=clk if clk != 8 else None)
    try:
        time.sleep(1.5)
        if clk == 8 and not (G / "work/dumps" / f"{scn}.bin").exists():
            (G / "work/dumps").mkdir(parents=True, exist_ok=True)
            (G / "work/dumps" / f"{scn}.bin").write_bytes(h.ram())
        out = {"scenario": scn, "clock": clk}
        out["fps"] = h.fps(400)
        pf = G / "work/prof" / f"{scn}_{clk}mhz.txt"
        pf.parent.mkdir(parents=True, exist_ok=True)
        out["profile_frames"] = h.profile_save(150, str(pf))
        r = h.cyc_trace(list(LOOP_SITES), vbls=120)
        out["trace"] = r
        (G / "work/prof" / f"{scn}_{clk}mhz_stages.json").write_text(json.dumps(out))
        print(scn, clk, out["fps"], "profile VBL handler runs:", out["profile_frames"], "trace hits:", len(r), flush=True)
    finally:
        h.close()
