#!/usr/bin/env python3
import os, sys, time
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "campgate"))
from cg import *
tag = "probe10"; logopen(tag)
r = Run("hd", "ste", 2*1024, tag, build=os.environ.get("ED_BUILD", "/tmp/msred6/hd"), camp_hd=CAMP/"c3.trk", sound=True)
try:
    r.boot_title(); r.menu_open(); time.sleep(1)
    def goto_item(n):
        for _ in range(12):
            s = r.w(0x100406)
            if s == n: return True
            r.h.cmd(f"hatari-event keypress {'0x50' if s < n else '0x48'}"); time.sleep(0.6)
        return False
    goto_item(1); r.key(0x1c); time.sleep(4)
    goto_item(3); r.key(0x1c); time.sleep(1.5); goto_item(4); r.key(0x1c); time.sleep(4)
    for _ in range(3): r.key(0x50); time.sleep(0.5)
    r.key(0x1c); time.sleep(1.0)
    for _ in range(3): r.key(0x50); time.sleep(0.4)
    r.key(0x1c); time.sleep(2.0)
    b = r.mem(0x140000+128, 2); log("stage", W(b))
    log("last a0", hex(r.l(0x140000+114)), "a0 after", hex(r.l(0x140000+142)))
    log("errors", r.errlines())
finally:
    r.close()
