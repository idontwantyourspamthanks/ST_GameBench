#!/usr/bin/env python3
import os, sys, time
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "campgate"))
from cg import *
ap_mem = int(sys.argv[1]) if len(sys.argv) > 1 else 2048
tag = f"menu6_{ap_mem//1024}m"
logopen(tag)
r = Run("hd", "ste", ap_mem, tag, build=os.environ.get("ED_BUILD", "/tmp/msred6/hd"), camp_hd=CAMP/"c3.trk", sound=True)
try:
    ok = r.boot_title(); log("title", ok, "vbl", r.vbl(), "$1021", r.b(0x1021), "$100e", r.w(0x100e), "$23c0", hex(r.l(0x23c0)))
    r.shot("0_before")
    r.key(0x44); time.sleep(3)
    log("M_CNT", r.w(0x100400), "M_SEL", r.w(0x100406), "$60ff", r.b(0x60ff), "$1021", r.b(0x1021), "$100e", r.w(0x100e))
    r.shot("1_after_f10")
    r.key(0x1c); time.sleep(2)
    log("after RETURN: M_CNT", r.w(0x100400), "M_SEL", r.w(0x100406), "loaded", r.b(0xb8e01), "$100e", r.w(0x100e))
    r.shot("2_after_return")
    log(f"Bus/Address error lines: {r.errlines()}")
except Exception:
    import traceback; log("EXC", traceback.format_exc())
finally:
    r.close()
log("RESULT", "PASS" if not FAILS else FAILS)
