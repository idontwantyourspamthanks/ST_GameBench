"""E1b: $ff8001 / $42e at hook time on every machine x RAM size (floppy build, title screen reached)."""
import sys, time
from cf import *
for machine, tos in (("st", None), ("ste", None), ("megaste", None)):
    for mem in (1024, 2048, 4096):
        h = mk(BUILD / "disk_a.st", machine=machine, mem=mem, tos=tos, fast=True)
        try:
            while h.vbl() < 320: time.sleep(1.5)
            print(f"{machine:8s} {mem:5d} KB  vbl {h.vbl()}  $ff8001={rd(h,0xff8001,1).hex()} $42e={rd(h,0x42e,4).hex()} $424={rd(h,0x424,1).hex()} $1021={rd(h,0x1021,1).hex()}", flush=True)
        finally:
            close(h)
