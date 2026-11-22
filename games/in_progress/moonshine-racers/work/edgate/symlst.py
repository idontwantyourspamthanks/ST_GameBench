#!/usr/bin/env python3
"""assemble patches/ovl/msedit.s exactly as msrpatch.py does, with a vasm listing (symbols) -> /tmp/msred4/ovl.lst  (addresses for breakpoints in speed.py)"""
import sys, subprocess
from pathlib import Path
G = Path(__file__).resolve().parents[2]; sys.path.insert(0, str(G / "tools"))
import msrpatch as P
common = "".join(f"{k}\tequ\t${v:x}\n" for k, v in P.CP_EQUS.items()) + "FLOPPY\tequ\t0\n"
src = f"IB\tequ\t${P.IB:x}\nTABLE\tequ\t${P.TABLE:x}\n{common}\n\torg\t${P.CP_EQUS['EDBASE']:x}\n" + P.OVL_SRC.read_text().replace(P.VERSION_TAG, P.release_version()) + "\n"
Path("/tmp/msred4/ovl_full.s").write_text(src)
r = subprocess.run([P.VASM, "-Fbin", "-m68000", "-quiet", "-L", "/tmp/msred4/ovl.lst", "-o", "/tmp/msred4/ovl.bin", "/tmp/msred4/ovl_full.s"], capture_output=True, text=True)
print(r.returncode, r.stderr[:300])
