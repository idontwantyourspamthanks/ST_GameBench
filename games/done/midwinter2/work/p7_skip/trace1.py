import sys, time, re
from pathlib import Path
sys.path.insert(0, '/home/ryan/Code/AtariST/midwinter2/tools')
from mw2harness import Hatari
snap = sys.argv[1]; out = sys.argv[2]; nth = int(sys.argv[3]) if len(sys.argv) > 3 else 1
h = Hatari(snapshot=snap)
try:
    on = h.R/'on.txt'; off = h.R/'off.txt'
    on.write_text(f"trace cpu_disasm,cpu_regs\nb pc = $315a8 :trace :once :file {off}\n")
    off.write_text("trace none\nb all\n")
    h.debug("b all", 0.3)
    n0 = len(h._logtext())
    cnt = f" :{nth}" if nth > 1 else ""
    h.cmd(f"hatari-debug b pc = $315a4{cnt} :trace :once :file {on}")
    time.sleep(0.3)
    t = time.time()
    while 'trace none' not in h._logtext()[n0:] and time.time()-t < 120:
        time.sleep(0.5)
    time.sleep(1)
    Path(out).write_text(h._logtext()[n0:])
finally:
    h.close()
