"""after_fl.py dir tag : floppy: at the prompt swap to FFB, press space, screenshot every 2 s; report whether the credit text stays"""
import sys, time, shutil
from pathlib import Path
ROOT = Path('/home/ryan/Code/AtariST/midwinter2')
sys.path.insert(0, str(ROOT / 'tools'))
from mw2harness import Hatari
B = Path.home() / "Emulators/BIOS/AtariST"
TOS162 = B / "TOS v1.62 (1990)(Atari Corp)(STE)(GB)[STE TOS, Rev 2].img"
src, tag = Path(sys.argv[1]), sys.argv[2]
scratch = Path(f'/tmp/cr_{tag}'); shutil.rmtree(scratch, ignore_errors=True); scratch.mkdir()
shutil.copy(src / 'FFA_boot.st', scratch / 'A.st'); shutil.copy(src / 'FFB_graphics.st', scratch / 'G.st')
empty = scratch / 'empty'; empty.mkdir()
h = Hatari(snapshot=None, memsize_kb=1024, machine='ste', tos=TOS162, game_dir=empty, extra=['--disk-a', str(scratch / 'A.st')])
try:
    f = Path(f'/tmp/cr/af_{tag}.txt'); f.write_text("r\n")
    h.debug(f"b pc = $1f620 :trace :once :file {f}")
    t0 = time.time()
    while 'Next PC' not in h._logtext() and time.time() - t0 < 240: time.sleep(1)
    time.sleep(2)
    h.cmd(f"hatari-option --disk-a {scratch / 'G.st'}"); time.sleep(2)
    h.cmd("hatari-event keypress 57")
    for i in range(20):
        time.sleep(2)
        for k in range(4):
            try:
                h.shot(str(ROOT / f'work/credit/tl/{tag}_{i:02d}.png')); break
            except Exception as e:
                time.sleep(1)
        else:
            print('shot fail', i); print(h._logtext()[-600:]) if i==0 else None
        if i % 3 == 2: h.cmd("hatari-event keypress 57")
finally:
    h.close()
