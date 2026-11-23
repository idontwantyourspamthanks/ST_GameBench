"""Shipped-zip cell: unzip fresh, cold boot via the harness HD image builder (HDDRIVER ACSI), title credit, tower, patch state, T/E, short play.
usage: zip_verify.py ZIP OUTDIR machine mem tos [--gemdos]"""
import sys, time, zipfile, shutil, re
sys.path.insert(0,'/home/ryan/Code/AtariST/gamebench/tools'); sys.path.insert(0,'/home/ryan/Code/AtariST/gamebench/games/in_progress/nebulus/tools')
from nebulus import Nebulus, TOS
from pathlib import Path
from PIL import Image
zp, out = Path(sys.argv[1]), Path(sys.argv[2]).resolve(); mach, mem, tos = sys.argv[3], int(sys.argv[4]), sys.argv[5]
shutil.rmtree(out, ignore_errors=True); out.mkdir(parents=True)
with zipfile.ZipFile(zp) as z: z.extractall(out / 'unz')
game = out / 'unz' / 'NEBULUS'
print('files', sorted(p.name for p in game.iterdir()))
h = Nebulus(workdir=str(out / 'wd'), machine=mach, tos=TOS[tos], memsize_kb=mem, game=game)
def words(a, n): 
    o = h.debug(f"m ${a:x} {2*n}", 0.6); b = bytes(int(x,16) for x in re.findall(r'\b[0-9a-f]{2}\b', ' '.join(l.split(':',1)[1][:48] for l in o.splitlines() if re.match(r'^[0-9a-f]{8}:', l, re.I))))
    return b[:2*n]
def W(a): return int.from_bytes(words(a,1),'big')
def L(a): return int.from_bytes(words(a,2),'big')
def timer(): return tuple(words(0x3ad98,3)[1::2])
def states(): return tuple(W(0x3398c+2*i) for i in range(4))
try:
    t0 = time.time()
    ok = h.boot_to_title(timeout=400, space_until=(130 if mem > 1024 else 20))
    print('title', ok, '%.0fs' % (time.time()-t0), flush=True)
    box=(96,58,736,458); lit=0
    for i in range(4):
        h.shot(str(out / f'title{i}.png')); im = Image.open(out / f'title{i}.png').convert('RGB').crop(box).crop((128,288,510,318))
        n = sum(1 for p in im.getdata() if p != (0,0,0)); lit = max(lit, n); time.sleep(0.5)
    print('credit band lit pixels (max of 4 shots)', lit)
    time.sleep(1.0)
    h.key('Right', hold=0.5); time.sleep(0.5); h.key('Control_R', hold=1.0); time.sleep(4.0)
    print('tower timer word', hex(W(0x3ad98)), 'timer', timer())
    print('marker', hex(L(0xB0020)), 'sites', W(0xB0024), '| $39ffa', hex(W(0x39ffa)), '$38514', hex(W(0x38514)), hex(L(0x38516)), '$3dcf4', hex(W(0x3dcf4)), hex(L(0x3dcf6)), '$3d698', hex(W(0x3d698)), hex(L(0x3d69a)))
    t1 = timer(); time.sleep(3); t2 = timer(); print('counting', t1, t2, 'changes', t1 != t2)
    print('before keys: frz', hex(W(0x76c02)), 'noen', hex(W(0x76c04)), 'states', states())
    h.key('e', hold=0.5); time.sleep(1.5); print('after E: noen', hex(W(0x76c04)), 'states', states()); time.sleep(3); print('  3s later states', states(), 'timer', timer())
    time.sleep(2.0); a0 = timer(); time.sleep(2.0); a1 = timer(); print('E on, counting (no deaths)', a0, a1, a0 != a1)
    h.key('t', hold=0.5); time.sleep(1.0); a = timer(); time.sleep(3); b = timer(); time.sleep(3); c = timer()
    print('after T: frz', hex(W(0x76c02)), 'timer', a, b, c, 'frozen mid-count', a == b == c)
    h.key('t', hold=0.5); time.sleep(1.0); a = timer(); time.sleep(3); b = timer(); print('T again: frz', hex(W(0x76c02)), a, b, 'running', a != b)
    h.key('e', hold=0.5); time.sleep(1.5); print('E again: noen', hex(W(0x76c04)), 'states', states())
    # short play: walk right, jumps, check alive and timer running
    for i in range(6):
        h.key('Right', hold=1.0); h.key('Control_R', hold=0.15); time.sleep(0.3)
    h.shot(str(out / 'play.png')); a = timer(); time.sleep(2); b = timer()
    print('after play: timer', a, b, 'tower', W(0x3390c), 'vbl', h.vbl(), 'marker', hex(L(0xB0020)))
finally:
    h.close()
