"""Play the 'LOOKS' campaign (10 levels, same grid, differ only in mission/tower bytes); at each level start dump RAM + screenshot.
usage: run_camp.py BUILD_DIR OUT_DIR [n_levels]"""
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
_r0=_ed.grab
build=Path(sys.argv[1]); out=Path(sys.argv[2]); out.mkdir(parents=True,exist_ok=True)
N=int(sys.argv[3]) if len(sys.argv)>3 else 10
RS=0x77c80
h=Nebulus(workdir='/tmp/looks/wd_camp',game=build)
def K(k,n=1,hold=0.2,gap=0.35):
    for _ in range(n): h.key(k,hold=hold); time.sleep(gap)
def rs(): return struct.unpack('>20H',grab(h,RS,40,'rs'))
def force():
    poke(h,0x33a46,bytes([0,1])); poke(h,0x33a20,bytes([0,4])); poke(h,0x33a1e,bytes([0,0]))
def wait_level(pos,timeout=120):
    t0=time.time()
    while time.time()-t0<timeout:
        time.sleep(1.0)
        w=rs()
        if w[1]==pos and W(h,0x33a20)==0 and W(h,0x33938)==1: return True
    return False
try:
    print('title',h.boot_to_title(timeout=240),flush=True); time.sleep(3)
    h.key('F10',hold=0.5); time.sleep(2)
    K('Down'); K('Control_R',hold=0.4,gap=1.0); K('Control_R',hold=0.4,gap=1.0); K('Control_R',hold=0.4,gap=0.5)
    for i in range(N):
        ok=wait_level(i)
        poke(h,0x76c04,bytes([0xff,0xff]))   # trainer E (enemies off): the frog survives, the door can be forced; sprite tables are built regardless
        time.sleep(2.5)
        print(f"level {i} ok={ok} rsPos {rs()[1]} rsLvl {rs()[2]} tower {W(h,0x3390c)} mission {W(h,0x33910)} st {W(h,0x33a20)} states {[W(h,0x3398c+2*k) for k in range(4)]}",flush=True)
        h.shot(str(out/f'lvl{i}.png'))
        d=grab(h,0,0x80000,'big'); open(out/f'lvl{i}.bin','wb').write(d)
        time.sleep(2.0)
        h.shot(str(out/f'lvl{i}b.png'))
        force()
finally: h.close()
