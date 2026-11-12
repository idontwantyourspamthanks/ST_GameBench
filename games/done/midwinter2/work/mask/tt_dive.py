import sys, time
from pathlib import Path
from PIL import Image
G = Path('/home/ryan/Code/AtariST/gamebench/games/in_progress/midwinter2')
sys.path.insert(0, str(G / 'work/vehicles_p3b')); sys.path.insert(0, str(G / 'tools')); sys.path.insert(0, '/home/ryan/Code/AtariST/gamebench/tools')
import vt
from stharness import TOS
import mw2raids
tag, bdir = sys.argv[1], sys.argv[2]          # e.g. stock build/mask_stock
out = G / 'work/mask'
h = vt.Hatari(snapshot=None, memsize_kb=4096, game_dir=G / bdir, machine='tt', tos=TOS['3.06'], extra=['--mmu', 'true'])
n = [0]; last = [None]
def snap(name):
    im = Image.open(h.shot()).convert('RGB')
    im = im.crop((0, 0, 640, 400) if im.width == 640 else (96, 58, 736, 458))
    im.save(out / name)
def sample(phase, force=False):
    for _try in range(5):
        try:
            ty = h.peekw(0x6220); kb = vt.memb(h, 0xb4680, 8); bank = h.peekw(0x6746); break
        except Exception: time.sleep(0.3)
    else: return last[0]
    n[0] += 1
    if force or ty != last[0] or n[0] % 6 == 0:
        snap(f'ttm_{tag}_{n[0]:03d}_{phase}_t{ty:02x}.png')
    last[0] = ty
    print(tag, n[0], phase, 'type', hex(ty), 'bank', hex(bank), 'KB', ' '.join(f'{b:02x}' for b in kb), flush=True)
    return ty
def hold(keysym, secs, phase):
    h._xdo('mousedown', keysym)
    t = time.time()
    try:
        while time.time() - t < secs: sample(phase); time.sleep(0.25)
    finally:
        h._xdo('mouseup', keysym)
try:
    t0 = time.time()
    time.sleep(70)
    ref = G / 'work' / 'ref' / 'mode_select.png'
    for i in range(60):
        h.cmd('hatari-event keypress 57'); time.sleep(5)
        if h.screen_matches(ref, (280, 350, 560, 420)): break
    for i in range(6):
        time.sleep(3); h.cmd('hatari-event keypress 50'); time.sleep(6)
        if not h.screen_matches(ref, (280, 350, 560, 420)): break
    time.sleep(45)
    mw2raids._enter_raids_from_hall(h)
    r = mw2raids.enter_raid(h, 275, 249)
    print(tag, 'entered', r, 'marker', vt.memb(h, 0xb2ff8, 4), flush=True)
    time.sleep(6); sample('boat', True)
    h.key('Escape', hold=0.6)
    t = time.time()
    while time.time() - t < 25: sample('esc'); time.sleep(0.3)
    hold('1', 12, 'dive')
    t = time.time()
    while time.time() - t < 6: sample('rel1'); time.sleep(0.3)
    hold('3', 12, 'surf')
    t = time.time()
    while time.time() - t < 4: sample('rel2'); time.sleep(0.3)
    hold('1', 12, 'dive2')
    sample('end', True)
    print(tag, 'bus errors', sum('Bus Error' in l for l in h._logtext().splitlines()), flush=True)
finally:
    h.close()
