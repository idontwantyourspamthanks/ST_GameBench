"""traceN.py snap out K mem [debugger cmds...]: cpu_disasm trace of K whole loop iterations ($31486..$31486 x K) after 3rd loop top."""
import sys, time
from pathlib import Path
sys.path.insert(0, '/home/ryan/Code/AtariST/midwinter2/tools')
from mw2harness import Hatari
snap, out, K, mem = sys.argv[1], sys.argv[2], int(sys.argv[3]), int(sys.argv[4])
pre = sys.argv[5:]
h = Hatari(snapshot=snap, memsize_kb=mem)
try:
    on = h.R/'on.txt'; off = h.R/'off.txt'
    on.write_text(f"trace cpu_disasm\nb pc = $31486 :{K} :trace :once :file {off}\n")
    off.write_text("trace none\nb all\n")
    h.debug("b all", 0.3)
    for c in pre: h.debug(c, 0.3)
    n0 = h.logpath.stat().st_size
    h.cmd(f"hatari-debug b pc = $31486 :3 :trace :once :file {on}")
    t = time.time()
    while time.time()-t < 600:
        time.sleep(1)
        if 'trace none' in h._logtext()[-3000:] or h.logpath.stat().st_size - n0 > 0 and 'Removed CPU breakpoint' in h._logtext()[-1500:] and 'trace none' in h._logtext()[n0:][-100000:]: break
    time.sleep(1)
    Path(out).write_bytes(h.logpath.read_bytes()[n0:])
finally:
    h.close()
