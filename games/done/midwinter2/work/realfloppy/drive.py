"""Real-floppy investigation driver (private HOME, one Hatari at a time).
python3 drive.py NAME MACHINE DISKDIR MODE [TOS]
MODE: instant  = hatari-option --disk-a B.st at the prompt, then key
      eject    = eject A (--disk-a ""), wait 3 s, insert B, wait 3 s, key
      nokey    = swap and DON'T press a key (watch FDC)
"""
import os, sys, time, shutil, re
from pathlib import Path
ROOT = Path('/home/ryan/Code/AtariST/gamebench')
sys.path.insert(0, str(ROOT/'tools'))
os.environ['HOME'] = '/tmp/mwrf/home'
os.environ['HATARI'] = '/home/ryan/Code/AtariST/hattari/build/src/hatari'
from stharness import Hatari, TOS
from PIL import Image, ImageChops, ImageStat
MW = ROOT/'games/done/midwinter2'
name, machine, diskdir, mode = sys.argv[1:5]
tos = TOS[sys.argv[5]] if len(sys.argv) > 5 else None
diskdir = Path(diskdir).resolve()
scr = Path('/tmp/mwrf')/name; shutil.rmtree(scr, ignore_errors=True); scr.mkdir(parents=True)
for s, d in (('FFA_boot.st','ffa_boot.st'),('FFB_graphics.st','ffb_gfx.st')):
    shutil.copy(diskdir/s, scr/d)
empty = scr/'empty'; empty.mkdir()
tracef = scr/'fdc.trace'
h = Hatari(game_dir=empty, snapshot=None, memsize_kb=1024, machine=machine, tos=tos, autorun=None,
           workdir=str(scr/'run'),
           extra=['--disk-a', str(scr/'ffa_boot.st'), '--drive-b', os.environ.get('DRIVEB','false'), '--fastfdc', 'no', '--trace', 'fdc', '--trace-file', str(tracef)] + os.environ.get('EXTRA','').split())
def sdiff(ref, box):
    cur = Image.open(h.shot()).convert("RGB").crop(box)
    d = ImageChops.difference(cur, Image.open(ref).convert("RGB").crop(box))
    return sum(ImageStat.Stat(d).mean) / 3
def tl(): return tracef.stat().st_size if tracef.exists() else 0
def L(*a): print(time.strftime('%H:%M:%S'), *a, flush=True)
try:
    if os.environ.get('CPUCLK'):
        h.set_cpuclock(int(os.environ['CPUCLK'])); h.shot(scr/'clk.png')
    t0 = time.time(); last = (-1, time.time())
    while time.time()-t0 < 500:
        time.sleep(3)
        n = tl()
        if n != last[0]: last = (n, time.time())
        elif n > 4_000_000 and time.time()-last[1] > 25: break
    else:
        h.shot(scr/'noprompt.png'); raise RuntimeError('no idle')
    h.shot(scr/'idle.png')
    L('prompt after %.0f s' % (time.time()-t0), 'trace bytes', tl())
    time.sleep(8)
    n0 = tl(); L('idle 8s at prompt: trace growth', tl()-n0)
    h.shot(scr/'prompt.png')
    mark = tl()
    open(tracef,'ab').write(b'\n==== MARK SWAP ====\n')
    if mode == 'keyfirst':
        for i in range(2):
            h.cmd("hatari-event keypress 57"); time.sleep(5)
            L('wrong-disk key', i, 'trace growth', tl()-mark)
        time.sleep(30); L('after 30 s more', tl()-mark)
        h.shot(scr/'wrongdisk.png')
        mark = tl()
        h.cmd(f"hatari-option --disk-a {scr/'ffb_gfx.st'}")
    elif mode == 'instant' or mode == 'nokey':
        h.cmd(f"hatari-option --disk-a {scr/'ffb_gfx.st'}")
    elif mode == 'eject':
        h.cmd('hatari-option --disk-a ""'); time.sleep(3)
        h.cmd(f"hatari-option --disk-a {scr/'ffb_gfx.st'}"); time.sleep(3)
    time.sleep(3)
    L('after swap, trace growth', tl()-mark)
    if mode != 'nokey':
        open(tracef,'ab').write(b'\n==== MARK KEY ====\n')
        for i in range(3):
            h.cmd("hatari-event keypress 57"); time.sleep(4)
            L('key', i, 'trace growth', tl()-mark)
    time.sleep(40)
    L('+40s trace growth', tl()-mark)
    try: h.shot(scr/'after.png')
    except Exception as e: L('shot failed', e)
    print(h._logtext()[-600:])
finally:
    h.close()
