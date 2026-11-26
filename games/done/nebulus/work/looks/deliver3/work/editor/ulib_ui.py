import sys, os, time, struct, re, shutil
os.environ.setdefault('HOME', '/tmp/nld/home')
sys.path.insert(0, '/tmp/nld/games/in_progress/nebulus/work/editor')
from ui import *
from pathlib import Path
import stharness
from stharness import Hatari
class UH(Nebulus):
    """Hatari on a prebuilt ACSI image (the user's all-games image), autostart C:\\NEBULUS\\START.TOS"""
    def __init__(self, img, workdir, machine='megaste', tos=None, memsize_kb=4096, autorun='C:\\NEBULUS\\START.TOS', extra=None):
        R = Path(workdir); R.mkdir(parents=True, exist_ok=True)
        ex = ['--gemdos-drive', 'skip', '--acsi', f'0={img}', '--fast-boot', 'no', '--joy1', 'keys'] + (extra or [])
        Hatari.__init__(self, game_dir=ORIGIN, workdir=str(R), machine=machine, tos=tos or stharness.MACHINE_TOS[machine], memsize_kb=memsize_kb,
                        files=[], overlay=Path('/nonexistent'), autorun=autorun, extra=ex)
from nebulus import ORIGIN
def goto(h, idx, tries=40):
    for _ in range(tries):
        items, sel = menu(h)
        if sel == idx: return items
        h.key('Down' if idx > sel else 'Up', hold=0.2); time.sleep(0.45)
    raise RuntimeError(f'goto {idx} failed')
def pick(h, what, gap=1.3):
    items, sel = menu(h)
    idx = what if isinstance(what, int) else [i for i, (a, p, t) in enumerate(items) if t.startswith(what)][0]
    goto(h, idx); h.key('Control_R', hold=0.35); time.sleep(gap)
def open_manager(h):
    for _ in range(4):
        h.key('F10', hold=0.4); time.sleep(2.0)
        if L(h, 0x70) != 0x382d8: return True
    return False
def wait_running(h, tmo=60):
    t0 = time.time()
    while time.time() - t0 < tmo:
        time.sleep(0.7)
        if W(h, 0x33a20) == 0 and W(h, 0x33938) == 1: time.sleep(0.8); return True
    return False
def flag_byte(h): return grab(h, RS + 50, 1, 'fl')[0]
def tower_menu(h, label, gap=1.3):
    h.key('Control_R', hold=0.35); time.sleep(1.5)
    menu(h)
    pick(h, 'Tower >', 1.0); pick(h, label, gap)
def pal(h): return grab(h, 0x351ac, 32, 'p').hex()
def errors(h):
    log = open(h.R / 'log.txt', errors='replace').read()
    return [l for l in log.splitlines() if re.search(r'Address Error|Bus Error|Illegal|Double|exception', l)]
def level_menu(h, label, gap=1.3):
    h.key('Control_R', hold=0.35); time.sleep(1.5)
    menu(h)
    pick(h, 'Level >', 1.0); pick(h, label, gap)
def mk_snap(build, snap, machine='ste', wd='/tmp/nld/x/wdsnap'):
    kw = {}
    if machine == 'megaste': kw = dict(machine='megaste', tos=stharness.TOS['2.06'], memsize_kb=4096)
    if machine == 'st': kw = dict(machine='st', tos=stharness.TOS['1.04'])
    h = Nebulus(workdir=wd, game=Path(build), **kw)
    ok = h.boot_to_title(timeout=240); time.sleep(3)
    p = Path('/tmp/nld/home/.config/hatari/hatari.sav'); p.unlink(missing_ok=True); h.cmd('hatari-shortcut savemem')
    for _ in range(100):
        if p.exists() and p.stat().st_size > 0: break
        time.sleep(0.2)
    time.sleep(1.5); shutil.copy(p, snap); h.close(); time.sleep(1)
    return ok
def save_load_disk(h, disk, what):
    m = None
    pick(h, what, 1.2); h.key('Control_R', hold=0.35)
    for _ in range(80):
        time.sleep(0.5)
        if W(h, V + 174) == 0:
            a = L(h, V + 20)
            if a: m = grab(h, a, 48, 'ms').split(b'\0')[0].decode('latin1'); break
    return m
