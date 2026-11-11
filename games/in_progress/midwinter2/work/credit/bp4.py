"""bp4.py hd|fl dir tag secs bp...: at first hit of each bp log regs + stack, and screenshot right after"""
import sys, time, shutil, re
from pathlib import Path
ROOT = Path('/home/ryan/Code/AtariST/midwinter2')
sys.path.insert(0, str(ROOT / 'tools'))
from mw2harness import Hatari
B = Path.home() / "Emulators/BIOS/AtariST"
TOS162 = B / "TOS v1.62 (1990)(Atari Corp)(STE)(GB)[STE TOS, Rev 2].img"
kind, src, tag, secs = sys.argv[1:5]
bps = sys.argv[5:]
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
        f.write_text(f"r\nm a7 48\nm $ff8200 4\n")
        h.debug(f"b pc = ${bp} :trace :once :file {f}")
    t0 = time.time(); seen = 0
    while time.time() - t0 < float(secs):
        time.sleep(1.0)
        txt = h._logtext()
        n = len(re.findall(r'^Next PC', txt, re.M))
        if n != seen:
            seen = n
            h.shot(f'/home/ryan/Code/AtariST/midwinter2/work/credit/tl/{tag}_hit{n}.png')
            print('hit', n, 't=%.0f' % (time.time() - t0), flush=True)
    Path(f'/tmp/cr/{tag}_log.txt').write_text(h._logtext())
finally:
    h.close()
