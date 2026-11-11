import sys, time; from pathlib import Path; sys.path.insert(0,str(__import__('pathlib').Path(__file__).resolve().parents[2]/'tools'))
from mw2harness import Hatari
snap, tag, mem, n, dx = sys.argv[1], sys.argv[2], int(sys.argv[3]), int(sys.argv[4]), int(sys.argv[5])
dy = int(sys.argv[6]) if len(sys.argv)>6 else 0
d = Path('/tmp/cc/s'); d.mkdir(exist_ok=True)
h = Hatari(snapshot=snap, memsize_kb=mem)
try:
    for i in range(n):
        f = d/f'{tag}_{i}.bin'
        if f.exists(): f.unlink()
        (h.R/f'c{i}.txt').write_text(f"savebin {f} $0 $90000\n")
        h.cmd(f"hatari-debug b pc = $1ebda :trace :once :file {h.R}/c{i}.txt")
        if dx or dy: h.rel(dx, dy, steps=3)
        t0=time.time()
        while not (f.exists() and f.stat().st_size==0x90000):
            if time.time()-t0>200: raise TimeoutError
            time.sleep(0.2)
        time.sleep(0.8)
    print('done',tag,n)
finally:
    h.close()
    import shutil; shutil.rmtree(h.R, ignore_errors=True)
