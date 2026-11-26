"""NebGateCore cell: final_cell.py without the editor flow (stale menu navigation in v1.1) - cold boot, credit, F10 open/close, tower, hook bytes, E/T, 20 s drive. usage as final_cell.py"""
"""(orig doc) Final shipped-zip cell. usage: final_cell.py ZIP OUTDIR machine mem tos
fresh unzip -> harness HD image of the unzipped folder -> title/credit -> F10 manager -> zero-OVL editor flow (new level, one cell, Save) ->
tower (NEPO, hook bytes, E/T, 20 s drive) -> close -> file read back from the image -> reboot with the saved file -> level in the list -> play it."""
import sys, time, zipfile, shutil, re, subprocess, os
sys.path.insert(0,'/home/ryan/Code/AtariST/gamebench/tools'); sys.path.insert(0,'/home/ryan/Code/AtariST/gamebench/games/in_progress/nebulus/tools')
from nebulus import Nebulus, TOS
from pathlib import Path
from PIL import Image
zp, out = Path(sys.argv[1]).resolve(), Path(sys.argv[2]).resolve(); mach, mem, tos = sys.argv[3], int(sys.argv[4]), sys.argv[5]
shutil.rmtree(out, ignore_errors=True); out.mkdir(parents=True)
(out/'unz').mkdir(); shutil.copytree(zp, out/'unz'/'NEBULUS')
game = out / 'unz' / 'NEBULUS'
print('files', sorted(p.name for p in game.iterdir()), 'ovl zero', not any((game/'NEBLEVEL.OVL').read_bytes()))
def mk(g, name):
    return Nebulus(workdir=str(out / name), machine=mach, tos=TOS[tos], memsize_kb=mem, game=g)
def words(h, a, n):
    o = h.debug(f"m ${a:x} {n}", 0.6)
    b = bytes(int(x,16) for l in o.splitlines() if re.match(r'^[0-9a-f]{8}:', l, re.I) for x in re.findall(r'(?<=\s)[0-9a-f]{2}(?=\s)', l.split(':',1)[1][:48]))
    return b[:n]
def W(h,a): return int.from_bytes(words(h,a,2),'big')
def L(h,a): return int.from_bytes(words(h,a,4),'big')
def lit(path, box):
    im = Image.open(path).convert('RGB').crop(box); return sum(1 for p in im.getdata() if p != (0,0,0))
PIC=(96,58,736,458)
def shot(h, n):
    p = out / f'{n}.png'; h.shot(str(p)); return p
def crop_lit(h, n, box):
    p = shot(h, n); im = Image.open(p).convert('RGB').crop(PIC).crop(box); return sum(1 for q in im.getdata() if q != (0,0,0))
def K(h, k, hold=0.2, gap=0.5): h.key(k, hold=hold); time.sleep(gap)
def timer(h): return tuple(words(h,0x3ad98,6)[1::2])
def states(h): return tuple(W(h,0x3398c+2*i) for i in range(4))
slow = mem > 1024
h = mk(game, 'wd1')
try:
    t0=time.time(); ok=h.boot_to_title(timeout=400, space_until=(130 if slow else 20)); print('title', ok, '%.0fs'%(time.time()-t0), flush=True); time.sleep(2)
    print('marker', words(h,0xB0020,4), 'sites word', W(h,0xB0024), 'reused', W(h,0xB0026))
    print('credit band lit px (4 shots)', max(crop_lit(h,f'title{i}',(128,288,510,318)) for i in range(4)))
    K(h,'F10',1.0,2.5); print('manager open: $70 =', hex(L(h,0x70)), 'title text rows lit px =', crop_lit(h,'mgr',(100,160,600,200)), '(0 = title gone), menu text px =', crop_lit(h,'mgr2',(130,0,330,120)))
    K(h,'F10',1.0,2.5); print('manager closed again: $70 =', hex(L(h,0x70)), '(000382d8 = game VBL)', 'title text rows lit px =', crop_lit(h,'mgr3',(100,160,600,200)))
    time.sleep(1.0); h.key('Right', hold=0.5); time.sleep(0.5); h.key('Control_R', hold=1.0); time.sleep(5.0)
    print('tower: timer word', hex(W(h,0x3ad98)), 'timer', timer(h), 'tower', W(h,0x3390c))
    print('marker', hex(L(h,0xB0020)), 'sites', W(h,0xB0024), '| $39ffa', hex(W(h,0x39ffa)), '$38514', hex(W(h,0x38514)), hex(L(h,0x38516)), '$3dcf4', hex(W(h,0x3dcf4)), hex(L(h,0x3dcf6)),
          '$3d698', hex(W(h,0x3d698)), hex(L(h,0x3d69a)), '$3a332', hex(W(h,0x3a332)), '$377a2', hex(W(h,0x377a2)), hex(L(h,0x377a4)), '$3b87a', hex(L(h,0x3b87a)), '$37c42', words(h,0x37c42,4).hex(), '$38486', words(h,0x38486,4).hex(), '$3853a', words(h,0x3853a,4).hex(), '$39e2c', hex(W(h,0x39e2c)))
    K(h,'e',0.5,1.5); print('E: noen', hex(W(h,0x76c04)), 'states', states(h)); time.sleep(2); a0=timer(h); time.sleep(2); a1=timer(h); print('E on timer counts', a0, a1, a0!=a1)
    K(h,'t',0.5,1.0); a=timer(h); time.sleep(3); b=timer(h); time.sleep(3); c=timer(h); print('T: frz', hex(W(h,0x76c02)), a, b, c, 'frozen', a==b==c)
    K(h,'t',0.5,1.0); a=timer(h); time.sleep(3); b=timer(h); print('T again running', a, b, a!=b)
    K(h,'e',0.5,1.0); print('E off: noen', hex(W(h,0x76c04)))
    t1=time.time(); v0=h.vbl(); n=0
    while time.time()-t1 < 20:
        h.key('Right', hold=1.0); h.key('Control_R', hold=0.15); time.sleep(0.2); n+=1
    shot(h,'drive'); print('20 s drive: %d rounds, vbl +%d, tower %d, timer %s, frog x,y,state %d %d %d' % (n, h.vbl()-v0, W(h,0x3390c), timer(h), W(h,0x33a16), W(h,0x33a18), W(h,0x33a20)))
    log = (out/'wd1'/'log.txt').read_text(errors='replace'); print('crash lines in Hatari log:', len(re.findall(r'Address error|Illegal|double bus|CPU halted', log)))
finally:
    h.close()
