#!/usr/bin/env python3
"""prof_rebuild.py: Hatari profile (per-address cycles + exec counts) over exactly one rebuild sub_031dee ($31df6..$31f12), plus extra phase stops."""
import sys, time
from pathlib import Path
GAME = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(GAME / "tools"))
from mw2harness import Hatari
OUT = Path("/tmp/terr"); OUT.mkdir(exist_ok=True)
h = Hatari(snapshot=str(GAME / "work/snapshots/1mb_ingame_walking.sav"), memsize_kb=1024)
try:
    h.set_cpuclock(16)
    h.debug("b all", 0.3)
    (OUT/"p_entry.txt").write_text("e CycleCounter\nprofile on\n")
    (OUT/"p_exit.txt").write_text("e CycleCounter\nprofile cycles 3000\nprofile counts 3000\nprofile save /tmp/terr/prof_full.txt\n")
    stops = []   # extra phase stops reset the Hatari profile: entry/exit only
    for pc, tag in stops:
        f = OUT / f"s_{tag}.txt"; f.write_text("e CycleCounter\n")
        h.cmd(f"hatari-debug b pc = ${pc:x} :trace :once :file {f}"); time.sleep(0.25)
    h.cmd("hatari-debug b pc = $31df6 :trace :once :file /tmp/terr/p_entry.txt"); time.sleep(0.25)
    h.cmd("hatari-debug b pc = $31f12 :trace :once :file /tmp/terr/p_exit.txt"); time.sleep(0.25)
    h.debug("w $66e6 $00 $00 $13 $50", 0.5)
    t = time.time()
    while time.time() - t < 3000:
        if h._logtext().count("Removed CPU breakpoint") >= len(stops) + 2: break
        time.sleep(2)
    (OUT / "plog.txt").write_text(h._logtext())
    print("done", time.time() - t)
finally:
    h.close()
