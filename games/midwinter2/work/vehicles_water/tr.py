"""One unpatched loop iteration trace (cpu_disasm,cpu_regs) of a vehicle snapshot with held controls.
usage: tr.py snap out yc xc [nth]   (start pc=$315c6 nth hit, stop pc=$315a8)"""
import sys, time
from vw import *
snap, out, yc, xc = sys.argv[1], sys.argv[2], int(sys.argv[3]), int(sys.argv[4])
nth = int(sys.argv[5]) if len(sys.argv) > 5 else 6
h = Hatari(snapshot=str(SNAP / snap), memsize_kb=2048)
try:
    for c in (wb(0x6fba, (yc & 0xffff) << 16, 4), wb(0x6fb6, (xc & 0xffff) << 16, 4)):
        h.debug(c, 0.3)
    on = h.R / 'on.txt'; off = h.R / 'off.txt'
    on.write_text("trace cpu_disasm,cpu_regs\nb pc = $315a8 :trace :once :file %s\n" % off)
    off.write_text("trace none\nb all\n")
    h.debug("b all", 0.3)
    n0 = len(h._logtext())
    cnt = f" :{nth}" if nth > 1 else ""
    h.cmd(f"hatari-debug b pc = $315c6{cnt} :trace :once :file {on}")
    t = time.time()
    while 'trace none' not in h._logtext()[n0:] and time.time() - t < 400:
        time.sleep(0.5)
    time.sleep(1)
    Path(out).write_text(h._logtext()[n0:])
finally:
    h.close()
