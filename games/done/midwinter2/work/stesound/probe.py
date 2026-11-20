"""Gate (c): disk-swap behaviour with ONE and with TWO drives (STE/Mega STE, `--fastfdc no --trace fdc`).

    python3 swapgate.py NAME MACHINE TOS CLK DRIVES DISKDIR SCEN [SCEN ...]

DRIVES 1 = drive A only; 2 = drive B present, holding the created campaign disk (`2f` = drive B holds FFB_graphics instead).
Boot FFA to the orange "Insert Graphics Disk" prompt (the game's SECOND disk check, which wants FFB at track 0), then per scenario:
  A  wrong disk: press a key with FFA still in drive A.  Measures key -> end of the FDC burst (= when the black prompt is up) from the trace and
     checks that the screen went black (the game's own "Insert Graphics Disk / press any key").
  B  after A: insert FFB into drive A, press a key -> must reach the M/J/K screen (the disk passes).
  C  missing disk: eject drive A, press a key (burst measured as in A), then B.
  D  press a key at the orange prompt with FFA in A and FFB in drive B (2f): the game finds the graphics disk in drive B without a prompt -> M/J/K.
Prints `SWAP <scenario> ...` result lines; work/floppy16/out/NAME.txt.
"""
import os, sys, time, shutil, re
from pathlib import Path
HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
GB = ROOT.parent.parent.parent
os.environ['HOME'] = '/tmp/mw2s/home'
os.environ['HATARI'] = os.environ.get('HATARI', '/home/ryan/Code/AtariST/hattari/build/src/hatari')
sys.path.insert(0, str(ROOT / 'tools')); sys.path.insert(0, str(HERE))
from mw2harness import Hatari
import fdctrace as F
from PIL import Image, ImageChops, ImageStat

a = sys.argv[1:]
name, machine, tosk, clk, drives, diskdir = a[:6]
scens = a[6:]
TOSF = {'162': 'TOS_1_62.img', '206': 'TOS_2_06.img', '104': 'TOS_1_04.img', '306': 'TOS_3_06_uk.img'}
diskdir = Path(diskdir).resolve()
scr = Path('/tmp/mw2s') / name
shutil.rmtree(scr, ignore_errors=True); scr.mkdir(parents=True)
OUT = HERE / 'out'; OUT.mkdir(exist_ok=True)
log = []
def L(*x):
    s = ' '.join(str(v) for v in x); log.append(s); print(s, flush=True)
for src, dst in (('FFA_boot.st', 'disk_boot.st'), ('FFB_graphics.st', 'disk_gfx.st')):     # not A.st / B.st: Hatari auto-inserts <x>B.st into drive B and refuses to swap
    shutil.copy(diskdir / src, scr / dst)
if drives == '2':
    shutil.copy(ROOT / 'work/disk_overlay/FILES/FFD', scr / 'disk_camp.st')
if drives == '2f':
    shutil.copy(diskdir / 'FFB_graphics.st', scr / 'disk_camp.st')
(scr / 'empty').mkdir()
tracef = scr / 'fdc.trace'
extra = ['--disk-a', str(scr / 'disk_boot.st'), '--fastfdc', 'no', '--trace', 'fdc', '--trace-file', str(tracef)]
extra += ['--disk-b', str(scr / 'disk_camp.st')] if drives in ('2', '2f') else ['--drive-b', 'false']
extra += ['--sound', os.environ.get('MW2S_SOUND', 'off')]          # later --sound overrides the harness's `--sound off`; MW2S_SOUND=50066 -> DMA sound + YM mixed
extra += os.environ.get('MW2S_EXTRA', '').split()
h = Hatari(snapshot=None, memsize_kb=int(os.environ.get('MW2S_MEM', '1024')), machine=machine, tos=GB / 'tos' / TOSF[tosk], game_dir=scr / 'empty',
           workdir=str(scr / 'run'), extra=extra)
ins = ROOT / 'work/floppy_tests/ref_insert_graphics.png'
mjk = ROOT / 'work/ref/mode_select.png'
def sdiff(refp, bx):
    img = Image.open(h.shot()).convert('RGB')
    sb = (bx[0] - 96, bx[1] - 58, bx[2] - 96, bx[3] - 58) if img.width == 640 else bx          # TT screenshots have no border
    d = ImageChops.difference(img.crop(sb), Image.open(refp).convert('RGB').crop(bx))
    return sum(ImageStat.Stat(d).mean) / 3
def bright():
    return sum(ImageStat.Stat(Image.open(h.shot()).convert('RGB').crop((96, 58, 736, 458))).mean) / 3
def is_black():
    return bright() < 8
def vbl():
    for _ in range(8):
        try:
            return h.vbl()
        except IndexError:
            time.sleep(1.5)
    raise RuntimeError('debugger did not answer')
def press_confirmed(tries=4):
    """Press a key and require FDC activity within 6 s; a key lost by the harness (seen: no trace growth at all) is pressed again, and the retries are logged."""
    for i in range(tries):
        n0 = tracef.stat().st_size
        key()
        t = time.time()
        while time.time() - t < 6:
            time.sleep(0.5)
            if tracef.stat().st_size > n0 + 2000:
                if i:
                    L('   (key retried %d time(s): the first press(es) produced no FDC activity)' % i)
                return
    L('   (no FDC activity after %d key presses)' % tries)
def key():
    h.cmd('hatari-event keypress 57')
def burst_after(vbl0, quiet_s=4.0):
    """Events after VBL vbl0: (t_first_cmd, t_last_event, n_force) of the first contiguous burst (gaps < 3 s)."""
    ev, Lf, hz = F.parse(tracef)
    ev = [e for e in ev if e['vbl'] >= vbl0 and e['t'] is not None]
    if not ev:
        return None
    t0 = ev[0]['t']; last = t0; nf = 0; ncmd = 0
    for e in ev:
        if e['t'] - last > 3.0:
            break
        last = e['t']; nf += e['kind'] == 'force'; ncmd += e['kind'] in ('cmd1', 'cmd2')
    return t0, last, nf, ncmd, hz
def wait_mjk(timeout=240):
    """The key already pressed has started the check; then, as run_cell does, press space every 5 s (the intro screens want keys) until the M/J/K screen."""
    t = time.time(); n = 0
    while time.time() - t < timeout:
        time.sleep(5)
        if h.screen_matches(mjk, (280, 350, 560, 420)):
            return time.time() - t
        key(); n += 1
    return None
try:
    t0 = time.time()
    while time.time() - t0 < 420:
        time.sleep(4)
        if sdiff(ins, (280, 360, 560, 420)) < 0.3:
            break
    else:
        raise RuntimeError('never saw the orange prompt')
    L('orange prompt after %.0f s wall' % (time.time() - t0))
    time.sleep(3)
    for c in ('m $bbe00 16', 'm $bbe10 16', 'm $5138 4', 'm $ff8900 40', 'm $b96 4', 'm $b9a 4', 'info', 'info ym'):
        L('>>', c); L(h.debug(c, 1.5))
    for i in range(3):
        time.sleep(1); L(h.debug('m $ff8909 6', 0.8).strip().splitlines()[-1])
finally:
    try: h.close()
    except Exception: pass
