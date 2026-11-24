#!/usr/bin/env python3
"""Stage 5: cold-boot a built floppy and save Hatari memory snapshots of the scenes the speed / A-B gates use.

    python3 tools/wws5snap.py --disk build/s5_base/floppy.st --machine ste --out /tmp/pmww1s5/snaps [--scenes map_idle,get_men,random]

map_idle  = the 3D map view after the island click (the world counter ticking), 2 s later.
get_men   = overview click on the island, the 3-sword icon, GET MEN (a zoomed view with men moving; same clicks as work/profile/snap_getmen.py).
random    = Retire (lose) -> click -> PLAY RANDOM LAND -> map view (an enemy captain starts beside the player's; the battle: `--scenes ...,battle` after random: captain click, 3 swords, Attack, click the village).
Snapshots are written as <out>/<machine>_<scene>.sav (+ .png).  One Hatari at a time, private HOME (pmww.PMW).
"""
from __future__ import annotations
import argparse
import shutil
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import pmww  # noqa: E402

MACH = {"ste": ("ste", "1.62", 1024), "st": ("st", "1.04", 1024), "megaste": ("megaste", "2.06", 4096)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--disk", required=True)
    ap.add_argument("--machine", default="ste", choices=list(MACH))
    ap.add_argument("--out", default="/tmp/pmww1s5/snaps")
    ap.add_argument("--scenes", default="map_idle,get_men,random")
    ap.add_argument("--workdir")
    a = ap.parse_args()
    machine, tos, mem = MACH[a.machine]
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    wd = Path(a.workdir or f"/tmp/pmww1s5/snap_{a.machine}")
    shutil.rmtree(wd, ignore_errors=True)
    scenes = a.scenes.split(",")
    h = pmww.PMW(disk=Path(a.disk), workdir=str(wd), machine=machine, tos=pmww.TOS[tos], memsize_kb=mem)
    try:
        h.boot_to_map(noprot=True, swap=False)
        time.sleep(2)
        if "map_idle" in scenes:
            h.shot(str(out / f"{a.machine}_map_idle.png"))
            h.savemem(str(out / f"{a.machine}_map_idle.sav"))
            print("saved map_idle", flush=True)
        if "get_men" in scenes:
            h.click_st(36, 62, wait=6.0)
            h.click_st(97, 158, wait=0.8)
            h.click_st(229, 173, wait=6.0)
            h.shot(str(out / f"{a.machine}_get_men.png"))
            h.savemem(str(out / f"{a.machine}_get_men.sav"))
            print("saved get_men", flush=True)
        if "random" in scenes:
            h.retire(win=False)
            time.sleep(6)
            h.click_st(160, 100, wait=4)                 # picture -> option screen
            h.click_st(160, 121, wait=8.0)               # PLAY RANDOM LAND
            t1 = time.time()
            while not (h.peekw(pmww.WINDOW_OPEN) == 0 and h.ticking(1.5)):
                if time.time() - t1 > 150:
                    raise RuntimeError("random land map view not reached")
                time.sleep(2)
            time.sleep(10)
            h.shot(str(out / f"{a.machine}_random.png"))
            h.savemem(str(out / f"{a.machine}_random.sav"))
            print("saved random", flush=True)
        if "battle" in scenes:
            # random land: the player's captain is at minimap (12,112); 3 swords, the Attack icon, then the village next to it (3D view (192,133)): men fight, angels rise (explored in /tmp/pmww1s5b/exp)
            h.click_st(12, 112, wait=5.0)
            h.click_st(97, 158, wait=1.0)
            h.click_st(244, 191, wait=1.5)
            h.click_st(192, 133, wait=3.0)
            time.sleep(9)
            h.shot(str(out / f"{a.machine}_battle.png"))
            h.savemem(str(out / f"{a.machine}_battle.sav"))
            print("saved battle", flush=True)
    finally:
        h.close()


if __name__ == "__main__":
    main()
