#!/usr/bin/env python3
import os, sys, time
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "campgate"))
from cg import *
tag = "probe8"; logopen(tag)
r = Run("hd", "ste", 2*1024, tag, build=os.environ.get("ED_BUILD", "/tmp/msred6/hd"), camp_hd=CAMP/"c3.trk", sound=True)
try:
    ok = r.boot_title(); log("title", ok)
    r.menu_open(); time.sleep(1)
    def goto_item(n):
        for _ in range(12):
            s = r.w(0x100406)
            if s == n: return True
            r.h.cmd(f"hatari-event keypress {'0x50' if s < n else '0x48'}"); time.sleep(0.6)
        return False
    goto_item(1); r.key(0x1c); time.sleep(4)
    log("loaded", r.b(0xb8e01))
    goto_item(3); r.key(0x1c); time.sleep(1.5); goto_item(4); r.key(0x1c); time.sleep(4)
    log("EDOK", r.b(0xb8e0c))
    # editor track list: COPY OF AN ORIGINAL TRACK
    for _ in range(3): r.key(0x50); time.sleep(0.5)
    r.key(0x1c); time.sleep(1.0)
    for _ in range(3): r.key(0x50); time.sleep(0.4)
    log("arm bp")
    print(r.h.debug("b pc = $130346", 0.5)[-300:])
    r.key(0x1c); time.sleep(2.0)
    out = r.h.debug("r", 0.8)
    print(out[-1500:])
    out2 = r.h.debug("m $a7-32 40", 0.8)
    print(out2[-800:])
    print("state", r.w(0x140060), "via mem")
    log(f"Bus/Address error lines: {r.errlines()}")
except Exception:
    import traceback; log("EXC", traceback.format_exc())
finally:
    r.close()
