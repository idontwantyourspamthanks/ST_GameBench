"""Falcon (TOS 4.04, 4 MB) boot from the floppy build (default + jag): no navigation (the Falcon screen has no ST border, the reference images do not match).
Waits for the payload marker and the probe result, swaps A: to FFB after 80 s, then forces J mode and holds pad keys: PADJ / S must follow."""
import sys, shutil, time
from pathlib import Path
sys.path.insert(0, '/home/ryan/Code/AtariST/midwinter2/work/jagpad')
from jt import *
from stharness import MACHINE_TOS
diskdir = G / sys.argv[1]
scratch = Path('/tmp/fl/run_falcon'); shutil.rmtree(scratch, ignore_errors=True); scratch.mkdir(parents=True)
for src, dst in (('FFA_boot.st', 'A.st'), ('FFB_graphics.st', 'B.st')):
    shutil.copy(diskdir / src, scratch / dst)
shutil.copy(G / 'work/disk_overlay/FILES/FFD', scratch / 'D.st')
empty = scratch / 'empty'; empty.mkdir()
h = Hatari(snapshot=None, memsize_kb=4096, machine='falcon', tos=MACHINE_TOS['falcon'], game_dir=empty,
           extra=PADX + ['--disk-a', str(scratch / 'A.st'), '--disk-b', str(scratch / 'D.st')])
def st():
    try:
        d = memb(h, 0xb9ea0, 32); return d[0], memb(h, 0xb2ff8, 4), w(h, 0x700a), w(h, 0xeb76)
    except Exception as e:
        return None
try:
    t0 = time.time(); swapped = False
    while time.time() - t0 < 420:
        time.sleep(8)
        v = st(); print('%4.0fs' % (time.time() - t0), v, flush=True)
        if not swapped and time.time() - t0 > 80:
            h.cmd(f"hatari-option --disk-a {scratch / 'B.st'}"); swapped = True; print('disk A: -> FFB', flush=True)
        if swapped and v and v[0] != 0 and time.time() - t0 > 130: break
    h.shot(str(G / 'work/jagpad/falcon_fl_boot.png'))
    print('sites', [memb(h, a, 6).hex() for a in (0x262f6, 0x26b66, 0x26bea)], 'p5', memb(h, 0xb433a, 4).hex())
    jmode(h); time.sleep(1)
    for k in ['Left', 'Up', 'x', 'z', 'o', '1']:
        hold(h, k, 1.0); d = memb(h, 0xb9ea0, 32); pj = memb(h, 0xb9ee1, 2)
        print(f'hold {k}: J_ST={d[0]} PADJ={pj[0]:02x} BTN={pj[1]:02x} S={d[20:24].hex()} keys={keydown_list(h)}', flush=True)
        rel(h, k, 0.5)
    print('bus-error log lines', bus_errors(h)[:4])
finally:
    h.close()
