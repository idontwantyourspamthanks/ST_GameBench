#!/usr/bin/env python3
import os, sys, time
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "campgate"))
from cg import *
tag = "menu7"
logopen(tag)
r = Run("hd", "ste", 2048, tag, build=os.environ.get("ED_BUILD", "/tmp/msred6/hd"), camp_hd=CAMP/"c3.trk", sound=True)
try:
    ok = r.boot_title(); log("title", ok, "vbl", r.vbl())
    r.key(0x44); time.sleep(3)
    log("M_SEL", r.w(0x100406), "M_CNT", r.w(0x100400))
    r.shot("m0")
    r.key(0x50); time.sleep(1.5)
    log("after DOWN: M_SEL", r.w(0x100406))
    r.key(0x1c); time.sleep(3)
    log("after RETURN: loaded", r.b(0xb8e01), "count", r.w(0xb8e02), "M_SEL", r.w(0x100406), "M_CNT", r.w(0x100400), "$100e", r.w(0x100e))
    r.shot("m1")
    if r.b(0xb8e01):
        r.key(0x50); time.sleep(1.0); log("playlist M_SEL", r.w(0x100406), "M_CNT", r.w(0x100400)); r.shot("m2")
    log(f"Bus/Address error lines: {r.errlines()}")
except Exception:
    import traceback; log("EXC", traceback.format_exc())
finally:
    r.close()
