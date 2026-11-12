#!/usr/bin/env python3
"""v1.4 FLOPPY set cold boot: insert-graphics prompt -> M/J/K -> Raids map (pointer series) -> island -> 3D. Raw lines printed.
usage: fl14.py NAME MACHINE MEM"""
import sys, time, shutil, re
from pathlib import Path
from PIL import Image, ImageChops, ImageStat
ROOT = Path('/home/ryan/Code/AtariST/gamebench/games/in_progress/midwinter2')
sys.path.insert(0, str(ROOT / "tools")); sys.path.insert(0,'/home/ryan/Code/AtariST/gamebench/tools')
from mw2harness import Hatari
import mw2raids
from stharness import MACHINE_TOS
name, machine, mem = sys.argv[1:4]
tt = machine == 'tt'
out = ROOT/'work/mapptr'/name; out.mkdir(exist_ok=True)
scratch = Path(f'/tmp/fl14run_{name}'); shutil.rmtree(scratch, ignore_errors=True); scratch.mkdir()
for s, d in (('FFA_boot.st','A.st'), ('FFB_graphics.st','B.st')): shutil.copy(f'/tmp/fl14/{s}', scratch/d)
shutil.copy(ROOT/'work/disk_overlay/FILES/FFD', scratch/'D.st'); shutil.copy('/tmp/fl14/FFC_missions.st', scratch/'C.st')
empty = scratch/'empty'; empty.mkdir()
h = Hatari(snapshot=None, memsize_kb=int(mem), machine=machine, tos=MACHINE_TOS[machine], game_dir=empty,
           extra=(['--mmu','true'] if tt else []) + ['--disk-a', str(scratch/'A.st'), '--disk-b', str(scratch/'D.st')])
T0 = time.time()
class _T:
    def __getattr__(self, n): return getattr(time, n)
    def sleep(self, secs):
        end = time.time() + secs
        while True:
            left = end - time.time()
            if left <= 0: break
            time.sleep(min(4, left))
            if missions_prompt(): swap()
mw2raids.time = _T()
swapped = [0]
def missions_prompt():
    im = Image.open(h.shot()).convert('L'); ox, oy = (0, 0) if tt else (96, 58)
    reg = im.crop((ox+110, oy+170, ox+530, oy+230)).point(lambda v: 255 if v > 200 else 0).histogram()[255]
    allw = im.crop((ox, oy, ox+640, oy+160)).point(lambda v: 255 if v > 60 else 0).histogram()[255]
    return reg > 100 and allw < 50
def swap():
    swapped[0] += 1
    h.cmd(f"hatari-option --disk-a {scratch/'C.st'}"); time.sleep(2); h.cmd('hatari-event keypress 57')
    P('Insert Missions Disk prompt -> swapped A to FFC (#%d)' % swapped[0])
def P(*a): print(f'{time.time()-T0:6.1f}s', *a, flush=True)
def sdiff(ref, box):
    cur = Image.open(h.shot()).convert('RGB')
    r = Image.open(ref).convert('RGB').crop(box)
    if cur.width == 640: box = (box[0]-96, box[1]-58, box[2]-96, box[3]-58)
    d = ImageChops.difference(cur.crop(box), r)
    return sum(ImageStat.Stat(d).mean) / 3
def arrow(im, px, py):
    ox, oy = (0, 0) if tt else (96, 58); cx, cy = ox+2*px, oy+2*py; c = 0; p = im.load()
    for yy in range(cy-2, cy+28):
        for xx in range(cx-2, cx+22):
            if 0 <= xx < im.width and 0 <= yy < im.height:
                r, g, b = p[xx, yy]
                if r > 200 and 50 < g < 140 and b < 80: c += 1
    return c
try:
    ins = ROOT/'work/floppy_tests/ref_insert_graphics.png'; box = (280, 360, 560, 420)
    t0 = time.time(); k = 0
    while time.time() - t0 < 300:
        time.sleep(4)
        if k < 6: h.shot(str(out/f'boot{k}.png')); k += 1
        if sdiff(ins, box) < 0.3: break
    else: raise RuntimeError('no insert-graphics prompt')
    P('insert-graphics prompt'); h.shot(str(out/'insert_prompt.png'))
    h.cmd(f"hatari-option --disk-a {scratch/'B.st'}"); time.sleep(2)
    ref = ROOT/'work/ref/mode_select.png'
    for i in range(40):
        h.cmd('hatari-event keypress 57'); time.sleep(5)
        if h.screen_matches(ref, (280, 350, 560, 420)): break
    else: raise RuntimeError('no M/J/K screen')
    P('M/J/K screen after', i, 'presses')
    P('MWPO', h.debug('m $b2ff8 4').strip().splitlines()[-1])
    h.dump(str(out/'ram_mjk.bin'), 0, 0x100000); time.sleep(3)
    data = (out/'ram_mjk.bin').read_bytes()
    for m in re.finditer(rb'v[0-9.]+ enhanced by dad_prg', data): P('credit string in RAM @', hex(m.start()), m.group().decode())
    for i in range(5):
        time.sleep(3); h.cmd('hatari-event keypress 50'); time.sleep(6)
        if not h.screen_matches(ref, (280, 350, 560, 420)): break
    time.sleep(45 if tt else 8)
    mw2raids._enter_raids_from_hall(h)
    P('raids map reached; mode', h.peekw(0x700a), 'island', hex(h.peekw(0xeb9c)))
    t0 = time.time(); k = 0; mv = [(300, 250), (450, 200), (200, 300), (380, 330)]
    while time.time() - t0 < 30:
        if k % 4 == 2: h.goto(*mv[(k // 4) % 4])
        f = h.fps(50); s = h.shot(str(out/f'map{k:02d}.png')); px, py = h.peekw(0x6fae), h.peekw(0x6fb2)
        P(f'map{k:02d} mode={h.peekw(0x700a)} flips/50vbl={f["flips"]} px={px} py={py} arrow_px={arrow(Image.open(s).convert("RGB"), px, py)}'); k += 1
    P('enter_raid', mw2raids.enter_raid(h, 446, 177))
    time.sleep(10)
    P('vehicle $6220 =', hex(h.peekw(0x6220)), 'view $700a =', hex(h.peekw(0x700a)))
    P('MWPO', h.debug('m $b2ff8 4').strip().splitlines()[-1])
    P('site $26ea2', h.debug('m $26ea2 6').strip().splitlines()[-1])
    P('TT_F $b4f80', h.debug('m $b4f80 2').strip().splitlines()[-1])
    h.shot(str(out/'3d.png'))
except Exception as e:
    import traceback; P('EXC', repr(e)); traceback.print_exc()
    try: h.shot(str(out/'exc.png'))
    except Exception: pass
finally:
    h.close()
