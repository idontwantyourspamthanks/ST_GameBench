"""floppy cold boot; at VBL>N: regs, video regs, 1MB RAM dump. python3 snapfl.py DISK_A N TAG"""
import sys, time, os
sys.path.insert(0, 'tools')
from msrfloppy import mk
a, N, tag = sys.argv[1], int(sys.argv[2]), sys.argv[3]
h = mk(a)
base = os.path.abspath('work/credit')
try:
    f = h.R / "cap.txt"
    f.write_text(f"r\nm $ff8200 16\nm $ff8240 32\nsavebin {base}/{tag}.bin 0 $100000\n")
    start = len(h._logtext())
    h.cmd(f"hatari-debug b VBL > {N} :trace :once :file {f}")
    t=time.time()
    while not os.path.exists(f"{base}/{tag}.bin"):
        time.sleep(0.5)
        if time.time()-t>200: break
    time.sleep(2)
    open(f"{base}/{tag}.log","w").write(h._logtext()[start:])
    h.shot(f"{base}/{tag}.png")
finally:
    h.close()
