"""E1: what does the floppy build see at hook time: $42e, $424 memconf shadow, $ff8001 MMU config, $420/$43a validity longs, over boot time."""
import sys, time
from cf import *
machine, mem, tos = sys.argv[1], int(sys.argv[2]), (sys.argv[3] if len(sys.argv) > 3 else None)
h = mk(BUILD / "disk_a.st", machine=machine, mem=mem, tos=tos, fast=True)
try:
    last = None
    t0 = time.time()
    while time.time() - t0 < 75:
        time.sleep(2)
        v = h.vbl()
        s = {
          "$42e": rd(h, 0x42e, 4).hex(), "$424": rd(h, 0x424, 1).hex(), "$ff8001": rd(h, 0xff8001, 1).hex(),
          "$420": rd(h, 0x420, 4).hex(), "$436": rd(h, 0x436, 4).hex(), "$b2700": rd(h, 0xb2700, 4).hex(),
          "$5a0": rd(h, 0x5a0, 4).hex(), "$ff8e21": rd(h, 0xff8e21, 1).hex()}
        print(f"vbl {v:5d} " + " ".join(f"{k}={x}" for k, x in s.items()), flush=True)
finally:
    close(h)
