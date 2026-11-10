"""bp2.py fl dir tag secs : log every change of $ff8201/$ff8203 (PC + new base) and the first $28b9e hit"""
import sys, time, shutil
from pathlib import Path
ROOT = Path('/home/ryan/Code/AtariST/midwinter2')
sys.path.insert(0, str(ROOT / 'tools'))
from mw2harness import Hatari
B = Path.home() / "Emulators/BIOS/AtariST"
TOS162 = B / "TOS v1.62 (1990)(Atari Corp)(STE)(GB)[STE TOS, Rev 2].img"
kind, src, tag, secs = sys.argv[1:5]
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
    f = Path(f'/tmp/cr/{tag}_w.txt')
    f.write_text("r\nm $ff8200 4\n")
    h.debug(f"b ($ff8201).b ! ($ff8201).b :trace :file {f}")
    f2 = Path(f'/tmp/cr/{tag}_x.txt')
    f2.write_text("r\nm $ff8200 4\n")
    h.debug(f"b ($ff8203).b ! ($ff8203).b :trace :file {f2}")
    time.sleep(float(secs))
    Path(f'/tmp/cr/{tag}_log.txt').write_text(h._logtext())
finally:
    h.close()
