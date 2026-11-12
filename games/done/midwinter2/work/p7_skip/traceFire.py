import sys, time
from pathlib import Path
sys.path.insert(0, '/home/ryan/Code/AtariST/midwinter2/tools')
from mw2harness import Hatari
snap, out, K, mem = sys.argv[1], sys.argv[2], int(sys.argv[3]), int(sys.argv[4])
h = Hatari(snapshot=snap, memsize_kb=mem)
try:
    on = h.R/'on.txt'; off = h.R/'off.txt'
    on.write_text(f"trace cpu_disasm\nb pc = $31486 :{K} :trace :once :file {off}\n")
    off.write_text("trace none\nb all\n")
    h.debug("b all", 0.3)
    a0 = h.peekw(0x7000) if False else None
    h.cmd("hatari-debug m $7686 16")  # touch
    # press space and hold across several frames
    import threading
    def press():
        h.key('space', hold=1.2)
    th = threading.Thread(target=press); th.start()
    time.sleep(0.3)
    n0 = h.logpath.stat().st_size
    h.cmd(f"hatari-debug b pc = $31486 :2 :trace :once :file {on}")
    t = time.time()
    while time.time()-t < 300:
        time.sleep(1)
        if 'trace none' in h._logtext()[n0:][-100000:]: break
    th.join()
    time.sleep(1)
    Path(out).write_bytes(h.logpath.read_bytes()[n0:])
    print(h.debug('m $3cee 48', 0.5)[-300:])
finally:
    h.close()
