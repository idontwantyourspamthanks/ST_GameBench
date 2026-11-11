#!/usr/bin/env python3
"""T5: count changes of the palette register $ff8242 and GEMDOS reads during one screen transition
(Capt Stark's character screen -> click the map icon: the map is loaded from disk, 2 chunk reads),
original game vs a build.

    python3 tools/mw1pal.py NAME MACHINE TOS MEM_KB GAME_DIR
"""
import re
import shutil
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from mw1harness import MW1, TOS, REF  # noqa: E402

name, machine, tos, mem, game = sys.argv[1:6]
h = MW1(game_dir=Path(game).resolve(), snapshot=None, machine=machine, tos=TOS[tos], memsize_kb=int(mem),
        extra=["--trace", "gemdos"])
try:
    assert h.boot_to_options(), "options not reached"
    h.goto(415, 385); h.click()
    t = time.time()
    while time.time() - t < 60 and not h.matches(REF / "team_title.png", (320, 50, 510, 90)):
        time.sleep(2)
    print("team screen reached:", h.matches(REF / "team_title.png", (320, 50, 510, 90)))
    time.sleep(3)
    h.goto(176, 170); h.click(); time.sleep(8)             # Capt Stark's character screen (all resident)
    h.shot(f"/tmp/mw1/pal_{name}_before.png")
    h.cmd("hatari-debug b all"); time.sleep(0.5)
    (h.R / "pc.txt").write_text("r\n")
    h.cmd(f"hatari-debug b ($ff8242).w ! ($ff8242).w :trace :file {h.R / 'pc.txt'}"); time.sleep(0.5)
    mark = len(h._logtext())
    for attempt in range(6):                                # map icon; retry while the click is lost
        h.goto(380, 425); h.click(hold=0.6)
        time.sleep(10)
        if "Fread(64, 200000" in h._logtext()[mark:]:
            break
    print("click attempts:", attempt + 1)
    time.sleep(15)
    h.shot(f"/tmp/mw1/pal_{name}_after.png")
    log = h._logtext()[mark:]
    shutil.copy(h.logpath, f"/tmp/mw1/pal_{name}_log.txt")
    n = len(re.findall(r"CPU breakpoint condition\(s\) matched", log))
    reads = re.findall(r"GEMDOS 0x3F Fread\(64, (\d+), 0x([0-9a-fA-F]+)\)", log)
    pcs = re.findall(r"^([0-9a-f]{8}) ", log, re.M)
    from collections import Counter
    print(f"[{name}] $ff8242 changes during the transition: {n}")
    print(f"[{name}] GEMDOS Fread during the transition: {len(reads)} {reads[:12]}")
    print(f"[{name}] change PCs (top):", Counter(pcs).most_common(12))
finally:
    h.close()
