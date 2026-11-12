#!/usr/bin/env python3
"""cap_rebuild.py: restore 1mb_ingame_walking (unpatched), poke X near the window edge, and snapshot RAM / CycleCounter at the
phase boundaries of the local-map rebuild sub_031dee. Output: /tmp/terr/*.bin + /tmp/terr/log.txt"""
import sys, time, os
from pathlib import Path
GAME = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(GAME / "tools"))
import mw2tick as T
from mw2harness import Hatari
OUT = Path("/tmp/terr"); OUT.mkdir(exist_ok=True)
h = Hatari(snapshot=str(GAME / "work/snapshots/1mb_ingame_walking.sav"), memsize_kb=1024)
try:
    h.set_cpuclock(16)
    h.debug("b all", 0.3)
    # (pc, tag, extra debugger lines)
    stops = [
        (0x31df6, "entry",  ["savebin /tmp/terr/entry.bin 0 $100000"]),
        (0x24d2a, "L0",     ["savebin /tmp/terr/L0.bin $40040 $9000"]),
        (0x24d30, "L1",     ["savebin /tmp/terr/L1.bin $40040 $9000"]),
        (0x24d36, "L2",     ["savebin /tmp/terr/L2.bin $40040 $9000"]),
        (0x24d3c, "L3",     ["savebin /tmp/terr/L3.bin $40040 $9000"]),
        (0x24d42, "L4",     ["savebin /tmp/terr/L4.bin $40040 $9000"]),
        (0x24d48, "L5",     ["savebin /tmp/terr/L5.bin $40040 $9000"]),
        (0x31ee4, "after24d0e", ["savebin /tmp/terr/grid_raw.bin $40040 $9c40"]),
        (0x31eea, "after274e4", []),
        (0x31ef2, "before5092", ["savebin /tmp/terr/grid_pre.bin $40040 $9c40"]),
        (0x31efe, "after5092", ["savebin /tmp/terr/grid_shaded.bin $40040 $9c40"]),
        (0x31f12, "exit",   ["savebin /tmp/terr/exit.bin 0 $100000"]),
    ]
    for pc, tag, extra in stops:
        f = OUT / f"c_{tag}.txt"
        f.write_text("e VBL\ne CycleCounter\nm $66e6 8\nm $66bc 4\n" + "\n".join(extra) + "\n")
        h.cmd(f"hatari-debug b pc = ${pc:x} :trace :once :file {f}"); time.sleep(0.25)
    # trigger: put X just above the $1388 threshold
    h.debug("w $66e6 $00 $00 $13 $50", 0.5)
    s0 = len(h._logtext())
    T.wait_gone(h, s0, 3000) if False else None
    # wait for the exit stop (last in list) to appear: log text containing 'pc = $31f12' removal
    t = time.time()
    while time.time() - t < 3000:
        txt = h._logtext()
        if txt.count("Removed CPU breakpoint") >= len(stops): break
        time.sleep(2)
    (OUT / "log.txt").write_text(h._logtext())
    print("done", time.time() - t)
finally:
    h.close()
