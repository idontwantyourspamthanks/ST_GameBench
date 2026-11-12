"""bp1.py hd|fl dir tag secs : cold boot, breakpoints at $3104 and $28b9e that dump regs+screen RAM"""
import sys, time, shutil
from pathlib import Path
ROOT = Path('/home/ryan/Code/AtariST/midwinter2')
sys.path.insert(0, str(ROOT / 'tools'))
from mw2harness import Hatari
B = Path.home() / "Emulators/BIOS/AtariST"
TOS162 = B / "TOS v1.62 (1990)(Atari Corp)(STE)(GB)[STE TOS, Rev 2].img"
kind, src, tag, secs = sys.argv[1:5]
bps = sys.argv[5:] or ['3104', '28b9e']
src = Path(src)
if kind == 'hd':
    h = Hatari(snapshot=None, memsize_kb=1024, machine='ste', tos=TOS162, game_dir=src)
else:
    scratch = Path(f'/tmp/cr_{tag}'); shutil.rmtree(scratch, ignore_errors=True); scratch.mkdir()
    shutil.copy(src / 'FFA_boot.st', scratch / 'A.st')
    empty = scratch / 'empty'; empty.mkdir()
    h = Hatari(snapshot=None, memsize_kb=1024, machine='ste', tos=TOS162, game_dir=empty,
               extra=['--disk-a', str(scratch / 'A.st')])
try:
    for bp in bps:
        f = Path(f'/tmp/cr/{tag}_{bp}.txt')
        f.write_text(f"r\nm $ff8240 32\nm $ff8200 16\nsavebin /tmp/cr/{tag}_{bp}.scr $60000 $20000\n")
        h.debug(f"b pc = ${bp} :trace :once :file {f}")
    t0 = time.time()
    n = 0
    while time.time() - t0 < float(secs):
        time.sleep(2.5)
        h.shot(f'/home/ryan/Code/AtariST/midwinter2/work/credit/tl/{tag}_{int(time.time()-t0):03d}.png')
    print(h._logtext()[-3000:])
finally:
    h.close()
