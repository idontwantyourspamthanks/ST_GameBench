#!/usr/bin/env python3
"""dumps.py <snap> <outdir> <flip1,flip2,..> [mem_kb] [live-prefix] : RAM dump $0-$B3000 + both screens at the given flips after a fixed VBL."""
import sys, time, json
from pathlib import Path
sys.path.insert(0, '/home/ryan/Code/AtariST/midwinter2/tools')
from mw2harness import Hatari
FLIP = 0x26E98
snap, out = sys.argv[1], Path(sys.argv[2]); ks = [int(x) for x in sys.argv[3].split(',')]
mem = int(sys.argv[4]) if len(sys.argv) > 4 else 2048
out.mkdir(parents=True, exist_ok=True)
h = Hatari(snapshot=snap, memsize_kb=mem)
try:
    # state is restored at the first debugger command; take 'now' as origin
    v = h.vbl(); at = (v // 100 + 4) * 100
    cmds = []
    for k in ks:
        cf = h.R / f"cap{k}.txt"
        cf.write_text(f"savebin {out}/ram_{k}.bin 0 $b3000\n")
        cnt = f" :{k}" if k > 1 else ""
        cmds.append(f"b pc = ${FLIP:x}{cnt} :trace :once :file {cf}")
    app = h.R / "apply.txt"; app.write_text("\n".join(cmds) + "\n")
    h.cmd(f"hatari-debug b VBL > {at} && pc = ${FLIP:x} :trace :once :file {app}")
    t = time.time()
    while not (out / f"ram_{ks[-1]}.bin").exists() or (out / f"ram_{ks[-1]}.bin").stat().st_size < 0xb3000:
        if time.time() - t > 900: raise TimeoutError
        time.sleep(0.5)
    time.sleep(1)
finally:
    h.close()
