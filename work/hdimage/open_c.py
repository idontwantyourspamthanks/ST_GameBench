#!/usr/bin/env python3
"""open_c.py NAME MACHINE TOS MEM MONITOR IMG ICONX ICONY  (ICON = screenshot px of the C: icon; host px = 2x)"""
import sys, time, os
sys.path.insert(0, os.path.dirname(__file__))
from hh import H
name, machine, tos, mem, mon, img, ix, iy = sys.argv[1:9]
h = H(name, machine, tos, int(mem), mon, img)
try:
    time.sleep(float(os.environ.get("BOOT", "30")))
    print(h.shot("desktop"))
    h.move(int(ix) * 2, int(iy) * 2)
    h.dblclick()
    time.sleep(3)
    print(h.shot("cwin"))
finally:
    h.close()
