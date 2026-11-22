#!/usr/bin/env python3
"""editor PLAY gate: HD build, campaign file, F10 -> TRACK EDITOR -> track N -> PLAY THIS TRACK; the state and a screenshot every 2 s until a race stands.
   env3.sh python3 play2.py --camp FILE --track N [--build DIR] [--tag T]"""
import argparse
from ed2lib import *
ap = argparse.ArgumentParser(); ap.add_argument("--camp"); ap.add_argument("--track", type=int, default=1); ap.add_argument("--tag", default="play2"); ap.add_argument("--build", default=os.environ["ED_BUILD"])
ap.add_argument("--machine", default="ste")
a = ap.parse_args()
e = Ed(a.tag, a.machine, 2048, a.build, Path(a.camp)); r = e.r
try:
    e.boot_editor(True)
    time.sleep(3.0); r.shot("1_toplist"); log("top list: M_SEL", r.w(0x100406))
    e.key(0x50, a.track - 1, 0.5); log("M_SEL after downs", r.w(0x100406)); e.send(0x1c); time.sleep(1.5); log("srcix", e.vu("srcix")); e.key(0x50, 1, 0.5); r.shot("2_trackmenu"); log("M_SEL track menu", r.w(0x100406)); e.send(0x1c)
    for i in range(60):
        time.sleep(0.5)
        log(f"+{(i + 1) / 2}s vplay {e.vu('play')} V_START {r.w(0xb8e06)} CPV+4 {r.w(0xb8e04)} $102c {r.w(0x102c):#x} state {e.vu('state')}")
        if i % 4 == 3: r.shot(f"s{i + 1:02d}")
        if r.race_up(): r.st("race up"); r.shot("race_up"); break
finally:
    e.close()
