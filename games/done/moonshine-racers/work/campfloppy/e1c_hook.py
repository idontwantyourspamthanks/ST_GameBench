"""E1c: what the floppy hook (trampoline $b2708) sees."""
import sys, time
from cf import *
machine, mem = sys.argv[1], int(sys.argv[2])
h = mk(BUILD / "disk_a.st", machine=machine, mem=mem, fast=True)
try:
    cm = h.scratch / "c.txt"; cm.write_text("r\nm $42e 4\nm $424 1\nm $ff8001 1\nm $436 4\nm $432 8\nm $5a0 4\nm $42a 4\nm $2dc 4\n")
    n0 = len(h._logtext())
    h.cmd(f"hatari-debug b pc = $b2708 :trace :once :file {cm}")
    ok = wait_log(h, r"Changed back to", n0, 240)
    time.sleep(1)
    txt = h._logtext()[n0:]
    print("hit" if ok else "NOT HIT", "VBL", h.vbl())
    for l in txt.splitlines():
        if re.match(r"^(\s+D\d|\s+A\d|SR=|[0-9A-F]{8}: |0000[0-9a-f]{4} )", l): print(l)
finally:
    close(h)
