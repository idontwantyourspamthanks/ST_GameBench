"""Gate (a): the game's FIRST FDC `restore` must complete (not be cut by the game's own force interrupt).

    python3 bootgate.py NAME MACHINE CLK DISKDIR [--driveb] [--stock] [--expect pass|fail|any] [--tos NAME] [--ext st|msa]

MACHINE ste|megaste|st|tt; CLK 8|16 (16: `hatari-option --cpuclock 16` right after start, as the realfloppy investigation did: the
command-line option is not honoured on a Mega STE).  DISKDIR holds FFA_boot.st (+ FFB_graphics.st).  Cold boot of FFA with
`--fastfdc no --trace fdc`, wait for the orange "Insert Graphics Disk" prompt, parse the trace.  Private HOME, scratch /tmp/mw2f/<NAME>.
--stock: the image has the game's stock FDC wait (v1.3-v1.5, the original): time-out 2.18 s at 8 MHz.  Result line `GATE first-restore ...` and a JSON-ish summary in work/floppy16/out/<NAME>.txt.
"""
import os, sys, time, shutil
from pathlib import Path
HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
GB = ROOT.parent.parent.parent
os.environ['HOME'] = '/tmp/mw2s/home'
os.environ['HATARI'] = os.environ.get('HATARI', '/home/ryan/Code/AtariST/hattari/build/src/hatari')
sys.path.insert(0, str(GB / 'tools')); sys.path.insert(0, str(HERE))
from stharness import Hatari, TOS
import fdctrace as F
from PIL import Image, ImageChops, ImageStat

a = sys.argv[1:]
name, machine, clk, diskdir = a[:4]
opts = a[4:]
driveb = '--driveb' in opts
expect = opts[opts.index('--expect') + 1] if '--expect' in opts else 'pass'
tos = TOS[opts[opts.index('--tos') + 1]] if '--tos' in opts else None
ext = opts[opts.index('--ext') + 1] if '--ext' in opts else 'st'      # st | msa: boot the .msa copy
diskdir = Path(diskdir).resolve()
scr = Path('/tmp/mw2s') / name
shutil.rmtree(scr, ignore_errors=True); scr.mkdir(parents=True)
OUT = HERE / 'out'; OUT.mkdir(exist_ok=True)
log = []
def L(*x):
    s = ' '.join(str(v) for v in x); log.append(s); print(s, flush=True)

shutil.copy(diskdir / f'FFA_boot.{ext}', scr / f'disk_boot.{ext}')
if driveb:
    shutil.copy(GB / 'games/done/midwinter2/work/disk_overlay/FILES/FFD', scr / 'disk_camp.st')
(scr / 'empty').mkdir()
tracef = scr / 'fdc.trace'
extra = ['--disk-a', str(scr / f'disk_boot.{ext}'), '--fastfdc', 'no', '--trace', 'fdc', '--trace-file', str(tracef)]
extra += ['--disk-b', str(scr / 'disk_camp.st')] if driveb else ['--drive-b', 'false']
extra += ['--sound', os.environ.get('MW2S_SOUND', 'off')]
extra += os.environ.get('MW2S_EXTRA', '').split()
if machine == 'tt':
    extra += ['--mmu', 'true']
h = Hatari(game_dir=scr / 'empty', snapshot=None, memsize_kb=1024, machine=machine, tos=tos, autorun=None,
           workdir=str(scr / 'run'), extra=extra)
try:
    if clk != '8':
        h.set_cpuclock(int(clk)); h.shot(scr / 'clk.png')
    ins = ROOT / 'work/floppy_tests/ref_insert_graphics.png'
    box = (280, 360, 560, 420)
    def sdiff():
        img = Image.open(h.shot()).convert('RGB')
        sb = (box[0] - 96, box[1] - 58, box[2] - 96, box[3] - 58) if img.width == 640 else box      # TT screenshots have no border
        d = ImageChops.difference(img.crop(sb), Image.open(ins).convert('RGB').crop(box))
        return sum(ImageStat.Stat(d).mean) / 3
    t0 = time.time(); last = (-1, time.time()); seen = False
    while time.time() - t0 < 420:
        time.sleep(4)
        n = tracef.stat().st_size if tracef.exists() else 0
        if n != last[0]: last = (n, time.time())
        if sdiff() < 0.3:
            seen = True; break
        if n > 2_000_000 and time.time() - last[1] > 30:
            break
    L('prompt %s after %.0f s, trace %d B' % ('seen' if seen else 'NOT seen (trace idle)', time.time() - t0, tracef.stat().st_size))
    time.sleep(3)
    h.shot(scr / 'prompt.png'); shutil.copy(scr / 'prompt.png', OUT / f'{name}_prompt.png') if (scr / 'prompt.png').exists() else None
finally:
    h.close()
ok, _ = F.gate_first_restore(name, tracef, '--stock' in opts, L, OUT / f'{name}.cmds.txt')
if 'psg_write' in os.environ.get('MW2S_EXTRA', ''):
    import io, contextlib, psgcheck
    _b = io.StringIO()
    with contextlib.redirect_stdout(_b):
        _p = psgcheck.check(tracef, name)
    for _l in _b.getvalue().splitlines():
        L(_l)
    ok = ok and _p
verdict = expect == 'any' or (ok == (expect == 'pass'))
L('VERDICT %s (expected %s): %s' % (name, expect, 'OK' if verdict else 'UNEXPECTED'))
(OUT / f'{name}.txt').write_text('\n'.join(log) + '\n')
sys.exit(0 if verdict else 1)
