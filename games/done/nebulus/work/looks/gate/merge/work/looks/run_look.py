"""Level-start RAM dumps (512 KB + screenshots + RS words) of a campaign (rsPos = level k) or of the stock "Original game" sequence.
usage: run_look.py BUILD_DIR OUT_DIR N [camp|stock] [ste|megaste|st]
camp:  F10 -> Campaigns > -> first campaign -> Play; forced door between levels.   stock: F10 -> Original game; forced door.
The trainer E (enemies off) is poked at the first level so the frog survives; every dump is taken 2.5 s after the level is running."""
import sys,time,struct,os
sys.path.insert(0,'/home/ryan/Code/AtariST/gamebench/games/in_progress/nebulus/work/editor')
from ed import *
from pathlib import Path
import ed as _ed
_W0=_ed.W
def W(h,a):
    for _ in range(6):
        try: return _W0(h,a)
        except Exception: time.sleep(0.3)
    raise RuntimeError('W failed')
build=Path(sys.argv[1]); out=Path(sys.argv[2]); out.mkdir(parents=True,exist_ok=True)
N=int(sys.argv[3]); MODE=sys.argv[4] if len(sys.argv)>4 else 'camp'; MACH=sys.argv[5] if len(sys.argv)>5 else 'ste'
import stharness
kw={}
if MACH=='megaste': kw=dict(machine='megaste',tos=stharness.TOS['2.06'],memsize_kb=4096)
if MACH=='st': kw=dict(machine='st',tos=stharness.TOS['1.04'])
RS=0x77c80
# regions dumped when FULL is not set: sprite buffers (balls + eye frames), skyline buffer, palette, raster colours, grid + game variables, timer, RS (everything the look gate compares)
REG=[(0x14560,0x400),(0x24be0,0x2fae0-0x24be0),(0x100e0,0x1000),(0x351ac,0x20),(0x40380,0x80),(0x327f0,0x1000),(0x33900,0x180),(0x3ad90,0x20),(0x77c80,0x80)]
h=Nebulus(workdir=f'/tmp/looks/wd_{os.getpid()}',game=build,**kw)
def K(k,n=1,hold=0.2,gap=0.35):
    for _ in range(n): h.key(k,hold=hold); time.sleep(gap)
def rs(): return struct.unpack('>32H',grab(h,RS,64,'rs'))
def force():
    poke(h,0x33a46,bytes([0,1])); poke(h,0x33a20,bytes([0,4])); poke(h,0x33a1e,bytes([0,0]))
def running(): return W(h,0x33a20)==0 and W(h,0x33938)==1
def wait_level(i,last,timeout=150):
    t0=time.time()
    while time.time()-t0<timeout:
        time.sleep(1.0)
        if MODE=='camp':
            if rs()[1]==i and running(): return True
        else:
            key=(W(h,0x3390c),W(h,0x33910))
            if running() and (i==0 or key!=last): return True
    return False
last=None
try:
    print('title',h.boot_to_title(timeout=240),flush=True); time.sleep(3)
    h.key('F10',hold=0.5); time.sleep(2)
    if MODE=='camp':
        K('Down'); K('Control_R',hold=0.4,gap=1.0); K('Control_R',hold=0.4,gap=1.0); K('Control_R',hold=0.4,gap=0.5)
    else:
        K('Control_R',hold=0.4,gap=3.0)          # Original game -> back at the title
        h.key('Right',hold=0.5); time.sleep(0.5); h.key('Control_R',hold=1.0)      # start the game as the plain harness does (boot_to_game)
    for i in range(N):
        ok=wait_level(i,last)
        if i==0 and not os.environ.get('NOE'): poke(h,0x76c04,bytes([0xff,0xff]))
        time.sleep(float(os.environ.get('DELAY','2.5')))
        w=rs(); last=(W(h,0x3390c),W(h,0x33910))
        print(f"level {i} ok={ok} rsPos {w[1]} rsLvl {w[2]} tower {last[0]} mission {last[1]} rows {W(h,0x33912)} rsCol {w[31]} rsEye(word@+50) {w[25]:04x} st {W(h,0x33a20)} timer {grab(h,0x3ad98,6,'t').hex()}",flush=True)
        h.shot(str(out/f'lvl{i}.png'))
        if os.environ.get('FULL'):
            d=grab(h,0,0x80000,'big')
        else:
            d=bytearray(0x80000)
            for a,n in REG: d[a:a+n]=grab(h,a,n,'reg')
        open(out/f'lvl{i}.bin','wb').write(bytes(d))
        force()
finally: h.close()
