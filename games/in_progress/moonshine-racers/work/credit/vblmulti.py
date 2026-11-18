"""Like vblshots.py but arms ALL breakpoints first (fine VBL spacing). python3 vblmulti.py hd BUILD OUTDIR MACHINE MEM TOS START STOP STEP"""
import sys, time, os
sys.path.insert(0, 'tools')
import msr
from msr import Moonshine, GAME
from stharness import TOS
kind, build, out, machine, mem, tos, a, b, st = sys.argv[1:10]
out = os.path.abspath(out); os.makedirs(out, exist_ok=True)
vbls = list(range(int(a), int(b) + 1, int(st)))
h = Moonshine(machine=machine, memsize_kb=int(mem), game_dir=GAME / build, tos=TOS[tos])
try:
    time.sleep(1)
    for n in vbls:
        f = h.R / f"cap_{n}.txt"
        f.write_text(f"m $ff8200 16\nm $ff8240 32\nsavebin {out}/{n}_70000.bin $70000 $8000\nsavebin {out}/{n}_78000.bin $78000 $8000\n")
        h.cmd(f"hatari-debug b VBL > {n} :trace :once :file {f}"); time.sleep(0.15)
    t = time.time()
    while len([1 for n in vbls if os.path.exists(f"{out}/{n}_78000.bin")]) < len(vbls):
        time.sleep(1)
        if time.time() - t > 300: break
    time.sleep(2)
    log = h._logtext()
    for n in vbls:
        # per-capture register text is in the log; split by marker
        pass
    open(f"{out}/all.log", "w").write(log)
    print("captured", len([1 for n in vbls if os.path.exists(f"{out}/{n}_78000.bin")]), "of", len(vbls))
finally:
    h.close()
