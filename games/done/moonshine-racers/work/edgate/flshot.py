#!/usr/bin/env python3
"""Floppy title, deterministic screen capture: no key at all; a one-shot breakpoint `pc = $74c8 :N` (the end of the N-th message of the title's face / text loop, armed at power-on: no input, no wall-clock dependence) saves both game
screens ($70000, $78000: 32000 B each) to files.  Two builds booted the same way must give byte-identical screens when the hint is not applied (1 MB) and differ in text row 23 when it is (2 MB).
   work/edgate/env5.sh python3 work/edgate/flshot.py --tag T --mem 1024|2048 --disk DISK_A.st [--vbl 6300]"""
import argparse, sys, hashlib
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "campgate"))
from cg import *
ap = argparse.ArgumentParser(); ap.add_argument("--tag", default="flshot"); ap.add_argument("--mem", type=int, default=1024); ap.add_argument("--machine", default="ste")
ap.add_argument("--disk", required=True); ap.add_argument("--nth", type=int, default=3); a = ap.parse_args()
logopen(a.tag)
r = Run("fl", a.machine, a.mem, a.tag, disk_a=a.disk, sound=True); h = r.h
out = Path(os.environ.get("ED_TMP", "/tmp/msred5")) / f"fls_{a.tag}"; out.mkdir(parents=True, exist_ok=True)
for f in out.glob("*.bin"): f.unlink()
try:
    cap = h.R / "cap.txt"; cap.write_text(f"savebin {out}/s70.bin $70000 $8000\nsavebin {out}/s78.bin $78000 $8000\nm $1004 8\n")
    h.cmd(f"hatari-debug b pc = $74c8 :{a.nth} :trace :once :file {cap}"); time.sleep(0.5)
    r.ff(True); t0 = time.time()
    while time.time() - t0 < 900 and not ((out / "s78.bin").exists() and (out / "s78.bin").stat().st_size == 0x8000): time.sleep(0.5)
    r.ff(False); time.sleep(1.0)
    ok = (out / "s78.bin").exists()
    check("capture done", ok)
    if ok:
        for n in ("s70", "s78"): log(n, hashlib.md5((out / f"{n}.bin").read_bytes()).hexdigest())
        log("$742e/$7446 bytes:", r.mem(0x7446, 6).hex(), "IB+4", hex(r.mem(0xb2704, 1)[0]), "vbl", h.vbl())
        r.shot("capture")
    log(f"Bus/Address error lines: {r.errlines()}")
except Exception:
    import traceback; log("EXC", traceback.format_exc())
finally:
    r.close()
log(f"RESULT {a.tag}: {'ALL CHECKS PASS' if not FAILS else 'FAILED: ' + ', '.join(FAILS)}")
