#!/usr/bin/env python3
"""Is the 768-byte tail after each screen buffer ($67d00-$67fff, $77d00-$77fff; the edge walker / span fill write row 200
there) read by anything?  Run the same snapshot twice (both with the p4 set live-applied), poison those bytes in the second run
at the apply flip, then compare the visible screens and the game RAM after K flips.
    python3 work/p7_ck/poison.py <snapshot> <K>"""
import sys, time, hashlib, random
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent)); sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'tools'))
from ck import *
from concurrent.futures import ThreadPoolExecutor
def run(snap, poison, K, out, at):
    h = Hatari(snapshot=snap)
    try:
        od = Path(out); od.mkdir(parents=True, exist_ok=True)
        cmds = live_cmds('/tmp/ck/p4')
        if poison:
            random.seed(5); pb = bytes(random.randrange(256) for _ in range(0x300))
            (od / 'poison.bin').write_bytes(pb)
            cmds += [f"loadbin {od}/poison.bin $67d00", f"loadbin {od}/poison.bin $77d00"]
        cf = h.R / 'cap.txt'
        cf.write_text(f"savebin {od}/b60.bin $60000 $7d00\nsavebin {od}/b70.bin $70000 $7d00\n"
                      f"savebin {od}/ram_lo.bin $400 $5fc00\nsavebin {od}/ram_hi.bin $78000 $3a000\nsavebin {od}/done.bin $67a6 4\n")
        cmds.append(f"b pc = ${FLIP:x} :{K} :trace :once :file {cf}")
        app = h.R / 'apply.txt'; app.write_text("\n".join(cmds) + "\n")
        h.cmd(f"hatari-debug b VBL > {at} && pc = ${FLIP:x} :trace :once :file {app}")
        t = time.time()
        while not (od / 'done.bin').exists():
            if time.time() - t > 1200: raise TimeoutError
            time.sleep(0.5)
        time.sleep(1)
    finally:
        h.close()
snap, K = sys.argv[1], int(sys.argv[2])
h = Hatari(snapshot=snap)
try: at = at_vbl(h)
finally: h.close()
tag = Path(snap).stem
with ThreadPoolExecutor(2) as ex:
    fa = ex.submit(run, snap, False, K, f'/tmp/ck/poison/{tag}/A', at)
    fb = ex.submit(run, snap, True, K, f'/tmp/ck/poison/{tag}/B', at)
    fa.result(); fb.result()
for n in ('b60', 'b70', 'ram_lo', 'ram_hi'):
    a = (Path(f'/tmp/ck/poison/{tag}/A') / f'{n}.bin').read_bytes(); b = (Path(f'/tmp/ck/poison/{tag}/B') / f'{n}.bin').read_bytes()
    print(tag, n, len(a), 'IDENTICAL' if a == b else f'DIFF {sum(1 for i in range(len(a)) if a[i]!=b[i])} bytes')
