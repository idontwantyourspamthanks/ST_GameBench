"""bp3.py hd|fl dir tag secs bp...: dump $50000-$7FFFF + video regs at each breakpoint (first hit)"""
import sys, time, shutil
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
        f.write_text(f"r\nm $ff8240 32\nm $ff8200 16\nm $770e 16\nsavebin /tmp/cr/{tag}_{bp}.scr $50000 $30000\n")
        h.debug(f"b pc = ${bp} :trace :once :file {f}")
    time.sleep(float(secs))
    Path(f'/tmp/cr/{tag}_log.txt').write_text(h._logtext())
finally:
    h.close()
