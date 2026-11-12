"""gate.py hd|fl dir tag [machine tos mem] : cold boot a build; at the logo screen dump buffers + palette + marker, screenshot."""
import sys, time, shutil, re
from pathlib import Path
ROOT = Path('/home/ryan/Code/AtariST/midwinter2')
sys.path.insert(0, str(ROOT / 'tools'))
from mw2harness import Hatari
B = Path.home() / "Emulators/BIOS/AtariST"
TOS = {'162': B / "TOS v1.62 (1990)(Atari Corp)(STE)(GB)[STE TOS, Rev 2].img",
       '104': B / "TOS v1.04 (1989)(Atari Corp)(Mega ST)(GB)[Rainbow TOS].img"}
kind, src, tag = sys.argv[1:4]
machine = sys.argv[4] if len(sys.argv) > 4 else 'ste'
tos = sys.argv[5] if len(sys.argv) > 5 else '162'
mem = int(sys.argv[6]) if len(sys.argv) > 6 else 1024
src = Path(src)
if kind == 'hd':
    h = Hatari(snapshot=None, memsize_kb=mem, machine=machine, tos=TOS[tos], game_dir=src)
    bp = '1f644'
else:
    scratch = Path(f'/tmp/cr_{tag}'); shutil.rmtree(scratch, ignore_errors=True); scratch.mkdir()
    shutil.copy(src / 'FFA_boot.st', scratch / 'A.st')
    empty = scratch / 'empty'; empty.mkdir()
    h = Hatari(snapshot=None, memsize_kb=mem, machine=machine, tos=TOS[tos], game_dir=empty,
               extra=['--disk-a', str(scratch / 'A.st')])
    bp = '1f620'
try:
    f = Path(f'/tmp/cr/g_{tag}.txt')
    f.write_text(f"r\nm $ff8240 32\nm $ff8200 16\nm $770e 16\nm $b2ff8 4\nsavebin /tmp/cr/{tag}.scr $50000 $30000\n")
    h.debug(f"b pc = ${bp} :trace :once :file {f}")
    t0 = time.time()
    while 'Next PC' not in h._logtext() and time.time() - t0 < 240:
        time.sleep(1)
    print('hit after %.0f s' % (time.time() - t0), flush=True)
    time.sleep(1.5)
    h.shot(str(ROOT / f'work/credit/{tag}.png'))
    time.sleep(1.0)
    Path(f'/tmp/cr/{tag}_log.txt').write_text(h._logtext())
    print([l for l in h._logtext().splitlines() if 'B2FF8' in l.upper() or l.startswith('00FF82')])
finally:
    h.close()
