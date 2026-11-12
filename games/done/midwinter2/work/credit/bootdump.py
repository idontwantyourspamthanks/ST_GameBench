"""bootdump.py hd|fl dir out secs : savebin $0-$100000 at the first hit of $312a8 (game entry, boot state)"""
import sys, time, shutil
from pathlib import Path
ROOT = Path('/home/ryan/Code/AtariST/midwinter2')
sys.path.insert(0, str(ROOT / 'tools'))
from mw2harness import Hatari
B = Path.home() / "Emulators/BIOS/AtariST"
TOS162 = B / "TOS v1.62 (1990)(Atari Corp)(STE)(GB)[STE TOS, Rev 2].img"
kind, src, out, secs = sys.argv[1:5]
src = Path(src)
if kind == 'hd':
    h = Hatari(snapshot=None, memsize_kb=1024, machine='ste', tos=TOS162, game_dir=src)
else:
    scratch = Path('/tmp/cr_bd'); shutil.rmtree(scratch, ignore_errors=True); scratch.mkdir()
    shutil.copy(src / 'FFA_boot.st', scratch / 'A.st')
    empty = scratch / 'empty'; empty.mkdir()
    h = Hatari(snapshot=None, memsize_kb=1024, machine='ste', tos=TOS162, game_dir=empty,
               extra=['--disk-a', str(scratch / 'A.st')])
try:
    f = Path(f'/tmp/cr/bd_{kind}.txt')
    f.write_text(f"r\nsavebin {out} $0 $100000\n")
    h.debug(f"b pc = $312a8 :trace :once :file {f}")
    time.sleep(float(secs))
    print(h._logtext()[-600:])
finally:
    h.close()
