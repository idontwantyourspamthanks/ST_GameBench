"""Timeline: cold boot and screenshot every STEP s.  tl.py hd|fl GAMEDIR_OR_FLOPPYDIR tag secs [machine tos mem]"""
import sys, time, shutil
from pathlib import Path
ROOT = Path('/home/ryan/Code/AtariST/midwinter2')
sys.path.insert(0, str(ROOT / 'tools'))
from mw2harness import Hatari
B = Path.home() / "Emulators/BIOS/AtariST"
TOS = {'162': B / "TOS v1.62 (1990)(Atari Corp)(STE)(GB)[STE TOS, Rev 2].img",
       '104': B / "TOS v1.04 (1989)(Atari Corp)(Mega ST)(GB)[Rainbow TOS].img"}
kind, src, tag, secs = sys.argv[1:5]
machine = sys.argv[5] if len(sys.argv) > 5 else 'ste'
tos = sys.argv[6] if len(sys.argv) > 6 else '162'
mem = int(sys.argv[7]) if len(sys.argv) > 7 else 1024
out = ROOT / 'work/credit/tl'
src = Path(src)
if kind == 'hd':
    h = Hatari(snapshot=None, memsize_kb=mem, machine=machine, tos=TOS[tos], game_dir=src)
else:
    scratch = Path(f'/tmp/cr_{tag}'); shutil.rmtree(scratch, ignore_errors=True); scratch.mkdir()
    shutil.copy(src / 'FFA_boot.st', scratch / 'A.st')
    empty = scratch / 'empty'; empty.mkdir()
    h = Hatari(snapshot=None, memsize_kb=mem, machine=machine, tos=TOS[tos], game_dir=empty,
               extra=['--disk-a', str(scratch / 'A.st')])
try:
    t0 = time.time()
    while time.time() - t0 < float(secs):
        t = time.time() - t0
        try:
            h.shot(str(out / f'{tag}_{int(t):03d}.png'))
        except Exception as e:
            print('shot fail', e)
        time.sleep(2.5)
finally:
    h.close()
