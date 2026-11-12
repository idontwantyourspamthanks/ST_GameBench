import sys, time, re
from pathlib import Path
sys.path.insert(0, '/home/ryan/Code/AtariST/midwinter2/tools')
from mw2harness import Hatari
snap = sys.argv[1]; out = sys.argv[2]; nth = int(sys.argv[3]); start = sys.argv[4]; stop = sys.argv[5]
mem = int(sys.argv[6]) if len(sys.argv) > 6 else 1024
extra = sys.argv[7:]  # extra debugger commands executed at start (e.g. live patch)
h = Hatari(snapshot=snap, memsize_kb=mem)
try:
    on = h.R/'on.txt'; off = h.R/'off.txt'
    on.write_text(f"trace cpu_disasm,cpu_regs\nb pc = ${stop} :trace :once :file {off}\n")
    off.write_text("trace none\nb all\n")
    h.debug("b all", 0.3)
    n0 = len(h._logtext())
    cnt = f" :{nth}" if nth > 1 else ""
    h.cmd(f"hatari-debug b pc = ${start}{cnt} :trace :once :file {on}")
    t = time.time()
    while 'trace none' not in h._logtext()[n0:] and time.time()-t < 300:
        time.sleep(0.5)
    time.sleep(1)
    Path(out).write_text(h._logtext()[n0:])
finally:
    h.close()
