#!/usr/bin/env python3
import os, sys, time
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "campgate"))
from cg import *
tag = "probe9"; logopen(tag)
r = Run("hd", "ste", 2*1024, tag, build=os.environ.get("ED_BUILD", "/tmp/msred6/hd"), camp_hd=CAMP/"c3.trk", sound=True)
SYMS = {}
for ln in Path('/tmp/msred6/symmap.txt').read_text().splitlines():
    a,n = ln.split(); SYMS[n]=int(a,16)
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
    names = ["draw_view","draw_header","draw_labels","draw_grid","draw_panel","draw_keys","draw_hint","tile_draw","apps","ptext","ptextp","tiles_calc"]
    text = ""
    for n in names:
        r.h.cmd(f"hatari-debug b pc = ${SYMS[n]:x} :trace"); time.sleep(0.15); text += r.h._logtext()[-200:]
    n0 = len(r.h._logtext())
    r.key(0x1c); time.sleep(2.0)
    out = r.h._logtext()[n0:]
    for n in names:
        print(n, out.count(f"pc = ${SYMS[n]:x}"))
    print("errs", len(re.findall("Bus Error|Address Error", out)))
except Exception:
    import traceback; log("EXC", traceback.format_exc())
finally:
    r.close()
